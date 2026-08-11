#!/usr/bin/env python3
# SHORT-CROWD-EXPORT — dump SHORT-CROWDING predictions per-window (WFO leak-free) de chay
#   WFO real-path (thay proxy funding_label.csv). CONFIG WINNER da PASS o screen short-crowding
#   (net_chop +3.47, tpq>=30): target=9% drop, horizon=24h, stop=30% (stop ap dung O PHIA WFO/Java,
#   KHONG trong script nay), gate = ls_toptrader top-10%% (q0.90) AND ps cao.
#   Copy 100%% preamble load (tool1+OI merge) tu sl4h-ev2-export/run_train.py; GPU device=cuda +
#   fallback CPU giong ev2-export-2022/run_train.py (khong an CPU slot dang bi grid khac chiem).
#
# Moi window: train 1 classifier clfP(HIT_short_9%%_24h) tren IS (ts < cut-purge), predict tren OOS
#   [cut, cut+3m). HIT_short = drop>=9%% trong 24h, drop=-maxAdv_24h*100 (do sau giam, duong),
#   dieu kien nBars_24h>=96 (du bar cho horizon 24h tren grid 15m).
# Dump: win, ts, symbol, ps(=P(HIT_short_9%%_24h)), ls_toptrader, ls_global, oi_z — de Java loc
#   crowding-gate (ls_toptrader >= quantile cross-sectional) luc convert/WFO, KHONG loc o day
#   (giu raw predictions, gate ap dung downstream de con doi threshold ma khong train lai).
#
# KHONG deploy, KHONG dung WFO Oracle o day (chi export preds an toan cho Java doc + tu chay WFO
#   that o pipeline khac). KHONG git commit (theo yeu cau task).
import os, glob, gzip, json, logging
import numpy as np
import pandas as pd

TARGET_DROP_PCT = float(os.environ.get("TARGET_DROP_PCT", "9"))   # t=9%% (config winner)
HORIZON = os.environ.get("HORIZON", "24h")                        # horizon=24h (config winner)
NEED_BARS_24H = int(os.environ.get("NEED_BARS_24H", "96"))        # 24h / 15m grid = 96 bar
SEED = int(os.environ.get("SEED", "42"))
GRID_MS = 15 * 60 * 1000
N_ESTIMATORS = int(os.environ.get("N_ESTIMATORS", "400"))

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES        # 45 feat — KHOP train_meta selector
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("short-crowd-export")


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
FIRST_OOS = os.environ.get("FIRST_OOS", "202201")     # 2022 coverage (giong ev2-export-2022)
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
    missing_ls = [c for c in ("ls_toptrader", "ls_global") if c not in merged.columns]
    assert not missing_ls, f"THIEU cot crowding trong OI feature: {missing_ls}"
    log.info("Features ghep: %d rows | n_sym=%d", len(merged), merged.symbol.nunique())
    return merged.sort_values("ts").reset_index(drop=True)


def check_24h_columns():
    """Kiem tra funding_label.csv co du cot 24h TRUOC KHI train — bao NGAY neu thieu (theo yeu cau task)."""
    head = pd.read_csv(LABEL_CSV, nrows=1)
    cols = list(head.columns)
    need = [f"maxAdv_{HORIZON}", f"nBars_{HORIZON}"]
    missing = [c for c in need if c not in cols]
    if missing:
        log.error("THIEU COT %s TRONG funding_label.csv: %s | cot co san: %s", HORIZON, missing, cols)
        raise SystemExit(f"NO_{HORIZON.upper()}_COLUMNS: {missing}")
    log.info("funding_label.csv columns OK: co %s", need)
    return cols


def load_labels():
    ca, cn = f"maxAdv_{HORIZON}", f"nBars_{HORIZON}"
    cols = ["tEpochMs", "symbol", ca, cn]
    df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    df = df[(df[cn] >= NEED_BARS_24H) & df[ca].notna()].copy()
    dropp = (-df[ca].values * 100.0).astype(np.float32)          # do sau giam (loi short), duong
    df["hit_short"] = (dropp >= TARGET_DROP_PCT).astype(np.int8)
    log.info("Label HIT_short_%.0f%%_%s: base_rate=%.4f (n=%d, thieu-bar/NaN da loc)",
              TARGET_DROP_PCT, HORIZON, float(df["hit_short"].mean()), len(df))
    return df[["ts", "symbol", "hit_short"]]


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
    check_24h_columns()
    feats = build_features()
    lb = load_labels()
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    base_rate = float(ds["hit_short"].mean())
    log.info("Dataset ghep: %d rows | base_rate hit_short=%.4f", len(ds), base_rate)
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:1]
    purge = NEED_BARS_24H * GRID_MS

    def mk():
        return mk_classifier(xgb)

    parts = []
    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit_short"].sum() < 50 or (tr["hit_short"] == 0).sum() < 50:
            log.warning("win %d thieu data (tr=%d te=%d) - bo", fi, len(tr), len(te))
            continue
        try:
            clf = mk(); clf.fit(tr[FEAT], tr["hit_short"]); ps = clf.predict_proba(te[FEAT])[:, 1]
        except Exception as e:
            log.warning("win %d GPU fit loi (%s) - fallback CPU tree_method=hist", fi, e)
            clf = _mk_cpu(xgb); clf.fit(tr[FEAT], tr["hit_short"]); ps = clf.predict_proba(te[FEAT])[:, 1]
        out = pd.DataFrame({"win": fi, "ts": te["ts"].values, "symbol": te["symbol"].values,
                            "ps": np.round(ps, 5),
                            "ls_toptrader": np.round(te["ls_toptrader"].values, 5),
                            "ls_global": np.round(te["ls_global"].values, 5),
                            "oi_z": np.round(te["oi_z"].values, 5)})
        parts.append(out)
        log.info("win %d [%s..%s] OOS=%d rows | ps>=0.5: %d",
                 fi, str(pd.to_datetime(cut, unit="ms").date()),
                 str(pd.to_datetime(oos_end, unit="ms").date()), len(out), int((ps >= 0.5).sum()))

    if not parts:
        raise SystemExit("Khong window nao hop le.")
    allpred = pd.concat(parts, ignore_index=True)
    fp = os.path.join(OUT_DIR, "short_crowd_preds.csv.gz")
    allpred.to_csv(fp, index=False, compression="gzip")
    meta = {"rows": int(len(allpred)), "windows": int(allpred.win.nunique()),
            "symbols": int(allpred.symbol.nunique()), "base_rate": round(base_rate, 4),
            "n_ps_ge_0.5": int((allpred.ps >= 0.5).sum()),
            "ts_min": int(allpred.ts.min()), "ts_max": int(allpred.ts.max()),
            "target_drop_pct": TARGET_DROP_PCT, "horizon": HORIZON, "first_oos": FIRST_OOS,
            "file": os.path.basename(fp), "columns": list(allpred.columns)}
    json.dump(meta, open(os.path.join(OUT_DIR, "short_crowd_export_meta.json"), "w"), indent=2)
    print("SHORT_CROWD_EXPORT_RESULT " + json.dumps(meta))
    log.info("XONG -> %s (%d rows)", fp, len(allpred))


if __name__ == "__main__":
    run()
