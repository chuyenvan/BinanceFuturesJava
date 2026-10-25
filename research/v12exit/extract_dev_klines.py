#!/usr/bin/env python3
"""[V12 C6] Trich du lieu cho replay exit DEV (ExitReplayDevMain): chan (SELRANK) cua 1 seed printDone X14 + gia close 1m.

Dung: python3 -I extract_dev_klines.py <sim_full.log> <raw_dir> <out_dir> <YYYYMMDD+07> [<YYYYMMDD> ...]
Ra moi ngay D: out_dir/legs_D.csv (ts_ms,sym,rank,pred) va out_dir/px_D.csv.gz (ts_ms,sym,close) tu phut chan dau tien toi +22 ngay
(168h + X14 336h + du). ts la int64 ms (UTC epoch). Kiem: ts chia het 60000, khong trung (ts,sym).
"""
import csv, gzip, os, re, sys
from datetime import datetime, timedelta, timezone

import pyarrow.parquet as pq
import pyarrow.compute as pc

RX = re.compile(r'SELRANK sym=(\S+) tOpen=(\d{8}) (\d\d:\d\d) tMs=(\d+) rank=(-?\d+) pred=(\S+)')
MIN = 60_000
DAYS = 22


def months(a_ms, b_ms):
    d = datetime.fromtimestamp(a_ms / 1000, tz=timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = datetime.fromtimestamp(b_ms / 1000, tz=timezone.utc)
    out = []
    while d <= end:
        out.append(d.strftime('%Y-%m'))
        d = (d + timedelta(days=32)).replace(day=1)
    return out


def main():
    log, raw, out = sys.argv[1], sys.argv[2], sys.argv[3]
    dates = sys.argv[4:]
    os.makedirs(out, exist_ok=True)
    legs = {d: [] for d in dates}
    with open(log, encoding='utf-8', errors='replace') as f:
        for ln in f:
            m = RX.search(ln)
            if not m:
                continue
            sym, d, hm, tms, rank, pred = m.groups()
            if d in legs:
                legs[d].append((int(tms), sym, int(rank), float(pred)))
    for d in dates:
        L = sorted(legs[d])
        assert L, 'khong co chan ngay %s' % d
        for t, *_ in L:
            assert t % MIN == 0, 'tMs khong tron phut %d' % t
        a = L[0][0] - MIN
        b = a + DAYS * 86_400_000
        syms = sorted({x[1] for x in L})
        with open(os.path.join(out, 'legs_%s.csv' % d), 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['ts_ms', 'sym', 'rank', 'pred'])
            for t, s, r, p in L:
                w.writerow([t, s, r, repr(p)])
        rows = 0
        seen = set()
        tmp = os.path.join(out, 'px_%s.csv.gz' % d)
        parts = []
        for mo in months(a, b):
            p = os.path.join(raw, 'kline1m-%s.parquet' % mo)
            if not os.path.exists(p):
                print('THIEU', p)
                continue
            t = pq.read_table(p, columns=['ts', 'sym', 'close'],
                              filters=[('ts', '>=', a), ('ts', '<', b), ('sym', 'in', syms)])
            parts.append(t)
        recs = []
        for t in parts:
            ts = t.column('ts').to_pylist()
            sy = [str(x) for x in t.column('sym').to_pylist()]
            cl = t.column('close').to_pylist()
            for i in range(len(ts)):
                recs.append((int(ts[i]), sy[i], cl[i]))
        recs.sort()
        with gzip.open(tmp, 'wt', newline='') as f:
            w = csv.writer(f)
            w.writerow(['ts_ms', 'sym', 'close'])
            for t, s, c in recs:
                assert isinstance(t, int) and t % MIN == 0
                k = (t, s)
                assert k not in seen, 'trung %s' % (k,)
                seen.add(k)
                if c is None or not (c > 0):
                    continue
                w.writerow([t, s, repr(float(c))])
                rows += 1
        nsym = len({s for _, s, _ in recs})
        print('NGAY %s chan=%d sym=%d/%d dong_gia=%d tu=%d toi=%d' % (d, len(L), nsym, len(syms), rows, a, b))


if __name__ == '__main__':
    main()
