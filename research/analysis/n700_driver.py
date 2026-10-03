#!/usr/bin/env python3
"""N700 — tang so lenh duoi luat owner MOI (10-03). Pre-reg docs/prereg/PREREG_N700.md (commit 00ca54b6, chot TRUOC).

Arm (k=4): A1 = B0 + SELECTOR_RANK_TOPK=24 ; A2 = B0 + SIM_GATE_ROLLING_PCT=0.99985 (K16) ;
A3 = GEOM-K16 (bins g42) + TOPK 24 ; A4 = GEOM-K16 + PCT 0.99985. Nen: B0 = selab-p0 (ff3ce513), G42 = geom-g42.
B0REF = B0 nguyen van (ks.submit) cung dot => cong parity anh Kaggle (value-identical selab-p0).
Kernel = tools/kaggle_sim.py HEAD (NOWRITE242, md5 8b60b00a). A3/A4 dung duong s1_geom_sim (label_firsthit template).
Thuoc: MTM ngay paired block-10d NREP 2000 seed 20260905 (cua so 2022+), inflate sqrt(2 ln 4); MTM phut (run_mtm).
THUAN PYTHON khi cham; 0 Java tren Oracle; 0 cham 242/shadow.
Usage: python3 n700_driver.py submit ARM.. --code-sha SHA | status ARM.. | fetch ARM.. | parity | score [--workers 3]
"""
import argparse
import hashlib
import json
import logging
import math
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
HERE = os.path.join(REPO, "research/analysis")
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("n700")

ARMS = ["A1", "A2", "A3", "A4"]
TAG = {"A1": "n700-a1", "A2": "n700-a2", "A3": "n700-a3", "A4": "n700-a4", "B0REF": "n700-b0ref",
       "B0": "selab-p0", "G42": "geom-g42"}
BASE = {"A1": "B0", "A2": "B0", "A3": "G42", "A4": "G42"}
EXTRA = {"A1": {"SELECTOR_RANK_TOPK": 24}, "A2": {"SIM_GATE_ROLLING_PCT": 0.99985},
         "A3": {"SELECTOR_RANK_TOPK": 24}, "A4": {"SIM_GATE_ROLLING_PCT": 0.99985}, "B0REF": {}}
DESC = {"B0": "B0 (K16, pct 0.99995)", "G42": "GEOM-K16 g42", "A1": "B0 + K24", "A2": "B0 + pct 0.99985",
        "A3": "GEOM + K24", "A4": "GEOM + pct 0.99985", "B0REF": "B0REF (parity)"}
PROFILE = "r4_kg0_k16_f015_g155"
B0OV = {"SIM_GATE_ROLLING_MODE": "ratio", "SIM_GATE_ROLLING_DAYS": 90, "SIM_GATE_ROLLING_PCT": 0.999950829,
        "TS_GIVEBACK_RATIO": 1.0, "SIM_TS_MAX_GAP": 0.03, "SIM_TS_MAX_GAP_WEAK": 0.03}
KS_MD5_WANT = "8b60b00afad39f2528aaa15092225c9b"
JAR_DS, JAR_SHA = "sim-jar-gdv2", "7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a"
BUNDLE = "sim-x1-2021-bundle"
B0_MD5, B0_N, B0_EQ = "ff3ce513edf2316088a4b5ac464f76dc", 2517, 131908
G42_BINS_SHA = "6171f2cc0c541f1a584d0ca0f97fc35382b4f8edf9b929cb1f974f845de53d64"
K_INFL = 4
INFL = math.sqrt(2.0 * math.log(K_INFL))     # 1.6651
NREP, SEED, BLOCK_D = 2000, 20260905, 10
W0 = pd.Timestamp("2021-12-31")              # equity rebase; cua so chinh 2022-01-01..2025-12-30
YEARS = [2022, 2023, 2024, 2025]
N_YEAR_MIN, DD_MIN, CAL_MULT = 700.0, -40.0, 0.80
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
D = "/home/ubuntu/claude_master/1003/n700"
MTM_CACHE = D + "/mtm.json"
JSON_OUT = os.path.join(REPO, "docs/result/n700.json")
PRIMARY = [("A1", "B0"), ("A2", "B0"), ("A3", "G42"), ("A4", "G42")]
CROSS = [("G42", "B0"), ("A3", "B0"), ("A4", "B0"), ("A1", "A2"), ("A3", "A1"), ("A4", "A2"), ("B0REF", "B0")]


