#!/usr/bin/env python3
"""SELECTOR_ABLATION driver — submit/fetch kernel Kaggle + cong parity + cham. Pre-reg docs/prereg/PREREG_SELECTOR_ABLATION.md.

Arm KHOA: P0 = B0 (G2+FLAT3, bins goc) ; R42/R7/R13 = hoan vi ngau nhien diem selector trong cung tick (seed 42/7/13) ;
L = diem theo hang quoteVol 24h truoc tick. Chi doi bins selector -> funding.bin (dung lai bang s3_funding.py,
byte-faithful); gate/sizing/exit/profile/jar GIU NGUYEN B0.
Kernel = tools/kaggle_sim.py HEAD (NOWRITE242 + PREFLIGHT, md5 8b60b00a) + 1 khoi chen (sinh bins arm trong kernel bang
research/analysis/selector_ablation_scores.py, assert sha256 == ban Oracle, dung lai funding.bin, tro WFO_DATA_DIR/
WFO_FUNDING_PRED_DIR sang ban moi) + don file lon truoc khi ket thuc. Khong sua .java, khong build.

Usage:
  python3 selector_ablation_driver.py submit P0 | submit R42 R7 R13 L | upload_liq
  python3 selector_ablation_driver.py wait P0 ... ; fetch P0 ... ; parity ; score [--workers 3]
"""
import argparse
import base64
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
from tools import kaggle_sim as ks  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("sel_abl_drv")

ARMS = ["P0", "R42", "R7", "R13", "L"]
RARMS = ["R42", "R7", "R13"]
TAG = {"P0": "selab-p0", "R42": "selab-r42", "R7": "selab-r7", "R13": "selab-r13", "L": "selab-liq"}
LIQ_DIR = "/home/ubuntu/claude_master/1003/sa/liq"
KS_MD5_WANT = "8b60b00afad39f2528aaa15092225c9b"      # tools/kaggle_sim.py HEAD (NOWRITE242)
JAR_DS, JAR_SHA = "sim-jar-gdv2", "7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a"
BUNDLE = "sim-x1-2021-bundle"
MOC21_DS = "s3-moc-2021bins"
LIQ_DS = "sel-ablation-liq"
PROFILE = "r4_kg0_k16_f015_g155"
B0OV = {"SIM_GATE_ROLLING_MODE": "ratio", "SIM_GATE_ROLLING_DAYS": 90, "SIM_GATE_ROLLING_PCT": 0.999950829,
        "TS_GIVEBACK_RATIO": 1.0, "SIM_TS_MAX_GAP": 0.03, "SIM_TS_MAX_GAP_WEAK": 0.03}
PARITY_MD5, PARITY_N, PARITY_EQ = "650c386f0d0dfea334af9d55ca2f21d4", 2517, 131908
SHA_JSON = "/home/ubuntu/claude_master/1003/sa/bins/sha256.json"
HELPERS = {"selector_ablation_scores.py": os.path.join(HERE, "selector_ablation_scores.py"),
           "s3_funding.py": os.path.join(REPO, "research/pipeline/x1/s3_funding.py")}
K_INFL = 1                                           # pre-reg: 1 phep thu chinh (B0 - mean R gop 3 seed)
INFL = 1.0                                           # k=1 => khong inflate (ci_infl == ci_raw)
NREP, SEED, BLOCK_D = 2000, 20260905, 10
CAP0 = 35000.0
GO_YEARS = [2022, 2023, 2024, 2025]
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
MTM_CACHE = "/home/ubuntu/claude_master/1003/sa/mtm.json"
JSON_OUT = os.path.join(REPO, "docs/result/selector_ablation.json")

