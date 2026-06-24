#!/usr/bin/env python3
# TASK-108 WFO selector kernel — header resolve path Kaggle + nhúng train_funding_selector_wfo.py.
# Kaggle tự giải nén .gz -> .bin; mount /kaggle/input/datasets/<user>/<slug>/ -> dùng glob đệ quy.
# Chạy SMOKE trước (SMOKE=1, 1 fold) để kiểm luồng, rồi bản full (SMOKE=0). SAVE_LAST_MODEL=1 lưu model fold cuối.
import os, glob


def find1(p):
    m = sorted(glob.glob(p, recursive=True))
    assert m, f"KHONG TIM THAY: {p}"
    return m[0]


os.environ["TOOL1_GLOB"] = "/kaggle/input/**/ff_*.bin"
os.environ["OI_FILE"] = find1("/kaggle/input/**/oi_percoin_full.bin")
os.environ["LABEL_CSV"] = find1("/kaggle/input/**/funding_label.csv")
os.environ["MAP_CSV"] = find1("/kaggle/input/**/symbol_map.csv")
os.environ["OUT_DIR"] = "/kaggle/working"
os.environ.setdefault("OOS_MONTHS", "3")
os.environ.setdefault("FIRST_OOS", "202301")
os.environ.setdefault("LAST", "202606")
os.environ.setdefault("SMOKE", "0")  # SMOKE verified fold0 (LIFT 4h=2.648 khop README v1) -> FULL 14 fold
os.environ.setdefault("SAVE_LAST_MODEL", "1")
print("TOOL1 files:", len(glob.glob(os.environ["TOOL1_GLOB"], recursive=True)))
print("OI   :", os.environ["OI_FILE"])
print("LABEL:", os.environ["LABEL_CSV"])
print("MAP  :", os.environ["MAP_CSV"])
print("SMOKE:", os.environ["SMOKE"], "| SAVE_LAST_MODEL:", os.environ["SAVE_LAST_MODEL"])

# ===== WFO selector body (TASK-108, train_funding_selector_wfo.py) =====
import gzip, json, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wfo_sel")

H_STEPS = {"4h": 16, "12h": 48, "24h": 96, "72h": 288}
HORIZONS = ["4h", "12h", "24h", "72h"]
WIN = 0.06
GRID_MS = 15 * 60 * 1000
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES

TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])

TOOL1_GLOB = os.environ["TOOL1_GLOB"]
OI_FILE = os.environ["OI_FILE"]
LABEL_CSV = os.environ["LABEL_CSV"]
MAP_CSV = os.environ["MAP_CSV"]
OI_TOL_MS = int(os.environ.get("OI_TOL_MS", str(2 * 60 * 60 * 1000)))
OOS_MONTHS = int(os.environ.get("OOS_MONTHS", "3"))
FIRST_OOS = os.environ.get("FIRST_OOS", "202301")
LAST = os.environ.get("LAST", "202606")
OUT_DIR = os.environ.get("OUT_DIR", ".")
SMOKE = os.environ.get("SMOKE", "0") == "1"
SAVE_LAST_MODEL = os.environ.get("SAVE_LAST_MODEL", "0") == "1"
SEED = int(os.environ.get("SEED", "42"))
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
    parts = []
    for fp in files:
        parts.append(_read(fp, TOOL1_DT, 170, grid=True))
    a = np.concatenate(parts)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(40):
        df[f"f{j}"] = F[:, j]
    log.info("Tool1 (15m grid): %d rows | %d symId | ts[%s..%s]", len(df), df.symId.nunique(),
             pd.to_datetime(df.ts.min(), unit="ms"), pd.to_datetime(df.ts.max(), unit="ms"))
    return df.sort_values("ts").reset_index(drop=True)


def load_oi():
    files = sorted(glob.glob(OI_FILE, recursive=True)) if any(c in OI_FILE for c in "*?[") else [OI_FILE]
    a = _read(files[0], OI_DT, 30)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    O = np.asarray(a["oi"], dtype=np.float32)
    for j, nm in enumerate(OI_NAMES):
        df[nm] = O[:, j]
    log.info("OI: %d rows | %d symId", len(df), df.symId.nunique())
    return df.sort_values("ts").reset_index(drop=True)


def load_labels():
    cols = ["tEpochMs", "symbol"] + [f"maxFav_{H}" for H in HORIZONS] + [f"nBars_{H}" for H in HORIZONS]
    df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip")
    df = df.rename(columns={"tEpochMs": "ts"})
    for H in HORIZONS:
        need = H_STEPS[H]
        ok = (df[f"nBars_{H}"] >= need) & df[f"maxFav_{H}"].notna()
        df[f"y_{H}"] = np.where(ok, (df[f"maxFav_{H}"] >= WIN).astype(np.float32), np.nan)
        log.info("Label %s: %d hop le | base_rate=%.4f", H, int(ok.sum()), df.loc[ok, f"y_{H}"].mean())
    return df[["ts", "symbol"] + [f"y_{H}" for H in HORIZONS]]


def build_dataset(t, o, lb, mp):
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    ds = merged.merge(lb, on=["symbol", "ts"], how="inner")
    log.info("Dataset ghep: %d rows | n_sym=%d | base_rate per-H: %s", len(ds), ds.symbol.nunique(),
             {H: round(float(ds[f"y_{H}"].mean()), 4) for H in HORIZONS})
    return ds.sort_values("ts").reset_index(drop=True)


