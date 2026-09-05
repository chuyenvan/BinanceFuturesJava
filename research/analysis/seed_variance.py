"""SEED-VARIANCE CONTROL cho S1.

Cau hoi: |GPU - CPU| = 0.01843 (per-tick rank-IC) co LON so voi bien thien do
SEED tren CUNG mot device khong? Neu khong lon hon => device khong phai van de,
ket qua von nam trong nhieu. Day la nhom doi chung ma lenh cam GPU thieu.

Chay: python3 seed_variance.py [n_seed]   (mac dinh 5)
Moi thu giu NGUYEN nhu s1_rank.py; chi doi random_state.
"""
import logging
import sys
import time

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger(__name__)

H = 3600000
TZ = 7 * H
PURGE = 72 * H
LED = "/home/ubuntu/ledger"
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d",
        "rk_ret_3d", "ret_14d", "ls_global", "rk_oi_delta24h"]
CUT_DAYS = ["20220101", "20220401", "20220701", "20221001", "20230101",
            "20230401", "20230701", "20231001", "20240101", "20240401"]


def load():
    d = pd.read_parquet(f"{LED}/cand_dev.parquet")
    d = d[d.g1lite.notna()].copy()
    d["med"] = d.groupby("ts").g1lite.transform("median")
    d["rel"] = d.g1lite - d.med
    d["rk"] = d.groupby("ts").rel.rank(pct=True, method="first")
    d["rel5"] = np.minimum((d.rk * 5).astype(int), 4)
    d["ts_h"] = (d.ts // H) * H
    f = pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet")
    d = d.merge(f.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
    return d


def run_seed(d, cuts, seed):
    """Tra ve (per-tick rank-IC series, edge5 series) cho mot seed."""
    ics, edges = [], []
    for i, c in enumerate(cuts):
        lo = c
        hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
        tr = d[d.ts < c - PURGE].sort_values("ts")
        oos = d[(d.ts >= lo) & (d.ts < hi)].sort_values("ts")
        if len(tr) < 5000 or len(oos) == 0:
            continue
        assert tr.ts.max() < c, "LEAK"
        m = xgb.XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4,
                          learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                          min_child_weight=50, n_jobs=4, tree_method="hist",
                          random_state=seed, lambdarank_pair_method="topk",
                          lambdarank_num_pair_per_sample=8)
        m.fit(tr[KEEP], tr.rel5, qid=pd.factorize(tr.ts, sort=True)[0])
        o = oos[["ts", "sym", "g1lite"]].assign(score=-m.predict(oos[KEEP]))
        for ts, g in o.groupby("ts"):
            if len(g) > 4:
                ics.append((ts, spearmanr(-g.score, g.g1lite).correlation))
        o["rk"] = o.groupby("ts").score.rank(method="first")
        edges.append(o[o.rk <= 5].groupby("ts").g1lite.mean()
                     - o.groupby("ts").g1lite.mean())
    ic = pd.Series(dict(ics)).dropna()
    return ic, pd.concat(edges)


def main(nseed):
    t0 = time.time()
    d = load()
    cuts = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ for c in CUT_DAYS]
    LOG.info("pool %s | seeds %d", d.shape, nseed)
    res = {}
    for s in range(42, 42 + nseed):
        ic, e = run_seed(d, cuts, s)
        res[s] = ic
        LOG.info("seed %d | edge5 %+.4f%% | mean per-tick rankIC %+.6f | ticks %d | %.0fs",
                 s, 100 * e.mean(), ic.mean(), len(ic), time.time() - t0)
    M = pd.DataFrame(res).dropna()
    LOG.info("\n=== ticks chung: %d", len(M))
    LOG.info("sd cua mean per-tick rankIC giua cac seed: %.6f", M.mean().std())
    LOG.info("range mean rankIC: %.6f .. %.6f", M.mean().min(), M.mean().max())
    pw = []
    for a in M.columns:
        for b in M.columns:
            if a < b:
                pw.append(np.abs(M[a] - M[b]).mean())
    LOG.info("\n>>> SEED-VARIANCE: mean|rankIC_i - rankIC_j| tren tung tick")
    LOG.info(">>>   trung binh %.5f | min %.5f | max %.5f | n_cap %d",
             np.mean(pw), np.min(pw), np.max(pw), len(pw))
    LOG.info(">>> DOI CHIEU: |GPU - CPU| da do = 0.01843")
    LOG.info(">>> KET LUAN: %s",
             "device NAM TRONG nhieu seed => lenh cam GPU khong co co so"
             if np.mean(pw) >= 0.01843 else
             "device VUOT nhieu seed => khac biet moi truong that")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
