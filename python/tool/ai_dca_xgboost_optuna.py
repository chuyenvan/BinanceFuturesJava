# -*- coding: utf-8 -*-
import os
import gc
import glob
import logging
import ctypes
import random
import pandas as pd
import numpy as np
import xgboost as xgb
import optuna
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from onnxmltools.convert import convert_xgboost
from onnxconverter_common.data_types import FloatTensorType

# --- 1. CẤU HÌNH GRANDMASTER ---
# Tận dụng tối đa 2 Core vật lý mạnh mẽ
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = "storage/training_data_dca"
HEADER_FILE = f"{BASE_DIR}/header.csv"
DATA_PATTERN = f"{BASE_DIR}/data_*.csv"
MODEL_DIR = "models_dca_grandmaster" # Lưu folder riêng cho bản xịn

# 🔥 NÂNG CẤP 1: Tăng mẫu lên 3.5 Triệu (Vì RAM đang dư)
TARGET_SAMPLES_FINAL = 3500000
ESTIMATED_TOTAL_ROWS = 11200000

# Tìm kiếm tham số kỹ hơn (100 vòng)
N_TRIALS = 100

os.makedirs(MODEL_DIR, exist_ok=True)

def force_release_ram():
    """Ép OS thu hồi RAM ngay lập tức"""
    gc.collect()
    try:
        ctypes.CDLL('libc.so.6').malloc_trim(0)
    except:
        pass

def load_data_chunked_hd():
    logger.info("1. Reading Header...")
    if not os.path.exists(HEADER_FILE): return None

    header_df = pd.read_csv(HEADER_FILE)
    col_names = header_df.columns.tolist()

    # Tính toán tỷ lệ lấy mẫu
    sampling_rate = TARGET_SAMPLES_FINAL / ESTIMATED_TOTAL_ROWS
    sampling_rate = min(sampling_rate * 1.1, 1.0) # Lấy dư 10% để lọc rác

    logger.info(f"Target: {TARGET_SAMPLES_FINAL} rows. Sampling Rate: {sampling_rate:.1%}")

    file_list = glob.glob(DATA_PATTERN)
    chunks_list = []
    total_loaded = 0

    logger.info(f"2. Processing {len(file_list)} files (HD Quality)...")

    for file_path in file_list:
        # Load chunk vừa phải (200k)
        chunk_iter = pd.read_csv(file_path, names=col_names, header=None, chunksize=200000)

        for chunk in chunk_iter:
            # Lọc rác
            chunk = chunk[chunk['volatilityShock'] > 0.3] # Lấy cả biến động nhẹ hơn (0.3 thay vì 0.5)

            # Khử trùng
            chunk = chunk.drop_duplicates(subset=['distFromHigh24H', 'rsi1H', 'crashVelocity'])

            # Sampling
            if sampling_rate < 1.0 and not chunk.empty:
                chunk = chunk.sample(frac=sampling_rate, random_state=42)

            # Ép kiểu Float32 (Tiết kiệm RAM để dành cho thuật toán nặng)
            float_cols = chunk.select_dtypes(include=['float64']).columns
            chunk[float_cols] = chunk[float_cols].astype('float32')

            if not chunk.empty:
                chunks_list.append(chunk)
                total_loaded += len(chunk)

            if len(chunks_list) % 50 == 0:
                print(f"   -> Collected so far: {total_loaded} rows...", end='\r')

    logger.info(f"\nMerging {len(chunks_list)} chunks...")
    if not chunks_list: return None

    df = pd.concat(chunks_list, ignore_index=True)
    del chunks_list
    force_release_ram()

    # Chốt số lượng mẫu cuối cùng
    if len(df) > TARGET_SAMPLES_FINAL:
        logger.info(f"Refining size: {len(df)} -> {TARGET_SAMPLES_FINAL}")
        df = df.sample(n=TARGET_SAMPLES_FINAL, random_state=42)
        force_release_ram()

    logger.info(f"✅ HD Dataset ready: {len(df)} rows.")
    return df

