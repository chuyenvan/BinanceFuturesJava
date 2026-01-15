# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
from onnxmltools.convert import convert_xgboost, convert_sklearn
from onnxmltools.convert.common.data_types import FloatTensorType as OnnxFloatTensorType
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType as SklFloatTensorType
import logging
import warnings
import argparse
import optuna

# CẤU HÌNH TÀI NGUYÊN
os.environ["OMP_NUM_THREADS"] = "3"
os.environ["OPENBLAS_NUM_THREADS"] = "3"
os.environ["MKL_NUM_THREADS"] = "3"

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class V3_5_FinalTrainer:
    def __init__(self, model_dir="ai_models_v3_5_final"):
        self.model_dir = model_dir
        self.scaler = StandardScaler()
        os.makedirs(model_dir, exist_ok=True)

    def preprocess_data(self, df, target_name):
        # 1. FIX LỖI KHOẢNG TRẮNG TÊN CỘT
        df.columns = df.columns.str.strip()

        # 2. TÍNH TOÁN CÁC FEATURE QUAN TRỌNG (Python tự tính lại để chắc chắn)

        # [NEW] Volatility Term Structure (Cấu trúc kỳ hạn biến động)
        # Logic: Biến động ngắn hạn (1H) so với dài hạn (24H)
        # Nếu > 1: Thị trường đang biến động mạnh (Panic/FOMO). Nếu < 1: Sideway.
        if 'volatility1H' in df.columns and 'volatility24H' in df.columns:
            # Cộng 1e-6 để tránh chia cho 0
            df['volatilityTermStructure'] = df['volatility1H'] / (df['volatility24H'] + 1e-6)

        # [NEW] Momentum Interaction
        if 'momentum15M' in df.columns and 'volatility1H' in df.columns:
            df['mom15M_vol1H'] = df['momentum15M'] * df['volatility1H']

        # [NEW] RSI Acceleration
        if 'rsi14' in df.columns and 'momentumAcceleration' in df.columns:
            df['rsi_accel'] = (df['rsi14'] - 50) * df['momentumAcceleration']

        # 3. DANH SÁCH FEATURE FINAL
        feature_columns = [
            # Momentum Group
            'momentum15M', 'momentum1H', 'momentum4H', 'momentum24H',
            'momentumAcceleration',
            'trendStrengthBTC', 'trendStrengthETH',

            # Volatility Group
            'volatility15M', 'volatility1H', 'volatility24H',
            'volatilityTermStructure', # <-- Đã được tính toán ở trên

            # Market Breadth & Sentiment
            'advanceDeclineRatio', 'percentAboveMA20', 'volumeRatioUpDown',
            'marketBreadthStrength', 'btcDominance', 'volumeSpike',

            # Funding Rate
            'fundingRateRaw', 'fundingRateAvg24H', 'fundingRateTrend',

            # Time Features
            'hourOfDay', 'dayOfWeek', 'weekOfMonth', 'monthOfYear',

            # Basket Features
            'basketMomentum15M', 'basketMomentum1H', 'basketRsi14', 'basketVolSpike',

            # Interactions
            'mom15M_vol1H', 'rsi_accel'
        ]

        valid_features = [c for c in feature_columns if c in df.columns]
        if len(valid_features) < 15: return None, None

        # Chuyển đổi sang Float (Loại bỏ hoàn toàn String/Object gây lỗi)
        X = df[valid_features].replace([np.inf, -np.inf], np.nan).fillna(0).astype('float32')

        # 4. XỬ LÝ TARGET
        target_col = target_name
        if target_col not in df.columns:
            if "future" + target_col in df.columns: target_col = "future" + target_col
            elif target_col.startswith("maxDrawdown") and target_col.replace("maxDrawdown", "maxDrawdownNext") in df.columns:
                target_col = target_col.replace("maxDrawdown", "maxDrawdownNext")

        if target_col not in df.columns: return None, None

        y = df[target_col].replace([np.inf, -np.inf], np.nan)
        mask = y.notna()
        return X[mask].values, y[mask].values

    def load_data(self, data_directory, target_name):
        logger.info(f"🚀 Scanning data in {data_directory}...")
        all_files = sorted([f for f in os.listdir(data_directory) if f.endswith(".csv")])

        X_list, y_list = [], []
        files_loaded = 0

        for f in all_files:
            try:
                df = pd.read_csv(os.path.join(data_directory, f))
                if len(df) < 50: continue

                X, y = self.preprocess_data(df, target_name)

                if X is not None:
                    X_list.append(X)
                    y_list.append(y)
                    files_loaded += 1
            except Exception as e:
                if files_loaded == 0: logger.warning(f"⚠️ Error reading {f}: {str(e)}")
                pass

        if not X_list: return None, None
        X_all = np.vstack(X_list)
        y_all = np.hstack(y_list)
        logger.info(f"✅ Loaded {files_loaded} files ({len(X_all)} samples).")

        logger.info("Fitting Scaler...")
        X_scaled = self.scaler.fit_transform(X_all)
        return X_scaled, y_all

    def optimize_xgboost(self, X_train, y_train, X_valid, y_valid, n_trials):
        logger.info(f"⚡ OPTIMIZING XGBOOST ({n_trials} trials)...")
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dvalid = xgb.DMatrix(X_valid, label=y_valid)

        def objective(trial):
            params = {
                'verbosity': 0, 'objective': 'reg:squarederror', 'tree_method': 'hist', 'n_jobs': 3,
                'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
                'max_depth': trial.suggest_int('max_depth', 5, 14),
                'min_child_weight': trial.suggest_int('min_child_weight', 5, 100),
                'subsample': trial.suggest_float('subsample', 0.6, 0.95),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.95),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 10.0, log=True),
            }
            pruning_callback = optuna.integration.XGBoostPruningCallback(trial, "valid-rmse")
            model = xgb.train(params, dtrain, num_boost_round=3000, evals=[(dvalid, 'valid')],
                              early_stopping_rounds=100, verbose_eval=False, callbacks=[pruning_callback])
            return r2_score(y_valid, model.predict(dvalid))

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials)
        return study.best_params

    def train(self, target_name, data_dir, n_trials):
        X, y = self.load_data(data_dir, target_name)
        if X is None:
            logger.error(f"❌ Không load được dữ liệu cho {target_name}.")
            return

        split = int(len(X) * 0.9)
        X_train, X_test, y_train, y_test = X[:split], X[split:], y[:split], y[split:]

        best_params = self.optimize_xgboost(X_train, y_train, X_test, y_test, n_trials)

        logger.info("🔥 Training FINAL V3.5 Model (20,000 estimators)...")
        best_params['n_estimators'] = 20000
        best_params['learning_rate'] = min(best_params['learning_rate'], 0.005)
        best_params['n_jobs'] = 3

        model = xgb.XGBRegressor(**best_params)
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=1000, early_stopping_rounds=500)

        final_r2 = r2_score(y_test, model.predict(X_test))
        logger.info(f"FINAL V3.5 RESULT {target_name} -> R2: {final_r2:.4f}")

        clean_name = target_name.replace("future", "").replace("Next", "")
        if "maxDrawdown" in target_name: clean_name = target_name.replace("Next", "")

        onnx_model = convert_xgboost(model, initial_types=[('float_input', OnnxFloatTensorType([None, X.shape[1]]))])
        with open(f"{self.model_dir}/Model_Regressor_{clean_name}.onnx", "wb") as f: f.write(onnx_model.SerializeToString())

        onnx_scaler = convert_sklearn(self.scaler, initial_types=[('float_input', SklFloatTensorType([None, X.shape[1]]))])
        with open(f"{self.model_dir}/Scaler_{clean_name}.onnx", "wb") as f: f.write(onnx_scaler.SerializeToString())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--trials', type=int, default=100)
    args = parser.parse_args()
    V3_5_FinalTrainer().train(args.target, "storage/training_data_big_sequential", args.trials)