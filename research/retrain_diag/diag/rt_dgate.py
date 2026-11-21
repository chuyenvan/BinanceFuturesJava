#!/usr/bin/env python3
"""rt_dgate.py out.json lane=dir ... - D-gate (KHONG PnL): CHI doc dong '[GATE-RATIO] GATE-RATIO on' cuoi cua logs/sim.out.gz (so pass/seen theo quy).
HOLDOUT_UNSEAL_2026_1121 (U4a)."""
import gzip, json, re, sys
out = {}
for a in sys.argv[2:]:
    k, d = a.split("=", 1)
    last = None
    with gzip.open(d + "/logs/sim.out.gz", "rt", errors="replace") as f:
        for ln in f:
            if "GATE-RATIO on pct=" in ln:
                last = ln
    q = {m.group(1): [int(m.group(2)), int(m.group(3))] for m in re.finditer(r"(\d{4}Q\d):(\d+)/(\d+)", last)}
    tot = re.search(r"seen=(\d+) pass=(\d+)", last)
    out[k] = {"quarters": {x: q[x] for x in q if x >= "2025Q3"}, "seen": int(tot.group(1)), "pass": int(tot.group(2)),
              "rho_2026Q3": q["2026Q3"][0] / q["2026Q3"][1] if "2026Q3" in q else None}
json.dump(out, open(sys.argv[1], "w"), indent=1)
for k, v in out.items():
    print(k, v["pass"], v["quarters"], "rhoQ3=%.3g" % v["rho_2026Q3"])
