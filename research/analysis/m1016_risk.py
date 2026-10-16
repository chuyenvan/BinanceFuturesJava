import logging, sys
import pandas as pd, numpy as np
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("risk")
EQ0 = float(sys.argv[2]) if len(sys.argv) > 2 else 35000.0
d = pd.read_csv(sys.argv[1], index_col=False)
d["t0"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M")
d["t1"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce").fillna(d["t0"].max())
closed = d.sort_values("t1")[["t1", "pnl"]]
closed["cum"] = closed.pnl.cumsum()
def eq_at(t):
    i = closed.t1.searchsorted(t, side="left")
    return EQ0 + (closed.cum.iloc[i - 1] if i > 0 else 0.0)
b = d.groupby("t0").agg(n=("pnl", "size"), pnl=("pnl", "sum"), margin=("margin", "sum")).reset_index()
b["equity"] = b.t0.map(eq_at)
# open positions + margin at burst time (opened before t0, closing after t0), excluding the burst itself
st = d.t0.values; en = d.t1.values; mg = d.margin.values
b["open_before"] = [int(((st < t) & (en > t)).sum()) for t in b.t0.values]
b["margin_open_before"] = [float(mg[(st < t) & (en > t)].sum()) for t in b.t0.values]
b["loss_pct_eq"] = 100 * b.pnl / b.equity
b["burst_margin_pct_eq"] = 100 * b.margin / b.equity
b["tot_margin_pct_eq"] = 100 * (b.margin + b.margin_open_before) / b.equity
log.info("bursts=%d  eq0=%.0f final_realized_eq=%.0f", len(b), EQ0, EQ0 + d.pnl.sum())
for lo, hi in [(1, 5), (6, 12), (13, 24)]:
    s = b[(b.n >= lo) & (b.n <= hi)]
    log.info("size %2d-%2d n=%3d | pnl%%eq p5=%.2f p50=%.2f min=%.2f | burst margin%%eq p50=%.0f p95=%.0f max=%.0f | total margin%%eq p95=%.0f max=%.0f",
             lo, hi, len(s), s.loss_pct_eq.quantile(.05), s.loss_pct_eq.median(), s.loss_pct_eq.min(),
             s.burst_margin_pct_eq.median(), s.burst_margin_pct_eq.quantile(.95), s.burst_margin_pct_eq.max(),
             s.tot_margin_pct_eq.quantile(.95), s.tot_margin_pct_eq.max())
log.info("worst 10 bursts by pnl%%eq:\n%s", b.nsmallest(10, "loss_pct_eq")[["t0", "n", "pnl", "equity", "loss_pct_eq", "burst_margin_pct_eq", "open_before", "tot_margin_pct_eq"]].round(2).to_string(index=False))
# realized equity curve drawdown + share of DD episodes driven by bursts
curve = EQ0 + closed.set_index("t1").cum
dd = curve / curve.cummax() - 1
log.info("realized maxDD=%.2f%% at %s", 100 * dd.min(), dd.idxmin())
# day-level: pnl of entries by entry day
day = d.groupby(d.t0.dt.date).pnl.sum()
log.info("entry-day pnl: days=%d  worst5=%s", len(day), day.nsmallest(5).round(0).to_dict())
b.to_csv("/tmp/m1016_bursts.csv", index=False)