def ks_mod():
    from tools import kaggle_sim as ks
    md5 = hashlib.md5(open(os.path.join(REPO, "tools/kaggle_sim.py"), "rb").read()).hexdigest()
    assert md5 == KS_MD5_WANT, ("tools/kaggle_sim.py khong phai HEAD NOWRITE242", md5)
    assert "NOWRITE_HOST" in ks.KERNEL_TEMPLATE and "SYMBOL_MAPPER_PREFLIGHT_FAIL" in ks.KERNEL_TEMPLATE
    return ks


def submit(arm, code_sha):
    ks = ks_mod()
    ov = dict(B0OV)
    ov.update(EXTRA[arm])
    tag = TAG[arm]
    if arm in ("A1", "A2", "B0REF"):
        r = ks.submit(tag, PROFILE, ov, jar_ds=JAR_DS, bundle_ds=BUNDLE, sim_end_date="20251231", xmx="22g",
                      timeout_s=5400, code_sha=code_sha)
        log.info("PUSHED %s %s ov=%s", arm, r, json.dumps(ov))
        return
    # A3/A4: duong GEOM y het s1_geom_sim.submit (G42), chi doi tag + overrides
    import selector_ablation_driver as SAD
    import label_firsthit_sim as LFS
    sh = json.load(open("/home/ubuntu/claude_master/1003/geom/sim_sha256.json"))
    assert sh["G42"] == G42_BINS_SHA
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": PROFILE, "overrides": ov, "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 7200, "code_sha": code_sha, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "",
           "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
           "sel_arm": "P0", "fh_arm": "G42", "fh_ds": "geom-bins-g42", "want_bins_sha": sh["G42"],
           "src_bins_sha": sh["G42"], "moc21_ds": SAD.MOC21_DS, "liq_ds": SAD.LIQ_DS,
           "orig_md5_funding": "8e57d900d5c54c744bfcaf5c9b27fc93"}
    code = LFS.template().replace("__CFG_JSON__", repr(json.dumps(cfg)))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [ks.USER + "/" + BUNDLE] + ks.TICKER_DS
                               + [ks.USER + "/" + JAR_DS, ks.USER + "/" + SAD.MOC21_DS, ks.USER + "/geom-bins-g42"],
            "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    r = ks._api().kernels_push(folder)
    log.info("PUSHED %s %s ov=%s", arm, getattr(r, "url", r), json.dumps(ov))


def result_json(tag):
    p = OUT % tag + "result.json"
    return json.load(open(p)) if os.path.exists(p) else {}


def prof_run(tag):
    p = OUT % tag + "prof_run.properties"
    out = {}
    if os.path.exists(p):
        for ln in open(p):
            if "=" in ln and not ln.startswith("#"):
                k, v = ln.rstrip("\n").split("=", 1)
                out[k.strip()] = v.strip()
    return out


def parity():
    import reset_rule_score as R
    import selector_ablation_driver as SAD
    t = TAG["B0REF"]
    if not os.path.exists(OUT % t + "storage/printDone.csv"):
        log.info("B0REF chua co printDone")
        return None
    rj = result_json(t)
    md5 = R.md5_of(t)
    n = len(R.load_legs(t))
    eq = float(R.load_daily(t)["equity"].iloc[-1])
    ve = SAD.printdone_valeq(t, TAG["B0"])
    chk = dict(n=n == B0_N, eq=round(eq) == B0_EQ, jar=rj.get("jar_sha256") == JAR_SHA,
               mapper=(rj.get("symbol_mapper") or 0) >= 800,
               value_identical_vs_selab_p0=ve["cells_val_diff"] == 0 and ve["rows_a"] == ve["rows_b"])
    ok = all(chk.values())
    res = dict(ok=bool(ok), checks=chk, md5=md5, md5_eq_ff3ce513=md5 == B0_MD5, n=n, eq=eq, valeq=ve)
    # thong tin: A1 vs de-p2 (anh cu) theo gia tri
    if os.path.exists(OUT % TAG["A1"] + "storage/printDone.csv"):
        res["A1_vs_de-p2_valeq"] = SAD.printdone_valeq(TAG["A1"], "de-p2")
        res["A1_md5"] = R.md5_of(TAG["A1"])
    os.makedirs(D, exist_ok=True)
    json.dump(res, open(JSON_OUT + ".parity", "w"), indent=1)
    log.info("PARITY %s", json.dumps(res, default=str))
    return res


