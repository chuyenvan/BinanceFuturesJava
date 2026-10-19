import json
import numpy as np
B = json.load(open("/home/ubuntu/claude_master/bookhedge/book_hedge.json"))
E = json.load(open("/home/ubuntu/claude_master/bookhedge_eth/book_hedge_eth.json"))
S = list(B["per_seed"])
for k in ("h0.5", "h1.0"):
    print("ETH", k, json.dumps(E["summary"][k]))
    for nm, X in (("BTC", B), ("ETH", E)):
        dd = [round(X["per_seed"][s][k]["dd22"] - X["per_seed"][s]["base"]["dd22"], 2) for s in S]
        cal = [round(X["per_seed"][s][k]["calmar22"] - X["per_seed"][s]["base"]["calmar22"], 3) for s in S]
        hy = {y: round(np.mean([X["per_seed"][s][k]["hedge_pnl_year"].get(y, 0) for s in S])) for y in ("2021", "2022", "2023", "2024", "2025")}
        print(" ", nm, k, "dDD", dd, "dCal", cal, "hedgePnL/yr", hy)
    d = np.array([E["per_seed"][s][k]["calmar22"] - B["per_seed"][s][k]["calmar22"] for s in S])
    dd = np.array([E["per_seed"][s][k]["dd22"] - B["per_seed"][s][k]["dd22"] for s in S])
    print("  ETH-BTC paired dCal %.3f (pos %d/8)  dDD %.2f (pos %d/8)" % (d.mean(), (d > 0).sum(), dd.mean(), (dd > 0).sum()))
print("corr book-ETH", np.mean([E["per_seed"][s]["corr_book_btc_daily"] for s in S]))
