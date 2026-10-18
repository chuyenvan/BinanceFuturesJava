import json
import numpy as np
import pandas as pd
j = json.load(open('/home/ubuntu/claude_master/edge_attr/score.json'))
E = json.load(open('/home/ubuntu/claude_master/vz_e1_wt/docs/result/RESULT_ENTRYCOST_MEASURE.json'))['runs']['D']['bucket']
v2 = j['validation']['V2_recomputed']
print('V2 maxabs diff', max(abs(v2[s]['sum_pnl_end'] - E[s]['spnl']) for s in v2), {s: round(v2[s]['sum_pnl_end'] - E[s]['spnl'], 4) for s in v2})
D = j['D']
print('A_alt per seed', [round(x, 3) for x in D['A_alt']['per_seed']], 'A_btc', [round(x, 3) for x in D['A_btc']['per_seed']])
print('alpha,beta alt per seed', [[round(a, 4), round(b, 3)] for a, b in D['beta_alt_alpha_beta']])
print('S0 per seed', [round(x) for x in D['S0_pnl']['per_seed']], 'tot', [round(x) for x in D['tot_pnl']['per_seed']])
print('lowL share per seed', [round(x, 3) for x in D['R3_lowL_share']['per_seed']])
print('Y1 35k dpct', [round(x, 2) for x in D['Q2']['Y1.0_35k']['dpct']['per_seed']], 'lowL', [round(x) for x in D['Q2']['Y1.0_35k']['lowL_pnl']['per_seed']])
print('breakeven lowL bps per seed', [round(x) for x in D['Q2']['flat_lowL']['breakeven_bps_lowL']['per_seed']])
# mo ta phan bi loai (KHONG thuoc luat pre-reg, chi bao cao)
d = pd.read_parquet('/home/ubuntu/claude_master/edge_attr/legs.parquet')
d = d[(d.win == 'D')]
t0 = pd.to_datetime(d.start, format='%Y%m%d %H:%M')
d = d[(t0 >= '2021-07-01') & (t0 < '2026-01-01')]
good = (d.nbar >= 1368) & (d.L24 > 0) & np.isfinite(d.sig_d) & d.hasM_alt & d.hasE_alt & d.hasM_btc & d.hasE_btc & d.end.notna()
x = d[~good]
print('excluded n', len(x), 'per seed', x.groupby('seed').size().to_dict())
print('excluded pnl/seed', round(x.pnl.sum() / 8), 'pnl/leg', round(x.pnl.mean(), 1), 'win', round((x.pnl > 0).mean(), 3), 'roi_med', round((x.pnl / x.margin).median(), 4))
print('excluded nbar describe', x.nbar.describe().round(0).to_dict())
print('excluded L24 (partial) quantiles', x.L24.quantile([.1, .5, .9]).round(-3).to_dict())
print('excluded b buckets', pd.cut(x.b, [0, 5, 12, 99]).value_counts().to_dict())
print('excluded top syms', x.sym.value_counts().head(12).to_dict())
print('incl pnl/leg', round(d[good].pnl.mean(), 1))
# share cua nhom bi loai trong tong DEV
print('excluded share of total pnl', round(x.pnl.sum() / d.pnl.sum(), 3))
# L24 median theo bucket b (crash spike?)
g = d[good]
print('L24 median by b', g.groupby(pd.cut(g.b, [0, 5, 12, 99])).L24.median().round(-5).to_dict())
