#!/usr/bin/env python3
"""short_v4_score.py — CHẤM 0-sim cho PREREG_SHORT_V4.

Đo NGUYÊN các mục khoá ở `docs/prereg/PREREG_SHORT_V4.md`:
  §2  LIQ (mất thanh khoản) từ OI: LIQ = 0,5*z_CS(-oi_delta24h) + 0,5*z_CS(-oi_z)   [gate X1 / ranker X2]
  §3  giữ đủ lâu T=72h  vs  giữ ngắn T=4/12/24h
  §4  độ đều nhịp giảm: Q3a ex-post (bounce=maxFav_72h) + Q3b causal (S_hist từ t-72h)
  §5  funding: F1 dự báo CẢ cửa sổ (Fh=9*mean 8 settle trước t) vs N1b (1 settle) / N1a (lookahead)
  §6  chỉ số + CI block-72h (NREP=2000, SEED=20260905, ×1,21), k=3 seed {42,7,13}

KHÔNG train, KHÔNG sim, KHÔNG chạm .java. DEV <= 2025-12-31.
Quy ước funding: rate > 0 => long TRA / SHORT NHAN. f_h(t,sym)=sum rate trong (t, t+h].
"""
import argparse
import glob
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
LBL_COLS = ["tEpochMs", "symbol"]
for h in HOR:
    LBL_COLS += ["retEnd_%dh" % h, "maxFav_%dh" % h, "maxAdv_%dh" % h, "nBars_%dh" % h]


# ───────────────────────── funding (Aerospike cache) ─────────────────────────

class Fund:
    """Như V3 + thêm Fh = 9*mean(8 settle gần nhất TRƯỚC t) = dự báo funding CẢ cửa sổ 72h."""

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
        f = {h: np.full(n, np.nan) for h in HOR}
        r1 = np.full(n, np.nan); gap = np.full(n, np.nan); fb = np.full(n, np.nan)
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
                f[h][idx] = ca[hi] - ca[lo]
            ok = lo < len(ta)
            v = r1[idx]; v[ok] = ra[lo[ok]]; r1[idx] = v
            g = gap[idx]; g[ok] = ta[lo[ok]] - tt[ok]; gap[idx] = g
            # Fh: mean 8 settle TRƯỚC t (lo-1 .. lo-8) * 9 settle/72h
            fv = fb[idx]
            ok8 = lo >= 1
            if ok8.any():
                j = np.flatnonzero(ok8); li = lo[j]
                cs = ca  # cumsum(ra) với ca[k]=sum ra[:k]; ca[lo]-ca[lo-8]=sum 8 settle trước
                lo8 = np.maximum(li - 8, 0)
                cnt = li - lo8
                s8 = ca[li] - ca[lo8]
                fv[j] = 9.0 * (s8 / np.maximum(cnt, 1))
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
    acc = {"ts": [], "sym": []}
    for h in HOR:
        for k in ("ret", "mfav", "madv", "nb"):
            acc["%s_%d" % (k, h)] = []
    for fp in fs:
        d = FLPB.read_label(fp, usecols=LBL_COLS)
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
            acc["madv_%d" % h].append(d["maxAdv_%dh" % h].to_numpy(np.float32)[k])
            acc["nb_%d" % h].append(d["nBars_%dh" % h].to_numpy(np.float32)[k])
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

def load_oi_lookup(oi_file, keys):
    """Tra (oi_delta24h, oi_z) tại key=ts*1024+sym cho mảng `keys` (đã sort). Trả 2 mảng float32."""
    dt = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
    ao = np.memmap(oi_file, dtype=dt, mode="r")
    N = len(ao)
    k = np.empty(N, np.int64)
    d1 = np.empty(N, np.float32); d2 = np.empty(N, np.float32)
    CH = 8_000_000
    for c in range(0, N, CH):
        e = min(c + CH, N)
        blk = np.asarray(ao["ts"][c:e]).astype(np.int64) * RES + np.asarray(ao["sym"][c:e]).astype(np.int64)
        k[c:e] = blk
        oi = np.asarray(ao["oi"][c:e])
        d1[c:e] = oi[:, 0]; d2[c:e] = oi[:, 1]
    o = np.argsort(k, kind="stable")
    ks = k[o]; d1 = d1[o]; d2 = d2[o]
    del k, o
    ip = np.clip(np.searchsorted(ks, keys), 0, len(ks) - 1)
    hit = ks[ip] == keys
    v1 = np.where(hit, d1[ip], np.nan).astype(np.float32)
    v2 = np.where(hit, d2[ip], np.nan).astype(np.float32)
    return v1, v2, float(hit.mean())


