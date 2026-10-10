#!/usr/bin/env python3
"""HO4: khoang phut cua 1 file ticker DEV (UTC) + thu tu chen symbol phut dau (de chon thu tu ghi)."""
import datetime, logging, sys
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import ho3_b2_kline_as as k1
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
for day in sys.argv[1:]:
    mm = k1.load_ticker(day)
    ks = sorted(mm)
    f = lambda t: datetime.datetime.utcfromtimestamp(t / 1000).strftime("%Y-%m-%d %H:%M")
    logging.info("%s n=%d first=%s last=%s first_syms=%s", day, len(ks), f(ks[0]), f(ks[-1]), list(mm[ks[0]])[:8])
