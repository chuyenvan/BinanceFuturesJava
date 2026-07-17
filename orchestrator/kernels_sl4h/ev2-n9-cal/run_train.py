#!/usr/bin/env python3
# EV2-N9-CAL — sl4h-ev2 voi N_PCT=9 + CALIBRATION xac suat (vong 3b).
# BOI CANH: sl4h-ev2 (n6) PASS voi gate p6>=0.7 -> +1.74%/keo (ke toan SL-cung-4h). Khi day target
#   len N=9 (kho hon, base_rate thap hon) xac suat clf de bi "over-confident" -> nguong P* tho cua
#   p-raw co the lech. THU: sau khi fit clf, hoc anh xa hieu chinh (IsotonicRegression) tren train-tail
#   20% -> p-calibrated. So sanh GATING theo p-raw vs p-calibrated, P* in {0.5,0.6,0.7,0.8}.
# KE TOAN SL-cung-4h: keo HIT (maxFav_4h>=9%) -> +9% ; MISS -> retEnd_4h thuc %. Tai dung pipeline sl4h-ev2.
# CALIBRATION: clf fit tren train-core (80% dau theo ts); IsotonicRegression fit tren train-tail (20% cuoi)
#   anh xa p_raw->hit (out-of-fit, khong ro ri); ap len test. So sanh 2 bang gating. best_raw / best_cal
#   = P* co n_trades_med>=MIN va pnl_per_trade_med cao nhat.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
N_PCT = int(os.environ.get("N_PCT", "9"))    # target % — n9 (kho hon n6)
NEED_BARS_4H = 16                            # nBars_4h >= 16 (cua so 4h tren luoi 15m)
PSTAR_GRID = [0.5, 0.6, 0.7, 0.8]            # nguong P* cho gating (raw & calibrated)
CAL_TAIL_FRAC = 0.20                         # ty le train-tail dung fit isotonic
MIN_TRADES_FOLD = 30                         # tieu chi: >=30 keo/quy
RANDOM_REPS = 10                             # so lan lay ngau nhien do baseline
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ev2-n9-cal")


def find1(p):
    m = sorted(glob.glob(p, recursive=True))
    assert m, f"KHONG TIM THAY: {p}"
    return m[0]


TOOL1_GLOB = os.environ.get("TOOL1_GLOB", "/kaggle/input/**/ff_*.bin")
OI_FILE = os.environ.get("OI_FILE") or find1("/kaggle/input/**/oi_percoin_full.bin")
LABEL_CSV = os.environ.get("LABEL_CSV") or find1("/kaggle/input/**/funding_label.csv")
MAP_CSV = os.environ.get("MAP_CSV") or find1("/kaggle/input/**/symbol_map.csv")
OUT_DIR = os.environ.get("OUT_DIR", "/kaggle/working")
OI_TOL_MS = int(os.environ.get("OI_TOL_MS", str(2 * 60 * 60 * 1000)))
OOS_MONTHS = int(os.environ.get("OOS_MONTHS", "3"))
FIRST_OOS = os.environ.get("FIRST_OOS", "202301")
LAST = os.environ.get("LAST", "202606")
SEED = int(os.environ.get("SEED", "42"))
SMOKE = os.environ.get("SMOKE", "0") == "1"
N_ESTIMATORS = int(os.environ.get("N_ESTIMATORS", "400"))
os.makedirs(OUT_DIR, exist_ok=True)


def _read(path, dt, item, grid=False):
    raw = open(path, "rb").read()
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    assert len(raw) % item == 0, f"{path}: len {len(raw)} khong chia het {item}"
    a = np.frombuffer(raw, dtype=dt)
    if grid:
        a = a[(a["ts"] % GRID_MS) == 0]
    return a


def load_tool1():
    files = sorted(glob.glob(TOOL1_GLOB, recursive=True))
    assert files, f"Tool1 khong thay: {TOOL1_GLOB}"
    parts = [_read(fp, TOOL1_DT, 170, grid=True) for fp in files]
    a = np.concatenate(parts)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(40):
        df[f"f{j}"] = F[:, j]
    log.info("Tool1 (15m grid): %d rows | %d symId | ts[%s..%s]", len(df), df.symId.nunique(),
             pd.to_datetime(df.ts.min(), unit="ms"), pd.to_datetime(df.ts.max(), unit="ms"))
    return df.sort_values("ts").reset_index(drop=True)


