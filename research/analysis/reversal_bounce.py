#!/usr/bin/env python3
"""REVERSAL_BOUNCE — reversal-bounce long (tong quat isBtcTrendReverse) edge + MOM15 overlap/ICC.

Pre-registered: docs/prereg/PREREG_REVERSAL_BOUNCE.md (commit truoc khi chay). 0-sim, THUAN PYTHON,
khong Java, khong push. Doc 1M closes causal (Aerospike kline_1m_opt da extract san thanh
raw/<sym>.f32). Trigger: 1 nguong CO DINH (DROP_THRESH=0.01), HOLD 24h.

Output: /tmp/reversal_bounce/{signals.csv, report.txt}. Tam, xoa sau.
"""
import os
import glob
import struct
import json
import math
import logging
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

RAW = "/home/ubuntu/claudedata/rvb_1m/raw"
OUT = "/tmp/reversal_bounce"
os.makedirs(OUT, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("rvb2")

# ---- LOCKED params (PREREG) ----
DROP_THRESH = 0.01          # 1.0% drop from 15m/30m high (fixed, no FIT loop)
W15, W30 = 15, 30           # window (minutes)
HOLD = 1440                 # 24h
TAKER = 0.0005
FEE = TAKER * 2             # 0.10%
SLIP = 0.5                  # half 1m range
SEED = 20260905
NREP = 2000
BLOCK_H = 72                # hours
CI_INFLATE_LEGACY = 1.21    # per task spec (k=1 => repo std inflate(1)=1.0; show both)

S = struct.Struct("<ifffff")  # minute_epoch, O, H, L, C, V

UTC = timezone.utc


def min_of(y, mo, d, h=0, mi=0):
    return int(datetime(y, mo, d, h, mi, tzinfo=UTC).timestamp() // 60)


DEV_START = min_of(2022, 1, 1)
DEV_END = min_of(2024, 7, 1)          # exclusive -> DEV = 2022-01-01..2024-06-30
SAMPLE_END = min_of(2026, 1, 1)       # exclusive -> data ends 2025-12-31


def load_sym(path):
    b = open(path, "rb").read()
    n = len(b) // 24
    a = np.frombuffer(b, dtype=np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"),
                                         ("l", "<f4"), ("c", "<f4"), ("v", "<f4")]), count=n)
    ts = a["ts"].astype(np.int64)
    order = np.argsort(ts, kind="stable")
    ts = ts[order]
    a = a[order]
    uniq, idx = np.unique(ts, return_index=True)
    return (uniq, a["o"][idx].astype(np.float64), a["h"][idx].astype(np.float64),
            a["l"][idx].astype(np.float64), a["c"][idx].astype(np.float64))


def rolling_max(vals, w):
    return pd.Series(vals).rolling(w, min_periods=w).max().values


def gen_fires(ts, O, H, L, C):
    """Return (fire_pos_dense, entry_prices) for fixed-threshold reversal-bounce."""
    base = ts[0]
    span = int(ts[-1] - base + 1)
    O_ = np.full(span, np.nan); H_ = np.full(span, np.nan)
    L_ = np.full(span, np.nan); C_ = np.full(span, np.nan)
    pos = (ts - base).astype(np.int64)
    O_[pos] = O; H_[pos] = H; L_[pos] = L; C_[pos] = C
    present = ~np.isnan(C_)

    m15 = rolling_max(H_, W15)
    m30 = rolling_max(H_, W30)
    with np.errstate(invalid="ignore", divide="ignore"):
        d15 = C_ / m15 - 1.0
        d30 = C_ / m30 - 1.0
    drop = np.minimum(d15, d30)

    # anchors: 15m-aligned, drop <= -DROP_THRESH, present at j, j-14, j-29
    gmin = (np.arange(span) + base) % 15
    p14 = np.zeros(span, dtype=bool)
    p14[14:] = present[:-14]
    p29 = np.zeros(span, dtype=bool)
    p29[29:] = present[:-29]
    is_anchor = (gmin == 14) & (drop <= -DROP_THRESH) & present & p14 & p29
    anchors = np.where(is_anchor)[0]

    fires = []
    i = 0
    last_fire = -1
    na = len(anchors)
    while i < na:
        j = anchors[i]
        if j <= last_fire:
            i += 1
            continue
        pr = O_[j - 14]
        lo = j + 1
        hi = anchors[i + 1] if i + 1 < na else span
        if hi <= lo:
            i += 1
            continue
        seg_c = C_[lo:hi]
        seg_p = present[lo:hi]
        cross = np.where(seg_p & (seg_c > pr))[0]
        if len(cross):
            fp = lo + int(cross[0])
            fires.append(fp)
            last_fire = fp
            while i < na and anchors[i] <= last_fire:
                i += 1
        else:
            i += 1
    fires = np.array(fires, dtype=np.int64)
    return base, span, O_, H_, L_, C_, present, fires, m15


