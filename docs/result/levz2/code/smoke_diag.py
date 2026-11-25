"""LEVZ2 smoke diagnostics: classify every mismatch between the smoke run (W14 E0 z2.5 K10 SL50 H24, no trail/DCA)
and tier-1 events_A1 (explore+confirm) on (sym, te). Reads out/smoke_vs_A1.parquet, out/smoke_trades.parquet, work/inputs.npz.
usage: python3 code/smoke_diag.py -> out/smoke_diag.json"""
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]
import json
import logging
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

BASE = '/home/ubuntu/claude_master/w3/levz2'
H = 3600000
H0 = 1638316800000
log = logging.getLogger('levz2.diag')


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    z = np.load(BASE + '/work/inputs.npz')
    syms = [str(s) for s in z['syms']]
    col = {s: i for i, s in enumerate(syms)}
    CL = z['CL']
    j = pd.read_parquet(BASE + '/out/smoke_vs_A1.parquet')
    tr = pd.read_parquet(BASE + '/out/smoke_trades.parquet')
    ke, kx, tc = tr['ke'].values, tr['kx'].values, tr['c'].values
    ev = j[j['_merge'] != 'left_only'][['sym', 'te', 't0', 'nop']].copy()
    t1 = j[j['_merge'] == 'right_only'].copy()
    so = j[j['_merge'] == 'left_only'].copy()
    out = {}
    cls = []
    for r in t1.itertuples():
        k = int((r.te - H0) // H)
        c = col.get(r.sym)
        n_open = int(((ke < k) & (kx > k)).sum())
        same = ((tc == c) & (ke < k) & (k - ke <= 72)).any()
        if r.nop == 1:
            cls.append('tier1_nop')
        elif c is None or not np.isfinite(CL[k, c]):
            cls.append('no_store_price_at_te')
        elif same:
            cls.append('sim_cooldown_or_open_same_coin')
        elif n_open >= 10:
            cls.append('topK_full')
        else:
            n_rank = n_open + int(((ke == k)).sum())
            cls.append('topK_cut_same_hour' if n_rank >= 10 else 'other')
    t1['cls'] = cls
    out['tier1_only'] = t1['cls'].value_counts().to_dict()
    cls = []
    evk = {}
    for r in ev.itertuples():
        evk.setdefault(r.sym, []).append(int(r.te))
    for r in so.itertuples():
        prev = [t for t in evk.get(r.sym, []) if 0 < (r.te - t) <= 72 * H]
        if prev:
            cls.append('chain_shift_tier1_t0_within_72h_before')
        else:
            later = [t for t in evk.get(r.sym, []) if 0 < (t - r.te) <= 72 * H]
            cls.append('tier1_t0_later_within_72h' if later else 'other')
    so['cls'] = cls
    out['sim_only'] = so['cls'].value_counts().to_dict()
    b = j[j['_merge'] == 'both']
    out['matched_by_reason'] = b['reason'].value_counts().to_dict()
    sl = b[b['reason'] == 'sl']
    out['matched_sl_tier1_mae24_ge_0.5'] = int((sl['mae_24'] >= 0.5).sum())
    out['matched_sl_n'] = int(len(sl))
    out['matched_sl_gross_sim_mean'] = float(sl['gross_ret'].mean()) if len(sl) else None
    out['matched_sl_gross24_tier1_mean'] = float(sl['gross_24'].mean()) if len(sl) else None
    tm = b[b['reason'] == 'time']
    d = tm['gross_ret'] - tm['gross_24']
    out['time_n'] = int(len(tm))
    out['time_gross_diff_q'] = [float(x) for x in d.quantile([0.01, 0.05, 0.5, 0.95, 0.99])]
    out['time_frac_absdiff_le_0.5pct'] = float((d.abs() <= 0.005).mean())
    out['time_frac_absdiff_le_1pct'] = float((d.abs() <= 0.01).mean())
    out['sum_gross_all_sim'] = float((tr['gross'] / tr['notional_in']).sum())
    out['examples_other_tier1_only'] = t1[t1['cls'] == 'other'][['sym', 't0', 'te']].head(10).to_dict('records')
    out['examples_other_sim_only'] = so[so['cls'] == 'other'][['sym', 'te']].head(10).to_dict('records')
    with open(BASE + '/out/smoke_diag.json', 'w') as fh:
        json.dump(out, fh, indent=1, default=float)
    log.info('diag %s', json.dumps(out, default=float))


if __name__ == '__main__':
    main()
