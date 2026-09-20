import sys
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import numpy as np
import bigdown_struct as B

TAGS = B.TAGS
grid, px = B.hourly_grid()

results = {}
for name, tag in TAGS.items():
    d = B.load_trades_utc(tag)
    notional_grid = B.sum_notional_on_grid(d, grid)
    equity_grid = B.equity_at_grid(tag, grid)
    ratio = np.where(np.isfinite(equity_grid) & (equity_grid > 0),
                      notional_grid / equity_grid, np.nan)
    ratio = ratio[np.isfinite(ratio)]
    results[name] = dict(mean=float(np.mean(ratio)), median=float(np.median(ratio)),
                          n=int(len(ratio)))
    print(name, "overall mean=%.6f median=%.6f n=%d" % (results[name]["mean"],
          results[name]["median"], results[name]["n"]))

print()
print("P0_MULT candidate (mean ratio T170/T100) = %.6f" %
      (results["T170"]["mean"] / results["T100"]["mean"]))
print("P0_MULT candidate (median ratio T170/T100) = %.6f" %
      (results["T170"]["median"] / results["T100"]["median"] if results["T100"]["median"] > 0 else float("nan")))

# bigdown-conditional median (matches A-recon citation 0.058/0.27 approx 0.2)
flags, extra = B.build_bd_flags(grid, px)
flag_bd1a = flags["BD1a_5pct24h"]
for name, tag in TAGS.items():
    d = B.load_trades_utc(tag)
    notional_grid = B.sum_notional_on_grid(d, grid)
    equity_grid = B.equity_at_grid(tag, grid)
    ratio = np.where(np.isfinite(equity_grid) & (equity_grid > 0),
                      notional_grid / equity_grid, np.nan)
    rb = ratio[flag_bd1a]
    rb = rb[np.isfinite(rb)]
    print(name, "bigdown-only median=%.6f mean=%.6f n=%d" % (np.median(rb), np.mean(rb), len(rb)))
