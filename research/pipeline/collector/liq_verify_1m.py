#!/usr/bin/env python3
"""QUEUE_1015 P2 health check: liquidation price inside its 1m candle [low, high].

No REST. Joins the forward liquidation feed with the 1m candles that the
collector captured on the same WS connection:

  ~/collect/liq/YYYY-MM-DD.csv.gz          (event_time,symbol,...,price,...,trade_time)
  ~/collect/liq/kline1m/YYYY-MM-DD.csv.gz  (open_time,symbol,open,high,low,close,...)

Usage:
    python3 liq_verify_1m.py [YYYY-MM-DD] [--min-rate 0.99]

Exit code 0 always (report-only); prints a machine-readable JSON summary last.
"""
import gzip
import json
import os
import sys
import datetime as dt

STORE = os.path.expanduser("~/collect/liq")


def _read_gz(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with gzip.open(path, "rt") as f:
        hdr = f.readline().rstrip("\n").split(",")
        for line in f:
            p = line.rstrip("\n").split(",")
            if len(p) != len(hdr):
                continue
            rows.append(dict(zip(hdr, p)))
    return rows


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    day = args[0] if args else dt.datetime.utcnow().strftime("%Y-%m-%d")
    mine = 0.99
    for a in sys.argv[1:]:
        if a.startswith("--min-rate"):
            mine = float(a.split("=", 1)[1])

    liq = _read_gz(os.path.join(STORE, day + ".csv.gz"))
    kl = _read_gz(os.path.join(STORE, "kline1m", day + ".csv.gz"))

    # (symbol, minute_open_ms) -> (low, high)
    candles = {}
    for k in kl:
        try:
            key = (k["symbol"], int(k["open_time"]) // 60000)
            lo, hi = float(k["low"]), float(k["high"])
        except Exception:
            continue
        prev = candles.get(key)
        candles[key] = (min(lo, prev[0]), max(hi, prev[1])) if prev else (lo, hi)

    # The health check uses avg_price = the ACTUAL liquidation fill. `price`
    # (Binance forceOrder o.p) is the order/bankruptcy price and is NOT expected
    # inside the 1m range; it is reported only for reference.
    tot = covered = inside = inside_px = 0
    missing = {}
    out_of_range = []
    for r in liq:
        try:
            sym = r["symbol"]
            fill = float(r["avg_price"] or r["price"])
            px = float(r["price"])
            tt = int(r["trade_time"]) if r.get("trade_time") else int(r["event_time"])
        except Exception:
            continue
        tot += 1
        key = (sym, tt // 60000)
        c = candles.get(key)
        if not c:
            missing[sym] = missing.get(sym, 0) + 1
            continue
        covered += 1
        if c[0] <= px <= c[1]:
            inside_px += 1
        if c[0] <= fill <= c[1]:
            inside += 1
        else:
            out_of_range.append({"symbol": sym, "avg_price": fill, "price": px,
                                 "low": c[0], "high": c[1],
                                 "minute_ms": key[1] * 60000})

    rate = (inside / covered) if covered else None
    res = {
        "day": day,
        "liq_events": tot,
        "with_candle": covered,
        "inside_low_high": inside,
        "rate_inside": rate,
        "rate_inside_order_price_ref": (inside_px / covered) if covered else None,
        "coverage": (covered / tot) if tot else None,
        "min_rate": mine,
        "pass": (rate is not None and rate >= mine),
        "out_of_range_sample": out_of_range[:10],
        "missing_top": sorted(missing.items(), key=lambda x: -x[1])[:10],
    }
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