def main():
    files = sorted(glob.glob(RAW + "/*.f32"))
    fout = open(OUT + "/signals.csv", "w")
    fout.write("sym,entry_ts,entry_utc,year,entry,exit,hold_min,delist,raw_ret,slip,funding,net_ret\n")

    import aerospike, cramjam
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    funding_cache = {}

    def load_funding(sym):
        if sym in funding_cache:
            return funding_cache[sym]
        try:
            (k, m, b) = cli.get(("test", "funding_data", sym))
            if not b or "f_data" not in b:
                funding_cache[sym] = None
                return None
            d = json.loads(bytes(cramjam.snappy.decompress_raw(b["f_data"])))
            arr = sorted((int(ts), float(rt)) for ts, rt in d.items())
            ft = np.array([x[0] for x in arr], dtype=np.int64)
            fr = np.array([x[1] for x in arr], dtype=np.float64)
            funding_cache[sym] = (ft, fr)
            return (ft, fr)
        except Exception:
            funding_cache[sym] = None
            return None

    t0 = time.time()
    nfire = 0
    nsym = 0
    # accumulate breadth: minute (int32) + drop15 (float32)
    breadth_min = []
    breadth_val = []

    for fi, path in enumerate(files):
        sym = os.path.basename(path)[:-4]
        ts, O, H, L, C = load_sym(path)
        if len(ts) < W30 + 1:
            continue
        nsym += 1
        base, span, O_, H_, L_, C_, present, fires, m15 = gen_fires(ts, O, H, L, C)

        # breadth: drop15 at 15m-aligned minutes (all, not just anchors)
        gmin = (np.arange(span) + base) % 15
        with np.errstate(invalid="ignore", divide="ignore"):
            d15_all = C_ / m15 - 1.0
        bm = (gmin == 14) & present & ~np.isnan(d15_all)
        if np.any(bm):
            minutes = (np.arange(span)[bm] + base).astype(np.int32)
            breadth_min.append(minutes)
            breadth_val.append(d15_all[bm].astype(np.float32))

        if len(fires) == 0:
            continue
        funding = load_funding(sym)
        fpos = fires
        entry = C_[fpos]
        # exit: last present minute in (f, f+HOLD]; if f+HOLD > span-1 -> edge-censored
        edge_cens = fpos + HOLD > span - 1
        for k in range(len(fpos)):
            f = fpos[k]
            if edge_cens[k]:
                continue
            ex_end = f + HOLD
            exslice = C_[f + 1: ex_end + 1]
            pres = np.where(~np.isnan(exslice))[0]
            if len(pres) == 0:
                continue
            exit_pos = f + 1 + int(pres[-1])
            exitp = C_[exit_pos]
            hold = exit_pos - f
            delist = 1 if hold < HOLD else 0
            raw = exitp / entry[k] - 1.0
            hi_, lo_ = H_[f], L_[f]
            slip = SLIP * (hi_ - lo_) / entry[k] if entry[k] > 0 else 0.0
            fund = 0.0
            if funding is not None:
                ft, fr = funding
                t_ms = (base + f) * 60000
                e_ms = (base + exit_pos) * 60000
                m = (ft > t_ms) & (ft <= e_ms)
                if np.any(m):
                    fund = float(fr[m].sum())
            net = raw - FEE - slip - fund
            ets = int(base + f)
            eu = datetime.utcfromtimestamp(ets * 60).strftime("%Y-%m-%d %H:%M")
            yr = int(eu[:4])
            fout.write("%s,%d,%s,%d,%.8g,%.8g,%d,%d,%.6f,%.6f,%.6f,%.6f\n" %
                       (sym, ets, eu, yr, entry[k], exitp, hold, delist, raw, slip, fund, net))
            nfire += 1
        if fi % 50 == 0:
            log.info("sym %d/%d %s fires(so far)=%d el=%.0fs", fi, len(files), sym, nfire, time.time() - t0)

    fout.close()
    cli.close()

    # ---- breadth rateDown15MAvg (bottom-100 mean of drop15) ----
    bmin = np.concatenate(breadth_min)
    bval = np.concatenate(breadth_val)
    log.info("breadth pairs=%d building rateDown15MAvg...", len(bmin))
    order = np.argsort(bmin, kind="stable")
    bmin = bmin[order]; bval = bval[order]
    umin, start, cnt = np.unique(bmin, return_index=True, return_counts=True)
    rd15 = np.empty(len(umin), dtype=np.float64)
    for gi in range(len(umin)):
        s = start[gi]; c = cnt[gi]
        seg = bval[s:s + c]
        k = 100
        if k > int(c * 4 / 5):
            k = int(c * 4 / 5)
        if k <= 0:
            rd15[gi] = 0.0
            continue
        part = np.partition(seg, k - 1)[:k]
        rd15[gi] = part.mean()
    # map minute -> rateDown15MAvg (dict too big; keep arrays + searchsorted)
    np.save(OUT + "/rd15_min.npy", umin)
    np.save(OUT + "/rd15_val.npy", rd15)
    log.info("rateDown15MAvg computed: %d points, range [%.4f, %.4f]",
             len(umin), rd15.min(), rd15.max())
    open(OUT + "/SIGNALS_DONE", "w").write("fires=%d syms=%d\n" % (nfire, nsym))


if __name__ == "__main__":
    main()