def zcs_per_tick(v, inv, ncell):
    """z-score cross-section trong tick: (v - mean_t)/std_t. NaN giữ NaN."""
    m = np.isfinite(v)
    vv = np.where(m, v, 0.0)
    c = np.bincount(inv, minlength=ncell).astype(np.float64)
    s = np.bincount(inv, weights=vv, minlength=ncell)
    mu = s / np.maximum(c, 1)
    ss = np.bincount(inv, weights=vv * vv, minlength=ncell)
    var = np.maximum(ss / np.maximum(c, 1) - mu * mu, 1e-12)
    sd = np.sqrt(var)
    z = (v - mu[inv]) / sd[inv]
    return z.astype(np.float32)


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
    x = pd.Series(a[m]).rank().to_numpy()
    y = pd.Series(b[m]).rank().to_numpy()
    return float(np.corrcoef(x, y)[0, 1])


# ───────────────────────── chấm 1 cấu hình ─────────────────────────

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


def liq_decile(S, C=0.30, T=72, k=8):
    """Q1 phụ trợ: decile theo LIQ (trên lệnh K8/T72) -> mean retEnd + net (chưa credit funding)."""
    sel = S["r"] > (S["n"] - k)
    ts = S["ts"][sel]; ret = S["ret_%d" % T][sel]; mfav = S["mfav_%d" % T][sel]
    nb = S["nb_%d" % T][sel]; L = S["LIQ"][sel]
    ok = (nb >= NEED[T]) & np.isfinite(ret) & np.isfinite(L)
    ts, ret, mfav, L = ts[ok], ret[ok], mfav[ok], L[ok]
    pnl = np.where(mfav >= C, -C, -ret)
    q = pd.qcut(pd.Series(L), 10, labels=False, duplicates="drop")
    out = []
    for d in range(int(np.nanmax(q.to_numpy())) + 1):
        m = (q.to_numpy() == d)
        if m.sum() == 0:
            continue
        pt, pts = _per_tick((pnl - COST)[m], ts[m])
        out.append({"d": int(d), "n": int(m.sum()), "liq_mean": round(float(L[m].mean()), 3),
                    "ret_mean": round(float(-ret[m].mean()), 5),
                    "net_pre": round(float(pt.mean()), 5)})
    return out


