"""LEVZ2 price loader (PREREG_LEVZ2 sec 1): OHLCV_1H_v2.bin -> work/px_1h.parquet (sym, t = candle CLOSE time ms, open, high, low, close, qv).
Store: 30 B/rec big-endian [ts_h:int64 close-time ms][symId:int16][open,high,low,close,quoteVol:float32]; candle [t-1h, t).
Reader assert: candle OPEN time (t - 1h) < 2026-01-01 UTC (the candle closing exactly at 2026-01-01 00:00 is 2025-12-31 23:00..23:59 data).
S2 check (mandatory): store close vs tier-1 panel clast (w3/levz/work/hr_*.parquet, Vision 1m) for (sym, hour) in universe;
both label conventions tested on data (A: store t == panel h + 1h ; B: store t == panel h). PASS: rel diff <= 1e-3 on >= 99.5 %.
usage: python3 code/px.py build | s2"""
import json
import logging
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]  # code/select.py must not shadow stdlib select
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

log = logging.getLogger('levz2.px')
BIN = '/home/ubuntu/java/fsrun/OHLCV_1H_v2.bin'
SMAP = '/home/ubuntu/selector_pred_out/symbol_map.csv'
WORK = '/home/ubuntu/claude_master/w3/levz2/work'
HR = '/home/ubuntu/claude_master/w3/levz/work/hr_%s.parquet'
CUT = 1767225600000
H = 3600000
H0 = 1638316800000  # 2021-12-01 00:00 UTC
DT = np.dtype([('t', '>i8'), ('sid', '>i2'), ('o', '>f4'), ('h', '>f4'), ('l', '>f4'), ('c', '>f4'), ('qv', '>f4')])
assert DT.itemsize == 30


def read_store(t_min=H0):
    a = np.fromfile(BIN, dtype=DT)
    t = a['t'].astype(np.int64)
    m = (t - H < CUT) & (t >= t_min)
    a = a[m]
    t = a['t'].astype(np.int64)
    assert (t - H < CUT).all(), 'data >= 2026 loaded'
    sm = pd.read_csv(SMAP)
    mp = dict(zip(sm['symId'].astype(int), sm['symbol'].astype(str)))
    sid = a['sid'].astype(np.int64)
    assert np.isin(np.unique(sid), list(mp)).all()
    df = pd.DataFrame({'sym': pd.Series(sid).map(mp).values, 't': t,
                       'open': a['o'].astype(np.float64), 'high': a['h'].astype(np.float64),
                       'low': a['l'].astype(np.float64), 'close': a['c'].astype(np.float64), 'qv': a['qv'].astype(np.float64)})
    return df


def build():
    df = read_store()
    n0 = len(df)
    df = df.drop_duplicates(['sym', 't'], keep='last')
    bad = ~((df['high'] >= df[['open', 'close']].max(1)) & (df['low'] <= df[['open', 'close']].min(1)) & (df['low'] > 0))
    log.info('store rows=%d dup_dropped=%d syms=%d t=[%s, %s] bad_ohlc=%d', n0, n0 - len(df), df['sym'].nunique(),
             pd.Timestamp(df['t'].min(), unit='ms'), pd.Timestamp(df['t'].max(), unit='ms'), int(bad.sum()))
    df.sort_values(['t', 'sym'], kind='mergesort').to_parquet(WORK + '/px_1h.parquet', index=False)



def s2_real():
    px = pd.read_parquet(WORK + '/px_1h.parquet', columns=['sym', 't', 'close'])
    u = pd.read_parquet(WORK + '/sig_W14.parquet', columns=['sym', 't', 'u'])
    u = u[u['u']][['sym', 't']]
    sys.path.insert(0, '/home/ubuntu/claude_master/w3/levz/code')
    import common as C
    res = {}
    for lab, off in (('A_store_t_eq_h_plus_1h', H), ('B_store_t_eq_h', 0)):
        tot = dict(n_univ=0, n_join=0, n_ok=0, n_ok_all=0, n_join_all=0)
        q = []
        for ym in C.months('2021-12', '2025-12'):
            p = pd.read_parquet(HR % ym, columns=['sym', 'h', 'clast'])
            p['sym'] = p['sym'].astype(str)
            p['t'] = p['h'] + off
            j = p.merge(px, on=['sym', 't'], how='inner')
            rel = (j['close'] / j['clast'] - 1.0).abs()
            tot['n_join_all'] += len(j)
            tot['n_ok_all'] += int((rel <= 1e-3).sum())
            # universe at decision time = candle close time (t for A; h+1h for B both mean the hour the close is used)
            pu = p.assign(td=p['h'] + H).merge(u, left_on=['sym', 'td'], right_on=['sym', 't'], how='inner', suffixes=('', '_u'))
            tot['n_univ'] += len(pu)
            ju = pu[['sym', 't', 'clast']].merge(px, on=['sym', 't'], how='inner')
            ru = (ju['close'] / ju['clast'] - 1.0).abs()
            tot['n_join'] += len(ju)
            tot['n_ok'] += int((ru <= 1e-3).sum())
            q.append(ru.values)
        q = np.concatenate(q)
        tot['frac_ok_univ'] = tot['n_ok'] / max(tot['n_join'], 1)
        tot['coverage_univ'] = tot['n_join'] / max(tot['n_univ'], 1)
        tot['frac_ok_all'] = tot['n_ok_all'] / max(tot['n_join_all'], 1)
        tot['rel_q50_q99_q999_max'] = [float(np.quantile(q, x)) for x in (0.5, 0.99, 0.999)] + [float(q.max())] if len(q) else []
        res[lab] = tot
        log.info('S2 %s %s', lab, tot)
    best = max(res, key=lambda k: res[k]['frac_ok_univ'])
    res['label_convention'] = best
    res['pass'] = bool(res[best]['frac_ok_univ'] >= 0.995)
    with open(WORK + '/s2.json', 'w') as fh:
        json.dump(res, fh, indent=1)
    log.info('S2 convention=%s PASS=%s', best, res['pass'])


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    {'build': build, 's2': s2_real}[sys.argv[1]]()
