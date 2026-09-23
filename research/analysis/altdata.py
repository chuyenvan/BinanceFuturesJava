"""Daily close matrix (UTC day-end) for the ALT-regime study.

DEV source: /home/ubuntu/java/fsrun/CLOSES_1H.bin  (hour 23:00 close == day end)
2026 source: /home/ubuntu/altregime/daily/<YYYYMMDD>.csv (23:59 minute close)
Symbol universe: /home/ubuntu/map_kaggle.csv (symId -> symbol), base = symbol w/o USDT.
"""
import datetime as dt
import os

import numpy as np
import pandas as pd

CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
MAP = "/home/ubuntu/map_kaggle.csv"
DAILY_DIR = "/home/ubuntu/altregime/daily"
SEAL = 1767225600000          # 2026-01-01T00:00Z
DAY = 86400000
HOUR = 3600000

MAJORS = "BTC ETH BNB SOL XRP ADA DOGE AVAX DOT LINK TRX MATIC POL LTC BCH".split()


def load_map():
    m = pd.read_csv(MAP)
    m["base"] = m["symbol"].str.replace("USDT$", "", regex=True)
    return m


def dev_daily():
    """daily close per (base symbol, UTC date) from hourly closes.

    DO CHINH XAC (kiem cheo 24 ngay mau, xem RESULT): gia tri tai `ts` LA gia tri dong
    tai `ts` (khong phai open_time) -> close ngay UTC D = ban ghi `ts = (D+1) 00:00:00Z`.
    Khop tuyet doi (rel diff = 0) voi phut 23:59 cua ticker bins.
    """
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(CLOSES, dtype=DT)
    ts = a["ts"].astype(np.int64)
    sym = a["sym"].astype(np.int64)
    c = a["c"].astype(np.float64)
    m = (ts % DAY) == 0            # 00:00:00Z == dong ngay hom truoc (UTC)
    ts, sym, c = ts[m], sym[m], c[m]
    day = pd.to_datetime(ts, unit="ms", utc=True).normalize().tz_localize(None) - pd.Timedelta(days=1)
    mp = load_map()
    s2b = dict(zip(mp.symId, mp.base))
    df = pd.DataFrame({"date": day, "base": [s2b.get(int(s), None) for s in sym], "close": c})
    df = df.dropna(subset=["base"])
    w = df.pivot_table(index="date", columns="base", values="close", aggfunc="last")
    return w.sort_index()


def ext_daily():
    """daily close per (base symbol, UTC date) from extracted 23:59 minute closes."""
    rows = {}
    if not os.path.isdir(DAILY_DIR):
        return pd.DataFrame()
    for fn in sorted(os.listdir(DAILY_DIR)):
        if not fn.endswith(".csv"):
            continue
        d = dt.datetime.strptime(fn[:-4], "%Y%m%d").date()
        with open(os.path.join(DAILY_DIR, fn)) as f:
            for ln in f:
                p = ln.rstrip("\n").split(",")
                if len(p) != 2:
                    continue
                try:
                    rows.setdefault(d, {})[p[0]] = float(p[1])
                except ValueError:
                    pass
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index = pd.to_datetime(df.index)
    return df.sort_index().sort_index(axis=1)


def load_all(only_dev=False):
    w = dev_daily()
    if only_dev:
        return w
    e = ext_daily()
    if len(e):
        e = e[e.index > pd.Timestamp("2025-12-31")]
        cols = sorted(set(w.columns) | set(e.columns))
        w = w.reindex(columns=cols)
        e = e.reindex(columns=cols)
        w = pd.concat([w[w.index < pd.Timestamp("2026-01-01")], e])
    return w


def rets(w, d=1):
    return w / w.shift(d) - 1.0
