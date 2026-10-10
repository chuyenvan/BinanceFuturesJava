#!/usr/bin/env python3
"""HO3b B3 ticker Q3 (ADDENDUM-4 quyet dinh 1): Aerospike 242 ns ticker set kline_1m_opt (CHI DOC) -> ticker_YYYYMMDD.bin.gz
dung byte ExportTickerDaily (ho3b_jwrite, da kiem round-trip). Ngay UTC (file d = [d 07:00, d+1 07:00) +07).
Ghi md5(gunzip) + dem phut/symbol; KHONG in gia tri. Usage: ho3b_ticker_q3.py <outdir> <start YYYYMMDD> <end YYYYMMDD> [cluster=242]"""
import datetime, gzip, hashlib, json, logging, os, sys, time
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
sys.path.insert(0, "/home/ubuntu/claude_master/1003/ho3b")
import devexport_202609 as dx
import ho3b_jwrite as JW
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho3b_tq3")


def day_minutes(st, d0):
    recs = st.get_kline_day(d0)
    mins, miss = [], []
    for i in range(1440):
        t = d0 + i * 60000
        k = datetime.datetime.fromtimestamp(t / 1000, dx.TZ7).strftime("%Y%m%d-%H%M")
        if k not in recs:
            miss.append(k); continue
        syms, arr = dx.parse_minute(recs[k])
        if not syms:
            miss.append(k); continue
        mins.append((t, [(s,) + tuple(float(x) for x in arr[j]) for j, s in enumerate(syms)]))
    return mins, miss


def main():
    out, a, b = sys.argv[1], sys.argv[2], sys.argv[3]
    cl = sys.argv[4] if len(sys.argv) > 4 else "242"
    os.makedirs(out, exist_ok=True)
    st = dx.Store(cl, pool=32)
    d = datetime.datetime.strptime(a, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
    e = datetime.datetime.strptime(b, "%Y%m%d").replace(tzinfo=datetime.timezone.utc)
    man = {}
    mp = os.path.join(out, "MANIFEST_Q3.json")
    if os.path.exists(mp):
        man = json.load(open(mp))
    while d <= e:
        day = d.strftime("%Y%m%d")
        if day in man:
            d += datetime.timedelta(days=1); continue
        t0 = time.time()
        mins, miss = day_minutes(st, int(d.timestamp() * 1000))
        raw = JW.encode_day(mins)
        p = os.path.join(out, "ticker_%s.bin.gz" % day)
        with gzip.open(p + ".tmp", "wb", 6) as f:
            f.write(raw)
        os.replace(p + ".tmp", p)
        ns = [len(x[1]) for x in mins]
        seen = {}
        for t, ent in mins:
            for x_ in ent:
                v = seen.get(x_[0])
                if v is None:
                    seen[x_[0]] = [t, t]
                else:
                    v[1] = t
        json.dump(seen, open(os.path.join(out, 'seen_%s.json' % day), 'w'))
        man[day] = dict(md5_gunzip=hashlib.md5(raw).hexdigest(), bytes_raw=len(raw), bytes_gz=os.path.getsize(p),
                        n_min=len(mins), n_miss=len(miss), miss=miss[:50], sym_min=min(ns) if ns else 0,
                        sym_max=max(ns) if ns else 0, cluster=cl)
        json.dump(man, open(mp, "w"), indent=0)
        log.info("%s min=%d miss=%d sym=%d..%d %.0fs", day, len(mins), len(miss), man[day]["sym_min"], man[day]["sym_max"],
                 time.time() - t0)
        d += datetime.timedelta(days=1)
    st.close()


if __name__ == "__main__":
    main()
