#!/usr/bin/env python3
"""R3: day 1 kernel MTM cho cac run R3 da COMPLETE (+ r3g0-a1 doi chung). Usage: r3_mtm.py <tag_mtm> <tag1> [tag2 ...]"""
import sys
sys.path.insert(0, "/home/ubuntu/claude_master/res1109/r3_gate/orch")
import r3_orch as O
st = O.load_state()
tag, runs = sys.argv[1], sys.argv[2:]
for t in runs:
    s = O.KS._status(O.KS.kernel_ref(t))
    assert s == "COMPLETE", (t, s)
if tag in st:
    O.log.error("MTM %s da co", tag); sys.exit(3)
running = O.account_running()
if running > 1:
    O.log.error("KHONG push MTM: account_running=%d", running); sys.exit(2)
O.push_mtm(st, dict(tag=tag, runs=runs))
