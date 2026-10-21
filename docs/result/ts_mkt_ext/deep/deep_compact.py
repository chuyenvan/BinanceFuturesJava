#!/usr/bin/env python3
"""Bang gon (median 8 seed) P0 / X14 / Delta cho moi ky tu deep.json -> deep_compact.md."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
J = json.load(open(HERE + "/deep.json"))
PER = ["2021H2", "2022", "2023", "2024", "2025", "DEV", "2026W9"]
NAMES = [("n_cl", "Số cụm", 0), ("n_batch", "Số đợt vào", 0), ("n_leg", "Số leg", 0), ("win", "Win leg %", 1),
         ("pnl", "PnL USD", 0), ("roi", "ROI %", 1), ("dd", "maxDD MTM phút %", 2), ("dd_day", "maxDD EOD %", 2),
         ("calmar", "Calmar", 2), ("worst_m_pct", "Tháng tệ nhất %", 2), ("hold_mean", "Giữ TB h", 1),
         ("hold_p90", "Giữ p90 h", 0), ("n168", "Cụm chạm 168h", 0), ("ncut", "Cụm cắt time-stop", 0),
         ("exp_mean", "Phơi nhiễm TB %", 1), ("exp_max", "Phơi nhiễm max %", 1)]


def f(v, nd, sign=False):
    s = (("%+." if sign else "%.") + str(nd) + "f") % v
    return s.replace(".", ",") if nd else s


o = ["| Chỉ số (median 8 seed) P0 / X14 / Δ | " + " | ".join(PER) + " |", "|---|" + "---|" * len(PER)]
for k, lb, nd in NAMES:
    cells = []
    for p in PER:
        T = J["years"][p][k]
        cells.append("%s / %s / %s" % (f(T["P0"][0], nd), f(T["X14"][0], nd), f(T["D"][0], nd, True)))
    o.append("| %s | %s |" % (lb, " | ".join(cells)))
o.append("| DD đỉnh→đáy (mode) P0 \\| X14 | " + " | ".join(
    "%s→%s \\| %s→%s" % (J["years"][p]["dd_peak_P0"][5:], J["years"][p]["dd_trough_P0"][5:], J["years"][p]["dd_peak_X14"][5:],
                          J["years"][p]["dd_trough_X14"][5:]) for p in PER) + " |")
o.append("| Tháng tệ nhất (mode) P0 \\| X14 | " + " | ".join("%s \\| %s" % (J["years"][p]["worst_m_P0"], J["years"][p]["worst_m_X14"]) for p in PER) + " |")
open(HERE + "/deep_compact.md", "w").write("\n".join(o) + "\n")
