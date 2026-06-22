#!/usr/bin/env python3
"""
TASK-041 A0: đếm số cú sập THỊ TRƯỜNG độc lập theo (H, X) từ chuỗi BTC/ETH 15m close.
Quyết H/X cho gate chặn-sập: chỉ (H,X) có đủ cú sập độc lập (pre-register >= 30) mới đáng train.

forward return H giờ (close-to-close): ret[t] = close[t + H] / close[t] - 1.
"sập" = ret <= -X. de-overlap = greedy 1 cú / cửa sổ H (không đếm chồng).

Env: CSV (mac dinh D:/claudedata/mkt_close_15m.csv)
"""
import os, csv
import numpy as np

CSV = os.environ.get("CSV", "D:/claudedata/mkt_close_15m.csv")
STEP = 15 * 60 * 1000
HS = {"4h": 16, "12h": 48, "24h": 96}
XS = [0.15, 0.20]
MIN_INDEP = 30  # pre-register: duoi nguong nay -> bo cau hinh (khong du mau train)

rows = []
with open(CSV) as f:
    r = csv.reader(f)
    next(r)
    for line in r:
        if len(line) < 2:
            continue
        try:
            e = float(line[2]) if len(line) > 2 and line[2] not in ("", "nan", "NaN") else np.nan
            rows.append((int(line[0]), float(line[1]), e))
        except ValueError:
            continue
rows.sort()
price = {t: c for t, c, _ in rows}
eth = {t: e for t, _, e in rows}
ts0, ts1 = rows[0][0], rows[-1][0]
print(f"{len(rows)} mocs 15m | {np.datetime64(ts0//1000,'s')} .. {np.datetime64(ts1//1000,'s')}")
print(f"{'asset':>6} {'H':>4} {'X':>5} {'n_raw':>7} {'n_indep':>8} {'%time':>7} {'verdict':>8}")


def count(prices, steps, X):
    Hms = steps * STEP
    crash = []
    for t in prices:
        fc = prices.get(t + Hms)
        if fc is None:
            continue
        if fc / prices[t] - 1 <= -X:
            crash.append(t)
    crash.sort()
    indep, last = 0, -10**18
    for t in crash:
        if t > last + Hms:
            indep += 1
            last = t
    pct = 100 * len(crash) / max(1, len(prices))
    return len(crash), indep, pct


for asset, pr in [("BTC", price), ("ETH", {t: e for t, e in eth.items() if not np.isnan(e)})]:
    for Hname, steps in HS.items():
        for X in XS:
            nraw, indep, pct = count(pr, steps, X)
            verdict = "OK" if indep >= MIN_INDEP else "THIN"
            print(f"{asset:>6} {Hname:>4} {int(X*100):>4}% {nraw:>7} {indep:>8} {pct:>6.2f}% {verdict:>8}")

print(f"\n(pre-register: n_indep >= {MIN_INDEP} moi du mau train; THIN -> bo cau hinh do)")
