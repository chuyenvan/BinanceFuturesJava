#!/usr/bin/env python3
"""Tieu chi PASS buoc 2 (KLINE_FIX_242.md muc C) cho live_new/s1_new/s2_new .json. Exit 0 = PASS ca 3."""
import json, sys

ok_all, offs = True, set()
for p in sys.argv[1:]:
    j = json.load(open(p))
    an = j.get("analyse", {})
    q = (j.get("q_ratio_new_over_ref_30d_6h") or {})
    tl, tm = j.get("ticks_live") or 0, j.get("ticks_matched") or 0
    frac = tm / tl if tl else 0.0
    off = j.get("align_chosen_off_min")
    offs.add(off)
    chk = {"match>=0.99": frac >= 0.99, "armed": an.get("armed") is True,
           "first_ts_1001_1300": any(x in str(an.get("first_ts", "")) for x in ("2026-10-01 13:00", "20261001 13:00", "20261001-1300")),
           "q_p50_in[0.9,1.1]": q.get("p50") is not None and 0.9 <= q["p50"] <= 1.1}
    ok = all(chk.values())
    ok_all &= ok
    print("%s %s match=%.4f off=%s first=%s armed=%s q_now=%s q_ratio=%s %s" % (
        "PASS" if ok else "FAIL", p, frac, off, an.get("first_ts"), an.get("armed"), an.get("q_now"), q, chk))
if len(offs) != 1:
    print("FAIL align_chosen_off_min khac nhau giua cac dich: %s" % offs)
    ok_all = False
print("== BUOC 2 %s" % ("PASS" if ok_all else "FAIL — DUNG, giu buffer cu"))
sys.exit(0 if ok_all else 1)
