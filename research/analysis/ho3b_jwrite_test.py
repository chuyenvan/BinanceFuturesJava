#!/usr/bin/env python3
"""HO3b kiem bo ghi ticker: (A) round-trip file HO26 -> decode (jbin, giu thu tu stream) -> encode == byte goc;
(B) Aerospike LOCAL (chi doc) -> encode == file HO26 (ngay H1). Chi in khop/khong + dem."""
import datetime, gzip, hashlib, json, sys
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
sys.path.insert(0, "/home/ubuntu/claude_master/1003/ho3b")
import jbin, ho3b_jwrite as JW
TD = "/home/ubuntu/java/simulator/kaggle_data_hpo/"
res = {}
for day in sys.argv[1].split(","):
    raw = gzip.open(TD + "ticker_%s.bin.gz" % day).read()
    mins = []
    for ts, m in jbin.iter_minutes(raw):
        # jbin tuple: (startTime, maxPrice, minPrice, priceClose, priceOpen, totalUsdt)
        mins.append((ts, [(s, v[4], v[1], v[2], v[3], v[5], v[0]) for s, v in m.items()]))
    enc = JW.encode_day(mins)
    r = dict(n_min=len(mins), bytes_orig=len(raw), bytes_enc=len(enc), A_equal=enc == raw)
    if not r["A_equal"]:
        k = next(i for i in range(min(len(enc), len(raw))) if enc[i] != raw[i])
        r["first_diff"] = k
    if len(sys.argv) > 2:
        import devexport_202609 as dx
        st = dx.Store("local", pool=16)
        d0 = int(datetime.datetime.strptime(day, "%Y%m%d").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
        recs = st.get_kline_day(d0)
        mins2 = []
        for i in range(1440):
            t = d0 + i * 60000
            k = datetime.datetime.fromtimestamp(t / 1000, dx.TZ7).strftime("%Y%m%d-%H%M")
            if k not in recs:
                continue
            syms, arr = dx.parse_minute(recs[k])
            if not syms:
                continue
            mins2.append((t, [(s,) + tuple(float(x) for x in arr[j]) for j, s in enumerate(syms)]))
        enc2 = JW.encode_day(mins2)
        r.update(B_n_min=len(mins2), B_equal=enc2 == raw, B_md5=hashlib.md5(enc2).hexdigest(), orig_md5=hashlib.md5(raw).hexdigest())
        st.close()
    res[day] = r
print(json.dumps(res, indent=1))
