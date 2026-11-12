"""R1 PHA0 (chi doc): tim thu muc bins nao la nguon multiset P(win) cua map S1 (fold 20250101)."""
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("r1src")
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
FOLD = sys.argv[1]
MAP = "/home/ubuntu/predwf_map_s1a2_x1/predict_wf_%s.bin" % FOLD


def load(p):
    x = np.fromfile(p, dtype=REC)
    return pd.DataFrame({"ts": x["ts"].astype("i8"), "sym": x["sym"].astype("i2"), "p0": x["p0"].astype("f4")})


a = load(MAP)
a = a[np.isfinite(a.p0)]
for d in sys.argv[2:]:
    p = os.path.join(d, "predict_wf_%s.bin" % FOLD)
    if not os.path.exists(p):
        log.info("%s: khong co", d)
        continue
    b = load(p)
    b = b[np.isfinite(b.p0)]
    m = a.merge(b, on=["ts", "sym"], suffixes=("_m", "_c"))
    sa = m.sort_values(["ts", "p0_m"]).p0_m.values
    sb = m.sort_values(["ts", "p0_c"]).p0_c.values
    same_cell = float(np.mean(np.abs(m.p0_m.values - m.p0_c.values) <= 1e-6))
    log.info("%s: n_map=%d n_c=%d join=%d multiset_eq=%.4f cell_eq=%.4f", d, len(a), len(b), len(m),
             float(np.mean(np.abs(sa - sb) <= 1e-6)), same_cell)