def eval_cfg(S, back, cfg):
    """cfg: k, T, C, liq (None|('>=',Q)|'rank'), f1 (bool), n1b, n1a, q3a ('bounce'|'retain'), q3b (bool), regime"""
    k = cfg["k"]; T = cfg["T"]; C = cfg["C"]
    if cfg.get("rank") == "liq":
        # tổ hợp hạng trong tick: rank(score) + rank(LIQ); lấy top-k (giảm dần)
        comb = S["r"] + S["rliq"]
        o3 = np.lexsort((-comb, S["ts"]))
        ts_s = S["ts"][o3]
        new = np.empty(len(ts_s), bool); new[0] = True
        np.not_equal(ts_s[1:], ts_s[:-1], out=new[1:])
        gid = np.cumsum(new) - 1; firsts = np.flatnonzero(new)
        sizes = np.diff(np.append(firsts, len(ts_s)))
        r_sorted = (np.arange(len(ts_s)) - firsts[gid] + 1)
        sel = np.zeros(len(S["ts"]), bool); sel[o3] = r_sorted <= k
    else:
        sel = S["r"] > (S["n"] - k)
    ts = S["ts"][sel]
    ret = S["ret_%d" % T][sel]; mfav = S["mfav_%d" % T][sel]
    madv = S["madv_%d" % T][sel]; nb = S["nb_%d" % T][sel]
    ok = nb >= NEED[T]
    if C is None or not np.isfinite(C):
        pnl = -ret
    else:
        pnl = np.where(mfav >= C, -C, -ret)
    pnl = np.where(ok, pnl, np.nan)
    f = S["f_%d" % T][sel]
    keep = np.isfinite(pnl)
    if cfg.get("liq") is not None:
        L = S["LIQ"][sel]
        keep &= np.isfinite(L) & (L >= cfg["liq"])
    if cfg.get("f1"):
        fb = S["fb"][sel]
        keep &= np.isfinite(fb) & (fb >= 0)
    if cfg.get("n1b"):
        r1 = S["r1"][sel]
        keep &= np.isfinite(r1) & (r1 >= 0)
    if cfg.get("n1a"):
        keep &= S["f_72"][sel] >= 0
    if cfg.get("q3b"):
        sh = S["Shist"][sel]
        keep &= np.isfinite(sh) & (sh >= 0)  # Shist đã chuẩn hoá: >=0 = đều hơn trung vị
    if cfg.get("regime"):
        i = np.clip(np.searchsorted(back["u"], ts), 0, len(back["u"]) - 1)
        hit = back["u"][i] == ts
        bb = np.where(hit, back["bb"][i], np.nan); tb = np.where(hit, back["tb"][i], np.nan)
        keep &= np.isfinite(bb) & (bb <= 0.5)
        if cfg.get("regime") == "both":
            keep &= np.isfinite(tb) & (tb <= 0.0)
    nsel = int(sel.sum())
    if keep.sum() == 0:
        return {"n_sel": nsel, "n_kept": 0, "kept_frac": 0.0, "err": "no trade"}
    ts_k, pnl_k, f_k = ts[keep], pnl[keep], f[keep]
    mask = np.isfinite(f_k)
    ts_k, pnl_k, f_k = ts_k[mask], pnl_k[mask], f_k[mask]
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
            "C": bool((w > 0).mean() >= 0.55),
            "pnl_mean": round(float(pnl_k.mean()), 6)}


