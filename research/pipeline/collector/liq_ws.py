#!/usr/bin/env python3
"""Binance Futures liquidation stream listener (public WS !forceOrder@arr).
Appends each forced order to daily liquidations.csv. Auto-reconnects.

2026-09-19 fix: process was observed ESTAB on the TCP socket for 4 days
(2026-09-15..09-19) with zero log lines / zero rows written -- a silent
half-open TCP connection that websocket-client's ping/pong logic did not
detect (peer/middlebox dropped packets silently, no TCP keepalive was
enabled so the kernel never noticed). Fix: (1) enable SO_KEEPALIVE +
short TCP_KEEPIDLE/INTVL/CNT so the kernel detects a dead peer, and
(2) an explicit watchdog thread that force-closes the socket (which
trips the existing outer reconnect loop) if no message/pong has been
seen for STALE_SEC, independent of OS-level keepalive."""
import json, os, socket, threading, time, datetime as dt
import websocket

STORE = "/home/ubuntu/derivs_store"
URL = "wss://fstream.binance.com/ws/!forceOrder@arr"
LOG = STORE + "/liq_ws.log"
STALE_SEC = 300  # force-reconnect if no message/pong seen this long
HDR = ("event_time,symbol,side,order_type,time_in_force,orig_qty,price,"
       "avg_price,order_status,last_filled_qty,filled_accum_qty,trade_time")

_last_activity = [time.time()]

def log(m):
    line = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ ") + str(m)
    print(line, flush=True)
    try:
        open(LOG, "a").write(line + "\n")
    except Exception:
        pass

def on_message(ws, msg):
    _last_activity[0] = time.time()
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

def on_pong(ws, msg):
    _last_activity[0] = time.time()

def on_error(ws, e):
    log("error " + str(e))

def on_close(ws, a, b):
    log("closed " + str(a) + " " + str(b))

def on_open(ws):
    _last_activity[0] = time.time()
    log("connected " + URL)

def _watchdog(ws):
    while True:
        time.sleep(30)
        idle = time.time() - _last_activity[0]
        if idle > STALE_SEC:
            log("watchdog: stale %.0fs, forcing reconnect" % idle)
            try:
                ws.close()
            except Exception as e:
                log("watchdog close err " + str(e))
            _last_activity[0] = time.time()

def _keepalive_sockopt():
    opts = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
    for name, val in (("TCP_KEEPIDLE", 30), ("TCP_KEEPINTVL", 10), ("TCP_KEEPCNT", 3)):
        c = getattr(socket, name, None)
        if c is not None:
            opts.append((socket.IPPROTO_TCP, c, val))
    return opts

if __name__ == "__main__":
    while True:
        try:
            ws = websocket.WebSocketApp(URL, on_message=on_message,
                on_error=on_error, on_close=on_close, on_open=on_open,
                on_pong=on_pong)
            t = threading.Thread(target=_watchdog, args=(ws,), daemon=True)
            t.start()
            ws.run_forever(ping_interval=60, ping_timeout=10,
                sockopt=_keepalive_sockopt())
        except Exception as e:
            log("run_forever err " + str(e))
        time.sleep(5)
