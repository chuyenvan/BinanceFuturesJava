#!/usr/bin/env python3
"""GATE_ABLATION (Pha A chuong trinh GATE). Pre-reg docs/prereg/PREREG_GATE_ABLATION.md (bfdd3407, chot TRUOC).

Moi arm = 1 pred.bin thay the (chi cot p15), so GHEP CAP voi A1 = B0@K24 (~/kaggle_sim/out/n700-a1).
Arm: RND (uniform seed 20261004 -> map ve phan phoi p15 goc), RULE (-momentum15M -> map),
NOCAL (retrain bo 4 cot lich, tho), H60 (retrain nhan max upside 60' dung lai tu ticker, purge 60' -> map),
SEED7 (retrain seed 7, tho; chi bao cao). G0 = retrain seed 42 phai tai lap pred.bin goc (pearson/fold >= 0.99).
THUAN PYTHON tren Oracle (0 Java, 0 build); sim chi tren Kaggle, template = tools/kaggle_sim.py HEAD + 1 khoi chen.
Usage: python3 gate_ablation_driver.py retrain G0|NOCAL|SEED7|H60 | gen ARM | label60 [--workers 3] | labelgate
       | g1 | upload ARM | submit ARM --code-sha SHA | status | fetch ARM | parity | score | ic
"""
import argparse
import glob
import hashlib
import json
import logging
import math
import os
import struct
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
HERE = os.path.join(REPO, "research/analysis")
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("gabl")

D = "/home/ubuntu/claude_master/1004/gabl"
PRED0 = "/home/ubuntu/wfo_ds_x1_2021/pred.bin"
PRED0_MD5 = "5dd6bb4c3f98d89d58770005c0001526"
STORE = "/home/ubuntu/claudedata/gate_dataset_full.csv.gz"
STORE_MD5 = "4bde28cd6d439ec009954bb6ec7d2537"
TICKER_DIR = "/home/ubuntu/java/simulator/kaggle_data_hpo"
V3FULL = [
    "momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H", "momentumAcceleration",
    "trendStrengthETH", "trendConsistency",
    "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
    "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength", "btcDominance",
    "rsi14", "volumeSpike", "distMA20",
    "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
    "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike",
]
CAL = ["hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear"]
RULE_COL = "momentum15M"            # = MarketDataObject.rateDown15MAvg; p15' = -RULE_COL (lon = sap manh)
SEAL = pd.Timestamp("2026-01-01", tz="Asia/Ho_Chi_Minh").value // 10**6
FOLD_CUTS = [(pd.Timestamp("2021-04-01") + pd.DateOffset(months=3 * i)).strftime("%Y%m%d") for i in range(19)]
RETRAIN = {"G0": dict(feats=V3FULL, label="label_oldbasket", purge=15, seed=42),
           "NOCAL": dict(feats=[c for c in V3FULL if c not in CAL], label="label_oldbasket", purge=15, seed=42),
           "SEED7": dict(feats=V3FULL, label="label_oldbasket", purge=15, seed=7),
           "H60": dict(feats=V3FULL, label="label_h60", purge=60, seed=42)}
MAPPED = ("RND", "RULE", "H60")     # bien doi don dieu ve phan phoi p15 goc (pre-reg 3.1)
ARMS = ["RND", "RULE", "NOCAL", "H60", "SEED7"]
IN_K = ["RND", "RULE", "NOCAL", "H60"]
RND_SEED = 20261004
LABEL60 = D + "/label60.npz"
SPOT = ["2022-06-13", "2024-08-05", "2025-10-10"]


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_pred(p=PRED0):
    raw = open(p, "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:4 + n * 16], dtype=np.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")]))
    assert 4 + n * 16 == len(raw), ("kich thuoc pred.bin", len(raw), n)
    return raw, a


def load_store(cols):
    use = ["timestamp"] + [c for c in cols if c != "label_h60"]
    df = pd.read_csv(STORE, usecols=use, dtype={c: np.float32 for c in use if c != "timestamp"})
    df["timestamp"] = df["timestamp"].astype(np.int64)
    n0 = len(df)
    df = df[df["timestamp"] < SEAL].sort_values("timestamp").reset_index(drop=True)
    assert df["timestamp"].is_unique, "store trung ts"
    if "label_h60" in cols:
        z = np.load(LABEL60)
        lab = pd.Series(z["y60"], index=z["ts"])
        df["label_h60"] = df["timestamp"].map(lab).astype(np.float32)
        log.info("label_h60 join: co nhan %d / %d dong", int(df["label_h60"].notna().sum()), len(df))
    log.info("store %d dong (%d truoc khi cat 2026) %s .. %s", len(df), n0,
             pd.to_datetime(df.timestamp.iloc[0], unit="ms"), pd.to_datetime(df.timestamp.iloc[-1], unit="ms"))
    return df


def align(store_ts, pred_ts):
    j = np.searchsorted(store_ts, pred_ts)
    j = np.clip(j, 0, len(store_ts) - 1)
    ok = store_ts[j] == pred_ts
    return np.where(ok, j, -1)


def ms_local(yyyymmdd):
    return pd.Timestamp(yyyymmdd, tz="Asia/Ho_Chi_Minh").value // 10**6


def fold_bounds(i):
    lo = ms_local(FOLD_CUTS[i])
    hi = ms_local(FOLD_CUTS[i + 1]) if i + 1 < len(FOLD_CUTS) else SEAL
    return lo, hi


