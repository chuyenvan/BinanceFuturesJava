#!/usr/bin/env python3
"""NSEL_SCORE_A (2026-10-08): SCORER A (cham chinh thuc) vong NSEL -- PREREG_NSEL 9986c929 §3 J-E, §4-§6.

CHI cham output Kaggle co san: 0 sim, 0 Kaggle, 0 Java, 0 cham 242/shadow. Luat GO chot o pre-reg, KHONG doi/tune.
Thuoc IMPORT (khong viet lai): gkf_rescore (R.load_legs/load_daily, R.run_mtm + MTMStateW cua so 2022-01-01 UTC,
G.load_bars, G.year_ret, G.logtxt/vline), nsel_p0_data (P.load: cum (sym,end)/leg0; P._hw/P.eqh: equity moc gio),
nsel_jd (parse_on, RX_LEG, same_val).
Dinh nghia (tz: printDone + log = gio local +07; MTM phut tren truc UTC):
  cua so n/SumPnL: 2022-01-01 00:00 .. 2025-12-31 23:59 (+07);
  n/nam = so dong printDone co start trong cua so / 4 (moi loai chan);
  SumPnL22-25 = tong pnl dong co end trong cua so (penalty da nam trong gia vao => KHONG tru post-hoc);
  CAGR22 = equity ngay (dong Update 07:00 +07, b+unP) tu moc 2021-12-31 toi moc cuoi (2025-12-30), nam = ngay/365.25
     (= R.core_metrics(daily.loc[W0:]) cac vong truoc);
  maxDD22 / UW22 = equity MTM phut, state reset 2022-01-01 00:00 UTC (feat_add_v1_score.MTMStateW, dd_win/uw_win_days);
  Calmar22 = CAGR22/|maxDD22|; ROI nam y = eq ngay cuoi y / cuoi y-1 - 1 (G.year_ret), quy tuong tu;
  Delta ghep cap theo seed vs NEN-S; can duoi G2 = mean - t(0,95; n-1)*sd/sqrt(n).
J-E: CORE_ADD printDone = counter core_add_done; <=1 CORE_ADD/cum (sym,end); CORE_ADD chi o cum leg0 THEM (NSEL_LEG tier=1);
  CONC/coin = notional coin dang mo (m0<=t<m1, ke ca chan moi) / equity moc gio truoc (P.eqh, = equityNow sim) <= 15%
  tai moi phut vao chan (diem sim kiem) + moi moc gio (troi equity, chi bao cao); chan phat (log [CRASH-PENALTY] leg sap)
  = chan co nen 1m quyet dinh (phut start, lag 0) close/open-1 <= -1%; gia vao = close x (1+pen).
Usage: python3 research/analysis/nsel_score_a.py [--workers 3] [--stage parity|all]
"""
import argparse
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
from scipy import stats

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import gkf_rescore as G  # noqa: E402
import nsel_p0_data as P  # noqa: E402
import nsel_jd as J  # noqa: E402

R, N = G.R, G.N
log = logging.getLogger("nsel_score_a")
OUT = "/home/ubuntu/kaggle_sim/out/"
WD = "/home/ubuntu/claude_master/1008/nsel_score_a"
G.BAR_CACHE = WD + "/bar.json"
P.W = WD
MTM_CACHE = WD + "/mtm.json"
JSON_OUT = REPO + "/docs/result/NSEL_RESULT_A.json"
MD_OUT = REPO + "/docs/result/NSEL_RESULT_A.md"
QUEUE = "/home/ubuntu/claude_master/1008/nsel_impl/queue_status.tsv"
LOCK = "/home/ubuntu/claude_master/1002/oracle_heavy.lock"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
SIDE_SEEDS = [42, 7, 21]
JAR, PEN, CONC_CAP, CRASH = "b7c89f09", 0.01675, 0.15, -0.01
YEARS = [2022, 2023, 2024, 2025]
QS = ["%dQ%d" % (y, q) for y in YEARS for q in (1, 2, 3, 4)]
WS, WE = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-01-01")
NREP, BSEED, BLOCK = 2000, 20260905, 10
INFL2 = math.sqrt(2.0 * math.log(2))
BASEOV = dict(SIM_GATE_ROLLING_MODE="ratio", SIM_GATE_ROLLING_DAYS=90, SIM_GATE_ROLLING_PCT=0.999950829,
              TS_GIVEBACK_RATIO=1.0, SIM_TS_MAX_GAP=0.03, SIM_TS_MAX_GAP_WEAK=0.03, SELECTOR_RANK_TOPK=24,
              GATE_QUOTA_SKIP_WHEN_FULL="true")
NSELOV = dict(NSEL_ADD_ENABLED="true", NSEL_ADD_TOPK=32, SIM_NSEL_ADD_ROLLING_PCT=0.999915,
              SIM_NSEL_ADD_ROLLING_DAYS=90, SIM_NSEL_CORE_ADD="true", NSEL_CORE_ADD_MAX_PER_CLUSTER=1)
RX_PEN = re.compile(r"\[CRASH-PENALTY\] leg sap sym=(\S+?)USDT t=(\d{8} \d\d:\d\d) barRet=(\S+) penalty=(\S+) "
                    r"entry=(\S+) type=([A-Z_0-9]+):(\S+)")
LT = ["PRED_LOI", "PRED_THEM", "CORE_ADD", "BIGD", "DCA"]
FL = ["n_y", "sum_pnl", "cagr22", "dd22", "calmar22", "uw22"] + ["roi%d" % y for y in YEARS]


def tag(a, s):
    if a == "ref":
        return "gqsf-a1" if s == 42 else "gqsf-s%d" % s
    return "nsel-%s-s%d" % (a, s)


def expov(a):
    ov = dict(BASEOV)
    if a not in ("nen", "ref"):
        ov.update(NSELOV)
    if a in ("m2", "m2b"):
        ov["NSEL_ADD_F1_MIN_BARRET"] = -0.01
    if a in ("nen", "m1", "m2"):
        ov["SIM_CRASH_ENTRY_PENALTY"] = PEN
    return ov


