#!/usr/bin/env python3
"""NUP2 Pha 2b: cham cac o factorial tu eq_parquet da keo ve.

Usage: python3 score_f2b.py            # doc plan_nup2c.json, lay tag nup2-c-*
Ghi: ~/claude_master/nup2_wk/runs.csv (append/thay rows cua chinh cac tag do)
     docs/result/nup2/runs_f2b.csv
Dung dung ham cua score.py (Q.build + rows_for) nhu mode p2b cua HANDOFF buoc 4.
"""
import json
import os
import sys

import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
WK = "/home/ubuntu/claude_master/nup2_wk"
OUTD = REPO + "/docs/result/nup2"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/golive_quarterly")
sys.path.insert(0, REPO + "/research/nup2")
import quarterly as Q  # noqa: E402
import score as S  # noqa: E402

S.WK = WK
S.OUTD = OUTD


def main():
    plan = json.load(open(WK + "/plan_nup2c.json"))
    tags = [e["tag"] for e in plan if e["tag"].startswith("nup2-c-")]
    tags = [t for t in tags if os.path.exists(S.KS + t + "/storage/printDone.csv")]
    print("tags", len(tags))
    rows = []
    for t, r in S.build_r(tags, "DEV").items():
        seed = t.rsplit("-", 1)[-1]
        rows += S.rows_for(r, "DEV", seed)
    D = pd.DataFrame(rows)
    D.to_csv(OUTD + "/runs_f2b.csv", index=False)
    old = pd.read_csv(WK + "/runs.csv")
    keep = old[~old.tag.isin(set(tags))]
    pd.concat([keep, D], ignore_index=True).to_csv(WK + "/runs.csv", index=False)
    print("rows", len(D), "-> runs.csv total", len(keep) + len(D))


if __name__ == "__main__":
    main()
