#!/usr/bin/env python3
"""RESET_RULE_P1 — CHAM LAI HAU KIEM artifact sim CO SAN theo LUAT 4 TANG, tai phi base/stress.

Thuc thi DUNG docs/prereg/PREREG_RESET_RULE_P1.md (chot TRUOC khi tinh so).

THUAN PYTHON OFFLINE tren Oracle. KHONG Java/sim, KHONG claude-run, KHONG push du lieu,
DEV only (moi moc <= 2025-12-30, khong doc 2026).

  BUOC A  doc artifact: printDone.csv (leg) + sim.out (equity NGAY) cho 20 doi tuong.
  BUOC B  TU KIEM cong cu: KEEPLEG0 / cd-sel15 phai khop so DA CONG BO (n/equity/CAGR/maxDD daily/q*/top-1%).
          Lech => DUNG, khong cham tiep.
  BUOC C  hau kiem chi phi: net_pnl = pnl + (0,008 - c) * margin  (c = base/stress/legacy), XAP XI.
  BUOC D  MTM MOC PHUT tu ticker 1m (khung intraday_dd.py) => maxDD phut (toan ky + theo nam), UW.
  BUOC E  cham 4 tang @base + @stress, doi chieu du bao MASTER, dem so doi trang thai khi ha phi.

Usage: python3 reset_rule_score.py [--skip-mtm] [--workers 4] [--json OUT.json] [--report OUT.md]
"""
import argparse
import gzip
import json
import logging
import math
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

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("reset_p1")

KOUT = "/home/ubuntu/kaggle_sim/out"
DEV = "/home/ubuntu/java/devrun"
TICKER = "/home/ubuntu/kaggle_data_hpo"
CAP0 = 35000.0
TZ_SHIFT_H = 7
DAY0 = "20210701"
DAY1 = "20251230"

LEGACY = 0.008
COSTS = {"base": 0.00112, "stress": 0.00150}
COST_LEVELS = {"legacy": LEGACY, "base": COSTS["base"], "stress": COSTS["stress"]}
MTM_COSTS = COST_LEVELS

SEED = 20260905
NREP = 2000
BLOCK_H = 72
ANCHOR = pd.Timestamp("2021-07-01")
K_INFL = 19
INFL = math.sqrt(2.0 * math.log(K_INFL))

DD_MAX, UW_MAX, Q_MIN, CONC_MAX, GROSS_MAX = 40.0, 250, -20.0, 15.0, 70.0
Q_STAR_MIN, TOP1_MAX, EPISODE_DROP = 15.0, 25.0, 3
NI_WIN, NI_TSLOSS = -2.0, 2.5
TIER4_N_MULT = 1.3

B_STAR = "kg0-g170"          # == FG_KEEPLEG0 (1'), md5 99e42b75

# (tag, base_dir) — 20 doi tuong khoa truoc
TAGS = [
    ("kg0-g170", KOUT),
    ("cd-sel15", KOUT),
    ("sc-b1", KOUT), ("sc-b2", KOUT), ("sc-b3", KOUT), ("sc-b4", KOUT),
    ("kg0-g155", KOUT), ("kg0-g140", KOUT), ("kg0-g125", KOUT),
    ("gs2-t155", KOUT), ("gs2-t140", KOUT), ("gs2-t125", KOUT),
    ("cc-t100", KOUT),
    ("gr-kg0-q995", KOUT), ("gr-kg0-q998", KOUT), ("gr-kg0-q999", KOUT),
    ("gr-kg0-q998-15m", KOUT),
    ("rc-a-q995", KOUT), ("rc-a-q998", KOUT), ("rc-a-q999", KOUT),
]
BASE_OF = {"kg0-g170": os.path.join(DEV, "FG_KEEPLEG0")}   # B* o java/devrun (byte-identical voi out/kg0-g170)

RATE_KEYS = ["win%", "TSloss%", "mP|SM", "mP|SL"]

RX_DAILY = re.compile(r"Update (\d{8}) \d\d:\d\d => b:\s*(-?\d+).*?unP:\s*(-?\d+)")

REPORT = []


def say(s=""):
    REPORT.append(str(s))
    log.info(s)


def tagdir(tag):
    return BASE_OF.get(tag) or os.path.join(KOUT, tag)


# --------------------------------------------------------------- artifact
def load_legs(tag):
    p = os.path.join(tagdir(tag), "storage", "printDone.csv")
    d = pd.read_csv(p, on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    for c in ("quantity", "entry", "margin", "pnl", "profit"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["pnl", "margin"]).copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M", errors="coerce")
    d["te"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce")
    d = d.dropna(subset=["ts", "te"]).sort_values("ts", kind="mergesort").reset_index(drop=True)
    d["notional"] = d["quantity"] * d["entry"]
    d["blk2"] = ((d["ts"] - ANCHOR) / pd.Timedelta(hours=BLOCK_H)).astype(int)
    return d


def md5_of(tag):
    import hashlib
    p = os.path.join(tagdir(tag), "storage", "printDone.csv")
    h = hashlib.md5()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def load_daily(tag):
    p = os.path.join(tagdir(tag), "logs", "sim.out")
    rows = []
    with open(p, errors="ignore") as fh:
        for line in fh:
            m = RX_DAILY.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)), int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "b", "unP"]).drop_duplicates("d", keep="last")
    e["t"] = pd.to_datetime(e["d"], format="%Y%m%d")
    e = e.set_index("t").sort_index()
    e["equity"] = e["b"] + e["unP"]
    return e


