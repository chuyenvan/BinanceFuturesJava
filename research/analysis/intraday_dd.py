#!/usr/bin/env python3
"""INTRADAY_DD — maxDD/UW do tren chuoi equity MOC PHUT (mark-to-market) vs chuoi NGAY.

Thuc thi DUNG docs/PREREG_INTRADAY_DD.md (chot TRUOC khi do).

THUAN PYTHON OFFLINE tren Oracle. KHONG Java/sim, KHONG claude-run, KHONG push, DEV only
(moi moc <= 2025-12-30, khong doc 2026).

  BUOC 1  doc artifact (sim.out: Update 1 lan/ngay 07:00 GMT+7) + printDone.csv (leg).
  BUOC 2  TAI TAO equity moc phut tu du lieu 1m: equity = 35,000 + realized(m) + unP(m).
  BUOC 3  cong nghiem thu V1..V4 (BAT BUOC PASS truoc khi bao cao maxDD/UW).
  BUOC 4  maxDD/UW: NGAY vs PHUT (toan ky + theo nam); top-10 episode; attribution coin.
  BUOC 5  cua so 2025-10-09..13 (doi chieu RESULT_BLACKSWAN_2510).

Usage: python3 intraday_dd.py [--workers 4] [--out /home/ubuntu/intradaydd] [--report ...]
"""
import argparse
import gzip
import json
import os
import re
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jbin  # noqa: E402

TICKER = "/home/ubuntu/kaggle_data_hpo"
CAP0 = 35000.0
TZ_SHIFT_H = 7                       # printDone gio GMT+7; ticker key = ms UTC
DAY0 = "20210701"                    # sim bat dau 20210701 07:00 GMT+7 = 20210701 00:00Z
DAY1 = "20251230"                    # Update cuoi cung = 20251230 07:00 GMT+7
RUNS = {
    "T170": "/home/ubuntu/kaggle_sim/out/t170-x1-2021",
    "KEEPLEG0": "/home/ubuntu/java/devrun/FG_KEEPLEG0",
    "T100": "/home/ubuntu/kaggle_sim/out/hn-t100",
    "GD92": "/home/ubuntu/kaggle_sim/out/hn-g92",
}
# tuple 1m THAT (da kiem bang du lieu): (startTime, HIGH, LOW, CLOSE, OPEN, V)
F_HIGH, F_LOW, F_CLOSE, F_OPEN = 1, 2, 3, 4

RX_DAILY = re.compile(r"Update (\d{8}) \d\d:\d\d => b:\s*(-?\d+).*?\tunP:\s*(-?\d+)"
                      r"\tunPMin:\s*(-?\d+)")
RX_ANYUPD = re.compile(r"Update (\d{8}) (\d\d:\d\d)")

W0 = pd.Timestamp("2025-10-09")
W1 = pd.Timestamp("2025-10-13")
REPORT = []


def say(s=""):
    REPORT.append(str(s))
    print(s, flush=True)


# ------------------------------------------------------------------ artifact
def load_legs(base):
    d = pd.read_csv(os.path.join(base, "storage", "printDone.csv"), on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    for c in ("pnl", "entry", "quantity", "margin", "profit"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["pnl", "entry", "quantity"]).copy()
    d["sym"] = d["sym"].str.strip() + "USDT"
    d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=TZ_SHIFT_H)
    d["te"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=TZ_SHIFT_H)
    d = d.dropna(subset=["ts", "te"]).sort_values("ts").reset_index(drop=True)
    # vi tri phut tren truc chung
    d["m0"] = ((d.ts - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1)).astype(np.int64)
    d["m1"] = ((d.te - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1)).astype(np.int64)
    return d


def load_daily(base):
    rows, uptimes = [], set()
    with open(os.path.join(base, "logs", "sim.out"), errors="ignore") as fh:
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


