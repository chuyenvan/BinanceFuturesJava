#!/usr/bin/env python3
"""BTC_BASE: JSON nho cho repo (agg + luat + chi so chinh theo seed) + delta ghep cap S(w)-B0."""
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("bbtrim")
o = json.load(open(sys.argv[1]))
SEEDS = ["42", "7", "13", "21", "99", "123", "777", "2024"]
KEYS = ["cagr22", "cagr_full", "dd_rule", "dd_hour_full", "dd_day_full", "dd_min_full", "dd_min_22", "calmar_rule", "calmar22",
        "worst_month", "worst_month_at", "dd_peak", "dd_trough", "util_mean", "b_mean", "pnl_total", "pnl_cb", "pnl_btc",
        "btc_sleeve_dd_twr_hour", "ev_ra_n", "ev_ra_pnl", "pnl22_total", "pnl22_cb", "pnl22_btc", "dd22_min", "roi", "wbar"]
MAIN = ["B0", "S0.2", "S0.3", "S0.4", "S0.5", "O0.2", "O0.3", "O0.4", "O0.5", "SP0.3", "SB0.3", "OT0.3", "OE0.3", "OP0.3", "OG0.3"]
small = dict(prereg=o["prereg"], wstar=o["wstar"], verdict_dev=o["verdict_dev"], rule=o["rule"], q2=o["q2"], ho_rule=o["ho_rule"],
             dev_checks=o["dev_checks"], ho_checks=o["ho_checks"], btc_ho=o["btc_ho"], dev_agg=o["dev_agg"], ho_agg=o["ho_agg"],
             dev_seed={s: {v: {k: o["dev"][s][v].get(k) for k in KEYS} for v in MAIN} for s in SEEDS},
             ho_seed={s: {v: {k: o["ho"][s][v].get(k) for k in KEYS} for v in MAIN} for s in SEEDS},
             dev_chk={s: o["dev"][s]["_chk"] for s in SEEDS})
pd_ = {}
for v in ("S0.2", "S0.3", "S0.4", "S0.5", "O0.2", "O0.3", "OT0.3"):
    d = [o["dev"][s][v]["cagr22"] - o["dev"][s]["B0"]["cagr22"] for s in SEEDS]
    pd_[v] = [min(d), sorted(d)[3] / 2 + sorted(d)[4] / 2, max(d), sum(x > 0 for x in d)]
small["dcagr_vs_B0"] = pd_
json.dump(small, open(sys.argv[2], "w"), indent=1, default=float)
log.info("dcagr_vs_B0 (min, median, max, n>0): %s", {k: [round(x, 2) for x in v] for k, v in pd_.items()})
