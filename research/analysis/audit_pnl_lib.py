#!/usr/bin/env python3
"""audit_pnl_lib.py — hạ tầng DÙNG CHUNG cho audit độc lập `PREREG_AUDIT_PNL.md`.

KHÔNG phát minh gì: đọc bins thô bằng `jbin.iter_minutes` (y hệt `mr_label_build.load_chunk`) và gọi
THẲNG `exitfit/exit_engine.simulate` với luật `P0`, `pred=None`, entry `E=close(t)`, 1 leg — đúng đường
của `research/pipeline/mr_label_build.sim_one`. Chỉ khác: cửa sổ bars dựng theo từng cặp `(t,sym)`.

Thuần Python, chỉ ĐỌC. Không train, không Java, không sim hệ thống, không push.
"""
import gzip
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "research", "analysis"))
sys.path.insert(0, os.path.join(REPO, "research", "exitfit"))
sys.path.insert(0, os.path.join(REPO, "research", "pipeline"))

os.environ.setdefault("EXITFIT_PIN", "/home/ubuntu/java/exchange_info_pin.json")
import jbin                                    # noqa: E402
import exit_engine as E                        # noqa: E402

DAY = 86400000
HOUR = 3600000
TICKER_DIR = "/home/ubuntu/java/simulator/kaggle_data_hpo/daily"
LABEL = "/tmp/mrout/mrout/label_b_pnl.parquet"
S1_PARQUET = "/home/ubuntu/mr_kaggle/ds_mr_inputs/pred_s1a2x1.parquet"
MAP_CSV = "/home/ubuntu/claudedata/symbol_map_20260806.csv"
OUT = "/tmp/auditpnl"
FEE_RT = 0.008                                  # mô hình phí hiện hành (nhãn (b) đã dùng)
KMAX = 32
CHUNK_DAYS = 90
TS_MAX_MS = 1758992400000                       # = kernel mr-labelb-cpu (2025-10-01 00:00 GMT+7)
CUTS = ["20220401", "20220701", "20221001", "20230101", "20230401", "20230701", "20231001",
        "20240101", "20240401", "20240701", "20241001", "20250101", "20250401", "20250701",
        "20251001"]
POL = E.make_p0()

SEED_A = 20260925      # V1a: 200 cặp nhãn
SEED_B1 = 20260926     # V1b: 200 cặp BỊ BỎ
SEED_B2 = 20260926     # V1b: 200 cặp ĐƯỢC GIỮ
SEED_C = 20260927      # V3: 200 tick


def log(*a):
    print(("[auditpnl] " + (a[0] % a[1:] if len(a) > 1 else a[0])), flush=True)


# ───────────────────────────── đọc bins thô ─────────────────────────────
def day_of(ms):
    return int(ms) // DAY


def day_file(day):
    import datetime as dt
    s = dt.datetime.utcfromtimestamp(day * 86400).strftime("%Y%m%d")
    for ext in (".bin", ".bin.gz"):
        p = os.path.join(TICKER_DIR, "ticker_%s%s" % (s, ext))
        if os.path.exists(p):
            return p
    return None


def read_day(args):
    """Đọc 1 ngày bin; trả {sym: (ts int64[n], ohlc float32[n,4])} cho `need` (chỉ coin cần)."""
    day, need = args
    p = day_file(day)
    if p is None:
        return day, None
    if p.endswith(".gz"):
        with gzip.open(p, "rb") as g:
            b = g.read()
    else:
        with open(p, "rb") as f:
            b = f.read()
    acc = {}
    for k, v in jbin.iter_minutes(b):
        for sym, t in v.items():
            if sym not in need:
                continue
            a = acc.get(sym)
            if a is None:
                a = acc[sym] = ([], [], [], [], [])
            _st, hi, lo, cl, op, _vol = t          # thứ tự đã kiểm (PREREG_EXIT_FIT §2.1)
            a[0].append(k)
            a[1].append(op)
            a[2].append(hi)
            a[3].append(lo)
            a[4].append(cl)
    out = {}
    for sym, a in acc.items():
        if a[0]:
            out[sym] = (np.asarray(a[0], dtype=np.int64),
                        np.asarray(a[1:], dtype=np.float32).T)      # (n,4) = o,h,l,c
    return day, out


def load_days(days, need_by_day, workers=4):
    """days: list[int]; need_by_day: dict day -> set(sym). Trả dict day -> {sym: (ts,ohlc)}.
    Multiprocessing; mỗi worker chỉ giữ coin cần cho ngày nó đọc."""
    tasks = []
    for d in sorted(days):
        nd = need_by_day.get(d)
        if not nd:
            continue
        tasks.append((d, set(nd)))
    res = {}
    if not tasks:
        return res
    if workers <= 1:                                 # KHONG mo Pool khi da o trong worker (daemon)
        for i, t in enumerate(tasks):
            d, out = read_day(t)
            res[d] = out
            if i % 25 == 0:
                log("  đọc ngày %d/%d", i + 1, len(tasks))
        return res
    with Pool(workers) as pool:
        for i, (d, out) in enumerate(pool.imap_unordered(read_day, tasks, chunksize=1)):
            res[d] = out
            if i % 25 == 0:
                log("  đọc ngày %d/%d", i + 1, len(tasks))
    return res


