"""Buoc 0 (V4) — chi tiet GS100 lam moc tham chieu cho nhanh B/C (nen la GS100)."""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

tags = sys.argv[1:]
print("=== CONCURRENCY (so CUM mo dong thoi) + HOLDING TIME ===")
print("%-12s %8s %9s %9s %9s %9s %9s %9s %9s" % (
    "tag", "n_cum", "conc_tb", "conc_p50", "conc_p95", "conc_max", "hold_p50", "hold_p90", "hold_tb"))
for t in tags:
    d = C.trades(t)
    cl = d.groupby(["sym", "end"]).agg(
        st=("ts", "min"), pnl=("pnl", "sum")).reset_index()
    cl["et"] = pd.to_datetime(cl["end"], format="%Y%m%d %H:%M", errors="coerce")
    cl = cl.dropna(subset=["et"])
    # concurrency: +1 luc mo, -1 luc dong, lay mau theo gio
    ev = pd.concat([
        pd.Series(1, index=cl.st), pd.Series(-1, index=cl.et)]).sort_index()
    occ = ev.cumsum().resample("1h").last().ffill().fillna(0)
    hold = (cl.et - cl.st).dt.total_seconds() / 3600.0
    print("%-12s %8d %9.2f %9.0f %9.0f %9.0f %9.1f %9.1f %9.1f" % (
        t, len(cl), occ.mean(), occ.quantile(.50), occ.quantile(.95), occ.max(),
        hold.quantile(.50), hold.quantile(.90), hold.mean()))

print()
print("=== RATE THEO NAM (muc LEG) ===")
print("%-12s %5s %6s %7s %8s %8s %9s %9s" % (
    "tag", "nam", "n", "win%", "TSloss%", "meanP", "mMargin", "pnl"))
for t in tags:
    d = C.trades(t)
    for y, g in d.groupby(d.ts.dt.year):
        r = C.rates(g)
        print("%-12s %5d %6.0f %7.2f %8.2f %8.3f %9.0f %9.0f" % (
            t, y, r["n"], r["win"], r["tsloss"], r["meanP"], r["margin"], g.pnl.sum()))

print()
print("=== maxDD + CAGR-trong-nam (tu equity ngay) ===")
print("%-12s %5s %9s %6s %10s %12s" % ("tag", "nam", "maxDD%", "UW", "ret_nam%", "equity_cuoi"))
for t in tags:
    s = C.equity(t)
    for y, sy in s.groupby(s.index.year):
        dd = (sy / sy.cummax() - 1) * 100
        uw = sy < sy.cummax()
        uwmax = int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0
        print("%-12s %5d %9.2f %6d %10.2f %12.0f" % (
            t, y, dd.min(), uwmax, (sy.iloc[-1] / sy.iloc[0] - 1) * 100, sy.iloc[-1]))
