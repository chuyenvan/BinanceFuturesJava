#!/usr/bin/env python3
"""TAIL_LEVER — don bay dung: chan `gross exposure` (tran G) / trap ALT cat duoc bao nhieu duoi rui ro.

Thuc thi DUNG docs/PREREG_TAIL_LEVER.md (chot TRUOC khi do).

THUAN PYTHON OFFLINE tren Oracle. KHONG Java/sim, KHONG claude-run, KHONG push, DEV only
(moi moc <= 2025-12-30, khong doc 2026).

  STAGE data    doc 1m 1 luot -> (a) dong gop qty*P theo TUNG leg, (b) ret1h cross-section p10 + BTC.
  STAGE analyze W1..W4 (cong nghiem thu) + A (phan ra rui ro he thong) + B (tran G) + C (trap ALT).

Usage: python3 tail_lever.py [--stage all|data|analyze] [--workers 4] [--out /home/ubuntu/taillever]
"""
import argparse
import gzip
import heapq
import json
import os
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
TZ_SHIFT_H = 7
DAY0, DAY1 = "20210701", "20251230"
T = 1644 * 1440                       # 2,367,360 moc phut
YEARS = (pd.Timestamp("2025-12-30") - pd.Timestamp("2021-07-01")).days / 365.25
RUNS = {
    "T170": "/home/ubuntu/kaggle_sim/out/t170-x1-2021",
    "KEEPLEG0": "/home/ubuntu/java/devrun/FG_KEEPLEG0",
    "T100": "/home/ubuntu/kaggle_sim/out/hn-t100",
    "GD92": "/home/ubuntu/kaggle_sim/out/hn-g92",
}
BASELINE_NPZ = "/home/ubuntu/intradaydd/series.npz"   # cache cua RESULT_INTRADAY_DD (tai dung)
# gia tri chot truoc (PREREG_TAIL_LEVER §1.1 / §3)
G_LIST = [20, 30, 40, 50]
TRAP_P10 = 0.20      # L1
TRAP_BTC = 0.01      # L2
TRAP_ALT = -0.10     # L2
LOOKBACK = 15
WK0, WK1 = "2025-10-09", "2025-10-13"
I_W0 = int((pd.Timestamp(WK0) - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1))
I_W1 = int((pd.Timestamp(WK1) + pd.Timedelta(days=1) - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1))
MT = pd.date_range(DAY0, periods=T, freq="min")
F_HIGH, F_LOW, F_CLOSE, F_OPEN = 1, 2, 3, 4
REP = []


def say(s=""):
    REP.append(str(s))
    print(s, flush=True)


