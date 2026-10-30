import pandas as pd, numpy as np
M = pd.read_parquet('/home/ubuntu/claude_master/gst1030/live/buffer_labeled.parquet')
M['day'] = pd.to_datetime(M.ts + 7 * 3600000, unit='ms').dt.strftime('%m-%d')
g = M.groupby('day').agg(n=('r', 'size'), matched=('symbol', lambda s: round(s.notna().mean(), 4)),
                         tf=('kind', lambda s: round((s == 'TRADFI').mean(), 4)), held=('held', 'mean'))
g['held'] = g.held.round(4)
print(g.to_string())
x = M[M.symbol.isna()]
print('unmatched r quantiles', x.r.quantile([0.5, 0.99, 0.9999]).round(6).to_dict())
