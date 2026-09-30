#!/usr/bin/env python3
"""P1 SHORT_FEASIBILITY — counterfactual short tren tap lenh long cua G2 (0-sim, chi doc).
Chot TRUOC o docs/prereg/PREREG_SHORT_FEASIBILITY.md. KHONG chay sim, KHONG sua .java.
Output: research/analysis/out/short_feas_reverse.json
"""
import csv, json, os, collections

ART = "/home/ubuntu/kaggle_sim/out/de-p1"
CSV = os.path.join(ART, "storage", "printDone.csv")
FEE_SIDE = 0.000982      # SIM_RATE_FEE
SLIP_SIDE = 0.000067     # SIM_SLIPPAGE_RATE
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "short_feas_reverse.json")


def f(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def main():
    rows = list(csv.DictReader(open(CSV)))
    n = len(rows)
    notional = [f(r["quantity"]) * f(r["entry"]) for r in rows]
    pnl = [f(r["pnl"]) for r in rows]
    fund = [f(r["funding"]) for r in rows]
    prof = [f(r["profit"]) for r in rows]   # = 100*(tp/entry-1)
    totN = sum(notional); totP = sum(pnl); totF = sum(fund)
    fee_rt = 2 * FEE_SIDE * totN
    slip_rt = 2 * SLIP_SIDE * totN
    net_short = -totP - fee_rt - slip_rt     # funding tu lat dau (xem prereg P1)
    # by-year
    by = collections.defaultdict(lambda: dict(n=0, pnl=0.0, notional=0.0))
    for r, ni, pi in zip(rows, notional, pnl):
        y = r["start"][:4]
        by[y]["n"] += 1; by[y]["pnl"] += pi; by[y]["notional"] += ni
    res = dict(
        source=CSV, n=n, notional_sum=totN, pnl_long_sum=totP, funding_sum=totF,
        fee_rt=fee_rt, slip_rt=slip_rt, net_short=net_short,
        long=dict(price_ret_mean_pct=sum(prof) / n, win_pct=100 * sum(1 for x in prof if x > 0) / n),
        short=dict(price_ret_mean_pct=-sum(prof) / n, win_pct=100 * sum(1 for x in prof if x < 0) / n),
        by_year={k: dict(n=v["n"], pnl_long=round(v["pnl"], 1),
                         net_short_est=round(-v["pnl"] - 2 * (FEE_SIDE + SLIP_SIDE) * v["notional"], 1))
                 for k, v in sorted(by.items())},
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(res, open(OUT, "w"), indent=1)
    print("n=%d pnl_long=%.0f net_short=%.0f (fee_rt=%.0f slip_rt=%.0f)" % (n, totP, net_short, fee_rt, slip_rt))
    print("short win%%=%.1f  ->  wrote %s" % (res["short"]["win_pct"], OUT))


if __name__ == "__main__":
    main()
