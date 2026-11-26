"""C step 1: LONG system (c3 sim ledger printDone.csv, 4 runs) -> UTC legs, daily equity (realized AND MTM), hourly exposure.
printDone columns used (verified vs result.json): sym, side (all BUY), entry, tp (= exit price; profit = (tp/entry-1)*100),
start/end ('YYYYMMDD HH:MM', UTC+7 -> UTC = -7 h), quantity, margin (= entry x quantity = entry notional), pnl (net USD incl.
funding/fees; sum(pnl) = equity_final - equity_start). MTM: open legs valued at the 1m close of the bar ending at the day boundary
(levz_b1 close1m memmap, sym + 'USDT'); legs whose symbol is absent there count 0 unrealized (logged).
Outputs out/c_long_legs.parquet, out/c_long_daily.parquet (run, d, eq_real, eq_mtm, unreal, expo_mean, expo_max, n_open_mean),
out/c_long_hourly.parquet (run, k, expo, n_open), out/c_long_check.json."""
import sys
import os
import json
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import an_common as A
import numpy as np
import pandas as pd

log = logging.getLogger('levz_an.c_long')


def parse_t(s):
    t = pd.to_datetime(s.astype(str).str.strip(), format='%Y%m%d %H:%M') - pd.Timedelta(hours=7)
    return (t.values.astype('datetime64[ms]').astype(np.int64))


def main():
    A.setup_log('c_long')
    CB, P, X = A.b1()
    syms = A.meta()['syms']
    col = {s: i for i, s in enumerate(syms)}
    C1 = np.load(CB.WORK + '/close1m.npy', mmap_mode='r')
    NMIN = C1.shape[1]
    days = np.arange(A.DEV0, A.CUT + 1, 86400000, dtype=np.int64)        # 2022-01-01 .. 2026-01-01 boundaries
    hrs = A.H0 + np.arange((A.CUT - A.H0) // A.H, dtype=np.int64) * A.H
    legs_all, daily_all, hourly_all, chk = [], [], [], {}
    for run in A.LONG_RUNS:
        dd = A.LONG_DIR % run
        with open(dd + '/result.json') as fh:
            R = json.load(fh)
        d = pd.read_csv(dd + '/storage/printDone.csv')
        d = d.loc[:, ~d.columns.str.startswith('Unnamed')]
        assert len(d) == R['n_trades'] and (d['side'] == 'BUY').all()
        assert abs(d['pnl'].sum() - (R['equity_final'] - R['equity_start'])) < 1.0
        assert (np.abs(d['margin'] / (d['entry'] * d['quantity']) - 1) < 1e-5).all()
        d['ts'] = parse_t(d['start'])
        d['te'] = parse_t(d['end'])
        assert int(d['te'].max()) < A.CUT and (d['te'] >= d['ts']).all()
        hold = (d['te'] - d['ts']) / 3.6e6
        chk[run] = dict(n=len(d), sum_pnl=float(d['pnl'].sum()), eq_start=R['equity_start'], eq_final=R['equity_final'],
                        hold_vs_time_order_maxabs=float(np.abs(hold - d['time_order']).max()), first_start=int(d['ts'].min()),
                        last_end=int(d['te'].max()))
        d['run'] = run
        d['usym'] = d['sym'].astype(str) + 'USDT'
        d['c'] = d['usym'].map(col).fillna(-1).astype(int)
        E0 = float(R['equity_start'])
        # realized equity at boundaries
        te_sorted = np.sort(d['te'].values)
        cp = np.concatenate([[0.0], np.cumsum(d['pnl'].values[np.argsort(d['te'].values, kind='mergesort')])])
        eq_real = E0 + cp[np.searchsorted(te_sorted, days, 'right')]
        # unrealized at day boundaries
        unreal = np.zeros(len(days))
        miss = 0
        for r in d.itertuples(index=False):
            i0 = np.searchsorted(days, r.ts, 'left')
            i1 = np.searchsorted(days, r.te, 'left')       # boundaries D with ts <= D < te
            if i1 <= i0:
                continue
            if r.c < 0:
                miss += 1
                continue
            idx = (days[i0:i1] - A.H0) // A.M - 1
            assert (idx < NMIN).all()
            px = np.asarray(C1[r.c, idx], dtype=np.float64)
            if not np.isfinite(px).all():
                miss += 1
                px = np.where(np.isfinite(px), px, r.entry)
            unreal[i0:i1] += r.quantity * (px - r.entry)
        chk[run]['legs_unpriced'] = miss
        eq_mtm = eq_real + unreal
        assert abs(eq_real[-1] - R['equity_final']) < 1.0 and unreal[-1] == 0.0
        # hourly exposure (entry notional of open legs / realized equity at T_h)
        dlt = np.zeros(len(hrs) + 1)
        cnt = np.zeros(len(hrs) + 1)
        ih0 = np.searchsorted(hrs, d['ts'].values, 'left')
        ih1 = np.searchsorted(hrs, d['te'].values, 'left')
        np.add.at(dlt, ih0, d['margin'].values)
        np.add.at(dlt, ih1, -d['margin'].values)
        np.add.at(cnt, ih0, 1)
        np.add.at(cnt, ih1, -1)
        notl = np.cumsum(dlt)[:-1]
        nop = np.cumsum(cnt)[:-1]
        eqh = E0 + cp[np.searchsorted(te_sorted, hrs, 'right')]
        expo = notl / eqh
        kk = np.arange(len(hrs))
        hdf = pd.DataFrame({'run': run, 'k': kk, 'expo': expo, 'n_open': nop})
        hdf = hdf[hrs >= A.DEV0]
        hourly_all.append(hdf)
        hd = A.dts(hrs[hrs >= A.DEV0]).floor('D')
        agg = hdf.groupby(hd.values).agg(expo_mean=('expo', 'mean'), expo_max=('expo', 'max'), n_open_mean=('n_open', 'mean'))
        dl = pd.DataFrame({'run': run, 'd': A.dts(days[:-1]), 'eq_real': eq_real[1:], 'eq_mtm': eq_mtm[1:], 'unreal': unreal[1:],
                           'eq_real_prev': eq_real[:-1], 'eq_mtm_prev': eq_mtm[:-1]})
        dl['expo_mean'] = agg['expo_mean'].values
        dl['expo_max'] = agg['expo_max'].values
        dl['n_open_mean'] = agg['n_open_mean'].values
        daily_all.append(dl)
        legs_all.append(d[['run', 'sym', 'usym', 'c', 'level', 'status', 'entry', 'tp', 'quantity', 'margin', 'pnl', 'funding', 'ts', 'te']])
        chk[run].update(eq_real_2022_01_01=float(eq_real[0]), eq_mtm_2022_01_01=float(eq_mtm[0]), eq_end=float(eq_real[-1]),
                        n_legs_dev=int((d['te'] > A.DEV0).sum()), expo_mean=float(np.mean(expo[hrs >= A.DEV0])),
                        expo_max=float(np.max(expo[hrs >= A.DEV0])))
        log.info('%s %s', run, chk[run])
    pd.concat(legs_all).to_parquet(A.OUT + '/c_long_legs.parquet', index=False)
    pd.concat(daily_all).to_parquet(A.OUT + '/c_long_daily.parquet', index=False)
    pd.concat(hourly_all).to_parquet(A.OUT + '/c_long_hourly.parquet', index=False)
    with open(A.OUT + '/c_long_check.json', 'w') as fh:
        json.dump(chk, fh, indent=1)


if __name__ == '__main__':
    main()
