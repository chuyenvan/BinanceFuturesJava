"""LEVZ common readers. Every reader asserts ts < 2026-01-01 UTC (filter pushed into read)."""
import logging
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyarrow.compute as pc

CUTOFF_MS = 1767225600000  # 2026-01-01 00:00 UTC
H_MS = 3600000
M_MS = 60000
KL = '/home/ubuntu/claude_master/res1109/r1_s1/kl/kline1m-{ym}.parquet'
MET = '/home/ubuntu/vz/out/metrics5m/{y}/{ym}.parquet'
FUND = '/home/ubuntu/claude_master/1016/carry/fund/funding-{y}.parquet'
D1 = '/home/ubuntu/claude_master/1016/screen/d1.parquet'
WORK = '/home/ubuntu/claude_master/w3/levz/work'
# stable / index names excluded (prereg sec 1 + "ten tuong tu")
EXCL_BASE = {'USDC', 'BUSD', 'TUSD', 'FDUSD', 'USDP', 'DAI', 'UST', 'USDE', 'EUR', 'AEUR',
             'BTCDOM', 'DEFI', 'BLUEBIRD', 'FOOTBALL'}

log = logging.getLogger('levz')


def setup_log():
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def months(a='2021-12', b='2025-12'):
    out = []
    y, m = int(a[:4]), int(a[5:])
    while True:
        ym = '%04d-%02d' % (y, m)
        out.append(ym)
        if ym == b:
            return out
        m += 1
        if m == 13:
            y, m = y + 1, 1


def sym_ok(s):
    if not s.endswith('USDT') or '_' in s:
        return False
    return s[:-4] not in EXCL_BASE


def _chk(t, col='ts'):
    if t.num_rows:
        mx = pc.max(t[col]).as_py()
        if hasattr(mx, 'timestamp'):
            mx = int(pd.Timestamp(mx).value // 10**6)
        assert mx < CUTOFF_MS, 'data >= 2026 loaded'
    return t


def read_kline(ym):
    assert ym < '2026-01'
    t = pq.read_table(KL.format(ym=ym), columns=['ts', 'sym', 'close'], filters=[('ts', '<', CUTOFF_MS)])
    _chk(t)
    df = t.to_pandas()
    df['sym'] = df['sym'].astype(str)
    return df


def read_metrics(ym):
    assert ym < '2026-01'
    t = pq.read_table(MET.format(y=ym[:4], ym=ym), columns=['ts', 'sym', 'oi'], filters=[('ts', '<', CUTOFF_MS)])
    _chk(t)
    df = t.to_pandas()
    df['sym'] = df['sym'].astype(str)
    return df


def read_funding(y, cut=CUTOFF_MS):
    assert int(y) <= 2025 and cut <= CUTOFF_MS
    t = pq.read_table(FUND.format(y=y), columns=['ts', 'sym', 'interval_h', 'rate'], filters=[('ts', '<', cut)])
    _chk(t)
    df = t.to_pandas()
    df['sym'] = df['sym'].astype(str)
    return df


def read_d1(cut=CUTOFF_MS):
    assert cut <= CUTOFF_MS
    t = pq.read_table(D1, columns=['sym', 'day', 'qv'], filters=[('day', '<', pd.Timestamp(cut, unit='ms'))])
    _chk(t, 'day')
    df = t.to_pandas()
    df['sym'] = df['sym'].astype(str)
    return df


def universe_days(cut=CUTOFF_MS):
    """Return DataFrame (sym, day) eligible: qv30 of previous 30 full days >= 20M, listed >= 45 days, name ok.
    qv30(D) = mean qv over calendar days D-30..D-1 (requires all 30 present); listed: first d1 day <= D-45."""
    d = read_d1(cut)
    d = d[d['sym'].map(sym_ok)]
    out = []
    for s, g in d.groupby('sym', sort=True):
        g = g.set_index('day')['qv'].sort_index()
        g = g[~g.index.duplicated()]
        idx = pd.date_range(g.index.min(), g.index.max(), freq='D')
        g = g.reindex(idx)
        q30 = g.rolling(30, min_periods=30).mean().shift(1)
        first = idx[0]
        ok = (q30 >= 20e6) & (idx >= first + pd.Timedelta(days=45))
        dd = idx[ok.values]
        if len(dd):
            out.append(pd.DataFrame({'sym': s, 'day': dd}))
    u = pd.concat(out, ignore_index=True)
    return u
