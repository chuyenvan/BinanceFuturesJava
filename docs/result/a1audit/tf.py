#!/usr/bin/env python3
# [A1 audit] phan tich doc lap exchangeInfo that (khong import code repo)
import gzip, json, csv, os, sys, collections, time
F = os.path.expanduser("~/claude_master/v12/fixtures/exchangeInfo_20261025_1457.json.gz")
ei = json.load(gzip.open(F, "rt", encoding="utf-8"))
syms = ei["symbols"]
print("n_symbols", len(syms), "keys_top", sorted(ei.keys()))
print("rateLimits", json.dumps(ei.get("rateLimits")))
C = collections.Counter
def cnt(k):
    c = C()
    for s in syms:
        v = s.get(k, "<MISSING>")
        if isinstance(v, list):
            v = "|".join(v) if v else "<EMPTY>"
        c[v] += 1
    return c
for k in ["contractType", "underlyingType", "status", "quoteAsset", "marginAsset"]:
    print(k, dict(cnt(k).most_common()))
sub = C()
for s in syms:
    for t in s.get("underlyingSubType", []) or ["<EMPTY>"]:
        sub[t] += 1
print("underlyingSubType tags", dict(sub.most_common()))
# cross tab contractType x underlyingType
x = C((s.get("contractType"), s.get("underlyingType")) for s in syms)
print("ct x ut", dict(x))
# all keys union
keys = C()
for s in syms:
    keys.update(s.keys())
print("symbol keys", dict(keys))
# TradFi set by 'contractType contains TRADIFI/TRADFI' OR underlyingType not in {COIN,INDEX}
def tf_rule(s):
    ct = (s.get("contractType") or "").upper()
    ut = s.get("underlyingType")
    if "TRADIFI" in ct or "TRADFI" in ct: return "ct"
    if ut is not None and ut.upper() not in ("COIN", "INDEX"): return "ut"
    tags = {"TRADFI","STOCK","STOCKS","EQUITY","EQUITIES","ETF","FOREX","FX","COMMODITY","COMMODITIES","METAL","METALS"}
    for t in s.get("underlyingSubType", []) or []:
        if t.strip().upper() in tags: return "sub:" + t
    return None
rules = C(tf_rule(s) for s in syms)
print("rule hits", dict(rules))
tradfi = {s["symbol"] for s in syms if tf_rule(s)}
tradi_ct = {s["symbol"] for s in syms if "TRADIFI" in (s.get("contractType") or "").upper()}
print("tradfi_total", len(tradfi), "by_contractType", len(tradi_ct))
# non-TRADIFI contractType but rule hit:
oth = sorted(s["symbol"] + ":" + str(tf_rule(s)) + ":" + str(s.get("contractType")) + ":" + str(s.get("underlyingType")) + ":" + "|".join(s.get("underlyingSubType") or [])
             for s in syms if tf_rule(s) and s["symbol"] not in tradi_ct)
print("tradfi_not_by_ct", len(oth), oth[:60])
# TRADIFI contractType: underlyingType / subtype breakdown
print("TRADIFI ut", dict(C(s.get("underlyingType") for s in syms if s["symbol"] in tradi_ct)))
print("TRADIFI sub", dict(C("|".join(s.get("underlyingSubType") or []) for s in syms if s["symbol"] in tradi_ct).most_common(30)))
# crypto (not tradfi) subtype tags, to see suspicious tags
print("crypto sub", dict(C("|".join(s.get("underlyingSubType") or []) for s in syms if s["symbol"] not in tradfi).most_common(40)))
# crypto underlyingType INDEX symbols
print("INDEX ut", sorted(s["symbol"] for s in syms if s.get("underlyingType") == "INDEX"))
# proxy list
P = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/symlife/live_low_activity_1023.csv")
rows = list(csv.DictReader(open(P)))
print("proxy cols", list(rows[0].keys()), "n", len(rows))
symcol = [k for k in rows[0] if "sym" in k.lower()][0]
proxy = {r[symcol] for r in rows}
allsyms = {s["symbol"]: s for s in syms}
print("proxy not in dump", sorted(p for p in proxy if p not in allsyms))
print("proxy in dump & classified crypto (TradFi lot?)", sorted((p, allsyms[p].get("contractType"), allsyms[p].get("underlyingType"), "|".join(allsyms[p].get("underlyingSubType") or []), allsyms[p].get("status")) for p in proxy if p in allsyms and p not in tradfi))
print("tradfi TRADING not in proxy", len([t for t in tradfi if allsyms[t].get("status") == "TRADING" and t not in proxy]))
for n in ["IBKRUSDT", "UNITREEUSDT", "NAVERUSDT", "JPMUSDT", "TENCENTUSDT", "POWRUSDT", "MDTUSDT", "BTCDOMUSDT", "USDCUSDT", "XAUUSDT", "XAGUSDT", "PAXGUSDT", "TSLAUSDT", "MSTRUSDT", "COINUSDT", "HOODUSDT", "SPYUSDT", "QQQUSDT", "EURUSDT", "USDBRLUSDT", "KODEX200USDT", "SAMSUNGEMUSDT", "BITOUSDT"]:
    s = allsyms.get(n)
    print("SYM", n, None if s is None else (s.get("status"), s.get("contractType"), s.get("underlyingType"), s.get("underlyingSubType"), s.get("deliveryDate"), s.get("onboardDate")))
# non-ascii
na = [s["symbol"] for s in syms if any(ord(ch) < 0x21 or ord(ch) > 0x7e for ch in s["symbol"])]
print("non_ascii", len(na), [(x, allsyms[x].get("status"), allsyms[x].get("contractType")) for x in na])
# delivery
now = int(time.time() * 1000)
perp_dd = C(s.get("deliveryDate") for s in syms if s.get("contractType") == "PERPETUAL")
print("perp deliveryDate values", dict(perp_dd.most_common(5)))
dd_soon = sorted((s["symbol"], s.get("status"), s.get("deliveryDate")) for s in syms if s.get("contractType") == "PERPETUAL" and s.get("deliveryDate", 0) < 4133404800000)
print("perp with deliveryDate set (delist sched)", len(dd_soon), dd_soon[:40])
# final universe estimate: TRADING, USDT, PERPETUAL, not tradfi, not excluded
U = [s["symbol"] for s in syms if s.get("status") == "TRADING" and s.get("quoteAsset") == "USDT" and s.get("contractType") == "PERPETUAL" and not tf_rule(s) and s["symbol"] not in ("BTCDOMUSDT", "USDCUSDT")]
print("U_size", len(U))
# crypto-like names among TradFi (suspected false positive): list tradfi names w/ subtype
print("tradfi list", sorted((t, allsyms[t].get("status"), "|".join(allsyms[t].get("underlyingSubType") or [])) for t in tradfi))
# filters present
fl = C()
for s in syms:
    for f in s.get("filters", []):
        fl[f.get("filterType")] += 1
print("filters", dict(fl))
print("orderTypes TRADIFI sample", allsyms.get("IBKRUSDT", {}).get("orderTypes"))
