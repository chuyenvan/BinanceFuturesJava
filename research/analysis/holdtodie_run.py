#!/usr/bin/env python3
"""HOLDTODIE runner — 2 arm H0/H1 (tat time-stop 168h tren nen G2+FLAT3), Kaggle, jar sim-jar-gdv2 (KHONG build).

Pre-reg: docs/prereg/PREREG_HOLDTODIE.md. Nen: profiles/g2_flat3.properties (dung prof_r4_kg0_k16_f015_g155 + 6 override).
Tat TS theo code: SIM_LOSER_TIME_STOP_HOURS=0 (guard `loserTsHours > 0` o SimulatorMarketLevelTicker1MStopLoss.java:1026).
Usage: python3 holdtodie_run.py submit   # hoac: wait / fetch
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks

BUNDLE, JAR_DS, END = "sim-x1-2021-bundle", "sim-jar-gdv2", "20251231"
SHA = "da56927a"
# Bundle khong chua prof_g2_flat3 -> dung prof_r4_kg0_k16_f015_g155 + 6 override = g2_flat3 (md5 650c386f).
PROFILE = "r4_kg0_k16_f015_g155"
BASE = {"SIM_GATE_ROLLING_MODE": "ratio", "SIM_GATE_ROLLING_DAYS": 90,
        "SIM_GATE_ROLLING_PCT": 0.999950829, "TS_GIVEBACK_RATIO": 1.0,
        "SIM_TS_MAX_GAP": 0.03, "SIM_TS_MAX_GAP_WEAK": 0.03}

ARMS = {
    "h0": dict(BASE),                                                  # control: y nguyen g2_flat3 (TS=168)
    "h1": dict(BASE, **{"SIM_LOSER_TIME_STOP_HOURS": 0}),              # hold-to-die: TAT TS
}


def tag_of(n):
    return "htd-" + n


def do_submit(names):
    refs = {}
    for n in names:
        refs[n] = ks.submit(tag_of(n), PROFILE, ARMS[n], bundle_ds=BUNDLE, jar_ds=JAR_DS,
                            sim_end_date=END, code_sha=SHA)
        print("SUBMIT %-3s -> %-28s overrides=%s" % (n, refs[n], json.dumps(ARMS[n])), flush=True)
    print("STATUS", ks.wait(list(refs.values())), flush=True)


def do_fetch(names):
    import hashlib
    for n in names:
        tag = tag_of(n)
        out = ks.fetch(tag)
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
