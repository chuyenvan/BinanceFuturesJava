#!/usr/bin/env python3
"""TSX_V2 - nap du lieu chung (cum, cua so gia, funding, tick size, ALT_EW, co)."""
import hashlib
import json
import pickle
from decimal import Decimal

import numpy as np
import pandas as pd

import engine as EN

D = "/home/ubuntu/claude_master/tsx_v2"
CACHE = D + "/cache"
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
CAP504 = 504 * 60
DEV0, DEV1 = pd.Timestamp("2021-07-01"), pd.Timestamp("2025-12-31")


def ticks():
    ex = json.load(open("/home/ubuntu/java/exchange_info_pin.json"))
    out = {}
    for s in ex["symbols"]:
        for fl in s["filters"]:
            for f in fl:
                if f.get("tickSize") is not None:
                    out[s["symbol"]] = Decimal(EN.jstr(np.float32(float(f["tickSize"]))))
    return out


def load_all():
    C = pd.read_pickle(CACHE + "/clusters.pkl")
    keys = pickle.load(open(CACHE + "/win_meta.pkl", "rb"))
    arr = np.load(CACHE + "/win.npy", mmap_mode="r")
    fund = pickle.load(open(CACHE + "/fund.pkl", "rb"))
    return C, keys, arr, fund


def nofund_syms(C):
    """sym ma sim KHONG co du lieu funding: moi cum (>168h, >= 21 moc settle) trong 16 run deu funding = 0 (vd LIT)."""
    g = C.groupby("sym")["fund"].apply(lambda x: bool((x == 0).all()))
    return set(g[g].index)


class Wins:
    def __init__(self, keys, arr, fund, tk, use_tick=True, nofund=()):
        self.keys, self.arr, self.fund, self.tk, self.use_tick = keys, arr, fund, tk, use_tick
        self.nofund = set(nofund)
        self.cache = {}

    def get(self, wid):
        w = self.cache.get(wid)
        if w is None:
            sym, t0 = self.keys[wid]
            tick = self.tk.get(sym + "USDT") if self.use_tick else None
            fz = (np.zeros(0, np.int64), np.zeros(0)) if sym in self.nofund else self.fund[wid]
            w = EN.Win(np.asarray(self.arr[wid]), t0, fz, tick)
            self.cache[wid] = w
        return w


# ------------------------------------------------------------------ ALT_EW
def ew_minute():
    a = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
    ts = a["ew_ts"].astype(np.int64)
    L = np.cumsum(a["ew_r"].astype(np.float64))
    return ts, L


def ew_eod():
    ts, L = ew_minute()
    s = pd.Series(L, index=pd.to_datetime(ts, unit="ms"))
    return s.groupby(s.index.floor("D")).last()


def dd_series(eod, lookback):
    """dd(d) = exp(EOD(d) - max EOD(d-lookback..d)) - 1; co ap cho ngay d+1."""
    return np.exp(eod - eod.rolling(lookback + 1, min_periods=1).max()) - 1


def flag_days(eod, thr, lookback):
    dd = dd_series(eod, lookback)
    fd = sorted(dd[dd <= thr].index + pd.Timedelta(days=1))
    return [d for d in fd if DEV0 <= d <= DEV1]


def ranges_of(days):
    rng, st, pv = [], None, None
    for d in days:
        if st is None:
            st = pv = d
        elif d == pv + pd.Timedelta(days=1):
            pv = d
        else:
            rng.append((st, pv))
            st = pv = d
    if st is not None:
        rng.append((st, pv))
    return rng


def rstr(rng):
    return ",".join("%s-%s" % (x.strftime("%Y%m%d"), y.strftime("%Y%m%d")) for x, y in rng)


def base_flags_check(eod):
    days = flag_days(eod, -0.30, 30)
    pre = json.load(open("/home/ubuntu/claude_master/tsx/flags.json"))
    r = rstr(ranges_of(days))
    ok = r == pre["ranges"] and hashlib.sha256(r.encode()).hexdigest() == pre["sha256"]
    return days, ok


def dayints(days):
    return np.array([int(d.value // 86400000000000) for d in days], np.int64)


def episodes(eod, gap=3):
    """dot = cac khoang lien tiep cua tap co rong nhat (thr -0.25, lookback 45 - bao trum moi o B4), noi khoang cach <= gap ngay."""
    days = flag_days(eod, -0.25, 45)
    rng = ranges_of(days)
    out = []
    for a, b in rng:
        if out and (a - out[-1][1]).days - 1 <= gap:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out
