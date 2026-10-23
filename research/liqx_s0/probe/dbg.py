import pandas as pd, numpy as np, sys, os
sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/liqx_s0"))
from score import proxies
G = proxies(pd.read_parquet(os.path.expanduser("~/claude_master/liqx_wk/buckets_AB.parquet")))
A = G[G.valid & (G["sample"] == "A") & (G.r5 < -0.01)]
c = A.groupby("day").size(); c.index = pd.to_datetime(c.index, unit="ms").date
print(c.cumsum().to_string())
log = open(os.path.expanduser("~/claude_master/liqx_wk/v2.log")).read().split("\n")
print(log[:25])
