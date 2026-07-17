#!/usr/bin/env python3
# EDGE-ANATOMY — n=6, 4h, gate p6>=0.7 CO DINH. Mo xe "canh" cua EV2 theo thoi gian & feature (vong 3b).
# BOI CANH: sl4h-ev2 (n6) gate p6>=0.7 -> +1.74%/keo median. Median che dau bat on: fold nao AM?
#   canh den tu regime nao? feature nao dan dat? -> quyet dinh do ben cua edge truoc khi len size.
# THIET KE: tai dung pipeline load/fold/purge/XGB cua sl4h-ev2. clfP6=P(maxFav_4h>=6% & nBars_4h>=16).
#   Moi fold (14 quy): gate p6>=0.7 -> PnL/keo, n_keo, hit6. Ke toan SL-cung: HIT->+6 ; MISS->retEnd_4h%.
# PHAN TICH: (1) in du 14 dong per-fold; (2) gom regime tho: 2023H1/2023H2/2024/2025/2026 -> trung binh nhom;
#   (3) XGB feature_importances_ top-15 (map index f0..f39 / 5 OI) trung binh qua fold; (4) dem fold AM.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

# ===== HANG SO (pre-register — KHONG doi sau khi nhin so) =====
N_PCT = 6
NEED_BARS_4H = 16                            # nBars_4h >= 16 (cua so 4h)
GATE_PSTAR = 0.7                             # gate p6>=0.7 CO DINH
GRID_MS = 15 * 60 * 1000

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — index 0..39=f, 40..44=OI
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("edge-anatomy")


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
    df = pd.read_csv(LABEL_CSV, usecols=["tEpochMs", "symbol", "maxFav_4h", "retEnd_4h", "nBars_4h"],
                     on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    df = df[(df["nBars_4h"] >= NEED_BARS_4H) & df["maxFav_4h"].notna() & df["retEnd_4h"].notna()].copy()
    df["hit6"] = ((df["maxFav_4h"].values >= 0.06) & (df["nBars_4h"].values >= NEED_BARS_4H)).astype(np.int8)
    df["ret_pct"] = (df["retEnd_4h"].values * 100.0).astype(np.float32)
    log.info("Label n6: %d/%d rows | hit6=%.4f", len(df), n0, float(df.hit6.mean()))
    return df[["ts", "symbol", "hit6", "ret_pct"]]


def regime_of(dt):
    """Gom regime tho tu ngay oos_from."""
    y, m = dt.year, dt.month
    if y == 2023:
        return "2023H1" if m <= 6 else "2023H2"
    return str(y)


def fit_predict(xgb, tr, te):
    """clfP6 -> p6, auc, feature_importances_ (len 45)."""
    from sklearn.metrics import roc_auc_score
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            objective="binary:logistic", eval_metric="logloss",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(tr[FEAT], tr["hit6"])
    p6 = clf.predict_proba(te[FEAT])[:, 1]
    try:
        auc = float(roc_auc_score(te["hit6"].values, p6)) if te["hit6"].nunique() > 1 else None
    except Exception:
        auc = None
    fi = np.asarray(clf.feature_importances_, dtype=float)
    return p6, auc, fi


def run():
    feats = build_features()
    lb = load_labels()
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows | hit6=%.4f", len(ds), float(ds.hit6.mean()))
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:1]
        log.info("SMOKE: chi chay fold 0")
    log.info("EDGE-ANATOMY n6: %d fold expanding OOS=%dm | gate p6>=%.1f", len(folds), OOS_MONTHS,
             GATE_PSTAR)

    purge = NEED_BARS_4H * GRID_MS
    per_fold = []
    imp_acc = np.zeros(len(FEAT), dtype=float)
    imp_n = 0
    auc_hist = []

    for fi_idx, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit6"].sum() < 50 or (tr["hit6"] == 0).sum() < 50:
            log.warning("fold %d thieu data (tr=%d te=%d hit6=%d) - bo", fi_idx, len(tr), len(te),
                        int(tr["hit6"].sum()))
            continue
        p6, auc, imp = fit_predict(xgb, tr, te)
        if auc is not None:
            auc_hist.append(auc)
        imp_acc += imp
        imp_n += 1
        hit6 = te["hit6"].values
        pnl = np.where(hit6 == 1, float(N_PCT), te["ret_pct"].values)
        idx = np.where(p6 >= GATE_PSTAR)[0]
        n = int(len(idx))
        dt_from = pd.to_datetime(cut, unit="ms")
        label = str(dt_from.date())
        rec = {"fold": fi_idx, "label": label, "regime": regime_of(dt_from),
               "n": n, "pnl": round(float(pnl[idx].mean()), 4) if n else None,
               "hit6": round(float(hit6[idx].mean()), 4) if n else None,
               "auc": round(auc, 4) if auc else None}
        per_fold.append(rec)
        log.info("fold %2d [%s] regime=%s n=%s pnl/keo=%s hit6=%s AUC=%s", fi_idx, label,
                 rec["regime"], n, rec["pnl"], rec["hit6"], rec["auc"])

    if not per_fold:
        raise SystemExit("Khong fold nao hop le — kiem alignment ts/symbol.")
    imp_mean = (imp_acc / imp_n) if imp_n else imp_acc
    finalize(per_fold, imp_mean, auc_hist)


