#!/usr/bin/env python3
"""S3_INTRADAY — maxDD/UW tren chuoi equity MTM MOC PHUT (ban rut gon cua
`research/analysis/intraday_dd.py`, DUNG lai nguyen cong thuc tai tao muc 2 cua no).

Tai sao phai chay trong kernel Kaggle: Oracle KHONG con du lieu 1m
(`/home/ubuntu/kaggle_data_hpo` rong). Thuat toan GIONG intraday_dd.py:

  realized(m) = sum pnl cua leg da dong truoc m
  unP(m)      = sum qty*(P_sym(m) - entry) cua leg dang mo
  equity_mtm(m) = 35.000 + realized(m) + unP(m)   (P = close; bien the P = low)

Cong nghiem thu (phai PASS truoc khi bao cao maxDD/UW): V1 (realized vs b_final),
V2/V2-rel (equity_mtm(00:00Z) vs `b+unP` in ra), V3 (min-chay unP_low vs `unPMin`),
V5 (maxDD(chuoi ngay) vs maxDD(chuoi phut lay mau moc 0)).

Usage:
  python3 s3_intraday.py --run TAG=DIR [--run ...] --ticker DIR --workers 4 --json OUT.json
"""
import argparse
import gzip
import json
import logging
import os
import re
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import jbin  # noqa: E402  (copy cua research/analysis/jbin.py)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stdout)
LOG = logging.getLogger("s3_intraday")

CAP0 = 35000.0
TZ_SHIFT_H = 7
DAY0 = "20210701"
DAY1 = "20251230"
TICKER = "/home/ubuntu/kaggle_data_hpo"
RUNS = {}
F_HIGH, F_LOW, F_CLOSE, F_OPEN = 1, 2, 3, 4

RX_DAILY = re.compile(r"Update (\d{8}) \d\d:\d\d => b:\s*(-?\d+).*?\tunP:\s*(-?\d+)"
                      r"\tunPMin:\s*(-?\d+)")
RX_ANYUPD = re.compile(r"Update (\d{8}) (\d\d:\d\d)")


def _pdone(base):
    for nm in ("printDone.csv", "printdone.csv"):
        p = os.path.join(base, "storage", nm)
        if os.path.exists(p):
            return p
    raise SystemExit("S3_INTRADAY_FAIL: khong thay printDone.csv trong %s/storage" % base)


def load_legs(base):
    d = pd.read_csv(_pdone(base), on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    for c in ("pnl", "entry", "quantity", "margin", "profit"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["pnl", "entry", "quantity"]).copy()
    d["sym"] = d["sym"].str.strip() + "USDT"
    d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=TZ_SHIFT_H)
    d["te"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=TZ_SHIFT_H)
    d = d.dropna(subset=["ts", "te"]).sort_values("ts").reset_index(drop=True)
    d["m0"] = ((d.ts - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1)).astype(np.int64)
    d["m1"] = ((d.te - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1)).astype(np.int64)
    return d


def load_daily(base):
    p = os.path.join(base, "logs", "sim.out")
    if not os.path.exists(p) and os.path.exists(p + ".gz"):
        with gzip.open(p + ".gz", "rt", errors="ignore") as f, open(p, "w") as o:
            o.write(f.read())
    rows, uptimes = [], set()
    with open(p, errors="ignore") as fh:
        for line in fh:
            mu = RX_ANYUPD.search(line)
            if mu:
                uptimes.add(mu.group(2))
            m = RX_DAILY.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))))
    e = pd.DataFrame(rows, columns=["d", "b", "unP", "unPMin"]).drop_duplicates("d", keep="last")
    e["t"] = pd.to_datetime(e.d, format="%Y%m%d")
    e = e.set_index("t")
    e["equity"] = e.b + e.unP
    return e, sorted(uptimes)


def maxdd(s):
    return float((s / np.maximum.accumulate(s) - 1.0).min() * 100.0)


def longest_under(s):
    peak = np.maximum.accumulate(s)
    uw = s < peak
    best = cur = 0
    for v in uw:
        cur = cur + 1 if v else 0
        if cur > best:
            best = cur
    return int(best)


def per_year(t, s):
    out = {}
    yy = np.asarray(pd.DatetimeIndex(t).year)
    for y in sorted(set(yy.tolist())):
        k = yy == y
        out[int(y)] = dict(maxDD=maxdd(s[k]), uw=int(longest_under(s[k])),
                           uw_days=longest_under(s[k]) / 1440.0)
    return out


_G = {}


def _init(legs_by_run, need_by_day):
    _G["legs"] = legs_by_run
    _G["need"] = need_by_day


