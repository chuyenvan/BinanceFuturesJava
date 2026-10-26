#!/usr/bin/env python3
"""NUP validate V1-V5 (nhung phan do duoc)."""
import json
import os
import subprocess
import sys

import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
KS = "/home/ubuntu/kaggle_sim/out/"
OUTD = REPO + "/docs/result/nup"
JAR_OLD = "cc0f9d11ef6b865e9070e79b3111f6786ca7008a8c4a3a28571f54322e1b1dfe"
JAR_NEW = "ce4bcc17b824862d5f2b828d244dc7bb51dc6434420697d608b2196ea1012329"
EXP = {
    "a1": {"SIM_GATE_ROLLING_PCT"},
    "a2": {"SIM_GATE_ROLLING_PCT"},
    "a3": {"SELECTOR_RANK_TOPK"},
    "a4": {"SELECTOR_RANK_TOPK", "SIM_GATE_ROLLING_PCT"},
    "a5": {"SIM_GATE_DYN_SCALE"},
    "a6": {"SELECTOR_RANK_TOPK", "SIM_GATE_ROLLING_PCT", "SIM_F_BASE"},
    "a7": {"GATE_TIER2_ENABLED", "GATE_TIER2_PCT", "GATE_TIER2_U_MAX", "GATE_TIER2_CRASH_RET", "GATE_TIER2_SIZE_MULT"},
}


def props(tag):
    p = KS + tag + "/prof_run.properties"
    return {k: v for k, v in (ln.strip().split("=", 1) for ln in open(p) if "=" in ln)}


def main():
    rows = []
    for arm in EXP:
        for s in ["a1", "s7", "s21", "s99"]:
            t = "nup-%s-%s" % (arm, s)
            if not os.path.exists(KS + t + "/result.json"):
                continue
            rj = json.load(open(KS + t + "/result.json"))
            pr, pb = props(t), props("tsx-x14-" + s)
            diff = {k for k in set(pr) | set(pb) if pr.get(k) != pb.get(k)}
            rows.append(dict(tag=t, arm=arm, seed=s, java_rc=rj.get("java_rc"), ok=rj.get("ok"),
                             jar_ok=rj.get("jar_sha256") == (JAR_NEW if arm == "a7" else JAR_OLD),
                             diff=sorted(diff), diff_ok=diff == EXP[arm]))
    df = pd.DataFrame(rows)
    df.to_csv(OUTD + "/validate_v1.csv", index=False)
    print(df.to_string(index=False))
    print("V1 all ok:", bool(df.java_rc.eq(1).all() and df.ok.all() and df.jar_ok.all() and df.diff_ok.all()))
    # V2 quy = tong
    runs = pd.read_csv(OUTD + "/runs.csv")
    v2 = []
    for t, g in runs[runs.phase == "DEV"].groupby("tag"):
        q = g[(g.kind == "Q") & (g.period >= "2022")].pnl.sum()
        tot = g[g.period == "DEV_2022_25"].pnl.sum()
        v2.append(abs(q - tot))
    print("V2 max |sumQ - total| =", max(v2) if v2 else None)


if __name__ == "__main__":
    main()
