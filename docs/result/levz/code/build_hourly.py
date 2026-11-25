"""Per month: hourly price table from CLOSED 1m candles + hourly OI record (latency rule). Writes work/hr_<ym>.parquet, work/oi_<ym>.parquet.
hr: sym, h (ms, hour open), p0 = close of 1m candle with open_time == h (NaN if missing),
    clast = close of last 1m candle with open_time in [h, h+59m], cmax = max 1m close in [h, h+59m], nmin.
oi: sym, h, x = ln(oi) of latest record with ts in (h-70m, h-10m], tsr = that record ts."""
import logging
import sys
import numpy as np
import pandas as pd
import common as C

C.setup_log()
log = logging.getLogger('build')


def build_month(ym):
    k = C.read_kline(ym)
    k = k[np.isfinite(k['close']) & (k['close'] > 0)]
    k = k.sort_values(['sym', 'ts'], kind='mergesort')
    k['h'] = k['ts'] // C.H_MS * C.H_MS
    g = k.groupby(['sym', 'h'], sort=True)['close']
    hr = pd.DataFrame({'clast': g.last(), 'cmax': g.max(), 'nmin': g.size()}).reset_index()
    p0 = k.loc[k['ts'] % C.H_MS == 0, ['sym', 'ts', 'close']].rename(columns={'ts': 'h', 'close': 'p0'})
    hr = hr.merge(p0, on=['sym', 'h'], how='left')
    hr['nmin'] = hr['nmin'].astype('int16')
    hr.to_parquet('%s/hr_%s.parquet' % (C.WORK, ym), index=False)
    n1 = len(hr)
    del k, g, hr, p0
    m = C.read_metrics(ym)
    m = m[np.isfinite(m['oi']) & (m['oi'] > 0)]
    m['h'] = -((-(m['ts'] + 10 * C.M_MS)) // C.H_MS) * C.H_MS  # ceil((ts+10m)/H)*H : ts in (h-70m, h-10m]
    m = m.sort_values(['sym', 'h', 'ts'], kind='mergesort').drop_duplicates(['sym', 'h'], keep='last')
    oi = pd.DataFrame({'sym': m['sym'].values, 'h': m['h'].values, 'x': np.log(m['oi'].values), 'tsr': m['ts'].values})
    oi.to_parquet('%s/oi_%s.parquet' % (C.WORK, ym), index=False)
    log.info('%s hr=%d oi=%d', ym, n1, len(oi))


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else '2021-12'
    b = sys.argv[2] if len(sys.argv) > 2 else '2025-12'
    for ym in C.months(a, b):
        build_month(ym)


if __name__ == '__main__':
    main()
