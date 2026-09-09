#!/usr/bin/env python3
"""
CI cho so sanh 2 chu trinh: IC paired per fold + bootstrap block 72h x1.21.
Dau vao: 2 file p15_<tag>.csv + realized tu store.
So sanh: IC(cua trinh) - IC(STAGE0) tren CUNG de-overlap grid; block = 72h lien tuc theo ts.

Usage: python3 gate_feat_study/ci_cycle.py --tag CYC1 --ref STAGE0
"""
import argparse, datetime, logging, os
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("ci")
STORE = "/home/ubuntu/claudedata/gate_dataset_full.csv.gz"
OUTDIR = "/home/ubuntu/gate_feat_study"
BLOCK_MS = 72 * 3600_000
NREP = 2000
F = 1.21


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--ref", default="STAGE0")
    a = ap.parse_args()
    real = pd.read_csv(STORE, usecols=["timestamp", "label_oldbasket"]).rename(
        columns={"label_oldbasket": "realized"})
    t = pd.read_csv(os.path.join(OUTDIR, f"p15_{a.tag}.csv"))
    r = pd.read_csv(os.path.join(OUTDIR, f"p15_{a.ref}.csv"))
    m = pd.merge(pd.merge(t, real, on="timestamp"), r, on="timestamp", suffixes=("_t", "_r"))
    d = m[m.timestamp % 900000 == 0].reset_index(drop=True)  # de-overlap 15m
    LOG.info("n de-overlap=%d", len(d))
    ic_t = spearmanr(d.pred_t, d.realized).correlation
    ic_r = spearmanr(d.pred_r, d.realized).correlation
    LOG.info("IC %s=%.4f  IC %s=%.4f  diff=%.4f", a.tag, ic_t, a.ref, ic_r, ic_t - ic_r)

    # block bootstrap: cat theo block 72h, resample block
    d = d.sort_values("timestamp").reset_index(drop=True)
    blocks = []
    cur = []
    start = d.timestamp.iloc[0]
    for _, row in d.iterrows():
        if row.timestamp - start >= BLOCK_MS:
            blocks.append(cur)
            cur = []
            start = row.timestamp
        cur.append(row)
    if cur:
        blocks.append(cur)
    nblk = len(blocks)
    LOG.info("n block 72h=%d", nblk)
    rng = np.random.default_rng(20260909)
    diffs = np.empty(NREP)
    block_dfs = [pd.DataFrame(b) for b in blocks]
    for b in range(NREP):
        idx = rng.integers(0, nblk, nblk)
        s = pd.concat([block_dfs[i] for i in idx])
        d_t = spearmanr(s.pred_t, s.realized).correlation
        d_r = spearmanr(s.pred_r, s.realized).correlation
        diffs[b] = d_t - d_r
    lo, hi = np.percentile(diffs, 2.5), np.percentile(diffs, 97.5)
    # he so F (BENCH_DEVICE / PREREG_X1): CI hep gia -> nhan rong
    mean_diff = diffs.mean()
    half = (hi - lo) / 2
    LOG.info("diff mean=%.4f  CI95 raw [%.4f, %.4f]  CI95 x%.2f [%.4f, %.4f]",
             mean_diff, lo, hi, F, mean_diff - F * half, mean_diff + F * half)
    ppos = float((diffs > 0).mean())
    LOG.info("P(diff>0)=%.3f", ppos)


if __name__ == "__main__":
    main()
