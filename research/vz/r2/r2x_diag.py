"""Chan doan V2 R2X (KHONG dung pnl/ret). Doc legs parquet, chi dung cot feature/mid/snap."""
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/vz/r2")
import r2x_bookdepth as R  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("r2xd")
d = pd.read_parquet(R.W + "/r2x_legs_%s.parquet" % R.TAG)
rows = []
cache = {}
for i, r in d.iterrows():
    if pd.isna(r.mid):
        continue
    lo, hi, cl = np.inf, -np.inf, np.nan
    for tb in (r.t0 - pd.Timedelta(minutes=1), r.t0):
        key = (r.symbol, tb.strftime("%Y-%m-%d"))
        if key not in cache:
            cache[key] = R.kline_day(*key)
        k = cache[key]
        ms = int(tb.value // 10**6)
        if k is not None and ms in k.index:
            lo, hi = min(lo, k.at[ms, "low"]), max(hi, k.at[ms, "high"]); cl = k.at[ms, "close"]
    if np.isfinite(lo):
        ok = lo * 0.998 <= r.mid <= hi * 1.002
        dev = 0.0 if ok else (r.mid / hi - 1 if r.mid > hi else r.mid / lo - 1)
        rows.append(dict(sym=r.symbol, t0=r.t0, year=r.t0.year, ok=ok, dev=dev, lag_s=(r.t_dec - r.snap_ts).total_seconds(),
                         mid_close=r.mid / cl - 1, burst=r.t0))
X = pd.DataFrame(rows)
log.info("theo nam: %s", X.groupby("year").ok.agg(["mean", "size"]).round(4).to_dict())
bad = X[~X.ok]
log.info("so chan fail %d; dev |trung vi| %.4f p90 %.4f max %.4f", len(bad), bad.dev.abs().median(), bad.dev.abs().quantile(.9), bad.dev.abs().max())
log.info("lag snap (s) fail med %.0f vs ok med %.0f", bad.lag_s.median(), X[X.ok].lag_s.median())
log.info("fail theo dot (top): %s", bad.groupby("burst").size().sort_values(ascending=False).head(8).to_dict())
log.info("ty le fail trong cac dot do: %s", {str(b): round(1 - X[X.burst == b].ok.mean(), 2) for b in bad.groupby("burst").size().sort_values(ascending=False).head(8).index})
log.info("fail theo sym top: %s", bad.sym.value_counts().head(8).to_dict())
# thu noi bang [low*0.995, high*1.005] cho chan doan (KHONG doi tieu chi)
for tol in (0.002, 0.005, 0.01):
    pass
log.info("dev fail phan bo: <0.5%%: %d, 0.5-1%%: %d, 1-3%%: %d, >3%%: %d",
         (bad.dev.abs() < .005).sum(), ((bad.dev.abs() >= .005) & (bad.dev.abs() < .01)).sum(),
         ((bad.dev.abs() >= .01) & (bad.dev.abs() < .03)).sum(), (bad.dev.abs() >= .03).sum())
