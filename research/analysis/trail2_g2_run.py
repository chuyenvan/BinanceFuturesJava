#!/usr/bin/env python3
"""TRAIL2_G2 runner: 5 arm (pure proportional vs pure flat) tren nen G2 arm 7%, Kaggle, jar sim-jar-gdv2 (KHONG build).
Pre-reg: docs/prereg/PREREG_TRAIL2_G2.md. Cach submit = trail_g2_run.py (vong 1)."""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE, JAR_DS, END = "sim-x1-2021-bundle", "sim-jar-gdv2", "20251231"
SHA = "2b4dcbd+cp1db0613"
PROFILE = "r4_kg0_k16_f015_g155"
G2 = {"SIM_GATE_ROLLING_MODE": "ratio", "SIM_GATE_ROLLING_DAYS": 90,
      "SIM_GATE_ROLLING_PCT": 0.999950829}


def exit_block(ratio, cap, cap_weak):
    return {"TS_GIVEBACK_RATIO": ratio, "SIM_TS_MAX_GAP": cap, "SIM_TS_MAX_GAP_WEAK": cap_weak}


ARMS = {
    "t0":     exit_block(0.5, 0.08, 0.03),
    "prop50": exit_block(0.5, 1.0, 1.0),
    "prop30": exit_block(0.3, 1.0, 1.0),
    "flat3":  exit_block(1.0, 0.03, 0.03),
    "flat5":  exit_block(1.0, 0.05, 0.05),
}


def main(names):
    refs = {}
    for n in names:
        ov = dict(G2)
        ov.update(ARMS[n])
        tag = "trail2-g2-" + n
        refs[n] = ks.submit(tag, PROFILE, ov, bundle_ds=BUNDLE, jar_ds=JAR_DS,
                            sim_end_date=END, code_sha=SHA)
        print("SUBMIT %-7s -> %s overrides=%s" % (n, refs[n], json.dumps(ov)), flush=True)
    print("STATUS", ks.wait(list(refs.values())), flush=True)
    for n in names:
        out = ks.fetch("trail2-g2-" + n)
        print("FETCH %-7s %s" % (n, json.dumps(out["result"])), flush=True)
        print("        printDone=%s" % out["print_done"], flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or list(ARMS))
