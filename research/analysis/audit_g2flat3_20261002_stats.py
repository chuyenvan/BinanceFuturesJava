#!/usr/bin/env python3
"""AUDIT G2FLAT3 2026-10-02 — 0-sim, chi doc artifact Kaggle da co (printDone.csv + sim.out).
DEV <= 2025-12-31. Khong chay Java. Output: logging + JSON ~/claude_master/1002/b0stats.json
"""
import csv, re, json, math, collections, logging, sys
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(message)s")
L = logging.getLogger("a1002")
BASE = "/home/ubuntu/kaggle_sim/out/%s/"
TAGS = {"B0": "de-p1", "G2": "gdv2-g2", "R4": "cp-r4-parity", "R0base": "p2-r0-base", "T170old": "r4-par-t170",
        "K24": "de-p2", "PROP50": "trail2-g2-prop50", "PROP30": "trail2-g2-prop30", "FLAT5": "trail2-g2-flat5"}
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:\s*(-?\d+) pD:\s*(-?\d+)\s+m:\s*(-?\d+)\s+max:\s*(-?\d+)\s+(-?\d+)\s+unP:\s*(-?\d+)")
COST_SIM = 0.000982 + 2 * 0.000067
COST_OLD = 0.008


def load(tag):
    eq, mm = collections.OrderedDict(), {}
    for line in open(BASE % tag + "logs/sim.out", errors="ignore"):
        if "BudgetManagerSimple: Update" not in line:
            continue
        m = RX.search(line)
        if m:
            d = m.group(1)
            eq[d] = float(m.group(2)) + float(m.group(7))
            mm[d] = (float(m.group(4)), float(m.group(5)), float(m.group(6)))
    rows = []
    for r in csv.DictReader(open(BASE % tag + "storage/printDone.csv")):
        try:
            rows.append(dict(sym=r["sym"], st=r["start"], en=r["end"], lvl=r["level"], status=r["status"],
                             entry=float(r["entry"]), tp=float(r["tp"]), qty=float(r["quantity"]),
                             margin=float(r["margin"]), pnl=float(r["pnl"]), fund=float(r["funding"] or 0),
                             profit=float(r["profit"])))
        except Exception:
            continue
    return eq, mm, rows


def ddstats(vals):
    pk, mdd, uw, cur = None, 0.0, 0, 0
    for v in vals:
        if pk is None or v >= pk:
            pk, cur = v, 0
        else:
            cur += 1
        mdd = min(mdd, v / pk - 1)
        uw = max(uw, cur)
    return mdd * 100, uw


def episodes(rows):
    days = sorted({r["en"][:8] for r in rows})
    import datetime as dt
    D = [dt.datetime.strptime(x, "%Y%m%d") for x in days]
    eps, s, p = [], D[0], D[0]
    for x in D[1:]:
        if (x - p).days > 2:
            eps.append((s, p)); s = x
        p = x
    eps.append((s, p))
    out = []
    for a, b in eps:
        sm = sum(r["pnl"] for r in rows if a <= dt.datetime.strptime(r["en"][:8], "%Y%m%d") <= b)
        out.append((a.strftime("%Y%m%d"), b.strftime("%Y%m%d"), sm))
    return out


