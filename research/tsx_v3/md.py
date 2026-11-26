#!/usr/bin/env python3
"""TSX_V3 - bang markdown tu dev.json + ho.json -> docs/result/tsx_v3/tables.md (median [min; max] 8 seed; d = V - V0 cung seed)."""
import json
import logging
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx3md")
D = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/tsx_v3"
J = json.load(open(D + "/" + (sys.argv[1] if len(sys.argv) > 1 else "dev.json")))
H = json.load(open(D + "/ho.json"))
ARMS = [a for a in ("V1", "V2", "V3", "V4") if a in J["arms"]]
NAME = {"V1": "V1 trần 420h", "V2": "V2 B3b hồi≥20 %", "V3": "V3 −0,25/30", "V4": "V4 −0,30/45"}
YEARS = ["2021H2", "2022", "2023", "2024", "2025"]
LUNA, J24 = "2022-04-27..2022-07-06", "2024-06-18..2024-07-26"


def f(x, nd=0, sign=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    s = format(float(x), ("+" if sign else "") + ",." + str(nd) + "f")
    return s.replace(",", " ").replace(".", ",")


def med(v):
    v = np.asarray([x for x in v if x is not None and not (isinstance(x, float) and np.isnan(x))], float)
    return (float(np.median(v)), float(v.min()), float(v.max())) if len(v) else (np.nan, np.nan, np.nan)


def m3(v, nd=0, sign=False):
    a, b, c = med(v)
    return "%s [%s; %s]" % (f(a, nd, sign), f(b, nd, sign), f(c, nd, sign))


def rows(a):
    return J["arms"][a]["rows"]


def col(a, fn):
    return [fn(r) for r in rows(a).values()]


def main():
    o = ["# TSX_V3 — bảng (median [min; max] 8 seed DEV; Δ = biến thể − V0 cùng seed)\n"]
    a0 = ARMS[0]
    o.append("## 1. Headline DEV (MTM phút)\n")
    o.append("| Chỉ số | V0 (X14) | " + " | ".join(NAME[a] for a in ARMS) + " |")
    o.append("|---|---|" + "---|" * len(ARMS))
    for key, nm, nd in (("cagr22", "CAGR22 %", 2), ("sum_pnl", "ΣPnL USD", 0), ("dd_mtm22", "DD22 MTM %", 2), ("dd_mtm", "DD toàn kỳ %", 2),
                        ("calmar22", "Calmar22", 3), ("uw_mtm22", "UW22 (ngày)", 0)):
        o.append("| %s | %s | %s |" % (nm, m3(col(a0, lambda r: r[key][0]), nd), " | ".join(m3(col(a, lambda r: r[key][1]), nd) for a in ARMS)))
        o.append("| Δ %s | – | %s |" % (nm, " | ".join(m3(col(a, lambda r: r[key][2]), nd, True) for a in ARMS)))
    o.append("| seed ΔCAGR22 > 0 | – | %s |" % " | ".join("%d/8" % sum(r["cagr22"][2] > 0 for r in rows(a).values()) for a in ARMS))
    o.append("| DD22 seed tệ nhất | %s | %s |" % (f(min(col(a0, lambda r: r["dd_mtm22"][0])), 2),
                                               " | ".join(f(min(col(a, lambda r: r["dd_mtm22"][1])), 2) for a in ARMS)))
    o.append("\n## 2. Hoạt động / vốn (DEV 2021-07..2025-12)\n")
    o.append("| Chỉ số | V0 (X14) | " + " | ".join(NAME[a] for a in ARMS) + " |")
    o.append("|---|---|" + "---|" * len(ARMS))

    def P(r, k, i):
        return r["period"]["DEV"][k][i]
    for k, nm, nd in (("n_cl", "số cụm", 0), ("n_batch", "số đợt vào", 0), ("n_leg", "số leg", 0), ("notional", "khối lượng Σq·entry (triệu USD)", 2),
                      ("exp_mean", "phơi nhiễm TB % equity", 1), ("exp_max", "phơi nhiễm max %", 1), ("hold_mean", "giữ TB (h)", 1),
                      ("ncut", "cụm cắt time-stop ≥168h", 0)):
        sc = 1e6 if k == "notional" else 1.0
        o.append("| %s | %s | %s |" % (nm, m3(col(a0, lambda r: P(r, k, 0) / sc), nd), " | ".join(m3(col(a, lambda r: P(r, k, 1) / sc), nd) for a in ARMS)))
        if k in ("n_cl", "n_batch", "n_leg", "notional"):
            o.append("| Δ %s %% | – | %s |" % (nm, " | ".join(m3(col(a, lambda r: 100 * (P(r, k, 1) / P(r, k, 0) - 1)), 2, True) for a in ARMS)))
    for k, nm, nd in (("n", "cụm hoãn (DEEP §1)", 0), ("locked_flag_mean", "vốn giam cụm hoãn TB giờ ON % eq", 2),
                      ("locked_max", "vốn giam cụm hoãn đỉnh % eq", 1), ("exp_flag_mean", "phơi nhiễm TB giờ ON %", 1)):
        o.append("| %s | %s | %s |" % (nm, m3(col(a0, lambda r: r["defer"][k][0]), nd), " | ".join(m3(col(a, lambda r: r["defer"][k][1]), nd) for a in ARMS)))
    for k, nm, nd in (("hours", "giờ U ≥ U_MAX 0,60", 0), ("touches", "số lần chạm U_MAX", 0), ("u_mean", "U TB", 3), ("u_max", "U max", 3),
                      ("thr_all", "throttle (1−U/U_MAX) lúc vào cụm, TB*", 3), ("thr_flag", "throttle lúc vào, cụm vào ngày cờ*", 3)):
        o.append("| %s | %s | %s |" % (nm, m3(col(a0, lambda r: r["umax"][0][k]), nd), " | ".join(m3(col(a, lambda r: r["umax"][1][k]), nd) for a in ARMS)))
    o.append("\n\\* mô tả thêm ngoài danh sách prereg (cơ chế size lệnh mới = equity·F_BASE·(1−U/U_MAX)). U xấp xỉ: margin printDone / equity MTM.\n")
    o.append("## 3. Lệnh bị lỡ (25 đợt Phase A; TB-seed tổng các đợt; khoá sym+anchor)\n")
    o.append("| Cửa sổ | Chỉ số | " + " | ".join(NAME[a] for a in ARMS) + " |")
    o.append("|---|---|" + "---|" * len(ARMS))
    for nm, key in (("trong đợt", "missed_sum_in"), ("sau đợt ≤15 ngày", "missed_sum_after")):
        for k, lb, nd in (("new_v0", "cụm mới V0", 0), ("new_v", "cụm mới V", 0), ("v0_only", "chỉ V0 có (V lỡ)", 0),
                          ("v_only", "chỉ V có", 0), ("v0_only_pnl", "PnL cụm V lỡ", 0), ("v_only_pnl", "PnL cụm chỉ V có", 0)):
            o.append("| %s | %s | %s |" % (nm, lb, " | ".join(m3(col(a, lambda r: r[key][k]), nd) for a in ARMS)))
    for k, lb in (("v0_only", "toàn DEV: chỉ V0 có"), ("v_only", "toàn DEV: chỉ V có"), ("v0_only_pnl", "toàn DEV: PnL chỉ V0"),
                  ("v_only_pnl", "toàn DEV: PnL chỉ V")):
        o.append("| toàn DEV | %s | %s |" % (lb, " | ".join(m3(col(a, lambda r: r["missed_all"][k]), 0) for a in ARMS)))
    o.append("\n## 4. Phân rã ΔΣPnL (USD/seed) = direct (replay) + lãi kép (sizing) + phần dư (slot/vốn/lệnh khác)\n")
    o.append("| Biến thể | ô replay | ΔΣPnL sim | direct | sizing | phần dư | sim − replay | seed sim>0 / replay>0 |")
    o.append("|---|---|---|---|---|---|---|---|")
    for a in ARMS:
        R = rows(a)
        o.append("| %s | %s | %s | %s | %s | %s | %s | %d / %d |" % (NAME[a], J["arms"][a]["cell"], m3(col(a, lambda r: r["sum_pnl"][2]), 0, True),
                                                       m3(col(a, lambda r: r["direct"]), 0, True), m3(col(a, lambda r: r["sizing"]), 0, True),
                                                       m3(col(a, lambda r: r["resid"]), 0, True), m3(col(a, lambda r: r["replay_gap"]), 0, True),
                                                       sum(r["sum_pnl"][2] > 0 for r in R.values()), sum(r["direct"] > 0 for r in R.values())))
    o.append("\nTB 8 seed: " + "; ".join("%s ΔΣPnL %s = direct %s + sizing %s + dư %s" % (
        a, f(np.mean(col(a, lambda r: r["sum_pnl"][2])), 0, True), f(np.mean(col(a, lambda r: r["direct"])), 0, True),
        f(np.mean(col(a, lambda r: r["sizing"])), 0, True), f(np.mean(col(a, lambda r: r["resid"])), 0, True)) for a in ARMS))
    o.append("\n## 5. Theo năm (đóng, local +07)\n")
    o.append("| Năm | Chỉ số | " + " | ".join(NAME[a] for a in ARMS) + " |")
    o.append("|---|---|" + "---|" * len(ARMS))
    for y in YEARS:
        o.append("| %s | ΔPnL | %s |" % (y, " | ".join(m3(col(a, lambda r: r["dpnl_year"][y]), 0, True) for a in ARMS)))
        o.append("| %s | Δ đợt vào %% | %s |" % (y, " | ".join(m3(col(a, lambda r: 100 * (r["period"][y]["n_batch"][1] / r["period"][y]["n_batch"][0] - 1)), 2, True) for a in ARMS)))
        o.append("| %s | Δ leg %% | %s |" % (y, " | ".join(m3(col(a, lambda r: 100 * (r["period"][y]["n_leg"][1] / r["period"][y]["n_leg"][0] - 1)), 2, True) for a in ARMS)))
        o.append("| %s | Δ khối lượng %% | %s |" % (y, " | ".join(m3(col(a, lambda r: 100 * (r["period"][y]["notional"][1] / r["period"][y]["notional"][0] - 1)), 2, True) for a in ARMS)))
    o.append("\n## 6. Theo đợt (TB 8 seed USD; direct = replay; Δ đoạn = ΔPnL sim [đầu đợt k, đầu đợt k+1))\n")
    o.append("| Đợt | " + " | ".join("%s direct / Δ đoạn" % a for a in ARMS) + " |")
    o.append("|---|" + "---|" * len(ARMS))
    for e in J["episodes"]:
        cells = []
        for a in ARMS:
            g = J["arms"][a]["agg"]
            cells.append("%s / %s" % (f(g["dir_ep_mean"][e], 0, True), f(g["seg_ep_mean"][e], 0, True)))
        tag = " **(LUNA)**" if e == LUNA else (" **(06/2024)**" if e == J24 else "")
        o.append("| %s%s | %s |" % (e, tag, " | ".join(cells)))
    o.append("\n### LUNA và 06/2024 (median [min; max] 8 seed)\n")
    lab = J["episodes"]
    for e, nm in ((LUNA, "LUNA"), (J24, "06/2024")):
        i = lab.index(e)
        for a in ARMS:
            o.append("- %s %s: direct %s; Δ đoạn %s; cụm mới trong đợt V0/V %s / %s; V lỡ %s (PnL %s); sau đợt V lỡ %s (PnL %s)" % (
                nm, a, m3(col(a, lambda r: r["direct_ep"][i]), 0, True), m3(col(a, lambda r: r["seg_ep"][i]), 0, True),
                m3(col(a, lambda r: r["missed"][i]["in"]["new"][0]), 0), m3(col(a, lambda r: r["missed"][i]["in"]["new"][1]), 0),
                m3(col(a, lambda r: r["missed"][i]["in"]["v0_only"]), 0), m3(col(a, lambda r: r["missed"][i]["in"]["v0_only_pnl"]), 0),
                m3(col(a, lambda r: r["missed"][i]["after"]["v0_only"]), 0), m3(col(a, lambda r: r["missed"][i]["after"]["v0_only_pnl"]), 0)))
    o.append("\n## 7. Luật (PREREG_TSX_V3 §5)\n")
    o.append("| Biến thể | (i) ΔCAGR22>0 8/8 | (ii) DD22 tệ nhất ≥ V0−1pp | (iii) LOO e* | (iv) Δ đợt vào ≥ −3 % | (v) HO ≥0 ≥6/8 (mô tả) | ỨNG VIÊN |")
    o.append("|---|---|---|---|---|---|---|")
    for a in ARMS:
        r = J["arms"][a]["rule"]
        o.append("| %s | %d/8 %s | %s vs %s %s | e*=%s: %s %s | %s %% %s | %s %s | **%s** |" % (
            NAME[a], r["i"]["n_pos"], "✔" if r["i"]["ok"] else "✘", f(r["ii"]["worst_v"], 2), f(r["ii"]["worst_v0"], 2), "✔" if r["ii"]["ok"] else "✘",
            r["iii"]["e_star"], f(r["iii"]["loo"], 0, True), "✔" if r["iii"]["ok"] else "✘", f(100 * r["iv"]["mean_dbatch"], 2, True),
            "✔" if r["iv"]["ok"] else "✘", r["v"]["n_ge0"], {True: "✔", False: "✘ (cảnh báo)", None: "–"}[r["v"]["ok"]],
            "CÓ" if r["candidate"] else "không"))
    o.append("\nỨng viên: %s → chọn: %s" % (J["candidates"], J["pick"]))
    o.append("\n## 8. HO 2026 W9 (MÔ TẢ; Δ vs tsx-ho-x14 cùng seed)\n")
    o.append("| Biến thể | ΔPnL | seed ≥0 / >0 | ΔROI pp | ΔmaxDD pp | maxDD tệ nhất V0 / V | cụm hoãn V0 / V | ΔPnL Q1 / Q2 / Q3 |")
    o.append("|---|---|---|---|---|---|---|---|")
    for a in ("V1", "V2", "V3", "V4"):
        g = H["arms"][a]["agg"]
        mm = lambda v, nd=0, s=True: "%s [%s; %s]" % (f(v[0], nd, s), f(v[1], nd, s), f(v[2], nd, s))  # noqa: E731
        o.append("| %s | %s | %s / %d | %s | %s | %s / %s | %s / %s | %s / %s / %s |" % (
            NAME[a], mm(g["dPnL"]), g["n_ge0"], g["n_pos"], mm(g["dROI"], 2), mm(g["dMaxDD"], 2), f(g["worst_dd"][0], 2), f(g["worst_dd"][1], 2),
            f(g["defer"][0][0]), f(g["defer"][1][0]), f(g["q"]["Q1"][0], 0, True), f(g["q"]["Q2"][0], 0, True), f(g["q"]["Q3"][0], 0, True)))
    open(D + "/tables.md", "w").write("\n".join(o) + "\n")
    log.info("WROTE %s/tables.md (%d dong)", D, len(o))


if __name__ == "__main__":
    main()
