#!/usr/bin/env python3
"""GKF_RESCORE (2026-10-07): CHAM LAI GATE x K FRONTIER Phase 1 (claw, 0a3f10d0) theo DUNG thuoc pre-reg
docs/prereg/PREREG_GATE_K_FRONTIER.md (4e4fc975 + ADDENDUM-1 36b5d136) §8/§9.

CHI tinh tu output Kaggle CO SAN (~/kaggle_sim/out/gkf-*, gqsf-a1): 0 sim, 0 Java, 0 tune, 0 sua file claw.
Thuoc (= n700_driver / gate_skipfull_driver): MTM phut (reset_rule_score.run_mtm, phi legacy as-is, cua so 2022+ qua
feat_add_v1_score), CAGR22 tu equity ngay (b+unP), Calmar22 = CAGR22/|maxDD22 MTM phut|; MTM ngay paired block-10d
NREP 2000 seed 20260905 (selector_ablation_driver.daily_boot); dPnL paired theo ngay dong (n700_driver.pnl_boot);
inflate sqrt(2 ln 13) (k = 8 arm Phase 1 + p0b + 4 l2 da nhin).
STRESS (COST_TRUTH d059cc3) POST-HOC (khong co script san; vong truoc phat trong sim bang SIM_CRASH_ENTRY_PENALTY):
moi chan (moi dong printDone) co nen 1m QUYET DINH (nen co close = gia vao; quy uoc phut xac dinh bang khop entry)
voi close/open-1 <= -1% => gia vao nang 1.675% (unP MTM giam tu luc vao) va PnL lenh giam 1.675% x notional.
Khong mo phong lai duong di (qty/TP/SL/sizing/lich vao giu nguyen) => xap xi bac 1.
Nguon nen 1m = reset_rule_score.TICKER (/home/ubuntu/kaggle_data_hpo), cung nguon MTM phut cac vong truoc.
Usage: python3 research/analysis/gkf_rescore.py [--workers 3]
"""
import argparse
import gzip
import json
import logging
import math
import os
import re
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/analysis")
import reset_rule_score as R  # noqa: E402
import feat_add_v1_score as F  # noqa: E402,F401  (side effect: MTMState cua so 2022+ -> dd_win/uw_win_days)
import flat3_crashpen_driver as F3  # noqa: E402
import selector_ablation_driver as SAD  # noqa: E402
import n700_driver as N  # noqa: E402
import jbin  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("gkf_rescore")
R.MTM_COSTS = {"legacy": R.LEGACY}

OUT = "/home/ubuntu/kaggle_sim/out/%s/"
D = "/home/ubuntu/claude_master/1007/gkfscore"
JSON_OUT = REPO + "/docs/audit/AUDIT_GKF_PHASE1_20261007.json"
MD_OUT = D + "/tables.md"
MTM_CACHE = D + "/mtm.json"
BAR_CACHE = D + "/bar.json"
CALIB = REPO + "/docs/audit/GATE_OFFLINE_ISON_CALIB.json"
CLAW = REPO + "/docs/result/gate_k_frontier.json"
GQSF = REPO + "/docs/result/gate_skipfull.json"
BASE, REF = "gkf-nen", "gqsf-a1"
JAR_SHA = "20d412e83dba15ff9320b02c011f37d36a99c66b9f8487ff32a73adc12e7b238"   # dataset sim-jar-shadow2
PCT0 = "0.999950829"
# tag -> (duong, K, pct, n_t, khoa ADDENDUM-1)
ARMS = {
    "gkf-736-k12": ("iso-736", 12, "0.999924707", 736, "iso-736_K12"),
    "gkf-736-k16": ("iso-736", 16, "0.999937768", 736, "iso-736_K16"),
    "gkf-736-k32": ("iso-736", 32, "0.999981560", 736, "iso-736_K32"),
    "gkf-736-k40": ("iso-736", 40, "0.999999884", 736, "iso-736_K40"),
    "gkf-1k-k16": ("iso-1000", 16, "0.999922492", 1000, "iso-1000_K16"),
    "gkf-1k-k24": ("iso-1000", 24, "0.999939977", 1000, "iso-1000_K24"),
    "gkf-1k-k32": ("iso-1000", 32, "0.999971815", 1000, "iso-1000_K32"),
    "gkf-1k-k40": ("iso-1000", 40, "0.999993736", 1000, "iso-1000_K40"),
    "gkf-p0b-k48": ("p0b", 48, "0.999999869", 1000, None),
    "gkf-l2-k16": ("l2", 16, "0.999880000", None, None),
    "gkf-l2-k24": ("l2", 24, "0.999895000", None, None),
    "gkf-l2-k24b": ("l2", 24, "0.999870000", None, None),
    "gkf-l2-k32": ("l2", 32, "0.999915000", None, None),
}
TAGS = [BASE] + list(ARMS)
K_INFL = 13
INFL = math.sqrt(2.0 * math.log(K_INFL))
SAD.INFL = N.INFL = INFL
PEN, CRASH = 0.01675, -0.01
W0 = pd.Timestamp("2021-12-31")
YEARS = [2022, 2023, 2024, 2025]
QS = ["%dQ%d" % (y, q) for y in YEARS for q in (1, 2, 3, 4)]


