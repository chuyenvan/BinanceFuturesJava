#!/usr/bin/env python3
"""RESET_RULE_P3 (D5) — DO BEN UNG VIEN R4 vs B*, 4 test.

Thuc thi DUNG docs/prereg/PREREG_RESET_RULE_P3.md (chot TRUOC khi tinh so; commit `6119188`).

THUAN PYTHON OFFLINE. KHONG Java/sim, KHONG train, KHONG 2026, KHONG push du lieu.
Doi tuong: R4 (p2-r4-base / p2-r4-stress) vs B*=R0 (p2-r0-base / p2-r0-stress).
  T1 episode jackknife (bo top-1/3/5)
  T2 bootstrap cum episode 5000 rep seed 20260928 (CI Calmar + CI chenh R4-B*)
  T3 DSR (V[SR] tu run DEV cung cua so)
  T4 placebo 'cung phut vao, coin ngau nhien' (harness exit RESULT_EXIT_FIT)

Usage:
  python3 reset_rule_p3.py t123 [--json OUT.json]
  python3 reset_rule_p3.py t4   [--json OUT.json] [--draws 200] [--workers 4]
  python3 reset_rule_p3.py t4prep                  # build cache nen 1m (ngoai repo)
"""
import argparse
import gzip
import json
import math
import os
import pickle
import re
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reset_rule_score as R  # noqa: E402

KOUT = "/home/ubuntu/kaggle_sim/out"
TICKER = "/home/ubuntu/kaggle_data_hpo"
CACHE = "/home/ubuntu/rr_p3_cache"
NREP_BOOT = 5000
SEED_BOOT = 20260928
NREP_CI = 2000
SEED_CI = 20260905
BLOCK_H = 72
DAY0 = pd.Timestamp("20210701")
CAP0 = 35000.0

ARMS = {"R4": "p2-r4", "Bstar": "p2-r0"}


def tag(arm, cost):
    return "%s-%s" % (ARMS[arm], cost)


# =============================================================== T1
def build_episodes(d):
    """tra list[set(day)] — episode = ngay-vao lien tiep cach <=2 ngay trong."""
    days = pd.Series(d["ts"].dt.normalize().drop_duplicates().sort_values().to_numpy())
    vals = days.to_numpy()
    eps, cur = [], [vals[0]]
    for x in vals[1:]:
        if (x - cur[-1]) / np.timedelta64(1, "D") > 2:
            eps.append(cur)
            cur = [x]
        else:
            cur.append(x)
    eps.append(cur)
    return [set(e) for e in eps]


def _equity(d, mask, span_days):
    """duong equity ngay dung lai: 35000 + cumΣpnl theo ngay RA lenh; tra (eq_final, maxdd_pct)."""
    dd = d[mask]
    if len(dd) == 0:
        return CAP0, 0.0
    te = dd["te"].dt.normalize()
    g = dd.groupby(te)["pnl"].sum().sort_index()
    eq = CAP0 + g.cumsum()
    ddv = (eq / eq.cummax() - 1) * 100.0
    return float(eq.iloc[-1]), float(ddv.min())


def episode_jackknife(d, span_days):
    eps = build_episodes(d)
    day2ep = {}
    for i, e in enumerate(eps):
        for x in e:
            day2ep[x] = i
    leg_ep = np.array([day2ep.get(np.datetime64(x), -1) for x in d["ts"].dt.normalize().to_numpy()])
    ap = d["pnl"].to_numpy(float)
    ep_sum = np.array([ap[leg_ep == i].sum() for i in range(len(eps))])
    order = np.argsort(-ep_sum)
    tot = float(ap.sum())
    outp = {"n_ep": len(eps), "sum_pnl": tot}
    for k in (1, 3, 5, 10):
        top = set(order[:k].tolist())
        m = ~np.isin(leg_ep, list(top))
        rem = float(ap[m].sum())
        eqf, mdd = _equity(d, m, span_days)
        cagr = ((eqf / CAP0) ** (1 / span_days) - 1) * 100 if span_days > 0 else float("nan")
        cal = cagr / abs(mdd) if mdd != 0 else float("nan")
        outp["drop%d" % k] = dict(pct_top=float(100.0 * ep_sum[order[:k]].sum() / tot) if tot else float("nan"),
                                  sum_pnl_rem=rem, cagr_rem=float(cagr), maxdd_rem=mdd, calmar_rem=float(cal))
    return outp


# =============================================================== T2
def _block_days(eps, d_end):
    """so NGAY LICH cua moi khoi = [ngay dau episode i, ngay dau episode i+1 - 1]; khoi cuoi toi d_end."""
    starts = [min(e) for e in eps]
    out = []
    for i, s in enumerate(starts):
        nxt = starts[i + 1] if i + 1 < len(starts) else np.datetime64(d_end) + np.timedelta64(1, "D")
        out.append(max(1, int((nxt - s) / np.timedelta64(1, "D"))))
    return np.array(out, float)


