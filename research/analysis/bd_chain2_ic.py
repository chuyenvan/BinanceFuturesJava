#!/usr/bin/env python3
"""BD_CHAIN2 (NHIEM VU A) — do lai rank-IC cua `rateDown15MAvg` goc vs bien the ty le universe `f`.

0-SIM THUAN PYTHON: KHONG Java, KHONG sim, KHONG xgboost, KHONG cham 2026.
Nguon: gate store (momentum15M = rateDown15MAvg, momentum1M = rateDownAvg) +
        market.bin sinh lai cho f in {0,0.5,1.0} (Kernel A, /home/ubuntu/kaggle_bdchain/out).
IC dinh nghia y nhu `research/pipeline/gate_feat_study/score_cycle.py`: Spearman(feature, label_oldbasket)
de-overlap 15m (giu moc ts%900000==0). Day la rank-IC 1 chieu theo THOI GIAN (feature market-level,
KHONG co phuong sai cross-section => IC cross-section la suy bien).

Usage: python3 research/analysis/bd_chain2_ic.py
"""
import gzip
import json
import logging
import os
import struct

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("bd_chain2_ic")

STORE = "/home/ubuntu/claudedata/gate_dataset_full.csv.gz"
BIN_DIR = "/home/ubuntu/kaggle_bdchain/out"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "bd_chain2_ic.json")
DEV_END_MS = int(pd.Timestamp("2025-12-31 23:59:59", tz="Asia/Saigon").timestamp() * 1000)
DT = np.dtype([("ts", ">i8"), ("down", ">f4"), ("up", ">f4"), ("down15", ">f4")])


def load_market_bin(tag):
    p = os.path.join(BIN_DIR, tag, "market.bin")
    with open(p, "rb") as f:
        n = int(struct.unpack(">i", f.read(4))[0])
        buf = f.read(n * 20)
    a = np.frombuffer(buf, dtype=DT)
    return pd.DataFrame({"timestamp": a["ts"].astype(np.int64),
                         "d1": a["down"].astype(np.float64),
                         "d15": a["down15"].astype(np.float64)})


def ic_series(df, col, year=None):
    d = df[df.timestamp % 900000 == 0].copy()
    if year is not None:
        lo = int(pd.Timestamp(f"{year}-01-01", tz="Asia/Saigon").timestamp() * 1000)
        hi = int(pd.Timestamp(f"{year+1}-01-01", tz="Asia/Saigon").timestamp() * 1000)
        d = d[(d.timestamp >= lo) & (d.timestamp < hi)]
    d = d.dropna(subset=[col, "label"])
    if len(d) < 100:
        return None
    return dict(n=int(len(d)), ic=float(spearmanr(d[col], d["label"]).correlation))


def main():
    LOG.info("doc gate store ...")
    df = pd.read_csv(STORE, usecols=["timestamp", "momentum1M", "momentum5M",
                                     "momentum15M", "label_oldbasket"])
    df = df[df.timestamp < DEV_END_MS].reset_index(drop=True)
    df = df.rename(columns={"label_oldbasket": "label"})
    LOG.info("store DEV rows=%d  ts [%s .. %s]", len(df),
             pd.to_datetime(df.timestamp.min(), unit="ms", utc=True).tz_convert("Asia/Saigon"),
             pd.to_datetime(df.timestamp.max(), unit="ms", utc=True).tz_convert("Asia/Saigon"))

    res = {"store_rows": int(len(df)), "dev_end": DEV_END_MS, "arms": {}}

    # goc = momentum15M trong store goc
    base = df[["timestamp", "momentum1M", "momentum5M", "momentum15M", "label"]].copy()
    res["arms"]["goc(f=0,store)"] = {"m15": ic_series(base, "momentum15M"),
                                     "m1": ic_series(base, "momentum1M")}

    for tag, f in (("f000", 0.0), ("f050", 0.5), ("f100", 1.0)):
        mb = load_market_bin(tag)
        LOG.info("patch %s (f=%s) rows=%d", tag, f, len(mb))
        m = base.merge(mb, on="timestamp", how="left")
        m["momentum15M"] = m["d15"].fillna(m["momentum15M"])
        m["momentum1M"] = m["d1"].fillna(m["momentum1M"])
        m["momentumAcceleration"] = m["momentum5M"] - m["momentum15M"]
        arm = {"f": f, "matched_minutes": int(m["d15"].notna().sum()),
               "m15": ic_series(m, "momentum15M"), "m1": ic_series(m, "momentum1M"),
               "by_year": {}}
        for y in (2021, 2022, 2023, 2024, 2025):
            arm["by_year"][str(y)] = ic_series(m, "momentum15M", year=y)
        res["arms"][f"regen({tag},f={f})"] = arm

    # f=0 sinh lai de doi chieu "goc store" vs "goc tai tao"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)

    # in bang gon
    g = res["arms"]["goc(f=0,store)"]["m15"]
    LOG.info("=== rank-IC(momentum15M = rateDown15MAvg, label_oldbasket) de-overlap 15m ===")
    LOG.info("goc(store):  n=%d  IC=%+.5f", g["n"], g["ic"])
    for k, a in res["arms"].items():
        if not k.startswith("regen"):
            continue
        m15 = a["m15"]
        LOG.info("%-18s f=%.1f n=%d  IC=%+.5f  (ratio vs goc = %+.3f)",
                 k, a["f"], m15["n"], m15["ic"], m15["ic"] / g["ic"])
    LOG.info("saved %s", OUT)


if __name__ == "__main__":
    main()
