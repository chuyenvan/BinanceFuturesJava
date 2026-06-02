# -*- coding: utf-8 -*-
"""
TRAIN MARKET MODEL (V3 Full) — KHÔNG IN-SAMPLE, KHÔNG CHỒNG LẤN, ĐO IC CHUẨN.

3 TARGET, BẢN CHẤT KHÁC NHAU => CONFIG RIÊNG TỪNG TARGET (TARGET_CFG), CHUNG PLUMBING:
  - futureReturn15M / futureReturn24H = RETURN (higher=tốt) -> gate = IC đúng dấu + IR + quantile
    monotonic + BACKTEST long/flat/short có phí (Sharpe).
  - maxDrawdownNext4H = RISK (không phải return) -> KHÔNG backtest long/short. Gate = IC đúng dấu
    + monotonic + TAIL-RISK REDUCTION (nửa "an toàn" theo model phải ít sụt hơn rõ rệt).

Mọi chỉ số đo trên mẫu ĐÃ DE-OVERLAP (horizon riêng từng target). Gate MỘT CHIỀU, ĐÚNG DẤU
(model ngược dấu => FAIL, vì Java sẽ dùng score sai chiều).

Feature & thứ tự = OnnxInferenceManager.extractFeaturesV3Full() (33 feature). Scaler fit chỉ trên train.
Optuna tối ưu IC (đúng dấu, đã de-overlap) trên VAL. Holdout chỉ ĐO cuối.
"""
import os
import gc
import logging
import warnings

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
import optuna

from onnxmltools.convert import convert_xgboost
from onnxmltools.convert.common.data_types import FloatTensorType as OnnxFloatTensorType
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType as SklFloatTensorType

for h in logging.root.handlers[:]:
    logging.root.removeHandler(h)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)

# ====================== CẤU HÌNH CHUNG ======================
DATASET_PATH = "/kaggle/input/datasets/chuyendinh/market-training-data/storage/training_data_big_sequential"
OUTPUT_DIR = "/kaggle/working/ai_models_v3"

HOLDOUT_MONTHS = 12
VAL_FRAC = 0.15
PURGE_MS = 24 * 3600 * 1000     # purge GAP giữa split = horizon dài nhất (24H)
N_TRIALS = 40
TRADE_COST = 0.0004             # phí + slippage 1 chiều cho backtest. CHỈNH THEO SÀN.

MS_DAY = 86400 * 1000
MS_WEEK = 7 * MS_DAY

# 33 FEATURE — ĐÚNG THỨ TỰ extractFeaturesV3Full() (ONNX live). KHÔNG đổi thứ tự.
FEATURES = [
    "momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H",
    "momentumAcceleration", "trendStrengthETH", "trendConsistency",
    "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
    "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength", "btcDominance",
    "rsi14", "volumeSpike", "distMA20",
    "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
    "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike",
]

# ====================== CẤU HÌNH RIÊNG TỪNG TARGET ======================
# kind: "return" (giao dịch L/F/S) | "risk" (lọc rủi ro, KHÔNG L/F/S)
# horizon_ms: cửa sổ nhãn -> dùng để de-overlap & purge cho ĐÚNG target đó.
# worse_is_higher (chỉ "risk"): True nếu nhãn dd lưu dạng MAGNITUDE dương (lớn=tệ);
#                               False nếu lưu dạng SIGNED âm (âm=tệ).  ⚠️ CHỈNH KHỚP JAVA.
TARGET_CFG = {
    "futureReturn15M":   dict(kind="return", horizon_ms=15 * 60 * 1000),
    "futureReturn24H":   dict(kind="return", horizon_ms=24 * 3600 * 1000),
    "maxDrawdownNext4H": dict(kind="risk",   horizon_ms=4 * 3600 * 1000, worse_is_higher=False),
}
TARGETS = list(TARGET_CFG.keys())

