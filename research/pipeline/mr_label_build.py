#!/usr/bin/env python3
"""mr_label_build.py — SINH NHAN (b): **PnL THẬT theo luật thoát** (PREREG_MONEY_RANKER §4).

Không phát minh luật thoát: **gọi thẳng** `research/exitfit/exit_engine.simulate` (harness đã PARITY
PASS với `devrun/X1_GS_T170_2021`, xem `docs/result/RESULT_EXIT_FIT.md` §1).

Định nghĩa (chốt trước, KHÔNG sửa sau khi đọc số):
  PnL(t, sym) = engine(P0, **pred = None** ⇒ nhánh WEAK `cap = 0,03`) với entry `E = close(t)`,
  1 leg, giá 1m `ticker_*.bin(.gz)`, time-stop 168h, `gross = tp/E − 1`, `net = gross − 0,008`.

Ứng viên (chốt trước §4.2): top-K theo điểm S1 (`pred_s1a2x1.parquet`, score THẤP = TỐT),
`KMAX = 32`; `K = 8` là **tập con** của `K = 32` (mô phỏng KHÔNG phụ thuộc K ⇒ chỉ chạy MỘT lần).

CỔNG CHI PHÍ (§4.3): in thời gian **khoảng fold ĐẦU**; nếu > 2h ⇒ ABORT (fallback về nhãn (a)).

Chạy (Kaggle CPU): python3 mr_label_build.py
Env: S1_PARQUET TICKER_DIR EXITFIT_PIN MAP_CSV OUT_DIR [CHUNK_DAYS] [KMAX] [TS_MAX_MS] [MAX_INTERVAL_SEC]
"""
import glob
import gzip
import json
import os
import resource
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "research", "analysis"))
sys.path.insert(0, os.path.join(REPO, "research", "exitfit"))
import jbin                                    # noqa: E402
import exit_engine as E                        # noqa: E402

DAY = 86400000
HOUR = 3600000
H168 = 168 * HOUR
FEE_RT = 0.008

S1_PARQUET = os.environ["S1_PARQUET"]
TICKER_DIR = os.environ["TICKER_DIR"]
MAP_CSV = os.environ["MAP_CSV"]
OUT_DIR = os.environ["OUT_DIR"]
KMAX = int(os.environ.get("KMAX", "32"))
CHUNK_DAYS = int(os.environ.get("CHUNK_DAYS", "90"))
TS_MAX_MS = int(os.environ.get("TS_MAX_MS", "0")) or None
MAX_INTERVAL_SEC = float(os.environ.get("MAX_INTERVAL_SEC", "7200"))   # 2h (§4.3)
CUTS = [x for x in os.environ.get(
    "CUTS_OVERRIDE",
    "20220401,20220701,20221001,20230101,20230401,20230701,20231001,20240101,20240401,20240701,"
    "20241001,20250101,20250401,20250701,20251001").split(",") if x]
TZ = 7 * HOUR
T0 = time.time()


def log(*a):
    m = a[0] % a[1:] if len(a) > 1 else a[0]
    print("[%7.1fs] %s" % (time.time() - T0, m), flush=True)


def peak_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


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


def read_bytes(p):
    if p.endswith(".gz"):
        with gzip.open(p, "rb") as g:
            return g.read()
    with open(p, "rb") as f:
        return f.read()