def jd(o):
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    return str(o)


def logtxt(tag):
    for fn in ("logs/full.log", "logs/sim.out"):
        p = OUT % tag + fn
        if os.path.exists(p):
            with open(p, errors="ignore") as f:
                return f.read()
    return ""


def gate_line(txt):
    """dong [GATE-RATIO] cuoi: seen/pass/skipFull + theo quy (candidate, pass)."""
    ls = [ln for ln in txt.splitlines() if "[GATE-RATIO] GATE-RATIO on" in ln]
    ln = ls[-1] if ls else ""
    q = {a: (int(b), int(c)) for a, b, c in re.findall(r"(\d{4}Q\d):(\d+)/(\d+)", ln)}

    def g(k):
        m = re.search(r"\b" + k + r"=(\d+)", ln)
        return int(m.group(1)) if m else None
    return dict(q=q, seen=g("seen"), pass_all=g("pass"), skipFull=g("skipFull"))


def vline(txt):
    v = [ln for ln in txt.splitlines() if "md5 verified" in ln and "pred=" in ln]
    return v[-1].split("LOAD offline OK")[-1].strip() if v else None


def parity():
    """PARITY/HOP LE moi run + cong nen (md5 gkf-nen == gqsf-a1)."""
    res = {}
    ref_v = vline(logtxt(REF))
    for t in [REF] + TAGS:
        rj, pr, txt = N.result_json(t), N.prof_run(t), logtxt(t)
        K, pct = (24, PCT0) if t in (BASE, REF) else (ARMS[t][1], ARMS[t][2])
        f32 = "%.8f" % float(np.float32(float(pct)))
        gl = gate_line(txt)
        chk = dict(jar=(rj.get("jar_sha256") == JAR_SHA) if t != REF else True, ok=rj.get("ok") is True,
                   date_last=rj.get("date_last") == "20251230", mapper=(rj.get("symbol_mapper") or 0) >= 800,
                   topk=pr.get("SELECTOR_RANK_TOPK") == str(K) and ("SELECTOR_RANK_TOPK=%d " % K) in txt,
                   pct=pr.get("SIM_GATE_ROLLING_PCT") == pct and ("BAT: mode=ratio pct=" + f32 + " ") in txt,
                   skipfull=pr.get("GATE_QUOTA_SKIP_WHEN_FULL") == "true" and "[GATE-QUOTA] SKIP_WHEN_FULL=ON" in txt,
                   b0ov=all(pr.get(k) == str(v) for k, v in N.B0OV.items() if k != "SIM_GATE_ROLLING_PCT"),
                   pred_md5_verified=vline(txt) is not None and vline(txt) == ref_v)
        res[t] = dict(ok=bool(all(chk.values())), checks=chk, md5=R.md5_of(t), n=rj.get("n_trades"),
                      eq=rj.get("equity_final"), jar=str(rj.get("jar_sha256"))[:8], java_rc=rj.get("java_rc"),
                      pct_log=f32, gate=gl)
        log.info("PARITY %-12s %s md5=%s n=%s eq=%s jar=%s pct_log=%s pass=%s skipFull=%s %s", t,
                 "PASS" if res[t]["ok"] else "*** VOID ***", res[t]["md5"][:8], res[t]["n"], res[t]["eq"],
                 res[t]["jar"], f32, gl["pass_all"], gl["skipFull"], {k: v for k, v in chk.items() if not v})
    res["_gate_nen"] = dict(md5_nen=res[BASE]["md5"], md5_ref=res[REF]["md5"], ok=res[BASE]["md5"] == res[REF]["md5"],
                            vline=ref_v)
    log.info("CONG NEN md5 %s vs %s -> %s", res[BASE]["md5"][:8], res[REF]["md5"][:8], res["_gate_nen"]["ok"])
    return res


