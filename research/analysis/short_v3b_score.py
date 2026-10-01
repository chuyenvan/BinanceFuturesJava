#!/usr/bin/env python3
"""short_v3b_score.py — CHẤM 0-sim cho PREREG_SHORT_V3B/V3C (STEER OWNER 06:32).

Kỹ thuật bộ nhớ: nhãn/feature/funding CHỈ ghép cho các dòng ĐƯỢC CHỌN (top-8/tick, ~2 M dòng),
không dựng ma trận 35 M dòng ⇒ tránh OOM trên host 24 GB.

  (a) LỌC "ĐANG MẤT THANH KHOẢN" bằng feature CỦA CHÍNH ma trận 45 đã train (Tool1):
      V3B: L1a vtrend<=0 · L1b vtrend<=0 & vz<=0 · L1c vtrend<=0 & sqz>=0   [VOID - sai ngu nghia]
      V3C: L1a' vtrend<1,0 · L1b' vtrend<1,0 & vz<0 · L1c' vtrend<1,0 & sqz<1,0  (ratio theo Java)
  (b) ĐO "ĐỘ ĐỀU NHỊP GIẢM" (chẩn đoán, lookahead): ratio=retEnd_72h/maxAdv_72h, hoi=maxFav_72h
  (c) GIỮ ĐỦ 72h là chính + BẢNG ĐỐI CHIẾU giữ ngắn 4/12/24h

KHÔNG train, KHÔNG sim, KHÔNG chạm .java. DEV ≤ 2025-12-31.
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
import short_model_score as SMS
import short_v3_score as V

H = 3600000
DEV_CUT = 1767225600000
RES = 1024
HOR = [4, 12, 24, 72]
NEED = {h: 4 * h for h in HOR}
FOLDS = V.FOLDS
FEAT_IDX = {"vz": 26, "vtrend": 27, "breadth": 4, "sqz": 31}
COLS = ["tEpochMs", "symbol", "maxAdv_72h"]
for h in HOR:
    COLS += ["retEnd_%dh" % h, "maxFav_%dh" % h, "nBars_%dh" % h]


def load_labels(lb_dir, map_csv):
    sys.path.insert(0, os.environ.get("SEL1M_CODE", "/home/ubuntu/sel1m_code"))
    import funding_label_pb as FLPB
    smap = pd.read_csv(map_csv)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    i2s = dict(zip(smap.symId.astype(np.int32), smap.symbol))
    fs = sorted(glob.glob(lb_dir + "/funding_label_*.pb"))
    fs = [f for f in fs if ".part" not in f]
    acc = {"ts": [], "sym": [], "madv": []}
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
        acc["madv"].append(d["maxAdv_72h"].to_numpy(np.float32)[k])
        for h in HOR:
            acc["ret_%d" % h].append(d["retEnd_%dh" % h].to_numpy(np.float32)[k])
            acc["mfav_%d" % h].append(d["maxFav_%dh" % h].to_numpy(np.float32)[k])
            acc["nb_%d" % h].append(d["nBars_%dh" % h].to_numpy(np.float32)[k])
    ts = np.concatenate(acc["ts"]); sym = np.concatenate(acc["sym"])
    key = ts * RES + sym.astype(np.int64)
    o = np.argsort(key, kind="stable")
    out = {"key": key[o], "i2s": i2s}
    for kk in list(acc):
        if kk == "ts":
            continue
        out[kk] = np.concatenate(acc[kk])[o]
    return out


def load_feats(t1_dir, years=("2022", "2023", "2024", "2025")):
    sys.path.insert(0, os.environ.get("SEL1M_CODE", "/home/ubuntu/sel1m_code"))
    from tool1_col import read_tool1
    ks, vs = [], []
    files = sorted(glob.glob(os.path.join(t1_dir, "features_*")))
    files = [f for f in files if ".part" not in f
             and any("_%s" % yr in os.path.basename(f) for yr in years)]
    print("  feat files: %d" % len(files), flush=True)
    for fp in files:
        a = read_tool1(fp, grid_ms=900000)
        F = a["f"]
        sym = a["sym"].astype(np.int32); ts = a["ts"].astype(np.int64)
        cols = np.empty((len(sym), len(FEAT_IDX)), dtype=np.float32)
        for j, nm in enumerate(FEAT_IDX):
            cols[:, j] = F[:, FEAT_IDX[nm]]
        ks.append(ts * RES + sym.astype(np.int64)); vs.append(cols)
        del a, F, cols, sym, ts
    key = np.concatenate(ks); val = np.concatenate(vs)
    o = np.argsort(key, kind="stable")
    return key[o], val[o], list(FEAT_IDX)


def _c(d):
    return {"mean": round(d["mean"], 6), "raw": [round(d["raw"][0], 6), round(d["raw"][1], 6)],
            "out_raw": d["out_raw"], "out_legacy": d["out_legacy"], "out_both": d["out_both"]}


def eval_cfg(S, cfg):
    k = cfg["k"]; T = cfg["T"]; C = cfg["C"]
    keep = S["r"] > (S["n"] - k)
    fav = {nm: S["f_" + nm] for nm in S["fnames"]}
    L = cfg.get("L")
    if L == "L1a":
        keep &= fav["vtrend"] <= 0
    elif L == "L1b":
        keep &= (fav["vtrend"] <= 0) & (fav["vz"] <= 0)
    elif L == "L1c":
        keep &= (fav["vtrend"] <= 0) & (fav["sqz"] >= 0)
    elif L == "L1a2":
        keep &= fav["vtrend"] < 1.0
    elif L == "L1b2":
        keep &= (fav["vtrend"] < 1.0) & (fav["vz"] < 0.0)
    elif L == "L1c2":
        keep &= (fav["vtrend"] < 1.0) & (fav["sqz"] < 1.0)
    if cfg.get("n1b"):
        keep &= S["n1b_ok"]
    if cfg.get("diag") == "smooth":
        keep &= S["ratio"] >= 0.5
    elif cfg.get("diag") == "smoothhoi":
        keep &= (S["ratio"] >= 0.5) & (S["mfav_72"] <= 0.03)
    nsel = int(keep.sum())
    if nsel == 0:
        return {"n_sel": 0, "n_kept": 0, "kept_frac": 0.0, "err": "no trade"}
    ts_k = S["ts"][keep]
    ret = S["ret_%d" % T][keep]; mfav = S["mfav_%d" % T][keep]; nb = S["nb_%d" % T][keep]
    ok = nb >= NEED[T]
    if C is None or not np.isfinite(C):
        pnl = -ret
    else:
        pnl = np.where(mfav >= C, -C, -ret)
    pnl = np.where(ok, pnl, np.nan)
    f = S["f_%d" % T][keep]
    m = np.isfinite(pnl) & np.isfinite(f)
    ts_k, pnl, f = ts_k[m], pnl[m], f[m]
    if len(ts_k) == 0:
        return {"n_sel": nsel, "n_kept": 0, "kept_frac": 0.0, "err": "no trade2"}
    pt, pts = V._per_tick(pnl, ts_k)
    ptf, _ = V._per_tick(pnl + f, ts_k)
    net_pre = SMS.ci_mean(pt - V.COST, pts)
    net_post = SMS.ci_mean(ptf - V.COST, pts)
    by_post = V._by_year(ptf - V.COST, pts)
    w = pnl - V.COST + f
    yrs = sum(1 for v in by_post.values() if v is not None and v > 0)
    ratio = S["ratio"][keep][m]; hoi = S["mfav_72"][keep][m]
    return {"n_sel": nsel, "n_kept": int(keep.sum()), "kept_frac": round(float(keep.mean()), 4),
            "net_pre": _c(net_pre), "net_post": _c(net_post),
            "winrate": round(float((w > 0).mean()), 4), "by_year_post": by_post,
            "yrs_pos_post": yrs, "fund_mean": round(float(f.mean()), 6),
            "ratio_med": round(float(np.nanmedian(ratio)), 4),
            "hoi_med": round(float(np.nanmedian(hoi)), 4),
            "out_both": bool(net_post["out_both"]), "B": bool(net_post["out_both"] and yrs >= 3),
            "C": bool((w > 0).mean() >= 0.55)}


CONFIGS = [
    ("base_T72_C30", dict(k=8, C=0.30, T=72)),
    ("giu_ngan_T4_C30", dict(k=8, C=0.30, T=4)),
    ("giu_ngan_T12_C30", dict(k=8, C=0.30, T=12)),
    ("giu_ngan_T24_C30", dict(k=8, C=0.30, T=24)),
    ("L1a_T72_C30", dict(k=8, C=0.30, T=72, L="L1a")),
    ("L1b_T72_C30", dict(k=8, C=0.30, T=72, L="L1b")),
    ("L1c_T72_C30", dict(k=8, C=0.30, T=72, L="L1c")),
    ("L1b_N1b_T72_C30", dict(k=8, C=0.30, T=72, L="L1b", n1b=True)),
    ("L1ap_T72_C30", dict(k=8, C=0.30, T=72, L="L1a2")),
    ("L1bp_T72_C30", dict(k=8, C=0.30, T=72, L="L1b2")),
    ("L1cp_T72_C30", dict(k=8, C=0.30, T=72, L="L1c2")),
    ("L1ap_N1b_T72_C30", dict(k=8, C=0.30, T=72, L="L1a2", n1b=True)),
    ("L1bp_N1b_T72_C30", dict(k=8, C=0.30, T=72, L="L1b2", n1b=True)),
    ("L1cp_N1b_T72_C30", dict(k=8, C=0.30, T=72, L="L1c2", n1b=True)),
    ("L1bp_N1b_T4_C30", dict(k=8, C=0.30, T=4, L="L1b2", n1b=True)),
    ("L1bp_N1b_T24_C30", dict(k=8, C=0.30, T=24, L="L1b2", n1b=True)),
    ("L1bp_N1b_T72_C50", dict(k=8, C=0.50, T=72, L="L1b2", n1b=True)),
    ("L1bp_N1b_K3_T72_C30", dict(k=3, C=0.30, T=72, L="L1b2", n1b=True)),
    ("diag_smooth_T72_C30", dict(k=8, C=0.30, T=72, diag="smooth")),
    ("diag_smoothhoi_T72_C30", dict(k=8, C=0.30, T=72, diag="smoothhoi")),
    ("L1bp_diag_smoothhoi_C30", dict(k=8, C=0.30, T=72, L="L1b2", diag="smoothhoi")),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins-root", required=True)
    ap.add_argument("--arms", default="SHORT42,SHORT7,SHORT13")
    ap.add_argument("--labels-dir", required=True)
    ap.add_argument("--map-csv", required=True)
    ap.add_argument("--fund-cache", required=True)
    ap.add_argument("--t1-dir", default="/home/ubuntu/ds_feat15m")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.time()
    lbl = load_labels(a.labels_dir, a.map_csv)
    print("### nhan %d dong (%.1f phut)" % (len(lbl["key"]), (time.time() - t0) / 60), flush=True)
    fund = V.Fund(a.fund_cache)
    fkey, fval, fnames = load_feats(a.t1_dir)
    print("### feats %d dong (%.1f phut)" % (len(fkey), (time.time() - t0) / 60), flush=True)
    res = {"cost": V.COST, "configs": [c[0] for c in CONFIGS], "feat_idx": FEAT_IDX, "arms": {}}
    for arm in [x.strip() for x in a.arms.split(",") if x.strip()]:
        dirp = os.path.join(a.bins_root, arm)
        files = [os.path.join(dirp, "predict_wf_%s.bin" % f) for f in FOLDS]
        files = [f for f in files if os.path.exists(f)]
        if not files:
            print("### arm %s KHONG co bins" % arm, flush=True)
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
        # rank & size trong tick
        o2 = np.lexsort((p, ts)); ts_s = ts[o2]
        new = np.empty(len(ts_s), dtype=bool); new[0] = True
        np.not_equal(ts_s[1:], ts_s[:-1], out=new[1:])
        gid = np.cumsum(new) - 1
        firsts = np.flatnonzero(new)
        sizes = np.diff(np.append(firsts, len(ts_s)))
        r_arr = np.empty(len(ts_s)); r_arr[o2] = (np.arange(len(ts_s)) - firsts[gid] + 1).astype(np.float64)
        n_arr = sizes[gid].astype(np.int64)
        del o2, ts_s, new, gid, firsts, sizes, p
        # CHỈ ghép cho dòng top-8 (giảm bộ nhớ ~15x)
        idx = np.flatnonzero(r_arr > (n_arr - 8))
        print("### arm %s rows=%d sel=%d (%.1f phut)" % (arm, len(ts), len(idx),
                                                        (time.time() - t0) / 60), flush=True)
        ts_s2 = ts[idx]; sym_s2 = sym[idx]; ip2 = ip[idx]
        key_s2 = ts_s2 * RES + sym_s2.astype(np.int64)
        S = {"ts": ts_s2, "r": r_arr[idx], "n": n_arr[idx], "fnames": fnames}
        del idx, r_arr, n_arr, ts, sym, ip
        for h in HOR:
            S["ret_%d" % h] = lbl["ret_%d" % h][ip2]
            S["mfav_%d" % h] = lbl["mfav_%d" % h][ip2]
            S["nb_%d" % h] = lbl["nb_%d" % h][ip2]
        S["mfav_72"] = S["mfav_72"]
        madv = lbl["madv"][ip2]
        S["ratio"] = np.clip(np.where(madv < -1e-6, S["ret_72"] / madv, np.nan), 0.0, 1.5)
        del madv
        # feature join (chỉ dòng chọn)
        jp = np.clip(np.searchsorted(fkey, key_s2), 0, len(fkey) - 1)
        jhit = fkey[jp] == key_s2
        for j, nm in enumerate(fnames):
            S["f_" + nm] = np.where(jhit, fval[jp, j], np.nan).astype(np.float32)
        del jp, jhit
        # funding (chỉ dòng chọn)
        fsid_map = np.full(RES, -1, dtype=np.int32)
        for sid, nm in lbl["i2s"].items():
            if nm in fund.s2i:
                fsid_map[int(sid) % RES] = fund.s2i[nm]
        fsid = fsid_map[sym_s2.astype(np.int64)]
        _f, _r1, _ = fund.compute(fsid, ts_s2)
        for h in HOR:
            S["f_%d" % h] = _f[h].astype(np.float32)
        S["n1b_ok"] = np.isfinite(_r1) & (_r1 >= 0)
        del _f, _r1
        print("### arm %s built S=%d (%.1f phut)" % (arm, len(S["ts"]), (time.time() - t0) / 60), flush=True)
        ar = {}
        for name, cfg in CONFIGS:
            ar[name] = eval_cfg(S, cfg)
            r = ar[name]
            print("%-24s kept=%.3f net_pre=%+.5f net_post=%+.5f win=%.3f yrs+=%s ratio=%.3f hoi=%.3f"
                  % (name, r.get("kept_frac", -1), r.get("net_pre", {}).get("mean", float("nan")),
                     r.get("net_post", {}).get("mean", float("nan")), r.get("winrate", float("nan")),
                     r.get("yrs_pos_post"), r.get("ratio_med", float("nan")),
                     r.get("hoi_med", float("nan"))), flush=True)
        res["arms"][arm] = ar
        del S
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("### JSON -> %s (%.1f phut)" % (a.out, (time.time() - t0) / 60))


if __name__ == "__main__":
    main()
