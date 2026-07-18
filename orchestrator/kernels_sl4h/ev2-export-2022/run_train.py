#!/usr/bin/env python3
# EV2-EXPORT-2022 — re-export EV2 predictions per-window (WFO leak-free), THEM 4 fold 2022
#   (FIRST_OOS=202201 thay vi 202301) de fix lo hong coverage: 4 window WFO 2022 dang bi
#   tinh ZERO_TRADES oan vi EV2 preds truoc gio bat dau tu 2023-01. GPU kernel (device=cuda),
#   khong an 5 CPU slot dang bi grid chiem. Copy 100% tu sl4h-ev2-export/run_train.py.
# Moi window: train clfP6 (P HIT6%) + clfP9 (P HIT9%) tren IS (ts < cut-purge), predict tren OOS
#   [cut, cut+3m). Dump: win, ts, symbol, p6, p9, oi_z, oi_delta24h, f8, f14, f22.
# Prereq cho baseline ladder (B0/REF/+SL/+TR/FULL). Reuse 100% preamble load cua sl4h-ev2-n6.
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

N_PCT = int(os.environ.get("N_PCT", "6"))
NEED_BARS_4H = 16
SEED = int(os.environ.get("SEED", "42"))
GRID_MS = 15 * 60 * 1000
N_ESTIMATORS = int(os.environ.get("N_ESTIMATORS", "400"))

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("ev2-export-2022")


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
FIRST_OOS = os.environ.get("FIRST_OOS", "202201")
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
    cols = ["tEpochMs", "symbol", "maxFav_4h", "nBars_4h"]
    df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    df = df[(df["nBars_4h"] >= NEED_BARS_4H) & df["maxFav_4h"].notna()].copy()
    mf = df["maxFav_4h"].values
    df["hit6"] = (mf >= N_PCT / 100.0).astype(np.int8)
    df["hit9"] = (mf >= 0.09).astype(np.int8)
    return df[["ts", "symbol", "hit6", "hit9"]]


def build_folds():
    cur = pd.Timestamp(f"{FIRST_OOS[:4]}-{FIRST_OOS[4:]}-01")
    last = pd.Timestamp(f"{LAST[:4]}-{LAST[4:]}-01")
    folds = []
    while cur < last:
        nxt = cur + pd.DateOffset(months=OOS_MONTHS)
        folds.append((cur.value // 10**6, min(nxt.value // 10**6, last.value // 10**6)))
        cur = nxt
    return folds


def _mk_gpu(xgb):
    return xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                             objective="binary:logistic", eval_metric="logloss",
                             n_jobs=-1, tree_method="hist", device="cuda", random_state=SEED)


def _mk_cpu(xgb):
    return xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                             objective="binary:logistic", eval_metric="logloss",
                             n_jobs=-1, tree_method="hist", random_state=SEED)


def mk_classifier(xgb):
    """GPU truoc (device=cuda, XGBoost 2.x tren Kaggle GPU); fallback CPU (tree_method=hist)
    neu GPU thieu / xgboost cu khong ho tro device= — de kernel khong chet khi GPU khong san sang."""
    try:
        return _mk_gpu(xgb)
    except TypeError as e:
        log.warning("device=cuda khong duoc ho tro (%s) - fallback CPU tree_method=hist", e)
        return _mk_cpu(xgb)


def run():
    feats = build_features()
    lb = load_labels()
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows", len(ds))
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:1]
    purge = NEED_BARS_4H * GRID_MS

    def mk():
        return mk_classifier(xgb)

    parts = []
    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit6"].sum() < 50 or (tr["hit6"] == 0).sum() < 50:
            log.warning("win %d thieu data (tr=%d te=%d) - bo", fi, len(tr), len(te))
            continue
        try:
            c6 = mk(); c6.fit(tr[FEAT], tr["hit6"]); p6 = c6.predict_proba(te[FEAT])[:, 1]
            c9 = mk(); c9.fit(tr[FEAT], tr["hit9"]); p9 = c9.predict_proba(te[FEAT])[:, 1]
        except Exception as e:
            log.warning("win %d GPU fit loi (%s) - fallback CPU tree_method=hist", fi, e)
            c6 = _mk_cpu(xgb); c6.fit(tr[FEAT], tr["hit6"]); p6 = c6.predict_proba(te[FEAT])[:, 1]
            c9 = _mk_cpu(xgb); c9.fit(tr[FEAT], tr["hit9"]); p9 = c9.predict_proba(te[FEAT])[:, 1]
        out = pd.DataFrame({"win": fi, "ts": te["ts"].values, "symbol": te["symbol"].values,
                            "p6": np.round(p6, 5), "p9": np.round(p9, 5),
                            "oi_z": np.round(te["oi_z"].values, 5),
                            "oi_delta24h": np.round(te["oi_delta24h"].values, 5),
                            "f8": np.round(te["f8"].values, 5),
                            "f14": np.round(te["f14"].values, 5),
                            "f22": np.round(te["f22"].values, 5)})
        parts.append(out)
        log.info("win %d [%s..%s] OOS=%d rows | p6>=0.7: %d",
                 fi, str(pd.to_datetime(cut, unit="ms").date()),
                 str(pd.to_datetime(oos_end, unit="ms").date()), len(out), int((p6 >= 0.7).sum()))

    if not parts:
        raise SystemExit("Khong window nao hop le.")
    allpred = pd.concat(parts, ignore_index=True)
    fp = os.path.join(OUT_DIR, "ev2_preds_n%d_2022.csv.gz" % N_PCT)
    allpred.to_csv(fp, index=False, compression="gzip")
    meta = {"n_pct": N_PCT, "rows": int(len(allpred)), "windows": int(allpred.win.nunique()),
            "symbols": int(allpred.symbol.nunique()),
            "ts_min": int(allpred.ts.min()), "ts_max": int(allpred.ts.max()),
            "n_p6_ge_0.7": int((allpred.p6 >= 0.7).sum()), "file": os.path.basename(fp),
            "first_oos": FIRST_OOS, "columns": list(allpred.columns)}
    json.dump(meta, open(os.path.join(OUT_DIR, "ev2_export_2022_meta.json"), "w"), indent=2)
    print("EV2_EXPORT_2022_RESULT " + json.dumps(meta))
    log.info("XONG -> %s (%d rows)", fp, len(allpred))


if __name__ == "__main__":
    run()