def retrain(arm):
    from xgboost import XGBRegressor
    from scipy.stats import pearsonr, spearmanr
    c = RETRAIN[arm]
    df = load_store(c["feats"] + [c["label"]])
    sts = df["timestamp"].to_numpy()
    _, a = read_pred()
    pts = a["ts"].astype(np.int64)
    p0 = a["p15"].astype(np.float32)
    out = p0.copy()
    jj = align(sts, pts)
    X = df[c["feats"]].to_numpy(np.float32)
    y = df[c["label"]].to_numpy(np.float32)
    folds, nmiss = [], 0
    for i, cut in enumerate(FOLD_CUTS):
        tr_cut = pd.Timestamp(cut).value // 10**6 - c["purge"] * 60_000     # y nguyen train_gate_fold.py (UTC)
        m = (sts < tr_cut) & np.isfinite(y)
        assert sts[m].max() < tr_cut
        model = XGBRegressor(objective="reg:squarederror", max_depth=4, n_estimators=150, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8, min_child_weight=10, random_state=c["seed"],
                             n_jobs=4)
        model.fit(X[m], y[m])
        lo, hi = fold_bounds(i)                                                  # OOS theo +07 (WFOGateRunner)
        pi = np.where((pts >= lo) & (pts < hi))[0]
        si = jj[pi]
        ok = si >= 0
        nmiss += int((~ok).sum())
        out[pi[ok]] = model.predict(X[si[ok]]).astype(np.float32)
        q, r = out[pi], p0[pi]
        f = dict(fold=i, cutoff=cut, n_train=int(m.sum()), n_oos=int(len(pi)), miss=int((~ok).sum()),
                 pearson=float(pearsonr(q, r)[0]), spearman=float(spearmanr(q, r).correlation),
                 p50=float(np.median(q)), p50_orig=float(np.median(r)), max=float(q.max()), max_orig=float(r.max()))
        folds.append(f)
        log.info("%s fold %2d %s ntr=%d noos=%d miss=%d pearson=%.5f spearman=%.5f p50 %.6f/%.6f", arm, i, cut,
                 f["n_train"], f["n_oos"], f["miss"], f["pearson"], f["spearman"], f["p50"], f["p50_orig"])
    cover = np.zeros(len(pts), bool)
    for i in range(len(FOLD_CUTS)):
        lo, hi = fold_bounds(i)
        cover |= (pts >= lo) & (pts < hi)
    np.save(D + "/p15_%s.npy" % arm, out)
    res = dict(arm=arm, cfg={k: (v if k != "feats" else len(v)) for k, v in c.items()}, folds=folds,
               n_uncovered=int((~cover).sum()), n_miss_store=nmiss,
               min_pearson=min(f["pearson"] for f in folds), min_spearman=min(f["spearman"] for f in folds))
    json.dump(res, open(D + "/retrain_%s.json" % arm, "w"), indent=1)
    log.info("RETRAIN %s xong: min pearson %.5f min spearman %.5f uncovered %d miss %d", arm, res["min_pearson"],
             res["min_spearman"], res["n_uncovered"], nmiss)
    return res


def series_x(arm, pts):
    """Chuoi xep hang x cua arm (truoc bien doi). NaN = khong co du lieu -> giu p15 goc."""
    if arm == "RND":
        return np.random.default_rng(RND_SEED).random(len(pts))
    if arm == "RULE":
        df = load_store([RULE_COL])
        jj = align(df["timestamp"].to_numpy(), pts)
        v = -df[RULE_COL].to_numpy(np.float64)
        return np.where(jj >= 0, v[np.clip(jj, 0, None)], np.nan)
    return np.load(D + "/p15_%s.npy" % arm).astype(np.float64)


def gen(arm):
    raw, a = read_pred()
    assert md5f(PRED0) == PRED0_MD5
    pts = a["ts"].astype(np.int64)
    p0 = a["p15"].astype(np.float32)
    x = series_x(arm, pts)
    ok = np.isfinite(x)
    if arm in MAPPED:
        y = p0.copy()
        idx = np.where(ok)[0]
        order = idx[np.argsort(x[idx], kind="stable")]
        y[order] = np.sort(p0[idx])                     # hoan vi dung tap gia tri p15 goc theo thu tu x
    else:
        y = np.where(ok, x, p0).astype(np.float32)
    b = a.copy()
    b["p15"] = y.astype(">f4")
    out_dir = D + "/pred_%s" % arm
    os.makedirs(out_dir, exist_ok=True)
    p = out_dir + "/pred.bin"
    with open(p, "wb") as f:
        f.write(raw[:4])
        f.write(b.tobytes())
    md5 = md5f(p)
    meta = dict(arm=arm, md5=md5, n=int(len(b)), n_nan_x=int((~ok).sum()), mapped=arm in MAPPED)
    json.dump(meta, open(out_dir + "/meta.json", "w"), indent=1)
    log.info("GEN %s -> %s md5=%s n=%d nan_x=%d mapped=%s", arm, p, md5, len(b), meta["n_nan_x"], meta["mapped"])
    return meta


