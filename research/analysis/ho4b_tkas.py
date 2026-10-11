#!/usr/bin/env python3
"""HO4-P0b Q1(iii): ticker DEV (file kaggle_data_hpo, export 08-21/22) vs Aerospike LOCAL kline_1m_opt HIEN TAI (CHI DOC)
theo ngay: phut, khoa (phut,symbol), gia tri 5 truong; liet ke symbol chi-file / chi-AS. Usage: ho4b_tkas.py <out.json> day..."""
import json, logging, sys
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import datetime
import devexport_202609 as dx
import ho3_b2_kline_as as k1
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
st = dx.Store("local", pool=8)
res = {}
for day in sys.argv[2:]:
    ms = int(datetime.datetime.strptime(day, "%Y%m%d").replace(tzinfo=datetime.timezone.utc).timestamp() * 1000)
    tk = k1.load_ticker(day)
    az = k1.fetch_as(st, ms)
    r = k1.compare(tk, az)
    sf, sa = set(), set()
    for m in tk:
        sf |= set(tk[m])
    for m in az:
        sa |= set(az[m])
    r.update(sym_file=len(sf), sym_as=len(sa), sym_file_only=sorted(sf - sa)[:50], sym_as_only=sorted(sa - sf)[:50])
    res[day] = r
    logging.info("%s %s", day, json.dumps(r)[:700])
st.close()
json.dump(res, open(sys.argv[1], "w"), indent=1)
