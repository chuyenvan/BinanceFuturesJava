#!/usr/bin/env python3
"""BTC_BASE: in bang markdown tu bb_res.json (median [min; max] qua 8 seed) -> bb_tab.md"""
import json
import logging
import sys
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("bbtab")
o = json.load(open(sys.argv[1]))
SEEDS = ["42", "7", "13", "21", "99", "123", "777", "2024"]


def f(x, nd=1):
    return ("%." + str(nd) + "f") % x


def cell(a, k, nd=1):
    v = a.get(k)
    if v is None:
        return "—"
    return "%s [%s; %s]" % (f(v[0], nd), f(v[1], nd), f(v[2], nd))


def worst_seed_dd(res, vn):
    s = min(SEEDS, key=lambda s: res[s][vn]["dd_rule"])
    m = res[s][vn]
    return "%s→%s (s%s)" % (m["dd_peak"][:10], m["dd_trough"][:10], s)


lines = []
A, R = o["dev_agg"], o["dev"]
order = ["B0"] + ["S%.1f" % w for w in (0.2, 0.3, 0.4, 0.5)] + ["O%.1f" % w for w in (0.2, 0.3, 0.4, 0.5)] + \
        ["SP%.1f" % w for w in (0.2, 0.3, 0.4, 0.5)] + ["SB0.3"] + ["OT%.1f" % w for w in (0.2, 0.3, 0.4, 0.5)] + \
        ["OE%.1f" % w for w in (0.2, 0.3, 0.4, 0.5)] + ["OP%.1f" % w for w in (0.2, 0.3, 0.4, 0.5)] + \
        ["OG%.1f" % w for w in (0.2, 0.3, 0.4, 0.5)]
lines.append("### DEV chinh")
lines.append("| bien the | CAGR22 % | DD luat % | DD phut toan ky % | Calmar (luat) | thang te nhat % | su dung von (n+b)/E | b/E TB | gross max |")
lines.append("|---|---|---|---|---|---|---|---|---|")
for vn in order:
    a = A[vn]
    lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (vn, cell(a, "cagr22"), cell(a, "dd_rule"), cell(a, "dd_min_full"),
                 cell(a, "calmar_rule", 2), cell(a, "worst_month"), cell(a, "util_mean", 3), cell(a, "b_mean", 3), cell(a, "gross_max", 2)))
lines.append("")
lines.append("### DEV PnL / su kien")
lines.append("| bien the | PnL tong (k) | PnL crash-buy (k) | PnL BTC (k) | DD sleeve BTC (TWR) % | so lan ban RA | USD ban RA (k) | PnL ban RA vs gia von (USD) | phi (k) | funding (k) | 2022 PnL tong / CB / BTC (k) | DD 2022 % | giai doan DD sau nhat (seed te nhat) |")
lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for vn in order:
    a = A[vn]

    def k_(key):
        v = a.get(key)
        return "—" if v is None else "%.1f" % (v[0] / 1000)
    lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s / %s / %s | %s | %s |" % (
        vn, k_("pnl_total"), k_("pnl_cb"), k_("pnl_btc"), cell(a, "btc_sleeve_dd_twr_hour"), cell(a, "ev_ra_n", 0), k_("ev_ra_usd"),
        cell(a, "ev_ra_pnl", 0), k_("ev_fees"), k_("ev_funding"), k_("pnl22_total"), k_("pnl22_cb"), k_("pnl22_btc"), cell(a, "dd22_min"),
        worst_seed_dd(R, vn)))
lines.append("")
lines.append("worst month at (B0/O0.3/S0.3): %s" % [Counter(R[s][vn]["worst_month_at"] for s in SEEDS).most_common(2) for vn in ("B0", "O0.3", "S0.3", "SP0.3")])
lines.append("trend OT0.3 off days / switches: %s %s" % (cell(A["OT0.3"], "ev_trend_off_days", 0), cell(A["OT0.3"], "ev_trend_switch", 0)))
lines.append("wbar SP: %s" % {vn: cell(A[vn], "wbar", 4) for vn in ("SP0.2", "SP0.3", "SP0.4", "SP0.5")})
lines.append("corr: %s" % {s: (round(R[s]["_chk"]["corr"]["corr_all"], 3), round(R[s]["_chk"]["corr"]["corr_entry_days"], 3)) for s in SEEDS})
lines.append("rule: %s" % {t: (round(v["worst_dd_rule"], 2), v["n_pos"], round(min(v["dcagr"]), 2), round(max(v["dcagr"]), 2), v["eligible"]) for t, v in o["rule"].items()})
q2 = o["q2"]
lines.append("q2: n_beat_S' %s worst_dd_O %.2f worst_dd_S' %.2f dcagr_vs_S' [%.2f; %.2f] n_beat_S %s fill_has_value %s" % (
    q2["n_beat_Sprime"], q2["worst_dd_O"], q2["worst_dd_Sprime"], min(q2["dcagr_vs_Sprime"]), max(q2["dcagr_vs_Sprime"]), q2["n_beat_S"], q2["fill_has_value"]))
per = []
for s in SEEDS:
    per.append("s%s O0.3 %.2f/%.2f S'0.3 %.2f/%.2f S0.3 %.2f/%.2f B0 %.2f/%.2f" % (
        s, R[s]["O0.3"]["cagr22"], R[s]["O0.3"]["dd_rule"], R[s]["SP0.3"]["cagr22"], R[s]["SP0.3"]["dd_rule"],
        R[s]["S0.3"]["cagr22"], R[s]["S0.3"]["dd_rule"], R[s]["B0"]["cagr22"], R[s]["B0"]["dd_rule"]))
lines += per
lines.append("")
lines.append("### HO W9")
H = o["ho_agg"]
lines.append("| bien the | ROI W9 % | DD luat % | DD phut % | PnL CB (k) | PnL BTC (k) | so lan RA | b/E TB |")
lines.append("|---|---|---|---|---|---|---|---|")
for vn in order:
    a = H[vn]
    lines.append("| %s | %s | %s | %s | %.1f | %.1f | %s | %s |" % (vn, cell(a, "roi", 2), cell(a, "dd_rule", 2), cell(a, "dd_min_full", 2),
                 a["pnl_cb"][0] / 1000, a["pnl_btc"][0] / 1000, cell(a, "ev_ra_n", 0), cell(a, "b_mean", 3)))
lines.append("ho_rule: %s" % o["ho_rule"])
lines.append("btc_ho: %s ; checks dev %s ho %s" % (o["btc_ho"], o["dev_checks"], o["ho_checks"]))
open(sys.argv[2], "w").write("\n".join(lines))
log.info("\n".join(lines))
