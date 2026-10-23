#!/usr/bin/env python3
"""PARITY_V11_WINDOW §2.3: file funding cho OfflineGuard (csv.gz "symbol,ts,rate") tu lake Vision monthly fundingRate
(~/claude_master/1016/carry/fund/funding-<nam>.parquet; nguon = data.binance.vision monthly, manifest ~/vz/manifest/fundingRate.csv.gz).
Chi symbol trong universe, ts <= cutoff (ms). rate ghi bang repr(float64) (= gia tri thap phan goc) -> Java Float.valueOf.
argv: universe.txt cutoff_ms out.csv.gz"""
import glob
import gzip
import logging
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("funding_build")
uni = {x.strip() for x in open(sys.argv[1]) if x.strip() and not x.startswith("#")}
cut = int(sys.argv[2])
fs = sorted(glob.glob("/home/ubuntu/claude_master/1016/carry/fund/funding-20*.parquet"))
d = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
n0 = len(d)
d = d[d.sym.isin(uni) & (d.ts <= cut)].drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"], kind="mergesort")
with gzip.open(sys.argv[3], "wt") as f:
    f.write("symbol,ts,rate\n")
    for s, t, r in zip(d.sym.values, d.ts.values, d.rate.values):
        f.write("%s,%d,%r\n" % (s, int(t), float(r)))
log.info("files=%d rows_all=%d rows_out=%d syms=%d/%d ts_max=%s univ_without_funding=%d", len(fs), n0, len(d),
         d.sym.nunique(), len(uni), pd.to_datetime(d.ts.max(), unit="ms"), len(uni - set(d.sym)))
