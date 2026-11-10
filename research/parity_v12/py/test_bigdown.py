#!/usr/bin/env python3
"""[ADD18/19] test BIG_DOWN-SEL (evaluate thuan) + gmicro ADD19 (jar cu co BIG_DOWN khong tinh, dich doc file)."""
import json
import os
import sys
import tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import day_bigdown as B  # noqa: E402
import gmicro as G  # noqa: E402

lines = [
    "10/11/2026 04:55:06.100 INFO [p] x: [LEGACY] managed 2: LEGAUSDT,LEGBUSDT",
    "10/11/2026 04:56:06.150 INFO [p] x: Market level change: 20261110 04:55 level: BIG_DOWN symbols:512",
    "10/11/2026 04:56:06.300 INFO [p] x: [BIG_DOWN-SEL] 20261110 04:55 level=BIG_DOWN n=2 pool=500 top=AUSDT=0.100000,CUSDT=0.120000",
]
ev, sel, leg = B.parse_log(lines)
ts = B.ms7("20261110 04:55")
leg_at = lambda t: leg[-1][1] if leg else set()
rows = [("LEGAUSDT", 0.05), ("AUSDT", 0.10), ("CUSDT", 0.12), ("DUSDT", 0.13)]
ok = []
nolock = lambda t: set()                                                                      # [ADD19 errata r4u3] chi loai coin c3 (da bo o p2)
r = B.evaluate(ev, sel, {ts: rows[1:]}, nolock); ok.append(r["status"] == "DAT")                   # 1 khop
r = B.evaluate(ev, sel, {ts: rows}, nolock); ok.append(r["status"] == "TRUOT")                     # 1b coin LEGACY KHONG duoc loai
sel_l = {k: dict(v, top=["LEGAUSDT", "AUSDT"]) for k, v in sel.items()}
r = B.evaluate(ev, sel_l, {ts: rows}, nolock); ok.append(r["status"] == "DAT")                     # 1c live chon ca coin LEGACY nhu sim
r = B.evaluate(ev, sel, {ts: [("AUSDT", 0.1), ("DUSDT", 0.11), ("CUSDT", 0.12)]}, nolock); ok.append(r["status"] == "TRUOT")   # 2 lech that
r = B.evaluate(ev, sel, {ts: [("AUSDT", 0.1), ("CUSDT", 0.12), ("DUSDT", 0.12)]}, nolock); ok.append(r["status"] in ("DAT", "XAM"))  # 3 hoa bien
r = B.evaluate(ev, sel, {ts: [("AUSDT", 0.1), ("DUSDT", 0.12), ("CUSDT", 0.1200000001)]}, nolock); ok.append(r["status"] == "XAM")  # 3b hoa bien lech
r = B.evaluate({}, {}, {}, nolock); ok.append(r["status"].startswith("KHONG AP DUNG"))                # 4 khong su kien
ev2, sel2, _ = B.parse_log(lines[:2]); r = B.evaluate(ev2, sel2, {ts: rows}, nolock); ok.append(r["status"] == "TRUOT")  # 5 thieu dong SEL
r = B.evaluate(ev, sel, {}, nolock); ok.append(r["status"] == "XAM")                                 # 6 KDD -> XAM
# gmicro ADD19
S = lambda jar, bd=0, sw=False: {"ket_luan": "DAT", "ngay_sach": "SACH", "jar": jar, "swap_day": sw, "bigdown_events": bd}
d = {"2026-11-07": S("r4t"), "2026-11-08": S("r4t", 1),
     "2026-11-10": {"ket_luan": "XAM", "ngay_sach": "KHONG SACH (no_restart)", "jar": "r4u", "swap_day": True}}
d.update({"2026-11-%02d" % k: S("r4u", 1) for k in range(11, 17)})
td = tempfile.mkdtemp()
json.dump({"target_jar": "r4u", "target_md5": "15f9e14f246f5667aade7a1647574384", "smoke_start_ms": 1}, open(td + "/gmicro_target.json", "w"))
ok.append(G.load_target(td) == ("r4u", "15f9e14f246f5667aade7a1647574384", 1))
g = G.count(d, True)
ok.append("2026-11-08" in g["khong_tinh"] and g["n_sach"] == 7 and g["ii"] and g["G_MICRO"] == "DAT")   # r4u co BIG_DOWN van tinh
ok.append(not G.count(d, True, md5_ok=False)["ii"])
print("cases", ok)
print("TEST_BIGDOWN", "PASS" if all(ok) else "FAIL")
