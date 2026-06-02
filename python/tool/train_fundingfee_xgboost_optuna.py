# -*- coding: utf-8 -*-
"""
TRAIN FUNDING CLASSIFIER — KHÔNG IN-SAMPLE, KHÔNG CHỒNG LẤN, ĐO IC/LIFT CHUẨN.

Nguyên tắc (Bước 1 ROADMAP + LUẬT #7 CLAUDE.md):
  1. Feature & THỨ TỰ LẤY ĐÚNG theo ONNX live:
     com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager.extractFeaturesToArray()
     => 21 feature, KHÔNG có momentum1M, đúng thứ tự dưới đây.
  2. CSV có timestamp,symbol ở đầu => split THEO THỜI GIAN + purge 72H chống chồng lấn chéo split.
  3. KHÔNG shuffle/stratify (leak chuỗi thời gian).
  4. Funding live KHÔNG có scaler => train cũng KHÔNG scale (giữ phân phối xác suất cho ngưỡng live).
  5. Gate trên HOLDOUT = NGƯỠNG SỐ CỨNG (xem GATE_*).

Nhãn (5 lớp, theo tốc độ chạm target): 4=trong 15M, 3=4H, 2=24H, 1=72H, 0=fail.

ĐO CHUẨN (sửa lỗi pooled-IC cũ):
  - Nhãn nhìn xa 72H, lấy mỗi phút => chồng lấn nặng. DE-OVERLAP THEO TỪNG SYMBOL trước khi đo.
  - Thước đo CHÍNH = conditional hit-rate / LIFT vs base-rate + z-test (cross-section của bạn
    chỉ 2-5 coin/mốc nên rank-IC cross-section thường vô nghĩa).
  - rank-IC (exp_class vs label) + t-stat + bootstrap CI là thước đo phụ, đo trên mẫu de-overlap.
  - IC cross-section per-timestamp chỉ tính khi mốc đó đủ coin (>=MIN_XS_COINS), nếu không thì bỏ qua.
"""
import os
import gc
import glob
import logging
import warnings

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr, norm

from skl2onnx import to_onnx, update_registered_converter
from skl2onnx.common.shape_calculator import calculate_linear_classifier_output_shapes
from onnxmltools.convert.xgboost.operator_converters.XGBoost import convert_xgboost as convert_xgboost_node

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')
os.environ["OMP_NUM_THREADS"] = "4"

# ====================== CẤU HÌNH ======================
DATA_DIR = "/kaggle/input/funding-entry/training_data_funding"
MODEL_DIR = "/kaggle/working/models_funding"
os.makedirs(MODEL_DIR, exist_ok=True)

TARGET = "label6"               # 🔧 "label6" (+6%) hoặc "label40" (+40%)
HOLDOUT_MONTHS = 12
VAL_FRAC = 0.15
HORIZON_MS = 72 * 3600 * 1000   # purge & de-overlap = 72H (nhãn xa nhất)
NUM_CLASS = 5
MS_DAY = 86400 * 1000
MS_WEEK = 7 * MS_DAY
MIN_XS_COINS = 8                # số coin tối thiểu/mốc để IC cross-section có nghĩa

# Ngưỡng GATE (mẫu đã de-overlap).
GATE_LIFT = 1.20        # lift hit-rate@P(fast)>=0.5 vs base >= 1.2
GATE_LIFT_N = 100       # cần >=100 lệnh được chọn ở ngưỡng đó
GATE_LIFT_Z = 2.0       # z-test lift khác base có ý nghĩa
GATE_T_IC = 2.0         # |t| rank-IC >= 2

# Schema CSV (KHÔNG header trong file data) — 26 cột Java xuất.
COLUMNS = [
    "timestamp", "symbol",
    "btcMomentum1H", "btcMomentum4H", "btcMomentum24H", "btcDominance", "marketBreadthStrength",
    "momentum1M", "momentum15M", "momentum1H", "momentum4H", "momentum24H",
    "rsi1H", "distFromLow24H", "volatilityShock",
    "basketMomentum15M", "basketMomentum1H", "basketMomentum24H", "basketRsi14", "basketVolSpike",
    "coinFundingRate", "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "label6", "label40",
]

# 21 FEATURE — ĐÚNG thứ tự extractFeaturesToArray() (BỎ momentum1M, timestamp, symbol, labels).
FEATURES = [
    "btcMomentum1H", "btcMomentum4H", "btcMomentum24H", "btcDominance", "marketBreadthStrength",
    "momentum15M", "momentum1H", "momentum4H", "momentum24H", "rsi1H", "distFromLow24H", "volatilityShock",
    "basketMomentum15M", "basketMomentum1H", "basketMomentum24H", "basketRsi14", "basketVolSpike",
    "coinFundingRate", "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
]


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