# --------------------------------------------------------------- cost adjust
def adj_pnl(d, c):
    return (d["pnl"] + (LEGACY - c) * d["notional"]).to_numpy(float)


def daily_adj(d, daily, c):
    """equity NGAY hau kiem = equity artifact (b+unP) + cum_notional(te<=t) * (LEGACY-c)."""
    eq = daily["equity"].astype(float).copy()
    if c == LEGACY:
        return eq
    te_days = d["te"].dt.normalize().to_numpy()
    o = np.argsort(te_days, kind="mergesort")
    cn = np.cumsum(d["notional"].to_numpy(float)[o])
    dd = daily.index.normalize().to_numpy()
    idx = np.searchsorted(te_days[o], dd, side="right")
    not_before = np.where(idx > 0, cn[np.clip(idx - 1, 0, len(cn) - 1)], 0.0)
    return eq + (LEGACY - c) * not_before


# --------------------------------------------------------------- metrics
def tail_metrics(p):
    p = np.asarray(p, float)
    p = p[np.isfinite(p)]
    n = len(p)
    if n == 0:
        return {}
    s = np.sort(p)[::-1]
    tot = s.sum()
    k1 = max(1, int(math.ceil(0.01 * n)))
    csum = np.cumsum(s)
    ks = np.where(csum >= tot)[0]
    return {
        "sum_pnl": float(tot),
        "top1_pct": float(100.0 * s[:k1].sum() / tot) if tot != 0 else float("nan"),
        "q_star": float(100.0 * (ks[0] + 1) / n) if len(ks) else float("nan"),
        "median": float(np.median(p)),
    }


def episode_drop3(d, ap):
    """Bo top-3 EPISODE (ngay co lenh, noi khoang trong <= 2 ngay) => tong con lai."""
    dd = pd.Series(d["te"].dt.normalize().to_numpy()).drop_duplicates().sort_values().to_numpy()
    if len(dd) == 0:
        return float("nan"), 0
    eps, start = [], dd[0]
    prev = dd[0]
    for x in dd[1:]:
        if (x - prev) / np.timedelta64(1, "D") > 2:
            eps.append((start, prev))
            start = x
        prev = x
    eps.append((start, prev))
    ted = d["te"].dt.normalize().to_numpy()
    sums = []
    for (a, b) in eps:
        m = (ted >= a) & (ted <= b)
        sums.append(float(ap[m].sum()))
    sums_sorted = sorted(sums, reverse=True)
    drop = sum(sums_sorted[:EPISODE_DROP])
    return float(sum(sums) - drop), len(eps)


def gross_conc(d, eq):
    """gross TB/MAX + conc 1 coin MAX (khuon size_count_score.gross)."""
    d = d.copy()
    dts = (d["ts"] - d["ts"].min()).dt.total_seconds().to_numpy(float)
    dte = (d["te"] - d["ts"].min()).dt.total_seconds().to_numpy(float)
    m = d["margin"].to_numpy(float)
    sym = d["sym"].to_numpy()
    ev = []
    for a, b, mm, s in zip(dts, dte, m, sym):
        if not (np.isfinite(a) and np.isfinite(b) and np.isfinite(mm)) or b < a:
            continue
        ev.append((a, mm, s, +1))
        ev.append((b, mm, s, -1))
    if not ev:
        return dict(gross_mean=float("nan"), gross_max=float("nan"), conc_max=float("nan"))
    ev.sort(key=lambda x: (x[0], -x[3]))
    t0 = d["ts"].min()
    eqi = eq.copy()
    days = eqi.index.normalize()
    vals = eqi.to_numpy(float)
    run_m, open_syms = 0.0, {}
    wg, wtime, gmax = 0.0, 0.0, 0.0
    coin_margin = {}
    cmax = 0.0
    prev = None

    def eq_at(sec):
        day = (t0 + pd.Timedelta(seconds=sec)).normalize()
        j = days.searchsorted(day, side="right") - 1
        return float(vals[j]) if j >= 0 else float(vals[0])

    for (t, mm, s, sign) in ev:
        if prev is not None and t > prev:
            e = eq_at(prev)
            if e > 0:
                g = run_m / e
                wg += g * (t - prev)
                wtime += (t - prev)
                gmax = max(gmax, g)
                cmax = max(cmax, max(coin_margin.values()) / e if coin_margin else 0.0)
        if sign > 0:
            run_m += mm
            open_syms[s] = open_syms.get(s, 0) + 1
            coin_margin[s] = coin_margin.get(s, 0.0) + mm
        else:
            run_m -= mm
            open_syms[s] = open_syms.get(s, 0) - 1
            coin_margin[s] = coin_margin.get(s, 0.0) - mm
            if open_syms[s] <= 0:
                open_syms.pop(s, None)
                coin_margin.pop(s, None)
        prev = t
    return dict(gross_mean=float(100.0 * wg / wtime) if wtime > 0 else float("nan"),
                gross_max=float(100.0 * gmax), conc_max=float(100.0 * cmax))


