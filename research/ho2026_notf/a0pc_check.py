#!/usr/bin/env python3
"""A0'(c) — so ket qua kernel `a0p3-chain-y26nox` (chain voi X = rong) voi `ho4p1-chain-y26` goc.

PASS  ⇔ moi steps.pred[seed].md5 trung ban goc (seed 42 la tieu chi chinh; 7 va 8 seed la kiem them).
Kiem phu: MANIFEST (md5 tung file) trung ban goc.

argv: a0pc_check.py <new_result.json> [orig_result.json]
"""
import json
import sys

NEW = sys.argv[1]
ORIG = sys.argv[2] if len(sys.argv) > 2 else "/home/ubuntu/claude_master/1011/ho4p1/kaggle/out/ho4p1-chain-y26/result.json"
n = json.load(open(NEW))
o = json.load(open(ORIG))
pn, po = n["steps"]["pred"], o["steps"]["pred"]
print("%-6s %-34s %-34s %s" % ("seed", "new md5", "orig md5", "khop"))
bad = []
for s in sorted(po, key=int):
    a, b = pn.get(s, {}).get("md5"), po[s]["md5"]
    ok = a == b
    if not ok:
        bad.append(s)
    print("%-6s %-34s %-34s %s" % (s, a, b, "OK" if ok else "LECH"))
print("\nseed 42:", "PASS" if pn.get("42", {}).get("md5") == po["42"]["md5"] else "FAIL")
print("so seed lech:", len(bad), bad)
# manifest
mn, mo = n.get("manifest") or {}, o.get("manifest") or {}
keys = sorted(set(mo) | set(mn))
diff = [k for k in keys if (mn.get(k) or {}).get("md5") != (mo.get(k) or {}).get("md5")]
print("MANIFEST: %d file goc, %d file moi, %d lech md5" % (len(mo), len(mn), len(diff)))
for k in diff[:10]:
    print("  LECH", k, (mn.get(k) or {}).get("md5"), (mo.get(k) or {}).get("md5"))
print("dup_ids new:", n.get("dup_ids"), "| orig:", o.get("dup_ids"))
print("exclude_ids_n new:", n.get("exclude_ids_n", "n/a"))
print("secs new:", n.get("secs"))
print("\nKET_LUAN A0'(c):", "PASS" if (not bad and not diff) else "FAIL")