# ───────────────────────── khoi chen vao kernel (sau dong PREDWF = ...) ─────────────────────────
SA_BLOCK = r'''
# [SELECTOR_ABLATION 2026-10-03] sinh bins arm TRONG kernel (helper nhung base64) -> assert sha256 == ban Oracle
#   -> dung lai funding.bin (s3_funding.py byte-faithful) -> WFO_DATA_DIR/WFO_FUNDING_PRED_DIR tro sang ban moi.
SA_INFO = {}
_SA = CFG.get("sel_arm") or ""
if _SA:
    import base64 as _b64m
    import hashlib as _h3
    _HELP = os.path.join(WORK, "sa_helpers")
    os.makedirs(_HELP, exist_ok=True)
    for _nm, _bb in __SA_HELPERS__.items():
        with open(os.path.join(_HELP, _nm), "wb") as _f:
            _f.write(_b64m.b64decode(_bb))
    sys.path.insert(0, _HELP)
    import selector_ablation_scores as SAS
    _b16 = sorted(glob.glob(DS + "/predict_wf_*.bin"))
    _c21 = [c for c in sorted(glob.glob(IN + "/**/predict_wf_20210701.bin", recursive=True))
            if ("/" + CFG["moc21_ds"] + "/") in c]
    if len(_b16) != 16 or not _c21:
        LOG.error("SA_FAIL bins nguon: bundle %d file (can 16), moc21=%s", len(_b16), _c21)
        sys.exit(7)
    _files = SAS.src_files([DS, os.path.dirname(_c21[0])])
    _liq = None
    if _SA == "L":
        _lc = [c for c in sorted(glob.glob(IN + "/**/liqrank_20220101.npy", recursive=True))
               if ("/" + CFG["liq_ds"] + "/") in c]
        if not _lc:
            LOG.error("SA_FAIL thieu liqrank (dataset %s)", CFG["liq_ds"])
            sys.exit(7)
        _liq = os.path.dirname(_lc[0])
    _src_sha = SAS.sha256_concat(_files)
    SA_BINS = os.path.join(WORK, "sa_bins_" + _SA)
    _sha, _outs = SAS.gen_arm(_SA, _files, SA_BINS, _liq)
    SA_INFO.update(arm=_SA, src_bins_sha256=_src_sha, bins_sha256=_sha, want_bins_sha256=CFG["want_bins_sha"],
                   bins_ok=_sha == CFG["want_bins_sha"])
    LOG.info("SA arm=%s src_sha=%s bins_sha=%s want=%s", _SA, _src_sha, _sha, CFG["want_bins_sha"])
    if _sha != CFG["want_bins_sha"] or _src_sha != CFG["src_bins_sha"]:
        LOG.error("SA_FAIL sha bins lech (src %s / arm %s) -> DUNG", _src_sha == CFG["src_bins_sha"], _sha == CFG["want_bins_sha"])
        sys.exit(7)
    SA_DS = os.path.join(WORK, "sa_ds")
    os.makedirs(SA_DS, exist_ok=True)
    for _nm in ("market.bin", "pred.bin"):
        if not os.path.lexists(os.path.join(SA_DS, _nm)):
            os.symlink(os.path.join(DS, _nm), os.path.join(SA_DS, _nm))
    _fj = os.path.join(WORK, "sa_funding.json")
    _t0 = time.time()
    _rc = subprocess.call([sys.executable, os.path.join(_HELP, "s3_funding.py"), "--bins", SA_BINS, "--data", DS,
                           "--out", os.path.join(SA_DS, "funding.bin"), "--json", _fj])
    LOG.info("SA s3_funding rc=%s %.0fs", _rc, time.time() - _t0)
    if _rc != 0:
        sys.exit(7)
    _F = json.load(open(_fj))
    _base, _order = {}, []
    for _ln in open(os.path.join(DS, "manifest.txt")):
        _s = _ln.rstrip("\n")
        _k = _s.split("=", 1)[0].strip()
        if _k and "=" in _s and not _k.startswith("predictWf."):
            if _k not in _base:
                _order.append(_k)
            _base[_k] = _s.split("=", 1)[1].strip()
    import datetime as _dt
    _mn = min(m["minTs"] for m in _F["predictWf"])
    _base.update({"fundingPredDir": SA_BINS, "binsSha256": _F["binsSha256"], "foldCount": str(_F["foldCount"]),
                  "maxFoldSpanDays": str(_F["maxFoldSpanDays"]), "fundingCount": str(_F["fundingCount"]),
                  "fundingRaw15mCount": str(_F["fundingRaw15mCount"]), "md5_funding": _F["md5_funding"],
                  "leakFreeFrom": _dt.datetime.utcfromtimestamp(_mn / 1000 + 7 * 3600).strftime("%Y-%m-%d"),
                  "selAblationArm": _SA})
    for _k in ("fundingPredDir", "binsSha256", "foldCount", "maxFoldSpanDays", "fundingCount",
               "fundingRaw15mCount", "md5_funding", "leakFreeFrom", "selAblationArm"):
        if _k not in _order:
            _order.append(_k)
    with open(os.path.join(SA_DS, "manifest.txt"), "w") as _f:
        for _k in _order:
            _f.write("%s=%s\n" % (_k, _base[_k]))
        for _m in sorted(_F["predictWf"], key=lambda x: x["name"]):
            _span = (_m["maxTs"] - _m["minTs"]) // 86400000
            _f.write("predictWf.%s=md5:%s;ts:%d..%d;span:%dd;rec:%d\n"
                     % (_m["name"], _m["md5"], _m["minTs"], _m["maxTs"], _span, _m["nrec"]))
    SA_INFO.update(funding_md5=_F["md5_funding"], funding_count=_F["fundingCount"], fold_count=_F["foldCount"],
                   leak_free_from=_base["leakFreeFrom"], orig_md5_funding=CFG.get("orig_md5_funding"))
    LOG.info("SA dataset ok: funding md5=%s count=%d fold=%d", _F["md5_funding"], _F["fundingCount"], _F["foldCount"])
    DS = SA_DS
    PREDWF = SA_BINS
'''

