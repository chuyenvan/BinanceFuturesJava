#!/usr/bin/env python3
"""NUP2 validate V1/V2/V3/V5 (V4 rieng). Usage: python3 validate2.py <tag...>
Doc prof_run + result.json + printDone + log; in bang.
"""
import json
import os
import re
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
WK = "/home/ubuntu/claude_master/nup2_wk"
KS = "/home/ubuntu/kaggle_sim/out/"
J0 = "cc0f9d11ef6b865e9070e79b3111f6786ca7008a8c4a3a28571f54322e1b1dfe"
J7 = "ce4bcc17b824862d5f2b828d244dc7bb51dc6434420697d608b2196ea1012329"
OV = {
    "b1": {"SIM_F_BASE": "0.006305"},
    "b2": {"DCA_GRID_LEVELS": "-0.335,-0.5025,-0.603"},
    "b3": {"DCA_GRID_LEVELS": "-0.50,-0.60,-0.70,-0.80,-0.90", "DCA_GRID_WEIGHTS": "1,1,1,1,1,1"},
    "b4": {"SIM_U_MAX": "0.75"},
    "b5": {"SIM_MIN_MOMENTUM_15M": "0.005"},
    "a7": {"GATE_TIER2_ENABLED": "true", "GATE_TIER2_PCT": "0.99985", "GATE_TIER2_U_MAX": "0.2",
           "GATE_TIER2_CRASH_RET": "-0.01", "GATE_TIER2_SIZE_MULT": "0.5"},
}


def prof(tag):
    d = {}
    for ln in open(KS + tag + "/prof_run.properties"):
        if "=" in ln:
            k, v = ln.rstrip("\n").split("=", 1)
            d[k.strip()] = v.strip()
    return d


def b0_prof(seed):
    return prof("tsx-x14-" + seed.lower())


def arm_of(tag):
    if tag.startswith("nup2-c-"):
        return tag.split("-")[2], None
    m = re.match(r"nup-([a-z0-9]+)-(.+)$", tag)
    return m.group(1), m.group(2)


def expected(tag):
    arm, cell = arm_of(tag)
    if arm in OV:
        return OV[arm]
    fj = json.load(open(WK + "/factorial.json"))
    return {k: str(v) for k, v in fj["overrides"][arm].items()}


def main(tags):
    rows = []
    for t in tags:
        arm, seed = arm_of(t)
        if arm.startswith("b") or arm == "a7":
            seed = t.rsplit("-", 1)[-1]
        elif t.startswith("nup2-c-"):
            seed = t.rsplit("-", 1)[-1]
        else:
            seed = t.rsplit("-", 1)[-1]
        b = b0_prof(seed)
        p = prof(t)
        exp = expected(t)
        diff = {k: (b.get(k), p.get(k)) for k in set(b) | set(p) if b.get(k) != p.get(k)}
        extra = {k: v for k, v in diff.items() if k not in exp}
        wrong = {k: (v, exp[k]) for k, v in diff.items() if k in exp and str(v[1]) != exp[k]}
        rj = json.load(open(KS + t + "/result.json"))
        rows.append(dict(tag=t, java_rc=rj.get("java_rc"), ok=rj.get("ok"),
                         jar_ok=(rj.get("jar_sha256") == (J7 if arm == "a7" else J0)),
                         diff_keys=",".join(sorted(diff)), extra=",".join(sorted(extra)),
                         wrong=json.dumps(wrong) if wrong else "", secs=rj.get("secs"), n=rj.get("n_trades")))
    D = pd.DataFrame(rows)
    D.to_csv(WK + "/validate_v1.csv", index=False)
    print(D.to_string(index=False))
    print("V1", bool((D.java_rc == 1).all() and D.ok.all() and D.jar_ok.all() and (D.extra == "").all() and (D.wrong == "").all()))


if __name__ == "__main__":
    main(sys.argv[1:])
