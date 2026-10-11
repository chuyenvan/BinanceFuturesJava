#!/usr/bin/env python3
"""KFIX F1/F3: websocket <sym>@kline_1m — thoi diem nhan su kien x=true va gia tri so voi REST final.
Stage: run --minutes N -> ws.json ; cmp -> so voi REST final (startTime). Khong dung key, khong ghi gi ngoai WD."""
import argparse, json, logging, os, sys, time, urllib.request
import websocket

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("kfix_wsprobe")
WD = "/home/ubuntu/claude_master/1010/kfix_probe"
MN = 60000


def run(a):
    syms = json.load(open(os.path.join(WD, "probe.json")))["syms"] if os.path.exists(os.path.join(WD, "probe.json")) else None
    if syms is None:
        d = json.loads(urllib.request.urlopen("https://fapi.binance.com/fapi/v1/ticker/24hr", timeout=15).read())
        d = sorted([x for x in d if x["symbol"].endswith("USDT")], key=lambda x: -float(x["quoteVolume"]))
        syms = [x["symbol"] for x in d[:30]]
    url = "wss://fstream.binance.com/market/stream?streams=" + "/".join(s.lower() + "@kline_1m" for s in syms)
    ws = websocket.create_connection(url, timeout=10)
    t_end = time.time() + a.minutes * 60
    ev = []
    last_open = {}
    while time.time() < t_end:
        try:
            msg = ws.recv()
        except websocket.WebSocketTimeoutException:
            continue
        tr = time.time()
        d = json.loads(msg)["data"]
        k = d["k"]
        rec = [d["s"], int(k["t"]), bool(k["x"]), tr, int(d["E"]), float(k["o"]), float(k["h"]), float(k["l"]), float(k["c"]), float(k["q"]), int(k["n"])]
        if rec[2]:
            ev.append(rec)
        else:
            last_open[(d["s"], int(k["t"]))] = rec     # nen chua chot cuoi cung nhan duoc
    ws.close()
    json.dump({"syms": syms, "final_ev": ev, "last_open": list(last_open.values())}, open(os.path.join(WD, "ws.json"), "w"))
    log.info("ws: %d su kien x=true, %d nen co x=false", len(ev), len(last_open))


def f32(x):
    import struct
    return struct.unpack("<f", struct.pack("<f", x))[0]


def cmp(a):
    W = json.load(open(os.path.join(WD, "ws.json")))
    W["syms"] = [s for s in W["syms"] if s.isascii()]
    ev = W["final_ev"]
    t0 = min(e[1] for e in ev)
    t1 = max(e[1] for e in ev)
    fin = {}
    for s in W["syms"]:
        u = "https://fapi.binance.com/fapi/v1/klines?symbol=%s&interval=1m&startTime=%d&limit=%d" % (s, t0, (t1 - t0) // MN + 1)
        for x in json.loads(urllib.request.urlopen(u, timeout=10).read()):
            fin[(s, int(x[0]))] = [float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[7]), int(x[8])]
    n = ok = 0
    lat, latE = [], []
    for e in ev:
        F = fin.get((e[0], e[1]))
        if F is None:
            continue
        n += 1
        same = all(f32(x) == f32(y) for x, y in zip(e[5:10], F[:5])) and e[10] == F[5]
        ok += same
        if not same and n - ok <= 5:
            log.info("ws x=true != final: %s %d ws=%s final=%s", e[0], e[1], e[5:11], F)
        lat.append(e[3] - (e[1] + MN) / 1000.0)
        latE.append(e[4] / 1000.0 - (e[1] + MN) / 1000.0)
    lat.sort(); latE.sort()
    q = lambda v, p: v[min(len(v) - 1, int(p * len(v)))]
    log.info("WS x=true: n=%d == REST final (O,H,L,C,Q,trades) %d (%.2f%%)", n, ok, 100.0 * ok / max(n, 1))
    log.info("tre nhan (gio Oracle, sau khi nen dong): p1 %.3f p50 %.3f p99 %.3f max %.3f s", q(lat, .01), q(lat, .5), q(lat, .99), lat[-1])
    log.info("tre E (event time san): p1 %.3f p50 %.3f p99 %.3f max %.3f s", q(latE, .01), q(latE, .5), q(latE, .99), latE[-1])
    mins = sorted({e[1] for e in ev})
    exp = len(W["syms"]) * (len(mins) - 2)
    got = sum(1 for e in ev if mins[0] < e[1] < mins[-1])
    log.info("do day du x=true (bo 2 phut bien): %d/%d", got, exp)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["run", "cmp"])
    ap.add_argument("--minutes", type=int, default=10)
    x = ap.parse_args()
    run(x) if x.stage == "run" else cmp(x)