def ms(datestr):
    d = pd.Timestamp("%s-%s-%s" % (datestr[:4], datestr[4:6], datestr[6:8]), tz="UTC")
    return int(d.value // 10**6) - TZ


# ─────────────────────────── ứng viên (top-K theo S1) ───────────────────────────
def load_candidates():
    d = pd.read_parquet(S1_PARQUET, columns=["ts", "sym", "score"])
    n0 = len(d)
    if TS_MAX_MS:
        d = d[d.ts < TS_MAX_MS]
    # sort theo (ts, score TANG DAN) => K dòng đầu mỗi tick = top-K (score THẤP = TỐT)
    d = d.sort_values(["ts", "score"], ascending=[True, True], kind="stable")
    d = d.groupby("ts", sort=True).head(KMAX).reset_index(drop=True)
    d["rank"] = d.groupby("ts", sort=True).cumcount()      # 0 = tot nhat (score thap nhat)
    smap = pd.read_csv(MAP_CSV)[["symId", "symbol"]]
    d = d.rename(columns={"sym": "symId"})
    d = d.merge(smap, on="symId", how="left")
    miss = int(d.symbol.isna().sum())
    d = d.dropna(subset=["symbol"])
    log("S1: %d dong -> sau loc ts<%s va top-%d: %d dong | n_tick=%d | sym khong map=%d",
        n0, TS_MAX_MS, KMAX, len(d), d.ts.nunique(), miss)
    return d


# ─────────────────────────── parse 1m theo chunk ngày ───────────────────────────
def load_chunk(days, need_syms):
    """days: danh sach day-index; tra dict sym -> (ts int64[n], ohlc float32[n,4])."""
    acc = {}
    nmin = 0
    for dd in days:
        p = day_file(dd)
        if p is None:
            continue
        for k, v in jbin.iter_minutes(read_bytes(p)):
            nmin += 1
            for sym in need_syms:
                t = v.get(sym)
                if t is None:
                    continue
                st, hi, lo, cl, op, _vol = t          # verified order (PREREG_EXIT_FIT §2.1)
                a = acc.get(sym)
                if a is None:
                    a = acc[sym] = ([], [], [], [], [])
                a[0].append(k)
                a[1].append(op)
                a[2].append(hi)
                a[3].append(lo)
                a[4].append(cl)
    out = {}
    for sym, a in acc.items():
        if a[0]:
            out[sym] = (np.asarray(a[0], dtype=np.int64),
                        np.asarray(a[1:], dtype=np.float32).T)     # (n,4) = o,h,l,c
    return out, nmin


POL = E.make_p0()


def sim_one(sym, ts_arr, ohlc, t0, cid):
    """Gọi THẲNG engine. Trả None nếu không có nến entry."""
    cl = {"cid": cid, "sym": sym, "end": int(t0),
          "legs": [{"ts": int(t0), "entry": None, "qty": 1.0, "pred": None, "pnl": 0.0,
                    "funding": 0.0, "status": "", "tp": 0.0, "level": 0}]}
    i0 = int(np.searchsorted(ts_arr, t0))
    if i0 >= len(ts_arr) or int(ts_arr[i0]) != int(t0):
        return None
    cl["legs"][0]["entry"] = float(ohlc[i0, 3])          # E = close(t)
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


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    log("EXITFIT_OUT=%s | PIN=%s | tick sizes=%d | engine P0=%s",
        E.OUT, E.PIN, len(E.TICKS), POL.desc)
    cand = load_candidates()
    cand["day"] = cand.ts.to_numpy() // DAY
    CUTS_MS = [ms(c) for c in CUTS]
    # khoảng "fold" = phần DỮ LIỆU MỚI mà mỗi fold thêm vào (tr_cut = c − 72h)
    edges = [int(cand.ts.min())] + [c - 72 * HOUR for c in CUTS_MS]
    log("khoang fold: %d | ticks %d..%d (%s..%s)", len(edges) - 1, cand.ts.min(), cand.ts.max(),
        pd.to_datetime(cand.ts.min(), unit="ms"), pd.to_datetime(cand.ts.max(), unit="ms"))

    rows = []
    cost = {"chunks": [], "interval_sec": {}, "n_sim": 0, "n_noentry": 0,
            "n_openend": 0, "n_days_parsed": 0, "n_days_missing": 0}
    aborted = None
    for ii in range(len(edges) - 1):
        lo_ms, hi_ms = edges[ii], edges[ii + 1]
        sub = cand[(cand.ts >= lo_ms) & (cand.ts < hi_ms)]
        tag = "i%02d_%s" % (ii, CUTS[ii])
        if not len(sub):
            log("khoang %s: 0 tick -> bo qua", tag)
            continue
        t_i = time.time()
        days_needed = sorted(set(range(int(sub.day.min()), int(sub.day.max()) + 9)))
        need_syms = set(sub.symbol.unique())
        # chunk theo CHUNK_DAYS (nhưng tách theo ngày có tick) để chặn RAM
        blocks = []
        d0 = days_needed[0]
        for d in days_needed:
            if d - d0 >= CHUNK_DAYS:
                blocks.append((d0, d - 1)); d0 = d
        blocks.append((d0, days_needed[-1]))
        for (b0, b1) in blocks:
            days = [d for d in days_needed if b0 <= d <= b1]
            # chỉ parse ngày có thể cần (bỏ ngày không tồn tại)
            t_p = time.time()
            bars, nmin = load_chunk(days, need_syms)
            nfound = sum(1 for d in days if day_file(d) is not None)
            cost["n_days_parsed"] += nfound
            cost["n_days_missing"] += len(days) - nfound
            tk = sub[(sub.day >= b0) & (sub.day <= b1 - 8)]
            if not len(tk):
                del bars
                continue
            for ts, sid, sym, rk in zip(tk.ts.to_numpy(), tk.symId.to_numpy(),
                                        tk.symbol.to_numpy(), tk["rank"].to_numpy()):
                b = bars.get(sym)
                if b is None:
                    cost["n_noentry"] += 1
                    continue
                r = sim_one(sym, b[0], b[1], int(ts), 0)
                if r is None:
                    cost["n_noentry"] += 1
                    continue
                r["ts"] = int(ts); r["rank"] = int(rk); r["symId"] = int(sid)
                rows.append(r)
                cost["n_sim"] += 1
                if r["status"] == "OPEN_AT_END":
                    cost["n_openend"] += 1
            cost["chunks"].append(dict(interval=tag, b0=b0, b1=b1, days=len(days), bars=len(bars),
                                       nmin=nmin, sec=round(time.time() - t_p, 1),
                                       peak_mb=round(peak_mb(), 1)))
            log("  chunk %s [%d..%d] days=%d bars=%d nmin=%d %.1fs peak=%.0fMB rows=%d",
                tag, b0, b1, len(days), len(bars), nmin, time.time() - t_p, peak_mb(), len(rows))
            del bars
        dt = time.time() - t_i
        cost["interval_sec"][tag] = round(dt, 1)
        log("KHOANG %s: n_tick=%d  %.1f phut  rows=%d  peak=%.0fMB", tag, sub.ts.nunique(),
            dt / 60, len(rows), peak_mb())
        if not cost.get("first_checked"):
            cost["first_checked"] = True
            log("COST_FOLD_FIRST[%s] = %.1f phut (cong %.0f phut) | nguong 120 phut",
                tag, dt / 60, MAX_INTERVAL_SEC / 60)
            if dt > MAX_INTERVAL_SEC:
                aborted = "fold dau %s = %.1f phut > %.0f phut (cong §4.3) => DUNG" % (
                    tag, dt / 60, MAX_INTERVAL_SEC / 60)
                log("ABORT: %s", aborted)
                break
    R = pd.DataFrame(rows)
    cost["n_rows"] = int(len(R))
    cost["aborted"] = aborted
    cost["total_sec"] = round(time.time() - T0, 1)
    cost["peak_mb"] = round(peak_mb(), 1)
    cost["tick_sizes_loaded"] = len(E.TICKS)
    if len(R):
        R = R[["ts", "symId", "sym", "rank", "E", "tp", "gross", "net", "status", "reason",
               "exit_ts", "hold_min", "n_arm"]]
        R.to_parquet(os.path.join(OUT_DIR, "label_b_pnl.parquet"), index=False)
        for K in (8, 32):
            S = R[R["rank"] < K]
            LK = pd.DataFrame({"ts": S.ts.to_numpy(np.int64), "symId": S.symId.to_numpy(np.int32),
                               "y": S.net.to_numpy(np.float32)})
            LK.to_parquet(os.path.join(OUT_DIR, "label_b_K%d.parquet" % K), index=False)
            log("K=%d: %d dong (nhan train y=net) | hold_min TB=%.0f | gross TB=%.5f | "
                "net TB=%.5f | OPEN_AT_END=%d | reason top=%s", K, len(S), S.hold_min.mean(),
                S.gross.mean(), S.net.mean(), int((S.status == "OPEN_AT_END").sum()),
                S.reason.value_counts().head(4).to_dict())
    json.dump(cost, open(os.path.join(OUT_DIR, "cost_report.json"), "w"), indent=1)
    log("DONE rows=%d sim=%d noentry=%d openend=%d peak=%.0fMB aborted=%s",
        len(R), cost["n_sim"], cost["n_noentry"], cost["n_openend"], peak_mb(), aborted)
    print("MR_LABEL_DONE " + json.dumps({"n_rows": len(R), "aborted": aborted,
                                          "total_min": round(cost["total_sec"] / 60, 1),
                                          "peak_mb": cost["peak_mb"]}), flush=True)


if __name__ == "__main__":
    main()
