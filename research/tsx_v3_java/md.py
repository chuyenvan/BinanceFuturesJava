#!/usr/bin/env python3
"""TSX_V3_JAVA - bang markdown tu dev.json / validate.json / ho.json / flags.json -> docs/result/tsx_v3_java/tables.md"""
import json
import logging
import os
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx3j_md")
D = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/tsx_v3_java"
ARMS = ["C420", "T25", "L45"]
YEARS = ["2021H2", "2022", "2023", "2024", "2025"]


def f(x, nd=2, sg=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    s = ("%+." if sg else "%.") + str(nd) + "f"
    return (s % x).replace(".", ",") if abs(x) < 1e15 else str(x)


def m3(v, nd=2, sg=True):
    return "%s [%s … %s]" % (f(v[0], nd, sg), f(v[1], nd, sg), f(v[2], nd, sg))


def med(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and np.isnan(x))]
    return [float(np.median(xs)), float(min(xs)), float(max(xs))] if xs else [float("nan")] * 3


def main():
    J = json.load(open(D + "/dev.json"))
    V = json.load(open(D + "/validate.json"))
    H = json.load(open(D + "/ho.json")) if os.path.exists(D + "/ho.json") else None
    FL = json.load(open(D + "/flags.json"))["arms"]
    o = []
    o.append("## Validate\n")
    o.append("- VA1 X14 TB 8 seed CAGR22 %s / DD22 %s (đích 39,49 / −22,55, ≤ 0,1pp) → %s; khớp mtm_vision max |Δ| %.1e" % (
        f(V["x14_cagr22_mean"], 3), f(V["x14_dd22_mean"], 3), V["VA1"], max(V["x14_vs_mtm_vision"].values())))
    va2 = V["VA2"]
    o.append("- VA2 md5 printDone DEV tsx2-ctl-a1 %s = tsx-x14-a1 %s; HO tsx2-ho-ctl-s7 %s = tsx-ho-x14-s7 %s → %s (tsx3-ctl-s13: %s)" % (
        va2["dev_md5_new"][:8], va2["dev_md5_old"][:8], va2["ho_md5_new"][:8], va2["ho_md5_old"][:8], V["VA2_ok"], va2["tsx3_ctl_s13"]))
    o.append("- VA3 cờ %s; VA4 MTM missing=0 & ΣPnL=printDone %s; VA5 cụm hoãn tái dựng = Java %s; parity VOID %s → ALL %s\n" % (
        V["VA3"], V["VA4"], V["VA5_ok"], V["bad"], V["ALL_OK"]))
    o.append("## DEV 2021H2–2025, 8 seed — X14 vs biến thể (median [min … max]; Δ = V − X14 cùng seed)\n")
    hdr = "| Chỉ số | X14 | " + " | ".join("%s (V)" % a for a in ARMS) + " | " + " | ".join("Δ %s" % a for a in ARMS) + " |"
    o.append(hdr)
    o.append("|" + "---|" * (2 + 2 * len(ARMS)))
    A = J["arms"]
    a0 = A[ARMS[0]]

    def row(name, get, nd=2):
        x14 = med([get(r, 0) for r in a0["rows"].values()])
        vs = [med([get(r, 1) for r in A[a]["rows"].values()]) for a in ARMS]
        ds = [med([get(r, 1) - get(r, 0) for r in A[a]["rows"].values()]) for a in ARMS]
        o.append("| %s | %s | %s | %s |" % (name, m3(x14, nd, False), " | ".join(m3(v, nd, False) for v in vs),
                                             " | ".join(m3(d, nd, True) for d in ds)))

    def P(k):
        return lambda r, i: r["period"]["DEV"][k][i]
    row("CAGR22 %", lambda r, i: r["cagr22"][i])
    row("ΣPnL", lambda r, i: r["sum_pnl"][i], 0)
    row("DD22 MTM phút %", lambda r, i: r["dd_mtm22"][i])
    row("DD toàn kỳ MTM %", lambda r, i: r["dd_mtm"][i])
    row("Calmar22", lambda r, i: r["calmar22"][i], 3)
    row("UW22 (ngày)", lambda r, i: r["uw_mtm22"][i], 0)
    row("win % leg 22–25", lambda r, i: r["win22"][i])
    row("win % cụm DEV", P("cl_win"))
    row("số cụm", P("n_cl"), 0)
    row("số đợt vào", P("n_batch"), 0)
    row("số leg", P("n_leg"), 0)
    row("khối lượng Σ notional (k)", lambda r, i: r["period"]["DEV"]["notional"][i] / 1e3, 0)
    row("phơi nhiễm TB %", P("exp_mean"))
    row("phơi nhiễm max %", P("exp_max"))
    row("giữ TB (h)", P("hold_mean"), 1)
    row("số cụm hoãn", lambda r, i: r["defer"]["n"][i], 0)
    row("giờ giữ thêm TB cụm hoãn", lambda r, i: r["defer"]["extra_h"][i], 1)
    row("PnL cụm hoãn", lambda r, i: r["defer"]["pnl"][i], 0)
    row("vốn giam TB mọi giờ %", lambda r, i: r["defer"]["locked"][i]["all_mean"])
    row("vốn giam TB giờ cờ ON %", lambda r, i: r["defer"]["locked"][i]["flag_mean"])
    row("vốn giam đỉnh %", lambda r, i: r["defer"]["locked"][i]["max"])
    row("giờ U ≥ 0,60", lambda r, i: r["umax"][i]["hours"], 0)
    o.append("")
    o.append("## Phân rã ΔΣPnL và đối chiếu từng đợt vào (median [min … max] 8 seed)\n")
    o.append("| | " + " | ".join(ARMS) + " |")
    o.append("|---|" + "---|" * len(ARMS))

    def r2(name, get, nd=0):
        o.append("| %s | %s |" % (name, " | ".join(m3(med([get(r) for r in A[a]["rows"].values()]), nd, True) for a in ARMS)))
    r2("ΔΣPnL", lambda r: r["sum_pnl"][2])
    r2("direct_sim (cụm hoãn khớp 2 run)", lambda r: r["dsim"]["direct"])
    r2("phần còn lại", lambda r: r["rest"])
    r2("direct replay (phaseB, dự đoán)", lambda r: r["direct_rep"])
    r2("sizing (lãi kép, DEEP)", lambda r: r["sizing"])
    r2("ΔΣPnL − direct replay", lambda r: r["sum_pnl"][2] - r["direct_rep"])
    r2("cụm hoãn khớp / hợp", lambda r: r["dsim"]["n_matched"])
    r2("đợt X14 BỎ ở V", lambda r: r["batch"]["drop"]["n"])
    r2("  – trong đợt cờ", lambda r: r["batch"]["drop"]["by_where"]["in"])
    r2("  – 15 ngày sau đợt", lambda r: r["batch"]["drop"]["by_where"]["after"])
    r2("  – ngoài", lambda r: r["batch"]["drop"]["by_where"]["out"])
    r2("  – Σ PnL X14 của đợt bỏ", lambda r: r["batch"]["drop"]["pnl_x"])
    r2("  – Σ notional X14 của đợt bỏ (k)", lambda r: r["batch"]["drop"]["notional_x"] / 1e3)
    r2("đợt THU NHỎ số mã", lambda r: r["batch"]["shrink_n"]["n"])
    r2("  – Δ số mã", lambda r: r["batch"]["shrink_n"]["d_sym"])
    r2("  – Δ PnL đợt (gồm khác biệt đường thoát)", lambda r: r["batch"]["shrink_n"]["d_pnl"])
    r2("đợt THU NHỎ size (< 0,99)", lambda r: r["batch"]["shrink_size"]["n"])
    r2("  – Δ notional (k)", lambda r: r["batch"]["shrink_size"]["d_notional"] / 1e3)
    r2("  – Δ PnL đợt (gồm khác biệt đường thoát)", lambda r: r["batch"]["shrink_size"]["d_pnl"])
    r2("đợt TO hơn (> 1,01)", lambda r: r["batch"]["bigger"]["n"])
    r2("đợt MỚI chỉ ở V", lambda r: r["batch"]["new"]["n"])
    r2("  – Σ PnL đợt mới", lambda r: r["batch"]["new"]["pnl_v"])
    r2("U tại t0 (median, đợt chung) V − X14 ×100", lambda r: 100 * (r["batch"]["U_at_t0_both"]["v_med"] - r["batch"]["U_at_t0_both"]["x_med"]), 2)
    r2("cụm hoãn mở tại t0 (TB) V − X14", lambda r: r["batch"]["open_def_both_mean"][1] - r["batch"]["open_def_both_mean"][0], 2)
    o.append("\nΔ PnL của đợt = Σ PnL cụm của đợt ở V − ở X14: gồm cả hiệu ứng size lẫn khác biệt đường thoát (cụm bị hoãn), không chỉ size.\n")
    o.append("## Theo năm (median 8 seed; Δ = V − X14)\n")
    o.append("| Arm | Năm | ΔPnL | ΔROI pp | ΔDD năm pp | Δcụm | Δđợt vào | Δleg | Δnotional % | Δwin pp | vốn giam TB X14→V % | đợt bỏ / mới |")
    o.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for a in ARMS:
        rows = A[a]["rows"].values()
        for y in YEARS:
            g = lambda k: med([r["period"][y][k][1] - r["period"][y][k][0] for r in rows])[0]  # noqa: E731
            yy = 2021 if y == "2021H2" else int(y)
            lx = med([r["defer"]["locked"][0]["by_year_mean"].get(str(yy), r["defer"]["locked"][0]["by_year_mean"].get(yy, np.nan)) for r in rows])[0]
            lv = med([r["defer"]["locked"][1]["by_year_mean"].get(str(yy), r["defer"]["locked"][1]["by_year_mean"].get(yy, np.nan)) for r in rows])[0]
            nt = med([100 * (r["period"][y]["notional"][1] / r["period"][y]["notional"][0] - 1) for r in rows])[0]
            bd = med([r["batch"]["drop"]["by_year"][y] for r in rows])[0]
            bn = med([r["batch"]["new"]["by_year"][y] for r in rows])[0]
            o.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s → %s | %s / %s |" % (
                a, y, f(g("pnl"), 0, True), f(g("roi"), 2, True), f(g("dd"), 2, True), f(g("n_cl"), 0, True), f(g("n_batch"), 0, True),
                f(g("n_leg"), 0, True), f(nt, 2, True), f(g("win"), 2, True), f(lx, 2), f(lv, 2), f(bd, 0), f(bn, 0)))
    o.append("\n## Luật (PREREG_TSX_V3_JAVA §5) + minh bạch luật TSX_V2_SIM / TSX_V3\n")
    o.append("| Arm | R1 ΔCAGR22>0 8/8 | R2 DD22 tệ nhất ≥ X14−1pp | R3 ΔCalmar≥0 ≥6/8 | R4 đợt vào TB ≥ −2 % | R5 direct_sim LOO > 0 | ỨNG VIÊN | ΔCalmar med | TSX_V2_SIM | TSX_V3 |")
    o.append("|---|---|---|---|---|---|---|---|---|---|")
    for a in ARMS:
        R = A[a]["rule"]
        O = A[a]["other_rules"]
        o.append("| %s | %d/8 %s | %s vs %s %s | %d/8 %s | %s %% %s | %s (bỏ %s: %s; TB %s; seed>0 %d/8) %s | **%s** | %s | %s | %s |" % (
            a, R["R1"]["n_pos"], "✓" if R["R1"]["ok"] else "✗", f(R["R2"]["worst_v"]), f(R["R2"]["worst_x14"]), "✓" if R["R2"]["ok"] else "✗",
            R["R3"]["n_ge0"], "✓" if R["R3"]["ok"] else "✗", f(100 * R["R4"]["mean"], 2, True), "✓" if R["R4"]["ok"] else "✗",
            f(R["R5"]["loo"], 0, True), R["R5"]["e_star"], f(R["R5"]["dsim_e_star"], 0, True), f(R["R5"]["dsim_mean"], 0, True),
            R["R5"]["n_seed_pos"], "✓" if R["R5"]["ok"] else "✗", "CÓ" if R["candidate"] else "KHÔNG", f(R["dcal_median"], 3, True),
            "ứng viên" if O["TSX_V2_SIM"]["candidate"] else "không (%s)" % ",".join(k for k in ("C1", "C2", "C3", "C4", "C5") if not O["TSX_V2_SIM"][k]),
            "ứng viên" if O["TSX_V3"]["candidate"] else "không (%s)" % ",".join(k for k in ("i", "ii", "iii", "iv") if not O["TSX_V3"][k])))
    o.append("\nỨng viên: %s → chọn %s\n" % (J["candidates"], J["pick"]))
    o.append("## direct_sim theo đợt cờ (TB 8 seed; 6 đợt |đóng góp| lớn nhất)\n")
    for a in ARMS:
        e = A[a]["agg"]["dsim_ep_mean"]
        top = sorted(e.items(), key=lambda t: -abs(t[1]))[:6]
        o.append("- %s: %s" % (a, "; ".join("%s %s" % (k, f(v, 0, True)) for k, v in top)))
    o.append("\n## Theo seed (DEV)\n")
    o.append("| Arm | seed | ΔCAGR22 | DD22 X14→V | ΔCalmar22 | ΔPnL | direct_sim | còn lại | đợt vào X14→V | Δleg | Δnotional % | vốn giam TB X14→V | bỏ/nhỏ số/nhỏ size/mới |")
    o.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for a in ARMS:
        for s, r in A[a]["rows"].items():
            Pp, b = r["period"]["DEV"], r["batch"]
            o.append("| %s | %s | %s | %s → %s | %s | %s | %s | %s | %d → %d | %s | %s | %s → %s | %d/%d/%d/%d |" % (
                a, s, f(r["cagr22"][2], 2, True), f(r["dd_mtm22"][0]), f(r["dd_mtm22"][1]), f(r["calmar22"][2], 3, True),
                f(r["sum_pnl"][2], 0, True), f(r["dsim"]["direct"], 0, True), f(r["rest"], 0, True), Pp["n_batch"][0], Pp["n_batch"][1],
                f(Pp["n_leg"][1] - Pp["n_leg"][0], 0, True), f(100 * (Pp["notional"][1] / Pp["notional"][0] - 1), 2, True),
                f(r["defer"]["locked"][0]["all_mean"]), f(r["defer"]["locked"][1]["all_mean"]), b["drop"]["n"], b["shrink_n"]["n"],
                b["shrink_size"]["n"], b["new"]["n"]))
    if H:
        o.append("\n## HO 2026 W9 — CHỈ MÔ TẢ (8 seed; Δ = V − X14)\n")
        o.append("| Arm | n | ΔPnL | ΔPnL ≥ 0 | ΔROI pp | ΔmaxDD pp | maxDD tệ nhất X14 → V | ROI X14 → V (median) | cụm hoãn X14 → V | Δ số leg |")
        o.append("|---|---|---|---|---|---|---|---|---|---|")
        for a in ARMS:
            g = H["arms"][a]["agg"]
            o.append("| %s | %d | %s | %d/8 | %s | %s | %s → %s | %s → %s | %s → %s | %s |" % (
                a, g["n"], m3(g["dPnL"], 0), g["n_ge0"], m3(g["dROI"]), m3(g["dMaxDD"]), f(g["worst_dd"][0]), f(g["worst_dd"][1]),
                f(g["roi_x14"][0]), f(g["roi_v"][0]), f(g["defer"][0][0], 0), f(g["defer"][1][0], 0), m3(g["dN"], 0)))
        o.append("\nVOID HO: %s; kiểm X14 HO tái lập max |Δ| %.1e\n" % (H["void"], max(H["check_x14"].values())))
    o.append("## Cờ (ngày ON)\n")
    o.append("| Arm | DEV | 2021H2 | 2022 | 2023 | 2024 | 2025 | HO 2026 |")
    o.append("|---|---|---|---|---|---|---|---|")
    for a in ["X14"] + ARMS:
        by = FL[a]["dev"]["by_year"]
        o.append("| %s | %d | %s | %s | %s | %s | %s | %d |" % (a, FL[a]["dev"]["n_days"], by.get("2021"), by.get("2022"), by.get("2023"),
                                                             by.get("2024"), by.get("2025"), FL[a]["ho"]["n_days"]))
    open(D + "/tables.md", "w").write("\n".join(o) + "\n")
    log.info("WROTE %s/tables.md (%d dong)", D, len(o))


if __name__ == "__main__":
    main()