SA_CLEAN = r'''# [SELECTOR_ABLATION] md5 printDone + don file lon (funding.bin ~4 GB, bins ~1 GB) truoc khi Kaggle luu output
if os.path.exists(PDONE):
    import hashlib as _h4
    SA_INFO["md5_printdone"] = _h4.md5(open(PDONE, "rb").read()).hexdigest()
    with open(WORK + "/result.json", "w") as f:
        res["sel"] = SA_INFO
        json.dump(res, f, indent=1)
for _p in (os.path.join(WORK, "sa_ds"), os.path.join(WORK, "sa_bins_" + (CFG.get("sel_arm") or "x"))):
    shutil.rmtree(_p, ignore_errors=True)
'''


def _patch(t, old, new):
    assert t.count(old) == 1, ("anchor", t.count(old), old[:60])
    return t.replace(old, new)


def build_template():
    import hashlib
    ksrc = open(os.path.join(REPO, "tools/kaggle_sim.py"), "rb").read()
    md5 = hashlib.md5(ksrc).hexdigest()
    assert md5 == KS_MD5_WANT, ("tools/kaggle_sim.py khong phai HEAD NOWRITE242", md5)
    assert "NOWRITE_HOST" in ks.KERNEL_TEMPLATE and "SYMBOL_MAPPER_PREFLIGHT_FAIL" in ks.KERNEL_TEMPLATE
    helpers = {nm: base64.b64encode(open(p, "rb").read()).decode() for nm, p in HELPERS.items()}
    blk = SA_BLOCK.replace("__SA_HELPERS__", repr(helpers))
    t = ks.KERNEL_TEMPLATE
    t = _patch(t, "PREDWF = os.path.dirname(_cand[0])\n", "PREDWF = os.path.dirname(_cand[0])\n" + blk)
    t = _patch(t, 'subprocess.call(["gzip", "-f", LOGP])', SA_CLEAN + 'subprocess.call(["gzip", "-f", LOGP])')
    return t


