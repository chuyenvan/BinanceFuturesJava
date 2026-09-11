import logging, pandas as pd, numpy as np
logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("sizing")
REF = "/home/ubuntu/java/devrun/X1_C3_FULL_PARITY_R/storage/printDone.csv"
d = pd.read_csv(REF)
d.columns = [c.strip() for c in d.columns]
d = d[["level", "start", "end", "margin", "pnl"]].copy()
d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M").astype("int64") // 10**6
d["te"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce").astype("int64") // 10**6
d["year"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M").dt.year
cl = d.dropna(subset=["end"]).sort_values("te")
ends = cl["te"].values
cum = np.cumsum(cl["pnl"].values)
idx = np.searchsorted(ends, d["ts"].values, "left")
d["eq"] = 35000.0 + np.where(idx > 0, cum[np.clip(idx - 1, 0, len(cum) - 1)], 0.0)
d["pct"] = 100.0 * d["margin"] / d["eq"]
LOG.info("n=%d  equity cuoi=%.0f", len(d), 35000.0 + d["pnl"].sum())
LOG.info("%-6s %6s %11s %11s %10s %9s %9s", "nam", "n", "meanMargin", "medMargin", "meanEq", "mean%eq", "med%eq")
for y, g in d.groupby("year"):
    LOG.info("%-6d %6d %11.1f %11.1f %10.0f %9.3f %9.3f", y, len(g), g["margin"].mean(),
             g["margin"].median(), g["eq"].mean(), g["pct"].mean(), g["pct"].median())
LOG.info("%-6s %6d %11.1f %11.1f %10.0f %9.3f %9.3f", "TONG", len(d), d["margin"].mean(),
         d["margin"].median(), d["eq"].mean(), d["pct"].mean(), d["pct"].median())
LOG.info("--- theo level (sleeve) ---")
for lv, g in d.groupby("level"):
    LOG.info("%-22s n=%-5d meanMargin=%9.1f mean%%eq=%6.3f pnl=%11.1f", lv, len(g),
             g["margin"].mean(), g["pct"].mean(), g["pnl"].sum())
