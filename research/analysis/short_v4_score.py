#!/usr/bin/env python3
"""short_v4_score.py — CHẤM 0-sim cho PREREG_SHORT_V4 (memory-lean).

Đo NGUYÊN các mục khoá ở `docs/prereg/PREREG_SHORT_V4.md`:
  §2  LIQ (mất thanh khoản) từ OI: LIQ = 0,5*z_CS(-oi_delta24h) + 0,5*z_CS(-oi_z)  [gate X1 / ranker X2]
  §3  giữ đủ lâu T=72h vs giữ ngắn T=4/12/24h
  §4  độ đều nhịp giảm: Q3a ex-post (bounce=maxFav_72h) + Q3b causal (Shist từ t-72h)
  §5  funding: F1 dự báo CẢ cửa sổ (Fh=9*mean 8 settle trước t) vs N1b (1 settle) / N1a (lookahead)
  §6  chỉ số + CI block-72h (NREP=2000, SEED=20260905, ×1,21), k=3 seed {42,7,13}

KHÔNG train, KHÔNG sim, KHÔNG chạm .java. DEV <= 2025-12-31.
Quy ước funding: rate > 0 => long TRA / SHORT NHAN. f_h(t,sym)=sum rate trong (t, t+h].
"""
import argparse
import glob
import gc
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import short_model_score as SMS  # read_bins, ci_mean

H = 3600000
DEV_CUT = 1767225600000
COST = 0.00112
COST_STRESS = 0.00150
FOLDS = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401", "20230701",
         "20231001", "20240101", "20240401", "20240701", "20241001", "20250101", "20250401",
         "20250701", "20251001"]
HOR = [4, 12, 24, 72]
NEED = {h: 4 * h for h in HOR}
RES = 1024
LBL = None  # panel nhãn (đặt trong main); S giữ `ip` để index lazy


# ───────────────────────── funding (Aerospike cache) ─────────────────────────

class Fund:
    def __init__(self, npz):
        z = np.load(npz, allow_pickle=True)
        self.syms = [str(s) for s in z["syms"]]
        self.ts = z["ts"].astype(np.int64)
        self.rt = z["rt"].astype(np.float64)
        self.sid = z["sid"].astype(np.int32)
        o = np.argsort(self.sid, kind="stable")
        self.ts, self.rt, self.sid = self.ts[o], self.rt[o], self.sid[o]
        self.bounds = np.searchsorted(self.sid, np.arange(len(self.syms) + 1))
        self.cum = np.zeros(len(self.ts) + 1)
        np.cumsum(self.rt, out=self.cum[1:])
        self.s2i = {s: i for i, s in enumerate(self.syms)}

    def compute(self, fsid, t):
        n = len(t)
        f = {h: np.full(n, np.nan, np.float32) for h in HOR}
        r1 = np.full(n, np.nan, np.float32); gap = np.full(n, np.nan, np.float32)
        fb = np.full(n, np.nan, np.float32)
        o = np.argsort(fsid, kind="stable"); fs = fsid[o]; tt_all = t[o]
        b = np.searchsorted(fs, np.arange(len(self.syms) + 1))
        for s in range(len(self.syms)):
            i0, i1 = b[s], b[s + 1]
            if i1 == i0:
                continue
            a, bb = self.bounds[s], self.bounds[s + 1]
            if bb <= a:
                continue
            idx = o[i0:i1]; tt = tt_all[i0:i1]
            ta, ca, ra = self.ts[a:bb], self.cum[a:bb + 1], self.rt[a:bb]
            lo = np.searchsorted(ta, tt, side="right")
            for h in HOR:
                hi = np.searchsorted(ta, tt + h * H, side="right")
                f[h][idx] = (ca[hi] - ca[lo]).astype(np.float32)
            ok = lo < len(ta)
            v = r1[idx]; v[ok] = ra[lo[ok]].astype(np.float32); r1[idx] = v
            g = gap[idx]; g[ok] = (ta[lo[ok]] - tt[ok]).astype(np.float32); gap[idx] = g
            fv = fb[idx]; ok8 = lo >= 1
            if ok8.any():
                j = np.flatnonzero(ok8); li = lo[j]
                lo8 = np.maximum(li - 8, 0)
                fv[j] = (9.0 * (ca[li] - ca[lo8]) / np.maximum(li - lo8, 1)).astype(np.float32)
            fb[idx] = fv
        return f, r1, gap, fb