def load_oi():
    a = _read(OI_FILE, OI_DT, 30)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    O = np.asarray(a["oi"], dtype=np.float32)
    for j, nm in enumerate(OI_NAMES):
        df[nm] = O[:, j]
    log.info("OI: %d rows | %d symId", len(df), df.symId.nunique())
    return df.sort_values("ts").reset_index(drop=True)


def build_features():
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    del t, o
    log.info("Features ghep: %d rows | n_sym=%d", len(merged), merged.symbol.nunique())
    return merged.sort_values("ts").reset_index(drop=True)


def build_folds():
    cur = pd.Timestamp(f"{FIRST_OOS[:4]}-{FIRST_OOS[4:]}-01")
    last = pd.Timestamp(f"{LAST[:4]}-{LAST[4:]}-01")
    folds = []
    while cur < last:
        nxt = cur + pd.DateOffset(months=OOS_MONTHS)
        folds.append((cur.value // 10**6, min(nxt.value // 10**6, last.value // 10**6)))
        cur = nxt
    return folds


def _med(vals):
    vals = [v for v in vals if v is not None]
    return round(float(np.median(vals)), 4) if vals else None


def load_labels():
    """hit = maxFav_4h >= N_PCT/100 ; ret_pct = retEnd_4h*100 (return thuc %)."""
    df = pd.read_csv(LABEL_CSV, usecols=["tEpochMs", "symbol", "maxFav_4h", "retEnd_4h", "nBars_4h"],
                     on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    df = df[(df["nBars_4h"] >= NEED_BARS_4H) & df["maxFav_4h"].notna() & df["retEnd_4h"].notna()].copy()
    df["hit"] = (df["maxFav_4h"].values >= N_PCT / 100.0).astype(np.int8)
    df["ret_pct"] = (df["retEnd_4h"].values * 100.0).astype(np.float32)
    log.info("Label n%d: %d/%d rows | base_rate(HIT)=%.4f | ret_pct mean=%.3f",
             N_PCT, len(df), n0, float(df.hit.mean()), float(df.ret_pct.mean()))
    return df[["ts", "symbol", "hit", "ret_pct"]]


def fit_predict_cal(xgb, tr, te):
    """clf fit tren train-core (80% dau theo ts). IsotonicRegression fit tren train-tail (20% cuoi)
       anh xa p_raw->hit -> p_cal. Ap len test. Tra (p_raw_te, p_cal_te, auc_te)."""
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import roc_auc_score
    tr = tr.sort_values("ts").reset_index(drop=True)
    ncut = int(len(tr) * (1.0 - CAL_TAIL_FRAC))
    core = tr.iloc[:ncut]
    tail = tr.iloc[ncut:]
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(core[FEAT], core["hit"])
    p_raw_te = clf.predict_proba(te[FEAT])[:, 1]
    # isotonic tren train-tail (out-of-fit so voi core -> khong ro ri)
    p_tail = clf.predict_proba(tail[FEAT])[:, 1]
    if tail["hit"].nunique() > 1 and len(tail) >= 200:
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(p_tail, tail["hit"].values)
        p_cal_te = iso.predict(p_raw_te)
    else:
        p_cal_te = p_raw_te.copy()                    # khong du data calibrate -> fallback raw
    try:
        auc = float(roc_auc_score(te["hit"].values, p_raw_te)) if te["hit"].nunique() > 1 else None
    except Exception:
        auc = None
    return p_raw_te, p_cal_te, auc


def gate_eval(te, p, rng):
    """Voi moi P* in PSTAR_GRID: n_trades, pnl_per_trade (SL-cung), hit_rate, random cung n."""
    hit = te["hit"].values
    pnl = np.where(hit == 1, float(N_PCT), te["ret_pct"].values)
    out = {}
    for ps in PSTAR_GRID:
        idx = np.where(p >= ps)[0]
        n = int(len(idx))
        if n == 0:
            out[ps] = {"n": 0, "pnl": None, "hit": None, "rnd": None}
            continue
        rnd = float(np.mean([pnl[rng.choice(len(pnl), n, replace=False)].mean()
                             for _ in range(RANDOM_REPS)]))
        out[ps] = {"n": n, "pnl": round(float(pnl[idx].mean()), 4),
                   "hit": round(float(hit[idx].mean()), 4), "rnd": round(rnd, 4)}
    return out


def run():
    feats = build_features()
    lb = load_labels()
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows | base_rate=%.4f", len(ds), float(ds.hit.mean()))
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:1]
        log.info("SMOKE: chi chay fold 0")
    log.info("EV2-N9-CAL n%d: %d fold expanding OOS=%dm", N_PCT, len(folds), OOS_MONTHS)

    purge = NEED_BARS_4H * GRID_MS
    auc_hist = []
    raw_hist = {ps: {"pnl": [], "n": [], "hit": [], "rnd": []} for ps in PSTAR_GRID}
    cal_hist = {ps: {"pnl": [], "n": [], "hit": [], "rnd": []} for ps in PSTAR_GRID}
    rng = np.random.default_rng(SEED)

    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit"].sum() < 50 or (tr["hit"] == 0).sum() < 50:
            log.warning("fold %d thieu data (tr=%d te=%d hit=%d) - bo", fi, len(tr), len(te),
                        int(tr["hit"].sum()))
            continue
        p_raw, p_cal, auc = fit_predict_cal(xgb, tr, te)
        if auc is not None:
            auc_hist.append(auc)
        fr_raw = gate_eval(te, p_raw, rng)
        fr_cal = gate_eval(te, p_cal, rng)
        for ps in PSTAR_GRID:
            for src, fr in ((raw_hist, fr_raw), (cal_hist, fr_cal)):
                src[ps]["pnl"].append(fr[ps]["pnl"]); src[ps]["n"].append(fr[ps]["n"])
                src[ps]["hit"].append(fr[ps]["hit"]); src[ps]["rnd"].append(fr[ps]["rnd"])
        log.info("fold %d [%s..%s] AUC=%s | raw p0.7 pnl=%s n=%s | cal p0.7 pnl=%s n=%s",
                 fi, str(pd.to_datetime(cut, unit="ms").date()),
                 str(pd.to_datetime(oos_end, unit="ms").date()),
                 round(auc, 4) if auc else None, fr_raw[0.7]["pnl"], fr_raw[0.7]["n"],
                 fr_cal[0.7]["pnl"], fr_cal[0.7]["n"])

    if not auc_hist and all(len(raw_hist[ps]["n"]) == 0 for ps in PSTAR_GRID):
        raise SystemExit("Khong fold nao hop le — kiem alignment ts/symbol.")
    finalize(auc_hist, raw_hist, cal_hist)


def _agg(hist):
    """Tong hop median qua fold cho tung P* + chon best (n_med>=MIN, max pnl_med)."""
    tab = {}
    for ps, h in hist.items():
        tab[ps] = {"pstar": ps, "n_med": _med(h["n"]), "pnl_med": _med(h["pnl"]),
                   "hit_med": _med(h["hit"]), "rnd_med": _med(h["rnd"])}
    cand = [t for t in tab.values() if t["pnl_med"] is not None]
    ok = [t for t in cand if (t["n_med"] or 0) >= MIN_TRADES_FOLD]
    pool = ok if ok else cand
    best = max(pool, key=lambda z: z["pnl_med"]) if pool else None
    return tab, best


def _print_tab(name, tab):
    print(f"\n===== GATING {name} (median qua fold) — n{N_PCT} =====")
    print("P*    n_med   pnl/keo  rand    hit")
    for ps in PSTAR_GRID:
        t = tab[ps]
        print("%.1f   %-7s %-8s %-7s %-6s" % (ps, t["n_med"], t["pnl_med"], t["rnd_med"], t["hit_med"]))


def finalize(auc_hist, raw_hist, cal_hist):
    auc = _med(auc_hist)
    tab_raw, best_raw = _agg(raw_hist)
    tab_cal, best_cal = _agg(cal_hist)
    _print_tab("p-RAW", tab_raw)
    _print_tab("p-CALIBRATED", tab_cal)

    def _b(b):
        return ({"pstar": b["pstar"], "pnl_per_trade_med": b["pnl_med"],
                 "n_trades_per_fold_med": b["n_med"], "hit_rate": b["hit_med"]} if b else None)

    result = {"n_pct": N_PCT, "auc": auc, "best_raw": _b(best_raw), "best_cal": _b(best_cal)}
    full = {"n_pct": N_PCT, "auc": auc,
            "raw": {str(ps): tab_raw[ps] for ps in PSTAR_GRID},
            "cal": {str(ps): tab_cal[ps] for ps in PSTAR_GRID},
            "best_raw": _b(best_raw), "best_cal": _b(best_cal)}
    json.dump(full, open(os.path.join(OUT_DIR, f"ev2_n{N_PCT}_cal_results.json"), "w"), indent=2)
    print("EV2N9CAL_RESULT " + json.dumps(result))
    log.info("XONG -> %s/ev2_n%d_cal_results.json", OUT_DIR, N_PCT)


if __name__ == "__main__":
    run()