def boot_one(d, d_end, nrep=NREP_BOOT, seed=SEED_BOOT, order="draw"):
    """resample cum episode: tra dict cac mang Σpnl_rep, CAGR_rep, Calmar_rep.
    order='draw' (chot truoc: theo thu tu rut) | 'orig' (AMENDMENT 1: xep lai theo chi so khoi goc)."""
    eps = build_episodes(d)
    day2ep = {}
    for i, e in enumerate(eps):
        for x in e:
            day2ep[x] = i
    leg_day = d["ts"].dt.normalize().to_numpy()
    leg_ep = np.array([day2ep.get(np.datetime64(x), -1) for x in leg_day])
    ap = d["pnl"].to_numpy(float)
    K = len(eps)
    bk_days = _block_days(eps, d_end)   # so NGAY LICH moi khoi
    bpnl = np.array([ap[leg_ep == i].sum() for i in range(K)])
    rng = np.random.default_rng(seed)
    sums = np.empty(nrep)
    cagrs = np.empty(nrep)
    cals = np.empty(nrep)
    for r in range(nrep):
        pick = rng.integers(0, K, size=K)
        if order == "orig":
            pick = np.sort(pick)
        p = bpnl[pick]
        # duong tuan tu theo thu tu kh oi
        eq = CAP0 + np.cumsum(p)
        peak = np.maximum.accumulate(np.concatenate(([CAP0], eq)))
        ddv = (np.concatenate(([CAP0], eq)) / peak - 1) * 100.0
        mdd = float(ddv.min())
        s = float(p.sum())
        ndays = float(bk_days[pick].sum())
        cagr = ((CAP0 + s) / CAP0) ** (365.25 / ndays) - 1 if ndays > 0 and (CAP0 + s) > 0 else -1.0
        sums[r] = s
        cagrs[r] = cagr * 100
        cals[r] = (cagr * 100) / abs(mdd) if mdd != 0 else np.nan
    return dict(sum=sums, cagr=cagrs, calmar=cals)


def boot_pair(dr, db, d_end, nrep=NREP_BOOT, seed=SEED_BOOT, order="draw"):
    """paired tren luoi khoi CHUNG (episode cua HOP ngay-vao 2 arm)."""
    both = pd.concat([dr[["ts"]], db[["ts"]]], ignore_index=True)
    eps = build_episodes(both)
    day2ep = {}
    for i, e in enumerate(eps):
        for x in e:
            day2ep[x] = i
    K = len(eps)
    blk_days = _block_days(eps, d_end)   # SO NGAY LICH moi khoi

    def prep(d):
        ld = d["ts"].dt.normalize().to_numpy()
        le = np.array([day2ep.get(np.datetime64(x), -1) for x in ld])
        ap = d["pnl"].to_numpy(float)
        return np.array([ap[le == i].sum() for i in range(K)])
    br = prep(dr)
    bb = prep(db)
    rng = np.random.default_rng(seed)
    out = np.empty((nrep, 6))   # cal_r, cal_b, sum_r, sum_b, cagr_r, cagr_b
    for r in range(nrep):
        pick = rng.integers(0, K, size=K)
        if order == "orig":
            pick = np.sort(pick)
        ndays = float(blk_days[pick].sum())
        vals = []
        for b in (br, bb):
            p = b[pick]
            eq = CAP0 + np.cumsum(p)
            peak = np.maximum.accumulate(np.concatenate(([CAP0], eq)))
            ddv = (np.concatenate(([CAP0], eq)) / peak - 1) * 100.0
            mdd = float(ddv.min())
            s = float(p.sum())
            cagr = (((CAP0 + s) / CAP0) ** (365.25 / ndays) - 1) if ndays > 0 and (CAP0 + s) > 0 else -1.0
            vals += [((cagr * 100) / abs(mdd) if mdd != 0 else np.nan), s, cagr * 100]
        out[r] = [vals[0], vals[3], vals[1], vals[4], vals[2], vals[5]]
    return dict(cal=out[:, 0] - out[:, 1], sum=out[:, 2] - out[:, 3], cagr=out[:, 4] - out[:, 5],
                cal_r=out[:, 0], cal_b=out[:, 1], K=K)


def ci95(a, lo=2.5, hi=97.5):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    return (float(np.percentile(a, lo)), float(np.percentile(a, hi))) if len(a) else (float("nan"), float("nan"))


# =============================================================== T3
RX = R.RX_DAILY


