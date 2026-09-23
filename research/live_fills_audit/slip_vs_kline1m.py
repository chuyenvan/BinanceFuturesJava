#!/usr/bin/env python3
"""Live fills audit — realized slippage per leg vs Binance 1m kline.

Input : data/trades.csv (from analyze_fills.py), raw3/kline_*.json
        (public GET /fapi/v1/klines for the exact fill minutes, saved on 242)
Output: data/slips.json + stdout summary

Definitions
  slip vs close = (fill - close)/close for BUY, (close - fill)/close for SELL
  proxy         = 0.5*(high-low)/close of the same 1m bar  (sim cost assumption)

Run:
  FILLS_RAW3=/tmp/fills_audit_oracle/raw3 python3 slip_vs_kline1m.py
"""
import json, glob, csv, os, collections, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
RAW3 = os.environ.get("FILLS_RAW3", os.path.join(HERE, "raw3"))
TRADES = os.environ.get("FILLS_TRADES", os.path.join(HERE, "data", "trades.csv"))

def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None

kl = {}
nfiles = 0
for p in glob.glob(os.path.join(RAW3, "kline_*.json")):
    d = load(p)
    if not isinstance(d, list):
        continue
    nfiles += 1
    sym = os.path.basename(p)[len("kline_"):].rsplit("_", 1)[0]
    for k in d:                       # [openTime, o,h,l,c, vol, closeTime, ...]
        kl[(sym, str(k[0]))] = k

rows = list(csv.DictReader(open(TRADES)))
slips = []
for r in rows:
    t = int(r["time_ms"]); m = t - (t % 60000)
    k = kl.get((r["symbol"], str(m)))
    if not k:
        continue
    o, h, l, c = float(k[1]), float(k[2]), float(k[3]), float(k[4])
    fill = float(r["price"])
    if r["side"] == "BUY":
        s_close, s_open = (fill - c) / c, (fill - o) / o
    else:
        s_close, s_open = (c - fill) / c, (o - fill) / o
    slips.append(dict(symbol=r["symbol"], side=r["side"], maker=r["maker"], fill=fill,
                      o=o, h=h, l=l, c=c, proxy=0.5 * (h - l) / c,
                      s_close=s_close, s_open=s_open, time=t))

print("kline files=%d ; trades matched=%d/%d" % (nfiles, len(slips), len(rows)))
sc = [s["s_close"] for s in slips]
px = [s["proxy"] for s in slips]
a = [abs(x) for x in sc]
print("slip vs close : mean=%+.5f%% median=%+.5f%% mean|.|=%.5f%%" % (100*st.mean(sc), 100*st.median(sc), 100*st.mean(a)))
print("slip vs open  : mean=%+.5f%% median=%+.5f%%" % (100*st.mean([s["s_open"] for s in slips]), 100*st.median([s["s_open"] for s in slips])))
print("sim proxy     : mean=%.5f%% median=%.5f%%" % (100*st.mean(px), 100*st.median(px)))
print("ratio mean|slip|/mean(proxy)=%.3f ; median|slip|/median(proxy)=%.3f" %
      (st.mean(a) / st.mean(px), st.median(a) / st.median(px)))
json.dump(slips, open(os.path.join(HERE, "data", "slips.json"), "w"))
