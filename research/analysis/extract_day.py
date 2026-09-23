"""Extract daily closes (UTC day end, 23:59 minute) from ticker bins or Aerospike.

Usage:
  python3 extract_day.py file YYYYMMDD      -> /home/ubuntu/altregime/daily/<YYYYMMDD>.csv
  python3 extract_day.py asp  YYYYMMDD      -> same, but read minute key from Aerospike 242
Output CSV: symbol,close   (symbol = base name, USDT suffix stripped)
"""
import gzip
import os
import struct
import sys

OUT = "/home/ubuntu/altregime/daily"
os.makedirs(OUT, exist_ok=True)


def base(sym):
    return sym[:-4] if sym.endswith("USDT") else sym


def from_ticker(path):
    import jbin
    with gzip.open(path, 'rb') as g:
        b = g.read()
    last = None
    for k, v in jbin.iter_minutes(b):
        last = v              # keep only the final minute of the day
    if last is None:
        return {}
    out = {}
    for sym, tup in last.items():
        # tup = (startTime, maxPrice, minPrice, priceClose, priceOpen, totalUsdt)
        out[base(sym)] = tup[3]
    return out


def from_asp(day):
    """day = YYYYMMDD (UTC). last minute of that UTC day = key at +7h."""
    import aerospike
    import snappy
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from aprobe import parse_map
    import datetime as dt
    d = dt.datetime.strptime(day, "%Y%m%d")
    keyts = d + dt.timedelta(hours=23, minutes=59) + dt.timedelta(hours=7)
    key = keyts.strftime("%Y%m%d-%H%M")
    c = aerospike.client({'hosts': [('103.157.218.242', 3222)]})
    rec = c.get(('ticker', 'kline_1m_opt', key))
    m = parse_map(snappy.decompress(rec[2]['data']))
    out = {}
    for sym, tup in m.items():
        out[base(sym)] = tup[3]      # tup = (open, high, low, close, vol)
    return out


if __name__ == '__main__':
    mode, day = sys.argv[1], sys.argv[2]
    dst = os.path.join(OUT, day + ".csv")
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        print("skip", day)
        sys.exit(0)
    if mode == 'file':
        p = "/home/ubuntu/java/simulator/kaggle_data_hpo/ticker_%s.bin.gz" % day
        if not os.path.exists(p):
            p = "/home/ubuntu/java/simulator/kaggle_data_hpo/daily/ticker_%s.bin.gz" % day
        d = from_ticker(p)
    else:
        d = from_asp(day)
    tmp = dst + ".tmp"
    with open(tmp, 'w') as f:
        for k in sorted(d):
            f.write("%s,%.10g\n" % (k, d[k]))
    os.replace(tmp, dst)
    print("ok", day, len(d))
