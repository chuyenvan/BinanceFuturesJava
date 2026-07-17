#!/usr/bin/env python3
# SL4H-TAIL-SL — tail predictor (q90 dip depth) -> adaptive disaster-SL, so voi fixed-SL.
# Muc tieu: chan duoi trai (2026 miss ~-17%) bang SL per-trade tu model, KHONG fixed cung.
# Target: dip = |maxAdv_4h|*100 (do sau cu dip toi te trong cua so). Quantile reg q90.
# SL sim proxy (dung cot label): stopped = dip >= L VA adverse den TRUOC favorable (tHitAdv<=tHitFav).
#   stopped -> pnl = -L ; else -> hit? +N : retEnd_4h. So L in {none, fix5, fix8, adaptive=q90_pred}.
# Gate = clfP6>=0.7 (co-train). Ke toan SL-cung. Reuse 100% preamble load cua sl4h-ev2-n6.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

N_PCT = int(os.environ.get("N_PCT", "6"))
NEED_BARS_4H = 16
Q_ALPHA = float(os.environ.get("Q_ALPHA", "0.9"))
PSTAR = float(os.environ.get("PSTAR", "0.7"))
MIN_TRADES_FOLD = 30
SEED = int(os.environ.get("SEED", "42"))
GRID_MS = 15 * 60 * 1000
N_ESTIMATORS = int(os.environ.get("N_ESTIMATORS", "400"))

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sl4h-tail-sl")


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
SMOKE = os.environ.get("SMOKE", "0") == "1"
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
    log.info("Tool1 (15m grid): %d rows | %d symId", len(df), df.symId.nunique())
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


def load_labels():
    """hit, ret_pct, dip=|maxAdv_4h|*100, fav_first (tHitFav<=tHitAdv & tHitFav>0)."""
    cols = ["tEpochMs", "symbol", "maxFav_4h", "retEnd_4h", "nBars_4h",
            "maxAdv_4h", "tHitFav_4h", "tHitAdv_4h"]
    df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    df = df[(df["nBars_4h"] >= NEED_BARS_4H) & df["maxFav_4h"].notna()
            & df["retEnd_4h"].notna() & df["maxAdv_4h"].notna()].copy()
    df["hit"] = (df["maxFav_4h"].values >= N_PCT / 100.0).astype(np.int8)
    df["ret_pct"] = (df["retEnd_4h"].values * 100.0).astype(np.float32)
    df["dip"] = np.abs(df["maxAdv_4h"].values * 100.0).astype(np.float32)
    thf = df["tHitFav_4h"].fillna(-1).values
    tha = df["tHitAdv_4h"].fillna(1 << 62).values
    df["fav_first"] = ((thf > 0) & (thf <= tha)).astype(np.int8)
    log.info("Label n%d: %d rows | base_hit=%.4f | dip mean=%.2f p50=%.2f p90=%.2f",
             N_PCT, len(df), float(df.hit.mean()), float(df.dip.mean()),
             float(np.percentile(df.dip, 50)), float(np.percentile(df.dip, 90)))
    return df[["ts", "symbol", "hit", "ret_pct", "dip", "fav_first"]]