def g1(arms=None):
    raw0, a0 = read_pred()
    res = {}
    for arm in arms or ARMS:
        p = D + "/pred_%s/pred.bin" % arm
        if not os.path.exists(p):
            continue
        raw, a = read_pred(p)
        chk = dict(size=len(raw) == len(raw0), header=raw[:4] == raw0[:4], n=len(a) == 2500260,
                   ts_identical=bool((a["ts"] == a0["ts"]).all()), risk_identical=bool((a["risk"] == a0["risk"]).all()),
                   p15_finite=bool(np.isfinite(a["p15"].astype(np.float32)).all()))
        spot = {}
        p0, p1 = a0["p15"].astype(np.float32), a["p15"].astype(np.float32)
        tsl = pd.to_datetime(a0["ts"].astype(np.int64), unit="ms", utc=True).tz_convert("Asia/Ho_Chi_Minh")
        for d in SPOT:
            day = np.where(tsl.strftime("%Y-%m-%d") == d)[0]
            i0, im = day[0], day[np.argmax(p0[day])]
            spot[d] = {str(tsl[i0])[:16]: [round(float(p0[i0]), 6), round(float(p1[i0]), 6)],
                       str(tsl[im])[:16] + " (max goc)": [round(float(p0[im]), 6), round(float(p1[im]), 6)]}
        sp = pd.Series(p1).corr(pd.Series(p0), method="spearman")
        res[arm] = dict(ok=all(chk.values()), checks=chk, md5=md5f(p), spot=spot, spearman_vs_orig=float(sp),
                        p50=float(np.median(p1)), p99=float(np.percentile(p1, 99)), max=float(p1.max()))
        log.info("G1 %-6s %s md5=%s spearman_vs_goc=%.4f %s spot=%s", arm, "PASS" if res[arm]["ok"] else "FAIL",
                 res[arm]["md5"], sp, chk, json.dumps(spot))
    json.dump(res, open(D + "/g1.json", "w"), indent=1)
    return res


# ------------------------------------------------------------------ nhan 60' (pre-reg 3.3)
def parse_day(day):
    """ticker_<day>.bin.gz -> (keys int64[m], syms list, H, C, U float32[m,S]); bo moi phut >= SEAL (2026)."""
    import gzip
    import jbin
    p = os.path.join(TICKER_DIR, "ticker_%s.bin.gz" % day)
    if not os.path.exists(p):
        p = os.path.join(TICKER_DIR, "daily", "ticker_%s.bin.gz" % day)
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rb") as g:
        b = g.read()
    rows = [(k, v) for k, v in jbin.iter_minutes(b) if k < SEAL]
    if not rows:
        return None
    rows.sort(key=lambda r: r[0])
    syms = sorted({s for _, v in rows for s in v})
    ix = {s: i for i, s in enumerate(syms)}
    m, S = len(rows), len(syms)
    H = np.full((m, S), np.nan, np.float32)
    C, U = H.copy(), H.copy()
    for r, (_, v) in enumerate(rows):
        for s, t in v.items():          # t = (startTime, maxPrice, minPrice, priceClose, priceOpen, totalUsdt)
            j = ix[s]
            H[r, j], C[r, j], U[r, j] = t[1], t[3], t[5]
    return np.array([k for k, _ in rows], np.int64), syms, H, C, U


def shifted(A, k):
    """B[t] = A[t+k] (k>0 tuong lai, k<0 qua khu), NaN ngoai bien."""
    B = np.full_like(A, np.nan)
    if k > 0:
        B[:-k] = A[k:]
    elif k < 0:
        B[-k:] = A[:k]
    else:
        B[:] = A
    return B


