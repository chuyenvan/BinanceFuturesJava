#!/usr/bin/env python3
"""FUNDNEG_T1 post-hoc DESCRIPTIVE (not criteria): tails, price-only component, funding contribution, by interval."""
import json, glob, os
import numpy as np, pandas as pd
OUTD = "/home/ubuntu/claude_master/fundneg_t1_wk/out"
T0, T1 = 1704067200000, 1767225600000
res = {}
for f in sorted(glob.glob(OUTD + "/trades_*.parquet")):
    nm = os.path.basename(f)[7:-8]
    x = pd.read_parquet(f)
    r = {}
    for per, m in [("DISC", x.tau < T0), ("TEST", (x.tau >= T0) & (x.tau < T1))]:
        y = x[m & ~x.overlap]
        n = y.net.values
        q = np.quantile(n, [0.01, 0.99])
        r[per] = dict(n=len(y), q=[float(v) for v in np.quantile(n, [0, .01, .05, .25, .5, .75, .95, .99, 1])],
                      trim1_mean=float(n[(n >= q[0]) & (n <= q[1])].mean()),
                      price_only_mean=float((y.gross - 0.003).mean()),
                      fund_mean=float(y.fund.mean()), fund_q=[float(v) for v in np.quantile(y.fund, [.05, .5, .95, 1])],
                      share_fund_pos=float((y.fund > 0).mean()),
                      by_interval={int(k): [int(len(g)), float(g.net.mean()), float(g.gross.mean()), float(g.fund.mean())] for k, g in y.groupby("interval_h")},
                      top10_net=[[s, float(v)] for s, v in y.nlargest(10, "net")[["sym", "net"]].values])
    r["n_ov_sym24"] = int(x.ov_sym24.sum()); r["n_ov_crashday"] = int(x.ov_crashday.sum()); r["n_overlap"] = int(x.overlap.sum())
    res[nm] = r
json.dump(res, open(OUTD + "/posthoc_desc.json", "w"), indent=1)
for nm, r in res.items():
    print(nm, "ov sym24/crash/any", r["n_ov_sym24"], r["n_ov_crashday"], r["n_overlap"])
    for per in ["DISC", "TEST"]:
        d = r[per]
        print(" ", per, "n", d["n"], "q", [round(v, 4) for v in d["q"]], "trim1 %.5f priceOnly %.5f fund %.5f fundq %s fund>0 %.2f" % (
            d["trim1_mean"], d["price_only_mean"], d["fund_mean"], [round(v, 4) for v in d["fund_q"]], d["share_fund_pos"]))
        print("    by_interval [n, net, gross, fund]", {k: [v[0]] + [round(z, 5) for z in v[1:]] for k, v in d["by_interval"].items()})
        print("    top10", [(s, round(v, 3)) for s, v in d["top10_net"]])