def q3a_split(S, C=0.30, T=72, k=8):
    """Q3a ex-post: chia lệnh K8/tick theo bounce=maxFav_72h (<= median tick = đều)."""
    sel = S["r"] > (S["n"] - k)
    ts = S["ts"][sel]; ret = S["ret_%d" % T][sel]; mfav = S["mfav_%d" % T][sel]
    nb = S["nb_%d" % T][sel]; f = S["f_%d" % T][sel]
    ok = (nb >= NEED[T]) & np.isfinite(ret) & np.isfinite(f)
    ts, ret, mfav, f = ts[ok], ret[ok], mfav[ok], f[ok]
    pnl = np.where(mfav >= C, -C, -ret)
    # median bounce per-tick
    df = pd.DataFrame({"ts": ts, "b": mfav})
    med = df.groupby("ts")["b"].transform("median").to_numpy()
    steady = mfav <= med
    out = {}
    for nm, ms in (("steady", steady), ("jerky", ~steady)):
        if ms.sum() == 0:
            continue
        pt, pts = _per_tick((pnl - COST + f)[ms], ts[ms])
        c = SMS.ci_mean(pt, pts)
        out[nm] = {"n": int(ms.sum()), "net_post": _c(c), "winrate": round(float((pnl[ms] - COST + f[ms] > 0).mean()), 4),
                   "bounce_mean": round(float(mfav[ms].mean()), 5),
                   "fund_mean": round(float(f[ms].mean()), 6)}
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins-root", required=True)
    ap.add_argument("--arms", default="SHORT42,SHORT7,SHORT13")
    ap.add_argument("--labels-dir", required=True)
    ap.add_argument("--map-csv", required=True)
    ap.add_argument("--fund-cache", required=True)
    ap.add_argument("--oi-file", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-arms", type=int, default=0)
    a = ap.parse_args()

    t0 = time.time()
    lbl = load_labels(a.labels_dir, a.map_csv)
    print("### nhãn %d dòng (%.1f p)" % (len(lbl["key"]), (time.time() - t0) / 60), flush=True)

    # --- LIQ từ OI (tra theo key nhãn) ---
    d_oi, z_oi, hitr = load_oi_lookup(a.oi_file, lbl["key"])
    print("### OI khớp %.3f (%.1f p)" % (hitr, (time.time() - t0) / 60), flush=True)
    u, inv = np.unique(lbl["ts"], return_inverse=True)
    z_d = zcs_per_tick(-d_oi, inv, len(u))       # z_CS(-oi_delta24h)
    z_z = zcs_per_tick(-z_oi, inv, len(u))       # z_CS(-oi_z)
    LIQ = (0.5 * np.nan_to_num(z_d) + 0.5 * np.nan_to_num(z_z)).astype(np.float32)
    LIQ[~np.isfinite(z_d) & ~np.isfinite(z_z)] = np.nan
    del d_oi, z_oi, z_d, z_z

    # --- S_hist causal: độ đều của path QUÁ KHỨ tại t-72h (bounce_hist) ---
    key_hist = (lbl["ts"] - 72 * H) * RES + lbl["sym"].astype(np.int64)
    ip = np.clip(np.searchsorted(lbl["key"], key_hist), 0, len(lbl["key"]) - 1)
    hh = lbl["key"][ip] == key_hist
    bh = np.where(hh, lbl["mfav_72"][ip], np.nan).astype(np.float32)
    # chuẩn hoá cross-section: Shist = z_CS(-bounce_hist)  (>=0 = ít nhúng lên = đều hơn)
    Shist = zcs_per_tick(-bh, inv, len(u))
    Shist = np.nan_to_num(Shist, nan=-99.0).astype(np.float32)
    del key_hist, ip, hh, bh

    fund = Fund(a.fund_cache)
    back = regime_tables(lbl)
    print("### regime+LIQ+Shist xong (%.1f p)" % ((time.time() - t0) / 60), flush=True)

    # IC toàn cục (trên panel nhãn) — LIQ & Shist vs -ret_72
    ic_liq = spearman(LIQ, -lbl["ret_72"].astype(np.float64))
    ic_sh = spearman(Shist, -lbl["ret_72"].astype(np.float64))
    print("### IC(LIQ,-ret72)=%.4f  IC(Shist,-ret72)=%.4f" % (ic_liq, ic_sh), flush=True)

    res = {"cost": COST, "cost_stress": COST_STRESS, "n_label": int(len(lbl["key"])),
           "oi_hit": round(hitr, 4), "ic_liq": round(ic_liq, 5), "ic_shist": round(ic_sh, 5),
           "configs": [c[0] for c in CONFIGS], "arms": {}}
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    if a.max_arms:
        arms = arms[:a.max_arms]
    for arm in arms:
        dirp = os.path.join(a.bins_root, arm)
        files = [os.path.join(dirp, "predict_wf_%s.bin" % f) for f in FOLDS]
        files = [f for f in files if os.path.exists(f)]
        if not files:
            print("### arm %s: KHONG co bins" % arm, flush=True)
            continue
        ts, sym, p = SMS.read_bins(files)
        key = ts * RES + sym.astype(np.int64)
        ip = np.clip(np.searchsorted(lbl["key"], key), 0, len(lbl["key"]) - 1)
        hh = lbl["key"][ip] == key
        ts, sym, p, ip = ts[hh], sym[hh], p[hh], ip[hh]
        ok = np.isfinite(p)
        ts, sym, p, ip = ts[ok], sym[ok], p[ok], ip[ok]
        o = np.argsort(ts, kind="stable")
        ts, sym, p, ip = ts[o], sym[o], p[o], ip[o]
        o2 = np.lexsort((p, ts)); ts_s = ts[o2]
        new = np.empty(len(ts_s), bool); new[0] = True
        np.not_equal(ts_s[1:], ts_s[:-1], out=new[1:])
        gid = np.cumsum(new) - 1; firsts = np.flatnonzero(new)
        sizes = np.diff(np.append(firsts, len(ts_s)))
        r_sorted = (np.arange(len(ts_s)) - firsts[gid] + 1).astype(np.float64)
        r_arr = np.empty(len(ts_s)); r_arr[o2] = r_sorted
        n_arr = sizes[gid].astype(np.int64)
        del o2, ts_s, new, gid, firsts, sizes, r_sorted
        fsid_map = np.full(RES, -1, dtype=np.int32)
        for sid, nm in lbl["i2s"].items():
            if nm in fund.s2i:
                fsid_map[int(sid) % RES] = fund.s2i[nm]
        fsid = fsid_map[sym.astype(np.int64)]
        _f, _r1, _gap, _fb = fund.compute(fsid, ts)
        _Lr = np.nan_to_num(LIQ[ip].astype(np.float64), nan=-1e9)
        _o = np.lexsort((_Lr, ts)); _ts2 = ts[_o]
        _nw = np.empty(len(_ts2), bool); _nw[0] = True
        np.not_equal(_ts2[1:], _ts2[:-1], out=_nw[1:])
        _g = np.cumsum(_nw) - 1; _f = np.flatnonzero(_nw)
        _rs = (np.arange(len(_ts2)) - _f[_g] + 1).astype(np.float64)
        _rl = np.empty(len(_ts2)); _rl[_o] = _rs
        del _Lr, _o, _ts2, _nw, _g, _f, _rs
        S = {"ts": ts, "p": p, "n": n_arr, "r": r_arr, "rliq": _rl, "LIQ": LIQ[ip],
             "Shist": Shist[ip], "r1": _r1, "gap": _gap, "fb": _fb, "i2s": lbl["i2s"]}
        for h in HOR:
            S["ret_%d" % h] = lbl["ret_%d" % h][ip].astype(np.float64)
            S["mfav_%d" % h] = lbl["mfav_%d" % h][ip].astype(np.float64)
            S["madv_%d" % h] = lbl["madv_%d" % h][ip].astype(np.float64)
            S["nb_%d" % h] = lbl["nb_%d" % h][ip].astype(np.float64)
            S["f_%d" % h] = _f[h]
        print("### arm %s rows=%d (%.1f p)" % (arm, len(ts), (time.time() - t0) / 60), flush=True)
        ar = {"n_rows": int(len(ts))}
        ar["ic_score"] = round(spearman(S["p"], -S["ret_72"]), 5)
        ar["ic_liq"] = round(spearman(S["LIQ"], -S["ret_72"]), 5)
        ar["ic_fb_actual"] = round(spearman(S["fb"], S["f_72"]), 5)
        ar["cut_rate_C30"] = round(float((S["mfav_72"] >= 0.30).mean()), 4)
        for name, cfg in CONFIGS:
            ar[name] = eval_cfg(S, back, cfg)
            r = ar[name]
            print("%-24s kept=%.3f net_pre=%+.5f net_post=%+.5f win=%.3f yrs+=%s" % (
                name, r.get("kept_frac", -1), r.get("net_pre", {}).get("mean", float("nan")),
                r.get("net_post", {}).get("mean", float("nan")), r.get("winrate", float("nan")),
                r.get("yrs_pos_post")), flush=True)
        ar["q3a"] = q3a_split(S)
        print("Q3a steady/jerky:", json.dumps(ar["q3a"], default=str)[:300], flush=True)
        ar["liq_decile"] = liq_decile(S)
        print("LIQ decile net:", json.dumps(ar["liq_decile"], default=str)[:400], flush=True)
        # decile theo LIQ (all rows, T72 C30, K8 gốc không gate) — báo net theo decile LIQ
        res["arms"][arm] = ar
        del S
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("### JSON -> %s (%.1f p)" % (a.out, (time.time() - t0) / 60))


if __name__ == "__main__":
    main()
