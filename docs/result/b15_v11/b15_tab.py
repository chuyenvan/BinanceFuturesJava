#!/usr/bin/env python3
"""B15_V11: bang markdown tu b15_dev.json + b15_ho.json (chi doc, khong tinh lai)."""
import json
import logging
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("tab")
W = "/home/ubuntu/claude_master/b15"
DS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
HS = [42, 7, 13, 21, 99, 123, 777, 2024]
f = lambda x, n=2: ("%." + str(n) + "f") % x if x is not None else "-"  # noqa: E731
mean = lambda v: float(np.mean(v))  # noqa: E731
med = lambda v: float(np.median(v))  # noqa: E731

d = json.load(open(W + "/b15_dev.json"))
R, S = d["rows"], d["stress"]
log.info("## DEV per seed")
log.info("| seed | CAGR22 P→S | ΔCAGR | DD22 P→S | DDall P→S | Calmar22 P→S | ΔCal | UW22 P→S | ΣPnL P→S | n P→S | gross_max P→S | conc P→S | PC blk P→S | near-cap P→S |")
log.info("|" + "---|" * 15)
for s in DS:
    p, q = R["P_" + s], R["S_" + s]
    log.info("| %s | %s→%s | %+.2f | %s→%s | %s→%s | %s→%s | %+.3f | %.0f→%.0f | %.0f→%.0f | %d→%d | %.1f→%.1f | %.1f→%.1f | %s→%s | %s→%s |", s,
             f(p["cagr22"]), f(q["cagr22"]), q["cagr22"] - p["cagr22"], f(p["dd_mtm22"]), f(q["dd_mtm22"]), f(p["dd_mtm"]), f(q["dd_mtm"]),
             f(p["calmar22"], 3), f(q["calmar22"], 3), q["calmar22"] - p["calmar22"], p["uw_mtm22"], q["uw_mtm22"], p["sum_pnl"], q["sum_pnl"],
             p["n"], q["n"], p["gross_max"], q["gross_max"], p["conc_coin_max"], q["conc_coin_max"], p["pc"]["summary"], q["pc"]["summary"],
             p["near_cap"]["n_entry_near"], q["near_cap"]["n_entry_near"])
F = ("cagr22", "dd_mtm22", "dd_mtm", "calmar22", "uw_mtm22", "sum_pnl", "n", "gross_max", "conc_coin_max", "pnl_per_notional_bps", "sum_notional")
for a in ("P", "S"):
    log.info("AGG %s mean %s", a, {k: round(mean([R[a + "_" + s][k] for s in DS]), 3) for k in F})
    log.info("AGG %s worst ddall %.2f median ddall %.2f worst dd22 %.2f median dd22 %.2f", a, min(R[a + "_" + s]["dd_mtm"] for s in DS),
             med([R[a + "_" + s]["dd_mtm"] for s in DS]), min(R[a + "_" + s]["dd_mtm22"] for s in DS), med([R[a + "_" + s]["dd_mtm22"] for s in DS]))
    log.info("AGG %s pc_blocked mean %.1f near_cap mean %.1f umax mean %.1f", a, mean([R[a + "_" + s]["pc"]["summary"] for s in DS]),
             mean([R[a + "_" + s]["near_cap"]["n_entry_near"] for s in DS]), mean([R[a + "_" + s]["near_cap"]["umax"] for s in DS]))
log.info("## DEV per year (mean 8 seed)")
log.info("| năm | ΣPnL P | ΣPnL S15 | ΔPnL | ROI P | ROI S15 | DD P | DD S15 | Calmar P | Calmar S15 | n P | n S |")
log.info("|" + "---|" * 12)
for y in ("2022", "2023", "2024", "2025"):
    g = lambda a, k: [R[a + "_" + s]["per_year"][y][k] for s in DS]  # noqa: E731
    cal = lambda a: mean([x for x in g(a, "calmar") if x is not None])  # noqa: E731
    log.info("| %s | %.0f | %.0f | %+.0f | %.1f | %.1f | %.2f | %.2f | %.2f | %.2f | %.0f | %.0f |", y, mean(g("P", "sum_pnl")), mean(g("S", "sum_pnl")),
             mean(g("S", "sum_pnl")) - mean(g("P", "sum_pnl")), mean(g("P", "roi_year")), mean(g("S", "roi_year")), mean(g("P", "dd")),
             mean(g("S", "dd")), cal("P"), cal("S"), mean(g("P", "n")), mean(g("S", "n")))
    log.info("  min DD %s: P %.2f S %.2f; ΔPnL>0 seeds %d/8", y, min(g("P", "dd")), min(g("S", "dd")),
             sum(a > b for a, b in zip(g("S", "sum_pnl"), g("P", "sum_pnl"))))
log.info("## DEV stress")
for sc in ("I10", "I20", "I20Y2"):
    for a in ("P", "S"):
        log.info("STRESS %s %s %s worst ddall %.2f", sc, a, {k: round(mean([S[a + "_" + s][sc][k] for s in DS]), 3) for k in S["P_A1"][sc]},
                 min(S[a + "_" + s][sc]["dd_mtm"] for s in DS))
    ci = d["cost_info"]
    log.info("COST %s P total %.0f S total %.0f (mean USD); med bps P %.2f S %.2f; invalid P %.1f S %.1f", sc,
             mean([ci["P_%s|%s" % (s, sc)]["total_usd"] for s in DS]), mean([ci["S_%s|%s" % (s, sc)]["total_usd"] for s in DS]),
             mean([ci["P_%s|%s" % (s, sc)]["med_bps"] for s in DS]), mean([ci["S_%s|%s" % (s, sc)]["med_bps"] for s in DS]),
             mean([ci["P_%s|%s" % (s, sc)]["n_invalid"] for s in DS]), mean([ci["S_%s|%s" % (s, sc)]["n_invalid"] for s in DS]))
