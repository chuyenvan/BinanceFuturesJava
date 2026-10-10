#!/usr/bin/env python3
"""HO4-P3 cong K-a/K-b: gop k/k_*.json (Vision vs ticker DEV) -> k_gate.json. Chi dem/ty le."""
import glob, json, logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
W = "/home/ubuntu/claude_master/1010/ho4"
T, per, nos, bad_days = {}, {}, set(), {}
for f in sorted(glob.glob(W + "/k/k_*.json")):
    d = json.load(open(f))
    t = d["totals"]
    per[d["window"][0]] = dict(both=t["both"], eq5=t["eq5_quote"], ref_only=t["ref_only"], vis_only=t["vis_only"], ref=t["ref"])
    for k in ("ref", "vis", "both", "eq5_quote", "ref_only", "vis_only"):
        T[k] = T.get(k, 0) + t[k]
    nos |= set(d.get("sym_no_vision", []))
    for day, v in d.get("byday_eq5", {}).items():
        if v < 0.9999:
            bad_days[day] = v
r = dict(prereg="ADDENDUM-5 31e3c9e7", totals=T, per_month=per, sym_no_vision=sorted(nos),
         Ka_frac=T["eq5_quote"] / max(1, T["both"]), Kb_frac_dev_only=T["ref_only"] / max(1, T["ref"]),
         vis_only_frac_of_ref=T["vis_only"] / max(1, T["ref"]), days_eq5_lt_0_9999=bad_days)
r["Ka_pass"] = r["Ka_frac"] >= 0.9999
r["Kb_pass"] = r["Kb_frac_dev_only"] <= 0.0001
json.dump(r, open(W + "/k_gate.json", "w"), indent=1)
logging.info("%s", json.dumps({k: v for k, v in r.items() if k not in ("per_month",)}))