# ───────────────────────── nhãn (panel) ─────────────────────────

def load_labels(lb_dir, map_csv):
    sys.path.insert(0, os.environ.get("SEL1M_CODE", "/home/ubuntu/sel1m_code"))
    import funding_label_pb as FLPB
    smap = pd.read_csv(map_csv)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    i2s = dict(zip(smap.symId.astype(np.int32), smap.symbol))
    fs = sorted(glob.glob(lb_dir + "/funding_label_*.pb"))
    fs = [f for f in fs if ".part" not in f]
    cols = ["tEpochMs", "symbol"] + ["maxAdv_72h"]
    for h in HOR:
        cols += ["retEnd_%dh" % h, "maxFav_%dh" % h, "nBars_%dh" % h]
    acc = {"ts": [], "sym": []}
    for h in HOR:
        for k in ("ret", "mfav", "nb"):
            acc["%s_%d" % (k, h)] = []
    acc["madv_72"] = []
    for fp in fs:
        d = FLPB.read_label(fp, usecols=cols)
        d = d[(d["nBars_72h"] >= NEED[72]) & d["retEnd_72h"].notna() & (d.tEpochMs < DEV_CUT)]
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        if not k.any():
            continue
        acc["ts"].append(d.tEpochMs.to_numpy(np.int64)[k])
        acc["sym"].append(sid[k].to_numpy(np.int32))
        for h in HOR:
            acc["ret_%d" % h].append(d["retEnd_%dh" % h].to_numpy(np.float32)[k])
            acc["mfav_%d" % h].append(d["maxFav_%dh" % h].to_numpy(np.float32)[k])
            acc["nb_%d" % h].append(d["nBars_%dh" % h].to_numpy(np.float32)[k])
        acc["madv_72"].append(d["maxAdv_72h"].to_numpy(np.float32)[k])
        del d
    ts = np.concatenate(acc["ts"]); sym = np.concatenate(acc["sym"])
    key = ts * RES + sym.astype(np.int64)
    o = np.argsort(key, kind="stable")
    out = {"key": key[o], "ts": ts[o], "sym": sym[o], "i2s": i2s}
    for kk in acc:
        if kk in ("ts", "sym"):
            continue
        out[kk] = np.concatenate(acc[kk])[o]
    return out


# ───────────────────────── OI (mất thanh khoản) ─────────────────────────

