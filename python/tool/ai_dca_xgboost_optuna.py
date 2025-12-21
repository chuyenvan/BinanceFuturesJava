# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error
from onnxmltools.convert import convert_xgboost, convert_sklearn
from onnxmltools.convert.common.data_types import FloatTensorType as OnnxFloatTensorType
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType as SklFloatTensorType
import logging
import argparse
import optuna

N_JOBS = 2
os.environ["OMP_NUM_THREADS"] = str(N_JOBS)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class DcaRiskTrainer:
    def __init__(self, model_dir="ai_models_dca_risk"):
        self.model_dir = model_dir
        self.scaler = StandardScaler()
        os.makedirs(model_dir, exist_ok=True)

    def preprocess_data(self, df):
        # --- FEATURE INPUT (18 Features) ---
        # GIỮ: currentDrawdown, lossVelocity1H (Để biết ngữ cảnh vị thế)
        # BỎ: dcaImpactRatio (Tuyệt đối không cho AI biết tiền nạp)
        feature_columns = [
            'currentDrawdown', 'lossVelocity1H', # <--- GIỮ LẠI
            # 'dcaImpactRatio',  <--- ĐÃ BỎ
            'instantAlpha', 'recoveryElasticity', 'dangerIndex',
            'crashVelocity', 'globalRateDownAvg', 'fundingRate',
            'btcMomentum15M', 'btcMomentum1H', 'btcMomentum4H', 'btcMomentum24H',
            'btcMomentumAcceleration', 'ethTrendStrength',
            'rsi1H', 'volumeAnomaly', 'distFromLow24H', 'maxRateChange60M'
        ]

        target_col = 'labelMaxDropFromNow' # <--- TARGET MỚI

        # Check features
        valid_features = [c for c in feature_columns if c in df.columns]
        if len(valid_features) < len(feature_columns): return None, None

        X = df[valid_features].replace([np.inf, -np.inf], np.nan).fillna(0).astype('float32')

        if target_col not in df.columns: return None, None
        y = df[target_col].replace([np.inf, -np.inf], np.nan)

        return X.values, y.values

    def load_data(self, data_directory):
        logger.info(f"Scanning data in {data_directory}...")
        all_files = sorted([f for f in os.listdir(data_directory) if f.endswith(".csv")])

        X_list, y_list = [], []
        for f in all_files:
            try:
                df = pd.read_csv(os.path.join(data_directory, f))
                if len(df) < 50: continue
                X, y = self.preprocess_data(df)
                if X is not None:
                    X_list.append(X)
                    y_list.append(y)
            except: pass

        if not X_list: return None, None
        X_all = np.vstack(X_list)
        y_all = np.hstack(y_list)
        logger.info(f"✅ Loaded TOTAL: {len(X_all)} samples.")

        X_scaled = self.scaler.fit_transform(X_all)
        return X_scaled, y_all

    def train(self, data_dir, n_trials=50):
        X, y = self.load_data(data_dir)
        if X is None: return

        # Split 90/10
        split = int(len(X) * 0.9)
        X_train, X_test, y_train, y_test = X[:split], X[split:], y[:split], y[split:]

        # Optuna Optimize
        def objective(trial):
            params = {
                'verbosity': 0, 'objective': 'reg:squarederror', 'tree_method': 'hist', 'n_jobs': N_JOBS,
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
                'max_depth': trial.suggest_int('max_depth', 5, 10),
                'min_child_weight': trial.suggest_int('min_child_weight', 20, 200),
                'subsample': trial.suggest_float('subsample', 0.6, 0.9),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.9),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.1, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 10.0, log=True),
            }
            model = xgb.XGBRegressor(**params, n_estimators=1000, early_stopping_rounds=50)
            model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
            return r2_score(y_test, model.predict(X_test))

        logger.info("Running Optuna...")
        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials)

        # Train Final
        best_params = study.best_params
        best_params.update({'n_estimators': 3000, 'n_jobs': N_JOBS, 'objective': 'reg:squarederror'})

        logger.info("Training Final Risk Model...")
        model = xgb.XGBRegressor(**best_params)
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=500, early_stopping_rounds=100)

        preds = model.predict(X_test)
        logger.info(f"🚀 FINAL R2: {r2_score(y_test, preds):.4f} | MAE: {mean_absolute_error(y_test, preds):.6f}")

        # Export ONNX
        initial_type = [('float_input', OnnxFloatTensorType([None, X.shape[1]]))]
        onnx_model = convert_xgboost(model, initial_types=initial_type)
        with open(f"{self.model_dir}/Model_DCA_MaxDrop.onnx", "wb") as f: f.write(onnx_model.SerializeToString())

        initial_type_scaler = [('float_input', SklFloatTensorType([None, X.shape[1]]))]
        onnx_scaler = convert_sklearn(self.scaler, initial_types=initial_type_scaler)
        with open(f"{self.model_dir}/Scaler_DCA_MaxDrop.onnx", "wb") as f: f.write(onnx_scaler.SerializeToString())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', type=str, required=True)
    args = parser.parse_args()
    DcaRiskTrainer().train(args.dir)