def attr_at(legsd, i, mt, cache):
    t = mt[i]
    day = t.strftime("%Y%m%d")
    mi = int((t - pd.Timestamp(day)) // pd.Timedelta(minutes=1))
    if day not in cache:
        p = os.path.join(TICKER, "ticker_%s.bin.gz" % day)
        px = {}
        if os.path.exists(p):
            t0 = int(pd.Timestamp(day).value // 10 ** 6)
            with gzip.open(p, "rb") as f:
                for k, v in jbin.iter_minutes(f.read()):
                    if k < t0 + mi * 60000:
                        continue
                    if k > t0 + mi * 60000:
                        break
                    px = {s: tup[F_CLOSE] for s, tup in v.items()}
        cache[day] = px
    px = cache[day]
    sub = legsd[(legsd.ts <= t) & (legsd.te > t)]
    per = {}
    for sym, q, e in zip(sub.sym, sub.quantity, sub.entry):
        v = px.get(sym)
        if v is None:
            continue
        per[sym] = per.get(sym, 0.0) + q * (v - e)
    return t, sorted(per.items(), key=lambda kv: kv[1])


# ------------------------------------------------------------------ metrics
def eq_dd(s):
    return s / np.maximum.accumulate(s) - 1.0


def maxdd(s):
    return float(eq_dd(s).min() * 100.0)


def longest_under(s):
    """So diem lien tuc dai nhat nam duoi dinh chay (khuon c3_rates: uw & cumsum)."""
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
    yy = np.asarray(t.year if hasattr(t, "year") else pd.DatetimeIndex(t).year)
    for y in sorted(set(yy.tolist())):
        k = yy == y
        out[int(y)] = (maxdd(s[k]), longest_under(s[k]))
    return out


def episodes(s):
    """Tra list (i_start, i_trough, i_end, peak_val, trough_val, depth)."""
    peak = np.maximum.accumulate(s)
    uw = s < peak
    ch = np.diff(uw.astype(np.int8))
    starts = list(np.where(ch == 1)[0] + 1)
    ends = list(np.where(ch == -1)[0] + 1)
    if uw[0]:
        starts = [0] + starts
    if uw[-1]:
        ends = ends + [len(s)]
    out = []
    for a, b in zip(starts, ends):
        j = a + int(np.argmin(s[a:b]))
        i = int(np.argmax(s[:a + 1])) if a > 0 else (0 if s[0] == peak[0] else 0)
        # dinh chay: lan cuoi peak dat duoc <= a
        pk = peak[a - 1] if a > 0 else s[0]
        i = int(np.max(np.where(s[:a + 1] >= pk - 1e-9)[0])) if a > 0 else 0
        out.append((i, j, b, float(s[i]), float(s[j]), float((s[i] - s[j]) / s[i] * 100.0)))
    return out


# ------------------------------------------------------------------ recon worker
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
            # carry-forward (ticker null => lastPrice khong doi), bfill cho nen dau thieu
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
            res[day][rn] = (
                CAP0 + realized + (accC - accE),   # P=close
                CAP0 + realized + (accL - accE),   # P=low (can duoi, cadence bar.low cua sim)
                realized, accE,
            )
    return res


# ------------------------------------------------------------------ main
def main():
    global DAY0, DAY1
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="/home/ubuntu/intradaydd")
    ap.add_argument("--report", default="/home/ubuntu/intradaydd/report_intraday_dd.txt")
    ap.add_argument("--chunk", type=int, default=41)
    ap.add_argument("--day0", default=DAY0)
    ap.add_argument("--day1", default=DAY1)
    a = ap.parse_args()
    DAY0, DAY1 = a.day0, a.day1
    os.makedirs(a.out, exist_ok=True)
    t_start = time.time()

    legs = {k: load_legs(v) for k, v in RUNS.items()}
    daily = {}
    uptimes_all = set()
    say("=" * 78)
    say("BUOC 1 — ARTIFACT: nguon equity moc phut?")
    say("%-9s %6s %7s %10s %12s %10s %10s" %
        ("run", "n_leg", "n_upd", "HH:MM duy nhat", "b_final", "unP_fin", "unPMin_fin"))
    for k, v in RUNS.items():
        e, ut = load_daily(v)
        daily[k] = e
        uptimes_all |= set(ut)
        say("%-9s %6d %7d %14s %12d %10d %10d" %
            (k, len(legs[k]), len(e), ",".join(sorted(ut)), e.b.iloc[-1], e.unP.iloc[-1],
             e.unPMin.iloc[-1]))
    say("=> Update xuat hien CHI 1 moc/ngay (07:00 GMT+7 = 00:00Z) => artifact KHONG co chuoi "
        "equity moc phut.")

    # ---- V1
    say("")
    say("BUOC 3 — CONG NGHIEM THU (phai PASS truoc khi bao cao)")
    v1 = {}
    for k, v in RUNS.items():
        e, _ = load_daily(v)
        diff = float(CAP0 + legs[k].pnl.sum() - e.b.iloc[-1])
        v1[k] = diff
        say("V1 %-9s CAP0+sum(pnl)=%.2f vs b_final=%d  diff=%.2f  %s" %
            (k, CAP0 + legs[k].pnl.sum(), e.b.iloc[-1], diff,
             "PASS" if abs(diff) <= 1 else "FAIL"))

    # ---- recon
    days = [pd.Timestamp(d).strftime("%Y%m%d")
            for d in pd.date_range(DAY0, DAY1, freq="D")]
    need = {}
    for rn, d in legs.items():
        for day in days:
            t = pd.Timestamp(day)
            sub = d[(d.ts < t + pd.Timedelta(days=1)) & (d.te > t)]
            if len(sub):
                need.setdefault(day, set()).update(sub.sym.unique())
    nneed = sum(len(v) for v in need.values())
    say("")
    say("BUOC 2 — TAI TAO MTM moc phut: %d ngay, %d symbol-ngay can gia (union 4 run)"
        % (len(days), nneed))
    cache = os.path.join(a.out, "series.npz")
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=False)
        eqC, eqL, realz = {}, {}, {}
        for rn in RUNS:
            eqC[rn] = z["c_" + rn]
            eqL[rn] = z["l_" + rn]
            realz[rn] = z["r_" + rn]
        print("  [cache] dung lai %s" % cache, flush=True)
    else:
        chunks = [days[i:i + a.chunk] for i in range(0, len(days), a.chunk)]
        with Pool(a.workers, initializer=_init, initargs=(legs, need)) as pool:
            parts = []
            t0 = time.time()
            for i, res in enumerate(pool.imap_unordered(_work, chunks)):
                parts.append(res)
                print("  chunk %d/%d  %.0fs" % (i + 1, len(chunks), time.time() - t0), flush=True)
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
        np.savez_compressed(cache, **{"c_" + k: v for k, v in eqC.items()},
                            **{"l_" + k: v for k, v in eqL.items()},
                            **{"r_" + k: v for k, v in realz.items()})
    mt = pd.date_range(DAY0, periods=len(days) * 1440, freq="min")
    ny = mt.year.to_numpy()

    # ---- V2/V4: equity tai moc in == b+unP in ra
    say("")
    for k in RUNS:
        e = daily[k]
        idx = np.array([((t - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1))
                        for t in e.index], dtype=np.int64)
        keep = (idx >= 0) & (idx < len(eqC[k]))
        idx = idx[keep]
        got = eqC[k][idx]
        err = np.abs(got - e.equity.to_numpy()[keep])
        rel = (err / e.equity.to_numpy()[keep]).max() * 100
        say("V2/V4 %-9s equity_mtm_recon(00:00Z) vs daily(b+unP) in ra: "
            "max|err|=%.2f  mean|err|=%.3f  n=%d  %s" %
            (k, err.max(), err.mean(), len(err), "PASS" if err.max() <= 2 else "FAIL"))
        say("V2-rel %-9s max|err|/equity = %.4f%% (nguong AMENDMENT-1: <=0.05%%)  so ngay |err|>2: %d  %s" %
            (k, rel, int((err > 2).sum()), "PASS" if rel <= 0.05 else "FAIL"))
        # V5: maxDD tren chuoi phut LAY MAU theo ngay (moc 0) phai == maxDD chuoi NGAY artifact
        dd_art = maxdd(e.equity.to_numpy()[keep])
        dd_smp = maxdd(eqC[k][idx])
        say("V5  %-9s maxDD(chuoi NGAY artifact)=%.2f%% vs maxDD(minute series lay mau moc 0)=%.2f%% "
            "|lech|=%.3f pp  %s" % (k, dd_art, dd_smp, abs(dd_art - dd_smp),
                                    "PASS" if abs(dd_art - dd_smp) <= 0.1 else "FAIL"))
        # V3: min chay cua unP_low == unPMin in ra
        unpl = eqL[k] - CAP0 - realz[k]
        mn = min(0.0, float(unpl.min()))
        pr = int(e.unPMin.iloc[-1])
        r = abs(mn - pr) / max(1.0, abs(pr)) * 100
        say("V3  %-9s min_chay(unP_low)=%.1f vs unPMin_in_ra=%d  lech=%.3f%%  %s" %
            (k, mn, pr, r, "PASS" if r <= 1.0 else "FAIL"))

    # ---- stats
    say("")
    say("BUOC 4 — maxDD/UW: NGAY vs PHUT")
    say("%-9s | %-24s | %-24s | %8s | %8s" %
        ("run", "NGAY maxDD/ UWinday", "PHUT maxDD/ UWday", "d_pp", "d_UW"))
    out = {}
    for k in RUNS:
        e = daily[k]
        sd = e.equity.to_numpy()
        TD = e.index
        SM = eqC[k]
        TM = mt
        dd_d, uw_d = maxdd(sd), longest_under(sd)
        dd_m, uw_m = maxdd(SM), longest_under(SM)
        out[k] = dict(dd_daily=dd_d, uw_daily=uw_d, dd_min=dd_m, uw_min=uw_m,
                      uw_min_days=uw_m / 1440.0,
                      py_daily=per_year(TD, sd), py_min=per_year(TM, SM))
        say("%-9s | %8.2f%% / %5d ngay  | %8.2f%% / %9.2f ngay | %+8.2f | %+9.2f" %
            (k, dd_d, uw_d, dd_m, uw_m / 1440.0, dd_m - dd_d, uw_m / 1440.0 - uw_d))
    say("")
    for k in RUNS:
        o = out[k]
        say("--- %s theo nam (maxDD%% / UW-ngay)" % k)
        say("  %-6s %-22s %-22s %8s" % ("nam", "NGAY", "PHUT", "d_pp"))
        for y in sorted(o["py_daily"]):
            a1, b1 = o["py_daily"][y]
            a2, b2 = o["py_min"].get(y, (float("nan"), float("nan")))
            say("  %-6d %8.2f%% /%6d ngay   %8.2f%% /%7.2f ngay %+8.2f" %
                (y, a1, b1, a2, b2 / 1440.0, a2 - a1))

    # ---- top-10 episode
    say("")
    say("--- [do ben] bien the P=bar.low (can duoi intrabar, cung cadence unPMin cua sim)")
    say("%-9s %10s %10s %10s %10s %10s" % ("run", "maxDD toan ky", "UW ngay", "nam xau", "maxDD nam", "UW nam"))
    for k in RUNS:
        SM = eqL[k]
        d = maxdd(SM)
        u = longest_under(SM) / 1440.0
        py = per_year(mt, SM)
        wy = min(py, key=lambda y: py[y][0])
        out[k]["dd_low"] = d
        out[k]["uw_low_days"] = u
        out[k]["py_low"] = py
        say("%-9s %9.2f%% %10.2f %10d %9.2f%% %10.2f" %
            (k, d, u, wy, py[wy][0], py[wy][1] / 1440.0))

    say("")
    say("BUOC 4b — TOP-10 cu giam INTRADAY sau nhat (toan ky)")
    pxcache = {}
    for k in RUNS:
        ep = episodes(eqC[k])
        ep.sort(key=lambda x: -x[5])
        say("--- %s" % k)
        say("  %2s %-16s %-16s %7s %8s %8s %s" %
            ("#", "dinh", "day", "do sau%", "gio", "USDT", "mat dinh truoc"))
        rows = []
        for n, (i, j, b, pk, tr, dep) in enumerate(ep[:10], 1):
            say("  %2d %-16s %-16s %7.2f %8.1f %8.0f %s" %
                (n, str(TM[i])[:16], str(TM[j])[:16], dep, (j - i) / 60.0, pk - tr,
                 str(TM[i])[:10]))
            at, per = attr_at(legs[k], j, TM, pxcache)
            worst = per[0] if per else ("-", 0.0)
            tot = sum(v for _, v in per)
            say("     attribution @day: %d leg/coin dang mo; unP tong %+.0f | xau nhat %s %+.0f "
                "(%.0f%% cua unP, %.0f%% cua do sau); top3: %s" %
                (len(per), tot, worst[0], worst[1],
                 abs(worst[1]) / max(1e-9, abs(tot)) * 100, abs(worst[1]) / max(1e-9, pk - tr) * 100,
                 ", ".join("%s %+.0f" % (s, v) for s, v in per[:3])))
            rows.append(dict(i=int(i), j=int(j), t_peak=str(TM[i]), t_trough=str(TM[j]),
                             depth=dep, hours=(j - i) / 60.0, usd=pk - tr,
                             n_coins=len(per), unP_total=tot,
                             worst_coin=(worst[0] if per else None),
                             worst_unP=(worst[1] if per else None)))
        out[k]["episodes"] = rows

    # ---- cua so 2025-10-09..13
    say("")
    say("BUOC 5 — cua so 2025-10-09 .. 2025-10-13")
    i0 = int((W0 - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1))
    i1 = int((W1 + pd.Timedelta(days=1) - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1))
    say("%-9s %10s %10s %10s %10s %10s" %
        ("run", "eq(10-09 00Z)", "eq_min(W)", "drop%", "eq_min(low)", "drop%low"))
    for k in RUNS:
        SM = eqC[k][i0:i1]
        SL = eqL[k][i0:i1]
        anchor = eqC[k][i0]
        pk = np.maximum.accumulate(np.concatenate([[anchor], SM]))[1:]
        pkl = np.maximum.accumulate(np.concatenate([[anchor], SL]))[1:]
        dmin = float((SM / pk - 1).min() * 100)
        dminl = float((SL / pkl - 1).min() * 100)
        jj = int(np.argmin(SM))
        out[k]["w2510"] = dict(anchor=float(anchor), eqmin=float(SM.min()), drop=dmin,
                               eqmin_low=float(SL.min()), drop_low=dminl,
                               t_min=str(mt[i0 + jj]))
        say("%-9s %10.0f %10.0f %9.2f%% %10.0f %9.2f%%  (day %s)" %
            (k, anchor, SM.min(), dmin, SL.min(), dminl, str(mt[i0 + jj])[:16]))

    # ---- (a)(b)(c)(d)
    say("")
    say("BUOC 6 — TRA LOI (a)(b)(c)(d)")
    say("(a) NGAY che mat (pp) — toan ky: " + " · ".join(
        "%s %+.2f" % (k, out[k]["dd_min"] - out[k]["dd_daily"]) for k in RUNS))
    say("    theo nam (pp) — gap LON NHAT: " + " · ".join(
        "%s %+.2f (%d)" % (k, min(out[k]["py_min"][y][0] - out[k]["py_daily"][y][0]
                                 for y in out[k]["py_daily"]),
                            min(out[k]["py_daily"],
                                key=lambda y: out[k]["py_min"][y][0] - out[k]["py_daily"][y][0]))
        for k in RUNS))
    say("(b) vuot maxDD 40%% intraday? " + " · ".join(
        "%s: toan ky %.2f%% %s | nam xau nhat %.2f%% %s" %
        (k, out[k]["dd_min"], "VUOT" if out[k]["dd_min"] < -40 else "khong",
         min(v[0] for v in out[k]["py_min"].values()),
         "VUOT" if min(v[0] for v in out[k]["py_min"].values()) < -40 else "khong")
        for k in RUNS))
    say("(c) vuot UW 250 ngay intraday? " + " · ".join(
        "%s: toan ky %.1f %s | nam xau nhat %.1f %s" %
        (k, out[k]["uw_min_days"], "VUOT" if out[k]["uw_min_days"] > 250 else "khong",
         max(v[1] for v in out[k]["py_min"].values()) / 1440.0,
         "VUOT" if max(v[1] for v in out[k]["py_min"].values()) / 1440.0 > 250 else "khong")
        for k in RUNS))
    flip = [k for k in RUNS
            if (out[k]["dd_min"] < -40) != (out[k]["dd_daily"] < -40)
            or (out[k]["uw_min_days"] > 250) != (out[k]["uw_daily"] > 250)]
    say("(d) doi trang thai PASS/FAIL cua nen nao? %s" %
        ("CO: " + ",".join(flip) if flip else "KHONG (khong nen nao doi trang thai)"))
    say("(b2) bien the bar.low (can duoi) vuot maxDD 40%%? " + " · ".join(
        "%s: toan ky %.2f%% %s | nam xau nhat %.2f%% %s" %
        (k, out[k]["dd_low"], "VUOT" if out[k]["dd_low"] < -40 else "khong",
         min(v[0] for v in out[k]["py_low"].values()),
         "VUOT" if min(v[0] for v in out[k]["py_low"].values()) < -40 else "khong")
        for k in RUNS))
    say("(c2) bien the bar.low vuot UW 250? " + " · ".join(
        "%s: toan ky %.1f %s | nam xau nhat %.1f %s" %
        (k, out[k]["uw_low_days"], "VUOT" if out[k]["uw_low_days"] > 250 else "khong",
         max(v[1] for v in out[k]["py_low"].values()) / 1440.0,
         "VUOT" if max(v[1] for v in out[k]["py_low"].values()) / 1440.0 > 250 else "khong")
        for k in RUNS))
    say("(e) cua so W 2025-10-09..13: max drop NGAY trong W vs max drop PHUT trong W")
    for k in RUNS:
        e = daily[k]
        wd = e.equity[(e.index >= W0) & (e.index <= W1)].to_numpy()
        peak = np.maximum.accumulate(np.concatenate([[eqC[k][i0]], wd]))[1:]
        dday = float((wd / peak - 1).min() * 100)
        say("    %-9s NGAY %+.2f%%  |  PHUT %+.2f%% (low: %+.2f%%)  |  chenh %+.2f pp" %
            (k, dday, out[k]["w2510"]["drop"], out[k]["w2510"]["drop_low"],
             out[k]["w2510"]["drop"] - dday))

    res = dict(runs=RUNS, cap0=CAP0, v1=v1, out={k: {kk: vv for kk, vv in out[k].items()} for k in RUNS},
               n_days=len(days), tz_shift_h=TZ_SHIFT_H, ticker=TICKER,
               secs=time.time() - t_start)
    with open(os.path.join(a.out, "intraday_dd.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    with open(a.report, "w") as f:
        f.write("\n".join(REPORT) + "\n")
    say("")
    say("[done] %.0fs  report=%s json=%s" % (time.time() - t_start, a.report,
                                             os.path.join(a.out, "intraday_dd.json")))


if __name__ == "__main__":
    main()
