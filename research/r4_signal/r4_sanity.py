#!/usr/bin/env python3
"""R4: doi chieu dem B0 cua r4_count (multi_q, J=2048) voi R3 P1 (p1_r3.json A0 cells) va R3b (r3b_iso.json a0)."""
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("san")
c = json.load(open("/home/ubuntu/claude_master/res1109/r4_signal/screen/count.json"))
b = json.load(open("/home/ubuntu/claude_master/res1109/r3_gate/r3b_iso.json"))["a0"]
try:
    p1 = json.load(open("/home/ubuntu/claude_master/res1109/r3_gate/p1_r3.json"))["seeds"]
except Exception as e:  # noqa: BLE001
    p1 = {}
    log.info("p1 loi %s", e)
for s, v in c["b0_by_seed"].items():
    r4_22, r4_2325 = v[0], sum(v[1:])
    log.info("%s R4 y22 %d y2325 %d tot %d | R3b y22 %s y2325 %s | R3P1 A0 cells %s", s, r4_22, r4_2325, sum(v),
             b.get(s, {}).get("y22"), b.get(s, {}).get("y2325"), p1.get(s, {}).get("A0", {}).get("cells"))
