#!/usr/bin/env python3
"""HO1 B6 — kiem symbol 2026H1 (quyet dinh MASTER 6): symbol co trong ticker 2026H1 / bins 2026 nhung THIEU trong
mapper Oracle (Aerospike test.symbol_mapper/global_id_map, CHI DOC) hoac exchange_info_pin.json (so TEN) => loai, dem,
liet ke. Cung kiem: symId trong bins 2026 (symbol_map.csv) == id mapper cung ten. Khong sua mapper.
Ten symbol trong ticker lay tu chuoi Java (TC_STRING) cua file serialize. Usage: python3 ho1_symbols.py <out.json>"""
import glob
import gzip
import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor

import aerospike
import numpy as np
import pandas as pd

TK = "/home/ubuntu/java/simulator/kaggle_data_hpo"
BINS = "/home/ubuntu/claude_master/1003/ho1/bins2026"
PIN = "/home/ubuntu/simbundle_x1_t170/exchange_info_pin.json"
MAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"   # map symId cua net015/bins (== mapper Oracle theo ten)
RX = re.compile(rb"\x74\x00([\x02-\x30])")
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])


def names(f):
    raw = gzip.open(f).read()
    out = set()
    for m in RX.finditer(raw):
        n = m.group(1)[0]
        s = raw[m.end():m.end() + n]
        try:
            t = s.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if t and t == t.upper() and re.fullmatch(r"[^\s.;/$\[\]]+", t):
            out.add(t if t.endswith("USDT") else t + "USDT")
    return out


def main():
    files = sorted(f for f in glob.glob(TK + "/ticker_2026*.bin.gz") if "20260101" <= f.split("ticker_")[1][:8] <= "20260630")
    assert len(files) == 181, len(files)
    T, days = set(), {}
    with ProcessPoolExecutor(3) as ex:
        for f, s in zip(files, ex.map(names, files)):
            T |= s
            for n in s:
                days.setdefault(n, []).append(f.split("ticker_")[1][:8])
    dev = sorted(f for f in glob.glob(TK + "/ticker_2025123*.bin.gz"))
    Tdev = names(dev[-1]) if dev else set()
    c = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    _, _, rec = c.get(("test", "symbol_mapper", "global_id_map"))
    c.close()
    mapper = {k: int(v) for k, v in rec["data"].items()}
    pin = set(x["symbol"] for x in json.load(open(PIN))["symbols"])
    mp = pd.read_csv(MAP)
    i2s = dict(zip(mp.symId.astype(int), mp.symbol))
    bsyms = set()
    for f in glob.glob(BINS + "/predict_wf_2026*.bin"):
        bsyms |= set(int(x) for x in np.unique(np.fromfile(f, dtype=DT)["sym"]))
    bnames = {i2s.get(s, "ID%d" % s) for s in bsyms}
    id_mismatch = sorted(n for n in bnames if n in mapper and mapper[n] != int(mp.set_index("symbol").symId.get(n, -1)))
    allsym = T | bnames
    miss_map = sorted(s for s in allsym if s not in mapper)
    miss_pin = sorted(s for s in allsym if s not in pin)
    excl = sorted(set(miss_map) | set(miss_pin))
    out = dict(n_ticker_files=len(files), n_ticker_syms=len(T), n_ticker_syms_20251231=len(Tdev),
               n_bins_syms=len(bnames), mapper_size=len(mapper), pin_size=len(pin),
               missing_mapper=miss_map, missing_pin=miss_pin, excluded=excl, n_excluded=len(excl),
               excluded_in_bins=sorted(set(excl) & bnames), excluded_in_ticker=sorted(set(excl) & T),
               bins_id_mismatch_mapper=id_mismatch,
               ticker_excluded_days={n: [len(days[n]), min(days[n]), max(days[n])] for n in sorted(set(excl) & T)},
               note='ticker-only (khong co trong bins) khong the vao lenh: entry chi lay tu predict2Symbol (bins); loai = bo khoi bins 2026',
               excluded_symids=sorted(int(mp.set_index("symbol").symId[n]) for n in set(excl) & bnames if n in set(mp.symbol)))
    json.dump(out, open(sys.argv[1], "w"), indent=1)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
