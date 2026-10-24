import sys, json, collections, time
sys.path.insert(0, "/home/ubuntu/claude_master/chd_wk")
import chd_lib as L
c = L.client()
print("exchanges", c.list_exchanges())
print("info", json.dumps(c.get_exchange_info("binance_futures")))
for dt in [None, "liquidations", "open_interest", "mark_price", "trades", "orderbook", "ticker"]:
    try:
        s = c.list_symbols("binance_futures", dt)
        print("symbols", dt, len(s), s[:5])
    except Exception as e:
        print("symbols ERR", dt, type(e).__name__, str(e)[:200])
t = time.time()
L.prov()
print("s3 creds ok", round(time.time() - t, 2))
for d, h in [("2025-06-28", 0), ("2025-09-02", 12), ("2025-10-10", 21), ("2026-10-23", 12)]:
    t = time.time()
    objs = L.list_hour(d, h)
    agg = collections.defaultdict(lambda: [0, 0])
    ext = collections.Counter()
    for o in objs:
        agg[o["data_type"]][0] += 1
        agg[o["data_type"]][1] += o["size"]
        ext[o.get("extension")] += 1
    print(d, h, "n=", len(objs), "t=", round(time.time() - t, 1), dict(ext))
    for k, (n, b) in sorted(agg.items(), key=lambda x: str(x[0])):
        print("   ", k, n, round(b / 1e6, 2), "MB")
    for sym in ["BTCUSDT", "SOLUSDT", "1000PEPEUSDT"]:
        print("    ", sym, [(o["data_type"], o["size"]) for o in objs if o["symbol"] == sym])
    if objs and objs[0]["data_type"] is None:
        print("unparsed sample", objs[0]["key"])