def _work(days):
    res = {}
    for day in days:
        p = os.path.join(TICKER, "ticker_%s.bin.gz" % day)
        syms = sorted(_G["need"].get(day, ())) if os.path.exists(p) else []
        C = L = None
        srow = {s: i for i, s in enumerate(syms)}
        if syms:
            C = np.full((len(syms), 1440), np.nan, np.float32)
            L = np.full((len(syms), 1440), np.nan, np.float32)
            t0 = int(pd.Timestamp(day).value // 10 ** 6)
            with gzip.open(p, "rb") as f:
                for k, v in jbin.iter_minutes(f.read()):
                    if k < t0 or k >= t0 + 1440 * 60000:
                        continue
                    mi = (k - t0) // 60000
                    for s, tup in v.items():
                        j = srow.get(s)
                        if j is not None:
                            C[j, mi] = tup[F_CLOSE]
                            L[j, mi] = tup[F_LOW]
            for M in (C, L):
                idx = np.where(np.isnan(M).any(axis=1))[0]
                if len(idx):
                    M[idx] = pd.DataFrame(M[idx].T).ffill().bfill().to_numpy().T
        base = int((pd.Timestamp(day) - pd.Timestamp(DAY0)) // pd.Timedelta(days=1)) * 1440
        res[day] = {}
        for rn, d in _G["legs"].items():
            accE = np.zeros(1440)
            accC = np.zeros(1440)
            accL = np.zeros(1440)
            step = np.zeros(1441)
            op = d[(d.m0 < base + 1440) & (d.m1 > base)]
            for sym, q, e, i0, i1 in zip(op.sym, op.quantity, op.entry,
                                         np.maximum(op.m0 - base, 0),
                                         np.minimum(op.m1 - base, 1440)):
                if i1 <= i0 or sym not in srow:
                    continue
                j = srow[sym]
                accC[i0:i1] += q * C[j, i0:i1]
                accL[i0:i1] += q * L[j, i0:i1]
                accE[i0:i1] += q * e
            cl = d[(d.m1 >= base) & (d.m1 < base + 1440)]
            for pnl, i1 in zip(cl.pnl, cl.m1 - base):
                step[int(i1)] += pnl
            realized = (d.pnl[d.m1 < base].sum()) + np.cumsum(step[:1440])
            res[day][rn] = (CAP0 + realized + (accC - accE), CAP0 + realized + (accL - accE),
                            realized, accE)
    return res


def main():
    global TICKER, DAY0, DAY1
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, metavar="TAG=DIR")
    ap.add_argument("--ticker", default=TICKER)
    ap.add_argument("--day0", default=DAY0)
    ap.add_argument("--day1", default=DAY1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=41)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--json", required=True)
    a = ap.parse_args()
    TICKER, DAY0, DAY1 = a.ticker, a.day0, a.day1
    for s in a.run:
        t, d = s.split("=", 1)
        RUNS[t] = d
    t_start = time.time()
    legs = {k: load_legs(v) for k, v in RUNS.items()}
    daily = {}
    uptimes_all = set()
    for k, v in RUNS.items():
        e, ut = load_daily(v)
        daily[k] = e
        uptimes_all |= set(ut)
        LOG.info("daily %s: n_leg=%d n_upd=%d i o HH:MM=%s b_final=%d unP_final=%d unPMin_final=%d",
                 k, len(legs[k]), len(e), ",".join(sorted(ut)), e.b.iloc[-1], e.unP.iloc[-1],
                 e.unPMin.iloc[-1])
    checks = {}
    for k in RUNS:
        e = daily[k]
        checks["V1_" + k] = dict(diff=float(CAP0 + legs[k].pnl.sum() - e.b.iloc[-1]))
    days = [pd.Timestamp(d).strftime("%Y%m%d") for d in pd.date_range(DAY0, DAY1, freq="D")]
    need = {}
    for rn, d in legs.items():
        for day in days:
            t = pd.Timestamp(day)
            sub = d[(d.ts < t + pd.Timedelta(days=1)) & (d.te > t)]
            if len(sub):
                need.setdefault(day, set()).update(sub.sym.unique())
    LOG.info("recon: %d ngay, %d symbol-ngay", len(days), sum(len(v) for v in need.values()))
    if a.cache and os.path.exists(a.cache):
        z = np.load(a.cache, allow_pickle=False)
        eqC = {rn: z["c_" + rn] for rn in RUNS}
        eqL = {rn: z["l_" + rn] for rn in RUNS}
        realz = {rn: z["r_" + rn] for rn in RUNS}
        LOG.info("[cache] dung lai %s", a.cache)
    else:
        chunks = [days[i:i + a.chunk] for i in range(0, len(days), a.chunk)]
        parts = []
        with Pool(a.workers, initializer=_init, initargs=(legs, need)) as pool:
            t0 = time.time()
            for i, res in enumerate(pool.imap_unordered(_work, chunks)):
                parts.append(res)
                LOG.info("chunk %d/%d %.0fs", i + 1, len(chunks), time.time() - t0)
        eqC = {rn: np.empty(len(days) * 1440) for rn in RUNS}
        eqL = {rn: np.empty(len(days) * 1440) for rn in RUNS}
        realz = {rn: np.empty(len(days) * 1440) for rn in RUNS}
        didx = {d: i for i, d in enumerate(days)}
        for res in parts:
            for day, per_run in res.items():
                b = didx[day] * 1440
                for rn, (ec, el, rz, _ae) in per_run.items():
                    eqC[rn][b:b + 1440] = ec
                    eqL[rn][b:b + 1440] = el
                    realz[rn][b:b + 1440] = rz
        if a.cache:
            np.savez_compressed(a.cache, **{"c_" + k: v for k, v in eqC.items()},
                                **{"l_" + k: v for k, v in eqL.items()},
                                **{"r_" + k: v for k, v in realz.items()})
    mt = pd.date_range(DAY0, periods=len(days) * 1440, freq="min")
    out = {}
    for k in RUNS:
        e = daily[k]
        idx = np.array([((t - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1))
                        for t in e.index], dtype=np.int64)
        keep = (idx >= 0) & (idx < len(eqC[k]))
        idx = idx[keep]
        err = np.abs(eqC[k][idx] - e.equity.to_numpy()[keep])
        rel = float((err / e.equity.to_numpy()[keep]).max() * 100)
        dd_art = maxdd(e.equity.to_numpy()[keep])
        dd_smp = maxdd(eqC[k][idx])
        unpl = eqL[k] - CAP0 - realz[k]
        mn = min(0.0, float(unpl.min()))
        pr = int(e.unPMin.iloc[-1])
        vr3 = abs(mn - pr) / max(1.0, abs(pr)) * 100
        checks["V2_" + k] = dict(max_err=float(err.max()), mean_err=float(err.mean()), n=int(len(err)))
        checks["V2rel_" + k] = dict(rel_pct=rel)
        checks["V3_" + k] = dict(min_unP_low=float(mn), unPMin_printed=pr, rel_pct=float(vr3))
        checks["V5_" + k] = dict(dd_daily=float(dd_art), dd_minute_sampled=float(dd_smp),
                                 d_pp=float(abs(dd_art - dd_smp)))
        sd = e.equity.to_numpy()
        out[k] = dict(
            n_leg=int(len(legs[k])), n_days=int(len(e)),
            equity_final=float(sd[-1]), b_final=int(e.b.iloc[-1]),
            daily=dict(maxDD=maxdd(sd), uw=int(longest_under(sd))),
            minute=dict(maxDD=maxdd(eqC[k]), uw=int(longest_under(eqC[k])),
                        uw_days=longest_under(eqC[k]) / 1440.0,
                        maxDD_low=maxdd(eqL[k]), uw_low_days=longest_under(eqL[k]) / 1440.0),
            py_min=per_year(mt, eqC[k]), py_low=per_year(mt, eqL[k]),
            py_daily=per_year(e.index, sd))
    res = dict(runs=list(RUNS), day0=DAY0, day1=DAY1, cap0=CAP0, checks=checks, stats=out,
               secs=round(time.time() - t_start, 1))
    with open(a.json, "w") as f:
        json.dump(res, f, indent=1)
    ok = all(abs(checks["V1_" + k]["diff"]) <= 1 for k in RUNS) and \
        all(checks["V2rel_" + k]["rel_pct"] <= 0.05 for k in RUNS) and \
        all(checks["V3_" + k]["rel_pct"] <= 1.0 for k in RUNS) and \
        all(checks["V5_" + k]["d_pp"] <= 0.1 for k in RUNS)
    LOG.info("S3_INTRADAY_%s runs=%s secs=%.0f", "PASS" if ok else "FAIL", list(RUNS), res["secs"])
    for k in RUNS:
        LOG.info("  %-4s PHUT maxDD=%.2f%% UW=%.2f ngay | NGAY maxDD=%.2f%% UW=%d | low maxDD=%.2f%%",
                 k, out[k]["minute"]["maxDD"], out[k]["minute"]["uw_days"],
                 out[k]["daily"]["maxDD"], out[k]["daily"]["uw"], out[k]["minute"]["maxDD_low"])
    if not ok:
        sys.exit(3)


if __name__ == "__main__":
    main()
