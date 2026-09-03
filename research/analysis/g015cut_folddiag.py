"""So per-fold rho: ban tai lap (full45) vs ban da deploy (p_old). Chan doan tai lap."""
import logging, numpy as np, pandas as pd
from scipy.stats import spearmanr
logging.basicConfig(level=logging.INFO, format="%(message)s")
L = logging.getLogger("fd")
TZ = 7 * 3600 * 1000
pool = pd.read_parquet("/home/ubuntu/g015/pool/pool_dev.parquet")
ts = pool.ts.to_numpy(np.int64)
y = pool.g1lite.to_numpy(np.float64)
po = pool.p_old.to_numpy(np.float64)
pf = np.load("/home/ubuntu/g015/out_g015-cut-a/pred_full45.npy").astype(np.float64)
pn = np.load("/home/ubuntu/g015/out_g015-cut-a/pred_no_oi.npy").astype(np.float64)
cuts = ["20220101", "20220401", "20220701", "20221001", "20230101",
        "20230401", "20230701", "20231001", "20240101", "20240401"]
cms = [int(pd.Timestamp("%s-%s-%s" % (c[:4], c[4:6], c[6:8]), tz="UTC").value // 10**6) - TZ
       for c in cuts]
L.info("%-10s %9s %8s %8s %8s %8s", "fold", "n", "p_old", "full45", "no_oi", "delta")
for i, c in enumerate(cms):
    hi = cms[i + 1] if i + 1 < len(cms) else int(ts.max()) + 1
    m = (ts >= c) & (ts < hi)
    a = spearmanr(po[m], y[m]).correlation
    b = spearmanr(pf[m], y[m]).correlation
    d = spearmanr(pn[m], y[m]).correlation
    L.info("%-10s %9d %8.4f %8.4f %8.4f %+8.4f", cuts[i], int(m.sum()), a, b, d, b - a)
L.info("%-10s %9d %8.4f %8.4f %8.4f %+8.4f", "TOAN POOL", len(ts),
       spearmanr(po, y).correlation, spearmanr(pf, y).correlation,
       spearmanr(pn, y).correlation,
       spearmanr(pf, y).correlation - spearmanr(po, y).correlation)
L.info("tuong quan spearman giua full45 va no_oi: %.5f",
       spearmanr(pf[::37], pn[::37]).correlation)
L.info("tuong quan spearman giua full45 va p_old: %.5f",
       spearmanr(pf[::37], po[::37]).correlation)