def _lift_ztest(hit, base, n):
    """z-test 1 mẫu: tỉ lệ hit (n quan sát) khác base-rate không (base coi như đã biết)."""
    if n <= 0 or base <= 0 or base >= 1:
        return np.nan
    se = np.sqrt(base * (1 - base) / n)
    return (hit - base) / se if se > 0 else np.nan


# ====================== DATA + SPLIT ======================
def load_all():
    single = f"{DATA_DIR}/data_funding_all.csv"
    files = [single] if os.path.exists(single) else sorted(glob.glob(f"{DATA_DIR}/data_funding_*.csv"))
    if not files:
        raise FileNotFoundError(f"Không thấy data_funding_*.csv trong {DATA_DIR}")

    dtypes = {c: "float32" for c in COLUMNS}
    dtypes.update({"timestamp": "int64", "symbol": "string", "label6": "int8", "label40": "int8"})

    parts = []
    for f in files:
        try:
            df = pd.read_csv(f, names=COLUMNS, header=None, dtype=dtypes)
            df = df[df[TARGET].isin(range(NUM_CLASS))]
            parts.append(df)
        except Exception:
            pass

    df = pd.concat(parts, ignore_index=True)
    df = df.replace([np.inf, -np.inf], 0.0)
    df[FEATURES] = df[FEATURES].fillna(0.0)
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    logger.info("✅ Tổng mẫu: %d | từ %s đến %s | phân bố %s: %s",
                len(df),
                pd.to_datetime(df["timestamp"].iloc[0], unit="ms"),
                pd.to_datetime(df["timestamp"].iloc[-1], unit="ms"),
                TARGET, np.bincount(df[TARGET].values, minlength=NUM_CLASS).tolist())
    return df


