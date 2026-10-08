#!/usr/bin/env python3
"""HO1 B4b — feat_v2 (CHI 9 feature KEEP cua S1) dung theo CUA SO, y het cong thuc x1_feat_v2_build.py.
Pre-reg 35d03784 ADDENDUM-1 §5. closes = CLOSES_1H.bin ghim (DEV) + CLOSES_1H_2026.bin (Vision 2026); OI ghim e3887f63.
Cua so P tu T_START (warm-up >= 31 ngay truoc 2025-10-01; moi feature KEEP dung cua so <= 336h).
Cong G-B4a: doan chong 2025Q4 so feat_v2_x1.parquet — o lech tuong doi > 1e-6 (hoac NaN lech, hoac dong chi 1 ben)
chiem > 0,1% so o => DUNG. SEAL: khong in thong ke gia tri 2026.
Usage: python3 ho1_featv2_window.py <closes2026.bin> <out.parquet>"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho1feat")
H = 3600000
CLO = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
OI = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
DEVF = "/home/ubuntu/s1hpo/kaggle_ds/feat_v2_x1_keep9.parquet"  # = feat_v2_x1 KEEP9 ep float32 (md5 1aa3b974); ban goc da bi xoa
T_START = int(pd.Timestamp("2025-08-01").value // 10**6)       # UTC
T_END = int(pd.Timestamp("2026-07-01").value // 10**6)         # UTC (= 07:00 +07)
KEEP_FROM = int(pd.Timestamp("2025-09-30").value // 10**6)
Q4_LO = int(pd.Timestamp("2025-09-30 17:00").value // 10**6)   # 2025-10-01 00:00 +07
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d", "ls_global", "rk_oi_delta24h"]
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
ODT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]


def closes(c26):
    a = np.fromfile(CLO, dtype=DT)
    b = np.fromfile(c26, dtype=DT)
    dmax = int(a["ts"].astype(np.int64).max())
    b = b[b["ts"].astype(np.int64) > dmax]
    df = pd.concat([pd.DataFrame({"ts": x["ts"].astype(np.int64), "sym": x["sym"].astype(np.int32),
                                  "c": x["c"].astype(np.float64)}) for x in (a, b)])
    df = df[(df.ts >= T_START) & (df.ts <= T_END)]
    log.info("closes: DEV max ts %s, 2026 them %d rec, cua so %d rec", pd.to_datetime(dmax, unit="ms"), len(b), len(df))
    P = df.pivot(index="ts", columns="sym", values="c").sort_index()
    hours = pd.Index(np.arange(P.index.min(), P.index.max() + H, H))
    return P.reindex(hours)


def hrs_since_high(P, win):
    arr = P.to_numpy()
    n, m = arr.shape
    out = np.full((n, m), np.nan, dtype=np.float32)
    for j in range(m):
        col = arr[:, j]
        for i in range(win - 1, n):
            w = col[i - win + 1:i + 1]
            if np.isnan(w).sum() > win // 2:
                continue
            k = np.nanargmax(w)
            out[i, j] = (win - 1 - k) / win
    return pd.DataFrame(out, index=P.index, columns=P.columns)


def oi_frames(P):
    n = os.path.getsize(OI) // ODT.itemsize
    parts = []
    for k in range(0, n, 10_000_000):
        c = np.fromfile(OI, dtype=ODT, count=min(10_000_000, n - k), offset=k * ODT.itemsize)
        t = c["ts"].astype(np.int64)
        parts.append(c[(t <= T_END) & (t % H == 0) & (t >= T_START - 3 * H)].copy())
    o = np.concatenate(parts)
    od = pd.DataFrame({"ts": o["ts"].astype(np.int64), "sym": o["sym"].astype(np.int32)})
    ov = np.asarray(o["oi"], dtype=np.float32)
    out = {}
    for j, nm in enumerate(NAMES):
        if nm not in ("oi_delta24h", "ls_global"):
            continue
        M = od.assign(v=ov[:, j]).pivot(index="ts", columns="sym", values="v").reindex(index=P.index, columns=P.columns)
        out[nm] = M.ffill(limit=2)
    return out


def features(P):
    F = {}
    R1 = P / P.shift(1) - 1
    F["ret_3d"] = P / P.shift(72) - 1
    F["ret_14d"] = P / P.shift(336) - 1
    mx7 = P.rolling(168, min_periods=84).max()
    F["dd_7d"] = P / mx7 - 1
    F["hrs_since_high_7d"] = hrs_since_high(P, 168)
    F["vol_7d"] = R1.rolling(168, min_periods=84).std()
    O = oi_frames(P)
    F["ls_global"] = O["ls_global"]
    F["rk_dd_7d"] = F["dd_7d"].rank(axis=1, pct=True)
    F["rk_ret_3d"] = F["ret_3d"].rank(axis=1, pct=True)
    F["rk_oi_delta24h"] = O["oi_delta24h"].rank(axis=1, pct=True)
    stk = P.stack(dropna=False)
    idx, mask = stk.index, stk.notna().to_numpy()
    cols = {}
    for nm in KEEP:
        s = F[nm].stack(dropna=False)
        assert s.index.equals(idx), nm
        cols[nm] = s.to_numpy()[mask]
    long = pd.DataFrame(cols)
    long.insert(0, "sym", idx.get_level_values(1).to_numpy()[mask])
    long.insert(0, "ts", idx.get_level_values(0).to_numpy()[mask])
    return long[long.ts >= KEEP_FROM].reset_index(drop=True)


def gate(new):
    dev = pd.read_parquet(DEVF, columns=["ts", "sym"] + KEEP)
    dmax = int(dev.ts.max())
    dev = dev[dev.ts >= Q4_LO]
    nq = new[(new.ts >= Q4_LO) & (new.ts <= dmax)]
    M = dev.merge(nq, on=["ts", "sym"], how="outer", suffixes=("_d", "_n"), indicator=True)
    only = int((M["_merge"] != "both").sum())
    B = M[M["_merge"] == "both"]
    bad, per = only * len(KEEP), {}
    for nm in KEEP:
        a, b = B[nm + "_n"].to_numpy(np.float64), B[nm + "_d"].to_numpy(np.float64)
        nan_x = np.isnan(a) != np.isnan(b)
        both = ~np.isnan(a) & ~np.isnan(b)
        rel = np.zeros(len(a))
        rel[both] = np.abs(a[both] - b[both]) / np.maximum(np.abs(b[both]), 1e-12)
        k = int(nan_x.sum() + (rel > 1e-6).sum())
        per[nm] = k
        bad += k
    tot = len(M) * len(KEEP)
    g = dict(dev_ts_max=str(pd.to_datetime(dmax, unit="ms")), rows_dev=int(len(dev)), rows_new=int(len(nq)), rows_only_one=only,
             cells=tot, bad_cells=bad, bad_frac=bad / tot, per_feat=per)
    g["pass"] = bool(g["bad_frac"] <= 0.001)
    log.info("G-B4a: %s", g)
    return g


def main():
    c26, out = sys.argv[1], sys.argv[2]
    P = closes(c26)
    log.info("P %s %s..%s", P.shape, pd.to_datetime(P.index[0], unit="ms"), pd.to_datetime(P.index[-1], unit="ms"))
    long = features(P)
    g = gate(long)
    meta = dict(prereg="35d03784+ADD1", G_B4a=g, t_start=T_START, t_end=T_END, n_rows=int(len(long)),
                n_rows_2026=int((long.ts >= Q4_LO + 92 * 86400000 - 3600000 * 0).sum()))
    json.dump(meta, open(out + ".json", "w"), indent=1)
    if not g["pass"]:
        log.error("G-B4a FAIL -> DUNG")
        sys.exit(2)
    long.to_parquet(out, index=False)
    log.info("SAVED %s rows %d", out, len(long))


if __name__ == "__main__":
    main()