def load_oi_lookup(oi_file, keys, need_syms):
    """Tra (oi_delta24h, oi_z) tại key=ts*1024+sym. OI = 779 block liên tiếp, mỗi sym 1 block;
    chỉ đọc block của sym CÓ trong nhãn (`need_syms`) => nhẹ I/O + RAM."""
    dt = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
    ao = np.memmap(oi_file, dtype=dt, mode="r")
    N = len(ao)
    s = np.asarray(ao["sym"]).astype(np.int32)
    brk = np.flatnonzero(np.diff(s) != 0)
    starts = np.concatenate(([0], brk + 1)); ends = np.concatenate((brk + 1, [N]))
    bsym = s[starts]
    del s, brk
    v1 = np.full(len(keys), np.nan, np.float32)
    v2 = np.full(len(keys), np.nan, np.float32)
    lts = (keys // RES).astype(np.int64)
    lsym = (keys % RES).astype(np.int32)
    ords = np.argsort(lsym, kind="stable")
    lsym_s = lsym[ords]
    for b in range(len(bsym)):
        sv = int(bsym[b])
        if sv not in need_syms:
            continue
        j0 = np.searchsorted(lsym_s, sv, "left"); j1 = np.searchsorted(lsym_s, sv, "right")
        if j1 <= j0:
            continue
        a, e = starts[b], ends[b]
        ta = np.asarray(ao["ts"][a:e]).astype(np.int64)
        idx = ords[j0:j1]
        lo = np.searchsorted(ta, lts[idx], side="left")
        jj = np.flatnonzero(lo < len(ta))
        if len(jj) == 0:
            continue
        eq = ta[lo[jj]] == lts[idx[jj]]
        sel = jj[eq]
        if len(sel) == 0:
            continue
        ov = np.asarray(ao["oi"][a:e])
        v1[idx[sel]] = ov[lo[sel], 0]
        v2[idx[sel]] = ov[lo[sel], 1]
        del ta, ov
    hit = np.isfinite(v1) | np.isfinite(v2)
    return v1, v2, float(hit.mean())


def zcs_per_tick(v, inv, ncell):
    m = np.isfinite(v)
    vv = np.where(m, v, 0.0)
    c = np.bincount(inv, minlength=ncell).astype(np.float64)
    s = np.bincount(inv, weights=vv, minlength=ncell)
    mu = s / np.maximum(c, 1)
    ss = np.bincount(inv, weights=vv * vv, minlength=ncell)
    var = np.maximum(ss / np.maximum(c, 1) - mu * mu, 1e-12)
    sd = np.sqrt(var)
    z = ((v - mu[inv]) / sd[inv]).astype(np.float32)
    z[~m] = np.nan
    return z


def regime_tables(lbl):
    ts, ret = lbl["ts"], lbl["ret_72"].astype(np.float64)
    u, inv = np.unique(ts, return_inverse=True)
    pos = (ret > 0).astype(np.float64)
    c = np.bincount(inv).astype(np.float64)
    bmap = dict(zip(u.tolist(), (np.bincount(inv, weights=pos) / np.maximum(c, 1)).tolist()))
    mmap = dict(zip(u.tolist(), (np.bincount(inv, weights=ret) / np.maximum(c, 1)).tolist()))
    t0 = u - 72 * H
    bb = np.array([bmap.get(int(x), np.nan) for x in t0], dtype=np.float64)
    tb = np.array([mmap.get(int(x), np.nan) for x in t0], dtype=np.float64)
    return {"u": u, "bb": bb, "tb": tb}


def spearman(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 100:
        return float("nan")
    x = pd.Series(np.asarray(a)[m]).rank().to_numpy()
    y = pd.Series(np.asarray(b)[m]).rank().to_numpy()
    return float(np.corrcoef(x, y)[0, 1])


def _c(d):
    return {"mean": round(d["mean"], 6), "raw": [round(d["raw"][0], 6), round(d["raw"][1], 6)],
            "out_raw": d["out_raw"], "out_legacy": d["out_legacy"], "out_both": d["out_both"]}


def _per_tick(v, ts):
    s = pd.Series(v).groupby(pd.Series(ts)).mean()
    return s.to_numpy(), s.index.to_numpy(np.int64)


def _by_year(v, ts):
    o = {}
    yr = pd.to_datetime(pd.Series(ts), unit="ms", utc=True).dt.year.to_numpy()
    v = np.asarray(v)
    for y in (2022, 2023, 2024, 2025):
        m = yr == y
        o[str(y)] = round(float(v[m].mean()), 6) if m.sum() else None
    return o


def _fields(S, T, cols):
    """Lấy các cột nhãn (retEnd/maxFav/maxAdv/nBars) tại horizon T cho MỌI dòng của arm."""
    return [LBL["%s_%d" % (c, T)][S["ip"]] for c in cols]


def eval_cfg(S, back, cfg):
    """cfg: k, T, C, rank='liq', liq (z ngưỡng), f1, n1b, n1a, q3b, regime."""
    k = cfg["k"]; T = cfg["T"]; C = cfg["C"]
    if cfg.get("rank") == "liq":
        comb = S["r"] + S["rliq"]
        o3 = np.lexsort((-comb, S["ts"]))
        ts_s = S["ts"][o3]
        new = np.empty(len(ts_s), bool); new[0] = True
        np.not_equal(ts_s[1:], ts_s[:-1], out=new[1:])
        gid = np.cumsum(new) - 1; firsts = np.flatnonzero(new)
        r_sorted = (np.arange(len(ts_s)) - firsts[gid] + 1)
        sel = np.zeros(len(S["ts"]), bool); sel[o3] = r_sorted <= k
        del o3, ts_s, new, gid, firsts, r_sorted
    else:
        sel = S["r"] > (S["n"] - k)
    ts = S["ts"][sel]
    ret = LBL["ret_%d" % T][S["ip"][sel]]
    mfav = LBL["mfav_%d" % T][S["ip"][sel]]
    nb = LBL["nb_%d" % T][S["ip"][sel]]
    ok = nb >= NEED[T]
    pnl = (-ret if (C is None or not np.isfinite(C)) else np.where(mfav >= C, -C, -ret))
    pnl = np.where(ok, pnl, np.nan)
    f = S["f_%d" % T][sel]
    keep = np.isfinite(pnl)
    if cfg.get("liq") is not None:
        Lv = S["LIQ"][sel]
        keep &= np.isfinite(Lv) & (Lv >= cfg["liq"])
    if cfg.get("f1"):
        v = S["fb"][sel]; keep &= np.isfinite(v) & (v >= 0)
    if cfg.get("n1b"):
        v = S["r1"][sel]; keep &= np.isfinite(v) & (v >= 0)
    if cfg.get("n1a"):
        keep &= S["f_72"][sel] >= 0
    if cfg.get("q3b"):
        v = S["Shist"][sel]; keep &= v >= 0
    if cfg.get("regime"):
        i = np.clip(np.searchsorted(back["u"], ts), 0, len(back["u"]) - 1)
        hit = back["u"][i] == ts
        bb = np.where(hit, back["bb"][i], np.nan)
        keep &= np.isfinite(bb) & (bb <= 0.5)
        if cfg.get("regime") == "both":
            tb = np.where(hit, back["tb"][i], np.nan)
            keep &= np.isfinite(tb) & (tb <= 0.0)
    nsel = int(sel.sum())
    if keep.sum() == 0:
        return {"n_sel": nsel, "n_kept": 0, "kept_frac": 0.0, "err": "no trade"}
    ts_k, pnl_k, f_k = ts[keep], pnl[keep], f[keep]
    m = np.isfinite(f_k)
    ts_k, pnl_k, f_k = ts_k[m], pnl_k[m], f_k[m]
    if len(ts_k) == 0:
        return {"n_sel": nsel, "n_kept": int(keep.sum()), "err": "no funding"}
    pt, pts = _per_tick(pnl_k, ts_k)
    ptf, _ = _per_tick(pnl_k + f_k, ts_k)
    net_pre = SMS.ci_mean(pt - COST, pts)
    net_post = SMS.ci_mean(ptf - COST, pts)
    by_post = _by_year(ptf - COST, pts)
    w = pnl_k - COST + f_k
    yrs = sum(1 for v in by_post.values() if v is not None and v > 0)
    return {"n_sel": nsel, "n_kept": int(keep.sum()), "kept_frac": round(float(keep.mean()), 4),
            "net_pre": _c(net_pre), "net_post": _c(net_post),
            "winrate": round(float((w > 0).mean()), 4),
            "by_year_post": by_post, "yrs_pos_post": yrs,
            "fund_mean": round(float(f_k.mean()), 6),
            "out_both": bool(net_post["out_both"]),
            "B": bool(net_post["out_both"] and yrs >= 3),
            "C": bool((w > 0).mean() >= 0.55)}


def q3a_split(S, C=0.30, T=72, k=8):
    sel = S["r"] > (S["n"] - k)
    ts = S["ts"][sel]
    ret = LBL["ret_%d" % T][S["ip"][sel]]
    mfav = LBL["mfav_%d" % T][S["ip"][sel]]
    nb = LBL["nb_%d" % T][S["ip"][sel]]
    madv = LBL["madv_72"][S["ip"][sel]]
    f = S["f_%d" % T][sel]
    ok = (nb >= NEED[T]) & np.isfinite(ret) & np.isfinite(f)
    ts, ret, mfav, f, madv = ts[ok], ret[ok], mfav[ok], f[ok], madv[ok]
    pnl = np.where(mfav >= C, -C, -ret)
    med = pd.Series(mfav).groupby(pd.Series(ts)).transform("median").to_numpy()
    out = {}
    for nm, ms in (("steady", mfav <= med), ("jerky", mfav > med)):
        if ms.sum() == 0:
            continue
        pt, pts = _per_tick((pnl - COST + f)[ms], ts[ms])
        c = SMS.ci_mean(pt, pts)
        rt = np.where(np.abs(madv[ms]) > 1e-9, madv[ms], np.nan)
        out[nm] = {"n": int(ms.sum()), "net_post": _c(c),
                   "winrate": round(float((pnl[ms] - COST + f[ms] > 0).mean()), 4),
                   "bounce_mean": round(float(mfav[ms].mean()), 5),
                   "retain_mean": round(float(np.nanmean(ret[ms] / rt)), 4),
                   "fund_mean": round(float(f[ms].mean()), 6)}
    return out


def liq_decile(S, C=0.30, T=72, k=8):
    sel = S["r"] > (S["n"] - k)
    ts = S["ts"][sel]
    ret = LBL["ret_%d" % T][S["ip"][sel]]
    mfav = LBL["mfav_%d" % T][S["ip"][sel]]
    nb = LBL["nb_%d" % T][S["ip"][sel]]
    Lv = S["LIQ"][sel]
    ok = (nb >= NEED[T]) & np.isfinite(ret) & np.isfinite(Lv)
    ts, ret, mfav, Lv = ts[ok], ret[ok], mfav[ok], Lv[ok]
    pnl = np.where(mfav >= C, -C, -ret)
    q = pd.qcut(pd.Series(Lv), 10, labels=False, duplicates="drop").to_numpy()
    out = []
    for d in range(int(np.nanmax(q)) + 1):
        m = (q == d)
        if m.sum() == 0:
            continue
        pt, pts = _per_tick((pnl - COST)[m], ts[m])
        out.append({"d": int(d), "n": int(m.sum()), "liq_mean": round(float(Lv[m].mean()), 3),
                    "ret_mean": round(float(-ret[m].mean()), 5), "net_pre": round(float(pt.mean()), 5)})
    return out


CONFIGS = [
    ("base_k8_T72_C30", dict(k=8, C=0.30, T=72)),
    ("base_k8_T72_C20", dict(k=8, C=0.20, T=72)),
    ("base_k8_T72_nocut", dict(k=8, C=None, T=72)),
    ("hold_k8_T4_C30", dict(k=8, C=0.30, T=4)),
    ("hold_k8_T12_C30", dict(k=8, C=0.30, T=12)),
    ("hold_k8_T24_C30", dict(k=8, C=0.30, T=24)),
    ("X1_liq050_k8_T72_C30", dict(k=8, C=0.30, T=72, liq=0.5)),
    ("X1_liq100_k8_T72_C30", dict(k=8, C=0.30, T=72, liq=1.0)),
    ("X2_liqrank_k3_T72_C30", dict(k=3, C=0.30, T=72, rank="liq")),
    ("X2_liqrank_k1_T72_C30", dict(k=1, C=0.30, T=72, rank="liq")),
    ("Q3b_steady_k8_T72_C30", dict(k=8, C=0.30, T=72, q3b=True)),
    ("F1_k8_T72_C30", dict(k=8, C=0.30, T=72, f1=True)),
    ("F1_liq100_k8_T72_C30", dict(k=8, C=0.30, T=72, f1=True, liq=1.0)),
    ("N1b_k8_T72_C30", dict(k=8, C=0.30, T=72, n1b=True)),
    ("N1a_k8_T72_C30", dict(k=8, C=0.30, T=72, n1a=True)),
    ("F1_k3_T72_C30", dict(k=3, C=0.30, T=72, f1=True)),
    ("F1_Q3b_k8_T72_C30", dict(k=8, C=0.30, T=72, f1=True, q3b=True)),
]


def main():
    global LBL
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins-root", required=True)
    ap.add_argument("--arms", default="SHORT42,SHORT7,SHORT13")
    ap.add_argument("--labels-dir", required=True)
    ap.add_argument("--map-csv", required=True)
    ap.add_argument("--fund-cache", required=True)
    ap.add_argument("--oi-file", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    t0 = time.time()
    lbl = load_labels(a.labels_dir, a.map_csv)
    LBL = lbl
    print("### nhãn %d dòng (%.1f p)" % (len(lbl["key"]), (time.time() - t0) / 60), flush=True)

    need_syms = set(np.unique(lbl["sym"]).tolist())
    d_oi, z_oi, hitr = load_oi_lookup(a.oi_file, lbl["key"], need_syms)
    print("### OI khớp %.3f (%.1f p)" % (hitr, (time.time() - t0) / 60), flush=True)
    u, inv = np.unique(lbl["ts"], return_inverse=True)
    del u
    zd = zcs_per_tick(-d_oi, inv, int(inv.max()) + 1)
    zz = zcs_per_tick(-z_oi, inv, int(inv.max()) + 1)
    del d_oi, z_oi
    LIQ = 0.5 * np.nan_to_num(zd) + 0.5 * np.nan_to_num(zz)
    LIQ[~np.isfinite(zd) & ~np.isfinite(zz)] = np.nan
    LIQ = LIQ.astype(np.float32)
    del zd, zz

    key_hist = (lbl["ts"] - 72 * H) * RES + lbl["sym"].astype(np.int64)
    ip = np.clip(np.searchsorted(lbl["key"], key_hist), 0, len(lbl["key"]) - 1)
    hh = lbl["key"][ip] == key_hist
    bh = np.where(hh, lbl["mfav_72"][ip], np.nan).astype(np.float32)
    del key_hist, ip, hh
    Shist = zcs_per_tick(-bh, inv, int(inv.max()) + 1)
    Shist = np.nan_to_num(Shist, nan=-99.0).astype(np.float32)
    del bh, inv
    fund = Fund(a.fund_cache)
    back = regime_tables(lbl)
    gc.collect()
    print("### regime+LIQ+Shist xong (%.1f p)" % ((time.time() - t0) / 60), flush=True)

    ic_liq = spearman(LIQ, -lbl["ret_72"].astype(np.float64))
    ic_sh = spearman(Shist, -lbl["ret_72"].astype(np.float64))
    print("### IC(LIQ,-ret72)=%.4f  IC(Shist,-ret72)=%.4f" % (ic_liq, ic_sh), flush=True)

    res = {"cost": COST, "cost_stress": COST_STRESS, "n_label": int(len(lbl["key"])),
           "oi_hit": round(hitr, 4), "ic_liq": round(ic_liq, 5), "ic_shist": round(ic_sh, 5),
           "configs": [c[0] for c in CONFIGS], "arms": {}}
    for arm in [x.strip() for x in a.arms.split(",") if x.strip()]:
        dirp = os.path.join(a.bins_root, arm)
        files = [os.path.join(dirp, "predict_wf_%s.bin" % f) for f in FOLDS]
        files = [f for f in files if os.path.exists(f)]
        if not files:
            print("### arm %s: KHONG co bins" % arm, flush=True)
            continue
        ts, sym, p = SMS.read_bins(files)
        key = ts * RES + sym.astype(np.int64)
        ip_ = np.clip(np.searchsorted(lbl["key"], key), 0, len(lbl["key"]) - 1)
        hh = lbl["key"][ip_] == key
        del key
        ts, sym, p, ip_ = ts[hh], sym[hh], p[hh], ip_[hh]
        ok = np.isfinite(p)
        ts, sym, p, ip_ = ts[ok], sym[ok], p[ok], ip_[ok]
        del ok, hh
        o = np.argsort(ts, kind="stable")
        ts, sym, p, ip_ = ts[o], sym[o], p[o], ip_[o]
        del o
        o2 = np.lexsort((p, ts)); ts_s = ts[o2]
        new = np.empty(len(ts_s), bool); new[0] = True
        np.not_equal(ts_s[1:], ts_s[:-1], out=new[1:])
        gid = np.cumsum(new) - 1; firsts = np.flatnonzero(new)
        sizes = np.diff(np.append(firsts, len(ts_s)))
        r_sorted = (np.arange(len(ts_s)) - firsts[gid] + 1).astype(np.float64)
        r_arr = np.empty(len(ts_s)); r_arr[o2] = r_sorted
        n_arr = sizes[gid].astype(np.int64)
        del o2, ts_s, new, gid, firsts, sizes, r_sorted
        Lr = np.nan_to_num(LIQ[ip_].astype(np.float64), nan=-1e9)
        o3 = np.lexsort((Lr, ts)); ts2 = ts[o3]
        nw = np.empty(len(ts2), bool); nw[0] = True
        np.not_equal(ts2[1:], ts2[:-1], out=nw[1:])
        g3 = np.cumsum(nw) - 1; f3 = np.flatnonzero(nw)
        rs = (np.arange(len(ts2)) - f3[g3] + 1).astype(np.float64)
        rliq = np.empty(len(ts2)); rliq[o3] = rs
        del Lr, o3, ts2, nw, g3, f3, rs
        fsid_map = np.full(RES, -1, dtype=np.int32)
        for sid, nm in lbl["i2s"].items():
            if nm in fund.s2i:
                fsid_map[int(sid) % RES] = fund.s2i[nm]
        fsid = fsid_map[sym.astype(np.int64)]
        _f, _r1, _gap, _fb = fund.compute(fsid, ts)
        S = {"ts": ts, "p": p, "n": n_arr, "r": r_arr, "rliq": rliq, "ip": ip_,
             "LIQ": LIQ[ip_], "Shist": Shist[ip_], "r1": _r1, "gap": _gap, "fb": _fb}
        for h in HOR:
            S["f_%d" % h] = _f[h]
        del _f, _r1, _gap, _fb, fsid, fsid_map
        gc.collect()
        print("### arm %s rows=%d (%.1f p)" % (arm, len(ts), (time.time() - t0) / 60), flush=True)
        ar = {"n_rows": int(len(ts))}
        ar["ic_score"] = round(spearman(S["p"], -LBL["ret_72"][ip_]), 5)
        ar["ic_liq"] = round(spearman(S["LIQ"], -LBL["ret_72"][ip_]), 5)
        ar["ic_fb_actual"] = round(spearman(S["fb"], S["f_72"]), 5)
        ar["cut_rate_C30"] = round(float((LBL["mfav_72"][ip_] >= 0.30).mean()), 4)
        for name, cfg in CONFIGS:
            ar[name] = eval_cfg(S, back, cfg)
            r = ar[name]
            print("%-24s kept=%.3f net_pre=%+.5f net_post=%+.5f win=%.3f yrs+=%s" % (
                name, r.get("kept_frac", -1), r.get("net_pre", {}).get("mean", float("nan")),
                r.get("net_post", {}).get("mean", float("nan")), r.get("winrate", float("nan")),
                r.get("yrs_pos_post")), flush=True)
        ar["q3a"] = q3a_split(S)
        print("Q3a:", json.dumps(ar["q3a"], default=str)[:400], flush=True)
        ar["liq_decile"] = liq_decile(S)
        print("LIQdec:", json.dumps(ar["liq_decile"], default=str)[:400], flush=True)
        res["arms"][arm] = ar
        json.dump(res, open(a.out, "w"), indent=1, default=str)
        del S, ts, sym, p, ip_, n_arr, r_arr, rliq
        gc.collect()
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("### JSON -> %s (%.1f p)" % (a.out, (time.time() - t0) / 60))


if __name__ == "__main__":
    main()