def load_daily_dir(root):
    p = os.path.join(root, "logs", "sim.out")
    pf = p
    if not os.path.exists(pf):
        pg = p + ".gz"
        if os.path.exists(pg):
            opener = lambda: gzip.open(pg, "rt", errors="ignore")
        else:
            return None
    else:
        opener = lambda: open(p, errors="ignore")
    rows = []
    with opener() as fh:
        for line in fh:
            m = RX.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)), int(m.group(3))))
    if not rows:
        return None
    e = pd.DataFrame(rows, columns=["d", "b", "unP"]).drop_duplicates("d", keep="last")
    e["t"] = pd.to_datetime(e["d"], format="%Y%m%d")
    return e.set_index("t").sort_index()["b"].add(e.set_index("t").sort_index()["unP"])


def pool_runs():
    roots = []
    for base in ("/home/ubuntu/java/devrun", KOUT):
        if os.path.isdir(base):
            for nm in sorted(os.listdir(base)):
                p = os.path.join(base, nm)
                if os.path.isdir(p):
                    roots.append(p)
    out = {}
    for p in roots:
        eq = load_daily_dir(p)
        if eq is None or len(eq) < 1640:
            continue
        if eq.index[0].strftime("%Y%m%d") != "20210701" or eq.index[-1].strftime("%Y%m%d") != "20251230":
            continue
        out[p.split("/")[-1] if "devrun" in p else p.split("/")[-1]] = eq
    return out


def dsr_from_pool(pool, target_name, Ns=(5, 10, 50, 200, 448)):
    """pool: dict name->equity(day). tra dict ket qua DSR cho target_name."""
    from scipy.stats import norm, skew as _skew, kurtosis as _kurt
    names = list(pool.keys())
    rets = {}
    for nm in names:
        e = pool[nm].astype(float)
        rets[nm] = (e / e.shift(1) - 1).dropna()
    # SR ngay
    SR = {}
    for nm in names:
        r = rets[nm].to_numpy(float)
        r = r[np.isfinite(r)]
        SR[nm] = float(np.mean(r) / np.std(r, ddof=1)) if len(r) > 2 and np.std(r, ddof=1) > 0 else np.nan
    sr = np.array([SR[n] for n in names], float)
    sr = sr[np.isfinite(sr)]
    V = float(np.var(sr, ddof=1)) if len(sr) > 1 else float("nan")
    # rho trung binh ngoai duong cheo tren truc ngay chung
    R2 = pd.DataFrame(rets)
    C = R2.corr()
    n = C.shape[0]
    rho = float((C.to_numpy().sum() - n) / (n * (n - 1))) if n > 1 else float("nan")
    N = len(names)
    Neff = N / (1 + (N - 1) * rho) if rho > -1 else float("nan")
    r = rets[target_name].to_numpy(float)
    r = r[np.isfinite(r)]
    T = len(r)
    mu, sd = float(np.mean(r)), float(np.std(r, ddof=1))
    sr_t = mu / sd
    sk = float(_skew(r, bias=False))
    ku = float(_kurt(r, fisher=False, bias=False))
    g = 0.5772156649
    res = dict(N=N, rho=rho, Neff=float(Neff), V=float(V), T=T, SR=sr_t, SR_ann=sr_t * math.sqrt(365),
               skew=sk, kurt=ku)
    # PSR(SR0=0)
    psr = norm.cdf((sr_t - 0.0) * math.sqrt(T - 1) / math.sqrt(1 - sk * sr_t + (ku - 1) / 4 * sr_t ** 2))
    res["PSR0"] = float(psr)
    d = {}
    for Nx in list(Ns) + [round(float(Neff), 2)]:
        sr0 = math.sqrt(V) * ((1 - g) * norm.ppf(1 - 1.0 / Nx) + g * norm.ppf(1 - 1.0 / (Nx * math.e)))
        dsr = norm.cdf((sr_t - sr0) * math.sqrt(T - 1) / math.sqrt(1 - sk * sr_t + (ku - 1) / 4 * sr_t ** 2))
        d[str(Nx)] = dict(SR0=float(sr0), DSR=float(dsr))
    res["DSR"] = d
    return res


