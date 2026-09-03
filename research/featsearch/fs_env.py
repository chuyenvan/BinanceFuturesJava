"""Kiem moi truong Oracle + tai lap S1 (keep9) doi chieu pred_s1a2 theo PREREG_FS muc 5."""
import logging, sys, os, time, json
import numpy as np, pandas as pd, xgboost as xgb
from scipy.stats import spearmanr
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
L = logging.getLogger(__name__)
L.info("xgboost %s numpy %s pandas %s nproc %s", xgb.__version__, np.__version__,
       pd.__version__, os.cpu_count())
L.info("loadavg %s", open("/proc/loadavg").read().strip())

H = 3600000
TZ = 7 * H
PURGE = 72 * H
BASE7 = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d"]
KEEP9 = BASE7 + ["ls_global", "rk_oi_delta24h"]
CUT_D = ["20220101", "20220401", "20220701", "20221001", "20230101",
         "20230401", "20230701", "20231001", "20240101", "20240401"]
CUT = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ for c in CUT_D]

D = pd.read_parquet("/home/ubuntu/fs/pack/fsdata.parquet")
assert D.ts.max() < 1719792000000
D["med"] = D.groupby("ts").g1lite.transform("median")
D["rel"] = D.g1lite - D.med
D["rkq"] = D.groupby("ts").rel.rank(pct=True, method="first")
D["rel5"] = np.minimum((D.rkq * 5).astype(int), 4)
t0 = time.time()
preds = []
for i, c in enumerate(CUT):
    hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
    tr = D[D.ts < c - PURGE].sort_values("ts")
    oos = D[(D.ts >= c) & (D.ts < hi)].sort_values("ts")
    assert tr.ts.max() < c, "LEAK"
    m = xgb.XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4,
                      learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                      min_child_weight=50, n_jobs=4, tree_method="hist",
                      random_state=42, lambdarank_pair_method="topk",
                      lambdarank_num_pair_per_sample=8)
    m.fit(tr[KEEP9], tr.rel5, qid=pd.factorize(tr.ts, sort=True)[0])
    preds.append(oos[["ts", "sym"]].assign(score=-m.predict(oos[KEEP9])))
    L.info("fold %d %s train=%d oos=%d %.0fs", i, CUT_D[i], len(tr), len(oos),
           time.time() - t0)
P = pd.concat(preds, ignore_index=True)
R = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2.parquet").rename(columns={"score": "ref"})
J = P.merge(R, on=["ts", "sym"], how="inner")
sp = spearmanr(J.score, J.ref).correlation
M = P.merge(D[["ts", "sym", "g1lite"]], on=["ts", "sym"], how="left")
M["rk"] = M.groupby("ts").score.rank(method="first")
e = (M[M.rk <= 5].groupby("ts").g1lite.mean() - M.groupby("ts").g1lite.mean()).mean()
L.info("REPRO n=%d spearman=%.6f edge5=%+.4f%% (goc +6.80%%) tong %.0fs",
       len(J), sp, 100 * e, time.time() - t0)
L.info("REPRO_PASS=%s", sp >= 0.999)
