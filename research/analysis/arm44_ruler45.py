#!/usr/bin/env python3
"""arm44_ruler45.py — RULER cua model 45 cot BAN DEPLOY (offline, Oracle).

Sinh `45deploy_perfold_ticks.parquet` + `arm44_ruler45.json` voi DUNG dinh nghia metric cua vong Stage 2 /
kernel ARM44: rank-IC cross-section theo tung tick (chi tick >= 2 coin) giua `p0` va `retEnd_4h`, va
`lift8` = mean_y(top-8 theo p0 trong tick) − base_rate(tick), THR = 0.015.

Nguon:
  bins : /home/ubuntu/claudedata/predwf_G015x26/predict_wf_<fold>.bin  (bins GIA TRI cua ban deploy,
         16 fold 20220101..20251001, 26 B/rec = >q h 4f)
  label: /home/ubuntu/label_15m/funding_label_*.pb  (DUNG file nhu dataset Kaggle `funding-label-15m`:
         da kiem 20/20 ten + so byte trung)

KHONG train, KHONG sim, KHONG cham ONNX/LIVE. Read-only.
Usage: python3 arm44_ruler45.py [--out /tmp/a44out] [--bins DIR] [--labels DIR]
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/sel1m_code")
import funding_label_pb as FLPB  # noqa: E402

FOLDS = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401", "20230701",
         "20231001", "20240101", "20240401", "20240701", "20241001", "20250101", "20250401",
         "20250701", "20251001"]
BIN_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p", ">f4"), ("z", ">f4", 3)])
THR = 0.015


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/a44out")
    ap.add_argument("--bins", default="/home/ubuntu/claudedata/predwf_G015x26")
    ap.add_argument("--labels", default="/home/ubuntu/label_15m")
    ap.add_argument("--map", default="/home/ubuntu/claudedata/oi/symbol_map.csv")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    smap = pd.read_csv(a.map)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    fs = sorted(f for f in os.listdir(a.labels)
                if f.startswith("funding_label_") and f.endswith(".pb") and f.split("_")[2] < "20260101")
    print("label files:", len(fs), flush=True)
    tl, sl, vl = [], [], []
    for fn in fs:
        d = FLPB.read_label(os.path.join(a.labels, fn),
                            usecols=["tEpochMs", "symbol", "retEnd_4h"])
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        ts = d.tEpochMs.to_numpy(np.int64)[k]
        v = d.retEnd_4h.to_numpy(np.float64)[k]
        ok = np.isfinite(v)
        sv = sid.to_numpy()[k]
        tl.append(ts[ok]); sl.append(sv[ok].astype(np.int32)); vl.append(v[ok])
        del d
    tl = np.concatenate(tl); sl = np.concatenate(sl); vl = np.concatenate(vl)
    order = np.argsort(tl * 1024 + sl, kind="stable")
    LK = (tl * 1024 + sl)[order]; LV = vl[order]
    del tl, sl, vl, order
    print("label rows (retEnd_4h notna):", len(LK), "| %.0fs" % (time.time() - t0), flush=True)

    rows = []
    for f in FOLDS:
        bp = os.path.join(a.bins, "predict_wf_%s.bin" % f)
        arr = np.fromfile(bp, dtype=BIN_DT)
        ts = arr["ts"].astype(np.int64); sy = arr["sym"].astype(np.int64)
        p = arr["p"].astype(np.float32)
        key = ts * 1024 + sy
        ip = np.clip(np.searchsorted(LK, key), 0, len(LK) - 1)
        hit = LK[ip] == key
        y = np.full(len(key), np.nan)
        y[hit] = LV[ip[hit]]
        m = np.isfinite(y)
        d = pd.DataFrame({"ts": ts[m], "p": p[m], "y": y[m]})
        nn = d.groupby("ts").size()
        d["_g"] = d["ts"].map(nn)
        d = d[d["_g"] >= 2]
        r1 = d.groupby("ts")["p"].rank(method="average")
        r2 = d.groupby("ts")["y"].rank(method="average")
        m1 = r1.groupby(d.ts).transform("mean"); m2 = r2.groupby(d.ts).transform("mean")
        num = ((r1 - m1) * (r2 - m2)).groupby(d.ts).sum()
        ss1 = ((r1 - m1) ** 2).groupby(d.ts).sum(); ss2 = ((r2 - m2) ** 2).groupby(d.ts).sum()
        ic = num / np.sqrt(ss1 * ss2).replace(0, np.nan)
        d["hit"] = (d.y > THR).astype(float)
        base = d.groupby("ts")["hit"].mean()
        top = d.sort_values(["ts", "p"], ascending=[True, False]).groupby("ts").head(8)
        t8 = top.groupby("ts")["hit"].mean()
        n8 = top.groupby("ts").size()
        n = d.groupby("ts").size()
        r = pd.DataFrame({"ic": ic, "base": base, "t8": t8, "n8": n8, "n_coin": n})
        r["lift8"] = r["t8"] - r["base"]
        r["fold"] = f
        rows.append(r.reset_index())
        print("  fold %s rows=%d ticks=%d" % (f, len(d), len(r)), flush=True)
        del arr, d, r
    A = pd.concat(rows, ignore_index=True)
    A.to_parquet(os.path.join(a.out, "45deploy_perfold_ticks.parquet"), index=False)
    g = A.groupby("fold")
    res = {"n_tick": int(len(A)), "ic_mean": float(A.ic.mean()), "lift8_mean": float(A.lift8.mean()),
           "ic_by_fold": {k: float(v) for k, v in g["ic"].mean().items()},
           "lift8_by_fold": {k: float(v) for k, v in g["lift8"].mean().items()},
           "n_coin_mean": float(A.n_coin.mean()),
           "bins_dir": a.bins, "labels_dir": a.labels,
           "seconds": round(time.time() - t0, 1)}
    json.dump(res, open(os.path.join(a.out, "arm44_ruler45.json"), "w"), indent=1)
    print("RULER45 n_tick=%d ic=%.6f lift8=%.6f | %.0fs" % (
        res["n_tick"], res["ic_mean"], res["lift8_mean"], res["seconds"]), flush=True)


if __name__ == "__main__":
    main()