def take_lock():
    while os.path.exists(LOCK):
        log.info("cho lock %s", LOCK)
        time.sleep(60)
    with open(LOCK, "w") as f:
        f.write("nsel_score_a %d %s\n" % (os.getpid(), time.ctime()))


def drop_lock():
    if os.path.exists(LOCK):
        os.remove(LOCK)


def queue():
    q = {}
    if os.path.exists(QUEUE):
        for ln in open(QUEUE).read().splitlines()[1:]:
            f = ln.split("\t")
            if len(f) >= 7:
                q[f[1].rstrip("/").split("/")[-1]] = f[6]      # dong sau ghi de (retry)
    return q


def parity(a, s, Q):
    """jar, override dung arm, pred md5 (= gqsf cung seed), [NSEL] on/CORE_ADD/F1, [CRASH-PENALTY] SUMMARY, queue."""
    t = tag(a, s)
    if not os.path.exists(OUT + t + "/result.json") or not os.path.exists(OUT + t + "/storage/printDone.csv"):
        return dict(tag=t, ok=False, missing=True)
    rj = json.load(open(OUT + t + "/result.json"))
    rr = json.load(open(OUT + tag("ref", s) + "/result.json"))
    ov = dict(rj.get("overrides") or {})
    if a in ("ref", "m1b", "m2b") and float(ov.get("SIM_CRASH_ENTRY_PENALTY", 0) or 0) == 0:
        ov.pop("SIM_CRASH_ENTRY_PENALTY", None)
    ex = expov(a)
    txt = G.logtxt(t)
    on = [ln for ln in txt.splitlines() if "[NSEL] on=" in ln]
    kv, lg = J.parse_on(on[-1][on[-1].index("[NSEL] on="):] if on else None)
    # legs= : regex rieng (J.parse_on dung [A-Z]+ sau ':' => bo sot khoa 'CORE_ADD:CORE_ADD'; sua sau lan chay 1)
    lg = {k: int(v) for k, v in re.findall(r"([A-Z_0-9]+:[A-Z_]+)=(\d+)", on[-1].partition(" legs=")[2])} if on else {}
    cps = re.findall(r"\[CRASH-PENALTY\] SUMMARY penalty=(\S+) total=(\d+)", txt)
    nrows = sum(1 for _ in open(OUT + t + "/storage/printDone.csv")) - 1
    vl, vr = G.vline(txt), G.vline(G.logtxt(tag("ref", s)))
    chk = dict(ok=rj.get("ok") is True, date_last=rj.get("date_last") == "20251230", n=rj.get("n_trades") == nrows,
               ov=set(ov) == set(ex) and all(J.same_val(ov[k], ex[k]) for k in ex),
               pred=rj.get("pred_md5_used") == rr.get("pred_md5_used") and vl is not None and vl == vr)
    if a != "ref":
        nsel = a != "nen"
        chk["jar"] = str(rj.get("jar_sha256")).startswith(JAR)
        chk["nsel_on"] = kv.get("on") == ("true" if nsel else "false") and \
            kv.get("core_add_on") == ("true" if nsel else "false")
        if nsel:
            chk["nsel_cfg"] = (kv.get("K_LOI") == "24" and kv.get("K_THEM") == "32" and kv.get("pct_add") == "0.99991500"
                               and kv.get("days_add") == "90" and kv.get("F1") == ("-0.01" if a in ("m2", "m2b") else "NaN"))
        if a in ("nen", "m1", "m2"):
            chk["pen_log"] = len(cps) > 0 and float(cps[-1][0]) == PEN
        else:
            chk["pen_log"] = len(cps) == 0 or float(cps[-1][0]) == 0.0
        chk["queue"] = Q.get(t) == "PASS"
    res = dict(tag=t, ok=bool(all(chk.values())), checks=chk, md5=R.md5_of(t), n=rj.get("n_trades"),
               eq=rj.get("equity_final"), jar=str(rj.get("jar_sha256"))[:8], pred=str(rj.get("pred_md5_used"))[:8],
               nsel_kv=kv, nsel_legs=lg, pen_summary=(cps[-1] if cps else None))
    log.info("PARITY %-16s %s md5=%s n=%s eq=%s jar=%s pred=%s fail=%s", t, "PASS" if res["ok"] else "*** FAIL ***",
             res["md5"][:8], res["n"], res["eq"], res["jar"], res["pred"], [k for k, v in chk.items() if not v])
    return res