def submit(arm, code_sha, push=True):
    shas = json.load(open(SHA_JSON))
    tag = TAG[arm]
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": PROFILE, "overrides": dict(B0OV), "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 7200, "code_sha": code_sha, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "",
           "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
           "sel_arm": arm, "want_bins_sha": shas[arm], "src_bins_sha": shas["P0"],
           "moc21_ds": MOC21_DS, "liq_ds": LIQ_DS, "orig_md5_funding": "8e57d900d5c54c744bfcaf5c9b27fc93"}
    code = build_template().replace("__CFG_JSON__", repr(json.dumps(cfg)))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [ks.USER + "/" + BUNDLE] + ks.TICKER_DS
                               + [ks.USER + "/" + JAR_DS, ks.USER + "/" + MOC21_DS]
                               + ([ks.USER + "/" + LIQ_DS] if arm == "L" else []),
            "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    if push:
        r = ks._api().kernels_push(folder)
        log.info("push %s -> %s", ref, getattr(r, "url", r))
    return ref


def result_json(arm):
    p = OUT % TAG[arm] + "result.json"
    return json.load(open(p)) if os.path.exists(p) else {}


def parity():
    import reset_rule_score as R
    rj = result_json("P0")
    md5 = R.md5_of(TAG["P0"])
    legs = R.load_legs(TAG["P0"])
    eq = float(R.load_daily(TAG["P0"])["equity"].iloc[-1])
    sel = rj.get("sel") or {}
    chk = {"md5": md5 == PARITY_MD5, "n": len(legs) == PARITY_N, "eq": round(eq) == PARITY_EQ,
           "jar": rj.get("jar_sha256") == JAR_SHA, "mapper": (rj.get("symbol_mapper") or 0) >= 800,
           "bins_sha_P0": sel.get("bins_ok") is True,
           "funding_md5_eq_bundle": sel.get("funding_md5") == "8e57d900d5c54c744bfcaf5c9b27fc93"}
    ok = all(chk.values())
    log.info("PARITY P0 md5=%s n=%d eq=%.0f %s -> %s", md5, len(legs), eq, chk, "PASS" if ok else "*** FAIL => VOID ***")
    json.dump(dict(ok=ok, md5=md5, n=len(legs), eq=eq, checks=chk, sel=sel), open(JSON_OUT + ".parity", "w"), indent=1)
    return ok


def daily_boot(eqs, nrep=NREP, seed=SEED, block=BLOCK_D):
    """Moving-block bootstrap PAIRED tren loi suat ngay MTM (b+unP), cung chi so khoi cho moi arm.
    Tra {arm: {metric: array nrep}} + obs; metric: cagr (%), mdd (% am), calmar, sharpe (nam hoa sqrt 365)."""
    idx = eqs["P0"].index
    R_ = {k: (v.reindex(idx).ffill().values[1:] / v.reindex(idx).ffill().values[:-1] - 1.0) for k, v in eqs.items()}
    T = len(idx) - 1
    years = (idx[-1] - idx[0]).days / 365.25

    def met(r):
        eq = np.concatenate(([1.0], np.cumprod(1.0 + r)))
        mdd = float((eq / np.maximum.accumulate(eq) - 1.0).min() * 100.0)
        cagr = (eq[-1] ** (1.0 / years) - 1.0) * 100.0
        sd = r.std(ddof=1)
        return dict(cagr=cagr, mdd=mdd, calmar=cagr / abs(mdd) if mdd < 0 else np.nan,
                    sharpe=float(r.mean() / sd * math.sqrt(365.0)) if sd > 0 else np.nan)

    obs = {k: met(r) for k, r in R_.items()}
    nb = int(math.ceil(T / block))
    rng = np.random.default_rng(seed)
    bs = {k: {m: np.empty(nrep) for m in ("cagr", "mdd", "calmar", "sharpe")} for k in R_}
    for i in range(nrep):
        st = rng.integers(0, T - block + 1, size=nb)
        pick = (st[:, None] + np.arange(block)[None, :]).ravel()[:T]
        for k, r in R_.items():
            m = met(r[pick])
            for q, v in m.items():
                bs[k][q][i] = v
    return obs, bs


