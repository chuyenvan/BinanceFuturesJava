#!/usr/bin/env python3
"""ADD7 (53ea666e): cong R (REST 10-27 vs Vision 10-27) roi tai REST 10-28 cho universe. Usage: rest1028.py gate | fetch UNIV.json"""
import io, json, os, sys, time, zipfile, urllib.request, urllib.error, datetime as dt
import numpy as np
OUT = "/home/ubuntu/claude_master/gst1030/k1028"
os.makedirs(OUT + "/zips", exist_ok=True)
API = "https://fapi.binance.com/fapi/v1/klines"
HDR = "open_time,open,high,low,close,volume,close_time,quote_volume,count,taker_buy_volume,taker_buy_quote_volume,ignore"
CAP = 300
LOG = open(OUT + "/rest.log", "a")
state = {"used": 0}


def log(*a):
    s = time.strftime("%F %T ") + " ".join(str(x) for x in a)
    print(s, flush=True); LOG.write(s + "\n"); LOG.flush()


def call(sym, start, limit):
    w = 5 if limit >= 500 else 2
    if state["used"] + w > CAP - 10:
        log("weight", state["used"], "-> ngu 61s"); time.sleep(61); state["used"] = 0
    url = "%s?symbol=%s&interval=1m&startTime=%d&limit=%d" % (API, sym, start, limit)
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "research-backfill/1"}), timeout=60)
    except urllib.error.HTTPError as e:
        if e.code in (418, 429):
            log("HTTP", e.code, "-> DUNG NGAY", sym); sys.exit(9)
        if e.code == 400:
            log("400", sym, e.read()[:120]); return []
        raise
    u = r.headers.get("X-MBX-USED-WEIGHT-1M")
    state["used"] = int(u) if u else state["used"] + w
    return json.loads(r.read())


def day(sym, d):
    t0 = int(dt.datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
    a = call(sym, t0, 1000)
    b = call(sym, t0 + 1000 * 60000, 440)
    rows = [x for x in a + b if t0 <= int(x[0]) < t0 + 86400000]
    seen, out = set(), []
    for x in rows:
        if int(x[0]) not in seen:
            seen.add(int(x[0])); out.append([str(v) for v in x])
    return out


def vision(sym, d):
    b = urllib.request.urlopen("https://data.binance.vision/data/futures/um/daily/klines/%s/1m/%s-1m-%s.zip" % (sym, sym, d), timeout=120).read()
    z = zipfile.ZipFile(io.BytesIO(b))
    return [l.split(",") for l in z.read(z.namelist()[0]).decode().splitlines() if l[:1].isdigit()]


def gate():
    res = {}
    for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "PARTIUSDT", "BLESSUSDT"):
        r, v = day(s, "2026-10-27"), vision(s, "2026-10-27")
        C = (0, 1, 2, 3, 4, 7)
        byte = len(r) == len(v) == 1440 and all(all(a[c] == b[c] for c in C) for a, b in zip(r, v))
        f32 = len(r) == len(v) and all(all(np.float32(float(a[c])) == np.float32(float(b[c])) for c in C) for a, b in zip(r, v))
        bad = [(i, [a[c] for c in C], [b[c] for c in C]) for i, (a, b) in enumerate(zip(r, v)) if any(a[c] != b[c] for c in C)][:2]
        res[s] = dict(n_rest=len(r), n_vision=len(v), byte=byte, f32=f32, first_bad=bad)
        log("GATE_R", s, res[s])
    res["PASS"] = all(x["byte"] for k, x in res.items() if k != "PASS")
    json.dump(res, open(OUT + "/gateR.json", "w"), indent=1)
    log("GATE_R_PASS", res["PASS"])
    return res["PASS"]


def fetch(univ):
    syms = json.load(open(univ))["2026-10"]
    man = {}
    for i, s in enumerate(syms):
        p = OUT + "/zips/%s-1m-2026-10-28.zip" % s
        if os.path.exists(p):
            continue
        rows = day(s, "2026-10-28")
        man[s] = len(rows)
        if not rows:
            log("rong", s); continue
        csv = HDR + "\n" + "\n".join(",".join(x) for x in rows) + "\n"
        with zipfile.ZipFile(p + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("%s-1m-2026-10-28.csv" % s, csv)
        os.replace(p + ".tmp", p)
        if i % 50 == 0:
            log("tien do", i, len(syms), s, len(rows), "weight", state["used"])
    json.dump(man, open(OUT + "/fetch_manifest_%d.json" % int(time.time()), "w"))
    n = len([f for f in os.listdir(OUT + "/zips") if f.endswith(".zip")])
    log("FETCH_DONE symbols", len(syms), "zip", n)


if __name__ == "__main__":
    if sys.argv[1] == "gate":
        sys.exit(0 if gate() else 2)
    if sys.argv[1] == "fetch":
        if not json.load(open(OUT + "/gateR.json")).get("PASS"):
            log("cong R chua PASS -> khong tai"); sys.exit(2)
        fetch(sys.argv[2])