def scan(t):
    """full.log: NSEL_LEG (sym, phut UTC epoch, level, tier) + [CRASH-PENALTY] leg sap."""
    legs, pen = [], []
    with open(OUT + t + "/logs/full.log", errors="ignore") as f:
        for ln in f:
            if "NSEL_LEG" in ln:
                m = J.RX_LEG.search(ln)
                if m:
                    legs.append((m.group(1), int(m.group(2)) // 60000, m.group(3), int(m.group(4))))
            elif "leg sap" in ln:
                m = RX_PEN.search(ln)
                if m:
                    pen.append((m.group(1), m.group(2), m.group(6), m.group(7), float(m.group(3)), float(m.group(5))))
    return (pd.DataFrame(legs, columns=["sym", "m0", "level", "tier"]),
            pd.DataFrame(pen, columns=["sym", "start", "level", "tier", "barret", "entry"]))


def label(d, nl):
    """tang tu NSEL_LEG (khop sym, m0, level); NSEL OFF => tier 0 (LOI)."""
    d["level"] = d["level"].astype(str).str.strip()
    d["start"] = d["start"].astype(str).str.strip()
    if len(nl):
        k = nl.drop_duplicates(["sym", "m0", "level"])
        x = d[["sym", "m0", "level"]].merge(k, on=["sym", "m0", "level"], how="left")
        d["tier"] = x["tier"].to_numpy(float)
    else:
        d["tier"] = 0.0
    lv, tr = d["level"], d["tier"]
    d["lab"] = np.select([lv == "CORE_ADD", (lv == "PREDICT_SYMBOL_TRADE") & (tr == 1),
                          lv == "PREDICT_SYMBOL_TRADE", lv == "BIG_DOWN"],
                         ["CORE_ADD", "PRED_THEM", "PRED_LOI", "BIGD"], "DCA")
    return float(np.isfinite(d["tier"]).mean())


def build_px(dd, workers):
    """close moc gio (ffill) cho moi symbol can, tinh moi bang P._hw (khong dung cache cu: do phu thoi gian)."""
    need, nH = {}, 0
    for d in dd.values():
        a, b = P.hour_span(d)
        nH = max(nH, int(b.max()) + 2)
        for s, x, y in zip(d["sym"].tolist(), a.tolist(), b.tolist()):
            for k in range(x // 24, max(x, y - 1) // 24 + 1):
                need.setdefault(k, set()).add(s)
    nH = max(nH, (max(need) + 1) * 24)
    jobs = [((pd.Timestamp("2021-07-01") + pd.Timedelta(days=k)).strftime("%Y%m%d"), sorted(v)) for k, v in sorted(need.items())]
    log.info("PX: %d ngay ticker, %d gio, %d symbol", len(jobs), nH, len(set().union(*need.values())))
    px, t0 = {}, time.time()
    with Pool(workers) as pool:
        for i, (day, out) in enumerate(pool.imap_unordered(P._hw, jobs, chunksize=4)):
            k = (pd.Timestamp(day) - pd.Timestamp("2021-07-01")).days
            for s, v in out.items():
                px.setdefault(s, np.full(nH, np.nan, np.float32))[k * 24:k * 24 + 24] = v
            if i % 200 == 0:
                log.info("  PX %d/%d %.0fs", i, len(jobs), time.time() - t0)
    for s in px:
        px[s] = pd.Series(px[s]).ffill().to_numpy(np.float32)
    return px, nH, sorted(set().union(*need.values()) - set(px))


def eqh_check(eq, daily):
    """equity moc gio tai lap (P.eqh) vs dong Update 07:00 +07 (= 00:00 UTC) cua log."""
    e = daily["equity"].astype(float)
    h = ((pd.to_datetime(e.index) - pd.Timestamp("2021-07-01")).days * 24).to_numpy()
    ok = (h >= 0) & (h < len(eq))
    r = np.abs(eq[h[ok]] / e.to_numpy()[ok] - 1)
    return dict(n=int(ok.sum()), med_rel=float(np.median(r)), p99_rel=float(np.percentile(r, 99)), max_rel=float(r.max()))


def conc(d, eq):
    """CONC/coin: tai moi phut vao chan (eq moc gio truoc, nhu Book.state) + tai moi moc gio (troi equity)."""
    H0 = P.H0_MIN
    a, b = P.hour_span(d)
    best_e, best_h, n_ev, n_over = (0.0, None), (0.0, None), 0, 0
    for s, g in d.groupby("sym"):
        m0, m1, nt = g["m0"].to_numpy(), g["m1"].to_numpy(), g["notional"].to_numpy(float)
        for t in np.unique(m0):
            op = nt[(m0 <= t) & (m1 > t)].sum()
            h = int((t - 1 - H0) // 60)
            r = op / (eq[h] if h >= 0 else P.CAP0)
            n_ev += 1
            n_over += r > CONC_CAP + 1e-6
            if r > best_e[0]:
                best_e = (float(r), "%s %s" % (s, pd.Timestamp((t + 420) * 60, unit="s")))
        arr = np.zeros(len(eq))
        for x, y, v in zip(a[g.index], b[g.index], nt):
            arr[x:y] += v
        j = int(np.argmax(arr / eq))
        if arr[j] / eq[j] > best_h[0]:
            best_h = (float(arr[j] / eq[j]), "%s h%d" % (s, j))
    return dict(n_entry_events=n_ev, n_over_entry=int(n_over), max_entry=best_e[0], max_entry_at=best_e[1],
                max_hour=best_h[0], max_hour_at=best_h[1])


def je(d, kv, lg, pen, bar, eq):
    r = {}
    ca = d[d["level"] == "CORE_ADD"]
    r["core_add_printDone"] = int(len(ca))
    r["core_add_done_counter"] = int(kv.get("core_add_done", -1))
    r["core_add_legs_counter"] = int(lg.get("CORE_ADD:CORE_ADD", 0))
    r["core_add_eq"] = r["core_add_printDone"] == r["core_add_done_counter"] == r["core_add_legs_counter"]
    r["clusters_gt1_core_add"] = int((ca.groupby("pid").size() > 1).sum())
    l0 = d[d["leg0"]].set_index("pid")
    x = l0.reindex(ca["pid"].to_numpy())
    good = (x["level"].to_numpy() == "PREDICT_SYMBOL_TRADE") & (x["tier"].to_numpy() == 1)
    r["core_add_leg0_them"] = int(good.sum())
    r["core_add_leg0_bad"] = int(len(ca) - good.sum())
    r["core_add_tier2"] = int((ca["tier"] == 2).sum())
    o = np.full(len(d), np.nan)
    c = np.full(len(d), np.nan)
    for i, (s, mm) in enumerate(zip(d["sym"].tolist(), (d["m0"] - P.DAY0_MIN).tolist())):
        v = bar.get((s, int(mm)))
        if v is not None:
            o[i], c[i] = v
    crash = (c / o - 1.0) <= CRASH
    key = d["sym"] + "|" + d["start"] + "|" + d["level"]
    pk = pen["sym"] + "|" + pen["start"] + "|" + pen["level"]
    inlog = key.isin(set(pk)).to_numpy()
    both, ol, ob = int((inlog & crash).sum()), int((inlog & ~crash).sum()), int((~inlog & crash).sum())
    ratio = d["entry"].to_numpy(float) / c
    r["pen"] = dict(n_log=int(len(pen)), n_log_unique=int(pk.nunique()), n_log_in_printDone=int(inlog.sum()),
                    n_crash_bar=int(crash.sum()), both=both, only_log=ol, only_bar=ob,
                    match_pct=100.0 * both / max(1, both + ol + ob), bar_missing=int(np.isnan(o).sum()),
                    entry_pen_ok=float(np.mean(np.abs(ratio[crash] / (1 + PEN) - 1) < 2e-5)) if crash.any() else None,
                    entry_nopen_ok=float(np.nanmean(np.abs(ratio[~crash] - 1) < 2e-5)),
                    by_level={k: int(v) for k, v in d.loc[crash, "level"].value_counts().items()})
    r["conc"] = conc(d, eq)
    r["pass"] = bool(r["core_add_eq"] and r["clusters_gt1_core_add"] == 0 and r["core_add_leg0_bad"] == 0
                     and r["pen"]["match_pct"] == 100.0 and r["conc"]["n_over_entry"] == 0)
    return r


def qret(eq):
    e = eq.astype(float).copy()
    e.index = pd.to_datetime(e.index)
    prev, out = float(e[e.index <= "2021-12-31"].iloc[-1]), {}
    for y in YEARS:
        for q, md in zip((1, 2, 3, 4), ("03-31", "06-30", "09-30", "12-31")):
            v = float(e[e.index <= "%d-%s" % (y, md)].iloc[-1])
            out["%dQ%d" % (y, q)], prev = 100 * (v / prev - 1), v
    return out


def metr(L, daily, mt):
    ent = L[(L["ts"] >= WS) & (L["ts"] < WE)]
    cl = L[(L["te"] >= WS) & (L["te"] < WE)]
    e = daily["equity"].astype(float)
    e = e[e.index >= N.W0]
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    cagr = 100 * ((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1)
    dd = float(mt["dd_win"])
    m = dict(n_y=len(ent) / 4.0, n_year={y: int((ent["ts"].dt.year == y).sum()) for y in YEARS},
             sum_pnl=float(cl["pnl"].sum()), cagr22=float(cagr), dd22=dd, calmar22=float(cagr / abs(dd)),
             uw22=float(mt["uw_win_days"]), eq_w0=float(e.iloc[0]), eq_end=float(e.iloc[-1]),
             eq_w0_day=str(e.index[0].date()), eq_end_day=str(e.index[-1].date()), roi_q=qret(daily["equity"]))
    for y, v in G.year_ret(daily["equity"]).items():
        m["roi%d" % y] = float(v)
    return m


def bytype(d):
    ent = d[(d["ts"] >= WS) & (d["ts"] < WE)]
    cl = d[(d["te"] >= WS) & (d["te"] < WE)]
    out = {}
    for k in LT:
        e, c = ent[ent["lab"] == k], cl[cl["lab"] == k]
        out[k] = dict(n_y=len(e) / 4.0, n_year={y: int((e["year"] == y).sum()) for y in YEARS},
                      sum_pnl=float(c["pnl"].sum()),
                      roi_leg=float((100 * c["pnl"] / c["notional"]).mean()) if len(c) else None)
    return out


def summ(v):
    v = np.asarray(v, float)
    n = len(v)
    if n == 0:
        return None
    sd = float(v.std(ddof=1)) if n > 1 else float("nan")
    tq = float(stats.t.ppf(0.95, n - 1)) if n > 1 else float("nan")
    return dict(n=n, mean=float(v.mean()), sd=sd, min=float(v.min()), max=float(v.max()), npos=int((v > 0).sum()),
                t95=tq, lb=float(v.mean() - tq * sd / math.sqrt(n)), vals=[float(x) for x in v])


def boot(DE, arm, base, seeds):
    """MTM ngay block-10d ghep cap: dPnL_MTM = sum(dEq_arm - dEq_nen) cua so (W0..cuoi), trung binh qua seed."""
    idx = DE[(base, seeds[0])].index
    idx = idx[idx >= N.W0]
    X = []
    for s in seeds:
        a, b = DE[(arm, s)].reindex(idx).astype(float), DE[(base, s)].reindex(idx).astype(float)
        assert not a.isna().any() and not b.isna().any(), ("lech ngay", arm, s)
        X.append((a.diff() - b.diff()).to_numpy()[1:])
    X = np.array(X)
    T = X.shape[1]
    nb = int(math.ceil(T / BLOCK))
    rng = np.random.default_rng(BSEED)
    bs = np.empty(NREP)
    for i in range(NREP):
        st = rng.integers(0, T - BLOCK + 1, size=nb)
        bs[i] = X[:, (st[:, None] + np.arange(BLOCK)[None, :]).ravel()[:T]].sum(axis=1).mean()
    obs = float(X.sum(axis=1).mean())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(obs=obs, per_seed=[float(x) for x in X.sum(axis=1)], ci_raw=[float(lo), float(hi)],
                ci_infl=[float(obs - (obs - lo) * INFL2), float(obs + (hi - obs) * INFL2)],
                p5=float(np.percentile(bs, 5)), p_le0=float(np.mean(bs <= 0)), T=T, nrep=NREP, seed=BSEED)


def rules(M, arm, seeds):
    dl = {f: summ([M[(arm, s)][f] - M[("nen", s)][f] for s in seeds]) for f in FL}
    g = {}
    g["G1"] = dict(val=dl["n_y"]["mean"], thr=">= +500 chan/nam", ok=dl["n_y"]["mean"] >= 500)
    g["G2"] = dict(val=dl["sum_pnl"]["mean"], lb=dl["sum_pnl"]["lb"], thr="mean >= 0 VA lb(t95,df n-1) >= -8000",
                   ok=dl["sum_pnl"]["mean"] >= 0 and dl["sum_pnl"]["lb"] >= -8000)
    dmin = min(M[(arm, s)]["dd22"] for s in seeds)
    g["G3"] = dict(val_min_dd=dmin, val_mean_ddd=dl["dd22"]["mean"], thr="maxDD22 <= 40% moi seed VA mean dDD >= -8pp",
                   ok=dmin >= -40.0 and dl["dd22"]["mean"] >= -8.0)
    ca, cb = np.mean([M[(arm, s)]["calmar22"] for s in seeds]), np.mean([M[("nen", s)]["calmar22"] for s in seeds])
    g["G4"] = dict(val=float(ca), base=float(cb), ratio=float(ca / cb), thr=">= 0,85 x NEN", ok=bool(ca >= 0.85 * cb))
    ym = {y: dl["roi%d" % y]["mean"] for y in YEARS}
    npos = sum(v >= 0 for v in ym.values())
    g["G5"] = dict(val=ym, n_ge0=int(npos), worst=float(min(ym.values())), thr=">= 2/4 nam mean dROI >= 0 VA khong nam < -8pp",
                   ok=npos >= 2 and min(ym.values()) >= -8.0)
    return dl, g


def fm(x, nd=2, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return ((("%+." if sign else "%.") + str(nd) + "f") % x).replace(".", ",")


def write_md(js):
    o = ["# NSEL — KẾT QUẢ CHẤM SCORER A (chính thức) — 2026-10-08", "",
         "Pre-reg `docs/prereg/PREREG_NSEL.md` (9986c929) §3 J-E, §4–§6. Script `research/analysis/nsel_score_a.py`; "
         "JSON `docs/result/NSEL_RESULT_A.json` (mọi số trong luật GO, khoá arm/seed). Chỉ chấm output có sẵn: 0 sim, "
         "0 Kaggle, 0 Java, 0 chạm 242/shadow. Luật không đổi, không tune. J-F (đối chiếu scorer B) do MASTER.", "",
         "## Định nghĩa (bắt buộc)", ""] + ["- " + x for x in js["definitions"]] + [""]
    o += ["## 1. Parity", "", "| run | kết quả | md5 printDone | n | eq | jar | pred | fail |", "|---|---|---|---|---|---|---|---|"]
    for t, p in js["parity"].items():
        if p.get("missing"):
            o.append("| %s | THIẾU | — | — | — | — | — | chưa có output |" % t)
            continue
        o.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (t, "PASS" if p["ok"] else "FAIL", p["md5"][:8], p["n"], p["eq"],
                 p["jar"], p["pred"], ",".join(k for k, v in p["checks"].items() if not v) or "—"))
    o += ["", "Seed hợp lệ: " + "; ".join("%s %s" % (a, v) for a, v in js["valid_seeds"].items()), ""]
    o += ["## 2. J-E (counter khớp printDone)", "",
          "| run | CORE_ADD printDone / counter done / legs | cụm >1 CORE_ADD | CORE_ADD leg0 THÊM / sai | phạt: log / nến sập / khớp / chỉ log / chỉ nến / % khớp | giá vào phạt OK | CONC max lúc vào (vượt) | CONC max mốc giờ | PASS |",
          "|---|---|---|---|---|---|---|---|---|"]
    for t, r in js["je"].items():
        p, c = r["pen"], r["conc"]
        o.append("| %s | %d / %d / %d | %d | %d / %d | %d / %d / %d / %d / %d / %s | %s | %s%% (%d) | %s%% | %s |" % (
            t, r["core_add_printDone"], r["core_add_done_counter"], r["core_add_legs_counter"], r["clusters_gt1_core_add"],
            r["core_add_leg0_them"], r["core_add_leg0_bad"], p["n_log"], p["n_crash_bar"], p["both"], p["only_log"],
            p["only_bar"], fm(p["match_pct"], 2), fm(p["entry_pen_ok"], 4), fm(100 * c["max_entry"], 2), c["n_over_entry"],
            fm(100 * c["max_hour"], 2), "PASS" if r["pass"] else "FAIL"))
    o += ["", "Equity mốc giờ tái lập (P.eqh) vs dòng Update 07:00: " + "; ".join(
        "%s max %s" % (t, fm(100 * v["max_rel"], 3) + "%") for t, v in js["eqh_check"].items()), "",
        "J-E tổng: **%s**" % ("PASS" if js["je_pass"] else "FAIL"), ""]
    o += ["## 3. Bảng chính (8 seed)", "", "| arm | seed | n/năm | ΣPnL22–25 | CAGR22 | maxDD22 | Calmar22 | UW22 (ngày) | ROI 2022 | 2023 | 2024 | 2025 |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in ("nen", "m1", "m2"):
        for s in SEEDS:
            m = js["metrics"].get("%s|%d" % (a, s))
            if m:
                o.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    a, s, fm(m["n_y"], 1), fm(m["sum_pnl"], 0), fm(m["cagr22"]), fm(m["dd22"]), fm(m["calmar22"], 3),
                    fm(m["uw22"], 1), fm(m["roi2022"]), fm(m["roi2023"]), fm(m["roi2024"]), fm(m["roi2025"])))
    o += ["", "## 4. Δ ghép cặp vs NỀN-S", "", "| arm | trường | mean | sd | min | max | seed Δ>0 | cận dưới (t95) |", "|---|---|---|---|---|---|---|---|"]
    for a in ("m1", "m2"):
        for f in FL:
            x = js["delta"][a][f]
            o.append("| %s | %s | %s | %s | %s | %s | %d/%d | %s |" % (a, f, fm(x["mean"], 2, True), fm(x["sd"]), fm(x["min"], 2, True),
                     fm(x["max"], 2, True), x["npos"], x["n"], fm(x["lb"], 2, True)))
    o += ["", "## 5. Luật GO §6", ""]
    for a in ("m1", "m2"):
        g = js["rules"][a]
        o.append("### %s-S → %s" % (a.upper(), g["verdict"]))
        o.append("- G1 mean Δn = %s (≥ +500) → %s" % (fm(g["G1"]["val"], 1, True), "PASS" if g["G1"]["ok"] else "FAIL"))
        o.append("- G2 mean ΔΣPnL = %s (≥ 0), cận dưới t95 df %d = %s (≥ −8000) → %s" % (
            fm(g["G2"]["val"], 0, True), js["delta"][a]["sum_pnl"]["n"] - 1, fm(g["G2"]["lb"], 0, True), "PASS" if g["G2"]["ok"] else "FAIL"))
        o.append("- G3 maxDD22 tệ nhất = %s%% (≥ −40), mean ΔmaxDD22 = %s pp (≥ −8) → %s" % (
            fm(g["G3"]["val_min_dd"]), fm(g["G3"]["val_mean_ddd"], 2, True), "PASS" if g["G3"]["ok"] else "FAIL"))
        o.append("- G4 mean Calmar22 = %s vs NỀN %s (tỉ lệ %s, ≥ 0,85) → %s" % (
            fm(g["G4"]["val"], 3), fm(g["G4"]["base"], 3), fm(g["G4"]["ratio"], 3), "PASS" if g["G4"]["ok"] else "FAIL"))
        o.append("- G5 mean ΔROI %s; năm ≥ 0: %d/4 (≥ 2), tệ nhất %s pp (≥ −8) → %s" % (
            ", ".join("%s %s" % (y, fm(v, 2, True)) for y, v in g["G5"]["val"].items()), g["G5"]["n_ge0"], fm(g["G5"]["worst"], 2, True),
            "PASS" if g["G5"]["ok"] else "FAIL"))
        o.append("- G6 J-A/J-B/J-C PASS (NSEL_IMPL_JOINTS), J-D PASS (fa749e23), J-E %s (mục 2), J-F CHỜ đối chiếu scorer B → %s" % (
            "PASS" if js["je_pass"] else "FAIL", g["G6"]))
        o.append("")
    o += ["**Chọn arm:** " + js["choice"], ""]
    o += ["## 6. Phụ (báo cáo, KHÔNG vào luật)", ""]
    o += ["### 6.1 Bootstrap MTM ngày block-10d (ΔPnL_MTM = Δ(eq cuối − eq 2021-12-31), trung bình 8 seed, NREP 2000 seed 20260905; inflate √(2 ln 2))", "",
          "| arm | obs | CI95 raw | CI95 inflate | p5 | P(≤0) |", "|---|---|---|---|---|---|"]
    for a, b in js["boot"].items():
        o.append("| %s | %s | [%s; %s] | [%s; %s] | %s | %s |" % (a, fm(b["obs"], 0, True), fm(b["ci_raw"][0], 0, True), fm(b["ci_raw"][1], 0, True),
                 fm(b["ci_infl"][0], 0, True), fm(b["ci_infl"][1], 0, True), fm(b["p5"], 0, True), fm(b["p_le0"], 3)))
    o += ["", "### 6.2 Theo quý — mean ΔROI (pp) vs NỀN-S", "", "| quý | " + " | ".join(js["quarter"]) + " |", "|---|" + "---|" * len(js["quarter"])]
    for q in QS:
        o.append("| %s | %s |" % (q, " | ".join(fm(js["quarter"][a][q]["mean"], 2, True) + " (%d/%d)" % (js["quarter"][a][q]["npos"], js["quarter"][a][q]["n"]) for a in js["quarter"])))
    o += ["", "### 6.3 Theo loại chân (mean 8 seed; n/năm theo entry, ΣPnL theo close 22–25, ROI/chân = mean 100·pnl/notional)", "",
          "| arm | loại | n/năm | ΣPnL | ROI/chân % | ΔΣPnL vs NỀN cùng loại |", "|---|---|---|---|---|---|"]
    for a, tb in js["bytype_mean"].items():
        for k in LT:
            x = tb[k]
            o.append("| %s | %s | %s | %s | %s | %s |" % (a, k, fm(x["n_y"], 1), fm(x["sum_pnl"], 0), fm(x["roi_leg"], 3), fm(x.get("d_sum_pnl"), 0, True)))
    o += ["", "CORE_ADD theo năm (mean 8 seed, theo entry): " + "; ".join(
        "%s %s" % (a, ", ".join("%s %s" % (y, fm(v, 1)) for y, v in js["core_add_year"][a].items())) for a in js["core_add_year"]), ""]
    o += ["### 6.4 Base-cost (penalty 0) m1b/m2b vs gqsf", ""]
    if js["side"]:
        o += ["| arm | seed | Δn/năm | ΔΣPnL | ΔCAGR22 | ΔmaxDD22 | ΔCalmar22 |", "|---|---|---|---|---|---|---|"]
        for a, rs in js["side"].items():
            for s, x in rs.items():
                o.append("| %s | %s | %s | %s | %s | %s | %s |" % (a, s, fm(x["n_y"], 1, True), fm(x["sum_pnl"], 0, True), fm(x["cagr22"], 2, True),
                         fm(x["dd22"], 2, True), fm(x["calmar22"], 3, True)))
    o += ["", "Run phụ thiếu/FAIL: " + (", ".join(js["side_missing"]) or "không"), ""]
    o += ["## 7. Tự kiểm thước", "", "Tái lập k32_confirm.json (gqsf-a1/s7/s21: cagr22, dd_mtm22, uw_mtm22, calmar22, sum_pnl_2022_25): "
          "%d khoá, lệch %d → %s" % (js["selfcheck"]["n"], len(js["selfcheck"]["bad"]), "OK" if not js["selfcheck"]["bad"] else "LỆCH"), ""]
    open(MD_OUT, "w", encoding="utf-8").write("\n".join(o) + "\n")


DEFS = ["Múi giờ: printDone/log = giờ local +07; MTM phút tính trên trục UTC (R.run_mtm).",
        "Cửa sổ n/ΣPnL: 2022-01-01 00:00 → 2025-12-31 23:59 (+07).",
        "n/năm = số dòng printDone (mọi loại chân) có start trong cửa sổ / 4.",
        "ΣPnL22–25 = Σ pnl dòng printDone có end trong cửa sổ; penalty đã nằm trong giá vào ⇒ KHÔNG trừ post-hoc.",
        "CAGR22 = equity ngày (dòng Update 07:00 +07 = b+unP) từ mốc 2021-12-31 (đầu 2022) tới mốc cuối 2025-12-30, năm = ngày/365,25 (= thước gkf_rescore/k32_confirm).",
        "maxDD22 = DD lớn nhất của equity MTM phút, đỉnh reset tại 2022-01-01 00:00 UTC (= 07:00 +07) (MTMStateW dd_win); UW22 = chuỗi dưới nước dài nhất (ngày, uw_win_days).",
        "Calmar22 = CAGR22/|maxDD22|. ROI năm y = eq ngày cuối y / cuối y−1 − 1 (pp, G.year_ret); quý tương tự.",
        "Δ = arm − NỀN-S cùng seed; cận dưới một phía G2 = mean − t(0,95; df n−1)·sd/√n (8 seed ⇒ t = 1,8946). G4 so mean Calmar22 arm với 0,85 × mean Calmar22 NỀN-S.",
        "Run FAIL/thiếu ⇒ seed đó loại khỏi CẢ cặp (arm, NỀN).",
        "Ghi chú sửa lỗi script (không đổi luật/thước): lần chạy 1 (22:46) J-E báo FAIL giả ở 16 run M1/M2 vì nsel_jd.parse_on (regex [A-Z]+ sau ':') không đọc khoá counter legs 'CORE_ADD:CORE_ADD' ⇒ legs=0; thay bằng regex riêng [A-Z_]+. Mọi số khác giữ nguyên (cache MTM/bar/eqh theo md5)."]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--stage", default="all", choices=["parity", "all"])
    a_ = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
    os.makedirs(WD, exist_ok=True)
    Q = queue()
    par = {}
    for a in ("ref", "nen", "m1", "m2"):
        for s in SEEDS:
            par[(a, s)] = parity(a, s, Q)
    for a in ("m1b", "m2b"):
        for s in SIDE_SEEDS:
            par[(a, s)] = parity(a, s, Q)
    ok = {k: v["ok"] for k, v in par.items()}
    valid = {a: [s for s in SEEDS if ok[(a, s)] and ok[("nen", s)]] for a in ("m1", "m2")}
    vside = {a: [s for s in SIDE_SEEDS if ok[(a, s)] and ok[("ref", s)]] for a in ("m1b", "m2b")}
    side_missing = [tag(a, s) + (" (thiếu)" if par[(a, s)].get("missing") else " (FAIL)")
                    for a in ("m1b", "m2b") for s in SIDE_SEEDS if not ok[(a, s)]]
    log.info("SEED HOP LE %s; PHU %s; thieu %s", valid, vside, side_missing)
    if a_.stage == "parity":
        return
    tags = {k: par[k]["tag"] for k in par if ok[k]}
    L = {k: R.load_legs(t) for k, t in tags.items()}
    DY = {k: R.load_daily(t) for k, t in tags.items()}
    md5 = {k: par[k]["md5"] for k in tags}
    take_lock()
    try:
        bar = G.load_bars({tags[k]: L[k] for k in tags}, a_.workers)
        raw = json.load(open(MTM_CACHE)) if os.path.exists(MTM_CACHE) else {}
        miss = {tags[k]: L[k] for k in tags if raw.get(tags[k], {}).get("md5") != md5[k]}
        log.info("MTM can tinh %d: %s", len(miss), sorted(miss))
        if miss:
            new = R.run_mtm(miss, workers=a_.workers, chunk=30)
            for t, v in new.items():
                raw[t] = dict(v["legacy"], md5=md5[[k for k in tags if tags[k] == t][0]])
            json.dump(raw, open(MTM_CACHE, "w"))
        jk = [k for k in tags if k[0] in ("nen", "m1", "m2")]
        PD = {}
        for k in jk:
            d, meta = P.load(tags[k])
            assert meta["n"] == len(L[k]), (k, meta["n"], len(L[k]))
            PD[k] = d
        if all(os.path.exists(WD + "/eqh_%s.npz" % tags[k]) and os.path.getmtime(WD + "/eqh_%s.npz" % tags[k]) >
               os.path.getmtime(OUT + tags[k] + "/storage/printDone.csv") for k in jk) and os.path.exists(WD + "/pxmiss.json"):
            pxmiss = json.load(open(WD + "/pxmiss.json"))      # eqh da tinh (cache tu tao) => khong doc lai ticker
            log.info("EQH: dung cache %d file", len(jk))
        else:
            px, nH, pxmiss = build_px({tags[k]: PD[k] for k in jk}, a_.workers)
            for k in jk:
                P.eqh(tags[k], PD[k], px, nH)
            del px
            json.dump(pxmiss, open(WD + "/pxmiss.json", "w"))
    finally:
        drop_lock()
    M = {k: metr(L[k], DY[k], raw[tags[k]]) for k in tags}
    # tu kiem thuoc: tai lap k32_confirm.json (nen gqsf 3 seed)
    k32 = json.load(open(REPO + "/docs/result/k32_confirm.json"))["metrics"]
    fmap = dict(cagr22="cagr22", dd22="dd_mtm22", uw22="uw_mtm22", calmar22="calmar22", sum_pnl="sum_pnl_2022_25")
    bad, nchk = [], 0
    for s in (42, 7, 21):
        t = tag("ref", s)
        if ("ref", s) in M and t in k32:
            for f, g in fmap.items():
                nchk += 1
                if abs(M[("ref", s)][f] - k32[t][g]) > 1e-6 * max(1.0, abs(k32[t][g])):
                    bad.append((t, f, M[("ref", s)][f], k32[t][g]))
    log.info("TU KIEM k32_confirm: %d, lech %s", nchk, bad)
    # J-E
    JE, EQC, LABJ, BT = {}, {}, {}, {}
    for k in jk:
        t = tags[k]
        nl, pen = scan(t)
        d = PD[k]
        LABJ[t] = label(d, nl)
        z = np.load(WD + "/eqh_%s.npz" % t)
        EQC[t] = eqh_check(z["eq"], DY[k])
        JE[t] = je(d, par[k]["nsel_kv"], par[k]["nsel_legs"], pen, bar, z["eq"])
        JE[t]["tier_join_rate"] = LABJ[t]
        JE[t]["pen_summary_total"] = int(par[k]["pen_summary"][1]) if par[k]["pen_summary"] else None
        BT[k] = bytype(d)
        log.info("J-E %-16s %s core_add %d/%d gt1 %d leg0bad %d pen match %.2f%% (log %d bar %d) conc %.4f (over %d) hour %.4f eqh max %.2e",
                 t, "PASS" if JE[t]["pass"] else "FAIL", JE[t]["core_add_printDone"], JE[t]["core_add_done_counter"],
                 JE[t]["clusters_gt1_core_add"], JE[t]["core_add_leg0_bad"], JE[t]["pen"]["match_pct"], JE[t]["pen"]["n_log"],
                 JE[t]["pen"]["n_crash_bar"], JE[t]["conc"]["max_entry"], JE[t]["conc"]["n_over_entry"], JE[t]["conc"]["max_hour"],
                 EQC[t]["max_rel"])
    del bar
    je_pass = all(JE[tags[k]]["pass"] for k in jk)
    delta, RL = {}, {}
    for a in ("m1", "m2"):
        delta[a], RL[a] = rules(M, a, valid[a])
    go = {}
    for a in ("m1", "m2"):
        g5 = all(RL[a][x]["ok"] for x in ("G1", "G2", "G3", "G4", "G5"))
        RL[a]["G6"] = "PASS (J-A..J-E), J-F chờ MASTER" if je_pass else "FAIL (J-E)"
        go[a] = g5 and je_pass
        RL[a]["verdict"] = ("GO (điều kiện J-F)" if go[a] else "NO-GO") + " — G1–G5: " + ", ".join(
            "%s %s" % (x, "PASS" if RL[a][x]["ok"] else "FAIL") for x in ("G1", "G2", "G3", "G4", "G5"))
    if go["m1"] and go["m2"]:
        d1, d2 = delta["m1"]["sum_pnl"]["mean"], delta["m2"]["sum_pnl"]["mean"]
        if abs(d1 - d2) >= 5000:
            choice = "M1-S" if d1 > d2 else "M2-S"
        else:
            choice = "M1-S" if delta["m1"]["n_y"]["mean"] >= delta["m2"]["n_y"]["mean"] else "M2-S"
        choice += " (cả 2 GO; chênh ΔΣPnL %.0f)" % (d1 - d2)
    elif go["m1"] or go["m2"]:
        choice = ("M1-S" if go["m1"] else "M2-S") + " (arm duy nhất GO, điều kiện J-F)"
    else:
        choice = "NO-GO — không arm nào GO ⇒ giữ K24 + skipFull"
    # phu
    DE = {k: DY[k]["equity"] for k in tags}
    bo = {a: boot(DE, a, "nen", valid[a]) for a in ("m1", "m2")}
    qt = {a: {q: summ([M[(a, s)]["roi_q"][q] - M[("nen", s)]["roi_q"][q] for s in valid[a]]) for q in QS} for a in ("m1", "m2")}
    btm, cay = {}, {}
    for a in ("nen", "m1", "m2"):
        ss = valid["m1"] if a == "nen" else valid[a]
        btm[a] = {}
        for lt in LT:
            vals = [BT[(a, s)][lt] for s in ss]
            x = dict(n_y=float(np.mean([v["n_y"] for v in vals])), sum_pnl=float(np.mean([v["sum_pnl"] for v in vals])),
                     roi_leg=float(np.nanmean([v["roi_leg"] if v["roi_leg"] is not None else np.nan for v in vals])) if any(v["roi_leg"] is not None for v in vals) else None)
            if a != "nen":
                x["d_sum_pnl"] = float(np.mean([BT[(a, s)][lt]["sum_pnl"] - BT[("nen", s)][lt]["sum_pnl"] for s in ss]))
            btm[a][lt] = x
        cay[a] = {y: float(np.mean([BT[(a, s)]["CORE_ADD"]["n_year"][y] for s in ss])) for y in YEARS}
    side = {}
    for a in ("m1b", "m2b"):
        if vside[a]:
            side[a] = {str(s): {f: M[(a, s)][f] - M[("ref", s)][f] for f in ("n_y", "sum_pnl", "cagr22", "dd22", "calmar22")} for s in vside[a]}
    js = dict(prereg="docs/prereg/PREREG_NSEL.md 9986c929", scorer="A", definitions=DEFS,
              parity={par[k]["tag"]: par[k] for k in par}, valid_seeds={a: v for a, v in valid.items()},
              valid_side=vside, side_missing=side_missing,
              metrics={"%s|%d" % k: M[k] for k in M}, je=JE, je_pass=je_pass, eqh_check=EQC, px_missing_syms=pxmiss,
              delta=delta, rules=RL, go=go, choice=choice, boot=bo, quarter=qt, bytype={"%s|%d" % k: v for k, v in BT.items()},
              bytype_mean=btm, core_add_year=cay, side=side, selfcheck=dict(n=nchk, bad=bad),
              go_inputs={a: {"%s|%d" % (b, s): {f: M[(b, s)][f] for f in FL} for b in ("nen", a) for s in valid[a]} for a in ("m1", "m2")})
    json.dump(js, open(JSON_OUT, "w"), indent=1, default=G.jd)
    write_md(json.loads(json.dumps(js, default=G.jd)))
    log.info("XONG: %s | %s | choice %s", {a: RL[a]["verdict"] for a in RL}, je_pass, choice)


if __name__ == "__main__":
    main()
