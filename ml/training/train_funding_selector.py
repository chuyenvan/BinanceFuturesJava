#!/usr/bin/env python3
"""
TASK-039 - Funding SELECTOR train.

Ghep 3 nguon -> train XGBoost du doan P(cham +6% trong horizon H), do tren OOS.
  Tool1 (40 feat) : ff_*.bin.gz   170B = >q h 40f  (ts_ms, symId, f0..f39)  nhip 1m -> LOC 15m grid
  OI    (5 feat)  : oi_percoin_*.bin.gz 30B = >q h 5f (ts_ms, symId, oi0..oi4)
  Label           : funding_label.csv 27 cot (tEpochMs,tDate,symbol + maxFav/maxAdv/tHitFav/tHitAdv/retEnd/nBars x {4h,12h,24h,72h})
  Map             : symId,symbol

Env:
  TOOL1_GLOB OI_FILE LABEL_CSV MAP_CSV  (bat buoc)
  HORIZON = 4h|12h|24h|72h  (mac dinh 24h) - knob lap K config
  OUT_DIR (mac dinh .)  SMOKE=1 (chi load+merge+barrier+shape, khong train)
  OI_TOL_MS (2h)  LBL_TOL_MS (0 = exact join symbol+ts)

Nguyen tac (ADR-0011): KHONG scale (live khong co scaler); split theo thoi gian,
KHONG shuffle, purge = horizon; KHOA convention pred[0]=P(fail)=1-P(win), rank uu tien P(win) cao.
Acceptance pre-register: LIFT>=1.20, N_top>=100, z>=2, |t_IC|>=2 (OOS 12 thang) VA beat baseline
(best-single-feature chon tren VAL, do tren TEST). Khong dat -> bo ML.
"""
import os, gzip, glob, json, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("fselector")

H_STEPS = {"4h": 16, "12h": 48, "24h": 96, "72h": 288}   # so buoc-15m moi horizon
WIN = 0.06
GRID_MS = 15 * 60 * 1000

HORIZON = os.environ.get("HORIZON", "24h")
assert HORIZON in H_STEPS, f"HORIZON khong hop le: {HORIZON}"
SMOKE = os.environ.get("SMOKE", "0") == "1"
OUT_DIR = os.environ.get("OUT_DIR", ".")
os.makedirs(OUT_DIR, exist_ok=True)
TOOL1_GLOB = os.environ["TOOL1_GLOB"]
OI_FILE = os.environ["OI_FILE"]
LABEL_CSV = os.environ["LABEL_CSV"]
MAP_CSV = os.environ["MAP_CSV"]
OI_TOL_MS = int(os.environ.get("OI_TOL_MS", str(2 * 60 * 60 * 1000)))
LBL_TOL_MS = int(os.environ.get("LBL_TOL_MS", "0"))
SEED = int(os.environ.get("SEED", "42"))                       # validate: doi seed xem ket qua co lap lai
REPORT_QUARTERS = os.environ.get("REPORT_QUARTERS", "0") == "1" # validate: do LIFT/IC theo tung quy (on dinh regime)
# TASK-130: knob GPU + so cay. Mac dinh cpu/400 = HANH VI CU KHONG DOI (additive). XGB_DEVICE=cuda -> train tren GPU.
XGB_DEVICE = os.environ.get("XGB_DEVICE", "cpu")               # cpu | cuda | cuda:0 ... (xgboost>=2 device=; xgboost<2 fallback gpu_hist)
N_ESTIMATORS = int(os.environ.get("N_ESTIMATORS", "400"))      # smoke ha thap (vd 60) de chay nhanh; full giu 400

TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # itemsize 170
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # itemsize 30
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]


def read_bin(path_or_glob, dt, item, grid_filter=False):
    is_glob = any(c in path_or_glob for c in "*?[")
    files = sorted(glob.glob(path_or_glob, recursive=True)) if is_glob else [path_or_glob]
    assert files, f"khong tim thay file: {path_or_glob}"
    parts = []
    for fp in files:
        raw = open(fp, "rb").read()
        if fp.endswith(".gz"):           # local: .gz; Kaggle tu giai nen -> .bin raw
            raw = gzip.decompress(raw)
        assert len(raw) % item == 0, f"{fp}: do dai {len(raw)} khong chia het {item}"
        a = np.frombuffer(raw, dtype=dt)
        if grid_filter:
            a = a[(a["ts"] % GRID_MS) == 0]
        parts.append(a)
    return np.concatenate(parts) if len(parts) > 1 else parts[0]


def tool1_df():
    a = read_bin(TOOL1_GLOB, TOOL1_DT, 170, grid_filter=True)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(40):
        df[f"f{j}"] = F[:, j]
    log.info("Tool1 (15m grid): %d rows | %d symId | ts[%s .. %s]", len(df), df.symId.nunique(),
             pd.to_datetime(df.ts.min(), unit="ms"), pd.to_datetime(df.ts.max(), unit="ms"))
    return df


