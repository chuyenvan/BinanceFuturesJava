"""R1 PHA0 (chi doc): so thu tu S1 (bins map) vs net015 raw (sel_models_net015) theo tick.
Kiem: cung (ts,sym), cung multiset p0 moi ts; do overlap top-24 / top-8 va Spearman trong tick, theo nam."""
import glob
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("r1ovl")
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
A, B = "/home/ubuntu/predwf_map_s1a2_x1", sys.argv[1]
log.info("map files=%s", sorted(os.path.basename(f) for f in glob.glob(A + "/predict_wf_*.bin")))
out = []
for fb in sorted(glob.glob(B + "/predict_wf_*.bin")):
    fa = os.path.join(A, os.path.basename(fb))
    if not os.path.exists(fa):
        log.info("thieu map %s", fa)
        continue
    a = pd.DataFrame(np.fromfile(fa, dtype=REC)[["ts", "sym", "p0"]].astype([("ts", "i8"), ("sym", "i2"), ("p0", "f4")]))
    b = pd.DataFrame(np.fromfile(fb, dtype=REC)[["ts", "sym", "p0"]].astype([("ts", "i8"), ("sym", "i2"), ("p0", "f4")]))
    a = a[np.isfinite(a.p0)]
    b = b[np.isfinite(b.p0)]
    m = a.merge(b, on=["ts", "sym"], suffixes=("_s1", "_net"), how="outer", indicator=True)
    both = (m["_merge"] == "both").mean()
    m = m[m["_merge"] == "both"].drop(columns="_merge")
    # multiset moi ts
    sa = m.sort_values(["ts", "p0_s1"]).p0_s1.values
    sb = m.sort_values(["ts", "p0_net"]).p0_net.values
    ms_eq = float(np.mean(np.abs(sa - sb) <= 1e-6))
    m["r_s1"] = m.groupby("ts").p0_s1.rank(method="first", ascending=False)
    m["r_net"] = m.groupby("ts").p0_net.rank(method="first", ascending=False)
    n_ts = m.ts.nunique()
    m["eq"] = np.abs(m.p0_s1.values - m.p0_net.values) <= 1e-6
    tick_ident = float(m.groupby("ts").eq.all().mean())
    g = m.groupby("ts")
    top = {}
    idt = m.groupby("ts").eq.transform("all")
    m2 = m[~idt]
    g2 = m2.groupby("ts")
    for k in (8, 24):
        inter = m[(m.r_s1 <= k) & (m.r_net <= k)].groupby("ts").size().reindex(g.size().index, fill_value=0)
        kk = np.minimum(g.size(), k)
        top[k] = float((inter / kk).mean())
        inter2 = m2[(m2.r_s1 <= k) & (m2.r_net <= k)].groupby("ts").size().reindex(g2.size().index, fill_value=0)
        top["n%d" % k] = float((inter2 / np.minimum(g2.size(), k)).mean()) if len(g2.size()) else float("nan")
    rng = np.random.default_rng(20261109)
    tss = m.ts.unique()
    samp = rng.choice(tss, size=min(400, len(tss)), replace=False)
    nid = m.groupby("ts").eq.all()
    samp = [t for t in samp if not nid.get(t, False)] or list(samp)
    sp = m[m.ts.isin(samp)].groupby("ts")[["r_s1", "r_net"]].corr(method="spearman").xs("r_s1", level=1)["r_net"]
    yr = pd.to_datetime(m.ts.median(), unit="ms").year
    out.append(dict(fold=os.path.basename(fb)[11:19], year=yr, n_ts=n_ts, pool_med=int(g.size().median()),
                    key_match=both, multiset_eq=ms_eq, tick_ident=tick_ident, ovl8=top[8], ovl24=top[24], ovl24_nonid=top["n24"], ovl8_nonid=top["n8"], spear_med=float(sp.median())))
    log.info("%s", out[-1])
df = pd.DataFrame(out)
log.info("\n%s", df.to_string(float_format=lambda v: "%.3f" % v))
log.info("\nTheo nam:\n%s", df.groupby("year")[["ovl8", "ovl24", "ovl8_nonid", "ovl24_nonid", "spear_med", "tick_ident", "pool_med"]].mean().to_string(float_format=lambda v: "%.3f" % v))