def ci_of(obs_d, arr):
    a = arr[np.isfinite(arr)]
    lo, hi = np.percentile(a, [2.5, 97.5])
    return dict(d=float(obs_d), ci_raw=[float(lo), float(hi)],
                ci_infl=[float(obs_d - (obs_d - lo) * INFL), float(obs_d + (hi - obs_d) * INFL)])


def contrasts(obs, bs):
    """B0 - arm (moi arm), B0 - mean(R), L - mean(R): chenh do bang paired bootstrap."""
    out = {}
    mR_obs = {m: np.mean([obs[k][m] for k in RARMS]) for m in ("cagr", "mdd", "calmar", "sharpe")}
    mR_bs = {m: np.mean([bs[k][m] for k in RARMS], axis=0) for m in ("cagr", "mdd", "calmar", "sharpe")}
    for m in ("cagr", "mdd", "calmar", "sharpe"):
        out.setdefault("B0-meanR", {})[m] = ci_of(obs["P0"][m] - mR_obs[m], bs["P0"][m] - mR_bs[m])
        out.setdefault("L-meanR", {})[m] = ci_of(obs["L"][m] - mR_obs[m], bs["L"][m] - mR_bs[m])
        out.setdefault("B0-L", {})[m] = ci_of(obs["P0"][m] - obs["L"][m], bs["P0"][m] - bs["L"][m])
        out.setdefault("L-B0", {})[m] = ci_of(obs["L"][m] - obs["P0"][m], bs["L"][m] - bs["P0"][m])
        for k in RARMS:
            out.setdefault("B0-" + k, {})[m] = ci_of(obs["P0"][m] - obs[k][m], bs["P0"][m] - bs[k][m])
    return out


def gate_stats(arm):
    """dong GATE-RATIO cuoi run trong sim.out (seen/pass/rho) — kiem gate giu luat."""
    p = OUT % TAG[arm] + "logs/sim.out"
    last = None
    if os.path.exists(p):
        for ln in open(p, errors="ignore"):
            if "GATE-RATIO on" in ln and "seen=" in ln:
                last = ln.strip()
    if not last:
        return None
    import re
    m = re.search(r"seen=(\d+) pass=(\d+) rho=([\d.]+)", last)
    return dict(seen=int(m.group(1)), pass_=int(m.group(2)), rho=float(m.group(3))) if m else None


def arm_metrics(R, F3, arm, legs, daily, mtm):
    m = R.core_metrics(arm, legs, daily, "legacy")
    eq = daily["equity"]
    r = eq.values[1:] / eq.values[:-1] - 1.0
    y = legs["ts"].dt.year
    per_year = {}
    for yy, g in legs.groupby(y):
        per_year[int(yy)] = dict(n=int(len(g)), sum_pnl=float(g["pnl"].sum()), win=float(100 * (g["profit"] > 0).mean()),
                                 mean_roi=float(g["profit"].mean()))
    return dict(tag=TAG[arm], n=int(len(legs)), sum_pnl=float(legs["pnl"].sum()), equity=float(eq.iloc[-1]),
                cagr=float(m["cagr"]), dd_mtm=float(mtm["dd_total"]), uw_mtm=float(mtm["uw_total_days"]),
                calmar_mtm=float(m["cagr"] / abs(mtm["dd_total"])), dd_daily=float(m["maxdd_daily"]),
                sharpe_daily=float(r.mean() / r.std(ddof=1) * math.sqrt(365.0)),
                win=float(100 * (legs["profit"] > 0).mean()), mean_roi=float(legs["profit"].mean()),
                median_roi=float(legs["profit"].median()), exposure=exposure(legs, daily),
                tsloss=float(m["rates"]["TSloss%"]), episodes=F3.episodes_top5(legs),
                roi_year={str(k): float(v) for k, v in m["yr"].items()},
                dd_mtm_year={str(k): float(v) for k, v in mtm["dd_year"].items()},
                per_year=per_year, n_level={str(k): int(v) for k, v in legs["level"].value_counts().items()}
                if "level" in legs else None, gate=gate_stats(arm), result_json=result_json(arm))


