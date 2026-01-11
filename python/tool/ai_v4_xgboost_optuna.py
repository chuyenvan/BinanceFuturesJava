# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
from onnxmltools.convert import convert_xgboost, convert_sklearn
from onnxmltools.convert.common.data_types import FloatTensorType as OnnxFloatTensorType
from skl2onnx.common.data_types import FloatTensorType as SklFloatTensorType
from skl2onnx import convert_sklearn
import logging
import warnings
import argparse
import optuna

# GIỚI HẠN TÀI NGUYÊN
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class V8Trainer:
    def __init__(self, model_dir="ai_models_tuned_v8"):
        self.model_dir = model_dir
        self.scaler = StandardScaler()
        os.makedirs(model_dir, exist_ok=True)

    def add_interaction_features(self, df):
        """Giữ nguyên vũ khí hạng nặng của V8"""
        df['mom15M_vol1H'] = df['momentum15M'] * df['volatility1H']
        if 'basketMomentum15M' in df.columns:
            df['relative_mom15M'] = df['basketMomentum15M'] - df['momentum15M']
        df['rsi_accel'] = (100 - df.get('rsi14', 50)) * df['momentumAcceleration']
        return df

    def preprocess_data(self, df, target_col_name):
        df = self.add_interaction_features(df)
        feature_columns = [
            'momentum1M', 'momentum5M', 'momentum15M', 'momentum1H', 'momentum4H', 'momentum24H',
            'momentumAcceleration', 'trendStrengthBTC', 'volatility1M', 'volatility15M',
            'volatility1H', 'volatility24H', 'rsi14', 'volumeSpike', 'distMA20',
            'hourOfDay', 'dayOfWeek', 'basketMomentum15M', 'basketVolSpike',
            'mom15M_vol1H', 'relative_mom15M', 'rsi_accel'
        ]
        valid_features = [c for c in feature_columns if c in df.columns]
        X = df[valid_features].replace([np.inf, -np.inf], np.nan).fillna(0).astype('float32')

        if target_col_name not in df.columns:
            if "future" + target_col_name in df.columns: target_col_name = "future" + target_col_name

        y = df[target_col_name].replace([np.inf, -np.inf], np.nan)
        valid_mask = y.notna()
        return X[valid_mask].values, y[valid_mask].values

    def train(self, target_name, data_dir, n_trials):
        X_list, y_list = [], []
        all_files = sorted([f for f in os.listdir(data_dir) if f.endswith(".csv")])
        logger.info(f"Loading {len(all_files)} files...")
        for f in all_files:
            try:
                df = pd.read_csv(os.path.join(data_dir, f))
                X_tmp, y_tmp = self.preprocess_data(df, target_name)
                if X_tmp is not None: X_list.append(X_tmp); y_list.append(y_tmp)
            except: pass
        X_all = np.vstack(X_list); y_all = np.hstack(y_list)
        X_scaled = self.scaler.fit_transform(X_all)

        split = int(len(X_scaled) * 0.9)
        X_train, X_test = X_scaled[:split], X_scaled[split:]
        y_train, y_test = y_all[:split], y_all[split:]

        # --- OPTUNA V8.3: ALIGN WITH V3 SUCCESS ---
        def objective(trial):
            params = {
                'objective': 'reg:squarederror',
                'tree_method': 'hist',
                'n_jobs': 2,
                'n_estimators': 3000, # Tăng cây để bù cho LR thấp
                # VÙNG THAM SỐ CỦA V3 (Success Zone)
                'learning_rate': trial.suggest_float('learning_rate', 0.003, 0.02, log=True), # LR Thấp
                'max_depth': trial.suggest_int('max_depth', 10, 16), # Cây Sâu
                'subsample': trial.suggest_float('subsample', 0.8, 0.95), # Tin tưởng dữ liệu
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.9),
                'min_child_weight': trial.suggest_int('min_child_weight', 5, 50),
                # Regularization nhẹ như V3
                'reg_alpha': trial.suggest_float('reg_alpha', 0.001, 1.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.001, 1.0, log=True),
            }
            model = xgb.XGBRegressor(**params)
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)], early_stopping_rounds=100, verbose=False)
            return r2_score(y_test, model.predict(X_test))

        logger.info("OPTIMIZING V8.3 (V3 LEGACY MODE)...")
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials)

        # 3. FINAL TRAIN (CÔNG THỨC 0.3)
        logger.info("Training FINAL Tuned Model (20k estimators, lr=0.005)...")
        best_params = study.best_params
        best_params['n_estimators'] = 20000
        best_params['learning_rate'] = 0.005 # Ép cứng theo V3
        best_params['n_jobs'] = 2

        model = xgb.XGBRegressor(**best_params)
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=1000, early_stopping_rounds=500)

        # 4. EXPORT ONNX
        clean_name = target_name.replace("future", "")
        onnx_model = convert_xgboost(model, initial_types=[('float_input', OnnxFloatTensorType([None, X_all.shape[1]]))])
        with open(f"{self.model_dir}/Model_Regressor_{clean_name}.onnx", "wb") as f:
            f.write(onnx_model.SerializeToString())

        onnx_scaler = convert_sklearn(self.scaler, initial_types=[('float_input', SklFloatTensorType([None, X_all.shape[1]]))])
        with open(f"{self.model_dir}/Scaler_{clean_name}.onnx", "wb") as f:
            f.write(onnx_scaler.SerializeToString())

        logger.info(f"🏆 FINAL R2: {r2_score(y_test, model.predict(X_test)):.4f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--trials', type=int, default=100)
    args = parser.parse_args()
    V8Trainer().train(args.target, "storage/training_data_big_sequential", args.trials)