def conc_exposure(legs, daily, t0=None):
    """So lenh mo dong thoi + exposure (Sigma margin mo / equity cuoi ngay truoc) — time-weighted tren luoi PHUT.
    t0: chi tinh tu moc nay (cua so); lenh mo truoc t0 van tinh neu con mo."""
    lo = legs["ts"].min().floor("min") if t0 is None else max(pd.Timestamp(t0), legs["ts"].min().floor("min"))
    hi = min(legs["te"].max().ceil("min"), pd.Timestamp("2025-12-31"))
    T = int((hi - lo) / pd.Timedelta(minutes=1)) + 1
    a = ((legs["ts"] - lo) // pd.Timedelta(minutes=1)).to_numpy().astype(np.int64)
    b = ((legs["te"] - lo) // pd.Timedelta(minutes=1)).to_numpy().astype(np.int64)
    a, b = np.clip(a, 0, T), np.clip(b, 0, T)
    m = legs["margin"].to_numpy(float)
    cnt, mar = np.zeros(T + 1), np.zeros(T + 1)
    np.add.at(cnt, a, 1)
    np.add.at(cnt, b, -1)
    np.add.at(mar, a, m)
    np.add.at(mar, b, -m)
    c, g = np.cumsum(cnt)[:T], np.cumsum(mar)[:T]
    days = (lo + pd.to_timedelta(np.arange(T), unit="min")).normalize()
    eq = daily["equity"].copy()
    eq.index = pd.to_datetime(eq.index).normalize()
    eqp = eq.shift(1).reindex(days, method="ffill").to_numpy()
    eqp = np.where(np.isfinite(eqp), eqp, float(eq.iloc[0]))
    ex = 100.0 * g / eqp
    return dict(open_mean=float(c.mean()), open_p95=float(np.percentile(c, 95)), open_max=int(c.max()),
                open_p95_when_open=float(np.percentile(c[c > 0], 95)) if (c > 0).any() else 0.0,
                pct_time_open=float(100 * (c > 0).mean()), expo_mean=float(ex.mean()),
                expo_p95=float(np.percentile(ex, 95)), expo_max=float(ex.max()))


def arm_metrics(R, F3, k, legs, daily, mtm):
    m = R.core_metrics(k, legs, daily, "legacy")
    lw = legs[legs["ts"] >= W0 + pd.Timedelta(days=1)].reset_index(drop=True)
    m22 = R.core_metrics(k, lw, daily.loc[W0:], "legacy")
    yr = {int(str(y)[:4]): float(v) for y, v in m["yr"].items()}
    cl = legs[(legs["te"] >= "2022-01-01") & (legs["te"] < "2026-01-01")]
    st = legs["status"].astype(str)
    per_year = {}
    for y, g in cl.groupby(cl["te"].dt.year):
        s = g["status"].astype(str)
        per_year[int(y)] = dict(n=int(len(g)), sum_pnl=float(g["pnl"].sum()), win=float(100 * (g["profit"] > 0).mean()),
                                sl=float(100 * (s == "STOP_LOSS_DONE").mean()), roi_lenh=float(g["profit"].mean()),
                                roi_year=yr.get(int(y)), dd_mtm_year=float(mtm["dd_year"].get(str(y), mtm["dd_year"].get(y, np.nan))))
    h0 = F3.hour0(legs)
    h022 = F3.hour0(cl)
    return dict(tag=TAG[k], desc=DESC[k], n=int(len(legs)), n_close_2022_25=int(len(cl)), n_per_year=len(cl) / 4.0,
                equity=float(daily["equity"].iloc[-1]), sum_pnl=float(legs["pnl"].sum()),
                sum_pnl_2022_25=float(cl["pnl"].sum()), cagr=float(m["cagr"]), cagr22=float(m22["cagr"]),
                dd_mtm=float(mtm["dd_total"]), dd_mtm22=float(mtm["dd_win"]), uw_mtm=float(mtm["uw_total_days"]),
                uw_mtm22=float(mtm["uw_win_days"]), calmar=float(m["cagr"] / abs(mtm["dd_total"])),
                calmar22=float(m22["cagr"] / abs(mtm["dd_win"])), dd_daily=float(m["maxdd_daily"]),
                win=float(100 * (legs["profit"] > 0).mean()), sl=float(100 * (st == "STOP_LOSS_DONE").mean()),
                win22=float(100 * (cl["profit"] > 0).mean()),
                sl22=float(100 * (cl["status"].astype(str) == "STOP_LOSS_DONE").mean()),
                roi_lenh=float(legs["profit"].mean()), roi_year=yr, per_year=per_year, hour0=h0, hour0_2022_25=h022,
                conc=conc_exposure(legs, daily), conc22=conc_exposure(legs, daily, "2022-01-01"),
                qmin=float(m["qmin"]), neg_year=m["neg_year"], conc_coin_max=float(m["conc_max"]),
                gross_max=float(m["gross_max"]))


def pnl_boot(legs, idx, keys, pairs):
    """dPnL paired: PnL thuc hien theo NGAY DONG (cua so idx[1:]), block-10d cung so do khoi voi SAD.daily_boot."""
    days = idx[1:]
    P = {}
    for k in keys:
        L = legs[k]
        s = L.groupby(L["te"].dt.normalize())["pnl"].sum()
        P[k] = s.reindex(days).fillna(0.0).to_numpy()
    T = len(days)
    nb = int(math.ceil(T / BLOCK_D))
    rng = np.random.default_rng(SEED)
    picks = []
    for _ in range(NREP):
        st = rng.integers(0, T - BLOCK_D + 1, size=nb)
        picks.append((st[:, None] + np.arange(BLOCK_D)[None, :]).ravel()[:T])
    out = {}
    for x, y in pairs:
        if x not in P or y not in P:
            continue
        d = P[x] - P[y]
        bs = np.array([d[p].sum() for p in picks])
        lo, hi = np.percentile(bs, [2.5, 97.5])
        obs = float(d.sum())
        out[x + "-" + y] = dict(d=obs, ci_raw=[float(lo), float(hi)],
                                ci_infl=[float(obs - (obs - lo) * INFL), float(obs + (hi - obs) * INFL)])
    return out


def score(workers, tagmap=None):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401  (side effect: MTMState co cua so 2022+)
    import flat3_crashpen_driver as F3
    import selector_ablation_driver as SAD
    R.MTM_COSTS = {"legacy": R.LEGACY}
    SAD.INFL = INFL
    if tagmap:
        TAG.update(tagmap)
    par = json.load(open(JSON_OUT + ".parity")) if os.path.exists(JSON_OUT + ".parity") else None
    if not tagmap and not (par and par["ok"]):
        log.info("VOID: parity B0REF chua PASS -> khong cham")
        sys.exit(3)
    keys = ["B0", "G42"] + [k for k in ARMS + ["B0REF"] if os.path.exists(OUT % TAG[k] + "storage/printDone.csv")]
    legs, daily, md5, rj, pr = {}, {}, {}, {}, {}
    void = {}
    for k in keys:
        t = TAG[k]
        legs[k], daily[k], md5[k], rj[k], pr[k] = R.load_legs(t), R.load_daily(t), R.md5_of(t), result_json(t), prof_run(t)
        sel = rj[k].get("sel") or {}
        log.info("%-5s %-11s n=%d eq=%.0f md5=%s jar_ok=%s mapper=%s phash=%s bins_ok=%s", k, t, len(legs[k]),
                 daily[k]["equity"].iloc[-1], md5[k], rj[k].get("jar_sha256") == JAR_SHA, rj[k].get("symbol_mapper"),
                 rj[k].get("profile_hash"), sel.get("bins_ok"))
        assert rj[k].get("jar_sha256") == JAR_SHA and (rj[k].get("symbol_mapper") or 0) >= 800, ("jar/mapper", k)
    # Cong 1 — key co hieu luc
    for k in [x for x in ARMS if x in keys]:
        b = BASE[k]
        want = {kk: str(v) for kk, v in EXTRA[k].items()}
        g = dict(md5_diff=md5[k] != md5[b], phash_diff=rj[k].get("profile_hash") != rj[b].get("profile_hash"),
                 prof_has_override=all(pr[k].get(kk) == v for kk, v in want.items()))
        if b == "G42":
            sel = rj[k].get("sel") or {}
            g["bins_ok"] = sel.get("bins_ok") is True and sel.get("bins_sha256") == G42_BINS_SHA
        void[k] = dict(ok=all(g.values()), checks=g, prof={kk: pr[k].get(kk) for kk in want})
        log.info("CONG1 %s %s %s", k, "PASS" if void[k]["ok"] else "*** FAIL => VOID ***", g)
    arms_ok = [k for k in ARMS if k in keys and void[k]["ok"]]
    # MTM phut, cache theo md5
    raw = json.load(open(MTM_CACHE)) if os.path.exists(MTM_CACHE) else {}
    miss = {k: legs[k] for k in keys if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM cache %s; can tinh %s", sorted(raw), sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        os.makedirs(D, exist_ok=True)
        json.dump(raw, open(MTM_CACHE, "w"))
    M = {k: arm_metrics(R, F3, k, legs[k], daily[k], raw[k]["legacy"]) for k in keys}
    for k in keys:
        M[k]["md5"] = md5[k]
        M[k]["overlap_vs_base"] = SAD.overlap(legs[BASE.get(k, "B0")], legs[k])
    # bootstrap paired ngay MTM, cua so 2022+
    eqs = {("P0" if k == "B0" else k): daily[k]["equity"][daily[k]["equity"].index >= W0] for k in keys}
    idx = eqs["P0"].index
    for k in eqs:
        assert len(eqs[k]) == len(idx) and (eqs[k].index == idx).all(), ("lech chi so ngay", k)
    obs, bs = SAD.daily_boot(eqs)
    obs["B0"], bs["B0"] = obs.pop("P0"), bs.pop("P0")
    mets = ("cagr", "mdd", "calmar", "sharpe")
    pairs = [(x, y) for x, y in PRIMARY + CROSS if x in keys and y in keys]
    con = {x + "-" + y: {m: SAD.ci_of(obs[x][m] - obs[y][m], bs[x][m] - bs[y][m]) for m in mets} for x, y in pairs}
    dpnl = pnl_boot(legs, idx, keys, pairs)
    for x, y in pairs:
        con[x + "-" + y]["pnl"] = dpnl[x + "-" + y]
    finish(M, obs, con, void, arms_ok, par, md5, keys)


def finish(M, obs, con, void, arms_ok, par, md5, keys):
    rule = {}
    for k in arms_ok:
        b = BASE[k]
        c = con[k + "-" + b]
        x, y = M[k], M[b]
        dy = {yy: (x["roi_year"].get(yy, np.nan) - y["roi_year"].get(yy, np.nan)) for yy in YEARS}
        c1a = c["cagr"]["d"] > 0 and c["cagr"]["ci_infl"][0] > 0
        c1b = c["pnl"]["d"] > 0 and c["pnl"]["ci_infl"][0] > 0
        c2 = x["dd_mtm"] >= DD_MIN and x["dd_mtm22"] >= DD_MIN
        c3 = x["calmar22"] >= CAL_MULT * y["calmar22"]
        c4 = sum(1 for v in dy.values() if v >= 0) >= 3
        c5 = x["n_per_year"] >= N_YEAR_MIN
        rule[k] = {"c1_loi_nhuan": dict(ok=bool(c1a or c1b), via_dCAGR=bool(c1a), via_dPnL=bool(c1b),
                                        dCAGR=c["cagr"]["d"], dCAGR_ci_raw=c["cagr"]["ci_raw"],
                                        dCAGR_ci_infl=c["cagr"]["ci_infl"], dPnL=c["pnl"]["d"],
                                        dPnL_ci_raw=c["pnl"]["ci_raw"], dPnL_ci_infl=c["pnl"]["ci_infl"]),
                   "c2_maxDD_MTM>=-40": dict(ok=bool(c2), full=x["dd_mtm"], w2022=x["dd_mtm22"]),
                   "c3_Calmar22>=0.8xnen": dict(ok=bool(c3), arm=x["calmar22"], base=y["calmar22"],
                                                 thr=CAL_MULT * y["calmar22"], ratio=x["calmar22"] / y["calmar22"]),
                   "c4_>=3/4_nam_dROI>=0": dict(ok=bool(c4), dROI=dy, n_ok=int(sum(1 for v in dy.values() if v >= 0))),
                   "c5_n/nam>=700": dict(ok=bool(c5), n_per_year=x["n_per_year"])}
        rule[k]["GO"] = bool(all(v["ok"] for kk, v in rule[k].items() if kk.startswith("c")))
    gos = [k for k in ("A1", "A2") if k in rule and rule[k]["GO"]]
    pick = max(gos, key=lambda k: rule[k]["c1_loi_nhuan"]["dCAGR_ci_infl"][0]) if gos else None
    robust = {}
    for a, g in (("A1", "A3"), ("A2", "A4")):
        if a in rule and g in rule:
            sa, sg = np.sign(rule[a]["c1_loi_nhuan"]["dCAGR"]), np.sign(rule[g]["c1_loi_nhuan"]["dCAGR"])
            robust[a] = "ben qua model" if sa == sg else "CANH BAO nguoc dau tren GEOM"
    verdict = ("GO: %s (ung vien shadow)" % pick) if pick else "NO-GO lever n o vong nay"
    log.info("")
    log.info("%-5s %5s %6s %7s %7s %6s %6s %7s %7s %5s %6s %6s %5s %5s %5s %5s %5s", "arm", "n", "n/nam", "SumPnL",
             "PnL2225", "CAGR", "CAGR22", "ddMTM", "ddMTM22", "UW", "Cal", "Cal22", "win", "SL", "op95", "opMx", "0h%")
    for k in keys:
        x = M[k]
        log.info("%-5s %5d %6.0f %7.0f %7.0f %6.2f %6.2f %7.2f %7.2f %5.0f %6.3f %6.3f %5.1f %5.1f %5.0f %5d %5.1f", k,
                 x["n"], x["n_per_year"], x["sum_pnl"], x["sum_pnl_2022_25"], x["cagr"], x["cagr22"], x["dd_mtm"],
                 x["dd_mtm22"], x["uw_mtm"], x["calmar"], x["calmar22"], x["win"], x["sl"], x["conc"]["open_p95"],
                 x["conc"]["open_max"], x["hour0"]["share0"])
    for k in keys:
        log.info("%-5s nam %s | expo TB/p95/max %.1f/%.1f/%.1f", k,
                 {y: (v["n"], round(v["sum_pnl"]), round(v["roi_year"] or 0, 1), round(v["dd_mtm_year"], 1))
                  for y, v in M[k]["per_year"].items()}, M[k]["conc"]["expo_mean"], M[k]["conc"]["expo_p95"],
                 M[k]["conc"]["expo_max"])
    for cc, d in con.items():
        log.info("CON %-9s %s", cc, {m: (round(v["d"], 2), [round(z, 2) for z in v["ci_infl"]])
                                     for m, v in d.items()})
    for k, r in rule.items():
        log.info("RULE %s GO=%s %s", k, r["GO"], {kk: v["ok"] for kk, v in r.items() if kk.startswith("c")})
    log.info("ROBUST %s", robust)
    log.info("VERDICT %s", verdict)
    js = dict(prereg="docs/prereg/PREREG_N700.md", prereg_commit="00ca54b6", k_infl=K_INFL, inflate=INFL, nrep=NREP,
              seed=SEED, block_days=BLOCK_D, window="2022-01-01..2025-12-30 (equity rebase 2021-12-31)",
              jar_sha256=JAR_SHA, kaggle_sim_md5=KS_MD5_WANT, tags=dict(TAG), md5=md5, parity=par, gate1=void,
              boot_obs=obs, contrasts=con, rule=rule, robust=robust, pick=pick, verdict=verdict, metrics=M)
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", JSON_OUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["submit", "status", "fetch", "parity", "score", "dryscore"])
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--code-sha", default="")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    if a.cmd == "submit":
        assert a.code_sha
        ks = ks_mod()
        log.info("free_slots=%d", ks.free_slots())
        for x in a.arms:
            submit(x, a.code_sha)
    elif a.cmd == "status":
        ks = ks_mod()
        for x in a.arms or ARMS + ["B0REF"]:
            log.info("%s %s", x, ks._status(ks.kernel_ref(TAG[x])))
    elif a.cmd == "fetch":
        ks = ks_mod()
        for x in a.arms:
            o = ks.fetch(TAG[x])
            log.info("%s %s", x, json.dumps(o.get("result"), default=str)[:600])
    elif a.cmd == "parity":
        r = parity()
        sys.exit(0 if r and r["ok"] else 3)
    elif a.cmd == "dryscore":
        # KIEM CODE (khong phai ket qua): A1 := de-p2 (anh cu), JSON ghi ra file rieng
        global JSON_OUT, MTM_CACHE
        JSON_OUT, MTM_CACHE = D + "/dry.json", D + "/mtm_dry.json"
        score(a.workers, tagmap={"A1": "de-p2"})
    else:
        score(a.workers)


if __name__ == "__main__":
    main()