def assemble(bars_by_day, sym, days):
    """Ghép bars của sym qua các ngày liên tiếp (chỉ ngày CÓ file) -> (ts, ohlc) hoặc None."""
    tl, ol, missing = [], [], []
    for d in days:
        dd = bars_by_day.get(d)
        if dd is None:
            missing.append(d)
            continue
        b = dd.get(sym)
        if b is None:
            missing.append(d)
            continue
        tl.append(b[0])
        ol.append(b[1])
    if not tl:
        return None, missing
    ts = np.concatenate(tl)
    o = np.concatenate(ol)
    idx = np.argsort(ts, kind="stable")
    return (ts[idx], o[idx]), missing


# ───────────────────────────── replay engine ─────────────────────────────
def replay(sym, ts_arr, ohlc, t0, cid=0):
    """Đúng đường `mr_label_build.sim_one` (P0, pred=None, E=close(t))."""
    cl = {"cid": cid, "sym": sym, "end": int(t0),
          "legs": [{"ts": int(t0), "entry": None, "qty": 1.0, "pred": None, "pnl": 0.0,
                    "funding": 0.0, "status": "", "tp": 0.0, "level": 0}]}
    i0 = int(np.searchsorted(ts_arr, t0))
    if i0 >= len(ts_arr) or int(ts_arr[i0]) != int(t0):
        return None
    cl["legs"][0]["entry"] = float(ohlc[i0, 3])
    res = E.simulate(cl, {cid: (ts_arr, ohlc)}, POL)
    if not res.get("ok"):
        return None
    entry = float(res["entry0"])
    tp = float(res["price_tp"])
    gross = tp / entry - 1.0
    return dict(sym=sym, E=entry, tp=tp, gross=gross, net=gross - FEE_RT,
                status=res["status"], reason=res["reason"], exit_ts=int(res["exit_ts"]),
                hold_min=(int(res["exit_ts"]) - int(t0)) // 60000,
                n_arm=int(res["rows"][0]["n_arm"]))


# ───────────────────────────── nguồn: nhãn + universe S1 ─────────────────────────────
def load_label():
    return pd.read_parquet(LABEL)


def ms(datestr):
    d = pd.Timestamp("%s-%s-%s" % (datestr[:4], datestr[4:6], datestr[6:8]), tz="UTC")
    return int(d.value // 10**6) - 7 * HOUR


def candidates_frame():
    """TÁI LẬP tập ứng viên của kernel: top-32 theo S1 (score thấp = tốt), ts < TS_MAX_MS."""
    d = pd.read_parquet(S1_PARQUET, columns=["ts", "sym", "score"])
    n0 = len(d)
    d = d[d.ts < TS_MAX_MS]
    d = d.sort_values(["ts", "score"], ascending=[True, True], kind="stable")
    d = d.groupby("ts", sort=True).head(KMAX).reset_index(drop=True)
    d["rank"] = d.groupby("ts", sort=True).cumcount()
    d = d.rename(columns={"sym": "symId"})      # `sym` của parquet S1 = symId (như mr_label_build)
    log("ứng viên S1: %d dòng -> %d dòng top-%d | n_tick=%d", n0, len(d), KMAX, d.ts.nunique())
    return d


def dropped_days(cand):
    """TÁI LẬP các cặp bị BỎ của kernel (chia khối 90 ngày, giữ `day <= b1-8`).
    BỎ theo TỪNG INTERVAL (cùng một ngày có thể vừa bị bỏ ở interval này vừa được giữ ở interval
    kề — dải `edge` chồng nhau) ⇒ trả MASK theo dòng, KHÔNG phải set ngày toàn cục.
    Trả (mask bool [len(cand)], số cặp bị bỏ, info theo interval)."""
    cand = cand.copy()
    cand["day"] = cand.ts.to_numpy() // DAY
    CUTS_MS = [ms(c) for c in CUTS]
    edges = [int(cand.ts.min())] + [c - 72 * HOUR for c in CUTS_MS]
    mask = np.zeros(len(cand), dtype=bool)
    tsv = cand.ts.to_numpy()
    dayv = cand.day.to_numpy()
    info = []
    for ii in range(len(edges) - 1):
        lo, hi = edges[ii], edges[ii + 1]
        inI = (tsv >= lo) & (tsv < hi)
        if not inI.any():
            continue
        daymin, daymax = int(dayv[inI].min()), int(dayv[inI].max())
        days_needed = list(range(daymin, daymax + 9))
        blocks = []
        d0 = days_needed[0]
        for d in days_needed:
            if d - d0 >= CHUNK_DAYS:
                blocks.append((d0, d - 1)); d0 = d
        blocks.append((d0, days_needed[-1]))
        dd = set()
        for bi, (b0, b1) in enumerate(blocks):
            if bi < len(blocks) - 1:                     # khối cuối: 8 ngày cuối ngoài dải tick
                dd |= set(range(b1 - 7, b1 + 1))
        m = inI & np.isin(dayv, list(dd))
        mask |= m
        info.append(dict(interval="i%02d_%s" % (ii, CUTS[ii]), n_blocks=len(blocks),
                         n_dropped_days=len(dd), n_dropped_pairs=int(m.sum())))
    return mask, int(mask.sum()), info