# ------------------------------------------------------------------ legs/layout
def load_layout(base):
    d = pd.read_csv(os.path.join(base, "storage", "printDone.csv"), on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    for c in ("pnl", "entry", "quantity", "margin", "profit"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["pnl", "entry", "quantity", "margin"]).copy()
    d["sym"] = d["sym"].str.strip() + "USDT"
    ts = pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=TZ_SHIFT_H)
    te = pd.to_datetime(d["end"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=TZ_SHIFT_H)
    d = d.assign(ts=ts.values, te=te.values).dropna(subset=["ts", "te"])
    d = d.sort_values("ts", kind="stable").reset_index(drop=True)
    m0 = ((d.ts - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
    m1 = ((d.te - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
    m0c = np.clip(m0, 0, T)
    m1c = np.clip(m1, 0, T)
    dur = np.maximum(m1c - m0c, 0)
    off = np.concatenate([[0], np.cumsum(dur)[:-1]]).astype(np.int64)
    return dict(sym=d.sym.to_numpy(), qty=d.quantity.to_numpy(np.float64),
                entry=d.entry.to_numpy(np.float64), margin=d.margin.to_numpy(np.float64),
                pnl=d.pnl.to_numpy(np.float64), m0=m0, m1=m1, m0c=m0c, m1c=m1c,
                dur=dur, off=off, qe=d.quantity.to_numpy(np.float64) * d.entry.to_numpy(np.float64),
                ts=d.ts.to_numpy(), nmin=int(off[-1] + dur[-1]) if len(dur) else 0, n=len(d))


# ------------------------------------------------------------------ data pass
_G = {}


def _init(L):
    _G["L"] = L


def _read_day(day):
    """-> (srow, C, L) hoac None.

    srow = UNION symbol cua CA NGAY (khong chi nen dau tien): symbol vang mat vai nen van co gia
    (ffill/bfill) — neu lay theo nen dau se MAT dong gop cua leg tai ngay do.
    C/L: (nsym,1440) close/low da ffill+bfill theo phut (giong _work cua intraday_dd).
    """
    p = os.path.join(TICKER, "ticker_%s.bin.gz" % day)
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rb") as f:
        b = f.read()
    mins = []
    for _k, v in jbin.iter_minutes(b):
        if len(mins) >= 1440:
            break
        mins.append({s: (t[F_CLOSE], t[F_LOW]) for s, t in v.items()})
    if not mins:
        return None
    allsyms = set()
    for m in mins:
        allsyms |= set(m.keys())
    syms = sorted(allsyms)
    srow = {s: i for i, s in enumerate(syms)}
    C = np.full((len(syms), 1440), np.nan, np.float32)
    L = np.full((len(syms), 1440), np.nan, np.float32)
    for mi, m in enumerate(mins):
        for s, (c, l) in m.items():
            j = srow[s]
            C[j, mi] = c
            L[j, mi] = l
    C = pd.DataFrame(C.T).ffill().bfill().to_numpy(np.float32).T
    L = pd.DataFrame(L.T).ffill().bfill().to_numpy(np.float32).T
    return srow, C, L


def _work(dic_days):
    """Chunk ngay lien tuc -> (di0, contributions, p10/btc/nsym series cuc bo)."""
    L = _G["L"]
    runs = list(RUNS)
    out_leg = {rn: {} for rn in runs}
    p10 = np.full(len(dic_days) * 1440, np.nan, np.float32)
    btc = np.full(len(dic_days) * 1440, np.nan, np.float32)
    nsym = np.zeros(len(dic_days) * 1440, np.float32)
    tail = None                                     # dict sym -> 60 close truoc do
    active = {rn: [] for rn in runs}
    ptr = {rn: 0 for rn in runs}
    di0 = dic_days[0][0]
    for li, (di, day) in enumerate(dic_days):
        base = di * 1440
        if tail is None and li == 0:
            prev = (pd.Timestamp(day) - pd.Timedelta(days=1)).strftime("%Y%m%d")
            r = _read_day(prev)
            if r is not None:
                srow_p, _Cp, _Lp = r
                tail = {s: _Cp[i, -60:].copy() for s, i in srow_p.items()}
        got = _read_day(day)
        if got is None:
            continue
        srow, C, Lm = got
        # ---- p10 cross-section ret1h + BTC ret1h
        R = np.full((C.shape[0], 1440), np.nan, np.float32)
        with np.errstate(all="ignore"):
            R[:, 60:] = C[:, 60:] / C[:, :-60] - 1.0
            if tail is not None:
                for s, i in srow.items():
                    t0 = tail.get(s)
                    if t0 is not None:
                        R[i, :60] = C[i, :60] / t0 - 1.0
            p10[li * 1440:(li + 1) * 1440] = np.nanpercentile(R, 10, axis=0)
        nsym[li * 1440:(li + 1) * 1440] = np.isfinite(R).sum(axis=0)
        jb = srow.get("BTCUSDT")
        if jb is not None:
            btc[li * 1440:(li + 1) * 1440] = R[jb, :]
        tail = {s: C[i, -60:].copy() for s, i in srow.items()}
        # ---- dong gop tung leg
        for rn in runs:
            d = L[rn]
            n = d["n"]
            a_l = active[rn]
            while ptr[rn] < n and d["m0c"][ptr[rn]] < base + 1440:
                a_l.append(ptr[rn])
                ptr[rn] += 1
            active[rn] = [i for i in a_l if d["m1c"][i] > base]
            if not active[rn]:
                continue
            ids, a_loc, b_loc, c_flat, l_flat, v_flat = [], [], [], [], [], []
            for i in active[rn]:
                a = int(max(d["m0c"][i] - base, 0))
                b = int(min(d["m1c"][i] - base, 1440))
                if b <= a:
                    continue
                row = srow.get(d["sym"][i])
                if row is None:
                    continue
                cv = C[row, a:b]
                lv = Lm[row, a:b]
                vv = np.isfinite(cv)
                if not vv.any():
                    continue
                ids.append(i)
                a_loc.append(a)
                b_loc.append(b)
                c_flat.append(np.where(vv, cv, 0.0))
                l_flat.append(np.where(vv, lv, 0.0))
                v_flat.append(vv.astype(np.uint8))
            if not ids:
                continue
            offs = np.concatenate([[0], np.cumsum([len(x) for x in c_flat])]).astype(np.int32)
            out_leg[rn][di] = (np.array(ids, np.int32), offs, np.array(a_loc, np.int32),
                               np.array(b_loc, np.int32),
                               np.concatenate(c_flat).astype(np.float32),
                               np.concatenate(l_flat).astype(np.float32),
                               np.concatenate(v_flat).astype(np.uint8))
    return di0, out_leg, p10, btc, nsym


def stage_data(a):
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()
    L = {rn: load_layout(v) for rn, v in RUNS.items()}
    for rn in RUNS:
        say("[legs] %-9s n=%4d tong-phut-leg=%9d" % (rn, L[rn]["n"], L[rn]["nmin"]))
    days = [d.strftime("%Y%m%d") for d in pd.date_range(DAY0, DAY1, freq="D")]
    chunks = [list(enumerate(days))[i:i + 20] for i in range(0, len(days), 20)]
    QC = {rn: np.zeros(L[rn]["nmin"], np.float32) for rn in RUNS}
    QL = {rn: np.zeros(L[rn]["nmin"], np.float32) for rn in RUNS}
    VV = {rn: np.zeros(L[rn]["nmin"], np.uint8) for rn in RUNS}
    p10 = np.full(len(days) * 1440, np.nan, np.float32)
    btc = np.full(len(days) * 1440, np.nan, np.float32)
    nsym = np.zeros(len(days) * 1440, np.float32)
    ndone = 0
    with Pool(a.workers, initializer=_init, initargs=(L,)) as pool:
        for k, (di0, out_leg, p, b, ns) in enumerate(pool.imap_unordered(_work, chunks)):
            p10[di0 * 1440:di0 * 1440 + len(p)] = p
            btc[di0 * 1440:di0 * 1440 + len(b)] = b
            nsym[di0 * 1440:di0 * 1440 + len(ns)] = ns
            for rn in RUNS:
                d = L[rn]
                for di, (ids, offs, a_loc, b_loc, c_flat, l_flat, v_flat) in out_leg[rn].items():
                    base = di * 1440
                    for j, i in enumerate(ids):
                        g = d["off"][i] + (base + a_loc[j] - d["m0c"][i])
                        s0 = offs[j]
                        s1 = offs[j + 1]
                        QC[rn][g:g + (s1 - s0)] = c_flat[s0:s1]
                        QL[rn][g:g + (s1 - s0)] = l_flat[s0:s1]
                        VV[rn][g:g + (s1 - s0)] = v_flat[s0:s1]
            ndone += len(p) // 1440
            if (k + 1) % 5 == 0:
                say("  [data] chunk %d/%d  ngay=%d  %.0fs" % (k + 1, len(chunks), ndone, time.time() - t0))
    np.savez_compressed(os.path.join(a.out, "trap.npz"), p10=p10, btc=btc, nsym=nsym)
    for rn in RUNS:
        np.savez(os.path.join(a.out, "contrib_%s.npz" % rn), pc=QC[rn], pl=QL[rn], vv=VV[rn])
    say("[data] done %.0fs -> %s" % (time.time() - t0, a.out))


# ------------------------------------------------------------------ metrics
def maxdd(s):
    return float((s / np.maximum.accumulate(s) - 1.0).min() * 100.0)


def uw_min(s):
    peak = np.maximum.accumulate(s)
    u = s < peak
    best = cur = 0
    for v in u:
        cur = cur + 1 if v else 0
        if cur > best:
            best = cur
    return int(best)


def win_drop(eq):
    S = eq[I_W0:I_W1]
    peak = np.maximum.accumulate(np.concatenate([[eq[I_W0]], S]))[1:]
    return float((S / peak - 1.0).min() * 100.0)


def run_drop(eq, i, j):
    S = eq[i:j + 1]
    peak = np.maximum.accumulate(S)
    return float((S / peak - 1.0).min() * 100.0)


def episodes(s):
    peak = np.maximum.accumulate(s)
    u = s < peak
    ch = np.diff(u.astype(np.int8))
    starts = list(np.where(ch == 1)[0] + 1)
    ends = list(np.where(ch == -1)[0] + 1)
    if u[0]:
        starts = [0] + starts
    if u[-1]:
        ends = ends + [len(s)]
    out = []
    for a, b in zip(starts, ends):
        j = a + int(np.argmin(s[a:b]))
        pk = peak[a - 1] if a > 0 else s[0]
        i = int(np.max(np.where(s[:a + 1] >= pk - 1e-9)[0])) if a > 0 else 0
        out.append((i, j, float(s[i]), float(s[j]), float((s[i] - s[j]) / s[i] * 100.0)))
    return out


# ------------------------------------------------------------------ analyze
class A(object):
    pass


def legs_open_at(d, m):
    hi = int(np.searchsorted(d["m0c"], m, side="right"))
    idx = np.arange(hi)
    return idx[d["m1c"][:hi] > m]


def per_sym_unp(d, PC, VV, m):
    """unP tung coin tai moc m (chi leg dang mo + co gia hop le). margin = qty*entry (1x)."""
    out = {}
    for i in legs_open_at(d, m):
        k = d["off"][i] + (m - d["m0c"][i])
        if VV[k]:
            s = d["sym"][i]
            out[s] = out.get(s, 0.0) + float(PC[k]) * d["qty"][i] - d["qe"][i]
    return out


def build_eq(d, QC, QL, VV, accept, low=False):
    Q = QL if low else QC
    accC = np.zeros(T, np.float64)
    accE = np.zeros(T, np.float64)
    step = np.zeros(T + 1, np.float64)
    for i in np.where(accept)[0]:
        a = d["off"][i]
        n = d["dur"][i]
        if n <= 0:
            continue
        src = slice(a, a + n)          # chi so trong mang concat theo leg
        dst = slice(d["m0c"][i], d["m1c"][i])   # chi so tren truc phut chung
        vv = VV[src]
        accC[dst] += np.where(vv, Q[src], 0.0) * d["qty"][i]
        accE[dst] += d["qe"][i] * vv
        step[d["m1c"][i]] += d["pnl"][i]
    return CAP0 + np.cumsum(step[:T]) + (accC - accE)


def greedy_cap(d, G, eqref):
    mg = d["margin"]
    n = d["n"]
    order = np.argsort(d["m0c"], kind="stable")
    acc = np.ones(n, bool)
    h = []
    gross = 0.0
    for i in order:
        t = d["m0c"][i]
        while h and h[0][0] <= t:
            gross -= heapq.heappop(h)[1]
        if d["dur"][i] <= 0:
            continue
        if gross + mg[i] > G / 100.0 * eqref[min(t, T - 1)]:
            acc[i] = False
        else:
            heapq.heappush(h, (d["m1c"][i], mg[i]))
            gross += mg[i]
    return acc


def metrics(d, eq, acc):
    return dict(maxdd=maxdd(eq), dropw=win_drop(eq), pnl=float(d["pnl"][acc].sum()),
                pnl_blocked=float(d["pnl"][~acc].sum()),
                eqf=float(eq[-1]), cagr=float(((eq[-1] / CAP0) ** (1.0 / YEARS) - 1) * 100),
                n=int(acc.sum()), nblock=int((~acc).sum()), uw=uw_min(eq) / 1440.0)


def exposure_stats(d, eqref):
    """Ty so (Σmargin mo)/equity TAI PHUT MO moi leg (duyet het, khong chan) — boi canh cho tran G."""
    out = np.zeros(d["n"])
    h = []
    gross = 0.0
    for i in np.argsort(d["m0c"], kind="stable"):
        t = d["m0c"][i]
        while h and h[0][0] <= t:
            gross -= heapq.heappop(h)[1]
        out[i] = (gross + d["margin"][i]) / eqref[min(int(t), T - 1)]
        heapq.heappush(h, (d["m1c"][i], d["margin"][i]))
        gross += d["margin"][i]
    return out


def analyze(a):
    os.makedirs(a.out, exist_ok=True)
    L = {rn: load_layout(v) for rn, v in RUNS.items()}
    QC, QL, VV = {}, {}, {}
    for rn in RUNS:
        z = np.load(os.path.join(a.out, "contrib_%s.npz" % rn), allow_pickle=False)
        QC[rn], QL[rn], VV[rn] = z["pc"], z["pl"], z["vv"]
    zt = np.load(os.path.join(a.out, "trap.npz"), allow_pickle=False)
    p10, btc, nsym = zt["p10"], zt["btc"], zt["nsym"]
    zb = np.load(BASELINE_NPZ, allow_pickle=False)
    base_eq = {rn: zb["c_" + rn].astype(np.float64) for rn in RUNS}
    out = dict(runs=RUNS, cap0=CAP0, years=YEARS)

    say("=" * 96)
    say("TAIL_LEVER — chan gross exposure / trap ALT (XAP XI offline; KHONG phai sim)")
    say("=" * 96)
    say("")
    say("BUOC 0 — CONG NGHIEM THU (chot truoc)")
    eqs = {}
    for rn in RUNS:
        d = L[rn]
        acc = np.ones(d["n"], bool)
        eq = build_eq(d, QC[rn], QL[rn], VV[rn], acc)
        eqs[rn] = eq
        dv = float(np.abs(eq - base_eq[rn]).max())
        rel = dv / float(np.abs(base_eq[rn]).max()) * 100
        say("W1 %-9s dựng lại từ đóng góp từng leg vs series.npz: max|Δ|=%.4g USDT (%.1e%% equity)  %s"
            % (rn, dv, rel, "PASS" if dv <= 2e-3 else "FAIL"))
    ref = {"T170": (-19.96, 144.4), "KEEPLEG0": (-19.96, 147.2), "T100": (-26.26, 248.2),
           "GD92": (-24.30, 277.8)}
    for rn in RUNS:
        dd, uw = maxdd(eqs[rn]), uw_min(eqs[rn]) / 1440.0
        r0, r1 = ref[rn]
        say("W2 %-9s maxDD=%.2f%% (ref %.2f) UW=%.1f ngay (ref %.1f)  %s"
            % (rn, dd, r0, uw, r1, "PASS" if abs(dd - r0) <= 0.05 and abs(uw - r1) <= 0.1 else "FAIL"))
        out.setdefault("baseline", {})[rn] = dict(
            maxdd=dd, uw=uw, dropw=win_drop(eqs[rn]), pnl=float(L[rn]["pnl"].sum()),
            eqf=float(eqs[rn][-1]), n=L[rn]["n"],
            cagr=float(((eqs[rn][-1] / CAP0) ** (1.0 / YEARS) - 1) * 100))

    # ---------------- A
    say("")
    say("BUOC A — PHAN RA RUI RO HE THONG (dong gop tung coin)")
    top10 = {}
    for rn in RUNS:
        ep = episodes(eqs[rn])
        ep.sort(key=lambda x: -x[4])
        top10[rn] = ep[:10]
    cases = []
    for rn in RUNS:
        for n_, (i, j, _pi, _pj, dep) in enumerate(top10[rn], 1):
            cases.append((rn, "ep%02d" % n_, i, j, dep))
    for rn in RUNS:
        eq = eqs[rn]
        jw = int(np.argmin(eq[I_W0:I_W1])) + I_W0
        iw = int(np.argmax(eq[I_W0:jw + 1])) + I_W0
        cases.append((rn, "W2510", iw, jw, 0.0))
    agg = {}
    say("%-9s %-7s %9s %10s %8s %8s %8s %6s %8s" %
        ("nen", "cú", "độ sâu%", "depth$", "top1%", "top3%", "rest%", "ncoin", "resid%"))
    a_rows = []
    for rn, tag, i, j, dep in cases:
        d = L[rn]
        ci = per_sym_unp(d, QC[rn], VV[rn], i)
        cj = per_sym_unp(d, QC[rn], VV[rn], j)
        contrib = {s: cj.get(s, 0.0) - ci.get(s, 0.0) for s in set(ci) | set(cj)}
        sel = (d["m1c"] > i) & (d["m1c"] <= j)
        for s, p in zip(d["sym"][sel], d["pnl"][sel]):
            contrib[s] = contrib.get(s, 0.0) + p
        depth = float(eqs[rn][i] - eqs[rn][j])
        if not depth:
            continue
        neg = sorted((v for v in contrib.values() if v < 0))
        tot_neg = sum(neg)
        t1 = neg[0] / tot_neg * 100 if neg else 0.0
        t3 = sum(neg[:3]) / tot_neg * 100 if neg else 0.0
        rest = 100.0 - t3
        resid = abs(sum(contrib.values()) + depth) / abs(depth) * 100
        names = [(s, v) for s, v in sorted(contrib.items(), key=lambda kv: kv[1]) if v < 0][:3]
        a_rows.append(dict(run=rn, tag=tag, i=int(i), j=int(j), t_peak=str(MT[i])[:16],
                           t_trough=str(MT[j])[:16], dep=dep, depth=depth,
                           top1=t1, top3=t3, rest=rest, ncoin=len(neg), resid=resid,
                           top1_sym=(names[0][0] if names else None),
                           top1_usd=(names[0][1] if names else 0.0),
                           top3_syms=[(s, round(v)) for s, v in names]))
        say("%-9s %-7s %8.2f %10.0f %7.1f %7.1f %7.1f %6d %7.2f  %s" %
            (rn, tag, dep, depth, t1, t3, rest, len(neg), resid,
             ", ".join("%s %+.0f" % (s, v) for s, v in names)))
        agg.setdefault(rn, []).append((t1, t3, rest, resid))
    rmax = max(r["resid"] for r in a_rows)
    say("W3 phân rã: max |Σcontrib − depth|/depth = %.2f%%  %s" % (rmax, "PASS" if rmax <= 2 else "FAIL"))
    say("")
    say("A-tong hop (11 cú/nền: 10 top + cửa sổ 11/10):")
    say("%-9s %8s %8s %8s %8s %10s" % ("nen", "top1%", "top3%", "rest%", "ncoin", "resid%"))
    for rn in RUNS:
        v = np.array([(x[0], x[1], x[2], x[3]) for x in agg[rn]], float)
        nc = np.mean([x["ncoin"] for x in a_rows if x["run"] == rn])
        say("%-9s %7.1f %8.1f %8.1f %8.1f %10.2f" %
            (rn, v[:, 0].mean(), v[:, 1].mean(), v[:, 2].mean(), nc, v[:, 3].max()))
    a_verdict = {}
    for rn in RUNS:
        tr = [(x[0], x[1]) for x in agg[rn]]
        a_verdict[rn] = dict(top1_mean=float(np.mean([t[0] for t in tr])),
                             top3_mean=float(np.mean([t[1] for t in tr])),
                             n_sys=int(sum(1 for t1, t3 in tr if t1 < 25 and t3 < 50)), m=len(tr),
                             n_single=int(sum(1 for t1, t3 in tr if t1 > 50)))
        say("   %-9s hệ thống (top1<25 & top3<50): %d/%d cú · 1-coin (top1>50): %d/%d cú"
            % (rn, a_verdict[rn]["n_sys"], a_verdict[rn]["m"],
               a_verdict[rn]["n_single"], a_verdict[rn]["m"]))
    out["A"] = dict(rows=a_rows, verdict=a_verdict)

    # ---------------- B
    say("")
    say("BUOC B — TRAN GROSS EXPOSURE (XAP XI offline, KHONG phai sim)")
    say("Quy tac chot truoc: chan leg moi khi Σmargin leg dang mo + margin_leg > G% * equity(m0).")
    say("")
    say("B0 — boi canh: (Σ margin mo)/equity TAI PHUT MO leg (duyet het, khong chan), theo leg:")
    say("%-9s %8s %8s %8s %8s %8s | %8s %8s %8s %8s" %
        ("nen", "mean%", "p50%", "p90%", "p99%", "max%", ">20%", ">30%", ">40%", ">50%"))
    expo = {}
    for rn in RUNS:
        r = exposure_stats(L[rn], eqs[rn])
        expo[rn] = r
        say("%-9s %7.1f %8.1f %8.1f %8.1f %8.1f | %7.0f%% %7.0f%% %7.0f%% %7.0f%%" %
            (rn, r.mean() * 100, np.percentile(r, 50) * 100, np.percentile(r, 90) * 100,
             np.percentile(r, 99) * 100, r.max() * 100,
             (r > 0.2).mean() * 100, (r > 0.3).mean() * 100, (r > 0.4).mean() * 100,
             (r > 0.5).mean() * 100))
    rows_b = {}
    say("%-9s %5s %9s %9s %10s %8s %6s %6s %7s %7s" %
        ("nen", "G%", "intraDD%", "dropW%", "PnL", "CAGR%", "n", "block", "UWd", "dCAGR"))
    for rn in RUNS:
        d = L[rn]
        b0 = out["baseline"][rn]
        rows_b[rn] = {}
        for G in [None] + G_LIST:
            eqref = eqs[rn]
            for it in range(3):
                acc = np.ones(d["n"], bool) if G is None else greedy_cap(d, G, eqref)
                eq = eqs[rn] if G is None else build_eq(d, QC[rn], QL[rn], VV[rn], acc)
                if it > 0 and np.array_equal(acc, prev):
                    break
                prev = acc
                eqref = eq
            m = metrics(d, eq, acc)
            if G is not None:
                m["d_dropw"] = m["dropw"] - b0["dropw"]
                m["d_maxdd"] = m["maxdd"] - b0["maxdd"]
                m["d_pnl_pct"] = (m["pnl"] / b0["pnl"] - 1) * 100
                m["d_cagr"] = m["cagr"] - b0["cagr"]
                m["cut_dropw_pct"] = -m["d_dropw"] / (-b0["dropw"]) * 100
            rows_b[rn][str(G)] = m
            say("%-9s %5s %9.2f %9.2f %10.0f %8.2f %6d %6d %7.1f %7.2f" %
                (rn, "-" if G is None else G, m["maxdd"], m["dropw"], m["pnl"], m["cagr"],
                 m["n"], m["nblock"], m["uw"], m["cagr"] - b0["cagr"]))
    out["B"] = rows_b
    # W4 don dieu
    mono = True
    for rn in RUNS:
        nb = [rows_b[rn][str(G)]["nblock"] for G in G_LIST]
        say("W4 %-9s #block theo G=20/30/40/50: %s  %s" %
            (rn, nb, "PASS" if all(nb[i] >= nb[i + 1] for i in range(3)) else "FAIL"))
        mono &= all(nb[i] >= nb[i + 1] for i in range(3))
    say("")
    say("B — bang 'cat duoc gi / mat gi' (Δ so voi KHONG tran):")
    say("%-9s %5s %10s %12s %10s %10s %12s %10s" %
        ("nen", "G%", "ΔdropW pp", "ΔintraDD pp", "ΔPnL %", "ΔCAGR pp", "PnL leg chan", "cat %depsau"))
    for rn in RUNS:
        for G in G_LIST:
            m = rows_b[rn][str(G)]
            say("%-9s %5d %10.2f %12.2f %10.1f %10.2f %12.0f %10.0f" %
                (rn, G, m["d_dropw"], m["d_maxdd"], m["d_pnl_pct"], m["d_cagr"],
                 m["pnl_blocked"], m["cut_dropw_pct"]))
    say("")
    say("B — gate chot truoc (cat >= 25%% do sau 11/10 VA giu >= 70%% PnL VA giu >= 70%% CAGR VA intraDD khong xau hon):")
    for rn in RUNS:
        b0 = out["baseline"][rn]
        ok = []
        for G in G_LIST:
            m = rows_b[rn][str(G)]
            if (m["cut_dropw_pct"] >= 25 and m["pnl"] >= 0.70 * b0["pnl"]
                    and m["cagr"] >= 0.70 * b0["cagr"] and m["d_maxdd"] <= 0.05):
                ok.append(G)
        say("   %-9s G dat gate: %s" % (rn, ok if ok else "KHONG co G nao"))

    # ---------------- C
    say("")
    say("BUOC C — TRAP ALT (p10 ret1h cross-section + BTC)")
    nb_ = np.isfinite(p10)
    l1 = np.zeros(T, bool)
    l1[nb_] = np.abs(p10[nb_]) > TRAP_P10
    l1n = np.zeros(T, bool)
    l1n[nb_] = p10[nb_] < -TRAP_P10
    l2 = np.zeros(T, bool)
    ok = nb_ & np.isfinite(btc)
    l2[ok] = (np.abs(btc[ok]) < TRAP_BTC) & (p10[ok] < TRAP_ALT)
    say("p10 ret1h: n_moc co du lieu %d/%d · min %.1f%% · p1 %.1f%% · p5 %.1f%% · median %.3f%%"
        % (nb_.sum(), T, np.nanmin(p10) * 100, np.nanpercentile(p10, 1) * 100,
           np.nanpercentile(p10, 5) * 100, np.nanmedian(p10) * 100))
    say("L1 |p10|>20%%: %d moc · L1neg p10<-20%%: %d moc · L2 (|BTC1h|<1%% & p10<-10%%): %d moc"
        % (l1.sum(), l1n.sum(), l2.sum()))

    def runs_of(mask):
        ch = np.diff(mask.astype(np.int8))
        st = list(np.where(ch == 1)[0] + 1)
        en = list(np.where(ch == -1)[0] + 1)
        if mask[0]:
            st = [0] + st
        if mask[-1]:
            en = en + [len(mask)]
        return list(zip(st, en))

    def variants():
        v = {}
        v["primary L1uL2"] = l1 | l2
        v["sens L1 only"] = l1
        v["sens L2 only"] = l2
        v["expl L1neg|L2"] = l1n | l2
        return v

    vs = variants()
    trap_out = {}
    for name, msk in vs.items():
        rr = runs_of(msk)
        yrs = {}
        for s0, s1 in rr:
            y = int(MT[s0].year)
            yrs[y] = yrs.get(y, 0) + 1
        trap_out[name] = dict(n_runs=len(rr), n_min=int(msk.sum()), by_year=yrs,
                              med_len=float(np.median([b - a for a, b in rr])) if rr else 0.0)
        say("%-14s kich hoat %4d lan (%6d moc, dai trung vi %.0f phut) · theo nam %s"
            % (name, len(rr), msk.sum(), trap_out[name]["med_len"],
               ",".join("%d:%d" % kv for kv in sorted(yrs.items()))))
    # lookback variant
    lag = np.zeros(T, bool)
    cum = np.concatenate([[0], np.cumsum(vs["primary L1uL2"].astype(np.int32))])
    for m in range(T):
        lag[m] = cum[m + 1] - cum[max(0, m + 1 - LOOKBACK)] > 0
    say("sens lookback %d phut: %d lan / %d moc" % (LOOKBACK, len(runs_of(lag)), lag.sum()))
    out["C_trap"] = trap_out

    say("")
    say("C — do tren duong equity (chan leg moi tai phut mo lệnh):")
    say("%-9s %-16s %9s %9s %10s %8s %6s %9s %12s" %
        ("nen", "luat", "intraDD%", "dropW%", "PnL", "%PnL", "n", "catTB10%", "PnL leg chan"))
    rows_c = {}
    for rn in RUNS:
        d = L[rn]
        b0 = out["baseline"][rn]
        rows_c[rn] = {}
        base_drops = -np.array([x[4] for x in top10[rn]])
        for name, msk in list(vs.items()) + [("sens lookback", lag)]:
            acc = np.ones(d["n"], bool)
            blocked = msk[np.clip(d["m0c"], 0, T - 1)]
            acc[blocked] = False
            eq = build_eq(d, QC[rn], QL[rn], VV[rn], acc)
            m = metrics(d, eq, acc)
            sc_drops = np.array([run_drop(eq, i, j) for i, j, _p, _q, _z in top10[rn]])
            cut = float(np.mean((1 - sc_drops / base_drops) * 100))
            m.update(d_dropw=m["dropw"] - b0["dropw"], d_maxdd=m["maxdd"] - b0["maxdd"],
                     cut_top10=cut, n_blocked=len(blocked))
            rows_c[rn][name] = m
            say("%-9s %-16s %9.2f %9.2f %10.0f %7.1f %6d %9.1f %12.0f" %
                (rn, name, m["maxdd"], m["dropw"], m["pnl"], m["pnl"] / b0["pnl"] * 100,
                 m["n"], cut, m["pnl_blocked"]))
    out["C"] = rows_c
    say("")
    say("C — tra loi (3): so lan / cat duoc / mat gi (primary L1uL2):")
    for rn in RUNS:
        b0 = out["baseline"][rn]
        m = rows_c[rn]["primary L1uL2"]
        say("   %-9s %d lan kich hoat | chan %d leg | ΔdropW %+.2f pp | ΔintraDD %+.2f pp | "
            "PnL giu %.0f%% | cat top10 TB %.1f%%" %
            (rn, trap_out["primary L1uL2"]["n_runs"], m["nblock"], m["d_dropw"], m["d_maxdd"],
             m["pnl"] / b0["pnl"] * 100, m["cut_top10"]))

    # ---------------- ket luan
    say("")
    say("KET LUAN (1)(2)(3)(4)")
    say("(1) Rui ro he thong: xem bang A — top1/top3 vs phan con lai.")
    for rn in RUNS:
        say("    %-9s top1 TB %.1f%% · top3 TB %.1f%% · con lai %.1f%% · he thong %d/%d cu"
            % (rn, a_verdict[rn]["top1_mean"], a_verdict[rn]["top3_mean"],
               100 - a_verdict[rn]["top3_mean"], a_verdict[rn]["n_sys"], a_verdict[rn]["m"]))
    say("(2) Tran G: xem bang B (d_dropw vs d_pnl_pct).")
    for rn in RUNS:
        for G in G_LIST:
            m = rows_b[rn][str(G)]
            say("    %-9s G=%2d%%: cat dropW %5.2f pp (%.0f%% do sau 11/10) · PnL giu %5.1f%% · "
                "block %4d/%d leg · intraDD %+.2f pp"
                % (rn, G, -m["d_dropw"], -m["d_dropw"] / (-out["baseline"][rn]["dropw"]) * 100,
                   m["pnl"] / out["baseline"][rn]["pnl"] * 100, m["nblock"], L[rn]["n"],
                   m["d_maxdd"]))
    say("(3) Trap ALT: xem bang C — co dang khong?")
    say("(4) De xuat cau hinh cho SIM THAT: xem muc cuoi cua RESULT_TAIL_LEVER.md.")
    with open(os.path.join(a.out, "report_tail_lever.txt"), "w") as f:
        f.write("\n".join(REP) + "\n")
    with open(os.path.join(a.out, "tail_lever.json"), "w") as f:
        json.dump({k: v for k, v in out.items()}, f, indent=1, default=str)
    say("")
    say("[done] report=%s json=%s" % (os.path.join(a.out, "report_tail_lever.txt"),
                                      os.path.join(a.out, "tail_lever.json")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["all", "data", "analyze"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="/home/ubuntu/taillever")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.stage in ("all", "data"):
        stage_data(a)
    if a.stage in ("all", "analyze"):
        analyze(a)


if __name__ == "__main__":
    main()