def label_day(days3):
    """days3 = (prev, cur, next) tu parse_day (prev/next co the None). Tra (ts, y15, y60) cho moi phut cua cur."""
    cur = days3[1]
    keys = cur[0]
    t_lo, t_hi = int(keys.min()) - 15 * 60_000, int(keys.max()) + 60 * 60_000
    T = np.arange(t_lo, t_hi + 1, 60_000, dtype=np.int64)
    syms = sorted({s for d in days3 if d is not None for s in d[1]})
    ix = {s: i for i, s in enumerate(syms)}
    H = np.full((len(T), len(syms)), np.nan, np.float32)
    C, U = H.copy(), H.copy()
    present_min = np.zeros(len(T), bool)
    for d in days3:
        if d is None:
            continue
        k, sy, h, c, u = d
        sel = (k >= t_lo) & (k <= t_hi)
        if not sel.any():
            continue
        r = ((k[sel] - t_lo) // 60_000).astype(np.int64)
        cols = np.array([ix[s] for s in sy], np.int64)
        H[np.ix_(r, cols)], C[np.ix_(r, cols)], U[np.ix_(r, cols)] = h[sel], c[sel], u[sel]
        present_min[r] = True
    # findPotentialLosersShort: max(maxPrice) tren nen startTime >= ts-15' (16 nen), nen hien tai = nen cuoi <= 15'
    Hw = H.copy()
    Cf, Uf = C.copy(), U.copy()
    for k in range(1, 16):
        Hw = np.fmax(Hw, shifted(H, -k))
        miss = np.isnan(Cf)
        Cs, Us = shifted(C, -k), shifted(U, -k)
        Cf[miss], Uf[miss] = Cs[miss], Us[miss]
    with np.errstate(invalid="ignore", divide="ignore"):
        drop = (Cf - Hw) / Hw
        cand = (Uf >= 5000) & (Hw > 0) & (drop < -0.001)
    drop = np.where(cand, drop, np.inf)
    rows = ((keys - t_lo) // 60_000).astype(np.int64)
    dr = drop[rows]
    kk = min(60, dr.shape[1])
    top = np.argpartition(dr, kk - 1, axis=1)[:, :kk] if dr.shape[1] > kk else np.tile(np.arange(dr.shape[1]), (len(rows), 1))
    inb = np.isfinite(np.take_along_axis(dr, top, axis=1))           # chi coin la ung vien that
    out = {}
    for Hh in (15, 60):
        F = np.full_like(H, np.nan)
        anyf = np.zeros(len(T), bool)
        for k in range(1, Hh + 1):
            F = np.fmax(F, shifted(H, k))
            anyf |= shifted(present_min.astype(np.float32)[:, None], k)[:, 0] == 1
        e = np.take_along_axis(C[rows], top, axis=1)                  # entry = close@ts (coin co mat o ts)
        f = np.take_along_axis(F[rows], top, axis=1)
        use = inb & np.isfinite(e) & (e > 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            g = np.where(np.isfinite(f), np.maximum((f.astype(np.float64) - e) / e, 0.0), 0.0)
        g = np.where(use, g, 0.0)
        cnt = use.sum(1)
        y = np.where(cnt > 0, g.sum(1) / np.maximum(cnt, 1), 0.0)
        y = np.where(anyf[rows], y, 0.0)                              # future rong -> 0
        out[Hh] = y.astype(np.float32)
    return keys, out[15], out[60]


def _l60_worker(args):
    wi, days = args
    out_p = D + "/l60_part_%02d.npz" % wi
    if os.path.exists(out_p):
        return out_p
    prevday = (pd.Timestamp(days[0]) - pd.Timedelta(days=1)).strftime("%Y%m%d")
    nextday = lambda d: (pd.Timestamp(d) + pd.Timedelta(days=1)).strftime("%Y%m%d")  # noqa: E731
    prev, cur = parse_day(prevday), parse_day(days[0])
    TS, Y15, Y60 = [], [], []
    for i, d in enumerate(days):
        nxt = parse_day(nextday(d))
        if cur is not None:
            k, y15, y60 = label_day((prev, cur, nxt))
            TS.append(k)
            Y15.append(y15)
            Y60.append(y60)
        prev, cur = cur, nxt
        if i % 30 == 0:
            logging.getLogger("gabl").info("l60 worker %d: %s (%d/%d)", wi, d, i, len(days))
    np.savez(out_p, ts=np.concatenate(TS), y15=np.concatenate(Y15), y60=np.concatenate(Y60))
    return out_p


def label60(workers):
    from multiprocessing import Pool
    days = [d.strftime("%Y%m%d") for d in pd.date_range("2020-12-31", "2025-12-31")]
    ch = np.array_split(np.arange(len(days)), workers * 4)
    jobs = [(i, [days[j] for j in c]) for i, c in enumerate(ch)]
    with Pool(workers) as pool:
        parts = pool.map(_l60_worker, jobs, chunksize=1)
    z = [np.load(p) for p in parts]
    ts = np.concatenate([q["ts"] for q in z])
    y15 = np.concatenate([q["y15"] for q in z])
    y60 = np.concatenate([q["y60"] for q in z])
    ts, first = np.unique(ts, return_index=True)
    y15, y60 = y15[first], y60[first].astype(np.float32)
    y60[ts > SEAL - 61 * 60_000] = np.nan                         # nhan 60' khong nhin vao 2026
    np.savez(LABEL60, ts=ts, y15=y15, y60=y60)
    log.info("LABEL60 %d phut %s .. %s -> %s", len(ts), pd.to_datetime(ts[0], unit="ms"),
             pd.to_datetime(ts[-1], unit="ms"), LABEL60)


def labelgate():
    df = load_store(["label_oldbasket"])
    z = np.load(LABEL60)
    m = pd.DataFrame({"timestamp": z["ts"], "y15": z["y15"], "y60": z["y60"]})
    j = df.merge(m, on="timestamp", how="inner")
    j = j[j.timestamp < ms_local("20251001")]
    yr = pd.to_datetime(j.timestamp, unit="ms", utc=True).dt.tz_convert("Asia/Ho_Chi_Minh").dt.year
    tot = float(np.corrcoef(j.y15, j.label_oldbasket)[0, 1])
    per = {int(y): float(np.corrcoef(g.y15, g.label_oldbasket)[0, 1]) for y, g in j.groupby(yr)}
    mad = float(np.median(np.abs(j.y15 - j.label_oldbasket)))
    res = dict(n_join=int(len(j)), n_store=int((df.timestamp < ms_local("20251001")).sum()), pearson=tot,
               pearson_year=per, median_absdiff=mad, med_store=float(j.label_oldbasket.median()),
               med_replica=float(j.y15.median()), corr_y15_y60=float(np.corrcoef(j.y15, j.y60.fillna(0))[0, 1]),
               med_y60=float(j.y60.median()))
    res["PASS"] = bool(tot >= 0.99 and all(v >= 0.98 for v in per.values()))
    json.dump(res, open(D + "/labelgate.json", "w"), indent=1)
    log.info("LABELGATE %s", json.dumps(res))
    return res


# ------------------------------------------------------------------ Kaggle
KS_MD5_WANT = "8b60b00afad39f2528aaa15092225c9b"
JAR_DS, JAR_SHA = "sim-jar-gdv2", "7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a"
BUNDLE = "sim-x1-2021-bundle"
PROFILE = "r4_kg0_k16_f015_g155"
B0OV = {"SIM_GATE_ROLLING_MODE": "ratio", "SIM_GATE_ROLLING_DAYS": 90, "SIM_GATE_ROLLING_PCT": 0.999950829,
        "TS_GIVEBACK_RATIO": 1.0, "SIM_TS_MAX_GAP": 0.03, "SIM_TS_MAX_GAP_WEAK": 0.03}
OV = dict(B0OV, SELECTOR_RANK_TOPK=24)
TAG = {"A1": "n700-a1", "RND": "gabl-rnd", "RULE": "gabl-rule", "NOCAL": "gabl-nocal", "H60": "gabl-h60",
       "SEED7": "gabl-seed7"}
DSN = {k: "gate-abl-" + k.lower() for k in ARMS}
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
A1_MD5 = "d9abf35fdc93cfbcf7c41c9c62c22c20"
JSON_OUT = os.path.join(REPO, "docs/result/gate_ablation.json")
PATCH_ANCHOR = 'link = os.path.join(WORK, "kaggle_data_hpo")\n'
PATCH_BLOCK = r'''# [GATE_ABLATION 2026-10-04] pred_ds: thay pred.bin (chi cot p15 khac) bang file tu dataset arm.
#   market.bin/funding.bin giu nguyen (symlink); viet lai md5_pred trong manifest (WfoDataset verify md5).
import hashlib as _h3
def _md5(_p):
    _m = _h3.md5()
    with open(_p, "rb") as _f:
        for _b in iter(lambda: _f.read(1 << 20), b""):
            _m.update(_b)
    return _m.hexdigest()
PRED_MD5_BASE = _md5(os.path.join(DS, "pred.bin"))
LOG.info("PRED_MD5_BASE=%s", PRED_MD5_BASE)
if PRED_MD5_BASE != CFG["want_pred_base"]:
    LOG.error("PRED_BASE_MISMATCH %s != %s", PRED_MD5_BASE, CFG["want_pred_base"])
    sys.exit(1)
_pc = [c for c in sorted(glob.glob(IN + "/**/pred.bin", recursive=True)) if ("/" + CFG["pred_ds"] + "/") in c]
if not _pc:
    LOG.error("MISSING pred.bin cho pred_ds=%r", CFG["pred_ds"])
    sys.exit(1)
PRED_MD5_USED = _md5(_pc[0])
LOG.info("PRED_MD5_USED=%s (%s)", PRED_MD5_USED, _pc[0])
if PRED_MD5_USED != CFG["want_pred_md5"]:
    LOG.error("PRED_USED_MISMATCH %s != %s", PRED_MD5_USED, CFG["want_pred_md5"])
    sys.exit(1)
_ovp = os.path.join(WORK, "wfo_ds_pred")
os.makedirs(_ovp, exist_ok=True)
for _nm in ("market.bin", "funding.bin"):
    if not os.path.lexists(os.path.join(_ovp, _nm)):
        os.symlink(os.path.join(DS, _nm), os.path.join(_ovp, _nm))
if not os.path.lexists(os.path.join(_ovp, "pred.bin")):
    os.symlink(_pc[0], os.path.join(_ovp, "pred.bin"))
_ml, _nrep = [], 0
for _ln in open(os.path.join(DS, "manifest.txt")):
    if _ln.startswith("md5_pred="):
        _ml.append("md5_pred=" + PRED_MD5_USED + "\n")
        _nrep += 1
    else:
        _ml.append(_ln)
assert _nrep == 1, _nrep
with open(os.path.join(_ovp, "manifest.txt"), "w") as _f:
    _f.writelines(_ml)
LOG.info("pred_ds=%s -> WFO_DATA_DIR %s md5_pred=%s", CFG["pred_ds"], _ovp, PRED_MD5_USED)
DS = _ovp
'''
RES_OLD = '"n_trades": n_trades, "symbol_mapper": mapper_n, "jar_sha256": JAR_SHA,'
RES_NEW = RES_OLD + ' "pred_md5_base": PRED_MD5_BASE, "pred_md5_used": PRED_MD5_USED,'


def ks_mod():
    from tools import kaggle_sim as ks
    md5 = md5f(os.path.join(REPO, "tools/kaggle_sim.py"))
    assert md5 == KS_MD5_WANT, ("tools/kaggle_sim.py khong phai HEAD NOWRITE242", md5)
    assert "NOWRITE_HOST" in ks.KERNEL_TEMPLATE and "SYMBOL_MAPPER_PREFLIGHT_FAIL" in ks.KERNEL_TEMPLATE
    return ks


def template():
    t = ks_mod().KERNEL_TEMPLATE
    for o, n in ((PATCH_ANCHOR, PATCH_BLOCK + PATCH_ANCHOR), (RES_OLD, RES_NEW)):
        assert t.count(o) == 1, o
        t = t.replace(o, n)
    assert "NOWRITE_HOST" in t and "SYMBOL_MAPPER_PREFLIGHT_FAIL" in t
    return t


def upload(a):
    ks = ks_mod()
    for arm in a.arms:
        meta = json.load(open(D + "/pred_%s/meta.json" % arm))
        fol = D + "/ds_" + arm
        os.makedirs(fol, exist_ok=True)
        dst = fol + "/pred.bin"
        if not os.path.exists(dst):
            os.link(D + "/pred_%s/pred.bin" % arm, dst)
        assert md5f(dst) == meta["md5"]
        json.dump({"title": DSN[arm], "id": ks.USER + "/" + DSN[arm], "licenses": [{"name": "CC0-1.0"}]},
                  open(fol + "/dataset-metadata.json", "w"))
        r = ks._api().dataset_create_new(fol, public=False, quiet=False, dir_mode="skip")
        log.info("upload %s -> %s", arm, getattr(r, "url", r))


def dsstatus(a):
    ks = ks_mod()
    for arm in a.arms or ARMS:
        try:
            log.info("%s %s", DSN[arm], ks._api().dataset_status(ks.USER + "/" + DSN[arm]))
        except Exception as e:
            log.info("%s loi %s", DSN[arm], e)


def submit(a):
    ks = ks_mod()
    assert a.code_sha
    log.info("free_slots=%d", ks.free_slots())
    for arm in a.arms:
        meta = json.load(open(D + "/pred_%s/meta.json" % arm))
        tag = TAG[arm]
        ref = ks.kernel_ref(tag)
        folder = os.path.join(ks.WORKDIR, ks.slug(tag))
        os.makedirs(folder, exist_ok=True)
        cfg = {"tag": tag, "profile": PROFILE, "overrides": dict(OV), "sim_end_date": "20251231", "xmx": "22g",
               "timeout_s": 7200, "code_sha": a.code_sha, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "",
               "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
               "pred_ds": DSN[arm], "want_pred_md5": meta["md5"], "want_pred_base": PRED0_MD5}
        code = template().replace("__CFG_JSON__", repr(json.dumps(cfg)))
        with open(os.path.join(folder, "run.py"), "w") as f:
            f.write(code)
        md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
              "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
              "dataset_sources": [ks.USER + "/" + BUNDLE] + ks.TICKER_DS
                                 + [ks.USER + "/" + JAR_DS, ks.USER + "/" + DSN[arm]],
              "competition_sources": [], "kernel_sources": []}
        with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
            json.dump(md, f, indent=1)
        r = ks._api().kernels_push(folder)
        log.info("PUSHED %s %s pred_md5=%s ov=%s", arm, getattr(r, "url", r), meta["md5"], json.dumps(OV))


def status(a):
    ks = ks_mod()
    for arm in a.arms or ARMS:
        try:
            log.info("%s %s", arm, ks._status(ks.kernel_ref(TAG[arm])))
        except Exception as e:
            log.info("%s chua co (%s)", arm, str(e)[:80])


def fetch(a):
    ks = ks_mod()
    for arm in a.arms:
        o = ks.fetch(TAG[arm])
        log.info("%s %s", arm, json.dumps(o.get("result"), default=str)[:700])


def result_json(tag):
    p = OUT % tag + "result.json"
    return json.load(open(p)) if os.path.exists(p) else {}


def prof_run(tag):
    p, out = OUT % tag + "prof_run.properties", {}
    if os.path.exists(p):
        for ln in open(p):
            if "=" in ln and not ln.startswith("#"):
                k, v = ln.rstrip("\n").split("=", 1)
                out[k.strip()] = v.strip()
    return out


def parity(a=None):
    import reset_rule_score as R
    res = {}
    for arm in ARMS:
        tag = TAG[arm]
        if not os.path.exists(OUT % tag + "storage/printDone.csv"):
            continue
        rj, pr = result_json(tag), prof_run(tag)
        meta = json.load(open(D + "/pred_%s/meta.json" % arm))
        chk = dict(jar=rj.get("jar_sha256") == JAR_SHA, mapper=(rj.get("symbol_mapper") or 0) >= 800,
                   topk24=pr.get("SELECTOR_RANK_TOPK") == "24", ok=rj.get("ok") is True,
                   pred_used=rj.get("pred_md5_used") == meta["md5"], pred_base=rj.get("pred_md5_base") == PRED0_MD5,
                   b0ov=all(pr.get(k) == str(v) for k, v in B0OV.items()))
        res[arm] = dict(ok=all(chk.values()), checks=chk, md5=R.md5_of(tag), n=int(len(R.load_legs(tag))),
                        eq=float(R.load_daily(tag)["equity"].iloc[-1]), pred_md5=meta["md5"],
                        date_first=rj.get("date_first"), date_last=rj.get("date_last"), secs=rj.get("secs"))
        log.info("PARITY %-5s %s n=%d eq=%.0f md5=%s pred=%s %s", arm, "PASS" if res[arm]["ok"] else "*** VOID ***",
                 res[arm]["n"], res[arm]["eq"], res[arm]["md5"][:8], meta["md5"][:8], chk)
    json.dump(res, open(D + "/parity.json", "w"), indent=1)
    return res


def gate_minutes(tag):
    d = pd.read_csv(OUT % tag + "storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    d = d[d["level"].astype(str).str.strip() == "PREDICT_SYMBOL_TRADE"]
    t = pd.to_datetime(d["start"], format="%Y%m%d %H:%M", errors="coerce").dropna()
    t = t[(t >= "2022-01-01") & (t < "2026-01-01")]
    u = t.drop_duplicates()
    per = {int(y): int(v) for y, v in u.groupby(u.dt.year).size().items()}
    return dict(per_year=per, mean=float(len(u)) / 4.0)


INFL = math.sqrt(2.0 * math.log(4))      # k = 4 (RND, RULE, NOCAL, H60)
W0 = pd.Timestamp("2021-12-31")
YEARS = [2022, 2023, 2024, 2025]
N700_MTM = "/home/ubuntu/claude_master/1003/n700/mtm.json"


def q_mtm(daily):
    e = daily["equity"].copy()
    e.index = pd.to_datetime(e.index)
    e = e[e.index >= W0]
    qe = e.groupby(e.index.to_period("Q")).last()
    prev = qe.shift(1)
    prev.iloc[0] = float(e.iloc[0])
    return {str(q): float(100 * (qe[q] / prev[q] - 1)) for q in qe.index if str(q) < "2026Q1"}


def score(a):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401  (side effect: MTMState cua so 2022+)
    import flat3_crashpen_driver as F3
    import selector_ablation_driver as SAD
    import n700_driver as N
    R.MTM_COSTS = {"legacy": R.LEGACY}
    SAD.INFL = INFL
    N.INFL = INFL
    N.TAG.update(TAG)
    N.DESC.update({k: "GATE_ABL " + k for k in ARMS})
    par = parity()
    keys = ["A1"] + [k for k in ARMS if k in par and par[k]["ok"]]
    legs, daily, md5 = {}, {}, {}
    for k in keys:
        legs[k], daily[k], md5[k] = R.load_legs(TAG[k]), R.load_daily(TAG[k]), R.md5_of(TAG[k])
    assert md5["A1"] == A1_MD5, md5["A1"]
    raw = json.load(open(D + "/mtm.json")) if os.path.exists(D + "/mtm.json") else {}
    if "A1" not in raw and os.path.exists(N700_MTM):
        n7 = json.load(open(N700_MTM))
        if n7.get("A1", {}).get("md5") == A1_MD5:
            raw["A1"] = n7["A1"]
    miss = {k: legs[k] for k in keys if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM cache %s; can tinh %s", sorted(raw), sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=a.workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        json.dump(raw, open(D + "/mtm.json", "w"))
    M = {k: N.arm_metrics(R, F3, k, legs[k], daily[k], raw[k]["legacy"]) for k in keys}
    for k in keys:
        M[k]["md5"] = md5[k]
        M[k]["gate_minutes"] = gate_minutes(TAG[k])
        M[k]["q_mtm"] = q_mtm(daily[k])
        M[k]["overlap_vs_A1"] = SAD.overlap(legs["A1"], legs[k])
    eqs = {("P0" if k == "A1" else k): daily[k]["equity"][daily[k]["equity"].index >= W0] for k in keys}
    idx = eqs["P0"].index
    for k in eqs:
        assert len(eqs[k]) == len(idx) and (eqs[k].index == idx).all(), ("lech chi so ngay", k)
    obs, bs = SAD.daily_boot(eqs)
    obs["A1"], bs["A1"] = obs.pop("P0"), bs.pop("P0")
    mets = ("cagr", "mdd", "calmar", "sharpe")
    pairs = [(k, "A1") for k in keys if k != "A1"] + [(x, "SEED7") for x in ("NOCAL", "H60") if x in keys and "SEED7" in keys]
    con = {x + "-" + y: {m: SAD.ci_of(obs[x][m] - obs[y][m], bs[x][m] - bs[y][m]) for m in mets} for x, y in pairs}
    dp = N.pnl_boot(legs, idx, keys, pairs)
    for x, y in pairs:
        con[x + "-" + y]["pnl"] = dp[x + "-" + y]
    finish(M, obs, con, par, keys)


def finish(M, obs, con, par, keys):
    A = M["A1"]
    g2 = {}
    for k in keys:
        if k == "A1":
            continue
        rn = M[k]["n_per_year"] / A["n_per_year"]
        rg = M[k]["gate_minutes"]["mean"] / A["gate_minutes"]["mean"]
        g2[k] = dict(ok=bool(0.75 <= rn <= 1.25 and 0.75 <= rg <= 1.25), ratio_n=rn, ratio_gate_min=rg)
    d = {k: con[k + "-A1"]["cagr"] for k in keys if k != "A1"}
    s7 = abs(d["SEED7"]["d"]) if "SEED7" in d else float("nan")
    dy = {k: {y: (M[k]["roi_year"].get(y, np.nan) - A["roi_year"].get(y, np.nan)) for y in YEARS} for k in keys}
    dq = {k: {q: M[k]["q_mtm"][q] - A["q_mtm"].get(q, np.nan) for q in M[k]["q_mtm"]} for k in keys}
    ans = {}
    valid = lambda k: k in d and g2.get(k, {}).get("ok")  # noqa: E731
    if valid("RND"):
        lo, hi = d["RND"]["ci_infl"]
        ans["Q1"] = ("gate co gia tri timing" if hi < 0 else "gate model kem ngau nhien" if lo > 0
                     else "khong do duoc gia tri timing")
    if valid("RULE"):
        lo, hi = d["RULE"]["ci_infl"]
        ans["Q2"] = ("33 feature > 1 quy tac" if hi < 0 else "quy tac > model" if lo > 0 else "33 feature ~ 1 quy tac")
    if valid("NOCAL") and "SEED7" in d:
        x = d["NOCAL"]
        ans["Q3"] = ("khong phan biet duoc voi nhieu retrain" if abs(x["d"]) <= s7 else
                     "vuot band nhieu retrain (dCAGR22 %+.2f)" % x["d"])
        ans["Q3_simplify"] = bool(x["ci_infl"][0] <= 0 <= x["ci_infl"][1] and x["d"] >= d["SEED7"]["d"] - s7)
    if valid("H60") and "SEED7" in d:
        x, h = d["H60"], M["H60"]
        go = dict(c1=x["ci_infl"][0] > 0, c2=h["dd_mtm"] >= -40 and h["dd_mtm22"] >= -40,
                  c3=h["calmar22"] >= 0.9 * A["calmar22"], c4=sum(1 for v in dy["H60"].values() if v >= 0) >= 3)
        ans["Q4"] = ("khong phan biet duoc voi nhieu retrain" if abs(x["d"]) <= s7 else
                     "vuot band nhieu retrain (dCAGR22 %+.2f)" % x["d"])
        ans["Q4_GO"] = dict(GO=bool(all(go.values())), **{kk: bool(v) for kk, v in go.items()})
    if "SEED7" in d:
        ans["Q5"] = dict(abs_dCAGR22=s7, dCAGR22=d["SEED7"]["d"], dPnL=con["SEED7-A1"]["pnl"]["d"])
    log.info("%-6s %5s %6s %7s %6s %7s %5s %6s %7s", "arm", "n", "n/nam", "gateMin", "CAGR22", "ddMTM22", "UW22",
             "Cal22", "PnL2225")
    for k in keys:
        x = M[k]
        log.info("%-6s %5d %6.0f %7.0f %6.2f %7.2f %5.0f %6.3f %7.0f", k, x["n"], x["n_per_year"],
                 x["gate_minutes"]["mean"], x["cagr22"], x["dd_mtm22"], x["uw_mtm22"], x["calmar22"],
                 x["sum_pnl_2022_25"])
    for cc, v in con.items():
        log.info("CON %-12s dCAGR %+.2f raw[%+.2f;%+.2f] infl[%+.2f;%+.2f] dPnL %+.0f infl[%+.0f;%+.0f]", cc,
                 v["cagr"]["d"], *v["cagr"]["ci_raw"], *v["cagr"]["ci_infl"], v["pnl"]["d"], *v["pnl"]["ci_infl"])
    for k in keys:
        if k != "A1":
            log.info("YEAR %-6s dROI %s | G2 %s", k, {y: round(v, 2) for y, v in dy[k].items()}, g2[k])
    log.info("ANS %s", json.dumps(ans, ensure_ascii=False))
    js = dict(prereg="docs/prereg/PREREG_GATE_ABLATION.md", prereg_commit="bfdd3407", k_infl=4, inflate=INFL,
              nrep=2000, seed=20260905, block_days=10, window="2022-01-01..2025-12-30 (rebase 2021-12-31)",
              jar_sha256=JAR_SHA, kaggle_sim_md5=KS_MD5_WANT, tags=TAG, parity=par, g2=g2, boot_obs=obs,
              contrasts=con, d_roi_year=dy, d_q_mtm=dq, answers=ans, metrics=M)
    for nm in ("g1", "retrain_G0", "retrain_NOCAL", "retrain_SEED7", "retrain_H60", "labelgate", "ic"):
        p = D + "/%s.json" % nm
        if os.path.exists(p):
            js[nm] = json.load(open(p))
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", JSON_OUT)


def ic(a=None):
    """Offline (bao cao): rank-IC phut cua p15 goc + moi p15' voi nhan 15' (store) va 60' (dung lai), 2022-01..2025-09."""
    from scipy.stats import spearmanr
    df = load_store(["label_oldbasket"])
    z = np.load(LABEL60)
    lab = df.merge(pd.DataFrame({"timestamp": z["ts"], "y60": z["y60"]}), on="timestamp", how="inner")
    lab = lab[(lab.timestamp >= ms_local("20220101")) & (lab.timestamp < ms_local("20251001"))]
    lab = lab[np.isfinite(lab.y60)]
    _, a0 = read_pred()
    pts = a0["ts"].astype(np.int64)
    j = align(pts, lab.timestamp.to_numpy())
    lab = lab[j >= 0]
    j = j[j >= 0]
    yr = pd.to_datetime(lab.timestamp, unit="ms", utc=True).dt.tz_convert("Asia/Ho_Chi_Minh").dt.year.to_numpy()
    out = {}
    for arm in ["ORIG"] + ARMS:
        p = PRED0 if arm == "ORIG" else D + "/pred_%s/pred.bin" % arm
        if not os.path.exists(p):
            continue
        q = read_pred(p)[1]["p15"].astype(np.float32)[j]
        r = dict(n=int(len(j)), ic15=float(spearmanr(q, lab.label_oldbasket).correlation),
                 ic60=float(spearmanr(q, lab.y60).correlation))
        r["ic15_year"] = {int(y): float(spearmanr(q[yr == y], lab.label_oldbasket.to_numpy()[yr == y]).correlation)
                          for y in YEARS}
        out[arm] = r
        log.info("IC %-6s ic15 %.4f ic60 %.4f year15 %s", arm, r["ic15"], r["ic60"],
                 {y: round(v, 3) for y, v in r["ic15_year"].items()})
    json.dump(out, open(D + "/ic.json", "w"), indent=1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--code-sha", default="")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(D, exist_ok=True)
    g = globals()
    if a.cmd == "retrain":
        for x in a.arms:
            retrain(x)
    elif a.cmd == "gen":
        for x in a.arms:
            gen(x)
    elif a.cmd == "g1":
        g1(a.arms or None)
    elif a.cmd == "label60":
        label60(a.workers)
    elif a.cmd == "labelgate":
        labelgate()
    elif a.cmd == "testday":
        import time
        t0 = time.time()
        d3 = [parse_day(x) for x in a.arms]
        t1 = time.time()
        k, y15, y60 = label_day(tuple(d3))
        log.info("parse %.1fs label %.1fs n=%d y15 p50 %.5f y60 p50 %.5f", t1 - t0, time.time() - t1, len(k),
                 np.median(y15), np.median(y60))
        np.savez(D + "/testday.npz", ts=k, y15=y15, y60=y60)
    elif a.cmd in g and callable(g[a.cmd]):
        g[a.cmd](a)
    else:
        raise SystemExit("cmd?")


if __name__ == "__main__":
    main()