def train_and_export_grandmaster(df, target_col, model_name_suffix):
    logger.info(f"\n{'='*50}\n🔥 START GRANDMASTER TRAINING: {target_col}\n{'='*50}")
    if target_col not in df.columns: return

    force_release_ram()

    ignore_cols = ['labelMaxDropFromNow', 'labelMaxRiseFromNow']
    feature_cols = [c for c in df.columns if c not in ignore_cols]

    # Split Data (Giữ Validation lớn để đánh giá chuẩn)
    X_train, X_valid, y_train, y_valid = train_test_split(
        df[feature_cols], df[target_col], test_size=0.15, random_state=999, shuffle=True
    )

    # --- GIAI ĐOẠN 1: OPTUNA (Tìm cấu trúc cây tốt nhất) ---
    logger.info("PHASE 1: Searching for best Architecture (Optuna)...")

    def objective(trial):
        param = {
            'verbosity': 0,
            'objective': 'reg:squarederror',
            'tree_method': 'hist',
            'n_jobs': 2,

            # 🔥 NÂNG CẤP 2: Tăng độ phân giải lên chuẩn (HD)
            'max_bin': 256,   # Trả về 256 vì RAM đang dư -> Chính xác hơn
            'enable_categorical': False,

            # Search space rộng
            'learning_rate': trial.suggest_float('learning_rate', 0.05, 0.2), # LR cao để dò nhanh cấu trúc
            'max_depth': trial.suggest_int('max_depth', 6, 14), # Cho phép cây sâu hơn
            'min_child_weight': trial.suggest_int('min_child_weight', 50, 400),
            'subsample': trial.suggest_float('subsample', 0.6, 0.9),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.9),
            'gamma': trial.suggest_float('gamma', 0.0, 5.0), # Thêm Gamma để tỉa cành
            'reg_alpha': trial.suggest_float('reg_alpha', 0.1, 20.0, log=True),
            'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 20.0, log=True),
        }

        # Train nhanh để test cấu trúc (1000 cây)
        model = xgb.XGBRegressor(**param, n_estimators=1000, early_stopping_rounds=50)

        pruning_callback = optuna.integration.XGBoostPruningCallback(trial, "validation_0-rmse")

        model.fit(
            X_train, y_train, eval_set=[(X_valid, y_valid)],
            verbose=False, callbacks=[pruning_callback]
        )
        return np.sqrt(mean_squared_error(y_valid, model.predict(X_valid)))

    study = optuna.create_study(direction='minimize')
    study.optimize(objective, n_trials=N_TRIALS)
    logger.info(f"Best Structure RMSE: {study.best_value:.5f}")

    # --- GIAI ĐOẠN 2: SLOW COOKING (Train thật sự) ---
    logger.info("PHASE 2: Slow Cooking with Low Learning Rate...")

    best_params = study.best_params

    # Cập nhật thông số cố định
    best_params['n_jobs'] = 2
    best_params['tree_method'] = 'hist'
    best_params['objective'] = 'reg:squarederror'
    best_params['max_bin'] = 256            # Giữ nguyên HD
    best_params['enable_categorical'] = False

    # 🔥 NÂNG CẤP 3: Ép Learning Rate siêu nhỏ để học chi tiết
    best_params['learning_rate'] = 0.005  # Rất nhỏ (Chậm nhưng chắc)

    # 🔥 NÂNG CẤP 4: Tăng số lượng cây lên cực đại
    # Với LR=0.005, ta cần khoảng 20k-50k cây để hội tụ
    final_model = xgb.XGBRegressor(
        **best_params,
        n_estimators=50000,        # Max 50k cây
        early_stopping_rounds=1000 # Kiên nhẫn chờ 1000 vòng
    )

    final_model.fit(
        X_train, y_train,
        eval_set=[(X_valid, y_valid)],
        verbose=1000 # In log mỗi 1000 cây
    )

    # --- EXPORT ---
    onnx_path = f"{MODEL_DIR}/Model_Grandmaster_{model_name_suffix}.onnx"

    # Xóa tên cột để tránh lỗi Feature Name
    final_model.get_booster().feature_names = None

    initial_type = [('float_input', FloatTensorType([None, len(feature_cols)]))]
    onnx_model = convert_xgboost(final_model, initial_types=initial_type)
    with open(onnx_path, "wb") as f: f.write(onnx_model.SerializeToString())

    logger.info(f"✅ DONE {model_name_suffix} (Slow Cooked)")
    del final_model, X_train, X_valid, y_train, y_valid
    force_release_ram()

def main():
    # Load Data xịn
    df = load_data_chunked_hd()
    if df is None: return

    # Train Risk (Sập)
    train_and_export_grandmaster(df, 'labelMaxDropFromNow', 'Risk')

    # Train Reward (Hồi)
    train_and_export_grandmaster(df, 'labelMaxRiseFromNow', 'Reward')

    logger.info("\n🏆 GRANDMASTER TRAINING COMPLETED!")

if __name__ == "__main__":
    main()