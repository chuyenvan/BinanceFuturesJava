#!/usr/bin/env python3
"""Binance Futures derivatives collector (public REST only).
Collects OI, funding/markPrice, long/short ratios every 5 min.
Appends daily CSVs; gzips days older than today. Idempotent per 5m cycle."""
import os, sys, time, json, gzip, glob, fcntl, datetime as dt
import requests

BASE = "https://fapi.binance.com"
STORE = "/home/ubuntu/derivs_store"
LOG = STORE + "/collector.log"
S = requests.Session()
S.headers.update({"User-Agent": "derivs-collector/1.0"})

def log(msg):
    line = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ ") + str(msg)
    print(line, flush=True)
    try:
        with open(LOG, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def get(path, params=None, tries=3):
    for i in range(tries):
        try:
            r = S.get(BASE + path, params=params, timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (418, 429):
                log("rate " + str(r.status_code) + " " + path)
                time.sleep(3 + 3 * i)
                continue
            return None
        except Exception:
            time.sleep(1 + i)
    return None

def universe():
    d = get("/fapi/v1/exchangeInfo")
    if not d:
        return []
    return sorted(s["symbol"] for s in d.get("symbols", [])
                  if s.get("contractType") == "PERPETUAL"
                  and s.get("quoteAsset") == "USDT"
                  and s.get("status") == "TRADING")

def append_rows(fpath, header, rows):
    newfile = not os.path.exists(fpath)
    with open(fpath, "a") as f:
        if newfile:
            f.write(header + "\n")
        for r in rows:
            f.write(r + "\n")

def compress_old(today):
    for d in glob.glob(STORE + "/2*"):
        day = os.path.basename(d)
        if not day.isdigit() or day >= today:
            continue
        for csv in glob.glob(d + "/*.csv"):
            gz = csv + ".gz"
            try:
                if not os.path.exists(gz):
                    with open(csv, "rb") as fi, gzip.open(gz, "wb") as fo:
                        fo.writelines(fi)
                os.remove(csv)
            except Exception as e:
                log("gzip fail " + csv + ": " + str(e))

def main():
    now = int(time.time())
    cycle = (now // 300) * 300
    deadline = cycle + 285
    cyc_iso = dt.datetime.utcfromtimestamp(cycle).strftime("%Y-%m-%dT%H:%M:%SZ")
    today = dt.datetime.utcfromtimestamp(cycle).strftime("%Y%m%d")
    daydir = STORE + "/" + today
    os.makedirs(daydir, exist_ok=True)
    marker = STORE + "/.last_cycle"
    if os.path.exists(marker):
        try:
            if open(marker).read().strip() == str(cycle):
                log("cycle " + str(cycle) + " already done, skip")
                return
        except Exception:
            pass
    syms = universe()
    log("universe=" + str(len(syms)) + " cycle=" + cyc_iso)
    if not syms:
        log("no universe, abort")
        return
    sset = set(syms)
    prem = get("/fapi/v1/premiumIndex") or []
    frows = []
    for p in prem:
        s = p.get("symbol")
        if s in sset:
            frows.append(",".join(str(x) for x in [cycle, cyc_iso, s,
                p.get("markPrice"), p.get("indexPrice"),
                p.get("lastFundingRate"), p.get("nextFundingTime")]))
    append_rows(daydir + "/funding.csv",
        "cycle_ts,cycle_iso,symbol,markPrice,indexPrice,lastFundingRate,nextFundingTime", frows)
    oirows = []
    for s in syms:
        d = get("/fapi/v1/openInterest", {"symbol": s})
        if d:
            oirows.append(",".join(str(x) for x in [cycle, cyc_iso, s,
                d.get("openInterest"), d.get("time")]))
        time.sleep(0.02)
    append_rows(daydir + "/oi.csv",
        "cycle_ts,cycle_iso,symbol,openInterest,time", oirows)
    lsrg = []
    lsrt = []
    for s in syms:
        if time.time() > deadline:
            log("deadline hit during LSR, partial")
            break
        g = get("/futures/data/globalLongShortAccountRatio",
                {"symbol": s, "period": "5m", "limit": 1})
        if g:
            x = g[0]
            lsrg.append(",".join(str(v) for v in [cycle, cyc_iso, s,
                x.get("longAccount"), x.get("shortAccount"),
                x.get("longShortRatio"), x.get("timestamp")]))
        time.sleep(0.015)
        t = get("/futures/data/topLongShortPositionRatio",
                {"symbol": s, "period": "5m", "limit": 1})
        if t:
            x = t[0]
            lsrt.append(",".join(str(v) for v in [cycle, cyc_iso, s,
                x.get("longAccount"), x.get("shortAccount"),
                x.get("longShortRatio"), x.get("timestamp")]))
        time.sleep(0.015)
    hdr = "cycle_ts,cycle_iso,symbol,longAccount,shortAccount,longShortRatio,timestamp"
    append_rows(daydir + "/lsr_global.csv", hdr, lsrg)
    append_rows(daydir + "/lsr_top.csv", hdr, lsrt)
    try:
        with open(marker, "w") as f:
            f.write(str(cycle))
    except Exception:
        pass
    log("done oi=" + str(len(oirows)) + " funding=" + str(len(frows)) +
        " lsrg=" + str(len(lsrg)) + " lsrt=" + str(len(lsrt)))
    try:
        compress_old(today)
    except Exception as e:
        log("compress_old err: " + str(e))

if __name__ == "__main__":
    lf = open("/tmp/collect_derivs.lock", "w")
    try:
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("another instance running, exit")
        sys.exit(0)
    try:
        main()
    except Exception as e:
        log("FATAL " + str(e))
        sys.exit(1)
