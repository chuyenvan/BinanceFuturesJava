#!/usr/bin/env python3
"""COVERAGE_M2_BASE (2026-10-09): phan tich KHACH QUAN (khong luat, khong GO) M2 (K24+skipFull+NSEL M2) vs baseline
(K24+skipFull): loi nhuan/rui ro tren equity MTM phut, DO PHU lenh ngay/tuan/thang, dac tinh lenh, benchmark BTC/ETH.

Chi run DEV <=2025-12-31 co san: stress 1,675% nsel-nen-s*/nsel-m2-s* (8 seed); phi goc gqsf-* (8) / nsel-m2b-* (3).
KHONG doc ~/kaggle_sim/out/ho26-*. 0 sim, 0 Kaggle, 0 Java, 0 cham 242. Thuoc MTM phut = nsel_score_b (import hang so,
parse_min, TICKER; jbin.iter_minutes doc nen 1m); tu kiem CAGR22/maxDD22 vs docs/result/NSEL_RESULT_B.json.
Usage: python3 research/analysis/coverage_m2_base.py [--workers 3] [--quick N] [--from-cache] [--md-only]
"""
import argparse
import gzip
import json
import logging
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy import stats

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import nsel_score_b as B  # noqa: E402
import jbin  # noqa: E402

log = logging.getLogger("coverage_m2_base")
OUT = "/home/ubuntu/kaggle_sim/out/"
WD = "/home/ubuntu/claude_master/1009/coverage"
LOCK = "/home/ubuntu/claude_master/1002/oracle_heavy.lock"
JSON_OUT = REPO + "/docs/audit/COVERAGE_M2_BASE_20261009.json"
MD_OUT = REPO + "/docs/audit/COVERAGE_M2_BASE_20261009.md"
B_JSON = REPO + "/docs/result/NSEL_RESULT_B.json"
A_JSON = REPO + "/docs/result/NSEL_RESULT_A.json"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
SIDE = [42, 7, 21]
YEARS = [2022, 2023, 2024, 2025]
T0, T1, NM, TZ_MS = B.T0, B.T1, B.NM, B.TZ_MS
NDAY = NM // 1440
DAY0 = pd.Timestamp("2022-01-01")
DAYS = pd.date_range(DAY0, periods=NDAY, freq="D")
YR = np.asarray(DAYS.year)
MID = np.asarray((DAYS.year - 2022) * 12 + DAYS.month - 1)
ME = np.nonzero(np.asarray(DAYS.is_month_end))[0]
MSI = np.r_[np.nonzero(np.asarray(DAYS.day) == 1)[0], NDAY]
NW = 208
WK_S = 1 + 7 * np.arange(NW)
WK_E = WK_S + 7
WY = YR[WK_S + 1]
YA = {y: int((pd.Timestamp("%d-01-01" % y) - DAY0).days) for y in YEARS + [2026]}
YRS = NDAY / 365.25
SQ = math.sqrt(365.0)
EP_GAP = 3
BTC, ETH = "BTCUSDT", "ETHUSDT"
GL = {}


def wait_lock():
    while os.path.exists(LOCK):
        log.info("cho lock %s", LOCK)
        time.sleep(60)


def runs_list():
    r = []
    for s in SEEDS:
        r += [("base", s, "nsel-nen-s%d" % s), ("m2", s, "nsel-m2-s%d" % s)]
    for s in SEEDS:
        r.append(("base_fee0", s, "gqsf-a1" if s == 42 else "gqsf-s%d" % s))
    for s in SIDE:
        r.append(("m2_fee0", s, "nsel-m2b-s%d" % s))
    assert not any(t.startswith("ho26") for _, _, t in r)
    ok = [x for x in r if os.path.exists(OUT + x[2] + "/storage/printDone.csv") and os.path.exists(OUT + x[2] + "/result.json")]
    log.info("run du %d/%d; thieu %s", len(ok), len(r), [x[2] for x in r if x not in ok])
    return ok


