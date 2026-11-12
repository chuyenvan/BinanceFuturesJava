"""R4_SIGNAL_SCREEN kernel fwd (prereg PREREG_R4_SIGNAL_SCREEN 5db738e2 §4) — logic y research/gate_smart/s4k.py.
Input: dataset r4s-cells (r4s_cells.parquet: ts, sym), vz-kline1m-2021..2026. Output /kaggle/working/r4s_fwd.parquet (c0,c24,c72)."""
import glob
import json
import logging
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("r4sk")
M1, H24, H72 = 60000, 86400000, 3 * 86400000
cp = glob.glob("/kaggle/input/**/r4s_cells.parquet", recursive=True)
assert cp, "thieu r4s_cells"
X = pd.read_parquet(cp[0])
F = {}
for p in glob.glob("/kaggle/input/**/kline1m-*.parquet", recursive=True):
    F[p.split("kline1m-")[-1][:7]] = p
log.info("cells %d months %d %s..%s", len(X), len(F), min(F), max(F))
X["ym"] = pd.to_datetime(X.ts, unit="ms").dt.strftime("%Y-%m")
out = []
t0 = time.time()
for ym, g in X.groupby("ym"):
    y, m = int(ym[:4]), int(ym[5:])
    nx = "%04d-%02d" % (y + (m == 12), 1 if m == 12 else m + 1)
    syms = sorted(g.sym.unique())
    parts = []
    for k in (ym, nx):
        if k in F:
            parts.append(pq.read_table(F[k], columns=["ts", "sym", "close"], filters=[("sym", "in", syms)]).to_pandas())
    K = pd.concat(parts, ignore_index=True).drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"])
    idx = {s: (d.ts.to_numpy(np.int64), d.close.to_numpy(np.float64)) for s, d in K.groupby("sym")}
    res = {"c0": [], "c24": [], "c72": []}
    for s, t in zip(g.sym.tolist(), g.ts.tolist()):
        tt, cc = idx.get(s, (np.zeros(0, np.int64), np.zeros(0)))
        for key, off in (("c0", M1), ("c24", M1 + H24), ("c72", M1 + H72)):
            j = np.searchsorted(tt, t + off, "right") - 1
            ok = j >= 0 and len(tt) and (t + off - tt[max(j, 0)]) <= 5 * M1
            res[key].append(cc[j] if ok else np.nan)
    gg = g.copy()
    for k, v in res.items():
        gg[k] = v
    out.append(gg)
    log.info("%s %d nan72 %d %ds", ym, len(g), int(np.isnan(gg.c72).sum()), round(time.time() - t0))
R = pd.concat(out, ignore_index=True)
R.to_parquet("/kaggle/working/r4s_fwd.parquet", index=False)
json.dump(dict(n=len(R), nan0=int(R.c0.isna().sum()), nan72=int(R.c72.isna().sum())), open("/kaggle/working/r4s_meta.json", "w"))
log.info("R4S_DONE %d", len(R))