def exposure(legs, daily):
    """% ngay lich co >=1 leg mo (ngay vao..ngay ra) + so leg mo trung binh / ngay."""
    d0, d1 = daily.index[0].normalize(), daily.index[-1].normalize()
    nd = int((d1 - d0).days) + 1
    cnt = np.zeros(nd + 1)
    a = ((legs["ts"].dt.normalize() - d0).dt.days).clip(0, nd - 1).to_numpy()
    b = ((legs["te"].dt.normalize() - d0).dt.days).clip(0, nd - 1).to_numpy()
    np.add.at(cnt, a, 1)
    np.add.at(cnt, b + 1, -1)
    c = np.cumsum(cnt)[:nd]
    return dict(pct_days_open=float(100 * (c > 0).mean()), mean_open_legs=float(c.mean()))


def verdict_rule(con, M):
    """Luat khai truoc (PREREG_SELECTOR_ABLATION §5). Thuoc chinh = Calmar tren loi suat ngay MTM (b+unP), paired
    block-10d bootstrap, B0 - mean(R42,R7,R13); k=1 => CI raw. Nam = ROI nam (equity MTM ngay) 2022-2025."""
    c = con["B0-meanR"]
    yrs = {yy: M["P0"]["roi_year"].get(str(yy), np.nan) - np.mean([M[k]["roi_year"].get(str(yy), np.nan) for k in RARMS])
           for yy in GO_YEARS}
    npos = int(sum(1 for v in yrs.values() if v > 0))
    cal_lo, cal_hi = c["calmar"]["ci_raw"]
    lever = cal_lo > 0 and npos >= 3
    dead = (cal_lo <= 0 <= cal_hi) and abs(c["cagr"]["d"]) < 3.0
    v = "SELECTOR LA LEVER" if lever else ("SELECTOR CHET" if dead else "CHUA KET LUAN")
    lb = con["L-B0"]
    liq_ok = M["L"]["calmar_boot_obs"] >= M["P0"]["calmar_boot_obs"]
    return dict(verdict=v, calmar_ci_lo_gt0=cal_lo > 0, years_b0_minus_meanR=yrs, years_pos=npos,
                dead_conditions=dict(calmar_ci_has0=cal_lo <= 0 <= cal_hi, abs_dcagr_lt3=abs(c["cagr"]["d"]) < 3.0),
                liq_rule=dict(L_ge_B0_calmar=bool(liq_ok), L_minus_B0=lb,
                              verdict="THANH KHOAN DU THAY SELECTOR" if liq_ok else "THANH KHOAN KHONG THAY DUOC SELECTOR"))


def overlap(lb, lx):
    """% lenh B0 (sym|ts phut vao) co mat trong arm; Jaccard."""
    kb = set(lb["sym"] + "|" + lb["start"].astype(str).str.strip())
    kx = set(lx["sym"] + "|" + lx["start"].astype(str).str.strip())
    inter = len(kb & kx)
    by_level = {}
    if "level" in lb.columns:
        for lv, g in lb.groupby(lb["level"].astype(str).str.strip()):
            kg = set(g["sym"] + "|" + g["start"].astype(str).str.strip())
            by_level[lv] = dict(n_b0=len(kg), pct_in_arm=100.0 * len(kg & kx) / max(1, len(kg)))
    return dict(n_b0=len(kb), n_arm=len(kx), inter=inter, pct_of_b0=100.0 * inter / max(1, len(kb)),
                jaccard=100.0 * inter / max(1, len(kb | kx)), by_level=by_level)


