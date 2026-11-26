"""A step 1: re-run levz_b1 port (DEV 2022-01-01..2025-12-31 contiguous) for REF cfgs + top-50 valid family; attach causal features.
Outputs: out/a_trades.parquet (one row per trade per cfg), out/a_eq_hourly.parquet (cfg_id, t, eq, expo, n_open),
out/a_check.json (DEV metrics vs grid_b1)."""
import sys
import os
import json
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import an_common as A
import numpy as np
import pandas as pd

log = logging.getLogger('levz_an.a_run')


def main():
    A.setup_log('a_run')
    CB, P, X = A.b1()
    m = A.meta()
    syms = m['syms']
    g, fam = A.family(50)
    cfgs = list(A.REF) + [c for c in fam if c not in A.REF]
    gi = g.set_index('cfg_id')
    T = X.load_table()
    cz = np.load(CB.WORK + '/cand_b1.npz')
    hz = np.load(CB.WORK + '/hourly.npz')
    CLH, has1m = hz['CLH'], hz['has1m']
    k0, kl = A.dev_k()
    trs, eqs, chk = [], [], []
    cache = {}
    for cid_ in cfgs:
        r = gi.loc[cid_]
        key = (int(r['W']), r['E'], float(r['zmin']))
        if key not in cache:
            cache[key] = P.load_class(cz, *key)
        xv = P.XView(T, CB.xidx(r['SL'], r['H'], r['arm'], r['gap']))
        tr, eq, met = P.run(int(r['K']), cache[key], xv, k0, kl)
        chk.append(dict(cfg_id=int(cid_), ret=met['ret'], grid_ret=float(r['DEV_ret']), n=int(met['n']), grid_n=int(r['DEV_n']),
                        acct_err=met['acct_err']))
        tr['cfg_id'] = int(cid_)
        tr['size'] = tr['notional_in']
        trs.append(tr)
        # open count per hour
        n = kl - k0 + 1
        d = np.zeros(n + 1)
        np.add.at(d, (tr['ke'].values - k0), 1)
        np.add.at(d, (tr['kx'].values - k0), -1)
        eq['n_open'] = np.cumsum(d)[:n]
        eq['cfg_id'] = int(cid_)
        eqs.append(eq)
    tr = pd.concat(trs, ignore_index=True)
    eq = pd.concat(eqs, ignore_index=True)
    assert int(eq['t'].max()) < A.CUT
    ck = pd.DataFrame(chk)
    ck['dret'] = ck['ret'] - ck['grid_ret']
    log.info('check max|dret|=%.3e max|dn|=%d max|acct|=%.2e', ck['dret'].abs().max(), int((ck['n'] - ck['grid_n']).abs().max()),
             ck['acct_err'].abs().max())
    assert ck['dret'].abs().max() < 1e-9 and (ck['n'] == ck['grid_n']).all()
    # features (causal: info at T_k; prices up to the entry close)
    U = {}
    for W in (7, 14):
        U[W] = A.dense_sig(W, syms)
    X_oi = A.dense_oi(syms)
    qv30 = A.dense_qv30(syms)
    btc7, ew7 = A.market(CLH, has1m, U[7]['u'], syms)
    gz = np.load(CB.WORK + '/gaps.npz')
    first = gz['first']
    ke = tr['ke'].values.astype(np.int64)
    c = tr['c'].values.astype(np.int64)
    Wv = tr['cfg_id'].map(gi['W']).values.astype(int)
    for kk in ('z_oi', 'z_f', 'f'):
        tr[kk] = np.where(Wv == 7, U[7][kk][ke, c], U[14][kk][ke, c])
    with np.errstate(invalid='ignore', divide='ignore'):
        tr['doi24'] = X_oi[ke, c] / X_oi[ke - 24, c] - 1.0
        tr['r24'] = CLH[ke, c] / CLH[ke - 24, c] - 1.0
    tr['qv30'] = qv30[ke, c]
    tr['age_d'] = (ke * 60 - first[c]) / 1440.0
    tr['age_cens'] = first[c] == 0
    tr['hod'] = ke % 24
    tr['btc7'] = btc7[ke]
    tr['ew7'] = ew7[ke]
    tr['t_entry'] = A.H0 + ke * A.H + A.M
    tr['t_exit'] = A.H0 + ke * A.H + tr['j'].values * A.M + A.M
    tr.loc[tr['reason'] == 'eod', 't_exit'] = A.H0 + tr['kx'] * A.H
    assert int(tr['t_exit'].max()) < A.CUT
    tr['sym'] = np.array(syms, dtype=object)[c]
    tr['hold_h'] = tr['j'] / 60.0
    tr['mae'] = tr['mx'] - 1.0
    tr['year'] = A.dts(tr['t_entry']).year
    tr['year_x'] = A.dts(tr['t_exit']).year
    tr.to_parquet(A.OUT + '/a_trades.parquet', index=False)
    eq.to_parquet(A.OUT + '/a_eq_hourly.parquet', index=False)
    mk = pd.DataFrame({'k': np.arange(len(btc7)), 'btc7': btc7, 'ew7': ew7})
    mk.to_parquet(A.OUT + '/a_market_hourly.parquet', index=False)
    with open(A.OUT + '/a_check.json', 'w') as fh:
        json.dump(dict(cfgs=cfgs, family=fam, check=chk), fh, indent=1, default=float)
    log.info('a_run done trades=%d cfgs=%d', len(tr), len(cfgs))


if __name__ == '__main__':
    main()