def oi_df():
    a = read_bin(OI_FILE, OI_DT, 30, grid_filter=False)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    O = np.asarray(a["oi"], dtype=np.float32)
    for j, nm in enumerate(OI_NAMES):
        df[nm] = O[:, j]
    log.info("OI: %d rows | %d symId | NaN/feat: %s", len(df), df.symId.nunique(),
             df[OI_NAMES].isna().mean().round(4).to_dict())
    return df


def label_df():
    fav, nb = f"maxFav_{HORIZON}", f"nBars_{HORIZON}"
    df = pd.read_csv(LABEL_CSV, usecols=["tEpochMs", "symbol", fav, nb], on_bad_lines="skip")
    df = df.rename(columns={"tEpochMs": "ts", fav: "maxFav", nb: "nBars"})
    need = H_STEPS[HORIZON]
    n0 = len(df)
    df = df[(df["nBars"] >= need) & df["maxFav"].notna()].copy()
    df["y"] = (df["maxFav"] >= WIN).astype(np.int8)
    log.info("Label H=%s: %d/%d rows du nBars>=%d | base_rate(+6%%)=%.4f",
             HORIZON, len(df), n0, need, df["y"].mean())
    return df[["ts", "symbol", "y"]]


def build_dataset():
    t = tool1_df().sort_values("ts").reset_index(drop=True)
    o = oi_df().sort_values("ts").reset_index(drop=True)
    m = pd.read_csv(MAP_CSV)  # symId,symbol
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(m, on="symId", how="left")
    nmiss = merged["symbol"].isna().sum()
    if nmiss:
        log.warning("%d rows khong map duoc symId->symbol (bo)", nmiss)
    merged = merged.dropna(subset=["symbol"])
    lb = label_df()
    if LBL_TOL_MS > 0:
        merged = merged.sort_values(["symbol", "ts"])
        lb = lb.sort_values(["symbol", "ts"])
        ds = pd.merge_asof(merged, lb, on="ts", by="symbol", direction="backward", tolerance=LBL_TOL_MS)
        ds = ds.dropna(subset=["y"])
    else:
        ds = merged.merge(lb, on=["symbol", "ts"], how="inner")
    ds["y"] = ds["y"].astype(np.int8)
    feat = [f"f{j}" for j in range(40)] + OI_NAMES
    log.info("Dataset ghep: %d rows | y=1(+6%%)=%.4f | n_feat=%d | n_sym=%d",
             len(ds), ds["y"].mean() if len(ds) else float("nan"), len(feat), ds.symbol.nunique())
    return ds.sort_values("ts").reset_index(drop=True), feat


