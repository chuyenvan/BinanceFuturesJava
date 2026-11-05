#!/usr/bin/env python3
"""test G-MICRO (ADD11): dem SACH, XAM restart khong pha chuoi, TRUOT dung, (ii) can ngay r4q tron + smoke."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gmicro as G  # noqa: E402

S = lambda jar="r4n", sw=False: {"ket_luan": "DAT", "ngay_sach": "SACH", "jar": jar, "swap_day": sw}
X = lambda jar="r4n", sw=False: {"ket_luan": "XAM", "ngay_sach": "KHONG SACH (no_restart)", "jar": jar, "swap_day": sw}
ok = []
# 1. 2 ngay r4n SACH, swap XAM, 5 ngay r4q SACH, smoke ok => DAT (7 SACH, 11-03 khong tinh)
d = {"2026-11-03": S(), "2026-11-04": S(), "2026-11-05": S(), "2026-11-06": X("r4q", True)}
d.update({"2026-11-%02d" % k: S("r4q") for k in range(7, 12)})
r = G.count(d, True); ok.append(r["G_MICRO"] == "DAT" and r["n_sach"] == 7 and r["sach"][-1] == "2026-11-11")
# 2. smoke chua do => chua du
ok.append(G.count(d, None)["G_MICRO"].startswith("CHUA DU"))
# 3. TRUOT 11-08 => DUNG, khong dem tiep
d3 = dict(d); d3["2026-11-08"] = {"ket_luan": "TRUOT", "ngay_sach": "SACH", "jar": "r4q"}
r3 = G.count(d3, True); ok.append(r3["G_MICRO"].startswith("DUNG") and r3["n_sach"] == 3)
# 4. ngay swap SACH khong tinh la "r4q tron" ; chi co r4n SACH => (ii) false
d4 = {"2026-11-%02d" % k: S() for k in range(4, 11)}
d4["2026-11-11"] = dict(S("r4q", True))
r4 = G.count(d4, True); ok.append(r4["i"] and not r4["ii"] and r4["r4q_sach_tron"] == [])
# 5. XAM ly do khac khong tinh, khong pha
d5 = dict(d); d5["2026-11-09"] = {"ket_luan": "XAM", "ngay_sach": "SACH", "jar": "r4q"}
r5 = G.count(d5, True); ok.append(r5["n_sach"] == 6 and "2026-11-09" in r5["khong_tinh"] and not r5["dung_vi_truot"])
print("cases", ok)
print("TEST_GMICRO", "PASS" if all(ok) else "FAIL")
