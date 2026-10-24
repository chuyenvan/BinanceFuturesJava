"""LIQX_S1: slim I_coin store for Step 2 (sym, T, I, r5) zstd -> S1/keep/icoin_YYYY.parquet."""
import os
import numpy as np
import pandas as pd
from common import S1, months

os.makedirs(S1 + "/keep", exist_ok=True)
for y in range(2022, 2026):
    fr = []
    for yy, m in months():
        if yy != y:
            continue
        g = pd.read_parquet(S1 + "/coin/%04d-%02d.parquet" % (yy, m), columns=["sym", "T", "I", "r5"])
        g["sym"] = g.sym.astype(str)
        fr.append(g)
    g = pd.concat(fr, ignore_index=True)
    g["sym"] = g.sym.astype("category")
    assert g["T"].dtype == np.int64
    g.to_parquet(S1 + "/keep/icoin_%d.parquet" % y, index=False, compression="zstd", compression_level=9)
    print(y, len(g), os.path.getsize(S1 + "/keep/icoin_%d.parquet" % y) // 2**20, "MB", flush=True)