def build_folds():
    cur = pd.Timestamp(f"{FIRST_OOS[:4]}-{FIRST_OOS[4:]}-01")
    last = pd.Timestamp(f"{LAST[:4]}-{LAST[4:]}-01")
    folds = []
    while cur < last:
        nxt = cur + pd.DateOffset(months=OOS_MONTHS)
        folds.append((cur.value // 10**6, min(nxt.value // 10**6, last.value // 10**6)))
        cur = nxt
    return folds


def pinball(y, pred, alpha):
    e = y - pred
    return float(np.mean(np.maximum(alpha * e, (alpha - 1.0) * e)))


def sl_pnl(sub, L):
    """L scalar (fixed) hoac vector (adaptive). stopped = dip>=L & KHONG fav_first -> -L."""
    dip = sub["dip"].values
    Lv = np.full(len(sub), L, dtype=float) if np.isscalar(L) else np.asarray(L, dtype=float)
    stopped = (dip >= Lv) & (sub["fav_first"].values == 0)
    base = np.where(sub["hit"].values == 1, float(N_PCT), sub["ret_pct"].values)
    pnl = np.where(stopped, -Lv, base)
    return pnl, float(stopped.mean())


def run():
    feats = build_features()
    lb = load_labels()
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows | base_hit=%.4f", len(ds), float(ds.hit.mean()))
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:1]
    purge = NEED_BARS_4H * GRID_MS

    opts = ["none", "fix5", "fix8", "adaptive"]
    hist = {o: {"pnl": [], "n": [], "stop": []} for o in opts}
    cov_hist, pin_hist, pin_base_hist, imp_hist = [], [], [], []

    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit"].sum() < 50 or (tr["hit"] == 0).sum() < 50:
            log.warning("fold %d thieu data (tr=%d te=%d) - bo", fi, len(tr), len(te))
            continue
        clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                                subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                objective="binary:logistic", eval_metric="logloss",
                                n_jobs=-1, tree_method="hist", random_state=SEED)
        clf.fit(tr[FEAT], tr["hit"])
        p6 = clf.predict_proba(te[FEAT])[:, 1]
        qreg = xgb.XGBRegressor(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                                subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                objective="reg:quantileerror", quantile_alpha=Q_ALPHA,
                                n_jobs=-1, tree_method="hist", random_state=SEED)
        qreg.fit(tr[FEAT], tr["dip"])
        q90 = qreg.predict(te[FEAT]).astype(float)
        q90 = np.clip(q90, 0.5, 50.0)
        cov = float(np.mean(te["dip"].values <= q90))
        pin = pinball(te["dip"].values, q90, Q_ALPHA)
        base_q = float(np.quantile(tr["dip"].values, Q_ALPHA))
        pin_base = pinball(te["dip"].values, np.full(len(te), base_q), Q_ALPHA)
        cov_hist.append(cov); pin_hist.append(pin); pin_base_hist.append(pin_base)
        imp_hist.append(qreg.feature_importances_)
        mask = p6 >= PSTAR
        sel = te[mask].copy()
        q90_sel = q90[mask]
        if len(sel) == 0:
            continue
        Lmap = {"none": 999.0, "fix5": 5.0, "fix8": 8.0, "adaptive": q90_sel}
        for o in opts:
            pnl, sr = sl_pnl(sel, Lmap[o])
            hist[o]["pnl"].append(float(pnl.mean()))
            hist[o]["n"].append(int(len(sel)))
            hist[o]["stop"].append(sr)
        log.info("fold %d [%s] n_gate=%d cov=%.3f pin=%.3f(base %.3f) none=%.3f fix5=%.3f adaptive=%.3f",
                 fi, str(pd.to_datetime(cut, unit="ms").date()), len(sel), cov, pin, pin_base,
                 hist["none"]["pnl"][-1], hist["fix5"]["pnl"][-1], hist["adaptive"]["pnl"][-1])

    def med(v):
        v = [x for x in v if x is not None]
        return round(float(np.median(v)), 4) if v else None

    def worst(v):
        v = [x for x in v if x is not None]
        return round(float(np.min(v)), 4) if v else None

    summary = {}
    for o in opts:
        summary[o] = {"pnl_med": med(hist[o]["pnl"]), "worst_fold": worst(hist[o]["pnl"]),
                      "n_med": med(hist[o]["n"]), "stop_rate_med": med(hist[o]["stop"])}
    imp = np.mean(imp_hist, axis=0) if imp_hist else np.zeros(len(FEAT))
    top = sorted(zip(FEAT, imp), key=lambda z: -z[1])[:10]
    result = {"n_pct": N_PCT, "q_alpha": Q_ALPHA, "pstar": PSTAR,
              "calib_cov_med": med(cov_hist), "pinball_med": med(pin_hist),
              "pinball_base_med": med(pin_base_hist), "sl_variants": summary,
              "top_features": [{"feat": f, "imp": round(float(i), 4)} for f, i in top]}
    json.dump(result, open(os.path.join(OUT_DIR, "sl4h_tail_sl_results.json"), "w"), indent=2)
    print("\n===== TAIL-SL n%d q%.2f gate>=%.1f =====" % (N_PCT, Q_ALPHA, PSTAR))
    print("calib_cov(med)=%s (muc tieu ~%.2f) | pinball=%s vs base %s (thap hon=co tin hieu)"
          % (result["calib_cov_med"], Q_ALPHA, result["pinball_med"], result["pinball_base_med"]))
    for o in opts:
        s = summary[o]
        print("  %-9s pnl/keo=%s worst_fold=%s stop_rate=%s n=%s"
              % (o, s["pnl_med"], s["worst_fold"], s["stop_rate_med"], s["n_med"]))
    print("TAIL_SL_RESULT " + json.dumps(result))


if __name__ == "__main__":
    run()
