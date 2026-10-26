#!/usr/bin/env python3
"""NUP2 DEV equity tu kline parquet (cung cong thuc ADDENDUM B).
Usage: python3 mtm_dev2.py <tag...>  -> nup2_wk/eq_parquet.npz + mtm_parquet.json
"""
import json
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/nup2")
import mtm_parquet as MP  # noqa: E402

W = "/home/ubuntu/claude_master/nup2_wk"
MP.W = W

if __name__ == "__main__":
    tags = sys.argv[1:]
    out, miss = MP.build(tags)
    np.savez(W + "/eq_parquet.npz", **out,
             **{k + "__m0": np.array([0], np.int64) for k in out})
    json.dump(dict(missing=miss, n=len(tags), tags=tags), open(W + "/mtm_parquet.json", "w"), indent=1)
    print("saved", len(out), "missing", miss)
