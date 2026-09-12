#!/usr/bin/env python3
"""Binance Futures liquidation stream listener (public WS !forceOrder@arr).
Appends each forced order to daily liquidations.csv. Auto-reconnects."""
import json, os, time, datetime as dt
import websocket

STORE = "/home/ubuntu/derivs_store"
URL = "wss://fstream.binance.com/ws/!forceOrder@arr"
LOG = STORE + "/liq_ws.log"
HDR = ("event_time,symbol,side,order_type,time_in_force,orig_qty,price,"
       "avg_price,order_status,last_filled_qty,filled_accum_qty,trade_time")

def log(m):
    line = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ ") + str(m)
    print(line, flush=True)
    try:
        open(LOG, "a").write(line + "\n")
    except Exception:
        pass

def on_message(ws, msg):
    try:
        d = json.loads(msg)
        o = d.get("o") or {}
        et = d.get("E")
        tt = o.get("T")
        base = tt or et or int(time.time() * 1000)
        day = dt.datetime.utcfromtimestamp(base / 1000).strftime("%Y%m%d")
        ddir = STORE + "/" + day
        os.makedirs(ddir, exist_ok=True)
        fp = ddir + "/liquidations.csv"
        new = not os.path.exists(fp)
        row = ",".join(str(x) for x in [et, o.get("s"), o.get("S"),
            o.get("o"), o.get("f"), o.get("q"), o.get("p"), o.get("ap"),
            o.get("X"), o.get("l"), o.get("z"), tt])
        with open(fp, "a") as f:
            if new:
                f.write(HDR + "\n")
            f.write(row + "\n")
    except Exception as e:
        log("msg err " + str(e))

def on_error(ws, e):
    log("error " + str(e))

def on_close(ws, a, b):
    log("closed " + str(a) + " " + str(b))

def on_open(ws):
    log("connected " + URL)

if __name__ == "__main__":
    while True:
        try:
            ws = websocket.WebSocketApp(URL, on_message=on_message,
                on_error=on_error, on_close=on_close, on_open=on_open)
            ws.run_forever(ping_interval=180, ping_timeout=10)
        except Exception as e:
            log("run_forever err " + str(e))
        time.sleep(5)
