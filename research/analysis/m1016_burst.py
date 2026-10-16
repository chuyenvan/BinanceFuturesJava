import logging, sys
import pandas as pd, numpy as np
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("burst")
d = pd.read_csv(sys.argv[1], index_col=False)
d["t0"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M")
d["t1"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce")
d["yr"] = d.t0.dt.year
log.info("n=%d range %s -> %s  sum_pnl=%.0f", len(d), d.t0.min(), d.t0.max(), d.pnl.sum())
b = d.groupby("t0").agg(n=("pnl", "size"), pnl=("pnl", "sum"), win=("pnl", lambda x: (x > 0).mean())).reset_index()
b["yr"] = b.t0.dt.year
log.info("bursts=%d  days_with_entry=%d", len(b), d.t0.dt.date.nunique())
log.info("burst size dist: %s", b.n.describe(percentiles=[.5, .75, .9, .99]).round(1).to_dict())
for lo, hi in [(1, 1), (2, 5), (6, 12), (13, 24)]:
    s = b[(b.n >= lo) & (b.n <= hi)]
    log.info("size %2d-%2d: bursts=%4d trades=%5d pnl=%10.0f share=%.1f%% mean/burst=%8.0f win_bursts=%.2f",
             lo, hi, len(s), s.n.sum(), s.pnl.sum(), 100 * s.pnl.sum() / d.pnl.sum(), s.pnl.mean(), (s.pnl > 0).mean())
bs = b.sort_values("pnl")
tot = d.pnl.sum()
log.info("top10 bursts pnl=%.0f (%.1f%% of total); worst10=%.0f", bs.pnl.tail(10).sum(), 100 * bs.pnl.tail(10).sum() / tot, bs.pnl.head(10).sum())
log.info("worst 5 bursts:\n%s", bs.head(5)[["t0", "n", "pnl", "win"]].to_string(index=False))
log.info("best 5 bursts:\n%s", bs.tail(5)[["t0", "n", "pnl", "win"]].to_string(index=False))
# max concurrent open
ev = pd.concat([pd.DataFrame({"t": d.t0, "x": 1}), pd.DataFrame({"t": d.t1.fillna(d.t0.max()), "x": -1})]).sort_values(["t", "x"])
ev["open"] = ev.x.cumsum()
log.info("max concurrent open=%d  p99=%.0f", ev.open.max(), ev.open.quantile(.99))
log.info("per year:\n%s", d.groupby("yr").agg(n=("pnl", "size"), pnl=("pnl", "sum")).join(
    b.groupby("yr").agg(bursts=("n", "size"), big24=("n", lambda x: (x >= 13).sum()))).to_string())
log.info("per-burst pnl / margin-sum (mean ret of burst) for size>=13: %s",
         (d.assign(ret=d.pnl / d.margin).groupby("t0").ret.mean()[b.set_index("t0").n >= 13]).describe().round(4).to_dict())