def finalize(per_fold, imp_mean, auc_hist):
    # ---- (1) in du cac dong per-fold ----
    print("\n===== EDGE-ANATOMY per-fold (gate p6>=%.1f) — n6 4h =====" % GATE_PSTAR)
    print("fold  oos_from    regime  n_keo   pnl/keo  hit6    AUC")
    for r in per_fold:
        print("%4d  %-10s  %-6s  %-6s  %-8s %-6s  %s" % (
            r["fold"], r["label"], r["regime"], r["n"], r["pnl"], r["hit6"], r["auc"]))
    # ---- (2) gom regime tho ----
    regimes = {}
    for r in per_fold:
        regimes.setdefault(r["regime"], []).append(r)
    regime_summary = {}
    print("--- regime (trung binh nhom) ---")
    for rg in sorted(regimes):
        grp = regimes[rg]
        rs = {"n_folds": len(grp), "pnl_mean": _med([g["pnl"] for g in grp]),
              "n_keo_mean": _med([g["n"] for g in grp]), "hit6_mean": _med([g["hit6"] for g in grp])}
        regime_summary[rg] = rs
        print("  %-7s folds=%d pnl/keo(med)=%s n_keo(med)=%s hit6=%s" % (
            rg, rs["n_folds"], rs["pnl_mean"], rs["n_keo_mean"], rs["hit6_mean"]))
    # ---- (3) feature importance top-15 (map index -> ten) ----
    order = np.argsort(imp_mean)[::-1][:15]
    top_features = [{"feat": FEAT[i], "idx": int(i), "imp": round(float(imp_mean[i]), 5)}
                    for i in order]
    print("--- top-15 feature_importances_ (trung binh qua fold) ---")
    for t in top_features:
        print("  %-14s idx=%2d imp=%.5f" % (t["feat"], t["idx"], t["imp"]))
    # ---- (4) dem fold AM ----
    pnls = [(r["label"], r["pnl"]) for r in per_fold if r["pnl"] is not None]
    folds_neg = sum(1 for _, p in pnls if p < 0)
    worst = min(pnls, key=lambda z: z[1]) if pnls else (None, None)
    print("FOLDS_NEG=%d / %d | worst_fold=%s pnl=%s | AUC_med=%s" % (
        folds_neg, len(pnls), worst[0], worst[1], _med(auc_hist)))

    result = {"n_pct": N_PCT, "gate_pstar": GATE_PSTAR, "auc_med": _med(auc_hist),
              "n_folds": len(per_fold), "folds_neg": folds_neg,
              "worst_fold": {"label": worst[0], "pnl": worst[1]},
              "regime_summary": regime_summary,
              "top_features": [{"feat": t["feat"], "imp": t["imp"]} for t in top_features]}
    full = {"n_pct": N_PCT, "gate_pstar": GATE_PSTAR, "per_fold": per_fold,
            "regime_summary": regime_summary, "top_features": top_features,
            "folds_neg": folds_neg, "auc_med": _med(auc_hist)}
    json.dump(full, open(os.path.join(OUT_DIR, "edge_anatomy_results.json"), "w"), indent=2)
    while len(json.dumps(result)) >= 2000 and len(result["top_features"]) > 5:
        result["top_features"].pop()
    print("ANATOMY_RESULT " + json.dumps(result))
    log.info("XONG -> %s/edge_anatomy_results.json", OUT_DIR)


if __name__ == "__main__":
    run()