def rates_profit(d):
    p = d["profit"]
    sm = p[d["status"] == "STOP_MARKET_DONE"]
    sl = p[d["status"] == "STOP_LOSS_DONE"]
    return {
        "win%": float(100.0 * (p > 0).mean()) if len(d) else float("nan"),
        "TSloss%": float(100.0 * (d["status"] == "STOP_LOSS_DONE").mean()) if len(d) else float("nan"),
        "mP|SM": float(sm.mean()) if len(sm) else float("nan"),
        "mP|SL": float(sl.mean()) if len(sl) else float("nan"),
    }


def yearly_quarterly(eq):
    ye = eq.resample("YE").last()
    y0 = pd.concat([pd.Series([eq.iloc[0]], index=[eq.index[0]]), ye]).iloc[:-1]
    yr = dict(zip((str(p.year) for p in ye.index.to_period("Y")),
                  (ye.values / y0.values - 1) * 100))
    qe = eq.resample("QE").last()
    q0 = pd.concat([pd.Series([eq.iloc[0]], index=[eq.index[0]]), qe]).iloc[:-1]
    qr = dict(zip((str(p) for p in qe.index.to_period("Q")),
                  (qe.values / q0.values - 1) * 100))
    return yr, qr


def core_metrics(tag, d, daily, ck):
    c = COST_LEVELS[ck]
    eq = daily_adj(d, daily, c)
    ap = adj_pnl(d, c)
    years = (daily.index[-1] - daily.index[0]).days / 365.25
    cagr = ((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1) * 100
    dd = (eq / eq.cummax() - 1) * 100
    uw_run = eq < eq.cummax()
    uw = int(uw_run.groupby((~uw_run).cumsum()).sum().max())
    yr, qr = yearly_quarterly(eq)
    t = tail_metrics(ap)
    ep_sum, n_ep = episode_drop3(d, ap)
    gc = gross_conc(d, eq)
    r = rates_profit(d)
    return dict(tag=tag, cost=ck, n=len(d), equity=float(eq.iloc[-1]), cagr=float(cagr),
                maxdd_daily=float(dd.min()), uw_daily=uw,
                qmin=float(min(qr.values())) if qr else float("nan"),
                qr={k: float(v) for k, v in qr.items()}, yr={k: float(v) for k, v in yr.items()},
                neg_year=[y for y, v in yr.items() if v < 0],
                q_star=t.get("q_star"), top1_pct=t.get("top1_pct"), sum_pnl=t.get("sum_pnl"),
                median=t.get("median"), ep_sum=ep_sum, n_ep=n_ep,
                gross_max=gc["gross_max"], gross_mean=gc["gross_mean"], conc_max=gc["conc_max"],
                rates=r)


# --------------------------------------------------------------- CI (paired block-72h)
def _block_aggs(d, blocks, idxmap):
    """gop theo khoi: n, cnt_win, cnt_sloss, cnt_sm, sum_p_sm, sum_p_sl (tren `profit` %)."""
    nb = len(blocks)
    bi = np.array([idxmap[b] for b in d["blk2"].to_numpy()], dtype=np.int64)
    prof = d["profit"].to_numpy(float)
    fin = np.isfinite(prof)
    st = d["status"].to_numpy()
    is_sm = (st == "STOP_MARKET_DONE")
    is_sl = (st == "STOP_LOSS_DONE")
    return dict(
        n=np.bincount(bi, minlength=nb).astype(float),
        win=np.bincount(bi, weights=((prof > 0) & fin).astype(float), minlength=nb),
        sloss=np.bincount(bi, weights=is_sl.astype(float), minlength=nb),
        c_sm=np.bincount(bi, weights=(is_sm & fin).astype(float), minlength=nb),
        s_sm=np.bincount(bi, weights=np.where(is_sm & fin, prof, 0.0), minlength=nb),
        c_sl=np.bincount(bi, weights=(is_sl & fin).astype(float), minlength=nb),
        s_sl=np.bincount(bi, weights=np.where(is_sl & fin, prof, 0.0), minlength=nb),
    )


def ci_pair(da, db):
    """Bootstrap khoi-72h PAIRED (cung luoi khoi), 2000 rep, seed 20260905, inflate(k)."""
    blocks = np.union1d(da["blk2"].unique(), db["blk2"].unique())
    idxmap = {int(b): i for i, b in enumerate(blocks)}
    A = _block_aggs(da, blocks, idxmap)
    Bx = _block_aggs(db, blocks, idxmap)
    nb = len(blocks)
    rng = np.random.default_rng(SEED)
    ra = rates_profit(da)
    rb = rates_profit(db)
    obs = {k: ra[k] - rb[k] for k in RATE_KEYS}
    draws = {k: np.empty(NREP) for k in RATE_KEYS}
    for r in range(NREP):
        pick = rng.choice(nb, size=nb, replace=True)
        W = np.bincount(pick, minlength=nb).astype(float)
        ta = {k: float(W @ v) for k, v in A.items()}
        tb = {k: float(W @ v) for k, v in Bx.items()}
        fa = {"win%": 100.0 * ta["win"] / ta["n"] if ta["n"] else np.nan,
              "TSloss%": 100.0 * ta["sloss"] / ta["n"] if ta["n"] else np.nan,
              "mP|SM": ta["s_sm"] / ta["c_sm"] if ta["c_sm"] else np.nan,
              "mP|SL": ta["s_sl"] / ta["c_sl"] if ta["c_sl"] else np.nan}
        fb = {"win%": 100.0 * tb["win"] / tb["n"] if tb["n"] else np.nan,
              "TSloss%": 100.0 * tb["sloss"] / tb["n"] if tb["n"] else np.nan,
              "mP|SM": tb["s_sm"] / tb["c_sm"] if tb["c_sm"] else np.nan,
              "mP|SL": tb["s_sl"] / tb["c_sl"] if tb["c_sl"] else np.nan}
        for k in RATE_KEYS:
            draws[k][r] = fa[k] - fb[k]
    out = {}
    for k in RATE_KEYS:
        arr = draws[k][np.isfinite(draws[k])]
        if len(arr) == 0:
            out[k] = dict(obs=float(obs[k]), lo=float("nan"), hi=float("nan"), worse_sig=False)
            continue
        lo, hi = np.percentile(arr, [2.5, 97.5])
        ctr = (lo + hi) / 2.0
        lo, hi = ctr - (ctr - lo) * INFL, ctr + (hi - ctr) * INFL
        out[k] = dict(obs=float(obs[k]), lo=float(lo), hi=float(hi),
                      worse_sig=bool(hi < 0.0))    # hieu < 0 co y nghia => KEM
    return out


# --------------------------------------------------------------- MTM phut
def load_legs_minute(d):
    """tra d voi chi so phut m0/m1 tren truc UTC (DAY0)."""
    ts = d["ts"] - pd.Timedelta(hours=TZ_SHIFT_H)
    te = d["te"] - pd.Timedelta(hours=TZ_SHIFT_H)
    d = d.copy()
    d["tsu"] = ts
    d["teu"] = te
    d["m0"] = ((ts - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1)).astype(np.int64)
    d["m1"] = ((te - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1)).astype(np.int64)
    return d


_G = {}


def _init(legsd, need_days):
    _G["legs"] = legsd
    _G["need_days"] = need_days


def _work(days):
    """moi ngay: tra per-tag (unP, stepcum_pnl, stepcum_margin, n_missing) float32[1440]."""
    res = {}
    for day in days:
        if day not in _G["need_days"]:
            res[day] = {}
            continue
        p = os.path.join(TICKER, "ticker_%s.bin.gz" % day)
        t0 = int(pd.Timestamp(day).value // 10 ** 6)
        base = int((pd.Timestamp(day) - pd.Timestamp(DAY0)) // pd.Timedelta(days=1)) * 1440
        per = {}
        need = {}
        for tag, d in _G["legs"].items():
            sub = d[(d.m0 < base + 1440) & (d.m1 > base)]
            if len(sub):
                need[tag] = sub
        C, srow, allnan = None, {}, set()
        if os.path.exists(p):
            syms = sorted({s + "USDT" for sub in need.values() for s in sub["sym"].unique()})
            srow = {s: i for i, s in enumerate(syms)}
            C = np.full((max(1, len(syms)), 1440), np.nan, np.float32)
            if syms:
                with gzip.open(p, "rb") as f:
                    for k, v in jbin.iter_minutes(f.read()):
                        if k < t0 or k >= t0 + 1440 * 60000:
                            continue
                        mi = (k - t0) // 60000
                        for s, tup in v.items():
                            j = srow.get(s)
                            if j is not None:
                                C[j, mi] = tup[3]      # priceClose
                idx = np.where(np.isnan(C).any(axis=1))[0]
                if len(idx):
                    C[idx] = pd.DataFrame(C[idx].T).ffill().bfill().to_numpy().T
                allnan = set(np.where(np.isnan(C).all(axis=1))[0].tolist())
                C[np.isnan(C)] = 0.0
        for tag, sub in need.items():
            u = np.zeros(1440, np.float32)
            nmiss = 0
            for sym, q, e, i0, i1 in zip(sub["sym"], sub["quantity"], sub["entry"],
                                         np.maximum(sub["m0"].to_numpy() - base, 0),
                                         np.minimum(sub["m1"].to_numpy() - base, 1440)):
                key = sym + "USDT"
                if i1 <= i0 or key not in srow or (int(srow[key]) in allnan):
                    nmiss += 1
                    continue
                j = srow[key]
                u[i0:i1] += (q * C[j, i0:i1]).astype(np.float32) - np.float32(q * e)
            sp = np.zeros(1440, np.float32)
            sm = np.zeros(1440, np.float32)
            cl = sub[(sub["m1"] >= base) & (sub["m1"] < base + 1440)]
            for pnl, mg, i1 in zip(cl["pnl"], cl["notional"], cl["m1"] - base):
                sp[int(i1)] += np.float32(pnl)
                sm[int(i1)] += np.float32(mg)
            per[tag] = (u, np.cumsum(sp).astype(np.float32), np.cumsum(sm).astype(np.float32), nmiss)
        res[day] = per
    return res


class MTMState:
    """Theo doi maxDD/UW tren chuoi phut (vector hoa theo ngay) cho cac muc phi."""

    def __init__(self):
        self.glob = {c: [-np.inf, 0.0, 0, 0] for c in MTM_COSTS}   # peak, dd, uw_run, uw_max
        self.py = {}                                             # (c, year) -> [peak, dd, uw_run, uw_max]

    @staticmethod
    def _consume(v, st):
        rp = np.maximum.accumulate(np.concatenate(([st[0]], v)))[1:]
        d = v / rp - 1.0
        m = float(d.min() * 100.0)
        if m < st[1]:
            st[1] = m
        st[0] = float(rp[-1])
        u = (v < rp)
        if not u.any():
            st[2] = 0
            return
        mk = np.concatenate(([0], u.view(np.int8), [0]))
        df = np.diff(mk)
        starts = np.where(df == 1)[0]
        ends = np.where(df == -1)[0]
        lens = (ends - starts).astype(int)
        max_run = int(lens.max())
        if u[0] and st[2] > 0:
            max_run = max(max_run, int(lens[0]) + int(st[2]))
        if max_run > st[3]:
            st[3] = max_run
        if u[0] and u.all():
            st[2] = int(st[2]) + int(len(u))
        elif u[-1]:
            st[2] = int(lens[-1])
        else:
            st[2] = 0

    def feed(self, m_global, eq):
        day = (pd.Timestamp(DAY0) + pd.Timedelta(minutes=int(m_global))).normalize()
        year = day.year
        for c in MTM_COSTS:
            v = np.asarray(eq[c], float)
            key = (c, year)
            if key not in self.py:
                self.py[key] = [float(v[0]), 0.0, 0, 0]
            self._consume(v, self.py[key])
            self._consume(v, self.glob[c])

def _mtm_result(st):
    out = {}
    for c in MTM_COSTS:
        out[c] = dict(
            dd_total=float(st.glob[c][1]),
            uw_total_days=float(st.glob[c][3] / 1440.0),
            dd_year={int(y): float(v[1]) for (cc, y), v in st.py.items() if cc == c},
            uw_year={int(y): float(v[3]) / 1440.0 for (cc, y), v in st.py.items() if cc == c},
            missing=0)
    return out


def run_mtm(legs, workers=4, chunk=30):
    """tra {tag: {cost: {dd_total, uw_total_days, dd_year, uw_year, missing}}}."""
    legsmin = {t: load_legs_minute(d) for t, d in legs.items()}
    lo = min(int(d["m0"].min()) for d in legsmin.values())
    hi = max(int(d["m1"].max()) for d in legsmin.values())
    lo_d = (pd.Timestamp(DAY0) + pd.Timedelta(minutes=lo)).normalize()
    hi_d = (pd.Timestamp(DAY0) + pd.Timedelta(minutes=hi)).normalize()
    days = [d.strftime("%Y%m%d") for d in pd.date_range(lo_d, hi_d, freq="D")]
    need_days = set()
    for t, d in legsmin.items():
        tsd = d["tsu"].dt.normalize().to_numpy()
        ted = d["teu"].dt.normalize().to_numpy()
        for a, b in zip(tsd, ted):
            for day in pd.date_range(a, b, freq="D"):
                need_days.add(day.strftime("%Y%m%d"))
    need_days &= set(days)
    log.info("MTM: %d ngay lien tuc (%s..%s), trong do %d ngay co vi the mo"
             % (len(days), days[0], days[-1], len(need_days)))

    prefix = {}
    for t, d in legsmin.items():
        te_days = (d["teu"]).dt.normalize().to_numpy()
        o = np.argsort(te_days, kind="mergesort")
        te_s = te_days[o]
        cp = np.cumsum(d["pnl"].to_numpy(float)[o])
        cn = np.cumsum(d["notional"].to_numpy(float)[o])
        pre = {}
        for day in days:
            key = pd.Timestamp(day).to_datetime64()
            i = int(np.searchsorted(te_s, key, side="left"))
            pre[day] = (float(cp[i - 1]) if i > 0 else 0.0, float(cn[i - 1]) if i > 0 else 0.0)
        prefix[t] = pre

    st = {t: MTMState() for t in legsmin}
    missing = {t: 0 for t in legsmin}
    zeros = (np.zeros(1440, np.float32), np.zeros(1440, np.float32),
              np.zeros(1440, np.float32), 0)
    chunks = [days[i:i + chunk] for i in range(0, len(days), chunk)]
    t0 = time.time()
    done = 0
    with Pool(workers, initializer=_init, initargs=(legsmin, need_days)) as pool:
        for res in pool.imap(_work, chunks):
            for day in sorted(res):
                per = res[day]
                didx = int((pd.Timestamp(day) - pd.Timestamp(DAY0)) // pd.Timedelta(minutes=1))
                for t in legsmin:
                    pr, pn = prefix[t][day]
                    u, sp, sm, nmiss = per.get(t, zeros)
                    if nmiss:
                        missing[t] += int(nmiss)
                    eq = {}
                    for c, cv in MTM_COSTS.items():
                        eq[c] = CAP0 + pr + (LEGACY - cv) * pn + sp + (LEGACY - cv) * sm + u
                    st[t].feed(didx, eq)
                done += 1
            if done % (10 * chunk) == 0:
                log.info("  MTM %d/%d ngay  %.0fs", done, len(days), time.time() - t0)
    out = {}
    for t in legsmin:
        out[t] = _mtm_result(st[t])
        for c in MTM_COSTS:
            out[t][c]["missing"] = int(missing[t])
    return out


# --------------------------------------------------------------- tiers
def tier1(m, mt):
    """tra (pass, chi tiet dict)"""
    worst_y = min(mt["dd_year"].values()) if mt["dd_year"] else float("nan")
    ok = {
        "maxDD_phut_nam": (worst_y >= -DD_MAX, worst_y),
        "UW": (mt["uw_total_days"] <= UW_MAX, mt["uw_total_days"]),
        "qmin": (m["qmin"] >= Q_MIN, m["qmin"]),
        "0_nam_am": (len(m["neg_year"]) == 0, m["neg_year"]),
        "conc": (m["conc_max"] <= CONC_MAX, m["conc_max"]),
        "gross": (m["gross_max"] <= GROSS_MAX, m["gross_max"]),
    }
    return all(v[0] for v in ok.values()), ok


def tier2(m):
    ok = {
        "q*": (m["q_star"] is not None and m["q_star"] >= Q_STAR_MIN, m["q_star"]),
        "top1%": (m["top1_pct"] <= TOP1_MAX, m["top1_pct"]),
        "bo_top3_episode>0": (m["ep_sum"] > 0, m["ep_sum"]),
    }
    return all(v[0] for v in ok.values()), ok


def tier3(m, ci):
    r, rb = m["rates"], m["bstar_rates"]
    dw = r["win%"] - rb["win%"]
    dt = r["TSloss%"] - rb["TSloss%"]
    det = {"win%_d": (dw >= NI_WIN, dw), "TSloss%_d": (dt <= NI_TSLOSS, dt),
           "mP|SM": (not ci["mP|SM"]["worse_sig"], ci["mP|SM"]["obs"]),
           "mP|SL": (not ci["mP|SL"]["worse_sig"], ci["mP|SL"]["obs"])}
    return all(v[0] for v in det.values()), det


def tier4(m, bstar):
    if m["tag"] == B_STAR:
        return None, {"ref": True}
    cal = m["cagr"] / abs(m["mtm_dd_total"]) if m["mtm_dd_total"] not in (0, None) else float("nan")
    calb = bstar["cagr"] / abs(bstar["mtm_dd_total"])
    ok = {"Calmar>=B*": (cal >= calb, (cal, calb)),
          "n>=1,3x": (m["n"] >= TIER4_N_MULT * bstar["n"], (m["n"], bstar["n"])),
          "conc<=B*": (m["conc_max"] <= bstar["conc_max"], (m["conc_max"], bstar["conc_max"]))}
    return all(v[0] for v in ok.values()), ok


# --------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-mtm", action="store_true")
    ap.add_argument("--mtm-cache", default="/tmp/rr_p1_mtm.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=30)
    ap.add_argument("--json", default="/home/ubuntu/src/BinanceFuturesJava/docs/result/reset_rule_p1.json")
    ap.add_argument("--report", default="/home/ubuntu/reset_rule_p1_run.txt")
    a = ap.parse_args()

    say("=" * 78)
    say("RESET_RULE_P1 — cham lai hau kiem @base %.5f / @stress %.5f (%%/vong) | k=%d inflate=%.4f"
        % (COSTS["base"], COSTS["stress"], K_INFL, INFL))

    legs, daily, md5 = {}, {}, {}
    say("")
    say("BUOC A — artifact (20 doi tuong)")
    say("%-16s %6s %10s %12s %10s %s" % ("tag", "n", "equity", "sum_pnl", "md5", "simout"))
    missing = []
    for tag, _ in TAGS:
        try:
            d = load_legs(tag)
            e = load_daily(tag)
            legs[tag], daily[tag] = d, e
            md5[tag] = md5_of(tag)
            say("%-16s %6d %10.0f %12.0f %10s %s" %
                (tag, len(d), e.equity.iloc[-1], d.pnl.sum(), md5[tag][:8], "OK"))
        except Exception as ex:
            missing.append(tag)
            say("%-16s THIEU ARTIFACT: %s" % (tag, ex))
    if missing:
        say("=> THIEU artifact: %s" % missing)
    if B_STAR not in legs:
        say("=> DUNG: thieu B*"); return

    # ---- TU KIEM
    say("")
    say("BUOC B — TU KIEM (muc phi legacy = nguyen trang artifact)")
    EXP = {"kg0-g170": dict(n=1085, eq=103083, cagr=27.14, dd=-11.21, qs=19.0, t1=23.74, md5="99e42b75"),
           "cd-sel15": dict(n=744, eq=71718, cagr=17.29, dd=-6.27, qs=21.2, t1=19.13, md5="13171916")}
    selfck = {}
    say("%-10s %-8s %5s %10s %7s %8s %6s %7s %8s" %
        ("tag", "khoan", "n", "equity", "CAGR", "maxDD", "q*", "top-1%", "md5"))
    fail = False
    for t, ex in EXP.items():
        if t not in legs:
            continue
        m = core_metrics(t, legs[t], daily[t], "legacy")
        row = dict(n=m["n"], eq=m["equity"], cagr=m["cagr"], dd=m["maxdd_daily"],
                   qs=m["q_star"], t1=m["top1_pct"], md5=md5[t][:8])
        for k in ("n", "eq", "cagr", "dd", "qs", "t1"):
            ke = {"n": "n", "eq": "eq", "cagr": "cagr", "dd": "dd", "qs": "qs", "t1": "t1"}[k]
            exp = ex[ke]
            gots = row[k]
            tol = 1.0 if k in ("n", "eq") else 0.15
            if k == "eq":
                tol = 1.0
            okk = abs(gots - exp) <= tol
            say("%-10s %-8s %5s %10s %7s %8s %6s %7s %8s  exp=%s %s" %
                (t, k, "", "", "", "", "", "", "", exp, "OK" if okk else "*** LECH ***"))
            if not okk:
                fail = True
        if row["md5"] != ex["md5"]:
            fail = True
        selfck[t] = dict(got=row, exp=ex)
    if fail:
        say("=> DUNG: tu kiem KHONG khop so da cong bo. Sua truoc khi cham tiep.")

    # ---- metrics 3 muc phi (legacy/base/stress)
    say("")
    say("BUOC C — hau kiem chi phi + do 4 tang")
    allm = {}
    for tag in legs:
        allm[tag] = {ck: core_metrics(tag, legs[tag], daily[tag], ck) for ck in COST_LEVELS}

    # CI tang 3 (tren profit %, KHONG phu thuoc phi)
    ci = {}
    for tag in legs:
        ci[tag] = ci_pair(legs[tag], legs[B_STAR]) if tag != B_STAR else \
            {k: dict(obs=0.0, lo=0.0, hi=0.0, worse_sig=False) for k in RATE_KEYS}

    # ---- MTM
    if not a.skip_mtm:
        say("")
        say("BUOC D — MTM MOC PHUT (ticker 1m, khung intraday_dd.py)")
        if a.mtm_cache and os.path.exists(a.mtm_cache):
            with open(a.mtm_cache) as fh:
                raw = json.load(fh)
            say("  [cache] dung lai %s" % a.mtm_cache)
        else:
            raw = run_mtm(legs, workers=a.workers, chunk=a.chunk)
            if a.mtm_cache:
                with open(a.mtm_cache, "w") as fh:
                    json.dump(raw, fh)
        for tag in legs:
            for c in MTM_COSTS:
                allm[tag][c]["mtm_dd_total"] = raw[tag][c]["dd_total"]
                allm[tag][c]["mtm_uw_days"] = raw[tag][c]["uw_total_days"]
                allm[tag][c]["mtm_dd_year"] = {int(k): v for k, v in raw[tag][c]["dd_year"].items()}
                allm[tag][c]["mtm_uw_year"] = raw[tag][c]["uw_year"]
                allm[tag][c]["mtm_missing"] = raw[tag][c].get("missing", 0)
        # cong MTM tu kiem cho KEEPLEG0 (RESULT_INTRADAY_DD: -19,96% / UW 147,2 ngay)
        mm = allm[B_STAR]["legacy"]
        say("TU KIEM MTM KEEPLEG0: maxDD phut toan ky = %.2f%% (cong bo -19,96) | UW = %.1f ngay (cong bo 147,2) %s"
            % (mm["mtm_dd_total"], mm["mtm_uw_days"],
               "OK" if abs(mm["mtm_dd_total"] + 19.96) <= 0.20 and abs(mm["mtm_uw_days"] - 147.2) <= 1.0 else "*** LECH ***"))
    else:
        say("")
        say("BUOC D — MTM BO QUA (--skip-mtm)")

    # ---- cham tang
    say("")
    say("BUOC E — BANG 4 TANG")
    out = {}
    for cost in ["legacy"] + list(COSTS.keys()):
        say("")
        say("== @%s (%.5f) ==" % (cost, MTM_COSTS[cost]))
        say("%-16s %5s %8s %7s %8s %7s %7s | %-5s %-5s %-5s %-5s" %
            ("tag", "n", "equity", "CAGR", "ddPhut", "q*", "top1%", "T1", "T2", "T3", "T4"))
        for tag in [t for t, _ in TAGS if t in allm]:
            m = allm[tag][cost]
            m["bstar_rates"] = allm[B_STAR][cost]["rates"]
            t1 = tier1(m, dict(dd_year=m.get("mtm_dd_year", {}),
                               uw_total_days=m.get("mtm_uw_days", float("nan")))) \
                if not a.skip_mtm else (None, {})
            t2 = tier2(m)
            t3 = tier3(m, ci[tag])
            t4 = tier4(m, allm[B_STAR][cost]) if not a.skip_mtm else (None, {})
            f = lambda x: "PASS" if x[0] else ("FAIL" if x[0] is False else "n/a")
            say("%-16s %5d %8.0f %7.2f %8.2f %7.1f %7.2f | %-5s %-5s %-5s %-5s" %
                (tag, m["n"], m["equity"], m["cagr"],
                 m.get("mtm_dd_total", float("nan")), m["q_star"] or float("nan"),
                 m["top1_pct"], f(t1), f(t2), f(t3), f(t4)))
            out.setdefault(tag, {})[cost] = dict(
                n=m["n"], equity=m["equity"], cagr=m["cagr"],
                maxdd_daily=m["maxdd_daily"], mtm_dd_total=m.get("mtm_dd_total"),
                mtm_dd_year=m.get("mtm_dd_year"), mtm_uw_days=m.get("mtm_uw_days"),
                qmin=m["qmin"], q_star=m["q_star"], top1_pct=m["top1_pct"],
                ep_sum=m["ep_sum"], n_ep=m["n_ep"],
                conc_max=m["conc_max"], gross_max=m["gross_max"],
                neg_year=m["neg_year"], rates=m["rates"],
                t1=t1, t2=t2, t3=t3, t4=t4, ci=ci[tag])

    # ---- lat verdict khi ha phi
    say("")
    say("BUOC F — LAT VERDICT KHI HA PHI (legacy 0,800 -> base 0,112 -> stress 0,150)")
    flips = {}
    for tag in out:
        row = {}
        for k in ("t2", "t4"):
            if tag == B_STAR and k == "t4":
                row[k] = None
                continue
            a_ = out[tag]["legacy"][k][0]
            b_ = out[tag]["base"][k][0]
            row[k] = (a_, b_, out[tag]["stress"][k][0])
        flips[tag] = row
    f2 = [t for t, r in flips.items() if r["t2"] and r["t2"][0] != r["t2"][1]]
    f4 = [t for t, r in flips.items() if r["t4"] and r["t4"][0] != r["t4"][1]]
    say("tang2 DOI trang thai legacy->base: %d/%d  %s" % (len(f2), len(flips), f2))
    say("tang4 DOI trang thai legacy->base: %d/%d  %s" % (len(f4), sum(1 for r in flips.values() if r["t4"]), f4))
    say("")
    say("%-16s %-28s %-28s" % ("tag", "T2 legacy|base|stress", "T4 legacy|base|stress"))
    for tag in flips:
        r = flips[tag]
        g = lambda x: "/".join("-" if y is None else ("P" if y else "F") for y in x) if x else "-"
        say("%-16s %-28s %-28s" % (tag, g(r["t2"]), g(r["t4"])))

    js = dict(prereg="docs/prereg/PREREG_RESET_RULE_P1.md", k_infl=K_INFL, inflate=INFL,
              seed=SEED, nrep=NREP, block_h=BLOCK_H, costs=COSTS, legacy=LEGACY,
              bstar=B_STAR, self_check=selfck, md5=md5, missing_artifact=missing,
              flips=flips, metrics=out)
    with open(a.json, "w") as fh:
        json.dump(js, fh, indent=1, ensure_ascii=False, default=str)
    with open(a.report, "w") as fh:
        fh.write("\n".join(REPORT))
    log.info("JSON -> %s", a.json)
    log.info("REPORT -> %s", a.report)


if __name__ == "__main__":
    main()
