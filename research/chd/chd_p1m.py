import pandas as pd
c = pd.read_parquet("/home/ubuntu/claude_master/chd_wk/cov_top20.parquet")
c["t"] = pd.to_datetime(c.date) + pd.to_timedelta(c.hour, unit="h")
def runs(ts):
    ts = sorted(ts); out = []; st = pv = None
    for t in ts:
        if st is None: st = pv = t
        elif t - pv == pd.Timedelta(hours=1): pv = t
        else: out.append((str(st)[:13], str(pv)[:13], int((pv - st) / pd.Timedelta(hours=1)) + 1)); st = pv = t
    if st is not None: out.append((str(st)[:13], str(pv)[:13], int((pv - st) / pd.Timedelta(hours=1)) + 1))
    return out
for s, ty in [("XPLUSDT", "open_interest"), ("WLFIUSDT", "open_interest"), ("PUMPUSDT", "trades"), ("PUMPUSDT", "open_interest"), ("ASTERUSDT", "open_interest"), ("ZECUSDT", "liquidations")]:
    x = c[c.symbol == s]; span = pd.date_range(x.t.min(), x.t.max(), freq="h")
    miss = span.difference(x[x.data_type == ty].t)
    r = runs(miss)
    print(s, ty, "missing", len(miss), "runs(top by len):", sorted(r, key=lambda z: -z[2])[:4])