# =============================================================== main t123
def run_t123(json_out):
    log = []
    say = lambda s="": (log.append(str(s)), print(s, flush=True))
    say("=" * 70)
    say("RESET_RULE_P3 T1-T3 — R4 vs B* (base & stress)")
    legs, daily = {}, {}
    for arm in ARMS:
        for cost in ("base", "stress"):
            t = tag(arm, cost)
            legs[t] = R.load_legs(t)
            daily[t] = R.load_daily(t)
            say("%-14s n=%d eq=%.0f" % (t, len(legs[t]), daily[t]["equity"].iloc[-1]))
    res = {"prereg": "docs/prereg/PREREG_RESET_RULE_P3.md"}
    # ---- T1
    say("\n== T1 EPISODE JACKKNIFE ==")
    t1 = {}
    for arm in ARMS:
        for cost in ("base", "stress"):
            t = tag(arm, cost)
            d = legs[t]
            span = (daily[t].index[-1] - daily[t].index[0]).days / 365.25
            j = episode_jackknife(d, span)
            j["span_y"] = span
            t1[t] = j
            say("%-14s ne=%3d sum=%9.0f | top1=%.1f%% top3=%.1f%% top5=%.1f%% top10=%.1f%% | rem3=%.0f cal3=%.2f(maDD %.2f) rem5=%.0f"
                % (t, j["n_ep"], j["sum_pnl"], j["drop1"]["pct_top"], j["drop3"]["pct_top"],
                   j["drop5"]["pct_top"], j["drop10"]["pct_top"], j["drop3"]["sum_pnl_rem"],
                   j["drop3"]["calmar_rem"], j["drop3"]["maxdd_rem"], j["drop5"]["sum_pnl_rem"]))
    res["T1"] = t1
    # T1 verdict
    v1 = {}
    for cost in ("base", "stress"):
        r = t1[tag("R4", cost)]
        b = t1[tag("Bstar", cost)]
        ok = (r["drop3"]["sum_pnl_rem"] > 0 and r["drop5"]["sum_pnl_rem"] > 0
              and r["drop3"]["calmar_rem"] >= b["drop3"]["calmar_rem"])
        v1[cost] = dict(pass_=bool(ok), r4_cal3=r["drop3"]["calmar_rem"], bst_cal3=b["drop3"]["calmar_rem"])
    res["T1_verdict"] = v1
    say("T1 verdict: base=%s stress=%s" % (v1["base"]["pass_"], v1["stress"]["pass_"]))

    # ---- T2
    say("\n== T2 BOOTSTRAP CUM EPISODE (5000, seed 20260928) ==")
    t2 = {}
    d_end_common = daily[tag("R4", "base")].index[-1]
    for arm in ARMS:
        for cost in ("base", "stress"):
            t = tag(arm, cost)
            d = legs[t]
            de = daily[t].index[-1]
            bs = boot_one(d, de)
            c = ci95(bs["calmar"])
            sp = ci95(bs["sum"])
            t2[t] = dict(calmar_ci=c, calmar_mean=float(np.mean(bs["calmar"])),
                         sum_ci=sp, P_sum_le0=float(np.mean(bs["sum"] <= 0)),
                         cagr_ci=ci95(bs["cagr"]))
            say("%-14s Calmar CI [%.2f, %.2f] mean %.2f | P(sum<=0)=%.3f | Sum CI [%.0f, %.0f]"
                % (t, c[0], c[1], t2[t]["calmar_mean"], t2[t]["P_sum_le0"], sp[0], sp[1]))
    # paired diff (chot truoc: duong theo thu tu rut)
    t2p = {}
    t2p_amend = {}
    for cost in ("base", "stress"):
        tr, tb = tag("R4", cost), tag("Bstar", cost)
        de = daily[tr].index[-1]
        pr = boot_pair(legs[tr], legs[tb], de)
        dci = ci95(pr["cal"])
        t2p[cost] = dict(diff_mean=float(np.mean(pr["cal"])), diff_ci=dci, K=pr["K"],
                         diff_cagr=float(np.mean(pr["cagr"])), diff_cagr_ci=ci95(pr["cagr"]),
                         diff_sum=float(np.mean(pr["sum"])), diff_sum_ci=ci95(pr["sum"]),
                         r4_cal_ci=ci95(pr["cal_r"]), bst_cal_ci=ci95(pr["cal_b"]),
                         contains0=bool(dci[0] <= 0 <= dci[1]))
        # AMENDMENT 1 (post-hoc, chi de doc): xep khoi theo CHI SO GOC
        pa = boot_pair(legs[tr], legs[tb], de, order="orig")
        t2p_amend[cost] = dict(diff_cal=float(np.mean(pa["cal"])), diff_cal_ci=ci95(pa["cal"]),
                               contains0=bool(ci95(pa["cal"])[0] <= 0 <= ci95(pa["cal"])[1]),
                               r4_cal_ci=ci95(pa["cal_r"]), bst_cal_ci=ci95(pa["cal_b"]),
                               diff_cagr=float(np.mean(pa["cagr"])), diff_cagr_ci=ci95(pa["cagr"]),
                               diff_sum=float(np.mean(pa["sum"])), diff_sum_ci=ci95(pa["sum"]))
        say("PAIRED %-6s K=%d diff(R4-B*) Calmar mean %.2f CI [%.2f, %.2f] contains0=%s | CAGR diff %.3f CI [%.3f,%.3f]"
            % (cost, pr["K"], t2p[cost]["diff_mean"], dci[0], dci[1], t2p[cost]["contains0"],
               t2p[cost]["diff_cagr"], t2p[cost]["diff_cagr_ci"][0], t2p[cost]["diff_cagr_ci"][1]))
        say("  [AMEND.1 orig-order] %-6s diff Calmar mean %.2f CI [%.2f, %.2f] contains0=%s | R4 cal CI [%.2f,%.2f] B* [%.2f,%.2f]"
            % (cost, t2p_amend[cost]["diff_cal"], t2p_amend[cost]["diff_cal_ci"][0],
               t2p_amend[cost]["diff_cal_ci"][1], t2p_amend[cost]["contains0"],
               t2p_amend[cost]["r4_cal_ci"][0], t2p_amend[cost]["r4_cal_ci"][1],
               t2p_amend[cost]["bst_cal_ci"][0], t2p_amend[cost]["bst_cal_ci"][1]))
    res["T2"] = t2
    res["T2_pair"] = t2p
    res["T2_pair_amendment1_origorder"] = t2p_amend
    # amendment 1 cho don doi tuong
    t2a = {}
    for cost in ("base", "stress"):
        t = tag("R4", cost)
        de = daily[t].index[-1]
        bs = boot_one(legs[t], de, order="orig")
        t2a[t] = dict(calmar_ci=ci95(bs["calmar"]), calmar_mean=float(np.mean(bs["calmar"])),
                      cagr_ci=ci95(bs["cagr"]), sum_ci=ci95(bs["sum"]), P_sum_le0=float(np.mean(bs["sum"] <= 0)))
        say("  [AMEND.1 orig-order] %-14s Calmar CI [%.2f, %.2f] mean %.2f"
            % (t, t2a[t]["calmar_ci"][0], t2a[t]["calmar_ci"][1], t2a[t]["calmar_mean"]))
    res["T2_amendment1"] = t2a
    v2 = {c: dict(pass_=bool(t2[tag("R4", c)]["calmar_ci"][0] > 0)) for c in ("base", "stress")}
    res["T2_verdict"] = v2
    say("T2 verdict (CI Calmar R4 lo>0): base=%s stress=%s" % (v2["base"]["pass_"], v2["stress"]["pass_"]))

    # ---- T3
    say("\n== T3 DSR ==")
    pool = pool_runs()
    say("pool runs (cung cua so): %d" % len(pool))
    for t in (tag("R4", "base"), tag("Bstar", "base")):
        if t not in pool:
            pool[t] = daily[t]
    t3 = {}
    for t in (tag("R4", "base"), tag("Bstar", "base")):
        if t in pool:
            t3[t] = dsr_from_pool(pool, t)
            d = t3[t]
            say("%-14s SRd=%.4f (ann %.2f) T=%d N=%d Neff=%.1f rho=%.3f V=%.2e skew=%.2f kurt=%.1f PSR0=%.3f"
                % (t, d["SR"], d["SR_ann"], d["T"], d["N"], d["Neff"], d["rho"], d["V"], d["skew"], d["kurt"], d["PSR0"]))
            say("   DSR: " + " ".join("%s=%.3f" % (k, v["DSR"]) for k, v in d["DSR"].items()))
    res["T3"] = t3
    v3 = {}
    try:
        r4 = t3[tag("R4", "base")]
        v3["base"] = dict(pass_=bool(r4["DSR"][str(round(r4["Neff"], 2))]["DSR"] >= 0.95
                                    and r4["DSR"]["5"]["DSR"] >= 0.95))
        v3["base"]["DSR_Neff"] = r4["DSR"][str(round(r4["Neff"], 2))]["DSR"]
        v3["base"]["DSR_5"] = r4["DSR"]["5"]["DSR"]
    except Exception as ex:
        say("T3 verdict loi: %s" % ex)
    res["T3_verdict"] = v3
    say("T3 verdict: %s" % v3)

    with open(json_out, "w") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False, default=str)
    print("JSON ->", json_out)


