"""BENCH_DEVICE — do khac biet ket qua train giua 3 moi truong.

Chay duoc y het nhau o oracle_cpu / kaggle_cpu / kaggle_gpu.
Bien moi truong:
  BENCH_DEVICE  cpu | cuda        (mac dinh cpu)
  BENCH_SEEDS   "42,43,44"
  BENCH_NJOBS   so thread xgboost (mac dinh 4)
  BENCH_TAG     ten output
  BENCH_DATA    duong dan bench_s1.parquet (trong => tim trong /kaggle/input)
  BENCH_OUT     thu muc output (mac dinh /kaggle/working)
Moi hyperparam giu NGUYEN nhu research/analysis/seed_variance.py.
"""
import glob
import hashlib
import json
import logging
import os
import platform
import sys
import time

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("bench_device")

H = 3600000
TZ = 7 * H
PURGE = 72 * H
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d",
        "rk_ret_3d", "ret_14d", "ls_global", "rk_oi_delta24h"]
CUT_DAYS = ["20220101", "20220401", "20220701", "20221001", "20230101",
            "20230401", "20230701", "20231001", "20240101", "20240401"]

DEV = os.environ.get("BENCH_DEVICE", "cpu")
NJOBS = int(os.environ.get("BENCH_NJOBS", "4"))
SEEDS = [int(x) for x in os.environ.get("BENCH_SEEDS", "42,43,44").split(",")]
TAG = os.environ.get("BENCH_TAG", "bench")
OUT = os.environ.get("BENCH_OUT", "/kaggle/working")


def resolve_data():
    p = os.environ.get("BENCH_DATA", "")
    if p and os.path.exists(p):
        return p
    hits = sorted(glob.glob("/kaggle/input/**/bench_s1.parquet", recursive=True))
    assert hits, "khong tim thay bench_s1.parquet trong /kaggle/input"
    return hits[0]


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha_arr(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def mk(seed, n_est):
    kw = dict(objective="rank:ndcg", n_estimators=n_est, max_depth=4,
              learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
              min_child_weight=50, n_jobs=NJOBS, tree_method="hist",
              random_state=seed, lambdarank_pair_method="topk",
              lambdarank_num_pair_per_sample=8)
    if DEV == "cuda":
        kw["device"] = "cuda"
    return xgb.XGBRanker(**kw)


def run_seed(d, cuts, seed, meta):
    ics, edges = [], []
    for i, c in enumerate(cuts):
        lo = c
        hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
        tr = d[d.ts < c - PURGE].sort_values("ts", kind="mergesort")
        oos = d[(d.ts >= lo) & (d.ts < hi)].sort_values("ts", kind="mergesort")
        if len(tr) < 5000 or len(oos) == 0:
            continue
        assert tr.ts.max() < c, "LEAK"
        m = mk(seed, 300)
        m.fit(tr[KEEP], tr.rel5, qid=pd.factorize(tr.ts, sort=True)[0])
        if i == 0 and "booster_cfg" not in meta:
            cfg = json.loads(m.get_booster().save_config())["learner"]["generic_param"]
            meta["booster_cfg"] = cfg
            LOG.info("BOOSTER generic_param=%s", cfg)
        o = oos[["ts", "sym", "g1lite"]].assign(score=-m.predict(oos[KEEP]))
        for ts, g in o.groupby("ts"):
            if len(g) > 4:
                ics.append((ts, spearmanr(-g.score, g.g1lite).correlation))
        o["rk"] = o.groupby("ts").score.rank(method="first")
        edges.append(o[o.rk <= 5].groupby("ts").g1lite.mean()
                     - o.groupby("ts").g1lite.mean())
    return pd.Series(dict(ics)).dropna(), pd.concat(edges)


def first_tree(d, cuts, meta):
    """Bai test sach nhat: 1 cay duy nhat, seed 42, dump ra csv."""
    c = cuts[0]
    tr = d[d.ts < c - PURGE].sort_values("ts", kind="mergesort")
    m = mk(42, 1)
    m.fit(tr[KEEP], tr.rel5, qid=pd.factorize(tr.ts, sort=True)[0])
    t = m.get_booster().trees_to_dataframe()
    t.to_csv(f"{OUT}/{TAG}_tree1.csv", index=False)
    meta["tree1_rows"] = int(len(t))
    meta["tree1_sha"] = hashlib.sha256(
        t.to_csv(index=False).encode()).hexdigest()
    meta["tree1_train_rows"] = int(len(tr))
    LOG.info("TREE1 rows=%d sha=%s train_rows=%d",
             len(t), meta["tree1_sha"], len(tr))


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    meta = {"tag": TAG, "device": DEV, "n_jobs": NJOBS, "seeds": SEEDS}
    meta["xgboost"] = xgb.__version__
    meta["numpy"] = np.__version__
    meta["pandas"] = pd.__version__
    meta["python"] = platform.python_version()
    meta["machine"] = platform.machine()
    meta["processor"] = platform.processor()
    meta["cpu_count"] = os.cpu_count()
    meta["OMP_NUM_THREADS"] = os.environ.get("OMP_NUM_THREADS", "<unset>")
    p = resolve_data()
    meta["data_path"] = p
    meta["file_sha256"] = sha_file(p)
    d = pd.read_parquet(p)
    X = d[KEEP].to_numpy(dtype=np.float32)
    meta["X_sha256"] = sha_arr(X)
    meta["X_dtype"] = str(X.dtype)
    meta["X_shape"] = list(X.shape)
    meta["ts_sha256"] = sha_arr(d.ts.to_numpy(dtype=np.int64))
    meta["y_sha256"] = sha_arr(d.rel5.to_numpy(dtype=np.int8))
    meta["g_sha256"] = sha_arr(d.g1lite.to_numpy(dtype=np.float64))
    for k, v in meta.items():
        LOG.info("META %s = %s", k, v)
    cuts = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ
            for c in CUT_DAYS]
    first_tree(d, cuts, meta)
    ic_res, ed_res, per = {}, {}, {}
    for s in SEEDS:
        ic, e = run_seed(d, cuts, s, meta)
        ic_res[s] = ic
        ed_res[s] = e
        per[s] = {"mean_rank_ic": float(ic.mean()), "n_ticks": int(len(ic)),
                  "edge5_pct": float(100 * e.mean()),
                  "ic_sha256": sha_arr(ic.to_numpy(dtype=np.float64))}
        LOG.info("SEED %d | edge5 %+.4f%% | mean rankIC %+.6f | ticks %d | %.0fs",
                 s, 100 * e.mean(), ic.mean(), len(ic), time.time() - t0)
    M = pd.DataFrame(ic_res)
    M.index.name = "ts"
    M.columns = [str(c) for c in M.columns]
    M.to_parquet(f"{OUT}/{TAG}_ic.parquet")
    E = pd.DataFrame(ed_res)
    E.index.name = "ts"
    E.columns = [str(c) for c in E.columns]
    E.to_parquet(f"{OUT}/{TAG}_edge.parquet")
    meta["per_seed"] = per
    meta["elapsed_s"] = round(time.time() - t0, 1)
    with open(f"{OUT}/{TAG}_meta.json", "w") as f:
        json.dump(meta, f, indent=1, default=str)
    LOG.info("DONE %s in %.0fs -> %s", TAG, time.time() - t0, OUT)


if __name__ == "__main__":
    main()
