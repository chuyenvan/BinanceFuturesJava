#!/usr/bin/env python3
"""exec_v1diag2.py -- EXEC dieu tra V1 buoc 2: lech o phut bien hay mat du lieu? So tong qty/high/low theo DOAN phut lien tiep
(cung sym) va kiem lech open/close co bang gia print sat bien phut (+-1s) khong."""
import json
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import exec_measure as M  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("v1diag2")
D = pd.read_pickle(M.W + "/v1diag.pkl").sort_values(["sym", "m"]).reset_index(drop=True)
D["seg"] = ((D["sym"] != D["sym"].shift()) | (D["m"].diff() != M.MN)).cumsum()
D["qa"] = D["v"] + D["dv"]
S = D.groupby("seg").agg(v=("v", "sum"), qa=("qa", "sum"), n=("m", "size"), okm=("ok", "mean"))
S["okv"] = (S["qa"] - S["v"]).abs() <= 1e-6 * S["v"] + 1e-9
S["rv"] = (S["qa"] - S["v"]) / S["v"]
# o/c lech: gia agg open co nam trong cac print +-1s quanh bien phut khong?
bad = D[(D["do"] != 0) & D["do"].notna()].sample(n=min(400, int(((D["do"] != 0) & D["do"].notna()).sum())), random_state=1)
hit = []
for r in bad.itertuples():
    K = M.load_npz(M.W + "/kl/%sUSDT_*.npz" % r.sym, ("t", "x"))
    A = M.load_npz(M.W + "/agg/%sUSDT_*.npz" % r.sym, ("t", "p", "q", "m"))
    o = K["x"][np.searchsorted(K["t"], r.m), 0]
    i0, i1 = np.searchsorted(A["t"], r.m - 1000), np.searchsorted(A["t"], r.m + 1000)
    hit.append(bool(np.any(A["p"][i0:i1] == o)))
out = dict(n_seg=int(len(S)), seg_vol_ok=float(S["okv"].mean()), seg_rv_q=S["rv"].quantile([0.05, 0.5, 0.95]).round(7).to_dict(),
           seg_min_ok_mean=float(S["okm"].mean()), open_bad_in_pm1s=float(np.mean(hit)), n_open_bad_sample=len(hit))
with open(M.W + "/v1diag2.json", "w") as f:
    json.dump(out, f, indent=1)
log.info("V1DIAG2 %s", json.dumps(out))
