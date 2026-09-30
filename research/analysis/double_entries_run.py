#!/usr/bin/env python3
"""DOUBLE_ENTRIES runner — 6 arm P1..P6 (K x size tren nen G2+FLAT3), Kaggle, jar sim-jar-gdv2 (KHONG build).

Pre-reg: docs/prereg/PREREG_DOUBLE_ENTRIES.md. Nen: profiles/g2_flat3.properties.
Usage: python3 double_entries_run.py submit p1 p2 p3 p4 p5   # hoac: wait / fetch
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE, JAR_DS, END = "sim-x1-2021-bundle", "sim-jar-gdv2", "20251231"
SHA = "9188b063"
# Bundle sim-x1-2021-bundle KHONG chua prof_g2_flat3 -> DUNG prof_r4_kg0_k16_f015_g155 +
# 6 override = g2_flat3 (dung y trail2 flat3, da cho md5 650c386f). 6 key = diff 2 profile.
PROFILE = "r4_kg0_k16_f015_g155"
BASE = {"SIM_GATE_ROLLING_MODE": "ratio", "SIM_GATE_ROLLING_DAYS": 90,
        "SIM_GATE_ROLLING_PCT": 0.999950829, "TS_GIVEBACK_RATIO": 1.0,
        "SIM_TS_MAX_GAP": 0.03, "SIM_TS_MAX_GAP_WEAK": 0.03}

ARMS = {
    "p1": dict(BASE),                                                # parity anchor = y baseline
    "p2": dict(BASE, **{"SELECTOR_RANK_TOPK": 24, "SIM_F_BASE": 0.015}),
    "p3": dict(BASE, **{"SELECTOR_RANK_TOPK": 32, "SIM_F_BASE": 0.015}),
    "p4": dict(BASE, **{"SELECTOR_RANK_TOPK": 24, "SIM_F_BASE": 0.010}),
    "p5": dict(BASE, **{"SELECTOR_RANK_TOPK": 32, "SIM_F_BASE": 0.0075}),
    "p6": dict(BASE, **{"SELECTOR_RANK_TOPK": 16, "SIM_F_BASE": 0.010}),
}


def tag_of(n):
    return "de-" + n


def do_submit(names):
    refs = {}
    for n in names:
        tag = tag_of(n)
        refs[n] = ks.submit(tag, PROFILE, ARMS[n], bundle_ds=BUNDLE, jar_ds=JAR_DS,
                            sim_end_date=END, code_sha=SHA)
        print("SUBMIT %-3s -> %-28s overrides=%s" % (n, refs[n], json.dumps(ARMS[n])), flush=True)
    print("STATUS", ks.wait(list(refs.values())), flush=True)


def do_fetch(names):
    for n in names:
        tag = tag_of(n)
        out = ks.fetch(tag)
        import hashlib
        md5 = None
        if out["print_done"]:
            h = hashlib.md5()
            with open(out["print_done"], "rb") as f:
                for ch in iter(lambda: f.read(1 << 20), b""):
                    h.update(ch)
            md5 = h.hexdigest()
        print("FETCH %-3s md5=%s %s" % (n, md5, json.dumps(out["result"])), flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    names = sys.argv[2:] or list(ARMS)
    {"submit": do_submit, "fetch": do_fetch}[cmd](names)