def load(tag):
    d = pd.read_csv(OUT + tag + "/storage/printDone.csv", index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("entry", "margin", "pnl", "quantity"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    n0 = len(d)
    d = d.dropna(subset=["entry", "margin", "pnl", "quantity"]).copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    d["ts"] = B.parse_min(d["start"].astype(str).str.strip()).to_numpy()
    d["te"] = B.parse_min(d["end"].astype(str).str.strip()).to_numpy()
    d["s"] = (d["ts"] - T0) // 60000
    d["e"] = (d["te"] - T0) // 60000
    d["q"] = d["margin"] / d["entry"]
    d["notional"] = d["quantity"] * d["entry"]
    d["row"] = np.arange(len(d))
    d = d.sort_values(["s", "row"], kind="mergesort").reset_index(drop=True)
    d["pid"] = d.groupby(["sym", "e"], sort=False).ngroup()
    d["leg0"] = ~d.duplicated("pid", keep="first")
    d["sym_t"] = d["sym"] + "USDT"
    return d, n0 - len(d)


def work(day):
    """1 ngay ticker (UTC): unrealized/phut theo run (= nsel_score_b.work), low 1m cho MAE, close BTC/ETH."""
    dms = int(pd.Timestamp(day).value // 10 ** 6)
    g0 = (dms - T0) // 60000
    m = (GL["s"] < g0 + 1440) & (GL["e"] > g0) & (GL["e"] > GL["s"])
    idx = np.nonzero(m)[0]
    syms = sorted(set(GL["sym"][idx].tolist()) | {BTC, ETH})
    si = {s: i for i, s in enumerate(syms)}
    C = np.full((len(syms), 1440), np.nan)
    LO = np.full((len(syms), 1440), np.nan)
    p = os.path.join(B.TICKER, "ticker_%s.bin.gz" % day)
    nofile = 0
    if os.path.exists(p):
        with gzip.open(p, "rb") as f:
            for k, v in jbin.iter_minutes(f.read()):
                j = (k - dms) // 60000
                if 0 <= j < 1440:
                    for s, i in si.items():
                        t = v.get(s)
                        if t is not None:
                            C[i, j], LO[i, j] = t[3], t[2]
    else:
        nofile = 1
    CF = pd.DataFrame(C).ffill(axis=1).to_numpy()
    U = np.zeros((GL["R"], 1440))
    miss = legmin = 0
    mi, mv = [], []
    for li in idx:
        i = si[GL["sym"][li]]
        s, e, en, q = int(GL["s"][li]), int(GL["e"][li]), GL["entry"][li], GL["q"][li]
        a, b = max(s, g0) - g0, min(e, g0 + 1440) - g0
        pr = CF[i, a:b]
        nn = np.isnan(pr)
        miss += int(nn.sum())
        legmin += int(b - a)
        U[GL["run"][li], a:b] += q * (np.where(nn, en, pr) - en)
        a2 = max(s + 1, g0) - g0
        if b > a2:
            lw = LO[i, a2:b]
            if np.isfinite(lw).any():
                mi.append(int(li))
                mv.append(float(np.nanmin(lw)))
    lo, hi = max(0, -g0), min(1440, NM - g0)
    hi = max(hi, lo)
    return dict(g0=g0 + lo, U=U[:, lo:hi], btc=C[si[BTC], lo:hi], eth=C[si[ETH], lo:hi], mi=mi, mv=mv,
                miss=miss, legmin=legmin, nofile=nofile)


def build(RUNS, D, workers, quick):
    cols = {k: [] for k in ("run", "sym", "entry", "q", "s", "e")}
    for ri, (_, _, t) in enumerate(RUNS):
        d = D[t]
        cols["run"].append(np.full(len(d), ri))
        cols["sym"].append(d["sym_t"].to_numpy())
        cols["entry"].append(d["entry"].to_numpy(float))
        cols["q"].append(d["q"].to_numpy(float))
        cols["s"].append(d["s"].to_numpy(np.int64))
        cols["e"].append(d["e"].to_numpy(np.int64))
    for k in cols:
        GL[k] = np.concatenate(cols[k])
    GL["R"] = len(RUNS)
    days = [x.strftime("%Y%m%d") for x in pd.date_range("2021-12-31", "2025-12-31", freq="D")]
    if quick:
        days = days[:quick]
    U = np.zeros((len(RUNS), NM))
    bt, et = np.full(NM, np.nan), np.full(NM, np.nan)
    mae = np.full(len(GL["s"]), np.nan)
    chk = dict(miss=0, legmin=0, nofile=0)
    t0 = time.time()
    with Pool(workers) as pool:
        for i, o in enumerate(pool.imap_unordered(work, days, chunksize=4)):
            g, n = o["g0"], o["U"].shape[1]
            U[:, g:g + n] += o["U"]
            bt[g:g + n], et[g:g + n] = o["btc"], o["eth"]
            if o["mi"]:
                ix, v = np.array(o["mi"]), np.array(o["mv"])
                mae[ix] = np.fmin(mae[ix], v)
            for k in chk:
                chk[k] += o[k]
            if i % 100 == 0:
                log.info("ngay %d/%d %.0fs", i, len(days), time.time() - t0)
    return U, bt, et, mae, chk


def equity(d, rj, Ur):
    """= nsel_score_b.metrics: realized pnl ghi tai phut end + unrealized phut."""
    ie = d["e"].to_numpy()
    pnl = d["pnl"].to_numpy(float)
    real = np.zeros(NM)
    ok = (ie >= 0) & (ie < NM)
    np.add.at(real, ie[ok], pnl[ok])
    return float(rj["equity_start"]) + pnl[ie < 0].sum() + np.cumsum(real) + Ur


def runs_of(b):
    x = np.diff(np.concatenate([[0], np.asarray(b, np.int8), [0]]))
    st = np.nonzero(x == 1)[0]
    return st, np.nonzero(x == -1)[0] - st


def tmin(m):
    return str(pd.Timestamp(T0 + int(m) * 60000 + TZ_MS, unit="ms"))[:16]


def pct(x):
    x = np.asarray(x)
    return 100.0 * float(np.mean(x)) if x.size else None


def gini(g):
    g = np.sort(np.asarray(g, float))
    n = len(g)
    if g.sum() <= 0:
        return None
    return float(np.sum((2 * np.arange(1, n + 1) - n - 1) * g) / (n * g.sum()))


def riskm(eq):
    e0 = float(eq[0])
    Ed = eq[1439::1440]
    assert len(Ed) == NDAY, len(Ed)
    r = Ed / np.concatenate([[e0], Ed[:-1]]) - 1.0
    pk = np.maximum.accumulate(eq)
    dd = eq / pk - 1.0
    t = int(dd.argmin())
    p = int(np.argmax(eq[:t + 1]))
    rec = np.nonzero(eq[t:] >= eq[p])[0]
    mdd = float(dd.min())
    cagr = (eq[-1] / e0) ** (1.0 / YRS) - 1.0
    _, ln = runs_of(eq < pk * (1 - 1e-12))
    wk = Ed[WK_E] / Ed[WK_S] - 1.0
    wz = np.abs(Ed[WK_E] - Ed[WK_S]) < 1e-6 * e0
    mo = Ed[ME] / np.concatenate([[e0], Ed[ME[:-1]]]) - 1.0
    sd = float(r.std(ddof=1))
    dn = float(np.sqrt(np.mean(np.minimum(r, 0) ** 2)))
    hr = len(rec) > 0
    m = dict(cagr=100 * cagr, maxdd=100 * mdd, calmar=cagr / abs(mdd) if mdd < 0 else None,
             sharpe=float(r.mean()) / sd * SQ if sd > 0 else None,
             sortino=float(r.mean()) / dn * SQ if dn > 0 else None,
             vol=100 * sd * SQ, worst_day=100 * float(r.min()), worst_week=100 * float(wk.min()),
             worst_month=100 * float(mo.min()), uw_max_d=float(ln.max()) / 1440 if len(ln) else 0.0,
             dd_peak=tmin(p), dd_trough=tmin(t), dd_recover=tmin(t + rec[0]) if hr else None,
             rec_trough_d=float(rec[0]) / 1440 if hr else None,
             rec_peak_d=float(t + rec[0] - p) / 1440 if hr else None,
             unrec_d=None if hr else float(NM - 1 - p) / 1440,
             skew=float(stats.skew(r)), kurt=float(stats.kurtosis(r)),
             pct_week_pos=pct((wk > 0) & ~wz), pct_week_neg=pct((wk < 0) & ~wz), pct_week_zero=pct(wz),
             pct_month_pos=pct(mo > 0), eq0=e0, eq1=float(eq[-1]),
             roi={y: 100 * (float(Ed[YA[y + 1] - 1]) / (e0 if YA[y] == 0 else float(Ed[YA[y] - 1])) - 1) for y in YEARS})
    return m, r, Ed, wk, wz


def occ(a, b, w=None):
    a, b = np.clip(a, 0, NM), np.clip(b, 0, NM)
    k = b > a
    ww = np.ones(int(k.sum())) if w is None else np.asarray(w, float)[k]
    x = np.zeros(NM + 1)
    np.add.at(x, a[k], ww)
    np.add.at(x, b[k], -ww)
    return np.cumsum(x[:-1])


def coverage(d, eq, Ed, wk, wz):
    s, e = d["s"].to_numpy(), d["e"].to_numpy()
    l0, pnl = d["leg0"].to_numpy(), d["pnl"].to_numpy(float)
    win = (s >= 0) & (s < NM)
    de, de0 = s[win] // 1440, s[win & l0] // 1440
    cnt = np.bincount(de, minlength=NDAY)
    has, has0 = cnt > 0, np.bincount(de0, minlength=NDAY) > 0
    wcnt = np.array([cnt[WK_S[k] + 1:WK_E[k] + 1].sum() for k in range(NW)])
    wh0 = np.array([has0[WK_S[k] + 1:WK_E[k] + 1].any() for k in range(NW)])
    mo_has = np.bincount(MID[de], minlength=48) > 0
    legs = occ(s, e)
    g = d.groupby("pid").agg(a=("s", "min"), b=("e", "max"))
    pos = occ(g["a"].to_numpy(), g["b"].to_numpy())
    Uu = np.maximum(occ(s, e, d["notional"].to_numpy(float)), 0) / eq
    inp = legs > 0.5
    dpos = inp.reshape(NDAY, 1440).any(axis=1)
    gs, gl = runs_of(~has)
    if not len(gl):
        gs, gl = np.array([0]), np.array([0])
    ed = np.nonzero(has)[0]
    brk = np.concatenate([[False], np.diff(ed) - 1 >= EP_GAP])
    epi = np.cumsum(brk)
    nep = int(epi[-1]) + 1
    epd = np.full(NDAY, -1)
    epd[ed] = epi
    ep_n = np.bincount(epd[de], minlength=nep)
    ep_p = np.bincount(epd[de], weights=pnl[win], minlength=nep)
    ep_st = ed[np.concatenate([[True], brk[1:]])]
    ep_en = ed[np.concatenate([brk[1:], [True]])]
    epy = np.bincount(YR[ep_st] - 2022, minlength=4)
    dE = np.diff(np.concatenate([[float(eq[0])], Ed]))
    srt = np.sort(dE)[::-1]
    tot, totp = float(dE.sum()), float(pnl[win].sum())
    m = dict(n_entries_y=float(win.sum()) / 4, n_leg0_y=float((win & l0).sum()) / 4,
             pct_day_entry_all=pct(has), pct_day_entry_leg0=pct(has0), pct_week_entry=pct(wcnt > 0),
             pct_week_entry_leg0=pct(wh0), pct_month_entry=pct(mo_has), pct_time_pos=pct(inp), pct_day_pos=pct(dpos),
             pos_mean=float(pos.mean()), pos_mean_inpos=float(pos[inp].mean()),
             pos_p95_inpos=float(np.percentile(pos[inp], 95)), pos_max=float(pos.max()),
             legs_mean_inpos=float(legs[inp].mean()), legs_max=float(legs.max()),
             U_mean_inpos=100 * float(Uu[inp].mean()), U_p95_inpos=100 * float(np.percentile(Uu[inp], 95)),
             U_max=100 * float(Uu.max()), n_gap=int(len(gl)), gap_p50=float(np.percentile(gl, 50)),
             gap_p90=float(np.percentile(gl, 90)), gap_max=int(gl.max()),
             gap_max_start=str(DAYS[int(gs[int(np.argmax(gl))])].date()),
             n_ep=nep, ep_per_year=nep / 4.0, ep_year={y: int(epy[y - 2022]) for y in YEARS},
             trades_per_ep=float(ep_n.mean()), ep_len_mean=float((ep_en - ep_st + 1).mean()),
             wk_trades_mean=float(wcnt.mean()), wk_trades_p25=float(np.percentile(wcnt, 25)),
             wk_trades_p50=float(np.percentile(wcnt, 50)), wk_trades_p75=float(np.percentile(wcnt, 75)),
             wk_trades_max=float(wcnt.max()), top5_share=100 * float(srt[:5].sum()) / tot,
             top10_share=100 * float(srt[:10].sum()) / tot, top20_share=100 * float(srt[:20].sum()) / tot,
             top3ep_share=100 * float(np.sort(ep_p)[::-1][:3].sum()) / totp, gini_gain=gini(np.maximum(dE, 0)))
    yr = {}
    for y in YEARS:
        a, b = YA[y], YA[y + 1]
        ws = WY == y
        _, gy = runs_of(~has[a:b])
        yr[y] = dict(n_entries=int(cnt[a:b].sum()), pct_day_entry_all=pct(has[a:b]), pct_day_entry_leg0=pct(has0[a:b]),
                     pct_week_entry=pct(wcnt[ws] > 0), pct_time_pos=pct(inp[a * 1440:b * 1440]), pct_day_pos=pct(dpos[a:b]),
                     gap_max=int(gy.max()) if len(gy) else 0, n_ep=int(epy[y - 2022]),
                     wk_trades_p50=float(np.median(wcnt[ws])), pct_week_pos=pct(((wk > 0) & ~wz)[ws]))
    m["yr"] = yr
    return m


def trades(d, eq, mae):
    s, e = d["s"].to_numpy(), d["e"].to_numpy()
    cl = (e >= 0) & (e < NM)
    pnl, mg = d["pnl"].to_numpy(float)[cl], d["margin"].to_numpy(float)[cl]
    hold = (d["te"].to_numpy() - d["ts"].to_numpy())[cl] / 3.6e6
    roi = 100 * pnl / mg
    w, ls = pnl > 0, pnl < 0
    l0 = d["leg0"].to_numpy()[cl]
    lc = 100 * pnl / eq[np.clip(s[cl] - 1, 0, NM - 1)]
    k = cl & (s >= 0)
    mv = 100 * (mae[k] / d["entry"].to_numpy(float)[k] - 1)
    mv = mv[np.isfinite(mv)]
    st = d["status"].astype(str).str.strip()[cl].value_counts()
    return dict(n_closed_y=float(cl.sum()) / 4, win_rate=pct(w), avg_win_usd=float(pnl[w].mean()),
                avg_loss_usd=float(pnl[ls].mean()), avg_win_pct=float(roi[w].mean()), avg_loss_pct=float(roi[ls].mean()),
                payoff=float(pnl[w].mean() / abs(pnl[ls].mean())), expectancy_pct=float(roi.mean()),
                expectancy_usd=float(pnl.mean()), hold_p50_h=float(np.percentile(hold, 50)),
                hold_p90_h=float(np.percentile(hold, 90)), pct_timestop=pct(hold >= 168 - 1e-6),
                pct_timestop_leg0=pct(hold[l0] >= 168 - 1e-6), worst_loss_cap_pct=float(lc.min()),
                worst_loss_pct_margin=float(roi.min()), mae_p10_pct=float(np.percentile(mv, 10)),
                mae_p50_pct=float(np.percentile(mv, 50)), mae_min_pct=float(mv.min()), mae_n=int(len(mv)),
                status={str(a): int(b) for a, b in st.items()})


def _cc(x, y):
    if len(x) > 2 and np.std(x) > 0 and np.std(y) > 0:
        return float(np.corrcoef(x, y)[0, 1])
    return None


def corr(r, rb, re_):
    m = rb < -0.05
    return dict(corr_full=_cc(r, rb), corr_eth=_cc(r, re_), n_crash=int(m.sum()), corr_crash=_cc(r[m], rb[m]),
                mean_ret_crash=100 * float(r[m].mean()) if m.any() else None,
                mean_btc_crash=100 * float(rb[m].mean()) if m.any() else None)


def bench(bt, et):
    out, rr, P = {}, {}, {}
    miss = {"BTC": int(np.isnan(bt).sum()), "ETH": int(np.isnan(et).sum())}
    for nm, px in (("BTC", bt), ("ETH", et)):
        P[nm] = pd.Series(px).ffill().bfill().to_numpy()
        out[nm], rr[nm] = riskm(P[nm] / P[nm][0])[:2]
    p, V, val = P["BTC"], np.empty(NM), 1.0
    for k in range(48):
        a, b = MSI[k] * 1440, MSI[k + 1] * 1440
        p0 = p[a - 1] if a > 0 else p[0]
        V[a:b] = 0.5 * val * p[a:b] / p0 + 0.5 * val
        val = float(V[b - 1])
    out["BTC50"], rr["BTC50"] = riskm(V)[:2]
    for nm in out:
        out[nm]["corr"] = corr(rr[nm], rr["BTC"], rr["ETH"])
    return out, rr, miss


def flat(m, pre=""):
    o = {}
    for k, v in m.items():
        if isinstance(v, dict):
            o.update(flat(v, pre + str(k) + "."))
        elif isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, (bool, np.bool_)):
            o[pre + str(k)] = float(v)
    return o


def aggregate(FL, RUNS):
    AG = {}
    for arm in ("base", "m2", "base_fee0", "m2_fee0"):
        ts = [t for a, _, t in RUNS if a == arm]
        if not ts:
            continue
        AG[arm] = {}
        for k in sorted(set().union(*[FL[t].keys() for t in ts])):
            v = np.array([FL[t][k] for t in ts if k in FL[t]], float)
            v = v[np.isfinite(v)]
            if len(v):
                AG[arm][k] = dict(mean=float(v.mean()), min=float(v.min()), max=float(v.max()), n=int(len(v)))
    return AG


def deltas(FL, RUNS):
    T = {(a, s): t for a, s, t in RUNS}
    DL = {}
    for am, rf in (("m2", "base"), ("m2_fee0", "base_fee0")):
        ss = [s for s in SEEDS if (am, s) in T and (rf, s) in T]
        if not ss:
            continue
        DL[am] = dict(seeds=ss)
        for k in sorted(set.intersection(*[set(FL[T[(am, s)]]) & set(FL[T[(rf, s)]]) for s in ss])):
            v = np.array([FL[T[(am, s)]][k] - FL[T[(rf, s)]][k] for s in ss], float)
            v = v[np.isfinite(v)]
            if len(v):
                DL[am][k] = dict(mean=float(v.mean()), min=float(v.min()), max=float(v.max()),
                                 npos=int((v > 0).sum()), nneg=int((v < 0).sum()), n=int(len(v)))
    return DL


DEFS = [
    "Nguồn: printDone.csv + result.json của run + nến 1m ticker (`/home/ubuntu/kaggle_data_hpo`, jbin). Không đọc `ho26-*`.",
    "Equity MTM phút = thước `nsel_score_b`: pnl realized ghi tại phút `end` + unrealized q·(close1m − entry), q = margin/entry; "
    "cửa sổ 2022-01-01 00:00 → 2025-12-31 23:59 (+07); CAGR22 = (E_cuối/E_đầu)^(1/4) − 1 (1461 ngày / 365,25).",
    "Return ngày = equity MTM 23:59 +07 / ngày trước − 1; Sharpe = mean/sd·√365, Sortino = mean/√mean(min(r,0)²)·√365, rf = 0; "
    "vol = sd·√365; skew/kurtosis dư (scipy) trên 1461 return ngày.",
    "Tuần = tuần ISO đủ 7 ngày (+07) 2022-01-03 → 2025-12-28 (208 tuần), năm của tuần = năm của thứ Hai; tháng = 48 tháng dương lịch. "
    "Tuần 'bằng 0' = |ΔE tuần| < 1e-6·E0 (không có vị thế cả tuần).",
    "maxDD = equity MTM phút, đỉnh reset đầu cửa sổ; UW dài nhất = chuỗi phút equity < đỉnh trước dài nhất (ngày); "
    "hồi DD lớn nhất = từ đáy (và từ đỉnh) tới phút đầu tiên equity ≥ đỉnh trước DD.",
    "Lệnh vào = dòng printDone có start trong cửa sổ (mọi loại chân); leg0 = chân đầu cụm (sym, end) (= nsel_p0_data.load).",
    "Có vị thế = ≥ 1 chân mở (start ≤ phút < end). Vị thế đồng thời = số cụm (sym, end) đang mở. "
    "U = Σ notional chân mở (quantity·entry, 1x) / equity MTM phút.",
    "Khoảng trống = chuỗi ngày (+07) liên tiếp không có lệnh vào (mọi chân). Đợt = cụm ngày có lệnh, tách khi ≥ 3 ngày liền "
    "không lệnh vào; PnL đợt = Σ pnl realized của lệnh vào trong đợt; % top-3 đợt chia cho Σ pnl lệnh vào trong cửa sổ.",
    "Tập trung ngày: % của ΣΔequity MTM ngày (net cả cửa sổ) đến từ top-k ngày; Gini trên max(ΔE ngày, 0) qua 1461 ngày.",
    "Đặc tính lệnh = dòng printDone có end trong cửa sổ (mọi chân); % = pnl/margin; expectancy = mean pnl/margin; "
    "time-stop = giữ ≥ 168h; lỗ đơn lệnh % vốn = pnl / equity MTM phút trước lúc vào; "
    "MAE = min(low 1m, phút s+1..e−1)/entry − 1 (entry stress đã gồm phạt), chỉ lệnh vào và đóng trong cửa sổ.",
    "Benchmark: close 1m BTCUSDT/ETHUSDT cùng nguồn ticker, ffill; 50/50 = 50% BTC + 50% tiền mặt, rebalance 00:00 +07 ngày 1 "
    "mỗi tháng; không phí, không funding.",
    "Tương quan = Pearson return ngày (+07) strategy vs BTC, toàn kỳ và chỉ các ngày BTC < −5%.",
    "Stress = phạt giá vào 1,675% khi nến 1m quyết định ≤ −1% (in-sim, nsel-nen/nsel-m2); phí gốc = phạt 0 (gqsf / nsel-m2b).",
    "Số trình bày = mean [min..max] qua seed. Không bootstrap, không inflate, không luật; đây là mô tả, không phải đo lever.",
]

R1 = [("cagr", "CAGR22 %", 2), ("maxdd", "maxDD MTM phút %", 2), ("calmar", "Calmar", 3),
      ("sharpe", "Sharpe ngày (×√365)", 2), ("sortino", "Sortino ngày (×√365)", 2), ("vol", "Vol năm hoá %", 1),
      ("worst_day", "Ngày tệ nhất %", 2), ("worst_week", "Tuần ISO tệ nhất %", 2), ("worst_month", "Tháng tệ nhất %", 2),
      ("uw_max_d", "UW dài nhất (ngày)", 0), ("rec_trough_d", "Hồi DD lớn nhất: đáy → đỉnh cũ (ngày)", 0),
      ("rec_peak_d", "Hồi DD lớn nhất: đỉnh → hồi (ngày)", 0), ("skew", "Skew return ngày", 2),
      ("kurt", "Kurtosis dư return ngày", 1), ("pct_week_pos", "% tuần dương", 1), ("pct_month_pos", "% tháng dương", 1),
      ("roi.2022", "ROI 2022 %", 1), ("roi.2023", "ROI 2023 %", 1), ("roi.2024", "ROI 2024 %", 1), ("roi.2025", "ROI 2025 %", 1)]
R2 = [("cov.n_entries_y", "Lệnh vào/năm (mọi chân)", 0), ("cov.n_leg0_y", "Leg0/năm", 0),
      ("cov.pct_day_entry_all", "% ngày có ≥1 lệnh vào (mọi chân)", 1), ("cov.pct_day_entry_leg0", "% ngày có ≥1 leg0", 1),
      ("cov.pct_week_entry", "% tuần có ≥1 lệnh vào", 1), ("cov.pct_week_entry_leg0", "% tuần có ≥1 leg0", 1),
      ("cov.pct_month_entry", "% tháng có ≥1 lệnh vào", 1), ("cov.pct_time_pos", "% thời gian (phút) có vị thế", 1),
      ("cov.pct_day_pos", "% ngày có vị thế mở", 1), ("cov.pos_mean", "Vị thế (cụm) đồng thời TB, mọi phút", 2),
      ("cov.pos_mean_inpos", "Vị thế đồng thời TB khi có vị thế", 2), ("cov.pos_p95_inpos", "Vị thế đồng thời p95 khi có vị thế", 0),
      ("cov.pos_max", "Vị thế đồng thời max", 0), ("cov.legs_max", "Chân mở đồng thời max", 0),
      ("cov.U_mean_inpos", "U TB khi có vị thế (% equity)", 1), ("cov.U_p95_inpos", "U p95 khi có vị thế %", 1),
      ("cov.U_max", "U max %", 1), ("cov.gap_max", "Khoảng trống dài nhất không lệnh vào (ngày)", 0),
      ("cov.gap_p50", "Khoảng trống p50 (ngày)", 1), ("cov.gap_p90", "Khoảng trống p90 (ngày)", 1),
      ("cov.n_gap", "Số khoảng trống", 0), ("cov.ep_per_year", "Đợt/năm (tách ≥ 3 ngày yên)", 1),
      ("cov.trades_per_ep", "Lệnh/đợt TB", 1), ("cov.ep_len_mean", "Độ dài đợt TB (ngày)", 1),
      ("cov.wk_trades_p25", "Lệnh/tuần p25", 0), ("cov.wk_trades_p50", "Lệnh/tuần p50", 0),
      ("cov.wk_trades_p75", "Lệnh/tuần p75", 0), ("cov.wk_trades_max", "Lệnh/tuần max", 0),
      ("pct_week_pos", "% tuần PnL MTM dương", 1), ("pct_week_neg", "% tuần âm", 1), ("pct_week_zero", "% tuần bằng 0", 1),
      ("pct_month_pos", "% tháng dương", 1), ("cov.top5_share", "% ΣPnL MTM từ top-5 ngày", 1),
      ("cov.top10_share", "% ΣPnL MTM từ top-10 ngày", 1), ("cov.top20_share", "% ΣPnL MTM từ top-20 ngày", 1),
      ("cov.top3ep_share", "% ΣPnL realized từ top-3 đợt", 1), ("cov.gini_gain", "Gini lãi ngày (max(ΔE,0))", 3)]
RY = [("n_entries", "Lệnh vào", 0), ("pct_day_entry_all", "% ngày có lệnh vào", 1),
      ("pct_day_entry_leg0", "% ngày có leg0", 1), ("pct_week_entry", "% tuần có lệnh vào", 1),
      ("pct_time_pos", "% thời gian có vị thế", 1), ("pct_day_pos", "% ngày có vị thế", 1),
      ("gap_max", "Khoảng trống dài nhất (ngày)", 0), ("n_ep", "Số đợt", 1), ("wk_trades_p50", "Lệnh/tuần p50", 1),
      ("pct_week_pos", "% tuần dương", 1), ("roi", "ROI năm %", 1)]
R4 = [("trd.n_closed_y", "Lệnh đóng/năm", 0), ("trd.win_rate", "Win rate %", 1),
      ("trd.avg_win_pct", "Avg win % margin", 2), ("trd.avg_loss_pct", "Avg loss % margin", 2),
      ("trd.avg_win_usd", "Avg win USD", 0), ("trd.avg_loss_usd", "Avg loss USD", 0),
      ("trd.payoff", "Payoff (avg win / avg loss tuyệt đối, USD)", 2), ("trd.expectancy_pct", "Expectancy %/lệnh (margin)", 3),
      ("trd.expectancy_usd", "Expectancy USD/lệnh", 1), ("trd.hold_p50_h", "Giữ p50 (giờ)", 1),
      ("trd.hold_p90_h", "Giữ p90 (giờ)", 1), ("trd.pct_timestop", "% chân giữ ≥ 168h (time-stop)", 1),
      ("trd.pct_timestop_leg0", "% leg0 giữ ≥ 168h", 1), ("trd.worst_loss_cap_pct", "Lỗ đơn lệnh tệ nhất % vốn", 2),
      ("trd.worst_loss_pct_margin", "Lỗ đơn lệnh tệ nhất % margin", 1), ("trd.mae_p10_pct", "MAE p10 %", 2),
      ("trd.mae_p50_pct", "MAE p50 %", 2), ("trd.mae_min_pct", "MAE tệ nhất %", 1)]
RC = [("corr.corr_full", "Tương quan ngày vs BTC (toàn kỳ)", 3), ("corr.corr_eth", "Tương quan ngày vs ETH", 3),
      ("corr.n_crash", "Số ngày BTC < −5%", 0), ("corr.corr_crash", "Tương quan, chỉ ngày BTC < −5%", 3),
      ("corr.mean_ret_crash", "Return TB những ngày BTC < −5% (%)", 2),
      ("corr.mean_btc_crash", "BTC TB những ngày đó (%)", 2)]
D5 = [("cagr", 1), ("maxdd", 1), ("calmar", 1), ("sharpe", 1), ("sortino", 1), ("vol", -1), ("worst_day", 1),
      ("worst_week", 1), ("worst_month", 1), ("uw_max_d", -1), ("pct_week_pos", 1), ("pct_month_pos", 1),
      ("cov.n_entries_y", 0), ("cov.pct_day_entry_all", 1), ("cov.pct_day_entry_leg0", 1), ("cov.pct_week_entry", 1),
      ("cov.pct_month_entry", 1), ("cov.pct_time_pos", 0), ("cov.U_mean_inpos", 0), ("cov.gap_max", -1),
      ("cov.ep_per_year", 0), ("cov.wk_trades_p50", 1), ("pct_week_zero", -1), ("cov.top10_share", -1),
      ("cov.gini_gain", -1), ("trd.win_rate", 1), ("trd.payoff", 1), ("trd.expectancy_pct", 1),
      ("trd.worst_loss_cap_pct", 1), ("trd.mae_p10_pct", 1), ("corr.corr_full", -1), ("corr.mean_ret_crash", 1)]


def F(x, nd=2):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "—"
    return (("%." + str(nd) + "f") % x).replace(".", ",")


def A(ag, k, nd=2):
    x = ag.get(k)
    return "—" if not x else "%s [%s..%s]" % (F(x["mean"], nd), F(x["min"], nd), F(x["max"], nd))


def write_md(js, path):
    AG, DL, CK = js["agg"], js["delta"], js["checks"]
    BF = {n: flat(v) for n, v in js["bench"].items()}
    LB = {k: lb for k, lb, _ in R1 + R2 + R4 + RC}
    ND = {k: nd for k, _, nd in R1 + R2 + R4 + RC}
    b, m = AG.get("base", {}), AG.get("m2", {})
    nb = len([1 for r in js["runs"] if r[0] == "base"])
    nm2 = len([1 for r in js["runs"] if r[0] == "m2"])
    o = ["# Độ phủ lệnh & lợi nhuận/rủi ro: M2 vs baseline (DEV 2022–2025)", "",
         "2026-10-09. Phân tích khách quan, KHÔNG luật, KHÔNG vòng GO. Script `research/analysis/coverage_m2_base.py`, "
         "JSON `docs/audit/COVERAGE_M2_BASE_20261009.json`. Chỉ run DEV có sẵn (sim_end 2025-12-31); KHÔNG mở `ho26-*`; "
         "0 sim / 0 Kaggle / 0 Java / 0 chạm 242." + (" **QUICK TEST — số không dùng.**" if CK.get("quick") else ""), "",
         "- Baseline = K24 + skipFull (`nsel-nen-s*`, %d seed); M2 = K24 + skipFull + NSEL M2 (`nsel-m2-s*`, %d seed); "
         "bản stress in-sim 1,675%% là chính. Phụ phí gốc: `gqsf-*` / `nsel-m2b-*`." % (nb, nm2),
         "- Số = mean [min..max] qua seed " + ", ".join(str(s) for s in SEEDS) + ".", "",
         "## Định nghĩa / phương pháp", ""] + ["- " + x for x in js["definitions"]] + [""]
    o += ["## 1. Lợi nhuận / rủi ro (stress; cửa sổ 2022-01-01 → 2025-12-31 +07)", "",
          "| chỉ số | Baseline | M2 | BTC B&H | ETH B&H | 50% BTC + 50% cash |", "|---|---|---|---|---|---|"]
    for k, lb, nd in R1:
        o.append("| %s | %s | %s | %s | %s | %s |" % (lb, A(b, k, nd), A(m, k, nd), F(BF["BTC"].get(k), nd),
                                                    F(BF["ETH"].get(k), nd), F(BF["BTC50"].get(k), nd)))
    unr = {a: [r["tag"] for r in js["res"].values() if r["arm"] == a and r.get("rec_trough_d") is None] for a in ("base", "m2")}
    o += ["", "DD lớn nhất chưa hồi tới cuối cửa sổ: baseline %s; M2 %s; benchmark %s." % (
        ", ".join(unr["base"]) or "không", ", ".join(unr["m2"]) or "không",
        ", ".join(n for n in js["bench"] if js["bench"][n].get("rec_trough_d") is None) or "không"), ""]
    o += ["## 2. Độ phủ lệnh (stress)", "", "| chỉ số | Baseline | M2 |", "|---|---|---|"]
    for k, lb, nd in R2:
        o.append("| %s | %s | %s |" % (lb, A(b, k, nd), A(m, k, nd)))
    o += ["", "### 2b. Theo năm (mean qua seed: Baseline / M2)", "", "| chỉ số | 2022 | 2023 | 2024 | 2025 |",
          "|---|---|---|---|---|"]
    for k, lb, nd in RY:
        cells = []
        for y in YEARS:
            kk = "roi.%d" % y if k == "roi" else "cov.yr.%d.%s" % (y, k)
            cells.append("%s / %s" % (F((b.get(kk) or {}).get("mean"), nd), F((m.get(kk) or {}).get("mean"), nd)))
        o.append("| %s | %s |" % (lb, " | ".join(cells)))
    o.append("| ROI BTC B&H %% | %s |" % " | ".join(F(BF["BTC"].get("roi.%d" % y), 1) for y in YEARS))
    o += ["", "## 3. Tương quan với BTC (return ngày +07)", "", "| chỉ số | Baseline | M2 | ETH B&H | 50/50 |",
          "|---|---|---|---|---|"]
    for k, lb, nd in RC:
        o.append("| %s | %s | %s | %s | %s |" % (lb, A(b, k, nd), A(m, k, nd), F(BF["ETH"].get(k), nd),
                                              F(BF["BTC50"].get(k), nd)))
    o += ["", "## 4. Đặc tính lệnh (stress; lệnh đóng trong cửa sổ, mọi chân)", "", "| chỉ số | Baseline | M2 |", "|---|---|---|"]
    for k, lb, nd in R4:
        o.append("| %s | %s | %s |" % (lb, A(b, k, nd), A(m, k, nd)))
    d2 = DL.get("m2", {})
    o += ["", "## 5. M2 − Baseline ghép cặp theo seed (stress)", "",
          "| chỉ số | Δ mean | Δ [min..max] | seed M2 tốt hơn |", "|---|---|---|---|"]
    for k, dr in D5:
        x = d2.get(k)
        if not x:
            continue
        nd = ND.get(k, 2)
        bt_ = ("%d/%d" % (x["npos"] if dr > 0 else x["nneg"], x["n"])) if dr else "trung tính (Δ>0: %d/%d)" % (x["npos"], x["n"])
        o.append("| %s | %s | [%s..%s] | %s |" % (LB.get(k, k), F(x["mean"], nd), F(x["min"], nd), F(x["max"], nd), bt_))
    o += ["", "## 6. Phụ: bản phí gốc (phạt 0)", ""]
    for arm, nm_ in (("base_fee0", "Baseline gqsf"), ("m2_fee0", "M2 nsel-m2b")):
        g = AG.get(arm)
        if g:
            o.append("- %s (%d seed): CAGR %s; maxDD %s; Calmar %s; Sharpe %s; %% ngày có lệnh %s; %% thời gian có vị thế %s; "
                     "%% tuần dương %s." % (nm_, g["cagr"]["n"], A(g, "cagr"), A(g, "maxdd"), A(g, "calmar", 3), A(g, "sharpe"),
                                            A(g, "cov.pct_day_entry_all", 1), A(g, "cov.pct_time_pos", 1), A(g, "pct_week_pos", 1)))
    df = DL.get("m2_fee0")
    if df:
        o.append("- M2 − Baseline phí gốc ghép cặp seed %s: ΔCAGR %s, ΔmaxDD %s, ΔCalmar %s, Δ%% ngày có lệnh %s, ΔSharpe %s." % (
            df["seeds"], F(df["cagr"]["mean"]), F(df["maxdd"]["mean"]), F(df["calmar"]["mean"], 3),
            F(df["cov.pct_day_entry_all"]["mean"], 1), F(df["sharpe"]["mean"])))
    sc, pa = CK["selfcheck_B"], CK["parity_A"]
    o += ["", "## 7. Tự kiểm", "",
          "- Thước MTM phút vs scorer B (`docs/result/NSEL_RESULT_B.json`): %d run, max |ΔCAGR22| = %s pp, "
          "max |ΔmaxDD22| = %s pp." % (sc["n"], F(sc["max_abs_dcagr"], 6), F(sc["max_abs_ddd"], 6)),
          "- Equity MTM cuối cửa sổ vs result.json equity_final: max |lệch| = %s%% (chân mở qua cuối cửa sổ)."
          % F(CK["max_abs_eq_dev_pct"], 4),
          "- Phút-chân thiếu giá (ffill/entry): %s%%; ngày thiếu file ticker: %d; phút thiếu giá BTC/ETH (trước ffill): %s."
          % (F(100 * CK["miss_frac"], 4), CK["build"]["nofile"], CK["bench_missing_min"]),
          "- Parity scorer A (`docs/result/NSEL_RESULT_A.json`) cho run dùng: %d/%d PASS%s." % (
              sum(1 for v in pa.values() if v is True), len(pa),
              "" if all(v is True for v in pa.values()) else " (khác: " + ", ".join(
                  "%s %s (queue %s)" % (t, v, CK.get("queue_parity", {}).get(t)) for t, v in pa.items() if v is not True) + ")"),
          "- Dòng printDone bị bỏ (thiếu số): %d." % sum(r["check"]["n_dropped"] for r in js["res"].values())]
    open(path, "w", encoding="utf-8").write("\n".join(o) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--quick", type=int, default=0, help="chi N ngay ticker dau (test pipeline), ghi ra WD")
    ap.add_argument("--from-cache", action="store_true")
    ap.add_argument("--md-only", action="store_true")
    a_ = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
    jout, mout = (WD + "/quick.json", WD + "/quick.md") if a_.quick else (JSON_OUT, MD_OUT)
    if a_.md_only:
        write_md(json.load(open(jout)), mout)
        return
    assert NDAY == 1461 and WK_E[-1] == 1457 and DAYS[WK_S[0] + 1].dayofweek == 0 and len(ME) == 48 and len(MSI) == 49
    os.makedirs(WD, exist_ok=True)
    RUNS = runs_list()
    D, RJ, DROP = {}, {}, {}
    for _, _, t in RUNS:
        D[t], DROP[t] = load(t)
        RJ[t] = json.load(open(OUT + t + "/result.json"))
        log.info("%-16s n=%d (bo %d) n_result=%s date_last=%s ok=%s", t, len(D[t]), DROP[t], RJ[t].get("n_trades"),
                 RJ[t].get("date_last"), RJ[t].get("ok"))
    cache = WD + "/U_cache.npz"
    if a_.from_cache and os.path.exists(cache):
        z = np.load(cache)
        U, bt, et, mae, chk = z["U"].astype(float), z["bt"], z["et"], z["mae"], json.loads(str(z["chk"]))
    else:
        wait_lock()
        U, bt, et, mae, chk = build(RUNS, D, a_.workers, a_.quick)
        if not a_.quick:
            np.savez(cache, U=U.astype(np.float32), bt=bt, et=et, mae=mae, chk=json.dumps(chk))
    log.info("build xong %s", chk)
    BM, RB, bmiss = bench(bt, et)
    RES, FL, DR, off = {}, {}, {}, 0
    for ri, (a, s, t) in enumerate(RUNS):
        d = D[t]
        mr = mae[off:off + len(d)]
        off += len(d)
        eq = equity(d, RJ[t], U[ri])
        m, r, Ed, wk, wz = riskm(eq)
        m["cov"] = coverage(d, eq, Ed, wk, wz)
        m["trd"] = trades(d, eq, mr)
        m["corr"] = corr(r, RB["BTC"], RB["ETH"])
        ef = float(RJ[t]["equity_final"])
        m["check"] = dict(eq_result=ef, eq_dev_pct=100 * (float(eq[-1]) / ef - 1), n_rows=len(d), n_dropped=DROP[t],
                          n_result=RJ[t].get("n_trades"), date_last=RJ[t].get("date_last"))
        RES[t] = dict(arm=a, seed=s, tag=t, **m)
        FL[t] = flat(m)
        DR[t] = r
        log.info("%-16s CAGR %.2f DD %.2f Cal %.3f Sh %.2f ngay-co-lenh %.1f%% tg-vi-the %.1f%% devEq %.4f%%", t, m["cagr"],
                 m["maxdd"], m["calmar"] or 0, m["sharpe"] or 0, m["cov"]["pct_day_entry_all"], m["cov"]["pct_time_pos"],
                 m["check"]["eq_dev_pct"])
    np.savez_compressed(WD + "/daily_ret%s.npz" % ("_quick" if a_.quick else ""),
                        **{t.replace("-", "_"): DR[t] for t in DR}, BTC=RB["BTC"], ETH=RB["ETH"], BTC50=RB["BTC50"])
    sc = dict(n=0, max_abs_dcagr=0.0, max_abs_ddd=0.0, rows=[])
    if os.path.exists(B_JSON):
        for row in json.load(open(B_JSON))["rows"]:
            t = row["tag"]
            if t in RES:
                dc, dd = RES[t]["cagr"] - row["cagr22"], RES[t]["maxdd"] - row["maxdd22"]
                sc["n"] += 1
                sc["max_abs_dcagr"] = max(sc["max_abs_dcagr"], abs(dc))
                sc["max_abs_ddd"] = max(sc["max_abs_ddd"], abs(dd))
                sc["rows"].append([t, dc, dd])
    par = {}
    if os.path.exists(A_JSON):
        pa = json.load(open(A_JSON))["parity"]
        par = {t: ("THIEU_LUC_CHAM_A" if pa[t].get("missing") else bool(pa[t]["ok"])) for t in RES if t in pa}
    qp = "/home/ubuntu/claude_master/1008/nsel_impl/queue_status.tsv"
    qs = {}
    if os.path.exists(qp):
        for ln in open(qp).read().splitlines()[1:]:
            f = ln.split("\t")
            if len(f) >= 7:
                qs[f[1].rstrip("/").split("/")[-1]] = f[6]
    par = {t: (v if v is not True or t not in qs else True) for t, v in par.items()}
    queue = {t: qs.get(t) for t in RES}
    checks = dict(build=chk, miss_frac=chk["miss"] / max(1, chk["legmin"]), bench_missing_min=bmiss, selfcheck_B=sc,
                  parity_A=par, queue_parity=queue, max_abs_eq_dev_pct=max(abs(RES[t]["check"]["eq_dev_pct"]) for t in RES), quick=a_.quick)
    log.info("TU KIEM vs scorer B: %s", {k: v for k, v in sc.items() if k != "rows"})
    js = dict(runs=RUNS, definitions=DEFS, checks=checks, bench=BM, res=RES, agg=aggregate(FL, RUNS),
              delta=deltas(FL, RUNS))
    js = json.loads(json.dumps(js, default=float))
    json.dump(js, open(jout, "w"), indent=1, ensure_ascii=False)
    write_md(js, mout)
    if not a_.quick and os.path.exists(cache):
        os.remove(cache)
    log.info("XONG %s", mout)


if __name__ == "__main__":
    main()
