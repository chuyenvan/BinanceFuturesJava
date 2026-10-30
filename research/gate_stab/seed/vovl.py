#!/usr/bin/env python3
"""vovl.py — cham V-OVL theo PREREG_PARITY_V12_DRY ADD4 (feb32107). KHONG nhin ket qua truoc khi chay.
Usage: vovl.py --trace A_trace.csv[.gz] --live-labeled live_labeled.parquet --tcut-ms T [--printdone A_printDone.csv] --out vovl.json"""
import argparse, json, datetime as dt
import numpy as np, pandas as pd
H, DAY = 3600000, 86400000
PCT = float(np.float32(0.999950829))
OVL0 = int((dt.datetime(2026, 10, 17) - dt.datetime(1970, 1, 1)).total_seconds() * 1000) - 7 * H
EXCL_DAYS = {'2026-10-25', '2026-10-26', '2026-10-27'}


def q_of(a):
    m = len(a)
    if m == 0: return np.nan
    k = min(m - 1, max(0, int(np.floor(PCT * (m - 1)))))
    return float(np.partition(a, k)[k])


ap = argparse.ArgumentParser()
ap.add_argument('--trace', required=True); ap.add_argument('--live-labeled', required=True)
ap.add_argument('--tcut-ms', type=int, required=True); ap.add_argument('--printdone'); ap.add_argument('--out', required=True)
a = ap.parse_args()
A = pd.read_csv(a.trace, dtype={'ts': np.int64, 'sp': np.float32, 'p15': np.float32, 'r': np.float32})
M = pd.read_parquet(a.live_labeled)
day = lambda ts: pd.to_datetime(pd.Series(ts) + 7 * H, unit='ms').dt.strftime('%Y-%m-%d').values
A['day'] = day(A.ts)
ovl_days = sorted(d for d, g in M.groupby('day') if d >= '2026-10-17' and d not in EXCL_DAYS and bool(g.day_full.iloc[0])
                  and d < day([a.tcut_ms])[0])
Ao = A[A.day.isin(ovl_days)].copy()
Mo = M[M.day.isin(ovl_days)].copy()
Cp = Mo[Mo.clean].copy()
Cp['sp'] = Cp.gateValue.astype(np.float32)
Mo['sp'] = Mo.gateValue.astype(np.float32)
# (i) giao (ts, sp)
Ao['k'] = Ao.groupby(['ts', 'sp']).cumcount(); Cp['k'] = Cp.groupby(['ts', 'sp']).cumcount(); Mo['k'] = Mo.groupby(['ts', 'sp']).cumcount()
J = Ao.merge(Cp[['ts', 'sp', 'k', 'r', 'symbol']], on=['ts', 'sp', 'k'], how='inner', suffixes=('_A', '_C'))
rel = (J.r_A.astype(np.float64) - J.r_C.astype(np.float64)).abs() / J.r_C.astype(np.float64).abs()
i_frac = float((rel <= 1e-9).mean()) if len(J) else float('nan')
# (ii) q theo gio
ta, ra = A.ts.values, A.r.values
mix_mask_A = (A.ts < OVL0) | ~A.day.isin(ovl_days)
tm = np.concatenate([A.ts.values[mix_mask_A], Cp.ts.values]); rm = np.concatenate([A.r.values[mix_mask_A], Cp.r.values.astype(np.float32)])
hours = sorted(set((Cp.ts // H * H).tolist()))
dq = []
for h in hours:
    qa = q_of(ra[(ta >= h - 90 * DAY) & (ta < h)]); qm = q_of(rm[(tm >= h - 90 * DAY) & (tm < h)])
    dq.append(abs(qm - qa) / qa)
dq = np.array(dq); ii_nan = int(np.isnan(dq).sum()); dq = dq[~np.isnan(dq)]
# (iii) khong giao (chi bao)
Ao2 = Ao.merge(Cp[['ts', 'sp', 'k']].assign(inC=1), on=['ts', 'sp', 'k'], how='left')
Aonly = Ao2[Ao2.inC.isna()].drop(columns='inC')
lk = Aonly.merge(Mo[['ts', 'sp', 'k', 'kind', 'held', 'symbol']], on=['ts', 'sp', 'k'], how='left')
cat_A = np.where(lk.symbol.isna(), 'ngoai_top24_live(LEGACY r4f/so sim/khac)',
                 np.where(lk.kind.isin(['TRADFI', 'INDEX']), 'universe', np.where(lk.held == True, 'giu_o_live', 'khac')))
Conly = Cp.merge(Ao[['ts', 'sp', 'k']].assign(inA=1), on=['ts', 'sp', 'k'], how='left')
Conly = Conly[Conly.inA.isna()]
cat_C = np.full(len(Conly), 'khac(so sim/top-24 sim)', dtype=object)
if a.printdone:
    d = pd.read_csv(a.printdone, index_col=False, dtype=str)
    d['sym'] = d.sym.str.strip() + 'USDT'
    tomin = lambda s: (pd.to_datetime(s.str.strip(), format='%Y%m%d %H:%M').values.astype('datetime64[ms]').astype(np.int64) - 7 * H)
    d['s'] = tomin(d.start); d['e'] = tomin(d.end)
    hs = np.zeros(len(Conly), bool)
    for sym, g in d.groupby('sym'):
        idx = np.nonzero(Conly.symbol.values == sym)[0]
        for s0, e0 in zip(g.s.values, g.e.values):
            hs[idx[(Conly.ts.values[idx] > s0) & (Conly.ts.values[idx] < e0)]] = True
    cat_C = np.where(hs, 'giu_o_sim', cat_C)
res = dict(prereg='ADD4 feb32107', ovl_days=ovl_days, n_A_ovl=int(len(Ao)), n_Cp_ovl=int(len(Cp)), n_pairs=int(len(J)),
           i_frac_rel_le_1e9=i_frac, i_pass=bool(i_frac >= 0.99),
           ii_hours=int(len(dq)), ii_median=float(np.median(dq)) if len(dq) else None, ii_max=float(dq.max()) if len(dq) else None,
           ii_nan_hours=ii_nan, ii_pass=bool(len(dq) and ii_nan == 0 and np.median(dq) <= 0.01 and dq.max() <= 0.05),
           iii_A_only=pd.Series(cat_A).value_counts().to_dict(), iii_C_only=pd.Series(cat_C).value_counts().to_dict())
res['seed_usable'] = bool(res['i_pass'] and res['ii_pass'])
json.dump(res, open(a.out, 'w'), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