def summarize(name, tag, res):
    eq, mm, rows = load(tag)
    days = list(eq.keys())
    vals = [eq[d] for d in days]
    yrs = (len(days) - 1) / 365.25
    cagr = ((vals[-1] / vals[0]) ** (1 / yrs) - 1) * 100
    mdd, uw = ddstats(vals)
    # 2022+ window
    d22 = [d for d in days if d >= "20211231"]
    v22 = [eq[d] for d in d22]
    cagr22 = ((v22[-1] / v22[0]) ** (365.25 / (len(d22) - 1)) - 1) * 100
    mdd22, uw22 = ddstats(v22)
    # year ROI
    yroi, prev = {}, vals[0]
    for y in ["2021", "2022", "2023", "2024", "2025"]:
        ys = [d for d in days if d[:4] == y]
        if not ys:
            continue
        e = eq[ys[-1]]
        yroi[y] = round((e / prev - 1) * 100, 2)
        yroi[y + "_ddday"] = round(ddstats([prev] + [eq[d] for d in ys])[0], 2)
        prev = e
    # exposure: monthly margin max / equity
    ratios = []
    for d in days:
        mmax_month = mm[d][2]
        if mmax_month > 0 and eq[d] > 0:
            ratios.append(mmax_month / eq[d])
    ratios = np.array(ratios) if ratios else np.array([0.0])
    # concurrent margin (upper bound: full final margin tu luc vao)
    ev = []
    for r in rows:
        ev.append((r["st"], 1, r["margin"])); ev.append((r["en"], 0, -r["margin"]))
    ev.sort()
    cur, peak_ratio, conc_cnt, maxcnt, peak_at = 0.0, 0.0, 0, 0, ""
    for t, k, m in ev:
        cur += m
        conc_cnt += 1 if k == 1 else -1
        maxcnt = max(maxcnt, conc_cnt)
        e = eq.get(t[:8]) or vals[-1]
        if cur / e > peak_ratio:
            peak_ratio, peak_at = cur / e, t
    notional = sum(r["margin"] for r in rows)
    pnl = np.array([r["pnl"] for r in rows])
    # implied cost check
    imp = []
    for r in rows:
        gross = r["qty"] * (r["tp"] - r["entry"])
        n0 = r["qty"] * r["entry"]
        if n0 > 0:
            imp.append(((gross - r["pnl"] - r["fund"]) / n0, (gross - r["pnl"] + r["fund"]) / n0))
    imp = np.array(imp)
    s = np.sort(pnl)[::-1]
    k1 = max(1, int(math.ceil(0.01 * len(s))))
    eps = sorted(episodes(rows), key=lambda x: -x[2])
    tot = pnl.sum()
    warm = [r for r in rows if r["st"][:8] <= "20210708"]
    by_lvl = collections.Counter(r["lvl"] for r in rows)
    notional_y = collections.defaultdict(float)
    for r in rows:
        notional_y[r["en"][:4]] += r["margin"]
    out = dict(tag=tag, n=len(rows), eq_end=vals[-1], cagr=round(cagr, 2), maxdd_day=round(mdd, 2), uw_day=uw,
               cagr22=round(cagr22, 2), maxdd22_day=round(mdd22, 2), uw22=uw22, yroi=yroi,
               marginmonth_over_eq_max=round(float(ratios.max()), 3), marginmonth_over_eq_p99=round(float(np.percentile(ratios, 99)), 3),
               conc_margin_ub_peak=round(peak_ratio, 3), conc_margin_peak_at=peak_at, max_concurrent_trades=maxcnt,
               sum_notional=round(notional), sum_pnl=round(float(tot)), notional_over_pnl=round(notional / tot, 2),
               notional_by_year={k: round(v) for k, v in sorted(notional_y.items())},
               implied_cost_med_fundminus=round(float(np.median(imp[:, 0])), 6), implied_cost_med_fundplus=round(float(np.median(imp[:, 1])), 6),
               implied_cost_p05_p95=[round(float(np.percentile(imp[:, 0], 5)), 6), round(float(np.percentile(imp[:, 0], 95)), 6)],
               top1_trade_pct=round(100 * s[0] / tot, 2), top1pct_trades_pct=round(100 * s[:k1].sum() / tot, 2),
               n_episodes=len(eps), top5_episodes=[(a, b, round(x), round(100 * x / tot, 1)) for a, b, x in eps[:5]],
               top5_ep_share=round(100 * sum(x for _, _, x in eps[:5]) / tot, 1),
               warmup_trades=len(warm), warmup_pnl=round(sum(r["pnl"] for r in warm)), levels=dict(by_lvl))
    # cost sensitivity linear (khong compounding)
    out["cost_sens"] = {str(dc): round(-dc * notional) for dc in (0.0005, 0.001, 0.002)}
    if name == "T170old":
        out["pnl_adj_to_simcost"] = round(float(tot + (COST_OLD - COST_SIM) * notional))
    res[name] = out
    L.info("%s %s", name, json.dumps(out, ensure_ascii=False))


res = {}
for name, tag in TAGS.items():
    try:
        summarize(name, tag, res)
    except Exception as e:
        L.info("%s ERR %r", name, e)
json.dump(res, open("/home/ubuntu/claude_master/1002/b0stats.json", "w"), indent=1)
