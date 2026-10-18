#!/usr/bin/env python3
"""ISO_RISK score lan 2 (addendum 1): MTM moi key bang nguon Vision (gvz_mtm), khong dung cache ticker.
P1: OFF Vision vs cache gqsf (bcd mtm.json, ticker) ; P2: missing."""
import argparse
import json
import logging
import sys

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402,F401  (patch R: nguon Vision) - PHAI import truoc

sys.path.insert(0, "/home/ubuntu/claude_master/iso")
import iso_risk_driver as I  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("isov")
B = I.B
OLD_BC = json.load(open(B.MTM_FILE))          # cache ticker cua BURST_COOLDOWN (OFF_s missing=0)
I.MTM_FILE = I.D + "/mtm_vision.json"
I.JSON_OUT = I.D + "/iso_risk_v.json"
B.MTM_FILE = "/nonexistent_bc_cache.json"      # cam tai dung cache ticker
import reset_rule_score as R  # noqa: E402
assert R._work is MT._work_vision, "R chua bi patch sang Vision"

a = argparse.Namespace(workers=3)
I.score(a)

raw = json.load(open(I.MTM_FILE))
okP1 = True
for s in I.SEEDS:
    k = "OFF_" + s
    v, c = raw[k]["legacy"], OLD_BC[k]["legacy"]
    d = abs(v["dd_total"] - c["dd_total"])
    log.info("P1 %s vision dd %.4f miss %d | cache dd %.4f miss %d | diff %.4f", k, v["dd_total"], v["missing"],
             c["dd_total"], c["missing"], d)
    okP1 &= d <= 0.05
offmiss = max(1, min(raw["OFF_" + s]["legacy"]["missing"] for s in I.SEEDS))
worst = sorted(((vv["legacy"]["missing"], k) for k, vv in raw.items()), reverse=True)[:5]
log.info("P1 %s ; missing top5 %s", "PASS" if okP1 else "FAIL", worst)
