#!/usr/bin/env python3
"""Tong hop T2a (ExitReplayDevMain toan bo ngay DEV seed tsx-x14-a1) -> t2a_summary.json."""
import collections
import glob
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("t2a")
B = "/home/ubuntu/claude_master/res1109/r1_s1/t2a"
rows = []
for f in sorted(glob.glob(B + "/day/*.json")):
    rows += json.load(open(f))
days = [x.strip() for x in open(B + "/days.txt")]
keys = ["legs", "legs_skipped", "decision_events", "decision_mismatch_symbols", "arms", "sl_moves", "time_stops", "defers",
        "trail_exit_both", "trail_exit_same_minute", "trail_exit_later", "trail_exit_only_paper", "trail_exit_only_live",
        "open_end_paper", "open_end_live", "open_state_diff"]
tot = {k: sum(r[k] for r in rows) for k in keys}
mm = [r for r in rows if r["decision_mismatch_symbols"] or r["trail_exit_only_paper"] or r["trail_exit_only_live"]
      or r["open_state_diff"] or r["trail_exit_later"]]
kinds = collections.Counter()
for r in mm:
    for m in r["mismatches"]:
        kinds[m.split(" ")[0][:40]] += 1
px = [r["mean_exit_px_diff_rel"] for r in rows if r["trail_exit_both"]]
out = dict(days_total=len(days), days_ok=len(rows), days_missing=sorted(set(days) - {r["date"] for r in rows}),
           totals=tot, mismatch_days=[dict(date=r["date"], n=r["decision_mismatch_symbols"], later=r["trail_exit_later"],
                                           only_paper=r["trail_exit_only_paper"], only_live=r["trail_exit_only_live"],
                                           open_diff=r["open_state_diff"], ex=r["mismatches"][:3]) for r in mm],
           mismatch_kinds=dict(kinds), mean_exit_px_diff_rel_avg=sum(px) / max(1, len(px)))
json.dump(out, open(B + "/../t2a_summary.json", "w"), indent=1)
log.info("days %d/%d missing=%s", len(rows), len(days), out["days_missing"][:10])
log.info("totals %s", tot)
log.info("mismatch days %d kinds %s", len(mm), dict(kinds))
for r in out["mismatch_days"][:12]:
    log.info("  %s", json.dumps(r)[:400])
