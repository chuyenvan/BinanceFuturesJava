#!/usr/bin/env python3
"""V1 engine validation: zero-fee random walk => traditional grid expected PnL ~ 0.
20 independent GBM paths (sigma 0.08%/min), 200k bars, no funding, no fees."""
import json
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g_sim  # noqa: E402

n = 200000
ts0 = 1638316800000
res = {0: [], 1: []}
for s in range(20):
    rng = np.random.default_rng(100 + s)
    r = rng.normal(0, 0.0008, n)
    c = 40000 * np.exp(np.cumsum(r))
    o = np.empty(n); o[0] = 40000; o[1:] = c[:-1]
    h = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.0005, n)))
    l = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.0005, n)))
    for mode in (0, 1):
        _, eq, _ = g_sim.run(o, h, l, c, ts0, 0, 0, n, mode, 0, False, 0.0, 0.0, 1.0)
        res[mode].append(float(eq[-1] - 1))
out = {("range" if k == 0 else "dyn_g"): {"mean": float(np.mean(v)), "median": float(np.median(v)),
                                           "frac_pos": float(np.mean(np.array(v) > 0)), "n": len(v)}
       for k, v in res.items()}
out["note"] = "139 ngay, 20 duong GBM doc lap, phi=0, funding=0"
print(json.dumps(out, indent=1))
json.dump(out, open(os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/grid_t1/validate.json"), "w"), indent=1)