def upload_liq():
    """Dataset Kaggle rieng tu: CHI liqrank_<fold>.npy (int16) cho arm L."""
    import shutil
    import glob as _g
    fol = "/home/ubuntu/claude_master/1003/sa/ds_liq"
    os.makedirs(fol, exist_ok=True)
    fs = sorted(_g.glob(os.path.join(LIQ_DIR, "liqrank_*.npy")))
    assert len(fs) == 18, len(fs)
    for f in fs:
        shutil.copy2(f, fol)
    json.dump({"title": LIQ_DS, "id": ks.USER + "/" + LIQ_DS, "licenses": [{"name": "CC0-1.0"}]},
              open(os.path.join(fol, "dataset-metadata.json"), "w"))
    r = ks._api().dataset_create_new(fol, public=False, quiet=True, dir_mode="skip")
    log.info("upload_liq -> %s", getattr(r, "url", r))


def score(workers):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401  (side effect: MTMState cua so 2022+)
    import flat3_crashpen_driver as F3
    R.MTM_COSTS = {"legacy": R.LEGACY}
    if not parity():
        log.info("VOID: parity P0 FAIL -> khong cham")
        sys.exit(3)
    legs, daily, md5 = {}, {}, {}
    for k in ARMS:
        legs[k], daily[k], md5[k] = R.load_legs(TAG[k]), R.load_daily(TAG[k]), R.md5_of(TAG[k])
        rj = result_json(k)
        sel = rj.get("sel") or {}
        log.info("%s n=%d eq=%.0f md5=%s jar_ok=%s mapper=%s bins_ok=%s funding=%s", k, len(legs[k]),
                 daily[k]["equity"].iloc[-1], md5[k], rj.get("jar_sha256") == JAR_SHA, rj.get("symbol_mapper"),
                 sel.get("bins_ok"), str(sel.get("funding_md5"))[:12])
        if rj.get("jar_sha256") != JAR_SHA or (rj.get("symbol_mapper") or 0) < 800 or sel.get("bins_ok") is not True:
            log.info("*** arm %s sai jar/mapper/bins => DUNG", k)
            sys.exit(4)
    raw = json.load(open(MTM_CACHE)) if os.path.exists(MTM_CACHE) else {}
    miss = {k: legs[k] for k in ARMS if k not in raw or raw[k].get("md5") != md5[k]}
    if miss:
        new = R.run_mtm(miss, workers=workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        json.dump(raw, open(MTM_CACHE, "w"))
    mtm = {k: raw[k]["legacy"] for k in ARMS}
    M = {k: arm_metrics(R, F3, k, legs[k], daily[k], mtm[k]) for k in ARMS}
    for k in ARMS:
        M[k]["md5"] = md5[k]
    obs, bs = daily_boot({k: daily[k]["equity"] for k in ARMS})
    for k in ARMS:
        M[k]["calmar_boot_obs"] = float(obs[k]["calmar"])
        M[k]["cagr_boot_obs"] = float(obs[k]["cagr"])
        M[k]["mdd_daily_mtm_obs"] = float(obs[k]["mdd"])
        M[k]["overlap_vs_B0"] = overlap(legs["P0"], legs[k])
    con = contrasts(obs, bs)
    rule = verdict_rule(con, M)
    # L vs R (thong tin, cung thuoc)
    lr_years = {yy: M["L"]["roi_year"].get(str(yy), np.nan) - np.mean([M[k]["roi_year"].get(str(yy), np.nan) for k in RARMS])
                for yy in GO_YEARS}
    # R tong hop mean +- sd
    agg = {}
    for f in ("n", "sum_pnl", "equity", "cagr", "dd_mtm", "calmar_mtm", "uw_mtm", "win", "mean_roi", "median_roi",
              "tsloss", "sharpe_daily", "calmar_boot_obs"):
        v = [M[k][f] for k in RARMS]
        agg[f] = dict(mean=float(np.mean(v)), sd=float(np.std(v, ddof=1)))
    agg["top5_share"] = dict(mean=float(np.mean([M[k]["episodes"]["top5_share"] for k in RARMS])),
                             sd=float(np.std([M[k]["episodes"]["top5_share"] for k in RARMS], ddof=1)))
    # thuoc phu (thong tin): rate muc lenh B0 vs tung R, CI block-72h paired grid
    R.K_INFL, R.INFL = K_INFL, INFL
    rates_ci = {k: R.ci_pair(legs[k], legs["P0"]) for k in RARMS + ["L"]}
    log.info("")
    log.info("%-3s %5s %8s %8s %6s %7s %6s %6s %6s %6s %6s %6s", "arm", "n", "SumPnL", "equity", "CAGR", "ddMTM",
             "Calm", "UW", "win%", "mROI", "Shrp", "top5e")
    for k in ARMS:
        x = M[k]
        log.info("%-3s %5d %8.0f %8.0f %6.2f %7.2f %6.3f %6.1f %6.2f %6.2f %6.2f %6.1f", k, x["n"], x["sum_pnl"],
                 x["equity"], x["cagr"], x["dd_mtm"], x["calmar_mtm"], x["uw_mtm"], x["win"], x["mean_roi"],
                 x["sharpe_daily"], x["episodes"]["top5_share"])
    for c, d in con.items():
        log.info("%-9s %s", c, {m: (round(v["d"], 2), [round(z, 2) for z in v["ci_raw"]], [round(z, 2) for z in v["ci_infl"]])
                                for m, v in d.items()})
    log.info("ROI nam %s", {k: {y: round(v, 1) for y, v in M[k]["roi_year"].items()} for k in ARMS})
    log.info("VERDICT %s | %s", rule["verdict"], {k: v for k, v in rule.items() if k != "verdict"})
    js = dict(prereg="docs/prereg/PREREG_SELECTOR_ABLATION.md", k_infl=K_INFL, inflate=INFL, nrep=NREP, seed=SEED,
              block_days=BLOCK_D, jar_sha256=JAR_SHA, kaggle_sim_md5=KS_MD5_WANT,
              bins_sha256=json.load(open(SHA_JSON)), parity=json.load(open(JSON_OUT + ".parity")),
              boot_obs=obs, contrasts=con, rule=rule, L_minus_meanR_years=lr_years, R_agg=agg,
              rates_ci_vs_B0=rates_ci, metrics=M)
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", JSON_OUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["template", "submit", "wait", "fetch", "parity", "score", "upload_liq"])
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--code-sha", default="head")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    arms = a.arms or ARMS
    if a.cmd == "template":
        t = build_template()
        open("/home/ubuntu/claude_master/1003/sa/kernel_template.py", "w").write(t)
        log.info("template ok %d bytes", len(t))
    elif a.cmd == "submit":
        log.info("free_slots=%d", ks.free_slots())
        for x in arms:
            submit(x, a.code_sha)
    elif a.cmd == "wait":
        log.info("%s", ks.wait([ks.kernel_ref(TAG[x]) for x in arms], poll_s=120, timeout_s=5 * 3600))
    elif a.cmd == "fetch":
        for x in arms:
            o = ks.fetch(TAG[x])
            log.info("%s %s", x, json.dumps(o.get("result"), default=str)[:600])
    elif a.cmd == "upload_liq":
        upload_liq()
    elif a.cmd == "parity":
        sys.exit(0 if parity() else 3)
    else:
        score(a.workers)


if __name__ == "__main__":
    main()
