"""BUOC 1 — dong bang du lieu benchmark cho bench_device.

Trich tu ledger/cand_dev.parquet + featv2/feat_v2.parquet dung y het load()
cua research/analysis/seed_variance.py, chi giu cot can, ep float32, ghi parquet.
In sha256 cua FILE va cua mang X sau khi load.
"""
import hashlib
import logging
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger(__name__)

H = 3600000
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d",
        "rk_ret_3d", "ret_14d", "ls_global", "rk_oi_delta24h"]
OUT = "/home/ubuntu/bench_device/bench_s1.parquet"


def main():
    d = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet")
    d = d[d.g1lite.notna()].copy()
    d["med"] = d.groupby("ts").g1lite.transform("median")
    d["rel"] = d.g1lite - d.med
    d["rk"] = d.groupby("ts").rel.rank(pct=True, method="first")
    d["rel5"] = np.minimum((d.rk * 5).astype(int), 4)
    d["ts_h"] = (d.ts // H) * H
    f = pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet")
    d = d.merge(f.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
    d = d.sort_values(["ts", "sym"], kind="mergesort").reset_index(drop=True)
    out = d[["ts", "sym", "rel5", "g1lite"] + KEEP].copy()
    out["ts"] = out.ts.astype("int64")
    out["sym"] = out.sym.astype(str)
    out["rel5"] = out.rel5.astype("int8")
    out["g1lite"] = out.g1lite.astype("float64")
    for c in KEEP:
        out[c] = out[c].astype("float32")
    out.to_parquet(OUT, index=False, compression="snappy")
    LOG.info("rows %d cols %d", len(out), out.shape[1])
    LOG.info("na per feat: %s", {c: int(out[c].isna().sum()) for c in KEEP})
    h = hashlib.sha256(open(OUT, "rb").read()).hexdigest()
    LOG.info("FILE_SHA256 %s", h)
    import os
    LOG.info("FILE_BYTES %d", os.path.getsize(OUT))
    b = pd.read_parquet(OUT)
    X = b[KEEP].to_numpy(dtype=np.float32)
    LOG.info("X_SHA256 %s", hashlib.sha256(np.ascontiguousarray(X).tobytes()).hexdigest())
    LOG.info("X_DTYPE %s X_SHAPE %s", X.dtype, X.shape)
    LOG.info("TS_SHA256 %s", hashlib.sha256(
        np.ascontiguousarray(b.ts.to_numpy(dtype=np.int64)).tobytes()).hexdigest())
    LOG.info("Y_SHA256 %s", hashlib.sha256(
        np.ascontiguousarray(b.rel5.to_numpy(dtype=np.int8)).tobytes()).hexdigest())
    LOG.info("G_SHA256 %s", hashlib.sha256(
        np.ascontiguousarray(b.g1lite.to_numpy(dtype=np.float64)).tobytes()).hexdigest())


if __name__ == "__main__":
    main()
