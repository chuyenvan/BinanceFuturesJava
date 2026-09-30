#!/usr/bin/env python3
"""short_v3_score.py — CHẤM 0-sim cho PREREG_SHORT_V3 (NỀ FUNDING + TĂNG WINRATE).

Đọc bins SHORT (nhãn ndown, 3 seed) của `sm-train-gpu` + nhãn `.pb` (4/12/24/72h) + funding
cache Aerospike (`fund_cache.npz`, exact) rồi đo NGUYÊN các mục đã khoá ở
`docs/prereg/PREREG_SHORT_V3.md` §2 (N1a/N1b/N2a/N2b) · §3 (P1/P2/P3) · §5 (chỉ số/CI).

KHÔNG train, KHÔNG sim, KHÔNG chạm .java. DEV ≤ 2025-12-31.
Quy ước funding: rate > 0 ⇒ long TRẢ / SHORT NHẬN. f_h(t,sym)=Σ rate trong (t, t+h].
pnl_short có funding = (-retEnd_h [đã cắt]) + f_h.
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
COLS = ["tEpochMs", "symbol"]
for h in HOR:
    COLS += ["retEnd_%dh" % h, "maxFav_%dh" % h, "nBars_%dh" % h]


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
        """Tất cả đại lượng funding cần cho 1 arm, 1 lượt (nhóm theo coin, không mask toàn mảng).
        Trả (f, r1, gap): f = dict h->mảng; r1 = rate settle kế tiếp; gap = ms tới settle kế tiếp.
        Hàng không có dữ liệu funding => NaN."""
        n = len(t)
        f = {h: np.full(n, np.nan) for h in (4, 12, 24, 72)}
        r1 = np.full(n, np.nan)
        gap = np.full(n, np.nan)
        o = np.argsort(fsid, kind="stable")
        fs = fsid[o]
        tt_all = t[o]
        b = np.searchsorted(fs, np.arange(len(self.syms) + 1))
        for s in range(len(self.syms)):
            i0, i1 = b[s], b[s + 1]
            if i1 == i0:
                continue
            a, bb = self.bounds[s], self.bounds[s + 1]
            if bb <= a:
                continue
            idx = o[i0:i1]
            tt = tt_all[i0:i1]
            ta, ca, ra = self.ts[a:bb], self.cum[a:bb + 1], self.rt[a:bb]
            lo = np.searchsorted(ta, tt, side="right")
            for h in (4, 12, 24, 72):
                hi = np.searchsorted(ta, tt + h * H, side="right")
                f[h][idx] = ca[hi] - ca[lo]
            ok = lo < len(ta)
            v = r1[idx]; v[ok] = ra[lo[ok]]; r1[idx] = v
            g = gap[idx]; g[ok] = ta[lo[ok]] - tt[ok]; gap[idx] = g
        return f, r1, gap


# ───────────────────────── nhãn ─────────────────────────

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
        acc["ret_%d" % h] = []; acc["mfav_%d" % h] = []; acc["nb_%d" % h] = []
    for fp in fs:
        d = FLPB.read_label(fp, usecols=COLS)
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
    ts = np.concatenate(acc["ts"]); sym = np.concatenate(acc["sym"])
    key = ts * RES + sym.astype(np.int64)
    o = np.argsort(key, kind="stable")
    out = {"key": key[o], "ts": ts[o], "sym": sym[o], "i2s": i2s}
    for kk in list(acc):
        if kk in ("ts", "sym"):
            continue
        out[kk] = np.concatenate(acc[kk])[o]
    return out


def regime_tables(lbl, btc_name):
    """Backward (KHÔNG lookahead) tại t−72h: breadth(t−72h) + lợi suất thị trường EW.
    LƯU Ý: "BTCUSDT" KHÔNG có trong universe nhãn ⇒ thay chân BTC bằng lợi suất EW
    (deviation do thiếu dữ liệu, chỉ dùng phụ trợ — xem RESULT §deviation)."""
    ts, sym, ret = lbl["ts"], lbl["sym"], lbl["ret_72"].astype(np.float64)
    u, inv = np.unique(ts, return_inverse=True)
    pos = (ret > 0).astype(np.float64)
    c = np.bincount(inv).astype(np.float64)
    bmap = dict(zip(u.tolist(), (np.bincount(inv, weights=pos) / np.maximum(c, 1)).tolist()))
    mmap = dict(zip(u.tolist(), (np.bincount(inv, weights=ret) / np.maximum(c, 1)).tolist()))
    t0 = u - 72 * H
    bb = np.array([bmap.get(int(x), np.nan) for x in t0], dtype=np.float64)
    mb = np.array([mmap.get(int(x), np.nan) for x in t0], dtype=np.float64)
    return {"u": u, "bb": bb, "tb": mb}


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


def eval_cfg(S, back, cfg):
    k = cfg["k"]; T = cfg["T"]; C = cfg["C"]
    sel = S["r"] > (S["n"] - k)
    ts = S["ts"][sel]
    ret = S["ret_%d" % T][sel]; mfav = S["mfav_%d" % T][sel]; nb = S["nb_%d" % T][sel]
    ok = nb >= NEED[T]
    if C is None or not np.isfinite(C):
        pnl = -ret
    else:
        pnl = np.where(mfav >= C, -C, -ret)
    pnl = np.where(ok, pnl, np.nan)
    f = S["f_%d" % T][sel]
    keep = np.isfinite(pnl)
    filt = cfg.get("filt")
    if filt == "n1a":
        keep &= S["f_72"][sel] >= 0
    elif filt == "n1b":
        r1 = S["r1"][sel]
        keep &= np.isfinite(r1) & (r1 >= 0)
    elif filt == "n2b":
        g = S["gap"][sel]
        keep &= np.isfinite(g) & (g > T * H)
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
    pt, pts = _per_tick(pnl_k, ts_k)
    ptf, _ = _per_tick(pnl_k + f_k, ts_k)
    net_pre = SMS.ci_mean(pt - COST, pts)
    net_post = SMS.ci_mean(ptf - COST, pts)
    net_stress = SMS.ci_mean(ptf - COST_STRESS, pts)
    by_pre = _by_year(pt - COST, pts)
    by_post = _by_year(ptf - COST, pts)
    w = pnl_k - COST + f_k
    yrs = sum(1 for v in by_post.values() if v is not None and v > 0)
    return {"n_sel": nsel, "n_kept": int(keep.sum()), "kept_frac": round(float(keep.mean()), 4),
            "net_pre": _c(net_pre), "net_post": _c(net_post), "net_post_stress": _c(net_stress),
            "winrate": round(float((w > 0).mean()), 4),
            "winrate_pre": round(float(((pnl_k - COST) > 0).mean()), 4),
            "by_year_pre": by_pre, "by_year_post": by_post, "yrs_pos_post": yrs,
            "fund_mean": round(float(f_k.mean()), 6),
            "out_both": bool(net_post["out_both"]),
            "B": bool(net_post["out_both"] and yrs >= 3),
            "C": bool((w > 0).mean() >= 0.55)}


CONFIGS = [
    ("base_k8_T72_C30", dict(k=8, C=0.30, T=72)),
    ("base_k8_T72_C20", dict(k=8, C=0.20, T=72)),
    ("base_k8_T72_C50", dict(k=8, C=0.50, T=72)),
    ("base_k8_T72_nocut", dict(k=8, C=None, T=72)),
    ("N1a_k8_T72_C30", dict(k=8, C=0.30, T=72, filt="n1a")),
    ("N1b_k8_T72_C30", dict(k=8, C=0.30, T=72, filt="n1b")),
    ("N1a_k8_T72_C50", dict(k=8, C=0.50, T=72, filt="n1a")),
    ("N2a_k8_T4_C30", dict(k=8, C=0.30, T=4)),
    ("N2a_k8_T12_C30", dict(k=8, C=0.30, T=12)),
    ("N2a_k8_T24_C30", dict(k=8, C=0.30, T=24)),
    ("N2b_k8_T4_C30", dict(k=8, C=0.30, T=4, filt="n2b")),
    ("P1_k1_T72_C30", dict(k=1, C=0.30, T=72)),
    ("P1_k2_T72_C30", dict(k=2, C=0.30, T=72)),
    ("P1_k3_T72_C30", dict(k=3, C=0.30, T=72)),
    ("P2_regime_k8_T72_C30", dict(k=8, C=0.30, T=72, regime="bre")),
    ("P2b_regime_k8_T72_C30", dict(k=8, C=0.30, T=72, regime="both")),
    ("C_k3_N1a_regime_C30", dict(k=3, C=0.30, T=72, filt="n1a", regime="both")),
    ("C_k3_N1b_regime_C30", dict(k=3, C=0.30, T=72, filt="n1b", regime="both")),
    ("C_k2_N1a_regime_C20", dict(k=2, C=0.20, T=72, filt="n1a", regime="both")),
    ("C_k8_N1a_regime_C30", dict(k=8, C=0.30, T=72, filt="n1a", regime="both")),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins-root", required=True)
    ap.add_argument("--arms", default="SHORT42,SHORT7,SHORT13")
    ap.add_argument("--labels-dir", required=True)
    ap.add_argument("--map-csv", required=True)
    ap.add_argument("--fund-cache", required=True)
    ap.add_argument("--btc", default="BTCUSDT")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    t0 = time.time()
    lbl = load_labels(a.labels_dir, a.map_csv)
    print("### nhãn %d dòng (%.1f phút)" % (len(lbl["key"]), (time.time() - t0) / 60), flush=True)
    fund = Fund(a.fund_cache)
    back = regime_tables(lbl, a.btc)
    print("### regime %d tick (%.1f phút)" % (len(back["u"]), (time.time() - t0) / 60), flush=True)

    res = {"cost": COST, "cost_stress": COST_STRESS, "configs": [c[0] for c in CONFIGS],
           "delta_f_flat_ref": -0.00585, "arms": {}}
    for arm in [x.strip() for x in a.arms.split(",") if x.strip()]:
        dirp = os.path.join(a.bins_root, arm)
        files = [os.path.join(dirp, "predict_wf_%s.bin" % f) for f in FOLDS]
        files = [f for f in files if os.path.exists(f)]
        if not files:
            print("### arm %s: KHONG co bins" % arm, flush=True)
            continue
        ts, sym, p = SMS.read_bins(files)
        key = ts * RES + sym.astype(np.int64)
        ip = np.clip(np.searchsorted(lbl["key"], key), 0, len(lbl["key"]) - 1)
        hit = lbl["key"][ip] == key
        ts, sym, p, ip = ts[hit], sym[hit], p[hit], ip[hit]
        ok = np.isfinite(p)
        ts, sym, p, ip = ts[ok], sym[ok], p[ok], ip[ok]
        o = np.argsort(ts, kind="stable")
        ts, sym, p, ip = ts[o], sym[o], p[o], ip[o]
        print("### %s join rows=%d (%.1f phút)" % (arm, len(ts), (time.time() - t0) / 60), flush=True)
        # rank & size trong tick (numpy, nhanh)
        o2 = np.lexsort((p, ts))
        ts_s = ts[o2]
        if len(ts_s):
            new = np.empty(len(ts_s), dtype=bool)
            new[0] = True
            np.not_equal(ts_s[1:], ts_s[:-1], out=new[1:])
            gid = np.cumsum(new) - 1
            firsts = np.flatnonzero(new)
            sizes = np.diff(np.append(firsts, len(ts_s)))
            r_sorted = (np.arange(len(ts_s)) - firsts[gid] + 1).astype(np.float64)
            r_arr = np.empty(len(ts_s)); r_arr[o2] = r_sorted
            n_arr = sizes[gid].astype(np.int64)
            del r_sorted, new
        else:
            gid = np.array([], dtype=np.int64); r_arr = np.array([]); n_arr = np.array([])
        del o2, ts_s
        # symId -> funding sid
        fsid_map = np.full(RES, -1, dtype=np.int32)
        for sid, nm in lbl["i2s"].items():
            if nm in fund.s2i:
                fsid_map[int(sid) % RES] = fund.s2i[nm]
        fsid = fsid_map[sym.astype(np.int64)]
        print("### %s funding... (%.1f phút)" % (arm, (time.time() - t0) / 60), flush=True)
        _f, _r1, _gap = fund.compute(fsid, ts)
        print("### %s funding done (%.1f phút)" % (arm, (time.time() - t0) / 60), flush=True)
        S = {"ts": ts, "p": p, "n": n_arr, "r": r_arr, "fsid": fsid, "i2s": lbl["i2s"]}
        for h in HOR:
            S["ret_%d" % h] = lbl["ret_%d" % h][ip].astype(np.float64)
            S["mfav_%d" % h] = lbl["mfav_%d" % h][ip].astype(np.float64)
            S["nb_%d" % h] = lbl["nb_%d" % h][ip].astype(np.float64)
        for h in HOR:
            S["f_%d" % h] = _f[h]
        S["r1"] = _r1
        S["gap"] = _gap
        print("### arm %s rows=%d (%.1f phút)" % (arm, len(ts), (time.time() - t0) / 60), flush=True)
        ar = {}
        for name, cfg in CONFIGS:
            ar[name] = eval_cfg(S, back, cfg)
            r = ar[name]
            print("%-22s kept=%.3f net_pre=%+.5f net_post=%+.5f win=%.3f yrs+=%s by_post=%s"
                  % (name, r.get("kept_frac", -1), r.get("net_pre", {}).get("mean", float("nan")),
                     r.get("net_post", {}).get("mean", float("nan")), r.get("winrate", float("nan")),
                     r.get("yrs_pos_post"), r.get("by_year_post")), flush=True)
        res["arms"][arm] = ar
        del S
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("### JSON -> %s (%.1f phút)" % (a.out, (time.time() - t0) / 60))


if __name__ == "__main__":
    main()
