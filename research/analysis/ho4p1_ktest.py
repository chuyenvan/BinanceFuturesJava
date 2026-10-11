#!/usr/bin/env python3
"""HO4-P1: thu khoi kline/ticker/CLOSES/lifecycle cua ho4p1_exp_kernel tren 3 symbol x 1 thang + 1 ngay daily (Oracle, nhe).
Chi kiem chay dung + gz tat dinh (2 lan ghi cung md5). Usage: ho4p1_ktest.py"""
import glob, hashlib, json, logging, os, sys
import pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import ho4p1_exp_kernel as E
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("kt")
W = "/home/ubuntu/claude_master/1011/ho4p1/ktest"
os.makedirs(W + "/out/ticker", exist_ok=True)
k = E.KX
a = k.index("TZ7 = datetime.timezone")
b = k.index("RES[\"steps\"][\"klines\"] = dict(")
mp = pd.read_csv("/home/ubuntu/claude_master/../claudedata/oi/symbol_map.csv") if False else pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv")
CFG = dict(tag="kt", mapper=["BTCUSDT", "BNXUSDT", "ETHUSDT", "BTCDOMUSDT"], months=["2025-06"], days=["2025-07-01"],
           ingest=["20250629", "20250701"], S=[1751302800000, 1767200400000], dl_threads=4,
           closes_map={r.symbol: int(r.symId) for r in mp.itertuples()})
hdr = "\n".join([
    "import glob, gzip, hashlib, io, json, logging, os, pickle, re, shutil, struct, sys, time, datetime",
    "import urllib.request, urllib.parse, zipfile",
    "from concurrent.futures import ThreadPoolExecutor",
    "import numpy as np",
    "LOG = logging.getLogger('kx')",
    "CFG = json.loads(%r)" % json.dumps(CFG),
    "OUTD = %r" % (W + "/out"),
    "sys.path.insert(0, '/home/ubuntu/src/BinanceFuturesJava/research/analysis')",
    "import ho3b_jwrite as JWR",
    "RES = dict(steps={})",
    "def save(): pass",
])
code = hdr + "\n" + k[a:b]
for run in (1, 2):
    g = {}
    exec(compile(code, "kx", "exec"), g)
    man = {os.path.basename(p): hashlib.md5(open(p, "rb").read()).hexdigest() for p in sorted(glob.glob(W + "/out/**/*", recursive=True)) if os.path.isfile(p)}
    log.info("RUN %d universe=%s tail=%s closes=%s lc=%s", run, sorted(g["KL"]), g["TAIL"], g["RES"]["steps"].get("closes1h"), g["LC_NEW"])
    log.info("RUN %d md5=%s", run, json.dumps(man))