# Ngưỡng GATE — chung phần ranking, riêng phần kinh tế.
GATE_T_IC = 2.0       # t-stat IC (ĐÚNG DẤU dương) >= 2
GATE_IR = 0.30        # IR theo bucket >= 0.3
GATE_POS = 0.60       # >=60% bucket có IC dương
GATE_MONO = 0.70      # rho monotonic quantile (DƯƠNG) >= 0.7
GATE_SHARPE = 0.50    # (return) Sharpe backtest quy năm >= 0.5
GATE_RISK_IMPROVE = 0.0  # (risk) tail-risk của nửa an toàn phải tốt hơn nửa rủi ro (>0)


# ====================== HÀM ĐO LƯỜNG CHUẨN ======================
def _nonoverlap_mask(ts, horizon_ms, groups=None):
    """Mặt nạ mẫu KHÔNG chồng lấn (>= horizon). groups=symbol -> de-overlap riêng từng coin."""
    ts = np.asarray(ts)
    mask = np.zeros(len(ts), dtype=bool)
    def _greedy(idx):
        idx = idx[np.argsort(ts[idx], kind="mergesort")]
        last = -np.inf
        for i in idx:
            if ts[i] - last >= horizon_ms:
                mask[i] = True
                last = ts[i]
    if groups is None:
        _greedy(np.arange(len(ts)))
    else:
        groups = np.asarray(groups)
        for g in pd.unique(groups):
            _greedy(np.where(groups == g)[0])
    return mask


def _ic_tstat(pred, true):
    pred, true = np.asarray(pred, float), np.asarray(true, float)
    ok = np.isfinite(pred) & np.isfinite(true)
    pred, true = pred[ok], true[ok]
    n = len(pred)
    if n < 10:
        return np.nan, np.nan, n
    ic, _ = spearmanr(pred, true)
    if not np.isfinite(ic) or abs(ic) >= 1.0:
        return ic, np.nan, n
    t = ic * np.sqrt((n - 2) / (1 - ic * ic))
    return ic, t, n


def _block_bootstrap_ci(pred, true, ts, n_boot=500, seed=0):
    order = np.argsort(np.asarray(ts), kind="mergesort")
    pred, true = np.asarray(pred, float)[order], np.asarray(true, float)[order]
    n = len(pred)
    if n < 30:
        return (np.nan, np.nan)
    L = max(2, int(round(np.sqrt(n))))
    n_blocks = int(np.ceil(n / L))
    pool = np.arange(0, n - L + 1)
    rng = np.random.default_rng(seed)
    ics = []
    for _ in range(n_boot):
        starts = rng.choice(pool, size=n_blocks, replace=True)
        idx = np.concatenate([np.arange(s, s + L) for s in starts])[:n]
        ic, _ = spearmanr(pred[idx], true[idx])
        if np.isfinite(ic):
            ics.append(ic)
    if not ics:
        return (np.nan, np.nan)
    return (float(np.percentile(ics, 2.5)), float(np.percentile(ics, 97.5)))


