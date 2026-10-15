#!/usr/bin/env python3
"""Binance USDT-M futures LIQUIDATION forward collector (public WS, NO REST).

QUEUE_1015 P2. Writes one gzip CSV per UTC day:
    ~/collect/liq/YYYY-MM-DD.csv.gz
Columns:
    event_time,symbol,side,order_type,price,avg_price,orig_qty,filled_qty,status,trade_time

ENDPOINT (2026-10-15, verified on this Oracle host):
    wss://fstream.binance.com/market/stream?streams=!forceOrder@arr
  The RAW endpoint `wss://fstream.binance.com/ws/!forceOrder@arr` completes the
  HTTP-101 upgrade from this host but then delivers ZERO frames (same for
  `/ws/<sym>@aggTrade`); only the COMBINED `/market/stream` endpoint streams.
  That is why the previous collector (same filename, raw endpoint) never wrote a
  single row (see ~/derivs_store/liq_ws.log, "connected" since 2026-09-12).

SELF-VERIFICATION DATA: on the first liquidation for a symbol the collector also
  SUBSCRIBEs to `<sym>@kline_1m` on the same connection and stores the CLOSED 1m
  candle to ~/collect/liq/kline1m/YYYY-MM-DD.csv.gz. This lets the 1h health
  check verify that each liquidation price is inside the [low, high] of its own
  1m candle without any REST call.

LIMITATION (documented, per plan): Binance pushes at most the LATEST liquidation
  order per symbol per 1000 ms (snapshot semantics) => this feed is a SAMPLE of
  liquidations, NOT the complete set.

Robustness: exponential reconnect backoff, a watchdog thread that force-closes
the socket if no frame/pong arrives within STALE_SEC, heartbeat line every
HEARTBEAT_SEC with the cumulative event count, daily UTC file rotation.
"""
import gzip
import json
import os
import signal
import socket
import sys
import threading
import time
import datetime as dt

import websocket

STORE = os.path.expanduser("~/collect/liq")
KDIR = os.path.join(STORE, "kline1m")
URL = "wss://fstream.binance.com/market/stream?streams=!forceOrder@arr"
LOG = os.path.join(STORE, "liq_ws.log")
PIDFILE = os.path.join(STORE, "liq_ws.pid")
STALE_SEC = 300          # force reconnect if no frame/pong for this long
HEARTBEAT_SEC = 300      # heartbeat log cadence (5')
HDR = ("event_time,symbol,side,order_type,price,avg_price,orig_qty,"
       "filled_qty,status,trade_time")
KHDR = "open_time,symbol,open,high,low,close,volume,trades,close_time"

_state = {
    "total": 0,
    "last_day": None,
    "last_activity": time.time(),
    "last_hb": time.time(),
    "ksub": 0,
    "kline": 0,
}
_lock = threading.Lock()


def log(msg):
    line = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ ") + str(msg)
    print(line, flush=True)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _day_str(ms):
    return dt.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d")


def _append_gz(path, fresh_header, row):
    fresh = (not os.path.exists(path)) or os.path.getsize(path) == 0
    with gzip.open(path, "at", newline="") as f:
        if fresh:
            f.write(fresh_header + "\n")
        f.write(row + "\n")


def write_event(o, ev_time):
    tt = o.get("T")
    base = tt or ev_time or int(time.time() * 1000)
    day = _day_str(base)
    _append_gz(os.path.join(STORE, day + ".csv.gz"), HDR, ",".join(str(x) for x in [
        ev_time, o.get("s"), o.get("S"), o.get("o"), o.get("p"),
        o.get("ap"), o.get("q"), o.get("z"), o.get("X"), o.get("T"),
    ]))
    return day


def write_kline(k):
    day = _day_str(k["t"])
    _append_gz(os.path.join(KDIR, day + ".csv.gz"), KHDR, ",".join(str(x) for x in [
        k.get("t"), k.get("s"), k.get("o"), k.get("h"), k.get("l"),
        k.get("c"), k.get("v"), k.get("n"), k.get("T"),
    ]))