def evaluate(name, score, y):
    import scipy.stats as st
    y = np.asarray(y)
    score = np.asarray(score, dtype=float)
    base = y.mean()
    n = len(y)
    k = max(100, n // 10)
    idx = np.argsort(-score)[:k]
    hit = y[idx].mean()
    lift = hit / base if base > 0 else float("nan")
    se = np.sqrt(base * (1 - base) / k)
    z = (hit - base) / se if se > 0 else float("nan")
    ic, _ = st.spearmanr(score, y)
    t_ic = ic * np.sqrt((n - 2) / max(1e-9, 1 - ic * ic)) if not np.isnan(ic) else float("nan")
    return {"name": name, "base_rate": float(base), "N_top": int(k), "hit_top": float(hit),
            "LIFT": float(lift), "z": float(z), "rankIC": float(ic), "t_IC": float(t_ic)}


def time_split(ds):
    MO = 30 * 24 * 3600 * 1000
    tmax = ds.ts.max()
    test_start = tmax - 12 * MO
    val_start = test_start - 6 * MO
    purge = H_STEPS[HORIZON] * GRID_MS
    tr = ds[ds.ts < val_start - purge]
    va = ds[(ds.ts >= val_start) & (ds.ts < test_start - purge)]
    te = ds[ds.ts >= test_start]
    return tr, va, te


def run_one(horizon):
    global HORIZON
    HORIZON = horizon
    log.info("########## RUN horizon=%s ##########", HORIZON)
    ds, feat = build_dataset()
    if len(ds) == 0:
        raise SystemExit("Dataset rong sau merge - kiem alignment ts/symbol (xem smoke).")
    if SMOKE:
        out = {"smoke": True, "rows": int(len(ds)), "base_rate": float(ds.y.mean()),
               "ts_min": str(pd.to_datetime(ds.ts.min(), unit="ms")),
               "ts_max": str(pd.to_datetime(ds.ts.max(), unit="ms")),
               "nan_per_feat": ds[feat].isna().mean().round(4).to_dict(),
               "n_symbol": int(ds.symbol.nunique())}
        json.dump(out, open(os.path.join(OUT_DIR, "smoke.json"), "w"), indent=2)
        log.info("SMOKE OK -> %s", out)
        return

    import xgboost as xgb
    tr, va, te = time_split(ds)
    log.info("split tr/va/te = %d/%d/%d", len(tr), len(va), len(te))
    assert len(tr) and len(va) and len(te), "split rong - du lieu khong du 18 thang"
    assert tr.ts.max() < va.ts.min() and va.ts.max() < te.ts.min(), "LEAK: split khong tang theo ts"
    Xtr, ytr = tr[feat], tr.y
    Xva, yva = va[feat], va.y
    Xte, yte = te[feat], te.y
    pos = ytr.mean()
    # TASK-130: dung device (xgboost>=2) hoac gpu_hist (xgboost<2) khi XGB_DEVICE=cuda; CPU giu tree_method=hist nhu cu.
    params = dict(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                  subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                  scale_pos_weight=(1 - pos) / max(pos, 1e-6),
                  eval_metric="auc", n_jobs=-1, random_state=SEED)
    xgb_major = int(xgb.__version__.split(".")[0])
    if XGB_DEVICE.startswith("cuda"):
        if xgb_major >= 2:
            params.update(tree_method="hist", device=XGB_DEVICE)
        else:
            params.update(tree_method="gpu_hist")   # xgboost<2 API cu
    else:
        params.update(tree_method="hist")
    log.info("XGBoost %s | device=%s | n_estimators=%d | params tree_method=%s",
             xgb.__version__, XGB_DEVICE, N_ESTIMATORS, params.get("tree_method"))
    clf = xgb.XGBClassifier(**params)
    clf.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
    if os.environ.get("SAVE_MODEL") == "1":
        clf.save_model(os.path.join(OUT_DIR, f"model_{HORIZON}.ubj"))
        json.dump({"horizon": HORIZON, "seed": SEED, "feat": feat,
                   "params": clf.get_params(),
                   "win_threshold": WIN, "h_steps": H_STEPS[HORIZON],
                   "n_train": int(len(tr)), "n_val": int(len(va)), "n_test": int(len(te)),
                   "ts_train_max": int(tr.ts.max()), "ts_test_min": int(te.ts.min()), "ts_test_max": int(te.ts.max())},
                  open(os.path.join(OUT_DIR, f"train_meta_{HORIZON}.json"), "w"), indent=2, default=str)
    pwin_te = clf.predict_proba(Xte)[:, 1]          # P(win); P(fail)=[:,0] (khoa convention)
    A = evaluate(f"model_{HORIZON}", pwin_te, yte)

    # baseline: chon (feature, sign) tot nhat theo LIFT tren VAL, roi do tren TEST (cong bang)
    best_val = (-1.0, None, 1)
    for c in feat:
        sv = va[c].fillna(va[c].median()).values
        st_ = te[c].fillna(te[c].median()).values
        for sgn in (1, -1):
            rv = evaluate(c, sgn * sv, yva)
            if not np.isnan(rv["LIFT"]) and rv["LIFT"] > best_val[0]:
                best_val = (rv["LIFT"], c, sgn)
    _, bc, bsgn = best_val
    base_test = evaluate(bc, bsgn * te[bc].fillna(te[bc].median()).values, yte)
    A["baseline_feature"] = f"{bc}{'+' if bsgn > 0 else '-'}"
    A["baseline_LIFT_test"] = base_test["LIFT"]
    A["beats_baseline"] = bool(A["LIFT"] > base_test["LIFT"])
    A["PASS_ml_gate"] = bool(A["LIFT"] >= 1.20 and A["N_top"] >= 100 and A["z"] >= 2 and abs(A["t_IC"]) >= 2)
    A["PASS_overall"] = bool(A["PASS_ml_gate"] and A["beats_baseline"])
    imp = sorted(zip(feat, clf.feature_importances_), key=lambda x: -x[1])[:15]
    A["top_importance"] = [(c, float(v)) for c, v in imp]
    if REPORT_QUARTERS:   # on dinh regime: LIFT/rankIC tung quy tren TEST
        te2 = te.assign(_p=pwin_te, _q=pd.to_datetime(te.ts, unit="ms").dt.to_period("Q").astype(str))
        pq = {}
        for q, g in te2.groupby("_q"):
            if len(g) >= 200:
                r = evaluate(q, g["_p"].values, g["y"].values)
                pq[q] = {"N": int(len(g)), "base": round(r["base_rate"], 4),
                         "LIFT": round(r["LIFT"], 3), "rankIC": round(r["rankIC"], 4)}
        A["per_quarter"] = pq
        A["seed"] = SEED
        log.info("  per_quarter LIFT: %s", {q: v["LIFT"] for q, v in pq.items()})
    json.dump(A, open(os.path.join(OUT_DIR, f"metrics_{HORIZON}.json"), "w"), indent=2)
    log.info("=== KET QUA H=%s ===", HORIZON)
    for kk in ["base_rate", "N_top", "hit_top", "LIFT", "z", "rankIC", "t_IC",
               "baseline_feature", "baseline_LIFT_test", "beats_baseline",
               "PASS_ml_gate", "PASS_overall"]:
        log.info("  %s = %s", kk, A[kk])
    log.info("  top feat: %s", [c for c, _ in A["top_importance"][:6]])


if __name__ == "__main__":
    horizons = [h.strip() for h in os.environ.get("HORIZONS", os.environ.get("HORIZON", "24h")).split(",")]
    for _h in horizons:
        assert _h in H_STEPS, f"horizon khong hop le: {_h}"
        run_one(_h)
