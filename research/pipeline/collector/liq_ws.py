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
  single row (see ~/derivs_store/liq_ws.log, connected since 2026-09-12).

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
URL = "wss://fstream.binance.com/market/stream?streams=!forceOrder@arr"
LOG = os.path.join(STORE, "liq_ws.log")
PIDFILE = os.path.join(STORE, "liq_ws.pid")
STALE_SEC = 300          # force reconnect if no frame/pong for this long
HEARTBEAT_SEC = 300      # heartbeat log cadence (5')
HDR = ("event_time,symbol,side,order_type,price,avg_price,orig_qty,"
       "filled_qty,status,trade_time")

_state = {
    "total": 0,
    "last_day": None,
    "last_activity": time.time(),
    "last_hb": time.time(),
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


def _path_for_day(day):
    return os.path.join(STORE, day + ".csv.gz")


def _row(o, ev_time):
    return ",".join(str(x) for x in [
        ev_time, o.get("s"), o.get("S"), o.get("o"), o.get("p"),
        o.get("ap"), o.get("q"), o.get("z"), o.get("X"), o.get("T"),
    ])


def write_event(o, ev_time):
    tt = o.get("T")
    base = tt or ev_time or int(time.time() * 1000)
    day = dt.datetime.utcfromtimestamp(base / 1000).strftime("%Y-%m-%d")
    path = _path_for_day(day)
    fresh = (not os.path.exists(path)) or os.path.getsize(path) == 0
    # gzip append = a new gzip member; Python/pandas read multi-member fine.
    with gzip.open(path, "at", newline="") as f:
        if fresh:
            f.write(HDR + "\n")
        f.write(_row(o, ev_time) + "\n")
    return day


def on_message(ws, msg):
    _state["last_activity"] = time.time()
    try:
        d = json.loads(msg)
        data = d.get("data", d)          # combined-stream wrapper
        if data.get("e") != "forceOrder":
            return
        o = data.get("o") or {}
        day = write_event(o, data.get("E"))
        with _lock:
            _state["total"] += 1
            _state["last_day"] = day
    except Exception as e:
        log("msg err " + str(e))


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
                log("heartbeat events=%d last_day=%s" % (_state["total"], _state["last_day"]))


def _keepalive_sockopt():
    opts = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
    for name, val in (("TCP_KEEPIDLE", 30), ("TCP_KEEPINTVL", 10), ("TCP_KEEPCNT", 3)):
        c = getattr(socket, name, None)
        if c is not None:
            opts.append((socket.IPPROTO_TCP, c, val))
    return opts


def _write_pid():
    try:
        with open(PIDFILE, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass


def _term(signum, frame):
    log("signal %d: exiting cleanly (events=%d)" % (signum, _state["total"]))
    sys.exit(0)


def main():
    os.makedirs(STORE, exist_ok=True)
    _write_pid()
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
            # a clean run_forever exit means the socket dropped
            if time.time() - t0 > 60:
                backoff = 1
        except Exception as e:
            log("run_forever err " + str(e))
        log("reconnect in %ds" % backoff)
        time.sleep(backoff)
        backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    main()
