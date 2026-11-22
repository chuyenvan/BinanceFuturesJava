#!/usr/bin/env python3
"""3b ho tro: xep hang tier xap xi cua sim (CoinRankManager.updateRanking a8690d46: tong totalUsdt 720 nen gan nhat, giam dan, bottom 20 % =
TIER_3, cap nhat moi gio). Nguon: Vision qv (quote volume) toan thi truong (mkt_dev2 + mkt_dev2b). Xap xi: universe = symbol co nen trong 720'."""
import gzip, collections, sys
from datetime import datetime, timezone, timedelta
TZ7 = timezone(timedelta(hours=7)); MIN = 60000; HR = 3600000
f7 = lambda ms: datetime.fromtimestamp(ms / 1000, TZ7).strftime('%m-%d %H:%M')
vol = collections.defaultdict(dict)
for fn in ('/dev/shm/add24/b/mkt_dev2b/mkt.csv.gz', '/dev/shm/add24/b/mkt_dev2/mkt.csv.gz'):
    for ln in gzip.open(fn, 'rt'):
        if ln.startswith('symbol'): continue
        p = ln.rstrip().split(','); vol[p[0]][int(p[1])] = float(p[6])
t0 = int(datetime(2026, 2, 1, 0, 0, tzinfo=TZ7).timestamp() * 1000); t1 = int(datetime(2026, 2, 6, 5, 0, tzinfo=TZ7).timestamp() * 1000)
for H in range(t0, t1, HR):
    sums = {}
    for s, m in vol.items():
        v = [m[t] for t in range(H - 720 * MIN, H, MIN) if t in m]
        if v: sums[s] = sum(v)
    order = sorted(sums, key=lambda s: (-sums[s], s)); n = len(order)
    res = []
    for s in ('FIGHTUSDT', 'SPACEUSDT'):
        i = order.index(s) if s in order else None
        res.append('%s rank %s/%d pct=%.3f %s' % (s[:5], i, n, (i / n) if i is not None else -1, 'T3' if i is not None and i >= int(n * 0.8) else ''))
    print(f7(H), ' | '.join(res))
