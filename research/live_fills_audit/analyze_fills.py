#!/usr/bin/env python3
"""Live fills audit — fees / maker-taker / fill-rate / per-symbol table.

Input : raw2/ (userTrades windows + probes saved by fetch_live_fills_242.sh)
        raw4/ (allOrders 7d windows)
Output: data/trades.csv, data/orders.csv, stdout summary

Run:
  FILLS_RAW2=/tmp/fills_audit_oracle/raw2 FILLS_RAW4=/tmp/fills_audit_oracle/raw4 \
  python3 analyze_fills.py
"""
import json, glob, csv, os, collections, statistics as st, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
RAW2 = os.environ.get("FILLS_RAW2", os.path.join(HERE, "raw2"))
RAW4 = os.environ.get("FILLS_RAW4", os.path.join(HERE, "raw4"))
OUT = os.path.join(HERE, "data")
os.makedirs(OUT, exist_ok=True)

def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None

# ---- trades -----
trades = {}
for p in sorted(glob.glob(os.path.join(RAW2, "trades_*.json"))) + sorted(glob.glob(os.path.join(RAW2, "probe_*.json"))):
    d = load(p)
    if isinstance(d, list):
        for t in d:
            trades[t["id"]] = t

f = lambda ms: dt.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M")
ts = sorted(t["time"] for t in trades.values())
print("TRADES n=%d symbols=%d  %s -> %s UTC" %
      (len(trades), len(set(t["symbol"] for t in trades.values())), f(ts[0]), f(ts[-1])))
mk = sum(1 for t in trades.values() if t.get("maker"))
print("maker=%d taker=%d maker%%=%.2f%%" % (mk, len(trades) - mk, 100.0 * mk / len(trades)))

fees = []
for t in trades.values():
    notional = float(t["price"]) * float(t["qty"])
    fees.append(100.0 * float(t["commission"]) / notional if notional else 0.0)
print("fee per leg: mean=%.5f%% median=%.5f%%  (sim: taker 0.05 / maker 0.02)" %
      (st.mean(fees), st.median(fees)))
print("round-trip fee median=%.5f%% vs sim 0.80%% -> %.2fx lower" %
      (2 * st.median(fees), 0.80 / (2 * st.median(fees))))

with open(os.path.join(OUT, "trades.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["symbol", "id", "orderId", "maker", "side", "positionSide", "price", "qty",
                "notional", "commission", "fee_pct", "realizedPnl", "time_ms"])
    for t in sorted(trades.values(), key=lambda x: x["time"]):
        n = float(t["price"]) * float(t["qty"])
        w.writerow([t["symbol"], t["id"], t["orderId"], t.get("maker"), t.get("side"),
                    t.get("positionSide"), t["price"], t["qty"], "%.12g" % n, t["commission"],
                    "%.8f" % (100.0 * float(t["commission"]) / n if n else 0), t["realizedPnl"], t["time"]])

# ---- orders ----
orders = {}
for p in glob.glob(os.path.join(RAW4, "ao_*.json")):
    d = load(p)
    if isinstance(d, list):
        for o in d:
            orders[o["orderId"]] = o
statuses = collections.Counter(o["status"] for o in orders.values())
print("ORDERS n=%d status=%s types=%s" %
      (len(orders), dict(statuses), dict(collections.Counter(o.get("origType") for o in orders.values()))))
print("fill_rate = %.2f%% (FILLED/total)" % (100.0 * statuses.get("FILLED", 0) / max(1, len(orders))))

with open(os.path.join(OUT, "orders.csv"), "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["symbol", "orderId", "status", "origType", "side", "reduceOnly", "closePosition",
                "origQty", "executedQty", "avgPrice", "time", "updateTime"])
    for o in sorted(orders.values(), key=lambda x: x["time"]):
        w.writerow([o["symbol"], o["orderId"], o["status"], o.get("origType"), o["side"],
                    o.get("reduceOnly"), o.get("closePosition"), o["origQty"], o["executedQty"],
                    o["avgPrice"], o["time"], o["updateTime"]])

# ---- per symbol table ----
by = collections.defaultdict(list)
for t in trades.values():
    by[t["symbol"]].append(t)
o_cnt = collections.Counter(o["symbol"] for o in orders.values())
print("\n| symbol | n_legs | n_orders | maker% | fee_med% | pnl_sum |")
print("|---|---|---|---|---|---|")
for s in sorted(by, key=lambda k: -len(by[k])):
    rs = by[s]
    fm = st.median([100.0 * float(r["commission"]) / (float(r["price"]) * float(r["qty"])) for r in rs])
    mkr = 100.0 * sum(1 for r in rs if r.get("maker")) / len(rs)
    print("| %s | %d | %d | %.1f | %.4f | %+.2f |" %
          (s, len(rs), o_cnt.get(s, 0), mkr, fm, sum(float(r["realizedPnl"]) for r in rs)))
