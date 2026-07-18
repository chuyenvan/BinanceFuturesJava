#!/usr/bin/env python3
# SHORT-EXPORT — dump SHORT predictions per-window (WFO leak-free) cho Java sim doc (nhu sl4h-ev2-export
# cho long, xem file do lam mau preamble+fold). Moi window: train 1 classifier P(HIT_short) tren IS
# (ts < cut-purge), predict tren OOS [cut, cut+3m). Dump: win, ts, symbol, ps, oi_z, oi_delta24h.
# Java sim doc file nay + 1m kline that de sim path short (hard-SL rong + let-dump-run, xem
# orchestrator/kernels_sl4h/short-selector/run_train.py phan ke toan — KHONG lap lai o day, export
# CHI predict xac suat, ke toan/threshold do Java WFO quyet dinh sau).
#
# LABEL SHORT (GIONG short-selector, horizon 4h CO DINH, khong sweep horizon):
#   drop = -maxAdv_4h*100  (do sau giam, duong — short loi khi gia giam)
#   rise =  maxFav_4h*100  (do tang, bat loi short)
#   HIT_short = (drop >= N_PCT) AND (tHitAdv_4h < tHitFav_4h OR tHitFav_4h <= 0)   [path-aware]
#   Dieu kien nBars_4h >= NEED_BARS_4H (=16, luoi 15m) de label du du lieu.
# Tai dung 100% pipeline load Tool1/OI/features cua sl4h-ev2-export.
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
log = logging.getLogger("short-export")


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
    """Label SHORT (horizon 4h, GIONG short-selector): HIT_short path-aware."""
    cols = ["tEpochMs", "symbol", "maxFav_4h", "maxAdv_4h", "tHitFav_4h", "tHitAdv_4h", "nBars_4h"]
    df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    df = df[(df["nBars_4h"] >= NEED_BARS_4H) & df["maxFav_4h"].notna() & df["maxAdv_4h"].notna()].copy()
    drop = (-df["maxAdv_4h"].values * 100.0).astype(np.float32)   # do sau giam (loi short), duong
    rise = (df["maxFav_4h"].values * 100.0).astype(np.float32)    # do tang (bat loi short), duong
    tfav = df["tHitFav_4h"].values.astype(np.float32)
    tadv = df["tHitAdv_4h"].values.astype(np.float32)
    hit_short = ((drop >= float(N_PCT)) & ((tadv < tfav) | (tfav <= 0))).astype(np.int8)
    out = pd.DataFrame({"ts": df["ts"].values, "symbol": df["symbol"].values, "hit_short": hit_short})
    log.info("Label SHORT 4h N%d: %d rows | base_rate(HIT_short)=%.4f | drop p50=%.2f p90=%.2f",
             N_PCT, len(out), float(out.hit_short.mean()),
             float(np.percentile(drop, 50)), float(np.percentile(drop, 90)))
    return out


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
    feats = build_features()
    lb = load_labels()
    ds = feats.merge(lb, on=["symbol", "ts"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Dataset ghep: %d rows | base_rate(hit_short)=%.4f", len(ds), float(ds.hit_short.mean()))
    import xgboost as xgb
    folds = build_folds()
    if SMOKE:
        folds = folds[:1]
    purge = NEED_BARS_4H * GRID_MS

    def mk():
        return xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                                 subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                 objective="binary:logistic", eval_metric="logloss",
                                 n_jobs=-1, tree_method="hist", random_state=SEED)

    parts = []
    for fi, (cut, oos_end) in enumerate(folds):
        tr = ds[ds.ts < cut - purge]
        te = ds[(ds.ts >= cut) & (ds.ts < oos_end)]
        if len(tr) < 5000 or len(te) < 500 or tr["hit_short"].sum() < 50 or (tr["hit_short"] == 0).sum() < 50:
            log.warning("win %d thieu data (tr=%d te=%d) - bo", fi, len(tr), len(te))
            continue
        c = mk(); c.fit(tr[FEAT], tr["hit_short"]); ps = c.predict_proba(te[FEAT])[:, 1]
        out = pd.DataFrame({"win": fi, "ts": te["ts"].values, "symbol": te["symbol"].values,
                            "ps": np.round(ps, 5),
                            "oi_z": np.round(te["oi_z"].values, 5),
                            "oi_delta24h": np.round(te["oi_delta24h"].values, 5)})
        parts.append(out)
        log.info("win %d [%s..%s] OOS=%d rows | ps>=0.5: %d",
                 fi, str(pd.to_datetime(cut, unit="ms").date()),
                 str(pd.to_datetime(oos_end, unit="ms").date()), len(out), int((ps >= 0.5).sum()))

    if not parts:
        raise SystemExit("Khong window nao hop le.")
    allpred = pd.concat(parts, ignore_index=True)
    fp = os.path.join(OUT_DIR, "short_preds.csv.gz")
    allpred.to_csv(fp, index=False, compression="gzip")
    meta = {"n_pct": N_PCT, "rows": int(len(allpred)), "windows": int(allpred.win.nunique()),
            "symbols": int(allpred.symbol.nunique()),
            "ts_min": int(allpred.ts.min()), "ts_max": int(allpred.ts.max()),
            "n_ps_ge_0.5": int((allpred.ps >= 0.5).sum()), "file": os.path.basename(fp),
            "columns": list(allpred.columns)}
    json.dump(meta, open(os.path.join(OUT_DIR, "short_export_meta.json"), "w"), indent=2)
    print("SHORT_EXPORT_RESULT " + json.dumps(meta))
    log.info("XONG -> %s (%d rows)", fp, len(allpred))


if __name__ == "__main__":
    run()