def legs_ref_daily(arm):
    return R.load_daily(tag(arm, "base"))


# =============================================================== T4 (placebo)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "exitfit"))
import exit_engine as E  # noqa: E402

GMT7_MS = 7 * 3600000
DAY_MS = 86400000


def _day_str(ms):
    return time.strftime("%Y%m%d", time.gmtime(ms // 1000))


def _ticker_path(day_str):
    p = os.path.join(TICKER, "ticker_%s.bin.gz" % day_str)
    return p if os.path.exists(p) else None


def _syms_of_day(args):
    day_str = args
    p = _ticker_path(day_str)
    if p is None:
        return day_str, []
    import jbin
    with gzip.open(p, "rb") as g:
        b = g.read()
    syms = set()
    for k, v in jbin.iter_minutes(b):
        syms.update(v.keys())
    return day_str, sorted(syms)


def _stitch(day_bars, sym):
    """day_bars: list cac dict sym -> (ts int64[], ohlc (n,4)); tra (ts, ohlc) noi tiep."""
    ts, rows = [], []
    for bars in day_bars:
        a = bars.get(sym)
        if a is None:
            continue
        t, o = a
        if t is None or len(t) == 0:
            continue
        ts.append(t)
        rows.append(o)
    if not ts:
        return None, None
    return np.concatenate(ts), np.concatenate(rows)


def _sim_one(sym, t0, margin, pred, bars, tick_key):
    ts, ohlc = bars
    if ts is None:
        return None
    i0 = int(np.searchsorted(ts, t0))
    if i0 >= len(ts) or ts[i0] != t0:
        return None
    entry = float(ohlc[i0, 3])
    if not np.isfinite(entry) or entry <= 0:
        return None
    qty = margin / entry
    cl = {"cid": 0, "sym": tick_key, "end": int(ts[-1]),
          "legs": [{"ts": int(t0), "entry": entry, "qty": qty, "pnl": 0.0, "funding": 0.0,
                    "pred": pred, "status": "", "tp": 0.0, "profit": 0.0,
                    "level": "PREDICT_SYMBOL_TRADE"}]}
    r = E.simulate(cl, {0: (ts, ohlc)}, POL)
    if not r.get("ok"):
        return None
    tp = r["price_tp"]
    return float((tp - entry) / entry), (r["status"], r["reason"])


POL = E.make_p0()
GMT7_MS = 7 * 3600000
DAY_MS = 86400000
_G4 = {}


def _held_intervals(legs):
    d = {}
    tsms = (legs["ts"].astype("int64") // 10 ** 6).to_numpy() - GMT7_MS
    tems = (legs["te"].astype("int64") // 10 ** 6).to_numpy() - GMT7_MS
    for s, a, b in zip(legs["sym"].to_numpy(), tsms, tems):
        d.setdefault(s + "USDT", []).append((int(a), int(b)))
    return d


def _init4(g):
    _G4.update(g)


def _day_job(dk):
    import jbin
    G = _G4
    leg_idx = G["by_day"][dk]
    t0 = G["t0"]; syms = G["syms"]; preds = G["preds"]; margins = G["margins"]
    U = G["U"]; draws = G["draws"]; first = G["first"]; held = G["held"]
    ds = time.strftime("%Y%m%d", time.gmtime(dk * 86400))
    # --- day0 full + presence tai cac minute t0
    need_minutes = set(int(t0[i] // 60000) % 1440 for i in leg_idx)
    acc, pres = {}, {}
    pf = _ticker_path(ds)
    if pf:
        with gzip.open(pf, "rb") as g:
            b = g.read()
        for k, v in jbin.iter_minutes(b):
            mi = (k // 60000) % 1440
            for s, tup in v.items():
                st, hi, lo, cl, op, _vol = tup
                a = acc.get(s)
                if a is None:
                    a = acc[s] = [[], [], [], [], []]
                a[0].append(k); a[1].append(op); a[2].append(hi); a[3].append(lo); a[4].append(cl)
                if mi in need_minutes:
                    pres.setdefault(mi, []).append(s)
    day0 = {s: (np.asarray(a[0], np.int64), np.asarray(a[1:], np.float32).T) for s, a in acc.items()}
    # --- ung vien
    cand = {}
    for i in leg_idx:
        mi = int(t0[i] // 60000) % 1440
        real = syms[i]
        dl = time.strftime("%Y%m%d", time.gmtime((int(dk) - 30) * 86400))
        lst = []
        for s in pres.get(mi, []):
            if s == real:
                continue
            if first.get(s, "99999999") > dl:
                continue
            iv = held.get(s)
            if iv:
                bad = False
                for (a_, b_) in iv:
                    if a_ <= t0[i] < b_:
                        bad = True; break
                if bad:
                    continue
            lst.append(s)
        cand[i] = lst
    # --- forward bars
    need_syms = set(syms[i] for i in leg_idx)
    for i in leg_idx:
        need_syms.update(cand[i])
    allb = [day0]
    for j in range(1, 8):
        fs = time.strftime("%Y%m%d", time.gmtime((dk + j) * 86400))
        d = {}
        pp = _ticker_path(fs)
        if pp:
            with gzip.open(pp, "rb") as g:
                b = g.read()
            for k, v in jbin.iter_minutes(b):
                for s, tup in v.items():
                    if s not in need_syms:
                        continue
                    st, hi, lo, cl, op, _vol = tup
                    a = d.get(s)
                    if a is None:
                        a = d[s] = [[], [], [], [], []]
                    a[0].append(k); a[1].append(op); a[2].append(hi); a[3].append(lo); a[4].append(cl)
        allb.append({s: (np.asarray(a[0], np.int64), np.asarray(a[1:], np.float32).T) for s, a in d.items()})
    cache = {}

    def get(s):
        if s not in cache:
            cache[s] = _stitch(allb, s)
        return cache[s]
    # --- sim
    sims = 0
    sr = {}
    spl = {}
    res_real = {}
    res_plac = {}
    for i in leg_idx:
        real = syms[i]
        rr = _sim_one(real, int(t0[i]), margins[i], preds[i], get(real), real)
        sims += 1
        if rr:
            res_real[i] = rr[0]
            sr[rr[1]] = sr.get(rr[1], 0) + 1
        cs = cand[i]
        ncn = len(cs)
        if ncn == 0:
            continue
        idxs = np.minimum((U[i] * ncn).astype(int), ncn - 1)
        uniq = {}
        for j, ci in enumerate(idxs):
            uniq.setdefault(cs[ci], []).append(j)
        row = np.full(draws, np.nan)
        for s, js in uniq.items():
            rr = _sim_one(s, int(t0[i]), margins[i], preds[i], get(s), s)
            sims += 1
            if rr:
                for j in js:
                    row[j] = rr[0]
                spl[rr[1]] = spl.get(rr[1], 0) + 1
        res_plac[i] = row
    pickle.dump(dict(leg_idx=leg_idx, real=res_real, plac={int(k): v for k, v in res_plac.items()},
                     sr=sr, spl=spl, sims=sims), open(os.path.join(CACHE, "day_%d.pkl" % dk), "wb"), protocol=4)
    return dk


def run_t4(draws, workers, json_out, pilot=9999):
    say = lambda s="": print(s, flush=True)
    say("=" * 70)
    say("RESET_RULE_P3 T4 PLACEBO — R4 @base (cung phut vao, coin ngau nhien)")
    legs = R.load_legs(tag("R4", "base"))
    p = legs[legs["level"] == "PREDICT_SYMBOL_TRADE"].reset_index(drop=True)
    t0 = (p["ts"].astype("int64") // 10 ** 6).to_numpy() - GMT7_MS
    t0_day = (t0 // DAY_MS).astype(np.int64)
    n = len(p)
    say("leg PREDICT_SYMBOL_TRADE = %d | entry days = %d" % (n, len(set(t0_day.tolist()))))
    held = _held_intervals(legs)
    dmin = int(pd.Timestamp("2021-06-01").value // 10 ** 6) // DAY_MS
    dmax = int(t0_day.max())
    fs_path = "/home/ubuntu/rr_p3_first_seen.npy"
    if os.path.exists(fs_path):
        first = dict(np.load(fs_path, allow_pickle=True).tolist())
        say("first-seen [cache] %d symbol" % len(first))
    else:
        days_scan = [time.strftime("%Y%m%d", time.gmtime(d * 86400)) for d in range(dmin, dmax + 1)]
        say("first-seen scan: %d ngay" % len(days_scan))
        first = {}
        t_start = time.time()
        with Pool(workers) as pool:
            for i, (dsx, syms) in enumerate(pool.imap_unordered(_syms_of_day, days_scan, chunksize=8)):
                for s in syms:
                    if s not in first or dsx < first[s]:
                        first[s] = dsx
                if i % 200 == 0:
                    say("  scan %d/%d %.0fs" % (i, len(days_scan), time.time() - t_start))
        say("scan xong %d ngay, %d symbol, %.0fs" % (len(days_scan), len(first), time.time() - t_start))
        np.save(fs_path, np.array(sorted(first.items()), dtype=object), allow_pickle=True)
    rng = np.random.default_rng(SEED_BOOT)
    U = rng.random((n, draws))
    by_day = {}
    for i in range(n):
        by_day.setdefault(int(t0_day[i]), []).append(i)
    dkeys = sorted(by_day.keys())
    if pilot < len(dkeys):
        dkeys = dkeys[:pilot]
    os.makedirs(CACHE, exist_ok=True)
    say("chay %d/%d entry days, draws=%d" % (len(dkeys), len(by_day), draws))
    glob = dict(t0=t0, syms=(p["sym"] + "USDT").to_numpy(), preds=p["symbolPred"].to_numpy(float),
                margins=p["margin"].to_numpy(float), U=U, draws=draws, first=first, held=held, by_day=by_day)
    todo = [dk for dk in dkeys if not os.path.exists(os.path.join(CACHE, "day_%d.pkl" % dk))]
    say("  checkpoint: %d da co, %d can chay" % (len(dkeys) - len(todo), len(todo)))
    t_start = time.time()
    ndone = 0
    try:
        with Pool(workers, initializer=_init4, initargs=(glob,), maxtasksperchild=6) as pool:
            for dk in pool.imap_unordered(_day_job, todo):
                ndone += 1
                if ndone % 5 == 0:
                    say("  done %d/%d (day=%d) %.0fs" % (ndone, len(todo), dk, time.time() - t_start))
    except Exception as ex:
        say("!! LOI pool: %r — dung lai, se doc checkpoint da co" % (ex,))
    # ---- doc checkpoint
    net_real = {}
    net_plac = {}
    stat_real = {}
    stat_plac = {}
    sims_tot = 0
    nday = 0
    for dk in dkeys:
        pf = os.path.join(CACHE, "day_%d.pkl" % dk)
        if not os.path.exists(pf):
            continue
        r = pickle.load(open(pf, "rb"))
        nday += 1
        sims_tot += r["sims"]
        net_real.update(r["real"])
        net_plac.update(r["plac"])
        for k, v in r["sr"].items():
            stat_real[k] = stat_real.get(k, 0) + v
        for k, v in r["spl"].items():
            stat_plac[k] = stat_plac.get(k, 0) + v
    say("checkpoint doc %d/%d ngay, sims=%d" % (nday, len(dkeys), sims_tot))
    f = 0.006
    real = np.full(n, np.nan)
    plac = np.full((n, draws), np.nan)
    for i, v in net_real.items():
        real[i] = v - f
    for i, row in net_plac.items():
        plac[i] = row - f
    ok = np.isfinite(real)
    say("")
    say("sims=%d real_ok=%d/%d place_filled=%.1f%%" % (sims_tot, ok.sum(), n, 100.0 * np.isfinite(plac).mean()))
    pm = np.nanmean(plac, axis=1)
    both = ok & np.isfinite(pm)
    mref = float(np.nanmean(real[both]))
    mp = float(np.nanmean(pm[both]))
    say("mean net/leg (f=0.006): THAT=%.5f P1=%.5f diff=%.5f (n=%d)" % (mref, mp, mref - mp, both.sum()))
    blk = ((t0 - t0.min()) // (BLOCK_H * 3600000)).astype(np.int64)
    ublk = np.unique(blk[both])
    imap = {b: k for k, b in enumerate(ublk)}
    bi = np.array([imap[b] for b in blk[both]])
    dr = real[both]; dp = pm[both]
    rng2 = np.random.default_rng(SEED_CI)
    nb = len(ublk)
    diffs = np.empty(NREP_CI)
    Wn = np.bincount(bi, minlength=nb).astype(float)
    for r in range(NREP_CI):
        pick = rng2.integers(0, nb, size=nb)
        W = np.bincount(pick, minlength=nb).astype(float)
        sr_ = float(W @ np.bincount(bi, weights=dr, minlength=nb))
        sp_ = float(W @ np.bincount(bi, weights=dp, minlength=nb))
        nn = float(W @ Wn)
        diffs[r] = (sr_ - sp_) / nn if nn else np.nan
    dlo, dhi = ci95(diffs)
    say("CI95 (block-72h, %d rep, nb=%d): diff THAT-P1 = %.5f [%.5f, %.5f]" % (NREP_CI, nb, float(np.mean(diffs)), dlo, dhi))
    say("status THAT: %s" % {f"{k[0]}|{k[1]}": v for k, v in stat_real.items()})
    say("status P1:   %s" % {f"{k[0]}|{k[1]}": v for k, v in stat_plac.items()})
    # f=0.008
    real8 = real - 0.002
    plac8 = plac - 0.002
    out = dict(n=n, sims=sims_tot, real_ok=int(ok.sum()), draws=draws, f=0.006,
               mean_real=mref, mean_place=mp, diff=mref - mp, ci=[dlo, dhi], ci_mean=float(np.mean(diffs)), nb=nb,
               mean_real8=float(np.nanmean(real8[both])), mean_place8=float(np.nanmean(plac8[both])),
               status_real={f"{k[0]}|{k[1]}": v for k, v in stat_real.items()},
               status_place={f"{k[0]}|{k[1]}": v for k, v in stat_plac.items()})
    with open(json_out, "w") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False, default=str)
    say("JSON -> %s" % json_out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["t123", "t4"])
    ap.add_argument("--json", default="/home/ubuntu/rr_p3.json")
    ap.add_argument("--draws", type=int, default=200)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--pilot", type=int, default=9999)
    a = ap.parse_args()
    if a.mode == "t123":
        run_t123(a.json)
    elif a.mode == "t4":
        run_t4(a.draws, a.workers, a.json, a.pilot)
