#!/usr/bin/env python3
"""MTM cho cac tag moi, GOP vao eq_parquet.npz san co (khong xoa tag cu).
Usage: python3 mtm_merge.py <tag...>
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
    f = W + "/eq_parquet.npz"
    d = {}
    if __import__("os").path.exists(f):
        z = np.load(f)
        d = {k: z[k] for k in z.files}
    for k, v in out.items():
        d[k] = v
        d[k + "__m0"] = np.array([0], np.int64)
    np.savez(f, **d)
    json.dump(dict(missing=miss, n_new=len(tags), tags_new=tags, total=len([k for k in d if not k.endswith("__m0")])),
              open(W + "/mtm_merge.json", "w"), indent=1)
    print("saved", len(out), "missing", miss, "total", len([k for k in d if not k.endswith("__m0")]))
