#!/usr/bin/env python3
"""TSX_V2_SIM - sinh bang markdown tu sim.json (+ ho.json neu co) -> docs/result/tsx_v2_sim/tables.md (+ per_seed.csv)."""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx2md")
D = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/tsx_v2_sim"
J = json.load(open(D + "/" + (sys.argv[1] if len(sys.argv) > 1 else "sim.json")))
ARMS = list(J["arms"])
KEY_EP = [("LUNA", "2022-05"), ("FTX", "2022-11"), ("04/2024", "2024-04"), ("06/2024", "2024-06"), ("03/2025", "2025-03"),
          ("10-12/2025", "2025-10")]


def med(v):
    v = np.asarray([x for x in v if x is not None and not (isinstance(x, float) and np.isnan(x))], float)
    return (float(np.median(v)), float(v.min()), float(v.max())) if len(v) else (np.nan, np.nan, np.nan)


def f(x, nd=0, sign=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    s = format(float(x), ("+" if sign else "") + ",." + str(nd) + "f")
    return s.replace(",", " ").replace(".", ",")


def m3(v, nd=0, sign=False):
    a, b, c = med(v)
    return "%s [%s; %s]" % (f(a, nd, sign), f(b, nd, sign), f(c, nd, sign))


def ep_index(lab, ym):
    for i, e in enumerate(lab):
        a, b = e.split("..")
        if a[:7] <= ym <= b[:7]:
            return i
    return None


def main():
    out = []
    lab = J["episodes"]
    out.append("# TSX_V2_SIM — bảng (median [min; max] 8 seed; Δ = biến thể − X14 cùng seed)\n")
    out.append("## 1. Headline DEV\n")
    out.append("| Chỉ số | " + " | ".join(ARMS) + " |")
    out.append("|---|" + "---|" * len(ARMS))
    rows = [("X14 CAGR22 %", lambda r: r["cagr22"][0], 2, False), ("Biến thể CAGR22 %", lambda r: r["cagr22"][1], 2, False),
            ("ΔCAGR22 pp", lambda r: r["cagr22"][2], 2, True), ("ΔΣPnL USD", lambda r: r["sum_pnl"][2], 0, True),
            ("X14 DD22 %", lambda r: r["dd_mtm22"][0], 2, False), ("Biến thể DD22 %", lambda r: r["dd_mtm22"][1], 2, False),
            ("ΔDD22 pp", lambda r: r["dd_mtm22"][2], 2, True), ("ΔDD toàn kỳ pp", lambda r: r["dd_mtm"][2], 2, True),
            ("ΔCalmar22", lambda r: r["calmar22"][2], 3, True), ("ΔUW22 ngày", lambda r: r["uw_mtm22"][2], 1, True)]
    for name, fn, nd, sg in rows:
        out.append("| %s | %s |" % (name, " | ".join(m3([fn(r) for r in J["arms"][a]["rows"].values()], nd, sg) for a in ARMS)))
    out.append("| DD22 seed tệ nhất X14 → biến thể | %s |" % " | ".join(
        "%s → %s" % (f(J["arms"][a]["rule"]["C3"]["worst_x14"], 2), f(J["arms"][a]["rule"]["C3"]["worst_v"], 2)) for a in ARMS))
    out.append("| seed ΔCAGR22>0 / ΔCalmar22≥0 | %s |" % " | ".join(
        "%d/8 / %d/8" % (J["arms"][a]["rule"]["C1"]["n_pos"], J["arms"][a]["rule"]["C2"]["n_ge0"]) for a in ARMS))
    out.append("")
    out.append("## 2. Hoạt động DEV (2021-07..2025-12): X14 / biến thể / Δ (median)\n")
    out.append("| Chỉ số | " + " | ".join(ARMS) + " |")
    out.append("|---|" + "---|" * len(ARMS))
    for fld, name, nd in (("n_cl", "Số cụm", 0), ("n_batch", "Số đợt vào", 0), ("n_leg", "Số leg", 0),
                          ("notional", "Notional vào (Σ q·entry) USD", 0), ("exp_mean", "Phơi nhiễm TB %", 2),
                          ("exp_max", "Phơi nhiễm max %", 1), ("hold_mean", "Giữ TB h", 1), ("ncut", "Cụm cắt time-stop", 0)):
        cells = []
        for a in ARMS:
            R = J["arms"][a]["rows"].values()
            x = med([r["period"]["DEV"][fld][0] for r in R])[0]
            v = med([r["period"]["DEV"][fld][1] for r in R])[0]
            d = med([r["period"]["DEV"][fld][1] - r["period"]["DEV"][fld][0] for r in R])
            cells.append("%s / %s / %s [%s; %s]" % (f(x, nd), f(v, nd), f(d[0], nd, True), f(d[1], nd, True), f(d[2], nd, True)))
        out.append("| %s | %s |" % (name, " | ".join(cells)))
    out.append("| Δ số đợt vào TB %% (C5) | %s |" % " | ".join("%+.2f" % (100 * J["arms"][a]["rule"]["C5"]["mean_dbatch"]) for a in ARMS))
    out.append("")
    out.append("## 3. Cụm hoãn và vốn giam (X14 → biến thể, median)\n")
    out.append("| Chỉ số | " + " | ".join(ARMS) + " |")
    out.append("|---|" + "---|" * len(ARMS))
    for name, fn, nd in (("Cụm hoãn/seed", lambda r, i: r["defer"]["n"][i], 0), ("ΣPnL cụm hoãn", lambda r, i: r["defer"]["pnl"][i], 0),
                         ("Giữ thêm TB h", lambda r, i: r["defer"]["extra_h"][i], 0),
                         ("Vốn giam TB giờ ON % equity", lambda r, i: r["defer"]["locked_flag_mean"][i], 1),
                         ("Vốn giam đỉnh % equity", lambda r, i: r["defer"]["locked_max"][i], 1),
                         ("Phơi nhiễm TB giờ ON %", lambda r, i: r["defer"]["exp_flag_mean"][i], 1),
                         ("Giờ ON", lambda r, i: r["defer"]["hours_flag"][i], 0)):
        out.append("| %s | %s |" % (name, " | ".join("%s → %s" % (f(med([fn(r, 0) for r in J["arms"][a]["rows"].values()])[0], nd),
                                                                  m3([fn(r, 1) for r in J["arms"][a]["rows"].values()], nd)) for a in ARMS)))
    out.append("| V4 cụm hoãn = Java | %s |" % " | ".join("%d/%d" % (sum(r["defer"]["V4_ok"] for r in J["arms"][a]["rows"].values()),
                                                                     len(J["arms"][a]["rows"])) for a in ARMS))
    out.append("| Thoát (gộp 8 seed) | %s |" % " | ".join(
        ", ".join("%s %d" % (k, sum(r["defer"]["exit"].get(k, 0) for r in J["arms"][a]["rows"].values()))
                  for k in ("cut_flag_off", "arm_trail", "cut_cap", "sl_other")) for a in ARMS))
    out.append("")
    out.append("## 4. Crash-buy lỡ so X14 (khoá sym+anchor; median/seed: số chỉ-X14 (PnL) | số chỉ-biến-thể (PnL))\n")
    out.append("| Phạm vi | " + " | ".join(ARMS) + " |")
    out.append("|---|" + "---|" * len(ARMS))
    cells = []
    for a in ARMS:
        R = list(J["arms"][a]["rows"].values())
        cells.append("%s (%s) \\| %s (%s); net %s" % (
            f(med([r["missed_all"]["x14_only"] for r in R])[0]), f(med([r["missed_all"]["x14_only_pnl"] for r in R])[0], 0, True),
            f(med([r["missed_all"]["v_only"] for r in R])[0]), f(med([r["missed_all"]["v_only_pnl"] for r in R])[0], 0, True),
            f(med([r["missed_all"]["v_only_pnl"] - r["missed_all"]["x14_only_pnl"] for r in R])[0], 0, True)))
    out.append("| Toàn DEV | %s |" % " | ".join(cells))
    for nm, ym in KEY_EP:
        i = ep_index(lab, ym)
        if i is None:
            continue
        cells = []
        for a in ARMS:
            R = list(J["arms"][a]["rows"].values())
            e = [r["missed"][i] for r in R]
            cells.append("%s (%s) \\| %s (%s); Δcụm mới %s" % (
                f(med([x["x14_only"] for x in e])[0]), f(med([x["x14_only_pnl"] for x in e])[0], 0, True),
                f(med([x["v_only"] for x in e])[0]), f(med([x["v_only_pnl"] for x in e])[0], 0, True),
                f(med([x["new"][1] - x["new"][0] for x in e])[0], 0, True)))
        out.append("| %s (%s, cửa sổ +15d) | %s |" % (nm, lab[i], " | ".join(cells)))
    out.append("")
    out.append("## 5. Phân rã ΔΣPnL = direct (replay) + phần còn lại (slot/lãi kép/lệnh khác)\n")
    out.append("| | " + " | ".join(ARMS) + " |")
    out.append("|---|" + "---|" * len(ARMS))
    for name, fn in (("ΔΣPnL sim", lambda r: r["sum_pnl"][2]), ("direct (replay)", lambda r: r["direct"]),
                     ("phần còn lại", lambda r: r["rest"])):
        out.append("| %s | %s |" % (name, " | ".join(m3([fn(r) for r in J["arms"][a]["rows"].values()], 0, True) for a in ARMS)))
    out.append("| seed ΔΣPnL>0 | %s |" % " | ".join("%d/8" % sum(r["sum_pnl"][2] > 0 for r in J["arms"][a]["rows"].values()) for a in ARMS))
    out.append("| kiểm direct = phaseB (max\\|Δ\\|) | %s |" % " | ".join(
        "%.1e" % max(abs(r["direct_check"]) for r in J["arms"][a]["rows"].values()) for a in ARMS))
    out.append("")
    out.append("## 6. ΔPnL thực hiện theo kỳ đóng (median [min; max])\n")
    out.append("| Kỳ | " + " | ".join(ARMS) + " |")
    out.append("|---|" + "---|" * len(ARMS))
    for per in ("2021H2", "2022", "2023", "2024", "2025"):
        out.append("| %s | %s |" % (per, " | ".join(m3([r["period"][per]["pnl"][1] - r["period"][per]["pnl"][0]
                                                         for r in J["arms"][a]["rows"].values()], 0, True) for a in ARMS)))
    out.append("| ΔDD MTM phút trong năm (2022) pp | %s |" % " | ".join(
        m3([r["period"]["2022"]["dd"][1] - r["period"]["2022"]["dd"][0] for r in J["arms"][a]["rows"].values()], 2, True) for a in ARMS))
    out.append("")
    out.append("## 7. Theo đợt (TB 8 seed): direct (replay) | Δ đoạn (sim) — chỉ đợt có |giá trị| ≥ 50\n")
    out.append("| Đợt | " + " | ".join(ARMS) + " |")
    out.append("|---|" + "---|" * len(ARMS))
    for i, e in enumerate(lab):
        vals = [(J["arms"][a]["agg"]["dir_ep_mean"][e], J["arms"][a]["agg"]["seg_ep_mean"][e]) for a in ARMS]
        if max(max(abs(x), abs(y)) for x, y in vals) < 50:
            continue
        out.append("| %s | %s |" % (e, " | ".join("%s \\| %s" % (f(x, 0, True), f(y, 0, True)) for x, y in vals)))
    out.append("| **Tổng** | %s |" % " | ".join("%s \\| %s" % (f(J["arms"][a]["rule"]["C4"]["direct_tot"], 0, True),
                                                             f(J["arms"][a]["rule"]["C4"]["seg_tot"], 0, True)) for a in ARMS))
    out.append("| Bỏ đợt lớn nhất (C4) | %s |" % " | ".join("%s (%s) \\| %s (%s)" % (
        f(J["arms"][a]["rule"]["C4"]["direct_loo"], 0, True), J["arms"][a]["rule"]["C4"]["direct_max_ep"][:7],
        f(J["arms"][a]["rule"]["C4"]["seg_loo"], 0, True), J["arms"][a]["rule"]["C4"]["seg_max_ep"][:7]) for a in ARMS))
    out.append("")
    out.append("## 8. Luật ứng viên v1.2\n")
    out.append("| | " + " | ".join(ARMS) + " |")
    out.append("|---|" + "---|" * len(ARMS))
    for c in ("C1", "C2", "C3", "C4", "C5", "candidate"):
        out.append("| %s | %s |" % (c, " | ".join(("✔" if (J["arms"][a]["rule"][c] if c == "candidate" else J["arms"][a]["rule"][c]["ok"])
                                                    else "✘") for a in ARMS)))
    out.append("\nỨng viên: %s → chọn %s\n" % (J.get("candidates"), J.get("pick")))
    if os.path.exists(D + "/ho.json") and len(sys.argv) < 2:
        H = json.load(open(D + "/ho.json"))["arms"]
        out.append("## 9. HO 2026 W9 (MÔ TẢ, không chấm; Δ = biến thể − X14 HO cùng seed)\n")
        out.append("| | " + " | ".join(H) + " |")
        out.append("|---|" + "---|" * len(H))
        for name, k, nd in (("ΔPnL W9 USD", "dPnL", 0), ("ΔROI W9 pp", "dROI", 2), ("ΔmaxDD W9 pp", "dMaxDD", 2), ("Δsố lệnh", "dN", 0)):
            out.append("| %s | %s |" % (name, " | ".join("%s [%s; %s]" % tuple(f(x, nd, True) for x in H[a]["agg"][k]) for a in H)))
        out.append("| seed ΔPnL>0 | %s |" % " | ".join("%d/%d" % (H[a]["agg"]["n_dPnL_pos"], H[a]["agg"]["n"]) for a in H))
        out.append("| ROI W9 X14 → biến thể (median) | %s |" % " | ".join(
            "%s → %s" % (f(H[a]["agg"]["roi_x14"][0], 2), f(H[a]["agg"]["roi_v"][0], 2)) for a in H))
        out.append("| maxDD seed tệ nhất X14 → biến thể | %s |" % " | ".join(
            "%s → %s" % (f(H[a]["agg"]["worst_dd"][0], 2), f(H[a]["agg"]["worst_dd"][1], 2)) for a in H))
        out.append("| Cụm hoãn/seed X14 → biến thể | %s |" % " | ".join(
            "%s → %s" % (f(H[a]["agg"]["defer"][0][0]), f(H[a]["agg"]["defer"][1][0])) for a in H))
        for q in ("Q1", "Q2", "Q3"):
            out.append("| ΔPnL %s | %s |" % (q, " | ".join("%s [%s; %s]" % tuple(f(x, 0, True) for x in H[a]["agg"]["q"][q]) for a in H)))
    fn = D + ("/tables.md" if len(sys.argv) < 2 else "/tables_smoke.md")
    open(fn, "w").write("\n".join(out) + "\n")
    ps = []
    for a in ARMS:
        for s, r in J["arms"][a]["rows"].items():
            ps.append(dict(arm=a, seed=s, cagr22_x14=r["cagr22"][0], cagr22_v=r["cagr22"][1], dd22_x14=r["dd_mtm22"][0], dd22_v=r["dd_mtm22"][1],
                           cal22_x14=r["calmar22"][0], cal22_v=r["calmar22"][1], uw22_x14=r["uw_mtm22"][0], uw22_v=r["uw_mtm22"][1],
                           pnl_x14=r["sum_pnl"][0], pnl_v=r["sum_pnl"][1], direct=r["direct"], rest=r["rest"],
                           batch_x14=r["period"]["DEV"]["n_batch"][0], batch_v=r["period"]["DEV"]["n_batch"][1],
                           cl_x14=r["period"]["DEV"]["n_cl"][0], cl_v=r["period"]["DEV"]["n_cl"][1],
                           leg_x14=r["period"]["DEV"]["n_leg"][0], leg_v=r["period"]["DEV"]["n_leg"][1],
                           notional_x14=r["period"]["DEV"]["notional"][0], notional_v=r["period"]["DEV"]["notional"][1],
                           defer_x14=r["defer"]["n"][0], defer_v=r["defer"]["n"][1], defer_java=r["defer"]["java"],
                           locked_max_x14=r["defer"]["locked_max"][0], locked_max_v=r["defer"]["locked_max"][1],
                           missed_x14only=r["missed_all"]["x14_only"], missed_x14only_pnl=r["missed_all"]["x14_only_pnl"],
                           missed_vonly=r["missed_all"]["v_only"], missed_vonly_pnl=r["missed_all"]["v_only_pnl"]))
    pd.DataFrame(ps).to_csv(D + ("/per_seed.csv" if len(sys.argv) < 2 else "/per_seed_smoke.csv"), index=False)
    log.info("WROTE %s", fn)


if __name__ == "__main__":
    main()