log.info("RULE DEV base %s", {k: v for k, v in d["rule"]["base"].items() if not isinstance(v, list)})
for sc in ("I10", "I20", "I20Y2"):
    log.info("RULE DEV %s %s", sc, {k: v for k, v in d["rule"]["stress"][sc].items() if not isinstance(v, list)})
log.info("dCAGR %s", [round(x, 2) for x in d["rule"]["base"]["dcagr"]])
log.info("dCal  %s", [round(x, 3) for x in d["rule"]["base"]["dcalmar"]])
log.info("dCAGR I20 %s", [round(x, 2) for x in d["rule"]["stress"]["I20"]["dcagr"]])
log.info("dCal I20 %s", [round(x, 3) for x in d["rule"]["stress"]["I20"]["dcalmar"]])

h = json.load(open(W + "/b15_ho.json"))
H = h["rows"]
log.info("## HO W9 per seed")
log.info("| seed | ROI P→S | ΔROI | maxDD P→S | Calmar P→S | ΔCal | ΣPnL P→S | n P→S | I20 ROI P→S | I20 DD S | I20 ΔCal | gross P→S | PC skip P→S | near-cap P→S |")
log.info("|" + "---|" * 15)
for s in HS:
    p, q = H["P_%d" % s], H["S_%d" % s]
    b, c = p["base"]["W9"], q["base"]["W9"]
    bi, ci_ = p["stress"]["I20"]["W9"], q["stress"]["I20"]["W9"]
    log.info("| %d | %s→%s | %+.2f | %s→%s | %s→%s | %+.2f | %.0f→%.0f | %d→%d | %s→%s | %s | %+.2f | %s→%s | %s→%s | %s→%s |", s, f(b["roi"]), f(c["roi"]),
             c["roi"] - b["roi"], f(b["maxdd"]), f(c["maxdd"]), f(b["calmar"]), f(c["calmar"]), c["calmar"] - b["calmar"], b["sum_pnl"], c["sum_pnl"],
             b["n"], c["n"], f(bi["roi"]), f(ci_["roi"]), f(ci_["maxdd"]), ci_["calmar"] - bi["calmar"],
             f(p["gc_W9"]["gross_max"], 1), f(q["gc_W9"]["gross_max"], 1), p["pc_W9"]["skip_lines"], q["pc_W9"]["skip_lines"],
             p["near_cap_W9"]["n_entry_near"], q["near_cap_W9"]["n_entry_near"])
for wk in ("W9", "Q1", "Q2", "Q3"):
    for a in ("P", "S"):
        g = lambda k, sc=None: [(H["%s_%d" % (a, s)]["base"][wk] if sc is None else H["%s_%d" % (a, s)]["stress"][sc][wk])[k] for s in HS]  # noqa: E731
        log.info("HO %s %s roi %.2f (min %.2f) maxdd mean %.2f worst %.2f med %.2f calmar %.2f pnl %.0f | I20 roi %.2f dd worst %.2f cal %.2f | I10 roi %.2f",
                 wk, a, mean(g("roi")), min(g("roi")), mean(g("maxdd")), min(g("maxdd")), med(g("maxdd")), mean(g("calmar")), mean(g("sum_pnl")),
                 mean(g("roi", "I20")), min(g("maxdd", "I20")), mean(g("calmar", "I20")), mean(g("roi", "I10")))
    dq = [H["S_%d" % s]["base"][wk]["roi"] - H["P_%d" % s]["base"][wk]["roi"] for s in HS]
    log.info("HO %s dROI mean %.2f pos %d/8 %s", wk, mean(dq), sum(x > 0 for x in dq), [round(x, 2) for x in dq])
for a in ("P", "S"):
    log.info("HO %s pnl/notional bps %.1f notional %.0f gross_max %.1f conc %.1f", a, mean([H["%s_%d" % (a, s)]["pnl_per_notional_bps_W9"] for s in HS]),
             mean([H["%s_%d" % (a, s)]["sum_notional_W9"] for s in HS]), mean([H["%s_%d" % (a, s)]["gc_W9"]["gross_max"] for s in HS]),
             mean([H["%s_%d" % (a, s)]["gc_W9"]["conc_max"] for s in HS]))
ci = h["cost_info"]
for sc in ("I10", "I20", "I20Y2"):
    log.info("HO COST %s P %%eq0 %.3f S %%eq0 %.3f med bps P %.2f S %.2f", sc, mean([ci["P_%d|%s" % (s, sc)]["total_pct_eq0"] for s in HS]),
             mean([ci["S_%d|%s" % (s, sc)]["total_pct_eq0"] for s in HS]), mean([ci["P_%d|%s" % (s, sc)]["med_bps"] for s in HS]),
             mean([ci["S_%d|%s" % (s, sc)]["med_bps"] for s in HS]))
log.info("RULE HO base %s", {k: v for k, v in h["rule"]["base"].items() if not isinstance(v, list)})
for sc in ("I10", "I20", "I20Y2"):
    log.info("RULE HO %s %s", sc, {k: v for k, v in h["rule"]["stress"][sc].items() if not isinstance(v, list)})
log.info("VALID dev %s", d["validate"])
log.info("VALID ho %s", {k: v for k, v in h["validate"].items() if k != "mtm_check"})
log.info("VALID ho mtm %s", {k: v for k, v in h["validate"]["mtm_check"].items() if k != "tail"})
