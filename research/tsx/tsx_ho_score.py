#!/usr/bin/env python3
"""TS_MKT_EXT addendum 1 §5/§7: cham W9 tu out JSON cua ecm_mtm_h.py (baseline ho4-k24-b-s* vs tsx-ho-x14-s*)."""
import json
import sys

W = "/home/ubuntu/claude_master/tsx/ho"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
m = json.load(open(W + "/ho_mtm.json"))
R = m["runs"]
res = json.load
rows, defer = {}, {}
for s in SEEDS:
    b, x = R["ho4-k24-b-s%d" % s], R["tsx-ho-x14-s%d" % s]
    rj = json.load(open(W + "/res_tsx-ho-x14-s%d.json" % s))
    defer[s] = rj["tsx"][3]
    rows[s] = {w: {k: [b[w][k], x[w][k]] for k in ("sum_pnl", "roi", "maxdd", "n")} for w in ("W9", "Q1", "Q2", "Q3")}
    rows[s]["eqcheck"] = [b["eqcheck"], x["eqcheck"]]
dp = {s: rows[s]["W9"]["sum_pnl"][1] - rows[s]["W9"]["sum_pnl"][0] for s in SEEDS}
dd = {s: rows[s]["W9"]["maxdd"][1] - rows[s]["W9"]["maxdd"][0] for s in SEEDS}
dr = {s: rows[s]["W9"]["roi"][1] - rows[s]["W9"]["roi"][0] for s in SEEDS}
mp, md = sum(dp.values()) / 8, sum(dd.values()) / 8
n_ge0 = sum(v >= 0 for v in dp.values())
n_gt0 = sum(v > 0 for v in dp.values())
base_roi = sum(rows[s]["W9"]["roi"][0] for s in SEEDS) / 8
s5 = sum(v > 0 for v in defer.values()) >= 6
if not s5:
    verdict = "NON-INFORMATIVE"
elif (mp < 0 and n_gt0 <= 3) or md < -2.0:
    verdict = "REJECT"
elif mp > 0 and n_ge0 >= 6 and md >= -1.0:
    verdict = "CONFIRM"
else:
    verdict = "INCONCLUSIVE"
out = dict(verdict=verdict, mean_dPnL=mp, mean_dMaxDD=md, mean_dROI=sum(dr.values()) / 8, n_dPnL_ge0=n_ge0,
           n_dPnL_gt0=n_gt0, s5_defer_ok=s5, defer=defer, dPnL=dp, dMaxDD=dd, dROI=dr, base_roi_W9_mean=base_roi,
           rows=rows, mtm_check=m.get("mtm_check"), dropped=m.get("dropped"))
json.dump(out, open(W + "/ts_mkt_ext_ho.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1, default=str))
for s in SEEDS:
    r = rows[s]
    print(s, "W9 pnl %.0f->%.0f roi %.2f->%.2f dd %.2f->%.2f" % (r["W9"]["sum_pnl"][0], r["W9"]["sum_pnl"][1], r["W9"]["roi"][0],
          r["W9"]["roi"][1], r["W9"]["maxdd"][0], r["W9"]["maxdd"][1]),
          "Q1 %.0f Q2 %.0f Q3 %.0f" % tuple(r[q]["sum_pnl"][1] - r[q]["sum_pnl"][0] for q in ("Q1", "Q2", "Q3")),
          "eq", r["eqcheck"])