def evaluate(score, y):
    import scipy.stats as st
    m = ~np.isnan(y)
    y = np.asarray(y)[m]; score = np.asarray(score, dtype=float)[m]
    if len(y) < 200 or y.sum() < 10:
        return None
    base = y.mean(); n = len(y); k = max(100, n // 10)
    idx = np.argsort(-score)[:k]
    hit = y[idx].mean()
    lift = hit / base if base > 0 else float("nan")
    ic, _ = st.spearmanr(score, y)
    return {"N": int(n), "base_rate": round(float(base), 4), "N_top": int(k),
            "hit_top": round(float(hit), 4), "LIFT": round(float(lift), 3), "rankIC": round(float(ic), 4)}


def build_folds():
    cur = pd.Timestamp(f"{FIRST_OOS[:4]}-{FIRST_OOS[4:]}-01")
    last = pd.Timestamp(f"{LAST[:4]}-{LAST[4:]}-01")
    folds = []
    while cur < last:
        nxt = cur + pd.DateOffset(months=OOS_MONTHS)
        folds.append((cur.value // 10**6, min(nxt.value // 10**6, last.value // 10**6)))
        cur = nxt
    return folds


def run():
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)
    lb = load_labels()
    ds = build_dataset(t, o, lb, mp)
    del t, o, lb
    if len(ds) == 0:
        raise SystemExit("Dataset rong sau merge - kiem alignment ts/symbol.")

    import xgboost as xgb
    folds = build_folds()
    log.info("WFO selector: %d fold expanding OOS=%dm, %d horizon", len(folds), OOS_MONTHS, len(HORIZONS))
    if SMOKE:
        folds = folds[:1]
        log.info("SMOKE: chi chay fold 0")

    results = {H: [] for H in HORIZONS}
    last_models = {}
    for fi, (cut, oos_end) in enumerate(folds):
        purge = {H: H_STEPS[H] * GRID_MS for H in HORIZONS}
        oos = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(oos) < 500:
            log.warning("fold %d OOS qua it (%d) - bo", fi, len(oos))
            continue
        for H in HORIZONS:
            ycol = f"y_{H}"
            tr = ds[ds.ts < cut - purge[H]]
            tr = tr[tr[ycol].notna()]
            te = oos[oos[ycol].notna()]
            if len(tr) < 5000 or len(te) < 200 or tr[ycol].sum() < 50:
                log.warning("fold %d H=%s thieu data (tr=%d te=%d) - bo", fi, H, len(tr), len(te))
                continue
            pos = tr[ycol].mean()
            clf = xgb.XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05,
                                    subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                    scale_pos_weight=(1 - pos) / max(pos, 1e-6),
                                    eval_metric="auc", n_jobs=-1, tree_method="hist", random_state=SEED)
            clf.fit(tr[FEAT], tr[ycol])
            pwin = clf.predict_proba(te[FEAT])[:, 1]
            ev = evaluate(pwin, te[ycol].values)
            if ev:
                ev["fold"] = fi
                ev["oos_from"] = str(pd.to_datetime(cut, unit="ms").date())
                ev["oos_to"] = str(pd.to_datetime(oos_end, unit="ms").date())
                ev["n_train"] = int(len(tr))
                results[H].append(ev)
                log.info("fold %d H=%s [%s..%s] LIFT=%.3f rankIC=%.4f base=%.3f N=%d ntr=%d",
                         fi, H, ev["oos_from"], ev["oos_to"], ev["LIFT"], ev["rankIC"],
                         ev["base_rate"], ev["N"], len(tr))
            if SAVE_LAST_MODEL:
                last_models[H] = clf

    summary = {}
    for H in HORIZONS:
        r = results[H]
        if not r:
            summary[H] = {"n_fold": 0}
            continue
        lifts = [x["LIFT"] for x in r]
        ics = [x["rankIC"] for x in r]
        summary[H] = {
            "n_fold": len(r),
            "LIFT_median": round(float(np.median(lifts)), 3),
            "LIFT_min": round(float(np.min(lifts)), 3),
            "LIFT_max": round(float(np.max(lifts)), 3),
            "LIFT_std": round(float(np.std(lifts)), 3),
            "pct_fold_LIFT_gt_1": round(float(np.mean([l > 1.0 for l in lifts])), 3),
            "rankIC_median": round(float(np.median(ics)), 4),
            "rankIC_min": round(float(np.min(ics)), 4),
            "rankIC_std": round(float(np.std(ics)), 4),
            "pct_fold_IC_gt_0": round(float(np.mean([c > 0 for c in ics])), 3),
        }
        log.info("=== H=%s ON DINH: %d fold | LIFT med=%.3f [%.3f,%.3f] std=%.3f | rankIC med=%.4f std=%.4f | pctfold IC>0=%.2f",
                 H, summary[H]["n_fold"], summary[H]["LIFT_median"], summary[H]["LIFT_min"],
                 summary[H]["LIFT_max"], summary[H]["LIFT_std"], summary[H]["rankIC_median"],
                 summary[H]["rankIC_std"], summary[H]["pct_fold_IC_gt_0"])

    out = {"oos_months": OOS_MONTHS, "first_oos": FIRST_OOS, "last": LAST, "seed": SEED,
           "n_folds_built": len(folds), "summary": summary, "per_fold": results}
    json.dump(out, open(os.path.join(OUT_DIR, "wfo_selector_results.json"), "w"), indent=2)
    log.info("XONG -> %s/wfo_selector_results.json", OUT_DIR)

    if SAVE_LAST_MODEL:
        for H, clf in last_models.items():
            clf.save_model(os.path.join(OUT_DIR, f"model_wfo_last_{H}.ubj"))
        log.info("da luu %d model fold cuoi", len(last_models))


run()
