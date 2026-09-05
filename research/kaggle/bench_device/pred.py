"""Dump du doan OOS gop (seed 42 va 43) de tinh dung thong ke ma cong cu ban GPU dung:
spearman(pred_A, pred_B). Chay duoc o ca 3 moi truong nhu run.py."""
import glob
import hashlib
import json
import logging
import os
import sys
import time

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("pred")
H = 3600000
TZ = 7 * H
PURGE = 72 * H
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d",
        "rk_ret_3d", "ret_14d", "ls_global", "rk_oi_delta24h"]
CUT_DAYS = ["20220101", "20220401", "20220701", "20221001", "20230101",
            "20230401", "20230701", "20231001", "20240101", "20240401"]
DEV = os.environ.get("BENCH_DEVICE", "cpu")
NJOBS = int(os.environ.get("BENCH_NJOBS", "4"))
SEEDS = [int(x) for x in os.environ.get("BENCH_SEEDS", "42,43").split(",")]
TAG = os.environ.get("BENCH_TAG", "pred")
OUT = os.environ.get("BENCH_OUT", "/kaggle/working")


def data():
    p = os.environ.get("BENCH_DATA", "")
    if p and os.path.exists(p):
        return p
    return sorted(glob.glob("/kaggle/input/**/bench_s1.parquet", recursive=True))[0]


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    d = pd.read_parquet(data())
    cuts = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ
            for c in CUT_DAYS]
    parts = []
    for c in cuts:
        hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
        tr = d[d.ts < c - PURGE].sort_values("ts", kind="mergesort")
        oos = d[(d.ts >= c) & (d.ts < hi)].sort_values("ts", kind="mergesort")
        if len(tr) < 5000 or len(oos) == 0:
            continue
        o = oos[["ts", "sym"]].copy()
        for s in SEEDS:
            kw = dict(objective="rank:ndcg", n_estimators=300, max_depth=4,
                      learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                      min_child_weight=50, n_jobs=NJOBS, tree_method="hist",
                      random_state=s, lambdarank_pair_method="topk",
                      lambdarank_num_pair_per_sample=8)
            if DEV == "cuda":
                kw["device"] = "cuda"
            m = xgb.XGBRanker(**kw)
            m.fit(tr[KEEP], tr.rel5, qid=pd.factorize(tr.ts, sort=True)[0])
            o[f"p{s}"] = np.asarray(m.predict(oos[KEEP]), dtype=np.float64)
        parts.append(o)
        LOG.info("cut %s done %.0fs", c, time.time() - t0)
    P = pd.concat(parts, ignore_index=True)
    P.to_parquet(f"{OUT}/{TAG}_pred.parquet", index=False)
    res = {"tag": TAG, "device": DEV, "rows": int(len(P)), "seeds": SEEDS}
    for s in SEEDS:
        res[f"sha_p{s}"] = hashlib.sha256(
            np.ascontiguousarray(P[f"p{s}"].to_numpy()).tobytes()).hexdigest()
    if len(SEEDS) > 1:
        a, b = SEEDS[0], SEEDS[1]
        res["spearman_pooled_seedAB"] = float(
            spearmanr(P[f"p{a}"], P[f"p{b}"]).correlation)
        pt = [spearmanr(g[f"p{a}"], g[f"p{b}"]).correlation
              for _, g in P.groupby("ts") if len(g) > 4]
        res["spearman_pertick_mean_seedAB"] = float(np.nanmean(pt))
    res["elapsed_s"] = round(time.time() - t0, 1)
    LOG.info("RESULT %s", json.dumps(res))
    json.dump(res, open(f"{OUT}/{TAG}_predmeta.json", "w"), indent=1)


if __name__ == "__main__":
    main()
