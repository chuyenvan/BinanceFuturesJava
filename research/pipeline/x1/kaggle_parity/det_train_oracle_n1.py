import argparse
import json
import os
import platform
import sys
import time

import numpy as np
import pandas as pd
import xgboost as xgb

print("=== ENV ===", flush=True)
print("python", sys.version, flush=True)
print("xgboost", xgb.__version__, flush=True)
print("pandas", pd.__version__, "numpy", np.__version__, flush=True)
print("platform", platform.platform(), flush=True)
print("cpu_count", os.cpu_count(), flush=True)

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True, help="output parquet path")
args = ap.parse_args()

H = 3600000
TZ = 7 * H
PURGE = 72 * H
KEEP9 = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d",
         "ret_14d", "ls_global", "rk_oi_delta24h"]
CUTS18 = ("20210701 20211001 20220101 20220401 20220701 20221001 20230101 20230401 "
          "20230701 20231001 20240101 20240401 20240701 20241001 20250101 20250401 "
          "20250701 20251001").split()


def cuts_to_ms(cut_days):
    return [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ for c in cut_days]


CUT_MS_18 = cuts_to_ms(CUTS18)

# DUNG Y HET file rut gon da dung cho Kaggle (dataset chuyendinh/s1-featv2-x1-20260919)
# de dam bao O1/O2/K1 doc CUNG mot input byte-for-byte, chi khac n_jobs.
LED_PATH = "/home/ubuntu/s1hpo/kaggle_ds/cand_dev_x1_lite.parquet"
FEAT_PATH = "/home/ubuntu/s1hpo/kaggle_ds/feat_v2_x1_keep9.parquet"
print("LED_PATH", LED_PATH, flush=True)
print("FEAT_PATH", FEAT_PATH, flush=True)

t0 = time.time()
D = pd.read_parquet(LED_PATH, columns=["ts", "sym", "g1lite"])
D = D[D.g1lite.notna()].copy()
print("pool", D.shape, flush=True)
D["med"] = D.groupby("ts").g1lite.transform("median")
D["rel"] = D.g1lite - D.med
D["rk"] = D.groupby("ts").rel.rank(pct=True, method="first")
D["rel5"] = np.minimum((D.rk * 5).astype(int), 4)
D["ts_h"] = (D.ts // H) * H

F = pd.read_parquet(FEAT_PATH, columns=["ts", "sym"] + KEEP9)
for c in KEEP9:
    if F[c].dtype == np.float64:
        F[c] = F[c].astype(np.float32)
D = D.merge(F.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
del F
print("join feat: co vol_7d", D.vol_7d.notna().mean().round(3), flush=True)
D["yr"] = pd.to_datetime(D.ts, unit="ms").dt.year
print("load done", round(time.time() - t0, 1), "sec", flush=True)


def make_model(random_state=42):
    return xgb.XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4,
                          learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                          min_child_weight=50, n_jobs=1, tree_method="hist",
                          random_state=random_state, lambdarank_pair_method="topk",
                          lambdarank_num_pair_per_sample=8)


def edge5_series(P):
    rk = P.groupby("ts").score.rank(method="first")
    top5 = P[rk <= 5]
    e = top5.groupby("ts").g1lite.mean() - P.groupby("ts").g1lite.mean()
    return e


t_start = time.time()
preds = []
fold_times = []
for i, c in enumerate(CUT_MS_18):
    tf0 = time.time()
    lo = c
    hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
    tr = D[D.ts < c - PURGE].sort_values("ts")
    oos = D[(D.ts >= lo) & (D.ts < hi)].sort_values("ts")
    if len(tr) < 5000 or len(oos) == 0:
        print("fold", i, CUTS18[i], "skip", flush=True)
        continue
    assert tr.ts.max() < c, "LEAK"
    qid = pd.factorize(tr.ts, sort=True)[0]
    m = make_model(random_state=42)
    m.fit(tr[KEEP9], tr.rel5, qid=qid)
    p = m.predict(oos[KEEP9])
    sc = -p
    rk = pd.Series(sc, index=oos.index).groupby(oos["ts"]).rank(method="first")
    o = oos[["ts", "sym", "g1lite", "yr"]].assign(score=rk.to_numpy(), fold=i)
    o["rk2"] = o.groupby("ts").score.rank(method="first")
    e = (o[o.rk2 <= 5].groupby("ts").g1lite.mean() - o.groupby("ts").g1lite.mean())
    tf1 = time.time()
    fold_times.append(tf1 - tf0)
    print(f"fold {i} {CUTS18[i]}: train {len(tr)} oos {len(oos)} ticks {oos.ts.nunique()} "
          f"edge5 {100*e.mean():+.3f}% time {tf1-tf0:.1f}s", flush=True)
    preds.append(o.drop(columns=["rk2"]))

t_total = time.time() - t_start
P = pd.concat(preds, ignore_index=True)
E = edge5_series(P)
yr = pd.to_datetime(E.index, unit="ms").year
print(f"=== baseline18_oracle_n1: edge5 all {100*E.mean():+.4f}% ticks {len(E)} "
      f"total_train_time {t_total:.1f}s ===", flush=True)
for _y in sorted(set(yr.tolist())):
    _e = E[yr == _y]
    print(f"  {_y}: edge5 {100*_e.mean():+.4f}% ticks {len(_e)}", flush=True)

P[["ts", "sym", "score", "fold"]].to_parquet(args.out)

summary = dict(
    xgboost_version=xgb.__version__,
    pandas_version=pd.__version__,
    numpy_version=np.__version__,
    python_version=sys.version,
    platform=platform.platform(),
    cpu_count=os.cpu_count(),
    n_folds_trained=len(preds),
    total_train_time_sec=t_total,
    fold_times_sec=fold_times,
    edge5_all_pct=float(100 * E.mean()),
    n_ticks=int(len(E)),
    edge5_by_year_pct={int(y): float(100 * E[yr == y].mean()) for y in sorted(set(yr.tolist()))},
    n_rows_pred=int(len(P)),
)
summary_path = args.out.replace(".parquet", "_summary.json")
with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2), flush=True)
print("DONE", flush=True)
