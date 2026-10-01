#!/usr/bin/env python3
"""BD_CHAIN2 (NHIEM VU A, doi chieu #2) — rank-IC cua rateDown15MAvg goc vs bien the `f`
so voi NHAN TUONG LAI 72h (retEnd_72h / pathq_72h) tu funding_label .pb.

Signal = rateDown15MAvg (market-level, 1 chieu theo thoi gian) => nhan cung phai market-level:
        EW-mean(retEnd_72h) va EW-mean(pathq_72h) tren universe tai moi moc 15m.
0-SIM: KHONG Java/sim/xgboost, KHONG cham 2026.
"""
import glob
import json
import logging
import os
import struct
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "/home/ubuntu/sel1m_code")
from funding_label_pb import read_label  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("bd_chain2_ic72")

LABDIR = "/home/ubuntu/claudedata/wfo15m/label_ds_15m"
BIN_DIR = "/home/ubuntu/kaggle_bdchain/out"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "bd_chain2_ic72.json")
Q = 900_000
DT = np.dtype([("ts", ">i8"), ("down", ">f4"), ("up", ">f4"), ("down15", ">f4")])


def market_forward():
    parts = []
    for p in sorted(glob.glob(os.path.join(LABDIR, "funding_label_15m_*.pb"))):
        if "2026" in os.path.basename(p):
            continue  # DEV <= 2025-12-31
        L = read_label(p, usecols=["tEpochMs", "retEnd_72h", "maxFav_72h", "maxAdv_72h"])
        L["pathq_72h"] = L["maxFav_72h"] / (L["maxAdv_72h"].abs() + 0.01)
        g = L.groupby("tEpochMs").agg(retEnd=("retEnd_72h", "mean"),
                                      pathq=("pathq_72h", "mean"),
                                      ncoin=("retEnd_72h", "size")).reset_index()
        parts.append(g)
        LOG.info("%s -> %d ticks", os.path.basename(p), len(g))
    d = pd.concat(parts, ignore_index=True)
    # tEpochMs da o moc 15' (khop thang voi market.bin)
    d["ts15"] = d["tEpochMs"].astype(np.int64)
    return d


def load_market_bin(tag):
    p = os.path.join(BIN_DIR, tag, "market.bin")
    with open(p, "rb") as f:
        n = int(struct.unpack(">i", f.read(4))[0])
        buf = f.read(n * 20)
    a = np.frombuffer(buf, dtype=DT)
    return pd.DataFrame({"ts": a["ts"].astype(np.int64), "d15": a["down15"].astype(np.float64)})


def ic(df, sig, lab, year=None):
    d = df.dropna(subset=[sig, lab])
    if year is not None:
        lo = int(pd.Timestamp(f"{year}-01-01", tz="Asia/Saigon").timestamp() * 1000)
        hi = int(pd.Timestamp(f"{year+1}-01-01", tz="Asia/Saigon").timestamp() * 1000)
        d = d[(d.ts15 >= lo) & (d.ts15 < hi)]
    if len(d) < 100:
        return None
    return dict(n=int(len(d)), ic=float(spearmanr(d[sig], d[lab]).correlation))


def main():
    LOG.info("doc funding_label -> nhan market-level 72h ...")
    fwd = market_forward()
    LOG.info("nhan: %d moc 15m, ncoin mean=%.1f", len(fwd), fwd.ncoin.mean())

    res = {"n_ticks_label": int(len(fwd)), "arms": {}}
    # goc (f=0) = rateDown15MAvg tu market.bin GOC trong bundle
    for tag, f in (("f000", 0.0), ("f050", 0.5), ("f100", 1.0)):
        mb = load_market_bin(tag)
        mb = mb[mb["ts"] % Q == 0].rename(columns={"ts": "ts15"})
        m = fwd.merge(mb, on="ts15", how="inner")
        arm = {"f": f, "matched_ticks": int(len(m)),
               "retEnd": ic(m, "d15", "retEnd"), "pathq": ic(m, "d15", "pathq"),
               "by_year_retEnd": {str(y): ic(m, "d15", "retEnd", year=y) for y in range(2021, 2026)}}
        res["arms"][f"regen({tag},f={f})"] = arm
        LOG.info("f=%.1f ticks=%d  IC(retEnd)=%+.5f  IC(pathq)=%+.5f", f, len(m),
                 arm["retEnd"]["ic"], arm["pathq"]["ic"])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    LOG.info("saved %s", OUT)


if __name__ == "__main__":
    main()
