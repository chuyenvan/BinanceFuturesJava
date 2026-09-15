"""V4 doc lai (KHONG rerun sim): bang day du theo TUNG NAM cho 10 config."""
import sys
import pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

TAGS = ["RG_A_T170", "DS_GS100", "DS_GS120", "DS_GS140", "DS_GS085", "DS_GS070",
        "DS_GS055", "DS_K10_GS100", "DS_K12_GS100",
        "DS_DCA20_GS100", "DS_DCA25_GS100", "DS_DCA30_GS100"]

print("%-16s %5s %8s %10s %12s %10s %8s %6s %8s" % (
    "tag", "nam", "ret%", "dEquity$", "pnl_real$", "maxDD%", "UW", "n_leg", "eq_cuoi"))
for t in TAGS:
    try:
        s = C.equity(t); d = C.trades(t)
    except Exception as e:
        print("%-16s LOI %s" % (t, e)); continue
    e_end = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce")
    d = d.assign(ey=e_end.dt.year)
    for y, sy in s.groupby(s.index.year):
        dd = (sy / sy.cummax() - 1) * 100
        uw = sy < sy.cummax()
        uwmax = int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0
        g = d[d.ey == y]
        print("%-16s %5d %8.2f %10.0f %12.0f %10.2f %8d %6d %8.0f" % (
            t, y, (sy.iloc[-1] / sy.iloc[0] - 1) * 100, sy.iloc[-1] - sy.iloc[0],
            g.pnl.sum() if len(g) else 0.0, dd.min(), uwmax, len(g), sy.iloc[-1]))
    dda = (s / s.cummax() - 1) * 100
    uwa = s < s.cummax()
    print("%-16s %5s %8.2f %10.0f %12.0f %10.2f %8d %6d %8.0f" % (
        t, "TONG", (s.iloc[-1] / s.iloc[0] - 1) * 100, s.iloc[-1] - s.iloc[0],
        d.pnl.sum(), dda.min(),
        int(uwa.groupby((~uwa).cumsum()).sum().max()), len(d), s.iloc[-1]))
    print()
