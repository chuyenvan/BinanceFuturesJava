#!/usr/bin/env python3
"""TRAIL_G2 runner: 5 arm tren nen G2 (chi doi khoi exit), Kaggle, jar sim-jar-gdv2 (KHONG build).
Pre-reg: docs/prereg/PREREG_TRAIL_G2.md. Copy cach submit tu reset_rule_gdv2_run.py (g2)."""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE, JAR_DS, END = "sim-x1-2021-bundle", "sim-jar-gdv2", "20251231"
SHA = "2b4dcbd+cp1db0613"
PROFILE = "r4_kg0_k16_f015_g155"
G2 = {"SIM_GATE_ROLLING_MODE": "ratio", "SIM_GATE_ROLLING_DAYS": 90,
      "SIM_GATE_ROLLING_PCT": 0.999950829}
LAD = {"TS_LADDER": 1, "TS_LADDER_LO": "0.05,0.10,0.20", "TS_LADDER_GAPS": "0.02,0.04,0.08"}
ARMS = {
    "t0":    {},
    "a5":    {"SIM_RATE_PROFIT_STOP_MARKET": 0.05},
    "gv3":   {"TS_GIVEBACK_RATIO": 0.3},
    "lad":   dict(LAD),
    "a5lad": dict(LAD, SIM_RATE_PROFIT_STOP_MARKET=0.05),
}


def main(names):
    refs = {}
    for n in names:
        ov = dict(G2)
        ov.update(ARMS[n])
        tag = "trail-g2-" + n
        refs[n] = ks.submit(tag, PROFILE, ov, bundle_ds=BUNDLE, jar_ds=JAR_DS,
                            sim_end_date=END, code_sha=SHA)
        print("SUBMIT %-5s -> %s overrides=%s" % (n, refs[n], json.dumps(ov)), flush=True)
    print("STATUS", ks.wait(list(refs.values())), flush=True)
    for n in names:
        out = ks.fetch("trail-g2-" + n)
        print("FETCH %-5s %s" % (n, json.dumps(out["result"])), flush=True)
        print("      printDone=%s" % out["print_done"], flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or list(ARMS))