def _subscribe_klines(ws, symbols):
    """Subscribe sym@kline_1m for newly seen liquidation symbols."""
    with _lock:
        new = [s for s in symbols if s and s not in _state.setdefault("subs", set())]
        for s in new:
            _state["subs"].add(s)
    if not new:
        return
    params = [s.lower() + "@kline_1m" for s in new]
    try:
        ws.send(json.dumps({"method": "SUBSCRIBE", "params": params, "id": 1}))
        with _lock:
            _state["ksub"] += len(params)
    except Exception as e:
        log("subscribe err " + str(e))
        with _lock:
            for s in new:
                _state["subs"].discard(s)


def on_message(ws, msg):
    _state["last_activity"] = time.time()
    try:
        d = json.loads(msg)
        data = d.get("data", d)          # combined-stream wrapper
        e = data.get("e")
        if e == "forceOrder":
            o = data.get("o") or {}
            sym = o.get("s")
            _subscribe_klines(ws, [sym])
            day = write_event(o, data.get("E"))
            with _lock:
                _state["total"] += 1
                _state["last_day"] = day
        elif e == "kline":
            k = data.get("k") or {}
            if k.get("x"):               # closed candle only
                write_kline(k)
                with _lock:
                    _state["kline"] += 1
    except Exception as ex:
        log("msg err " + str(ex))


def on_pong(ws, msg):
    _state["last_activity"] = time.time()


def on_ping(ws, msg):
    _state["last_activity"] = time.time()


def on_error(ws, e):
    log("error " + str(e))


def on_close(ws, a, b):
    log("closed " + str(a) + " " + str(b))


def on_open(ws):
    _state["last_activity"] = time.time()
    with _lock:
        _state["subs"] = set()           # a reconnect drops all subscriptions
    log("connected " + URL)


def _watchdog(ws):
    while True:
        time.sleep(15)
        idle = time.time() - _state["last_activity"]
        if idle > STALE_SEC:
            log("watchdog: stale %.0fs, forcing reconnect" % idle)
            try:
                ws.close()
            except Exception as e:
                log("watchdog close err " + str(e))
            _state["last_activity"] = time.time()
        if time.time() - _state["last_hb"] >= HEARTBEAT_SEC:
            _state["last_hb"] = time.time()
            with _lock:
                log("heartbeat events=%d klines=%d ksub=%d last_day=%s" % (
                    _state["total"], _state["kline"], _state["ksub"],
                    _state["last_day"]))


def _keepalive_sockopt():
    opts = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
    for name, val in (("TCP_KEEPIDLE", 30), ("TCP_KEEPINTVL", 10), ("TCP_KEEPCNT", 3)):
        c = getattr(socket, name, None)
        if c is not None:
            opts.append((socket.IPPROTO_TCP, c, val))
    return opts


def _term(signum, frame):
    log("signal %d: exiting cleanly (events=%d)" % (signum, _state["total"]))
    sys.exit(0)


def main():
    os.makedirs(STORE, exist_ok=True)
    os.makedirs(KDIR, exist_ok=True)
    _state["subs"] = set()
    try:
        with open(PIDFILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass
    signal.signal(signal.SIGTERM, _term)
    signal.signal(signal.SIGINT, _term)
    backoff = 1
    log("start events=%d endpoint=%s" % (_state["total"], URL))
    while True:
        try:
            ws = websocket.WebSocketApp(
                URL, on_message=on_message, on_error=on_error,
                on_close=on_close, on_open=on_open, on_pong=on_pong,
                on_ping=on_ping)
            threading.Thread(target=_watchdog, args=(ws,), daemon=True).start()
            t0 = time.time()
            ws.run_forever(ping_interval=60, ping_timeout=15,
                           sockopt=_keepalive_sockopt())
            if time.time() - t0 > 60:
                backoff = 1
        except Exception as e:
            log("run_forever err " + str(e))
        log("reconnect in %ds" % backoff)
        time.sleep(backoff)
        backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    main()