def _bucketed_ic(pred, true, ts, bucket_ms):
    bucket = (np.asarray(ts) // bucket_ms)
    vals = []
    for b in np.unique(bucket):
        m = bucket == b
        if m.sum() >= 20:
            ic, _ = spearmanr(pred[m], true[m])
            if np.isfinite(ic):
                vals.append(ic)
    if not vals:
        return None
    v = np.array(vals)
    ir = (v.mean() / v.std() * np.sqrt(len(v))) if v.std() > 0 else np.nan
    return dict(mean=v.mean(), std=v.std(), ir=ir, pos=(v > 0).mean(), n=len(v))


def _quantile_monotonicity(pred, true, n_q=5):
    pred, true = np.asarray(pred, float), np.asarray(true, float)
    try:
        q = pd.qcut(pd.Series(pred).rank(method="first"), n_q, labels=False, duplicates="drop")
    except Exception:
        return None, np.nan
    groups = sorted(pd.unique(q))
    means = [true[q.values == g].mean() for g in groups]
    if len(means) < 3:
        return means, np.nan
    rho, _ = spearmanr(np.arange(len(means)), means)
    return means, rho


def _backtest(pred, true, horizon_ms, cost=TRADE_COST):
    """RETURN: long/flat/short trên mẫu KHÔNG chồng lấn. pred>=Q70 long, <=Q30 short, else flat."""
    pred, true = np.asarray(pred, float), np.asarray(true, float)
    if len(pred) < 30:
        return None
    hi, lo = np.quantile(pred, 0.70), np.quantile(pred, 0.30)
    pos = np.where(pred >= hi, 1.0, np.where(pred <= lo, -1.0, 0.0))
    turn = np.abs(np.diff(np.concatenate([[0.0], pos])))
    pnl = pos * true - turn * cost
    if pnl.std() == 0:
        return None
    ppy = (365.0 * MS_DAY) / float(horizon_ms)
    cum = np.cumsum(pnl)
    return dict(sharpe=float(pnl.mean() / pnl.std() * np.sqrt(ppy)),
                ret=float(cum[-1]), turnover=float(turn.mean()),
                maxdd=float((cum - np.maximum.accumulate(cum)).min()))


def _risk_reduction(pred, true, worse_is_higher):
    """RISK: chia 2 nửa theo predicted-dd. Nửa 'an toàn' phải có đáy realized ít tệ hơn."""
    pred, true = np.asarray(pred, float), np.asarray(true, float)
    if len(pred) < 30:
        return None
    med = np.median(pred)
    if worse_is_higher:                       # nhãn lớn = tệ -> an toàn = pred nhỏ
        safe, risky = true[pred <= med], true[pred > med]
        tail_safe, tail_risky = np.percentile(safe, 95), np.percentile(risky, 95)
        improve = tail_risky - tail_safe
    else:                                     # nhãn âm = tệ -> an toàn = pred lớn
        safe, risky = true[pred >= med], true[pred < med]
        tail_safe, tail_risky = np.percentile(safe, 5), np.percentile(risky, 5)
        improve = tail_safe - tail_risky
    return dict(tail_safe=float(tail_safe), tail_risky=float(tail_risky), improve=float(improve))


def report_and_gate(name, holdout, y_pred):
    """In đầy đủ + gate PASS/FAIL theo kind của target."""
    cfg = TARGET_CFG[name]
    horizon = cfg["horizon_ms"]
    ts = holdout["timestamp"].values
    y = holdout[name].values
    groups = holdout["symbol"].values if "symbol" in holdout.columns else None

    mask = _nonoverlap_mask(ts, horizon, groups)
    p, yt, tt = y_pred[mask], y[mask], ts[mask]
    logger.info("   • [%s/%s] mẫu=%d -> de-overlap=%d (cửa sổ %dh)",
                name, cfg["kind"], len(y), int(mask.sum()), horizon // 3600000)

    # --- ranking chung: IC (ĐÚNG DẤU dương) + IR + monotonic ---
    ic, tstat, n = _ic_tstat(p, yt)
    lo, hi = _block_bootstrap_ci(p, yt, tt)
    logger.info("   • IC=%.4f t=%.2f n=%d CI95=[%.3f, %.3f]",
                ic, (tstat if np.isfinite(tstat) else float('nan')), n, lo, hi)
    # Bucket phải đủ lớn để mỗi bucket chứa >=20 mẫu ĐÃ de-overlap. De-overlap cho ~1 mẫu/horizon,
    # nên cần ~>=20*horizon. Với 24H: ~28 ngày (~28 mẫu/bucket); 15M & 4H vẫn co về ~tuần.
    # (Nếu để 4*horizon, target 24H chỉ ~7 mẫu/tuần < 20 -> bk=None -> gate ir/pos FAIL oan.)
    bucket_ms = max(MS_WEEK, 28 * horizon)
    bk = _bucketed_ic(p, yt, tt, bucket_ms)
    if bk:
        logger.info("   • IC bucket(~%dd): mean=%.4f std=%.4f IR=%.2f %%>0=%.0f%% (n=%d)",
                    bucket_ms // MS_DAY, bk['mean'], bk['std'], bk['ir'], bk['pos'] * 100, bk['n'])
    means, rho = _quantile_monotonicity(p, yt, 5)
    if means is not None:
        logger.info("   • Quintile realized: %s | monotonic rho=%.2f",
                    [round(float(x), 6) for x in means], rho)

    passed = {
        "ic_pos_sig": (np.isfinite(tstat) and ic > 0 and tstat >= GATE_T_IC),
        "ir": (bk is not None and np.isfinite(bk['ir']) and bk['ir'] >= GATE_IR),
        "pos": (bk is not None and bk['pos'] >= GATE_POS),
        "mono": (np.isfinite(rho) and rho >= GATE_MONO),
    }

    # --- phần kinh tế: RIÊNG theo kind ---
    if cfg["kind"] == "return":
        bt = _backtest(p, yt, horizon)
        if bt:
            logger.info("   • Backtest L/F/S (phí %.4f): Sharpe=%.2f ret=%.4f turnover=%.2f maxDD=%.4f",
                        TRADE_COST, bt['sharpe'], bt['ret'], bt['turnover'], bt['maxdd'])
        passed["sharpe"] = (bt is not None and bt['sharpe'] >= GATE_SHARPE)
    else:  # risk
        rr = _risk_reduction(p, yt, cfg.get("worse_is_higher", False))
        if rr:
            logger.info("   • Tail-risk: nửa an toàn=%.4f vs nửa rủi ro=%.4f -> cải thiện=%.4f",
                        rr['tail_safe'], rr['tail_risky'], rr['improve'])
        passed["risk_reduce"] = (rr is not None and rr['improve'] > GATE_RISK_IMPROVE)

    ok = all(passed.values())
    logger.info("   • GATE %s -> %s | %s", name, "✅ PASS" if ok else "❌ FAIL", passed)
    return ok


# ====================== DATA + SPLIT ======================
def load_all(data_dir):
    single = os.path.join(data_dir, "features_all.csv")
    if os.path.exists(single):
        files = [single]
    else:
        files = []
        for root, _, fs in os.walk(data_dir):
            for f in fs:
                if f.endswith(".csv"):
                    files.append(os.path.join(root, f))
    if not files:
        raise FileNotFoundError(f"Không thấy CSV trong {data_dir}")

    parts = []
    need = set(["timestamp", "symbol"] + FEATURES + TARGETS)
    for fn in sorted(files):
        try:
            df = pd.read_csv(fn)
            if len(df) < 5 or "timestamp" not in df.columns:
                continue
            keep = [c for c in df.columns if c in need]
            parts.append(df[keep])
        except Exception:
            pass

    df = pd.concat(parts, ignore_index=True)
    for c in FEATURES + TARGETS:
        if c not in df.columns:
            df[c] = 0.0
    df = df.replace([np.inf, -np.inf], 0.0)
    df[FEATURES] = df[FEATURES].fillna(0.0)
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    logger.info("✅ Tổng mẫu: %d | từ %s đến %s | có symbol=%s",
                len(df),
                pd.to_datetime(df["timestamp"].iloc[0], unit="ms"),
                pd.to_datetime(df["timestamp"].iloc[-1], unit="ms"),
                "symbol" in df.columns)
    return df


def time_split(df):
    """Purge GAP = horizon DÀI NHẤT (24H) để mọi target đều không peek chéo split."""
    ts = df["timestamp"].values
    usable_max = ts[-1] - PURGE_MS
    holdout_cut = usable_max - HOLDOUT_MONTHS * 30 * MS_DAY
    dev = df[ts < holdout_cut - PURGE_MS]
    holdout = df[(df["timestamp"].values >= holdout_cut) & (df["timestamp"].values <= usable_max)]
    dev_ts = dev["timestamp"].values
    val_cut = np.quantile(dev_ts, 1 - VAL_FRAC)
    train = dev[dev_ts < val_cut - PURGE_MS]
    val = dev[dev["timestamp"].values >= val_cut]
    logger.info("📦 SPLIT  train=%d  val=%d  holdout=%d", len(train), len(val), len(holdout))
    logger.info("   holdout [%s .. %s] (purge %dh)",
                pd.to_datetime(holdout_cut, unit="ms"), pd.to_datetime(usable_max, unit="ms"),
                PURGE_MS // 3600000)
    return train, val, holdout


# ====================== TRAIN 1 TARGET ======================
def train_one(target, train, val, holdout):
    cfg = TARGET_CFG[target]
    logger.info("\n🚀 TARGET: %s (kind=%s, horizon=%dh)", target, cfg["kind"], cfg["horizon_ms"] // 3600000)

    scaler = StandardScaler()
    Xtr = scaler.fit_transform(train[FEATURES].values)
    Xva = scaler.transform(val[FEATURES].values)
    Xho = scaler.transform(holdout[FEATURES].values)
    ytr, yva, yho = train[target].values, val[target].values, holdout[target].values

    val_groups = val["symbol"].values if "symbol" in val.columns else None
    val_mask = _nonoverlap_mask(val["timestamp"].values, cfg["horizon_ms"], val_groups)
    logger.info("   • val de-overlap để HPO: %d / %d", int(val_mask.sum()), len(yva))

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 400, 1500),
            "max_depth": trial.suggest_int("max_depth", 3, 9),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 0.9),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 0.9),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 50),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 10.0, log=True),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 10.0, log=True),
            "tree_method": "hist", "n_jobs": -1, "early_stopping_rounds": 50,
        }
        m = xgb.XGBRegressor(**params)
        m.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        ic, _, _ = _ic_tstat(m.predict(Xva)[val_mask], yva[val_mask])   # IC đúng dấu, de-overlap
        return -1.0 if not np.isfinite(ic) else ic

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=N_TRIALS)
    logger.info("   best val IC(de-overlap)=%.4f | n_trials=%d (NHỚ deflate khi đọc holdout)",
                study.best_value, N_TRIALS)

    best = dict(study.best_params)
    best.update({"n_estimators": 20000, "learning_rate": 0.005,
                 "early_stopping_rounds": 1000, "tree_method": "hist", "n_jobs": -1})
    model = xgb.XGBRegressor(**best)
    model.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=500)

    logger.info("📊 ĐO TRÊN HOLDOUT (chưa từng thấy):")
    pred_ho = model.predict(Xho)
    logger.info("   R2 holdout=%.4f", r2_score(yho, pred_ho))
    passed = report_and_gate(target, holdout, pred_ho)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    clean = target.replace("future", "").replace("Next", "")
    onnx_m = convert_xgboost(model, initial_types=[('float_input', OnnxFloatTensorType([None, len(FEATURES)]))])
    with open(f"{OUTPUT_DIR}/Model_Regressor_{clean}.onnx", "wb") as f:
        f.write(onnx_m.SerializeToString())
    onnx_s = convert_sklearn(scaler, initial_types=[('float_input', SklFloatTensorType([None, len(FEATURES)]))])
    with open(f"{OUTPUT_DIR}/Scaler_{clean}.onnx", "wb") as f:
        f.write(onnx_s.SerializeToString())
    logger.info("💾 Lưu Model_Regressor_%s.onnx + Scaler_%s.onnx", clean, clean)

    del Xtr, Xva, Xho, model
    gc.collect()
    return passed


if __name__ == "__main__":
    df = load_all(DATASET_PATH)
    train, val, holdout = time_split(df)
    del df
    gc.collect()
    results = {t: train_one(t, train, val, holdout) for t in TARGETS}
    logger.info("\n🎯 KẾT QUẢ GATE: %s", results)
    logger.info("🎉 XONG. return -> IC đúng dấu + IR + monotonic + Sharpe sau phí; "
                "risk -> IC đúng dấu + monotonic + giảm tail-risk. Tất cả trên mẫu de-overlap.")