def umin(d):
    """phut UTC tuyet doi (truc DAY0) cua start leg (printDone gio local +7)."""
    return ((d["ts"] - pd.Timedelta(hours=R.TZ_SHIFT_H) - pd.Timestamp(R.DAY0))
            // pd.Timedelta(minutes=1)).astype(np.int64).to_numpy()


def _cw(args):
    """1 ngay ticker: (open, close) cua cac (sym, phut) can."""
    day, mins = args
    p = os.path.join(R.TICKER, "ticker_%s.bin.gz" % day)
    out = {}
    if not os.path.exists(p):
        return day, out
    t0 = int(pd.Timestamp(day).value // 10 ** 6)
    with gzip.open(p, "rb") as f:
        b = f.read()
    for k, v in jbin.iter_minutes(b):
        ss = mins.get(int((k - t0) // 60000))
        if not ss:
            continue
        mi = int((k - t0) // 60000)
        for s in ss:
            tup = v.get(s + "USDT")
            if tup is not None:
                # tuple jbin = (startTime, maxPrice, minPrice, priceClose, priceOpen, totalUsdt): thu tu field
                # Java serialization (primitive xep ABC) -> open = tup[4], close = tup[3] (R._work dung tup[3])
                assert tup[2] <= tup[4] <= tup[1] and tup[2] <= tup[3] <= tup[1], (s, k, tup)
                out["%s|%d" % (s, mi)] = (float(tup[4]), float(tup[3]))
    return day, out


def load_bars(legs, workers):
    """{(sym, phut UTC tuyet doi): (o, c)} cho phut start va start-1 cua moi leg moi tag (cache theo bo md5)."""
    key = sorted("%s:%d" % (t, len(d)) for t, d in legs.items())
    if os.path.exists(BAR_CACHE):
        c = json.load(open(BAR_CACHE))
        if c.get("key") == key:
            return {(k.rsplit("|", 1)[0], int(k.rsplit("|", 1)[1])): tuple(v) for k, v in c["bar"].items()}
    need = {}
    for d in legs.values():
        for s, m in zip(d["sym"], umin(d)):
            for mm in (int(m), int(m) - 1):
                need.setdefault(mm // 1440, {}).setdefault(mm % 1440, set()).add(s)
    jobs = [((pd.Timestamp(R.DAY0) + pd.Timedelta(days=int(dd))).strftime("%Y%m%d"), v) for dd, v in sorted(need.items())]
    log.info("BAR: %d ngay ticker can doc", len(jobs))
    bar = {}
    with Pool(workers) as pool:
        for i, (day, out) in enumerate(pool.imap_unordered(_cw, jobs, chunksize=4)):
            dd = (pd.Timestamp(day) - pd.Timestamp(R.DAY0)).days
            for k, v in out.items():
                s, mi = k.rsplit("|", 1)
                bar[(s, dd * 1440 + int(mi))] = v
            if i % 200 == 0:
                log.info("  BAR %d/%d", i, len(jobs))
    json.dump(dict(key=key, bar={"%s|%d" % k: v for k, v in bar.items()}), open(BAR_CACHE, "w"))
    return bar


def match_conv(d, bar):
    """ty le entry == close nen phut start (lag0) va start-1 (lag1)."""
    m = umin(d)
    e = d["entry"].to_numpy(float)
    r = {}
    for lag in (0, 1):
        ok = n = 0
        for s, mm, x in zip(d["sym"], m, e):
            b = bar.get((s, int(mm) - lag))
            if b is None or not x > 0:
                continue
            n += 1
            ok += abs(b[1] / x - 1.0) < 1e-5
        r[lag] = dict(n=n, match=ok, rate=ok / n if n else None)
    return r


def crash_mask(d, bar, lag):
    m = umin(d)
    br = np.full(len(d), np.nan)
    hit = np.zeros(len(d), bool)
    for i, (s, mm, x) in enumerate(zip(d["sym"], m, d["entry"].to_numpy(float))):
        b = bar.get((s, int(mm) - lag))
        if b is not None and b[0] > 0:
            br[i] = b[1] / b[0] - 1.0
            hit[i] = abs(b[1] / x - 1.0) < 1e-5 if x > 0 else False
    return br <= CRASH, br, hit


def stress_legs(d, crash):
    s = d.copy()
    pen = np.where(crash, PEN * s["notional"].to_numpy(float), 0.0)
    s["pen"] = pen
    s["pnl"] = s["pnl"] - pen
    s["entry"] = s["entry"] * np.where(crash, 1.0 + PEN, 1.0)   # unP MTM phut giam pen tu luc vao
    return s


def stress_daily(daily, s):
    """equity ngay (Update D 07:00 local) - tong phat cac chan co ts < D 07:00."""
    e = daily.copy()
    tu = (pd.to_datetime(e.index) + pd.Timedelta(hours=7)).to_numpy()
    ts = s["ts"].to_numpy()
    o = np.argsort(ts, kind="mergesort")
    cp = np.cumsum(s["pen"].to_numpy(float)[o])
    i = np.searchsorted(ts[o], tu, side="left")
    e["equity"] = e["equity"].astype(float) - np.where(i > 0, cp[np.clip(i - 1, 0, len(cp) - 1)], 0.0)
    return e


def cagr_from(eq, a, b):
    e = eq.copy()
    e.index = pd.to_datetime(e.index)
    x0, x1 = e[e.index <= pd.Timestamp(a)].iloc[-1], e[e.index <= pd.Timestamp(b)]
    yrs = (x1.index[-1] - pd.Timestamp(a)).days / 365.25
    return float(100 * ((x1.iloc[-1] / x0) ** (1 / yrs) - 1))


def year_ret(eq):
    e = eq.copy()
    e.index = pd.to_datetime(e.index)
    out, prev = {}, float(e[e.index <= "2021-12-31"].iloc[-1])
    for y in YEARS:
        v = float(e[e.index <= "%d-12-31" % y].iloc[-1])
        out[y], prev = 100 * (v / prev - 1), v
    return out


def metrics(key, tag, legs, daily, mtm):
    N.TAG[key], N.DESC[key] = tag, key
    m = N.arm_metrics(R, F3, key, legs, daily, mtm)
    eq = daily["equity"]
    m["cagr23"] = cagr_from(eq, "2022-12-31", "2025-12-30")
    m["yret"] = year_ret(eq)
    cl = legs[(legs["te"] >= "2022-01-01") & (legs["te"] < "2026-01-01")]
    s = cl.groupby(cl["te"].dt.normalize())["pnl"].sum()
    m["top10_share"] = float(100 * s.nlargest(10).sum() / s.sum())
    pr = legs[legs["level"].astype(str).str.strip() == "PREDICT_SYMBOL_TRADE"]
    em = pr["ts"].drop_duplicates()
    m["gmin_year"] = {y: int((em.dt.year == y).sum()) for y in YEARS}
    m["gmin_per_year"] = sum(m["gmin_year"].values()) / 4.0
    w = (pr["ts"] >= "2022-01-01") & (pr["ts"] < "2026-01-01")
    m["n_predict_2225"] = int(w.sum())
    m["n_predict_min_2225"] = int(pr.loc[w, "ts"].nunique())
    m["dd_mtm_year"] = {y: m["per_year"].get(y, {}).get("dd_mtm_year") for y in YEARS}
    m["n_year"] = {y: m["per_year"].get(y, {}).get("n") for y in YEARS}
    return m


def boot(daily, legs, sfx):
    """Delta vs NEN cung muc phi: CAGR (MTM ngay paired block-10d) + dPnL (paired theo ngay dong), raw + inflate k=13."""
    keys = [t + sfx for t in TAGS]
    bk = BASE + sfx
    eqs = {("P0" if k == bk else k): daily[k]["equity"][daily[k]["equity"].index >= W0].astype(float) for k in keys}
    idx = eqs["P0"].index
    for k, v in eqs.items():
        assert len(v) == len(idx) and (v.index == idx).all(), ("lech chi so ngay", k)
    obs, bs = SAD.daily_boot(eqs)
    pairs = [(k, bk) for k in keys if k != bk]
    dp = N.pnl_boot({k: legs[k] for k in keys}, idx, keys, pairs)
    con = {}
    for k in keys:
        if k == bk:
            continue
        con[k] = dict(cagr=SAD.ci_of(obs[k]["cagr"] - obs["P0"]["cagr"], bs[k]["cagr"] - bs["P0"]["cagr"]),
                      pnl=dp[k + "-" + bk])
    return obs, con


def rules(M, C, sfx):
    """§9 proxy 1 seed. n/nam > NEN => luat iso-1000; n <= NEN => luat iso-736 (thieu seed => khong GO duoc)."""
    b = M[BASE + sfx]
    out = {}
    for t in ARMS:
        x, c = M[t + sfx], C[t + sfx]
        dy = {y: x["yret"][y] - b["yret"][y] for y in YEARS}
        dd_ok = bool(x["dd_mtm"] >= -40 and x["dd_mtm22"] >= -40)
        if x["n_per_year"] > b["n_per_year"]:
            kind = "iso-1000"
            cs = dict(c1_dPnL_ciinfl_gt0=bool(c["pnl"]["d"] > 0 and c["pnl"]["ci_infl"][0] > 0), c2_maxDD_le40=dd_ok,
                      c3_cal22_ge090=bool(x["calmar22"] >= 0.9 * b["calmar22"]),
                      c4_3of4_dROI_ge0=bool(sum(v >= 0 for v in dy.values()) >= 3))
        else:
            kind = "iso-736"
            cs = dict(c1_cal22_gt_nen=bool(x["calmar22"] > b["calmar22"]),
                      c2_dCAGR22_ge0=bool(x["cagr22"] - b["cagr22"] >= 0), c3_maxDD_le40=dd_ok,
                      c4_dCAGR23_ge_m1=bool(x["cagr23"] - b["cagr23"] >= -1.0))
        out[t] = dict(kind=kind, checks=cs, ok=bool(all(cs.values())), dROI=dy,
                      n_dROI_ge0=int(sum(v >= 0 for v in dy.values())), dCAGR22=x["cagr22"] - b["cagr22"],
                      dCAGR23=x["cagr23"] - b["cagr23"], cal_ratio=x["calmar22"] / b["calmar22"],
                      boot_dCAGR=c["cagr"], boot_dPnL=c["pnl"])
    return out


def screen(M, sfx):
    """§5: moi duong top-2 theo Calmar22 MTM giam dan (hoa => CAGR22)."""
    out = {}
    for line in ("iso-736", "iso-1000"):
        ts = [t for t in ARMS if ARMS[t][0] == line]
        rk = sorted(ts, key=lambda t: (-M[t + sfx]["calmar22"], -M[t + sfx]["cagr22"]))
        out[line] = dict(rank=rk, top2=rk[:2],
                         quota_dev={t: (M[t + sfx]["n_per_year"] - ARMS[t][3]) / ARMS[t][3] for t in ts})
    return out


def diagnose(par, M):
    """vi sao iso-n hong: pass offline (ADDENDUM-1) vs pass sim (log) vs lenh sim; float32 pct; tap trung phut."""
    cal = json.load(open(CALIB))
    arms = cal["arms"]
    mins_2225 = (pd.Timestamp("2026-01-01") - pd.Timestamp("2022-01-01")) // pd.Timedelta(minutes=1)
    out = {}
    for t in TAGS:
        pct = PCT0 if t == BASE else ARMS[t][2]
        f = float(np.float32(float(pct)))
        g = par[t]["gate"]
        # log Java theo quy = "pass/candidate" -> q[k] = (pass, candidate)
        sp = sum(g["q"].get(q, (0, 0))[0] for q in QS)
        seen = sum(g["q"].get(q, (0, 0))[1] for q in QS)
        m90 = int(round(seen / mins_2225 * 90 * 1440))   # co buffer 90 ngay uoc luong (nap r ~ ung vien PREDICT)
        ck = ARMS[t][4] if t in ARMS else None
        off = arms.get(ck, {}) if ck else {}
        offp = off.get("pass_2225", cal["meta"]["pass_nen_s42"] if t == BASE else None)
        offm = off.get("minutes_open_2225")
        x = M[t]
        out[t] = dict(pct=pct, pct_f32="%.10f" % f, one_m_pct=1 - float(pct), one_m_pct_f32=1 - f,
                      f32_rel_err=(1 - f) / (1 - float(pct)) - 1, k_eff_tick=seen / mins_2225,
                      rank_top_exact=(1 - float(pct)) * (m90 - 1),
                      rank_top_f32=(m90 - 1) - math.floor(f * (m90 - 1)),
                      rank_top_f64=(m90 - 1) - math.floor(float(pct) * (m90 - 1)),
                      pass_off_2225=offp, pass_sim_2225=sp, sim_over_off=(sp / offp) if offp else None,
                      pass_sim_year={y: sum(g["q"].get("%dQ%d" % (y, q), (0, 0))[0] for q in (1, 2, 3, 4)) for y in YEARS},
                      skipFull=g["skipFull"], n_predict_2225=x["n_predict_2225"],
                      predict_per_pass=x["n_predict_2225"] / sp if sp else None,
                      min_open_off_2225=offm, min_entry_sim_2225=x["n_predict_min_2225"],
                      pass_per_min_off=(offp / offm) if offp and offm else None,
                      predict_per_min_sim=x["n_predict_2225"] / x["n_predict_min_2225"] if x["n_predict_min_2225"] else None,
                      n_per_year=x["n_per_year"], n_t=ARMS[t][3] if t in ARMS else 736)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(D, exist_ok=True)
    par = parity()
    void = [t for t in TAGS if not par[t]["ok"]]
    assert par["_gate_nen"]["ok"], "CONG NEN TRUOT -> DUNG"
    assert not void, ("VOID", void)
    legs = {t: R.load_legs(t) for t in TAGS}
    daily = {t: R.load_daily(t) for t in TAGS}
    md5 = {t: par[t]["md5"] for t in TAGS}
    bar = load_bars(legs, a.workers)
    conv = {t: match_conv(legs[t], bar) for t in TAGS}
    lag = 0 if conv[BASE][0]["match"] >= conv[BASE][1]["match"] else 1
    log.info("QUY UOC NEN QUYET DINH: lag=%d  %s", lag, conv[BASE])
    cr = {}
    for t in TAGS:
        msk, br, hit = crash_mask(legs[t], bar, lag)
        s = stress_legs(legs[t], msk)
        legs[t + "#S"], daily[t + "#S"] = s, stress_daily(daily[t], s)
        lv = legs[t]["level"].astype(str).str.strip()
        w = ((legs[t]["ts"] >= "2022-01-01") & (legs[t]["ts"] < "2026-01-01")).to_numpy()
        cr[t] = dict(n=int(len(msk)), n_crash=int(msk.sum()), n_crash_2225=int((msk & w).sum()),
                     share_crash=float(msk.mean()), no_bar=int(np.isnan(br).sum()), entry_match=float(hit.mean()),
                     pen_sum=float(s["pen"].sum()), pen_sum_2225=float(s["pen"].to_numpy()[w].sum()),
                     by_level={k: dict(n=int((lv == k).sum()), crash=int((msk & (lv == k).to_numpy()).sum()),
                                       match=float(hit[(lv == k).to_numpy()].mean())) for k in sorted(lv.unique())})
        log.info("CRASH %-12s n=%d crash=%d (%.2f%%) no_bar=%d match=%.4f pen=%.0f", t, cr[t]["n"], cr[t]["n_crash"],
                 100 * cr[t]["share_crash"], cr[t]["no_bar"], cr[t]["entry_match"], cr[t]["pen_sum"])
    keys = TAGS + [t + "#S" for t in TAGS]
    km5 = {k: md5[k.split("#")[0]] + ("#S%.5f:lag%d" % (PEN, lag) if "#S" in k else "") for k in keys}
    raw = json.load(open(MTM_CACHE)) if os.path.exists(MTM_CACHE) else {}
    miss = {k: legs[k] for k in keys if raw.get(k, {}).get("md5") != km5[k]}
    if miss:
        log.info("MTM phut can tinh %d: %s", len(miss), sorted(miss))
        new = R.run_mtm(miss, workers=a.workers, chunk=30)
        for k, v in new.items():
            v["md5"] = km5[k]
            raw[k] = v
        json.dump(raw, open(MTM_CACHE, "w"))

    M = {k: metrics(k, k.split("#")[0], legs[k], daily[k], raw[k]["legacy"]) for k in keys}
    # tu kiem: NEN (md5 = gqsf-a1) phai khop docs/result/gate_skipfull.json ON_A1 (cung thuoc)
    ref = json.load(open(GQSF))["metrics"]["ON_A1"]
    bad = []
    for a_, b_ in (("cagr22", "cagr22"), ("calmar22", "calmar22"), ("dd_mtm22", "dd_mtm22"), ("uw_mtm22", "uw_mtm22"),
                   ("n_per_year", "n_per_year"), ("cagr23", "cagr23"), ("sum_pnl_2022_25", "sum_pnl_2022_25"),
                   ("dd_mtm", "dd_mtm")):
        if abs(M[BASE][a_] - ref[b_]) > 1e-6 * max(1.0, abs(ref[b_])):
            bad.append((a_, M[BASE][a_], ref[b_]))
    log.info("TU KIEM NEN vs gate_skipfull.json ON_A1: %d lech %s", len(bad), bad)
    assert not bad, "TU KIEM LECH -> DUNG"
    obs_b, con_b = boot(daily, legs, "")
    obs_s, con_s = boot(daily, legs, "#S")
    C = dict(con_b, **con_s)
    rb, rs = rules(M, C, ""), rules(M, C, "#S")
    sc_b, sc_s = screen(M, ""), screen(M, "#S")
    dg = diagnose(par, M)
    claw = {x["tag"]: x for x in json.load(open(CLAW))["arms"]}
    verdict = {}
    for t in ARMS:
        both = rb[t]["ok"] and rs[t]["ok"]
        if ARMS[t][0] == "l2":
            tag = "ngoai pre-reg - chi bao cao"
        elif ARMS[t][0] == "p0b":
            tag = "P0.b - chi bao cao (khong cham GO)"
        else:
            tag = "Phase 1"
        if rb[t]["kind"] == "iso-736":
            v = ("dat proxy base+stress nhung CHUA DU SEED (can 3/3)" if both else "TRUOT proxy")
        else:
            v = ("dat proxy 1 seed (chua du 3 seed)" if both else "TRUOT")
        fails = sorted({k for k, ok in rb[t]["checks"].items() if not ok} | {k + "@S" for k, ok in rs[t]["checks"].items() if not ok})
        verdict[t] = dict(scope=tag, rule=rb[t]["kind"], verdict=v, fails=fails)
        log.info("VERDICT %-12s %-8s %s fails=%s [%s]", t, rb[t]["kind"], v, fails, tag)
    log.info("SCREEN base %s | stress %s", {k: v["top2"] for k, v in sc_b.items()}, {k: v["top2"] for k, v in sc_s.items()})

    js = dict(title="AUDIT_GKF_PHASE1_20261007", prereg="docs/prereg/PREREG_GATE_K_FRONTIER.md",
              prereg_commits=["4e4fc975", "36b5d136"], claw_result="0a3f10d0", k_infl=K_INFL, inflate=INFL,
              nrep=2000, seed=20260905, block_days=10, window="2022-01-01..2025-12-30 (rebase 2021-12-31)",
              stress=dict(pen=PEN, crash_thr=CRASH, decision_bar_lag=lag, match_conv=conv, per_tag=cr,
                          note="post-hoc bac 1: gia vao +1.675% chan sap, PnL -1.675% notional; khong mo phong lai"),
              parity=par, metrics=M, contrasts=C, rules_base=rb, rules_stress=rs, verdict=verdict,
              screen_base=sc_b, screen_stress=sc_s, diagnose=dg, boot_obs=dict(base=obs_b, stress=obs_s),
              claw_daily={t: dict(calmar22=claw[t]["calmar22"], cagr22=claw[t]["cagr22"], maxdd22=claw[t]["maxdd22"])
                          for t in TAGS if t in claw})
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=jd)
    with open(MD_OUT, "w") as fo:
        fo.write("\n".join(tables(js)))
    log.info("OUT %s %s", JSON_OUT, MD_OUT)


def fm(x, d=2, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    s = (("%+." if sign else "%.") + str(d) + "f") % x
    return s.replace(".", ",")


def ci(c, d=2):
    return "%s [%s; %s] {%s; %s}" % (fm(c["d"], d, True), fm(c["ci_raw"][0], d, True), fm(c["ci_raw"][1], d, True),
                                     fm(c["ci_infl"][0], d, True), fm(c["ci_infl"][1], d, True))


def row(c):
    return "| " + " | ".join(str(x) for x in c) + " |"


def tbl(h, rows):
    return [row(h), row(["---"] * len(h))] + [row(r) for r in rows] + [""]


def lab(t):
    return t.replace("gkf-", "") + ("†" if t in ARMS and ARMS[t][0] in ("l2", "p0b") else "")


def tables(js):
    M, C, par, cd, dg = js["metrics"], js["contrasts"], js["parity"], js["claw_daily"], js["diagnose"]
    L = ["## 0. Parity / hợp lệ", ""]
    rows = [[lab(t), par[t]["md5"][:8], par[t]["jar"], par[t]["n"], par[t]["eq"], par[t]["pct_log"],
             par[t]["gate"]["pass_all"], par[t]["gate"]["skipFull"], "PASS" if par[t]["ok"] else "VOID"]
            for t in [REF] + TAGS]
    L += tbl(["run", "md5 printDone", "jar", "n", "eq", "pct log (f32)", "pass gate", "skipFull", "parity"], rows)
    L += ["## 1. Bảng chính (base, phí legacy as-is; MTM phút)", ""]
    rows = []
    for t in TAGS:
        x = M[t]
        k = 24 if t == BASE else ARMS[t][1]
        p = PCT0 if t == BASE else ARMS[t][2]
        rows.append([lab(t), k, p, fm(x["n_per_year"], 0), "%s (%s)" % (fm(x["gmin_per_year"], 0), x["gmin_year"][2022]),
                     fm(x["cagr22"]), fm(x["dd_mtm22"]), fm(x["calmar22"], 3), fm(cd.get(t, {}).get("calmar22"), 3),
                     fm(x["uw_mtm22"], 0), fm(x["hour0_2022_25"]["share0"], 1), fm(x["top10_share"], 1),
                     par[t]["gate"]["skipFull"], "%s/%s" % (fm(x["conc22"]["expo_mean"], 1), fm(x["conc22"]["expo_p95"], 1))])
    L += tbl(["arm", "K", "pct", "n/năm", "phút vào/năm (2022)", "CAGR22", "maxDD22 MTM", "Calmar22 MTM",
              "Calmar daily (claw)", "UW22 ng", "ΣPnL 0h %", "ΣPnL top10 ngày %", "skipFull", "U TB/p95 %"], rows)
    L += ["### 1b. Stress (+1,675%/chân vào nến 1m ≤ −1%, post-hoc)", ""]
    rows = []
    for t in TAGS:
        x, b, c = M[t + "#S"], M[t], js["stress"]["per_tag"][t]
        rows.append([lab(t), "%d (%s%%)" % (c["n_crash_2225"], fm(100 * c["share_crash"], 1)), fm(c["pen_sum_2225"], 0),
                     fm(x["cagr22"]), fm(x["cagr22"] - b["cagr22"], 2, True), fm(x["dd_mtm22"]), fm(x["calmar22"], 3),
                     fm(x["uw_mtm22"], 0), fm(x["hour0_2022_25"]["share0"], 1), fm(x["top10_share"], 1)])
    L += tbl(["arm", "chân sập 22–25 (% mọi chân)", "Σphạt 22–25", "CAGR22 S", "Δ vs base", "maxDD22 S", "Calmar22 S",
              "UW22 S", "ΣPnL 0h % S", "top10 % S"], rows)
    return L + tables2(js)


def tables2(js):
    M, C, rb, rs, dg = js["metrics"], js["contrasts"], js["rules_base"], js["rules_stress"], js["diagnose"]
    L = ["## 2. Δ vs NỀN — điểm [CI95 raw] {CI inflate k=13, ×%.3f}" % INFL, ""]
    rows = [[lab(t), ci(C[t]["cagr"]), ci(C[t]["pnl"], 0), ci(C[t + "#S"]["cagr"]), ci(C[t + "#S"]["pnl"], 0)]
            for t in ARMS]
    L += tbl(["arm", "ΔCAGR22 base (pp)", "ΔPnL base", "ΔCAGR22 stress", "ΔPnL stress"], rows)
    L += ["### 2b. ΔROI năm (pp, equity ngày) và ΔCAGR23 (ex-2022) — base / stress", ""]
    rows = [[lab(t)] + ["%s / %s" % (fm(rb[t]["dROI"][y], 2, True), fm(rs[t]["dROI"][y], 2, True)) for y in YEARS] +
            ["%s / %s" % (fm(rb[t]["dCAGR23"], 2, True), fm(rs[t]["dCAGR23"], 2, True)),
             "%d / %d" % (rb[t]["n_dROI_ge0"], rs[t]["n_dROI_ge0"])] for t in ARMS]
    L += tbl(["arm"] + ["ΔROI %d" % y for y in YEARS] + ["ΔCAGR23", "#năm ΔROI≥0"], rows)
    L += ["## 3. Luật §9 (proxy 1 seed) — base | stress", ""]
    rows = []
    for t in ARMS:
        v = js["verdict"][t]
        rows.append([lab(t), rb[t]["kind"], fm(M[t]["n_per_year"], 0), fm(rb[t]["cal_ratio"], 3), fm(rs[t]["cal_ratio"], 3),
                     " ".join(k.split("_")[0] + ("✓" if ok else "✗") for k, ok in rb[t]["checks"].items()),
                     " ".join(k.split("_")[0] + ("✓" if ok else "✗") for k, ok in rs[t]["checks"].items()),
                     v["verdict"], v["scope"]])
    L += tbl(["arm", "luật", "n/năm", "Cal×NỀN base", "Cal×NỀN stress", "base", "stress", "verdict", "phạm vi"], rows)
    L += ["## 4. Sàng lọc Phase 1 (top-2 mỗi đường theo Calmar22 MTM, hoà ⇒ CAGR22)", ""]
    rows = []
    for line in ("iso-736", "iso-1000"):
        sb, ss = js["screen_base"][line], js["screen_stress"][line]
        rows.append([line, " > ".join("%s(%s)" % (lab(t), fm(M[t]["calmar22"], 3)) for t in sb["rank"]),
                     ", ".join(lab(t) for t in sb["top2"]), ", ".join(lab(t) for t in ss["top2"]),
                     ", ".join("%s %s%%" % (lab(t), fm(100 * v, 0, True)) for t, v in sb["quota_dev"].items() if abs(v) > 0.15)])
    L += tbl(["đường", "xếp hạng base", "top-2 base (luật)", "top-2 stress (tham khảo)", "lệch quota >15%"], rows)
    L += ["## 5. Chẩn đoán iso-n (2022–25)", ""]
    rows = [[lab(t), dg[t]["pct"], dg[t]["pct_f32"], "%.3e / %.3e (%s%%)" % (dg[t]["one_m_pct"], dg[t]["one_m_pct_f32"],
             fm(100 * dg[t]["f32_rel_err"], 2, True)), fm(dg[t]["k_eff_tick"], 1),
             "%s / %s / %s" % (fm(dg[t]["rank_top_exact"], 2), fm(dg[t]["rank_top_f64"], 0), fm(dg[t]["rank_top_f32"], 0)),
             dg[t]["pass_off_2225"], dg[t]["pass_sim_2225"], fm(dg[t]["sim_over_off"], 3), dg[t]["skipFull"],
             dg[t]["n_predict_2225"], fm(dg[t]["predict_per_pass"], 3), dg[t]["min_open_off_2225"],
             dg[t]["min_entry_sim_2225"], fm(dg[t]["pass_per_min_off"], 2), fm(dg[t]["predict_per_min_sim"], 2)]
            for t in TAGS]
    L += tbl(["arm", "pct", "pct f32", "1−pct / 1−pct_f32 (lệch)", "ứng viên/tick", "hạng từ đỉnh q: liên tục / f64 / f32",
              "pass offline", "pass sim", "sim/off", "skipFull", "lệnh PREDICT", "PREDICT/pass", "phút mở off",
              "phút vào sim", "pass/phút off", "PREDICT/phút sim"], rows)
    return L


if __name__ == "__main__":
    main()
