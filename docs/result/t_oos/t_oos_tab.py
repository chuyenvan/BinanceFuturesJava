#!/usr/bin/env python3
"""T_OOS: dung bang markdown tu t_oos_res.json (chi dinh dang, khong tinh them). Usage: python3 t_oos_tab.py dir"""
import json
import sys

d = sys.argv[1]
r = json.load(open(d + "/t_oos_res.json"))
L = []


def p(x):
    return "%+.1f%%" % (100 * x)


def row(name, m, sw=None, off=None):
    return "| %s | %s | %s | %s | %s → %s | %s | %s |" % (name, p(m["total"]), p(m["cagr"]), p(m["maxdd"]), m["peak_date"], m["trough_date"],
                                                          "" if sw is None else sw, "" if off is None else off)


def block(title, T, BH, sw, off):
    L.append("**%s**" % title)
    L.append("")
    L.append("| | tổng LN | CAGR | maxDD | đỉnh → đáy | số lần đổi | ngày OFF |")
    L.append("|---|---|---|---|---|---|---|")
    L.append(row("T", T, sw, off))
    L.append(row("B&H", BH))
    L.append("")


pr = r["primary"]
block("OOS primary 2018-01-01→2019-12-31", pr["T"], pr["BH"], pr["switches"], pr["off_days"])
L.append("C1 (|DD_T| ≤ 0,6×|DD_BH|): %s (tỷ lệ %.3f) · C2: %s · C3 (|DD_T| ≤ 40 %%): %s" % (pr["c1"], pr["dd_ratio"], pr["c2"], pr["c3"]))
L.append("")
L.append("Đợt ON (net phí):")
L.append("")
L.append("| # | vào | ra | LN đợt |")
L.append("|---|---|---|---|")
for i, e in enumerate(pr["episodes"], 1):
    L.append("| %d | %s | %s | %s |" % (i, e["entry"], e["exit"] or "(mở cuối kỳ, MTM)", p(e["ret"])))
L.append("")
L.append("Ngày đổi trạng thái:")
L.append("")
L.append("| ngày (close, UTC) | hành động | giá |")
L.append("|---|---|---|")
for t in pr["trades"]:
    L.append("| %s | %s | %.2f |" % (t["date"], t["action"], t["price"]))
L.append("")
gs = r["grid_summary"]
L.append("**Lưới 27 ô**: %d/27 đạt C1∧C2 (cần ≥ %d) · C1 %d · C2 %d · C3 %d" % (gs["n_c1c2"], gs["threshold_cells"], gs["n_c1"], gs["n_c2"], gs["n_c3"]))
L.append("")
for thr in (0.65, 0.70, 0.75):
    L.append("thr = %.2f (ô: LN T / DD T · C1C2C3 · số đổi; B&H %s / %s)" % (thr, p(pr["BH"]["total"]), p(pr["BH"]["maxdd"])))
    L.append("")
    L.append("| P \\ R | 20 | 30 | 40 |")
    L.append("|---|---|---|---|")
    for P in (120, 180, 240):
        cells = []
        for R in (20, 30, 40):
            g = [x for x in r["grid"] if x["thr"] == thr and x["P"] == P and x["R"] == R][0]
            cells.append("%s / %s · %s%s%s · %d" % (p(g["T_total"]), p(g["T_maxdd"]), "Đ" if g["c1"] else "x", "Đ" if g["c2"] else "x",
                                                    "Đ" if g["c3"] else "x", g["switches"]))
        L.append("| %d | %s |" % (P, " | ".join(cells)))
    L.append("")
s = r["secondary"]
a = s["from_2018_02_14"]
block("Phụ (a): cửa sổ từ 2018-02-14 (rebase, T thừa kế vị thế; ON tại đầu: %s)" % a["state_on_at_start"], a["T"], a["BH"], None, None)
L.append("C1 %s · C2 %s · C3 %s" % (a["c1"], a["c2"], a["c3"]))
L.append("")
w = s["warm_start"]
block("Phụ (b): warm-start liên tục từ 2017-08-17 (trạng thái tại t0: %s; %d lần đổi trước t0)" % (w["state_at_t0"], w["switches_before_t0"]), w["T"], w["BH"], w["switches"], w["off_days"])
L.append("C1 %s · C2 %s · C3 %s" % (w["c1"], w["c2"], w["c3"]))
L.append("")
L.append("Warm-start — ngày đổi trạng thái trong cửa sổ:")
L.append("")
L.append("| ngày | hành động | giá |")
L.append("|---|---|---|")
for t in w["trades"]:
    L.append("| %s | %s | %.2f |" % (t["date"], t["action"], t["price"]))
L.append("")
dv = r["dev"]
block("DEV 2021-06-30→2025-12-30 (giá USDT-M perp, cùng phí 0,15 %/chiều, sleeve đứng riêng)", dv["T"], dv["BH"], dv["switches"], dv["off_days"])
L.append("C1 %s · C2 %s · C3 %s · số đợt ON %d" % (dv["c1"], dv["c2"], dv["c3"], len(dv["episodes"])))
L.append("")
eps = [e["ret"] for e in dv["episodes"]]
L.append("DEV: đợt ON thắng %d / %d; LN đợt min %s, median %s, max %s" % (sum(1 for x in eps if x > 0), len(eps), p(min(eps)), p(sorted(eps)[len(eps) // 2]), p(max(eps))))
L.append("")
ep = [e["ret"] for e in pr["episodes"]]
L.append("OOS: đợt ON thắng %d / %d; LN đợt min %s, median %s, max %s" % (sum(1 for x in ep if x > 0), len(ep), p(min(ep)), p(sorted(ep)[len(ep) // 2]), p(max(ep))))
open(d + "/t_oos_tab.md", "w").write("\n".join(L) + "\n")
print("\n".join(L))