def time_split(df):
    ts = df["timestamp"].values
    usable_max = ts[-1] - HORIZON_MS
    holdout_cut = usable_max - HOLDOUT_MONTHS * 30 * MS_DAY
    dev = df[ts < holdout_cut - HORIZON_MS]
    holdout = df[(df["timestamp"].values >= holdout_cut) & (df["timestamp"].values <= usable_max)]
    dev_ts = dev["timestamp"].values
    val_cut = np.quantile(dev_ts, 1 - VAL_FRAC)
    train = dev[dev_ts < val_cut - HORIZON_MS]
    val = dev[dev["timestamp"].values >= val_cut]
    logger.info("📦 SPLIT  train=%d  val=%d  holdout=%d | holdout [%s .. %s] (cắt đuôi %dh)",
                len(train), len(val), len(holdout),
                pd.to_datetime(holdout_cut, unit="ms"), pd.to_datetime(usable_max, unit="ms"),
                HORIZON_MS // 3600000)
    return train, val, holdout


def regime_of(df):
    m = df["btcMomentum24H"].values
    return np.where(m > 0.02, "up", np.where(m < -0.02, "down", "side"))


# ====================== REPORT + GATE ======================
def report_and_gate(holdout, proba):
    """LIFT (chính) + rank-IC (phụ) + cross-section IC (nếu đủ coin), trên mẫu DE-OVERLAP."""
    y_full = holdout[TARGET].values
    ts_full = holdout["timestamp"].values
    sym_full = holdout["symbol"].values
    exp_full = (proba * np.arange(NUM_CLASS)).sum(axis=1)     # điểm kỳ vọng lớp
    pfast_full = proba[:, 3] + proba[:, 4]                    # P(chạm <=4H)

    # --- de-overlap theo từng symbol (nhãn 72H) ---
    mask = _nonoverlap_mask(ts_full, HORIZON_MS, sym_full)
    y, ts, exp_c, pfast = y_full[mask], ts_full[mask], exp_full[mask], pfast_full[mask]
    logger.info("   • holdout=%d -> de-overlap=%d (72H theo symbol)", len(y_full), int(mask.sum()))

    # --- (1) rank-IC phụ ---
    ic, tstat, n = _ic_tstat(exp_c, y)
    lo, hi = _block_bootstrap_ci(exp_c, y, ts)
    logger.info("   • rank-IC(de-overlap)=%.4f t=%.2f n=%d CI95=[%.3f, %.3f]",
                ic, (tstat if np.isfinite(tstat) else float('nan')), n, lo, hi)

    # --- (2) IC cross-section per-timestamp (chỉ khi đủ coin) ---
    xs = []
    for t_ in np.unique(ts_full):
        m = ts_full == t_
        if m.sum() >= MIN_XS_COINS:
            v, _ = spearmanr(exp_full[m], y_full[m])
            if np.isfinite(v):
                xs.append(v)
    if xs:
        xs = np.array(xs)
        ir_xs = xs.mean() / xs.std() * np.sqrt(len(xs)) if xs.std() > 0 else np.nan
        logger.info("   • IC cross-section: mean=%.4f IR=%.2f n_mốc=%d (>=%d coin)",
                    xs.mean(), ir_xs, len(xs), MIN_XS_COINS)
    else:
        logger.info("   • IC cross-section: BỎ QUA (không mốc nào đủ %d coin) -> dựa vào LIFT.", MIN_XS_COINS)

    # --- (3) LIFT — thước đo CHÍNH ---
    base = np.isin(y, [3, 4]).mean()
    logger.info("   • base-rate hit(<=4H) = %.1f%%", base * 100)
    lift_pass = False
    for thr in (0.3, 0.5, 0.7):
        sel = pfast >= thr
        ns = int(sel.sum())
        if ns >= 30:
            hit = np.isin(y[sel], [3, 4]).mean()
            lift = hit / base if base > 0 else float('nan')
            z = _lift_ztest(hit, base, ns)
            logger.info("     P(fast)>=%.1f: n=%d hit=%.1f%% (base %.1f%%) lift=x%.2f z=%.2f",
                        thr, ns, hit * 100, base * 100, lift, z)
            if abs(thr - 0.5) < 1e-9:
                lift_pass = (ns >= GATE_LIFT_N and lift >= GATE_LIFT and np.isfinite(z) and z >= GATE_LIFT_Z)

    # --- LIFT theo regime ---
    rg = regime_of(holdout)[mask]
    for r in ["up", "down", "side"]:
        m = (rg == r) & (pfast >= 0.5)
        if m.sum() >= 30:
            hit = np.isin(y[m], [3, 4]).mean()
            logger.info("     [regime %s] n=%d hit@0.5=%.1f%%", r, int(m.sum()), hit * 100)

    # --- GATE ---
    passed = {
        "lift@0.5": lift_pass,
        "t_rankIC": (np.isfinite(tstat) and abs(tstat) >= GATE_T_IC),
    }
    ok = all(passed.values())
    logger.info("   • GATE -> %s | chi tiết: %s", "✅ PASS" if ok else "❌ FAIL", passed)
    return ok


# ====================== MAIN ======================
def main():
    df = load_all()
    train, val, holdout = time_split(df)
    del df
    gc.collect()

    params = dict(objective="multi:softprob", num_class=NUM_CLASS, tree_method="hist",
                  device="cuda", eval_metric="mlogloss", learning_rate=0.015, max_depth=10,
                  min_child_weight=50, subsample=0.8, colsample_bytree=0.8,
                  reg_lambda=1.0, reg_alpha=0.0, n_estimators=10000)
    model = xgb.XGBClassifier(**params, early_stopping_rounds=100)
    logger.info("🔥 Train (time-ordered, no shuffle)...")
    model.fit(train[FEATURES].values, train[TARGET].values,
              eval_set=[(val[FEATURES].values, val[TARGET].values)], verbose=500)

    logger.info("📊 ĐO TRÊN HOLDOUT (chưa từng thấy):")
    proba = model.predict_proba(holdout[FEATURES].values)
    passed = report_and_gate(holdout, proba)
    logger.info("🎯 KẾT QUẢ GATE (%s): %s", TARGET, "✅ PASS" if passed else "❌ FAIL")

    # EXPORT ONNX (21 feature thô, KHÔNG scaler — khớp inference live)
    update_registered_converter(
        xgb.XGBClassifier, 'XGBoostXGBClassifier',
        calculate_linear_classifier_output_shapes, convert_xgboost_node,
        options={'nocl': [True, False], 'zipmap': [True, False, 'columns']})
    model.get_booster().feature_names = None
    X_sample = train[FEATURES].values[:1].astype(np.float32)
    onnx_model = to_onnx(model, X_sample,
                         target_opset={'': 12, 'ai.onnx.ml': 3}, options={'zipmap': False})
    save_path = f"{MODEL_DIR}/Funding_Classifier_Final.onnx"
    with open(save_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    logger.info("✅ Lưu %s (target=%s). Lưu ý tool sinh predict đọc 'Funding_Classifier_Final_Fixed.onnx' "
                "— đổi tên/đối chiếu khi deploy.", save_path, TARGET)


if __name__ == "__main__":
    main()