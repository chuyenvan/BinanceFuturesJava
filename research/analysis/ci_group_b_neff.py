"""n hieu dung THAT cho nhom B: so khoi 72h co du lieu (khong phai so khoi cua ca doan)."""
import logging
import numpy as np, pandas as pd
from scipy.stats import spearmanr
logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/ci/ciB3.out", "w"),
                              logging.StreamHandler()])
L = logging.getLogger("b3")
H = 3600_000
C = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet",
                    columns=["ts", "sym", "gate_dyn_ok", "score_g015", "g1lite"])
P = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2.parquet")
R = pd.read_parquet("/home/ubuntu/ledger/path_labels.parquet",
                    columns=["ts", "sym", "g1_replay"])
M = C.merge(P, on=["ts", "sym"], how="inner").merge(R, on=["ts", "sym"], how="left")
M["gate_ok"] = M.gate_dyn_ok.astype(bool)
M = M.dropna(subset=["g1_replay"])
TS0 = M.ts.min()
OPEN, CLOSED = M[M.gate_ok], M[~M.gate_ok]
ics = {ts: 1 for ts, g in OPEN.groupby("ts") if len(g) >= 10
       and not np.isnan(spearmanr(-g.score.values, g.g1_replay.values).correlation)}


def nb(tsv, bh=72):
    return len(np.unique((np.asarray(tsv) - TS0) // (bh * H)))


d = OPEN.copy()
d["rk"] = d.groupby("ts").score.rank(ascending=True, method="first")
T8 = d[d.rk <= 8]
R8 = OPEN.sample(frac=1.0, random_state=0).groupby("ts").head(8)
dc = CLOSED.copy()
dc["rk"] = dc.groupby("ts").score.rank(ascending=True, method="first")
T8c = dc[dc.rk <= 8]
L.info("tong khoi 72h trong doan = %d", nb(M.ts.values))
L.info("#7  n_tick co IC = %d -> nam trong %d khoi 72h", len(ics), nb(list(ics)))
L.info("#8  top8 gate MO  n_row=%d n_tick=%d -> %d khoi 72h",
       len(T8), T8.ts.nunique(), nb(T8.ts.values))
L.info("#8  random8 MO    n_row=%d -> %d khoi 72h", len(R8), nb(R8.ts.values))
L.info("#9  top8 gate DONG n_row=%d n_tick=%d -> %d khoi 72h",
       len(T8c), T8c.ts.nunique(), nb(T8c.ts.values))
