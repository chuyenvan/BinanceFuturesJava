# -*- coding: utf-8 -*-
import os
# SET CUNG TRONG CODE LUON CHO CHAC
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["VECLIB_MAXIMUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
from onnxmltools.convert import convert_xgboost, convert_sklearn
from onnxmltools.convert.common.data_types import FloatTensorType as OnnxFloatTensorType
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType as SklFloatTensorType
import logging
import warnings
import gc
import argparse
import optuna

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class V1Trainer:
    def __init__(self, model_dir="ai_models_reg_v1"):
        self.model_dir = model_dir
        self.scaler = StandardScaler()
        os.makedirs(model_dir, exist_ok=True)

    def preprocess_data(self, df, target_col_name):
        feature_columns = [
            'momentum1M', 'momentum5M', 'momentum15M', 'momentum1H', 'momentum4H', 'momentum24H',
            'momentumAcceleration', 'trendStrengthBTC', 'trendStrengthETH', 'trendConsistency',
            'volatility1M', 'volatility15M', 'volatility1H', 'volatility24H', 'volatilityTermStructure',
            'volatilityRegime',
            'advanceDeclineRatio', 'percentAboveMA20', 'volumeRatioUpDown', 'marketBreadthStrength', 'btcDominance',
            'rsi14', 'volumeSpike', 'distMA20',
            'fundingRateRaw', 'fundingRateAvg24H', 'fundingRateTrend',
            'hourOfDay', 'dayOfWeek', 'weekOfMonth', 'monthOfYear'
        ]

        numeric_features = [f for f in feature_columns if f not in ['volatilityRegime', 'marketRegime', 'regimeLabel']]

        potential_new_cols = ['basketMomentum15M', 'basketMomentum1H', 'basketRsi14', 'basketVolSpike']
        for col in potential_new_cols:
            if col in df.columns: numeric_features.append(col)

        valid_features = [c for c in numeric_features if c in df.columns]
        valid_features = [c for c in valid_features if c not in ['var95_1H', 'expectedShortfall1H']]

        if not valid_features: return None, None

        X = df[valid_features].replace([np.inf, -np.inf], np.nan).fillna(0).astype('float32')

        if target_col_name not in df.columns:
            if "future" + target_col_name in df.columns: target_col_name = "future" + target_col_name
            elif "maxDrawdownNext" + target_col_name.replace("maxDrawdown", "") in df.columns: pass
            elif target_col_name.startswith("maxDrawdown") and target_col_name.replace("maxDrawdown", "maxDrawdownNext") in df.columns:
                target_col_name = target_col_name.replace("maxDrawdown", "maxDrawdownNext")

        if target_col_name not in df.columns: return None, None
        y = df[target_col_name].replace([np.inf, -np.inf], np.nan)

        valid_mask = y.notna()
        return X[valid_mask].values, y[valid_mask].values

    def load_data(self, data_directory, target_name, max_files=0):
        logger.info(f"Scanning data in {data_directory}...")
        all_files = sorted([f for f in os.listdir(data_directory) if f.endswith(".csv")])
        if max_files > 0: all_files = all_files[:max_files]

        X_list, y_list = [], []
        for i, filename in enumerate(all_files):
            try:
                df = pd.read_csv(os.path.join(data_directory, filename))
                if len(df) < 50: continue
                X, y = self.preprocess_data(df, target_name)
                if X is not None:
                    X_list.append(X)
                    y_list.append(y)
            except: pass

        if not X_list: return None, None
        X_all = np.vstack(X_list)
        y_all = np.hstack(y_list)
        logger.info(f"Loaded {len(X_all)} samples.")

        logger.info("Fitting Scaler...")
        X_scaled = self.scaler.fit_transform(X_all)
        return X_scaled, y_all

    def optimize_xgboost(self, X_train, y_train, X_valid, y_valid, n_trials):
        logger.info(f"OPTIMIZING V1 XGBOOST ({n_trials} trials)...")
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dvalid = xgb.DMatrix(X_valid, label=y_valid)

        def objective(trial):
            params = {
                'verbosity': 0,
                'objective': 'reg:squarederror',
                'tree_method': 'hist',
                'n_jobs': 2, # <--- DA SUA THANH 2
                'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
                'max_depth': trial.suggest_int('max_depth', 5, 15),
                'min_child_weight': trial.suggest_int('min_child_weight', 5, 100),
                'subsample': trial.suggest_float('subsample', 0.6, 0.95),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.95),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 10.0, log=True),
            }
            pruning_callback = optuna.integration.XGBoostPruningCallback(trial, "valid-rmse")
            model = xgb.train(params, dtrain, num_boost_round=5000, evals=[(dvalid, 'valid')],
                              early_stopping_rounds=100, verbose_eval=False, callbacks=[pruning_callback])
            return r2_score(y_valid, model.predict(dvalid))

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials)
        return study.best_params

    def train(self, target_name, data_dir, n_trials):
        X, y = self.load_data(data_dir, target_name)
        if X is None: return

        split = int(len(X) * 0.9)
        X_train, X_test, y_train, y_test = X[:split], X[split:], y[:split], y[split:]

        best_params = self.optimize_xgboost(X_train, y_train, X_test, y_test, n_trials)

        logger.info("Training FINAL V1 Model (High Estimators)...")
        best_params['n_estimators'] = 12000
        best_params['learning_rate'] = min(best_params['learning_rate'], 0.005)
        best_params['n_jobs'] = 2 # <--- DA SUA THANH 2

        model = xgb.XGBRegressor(**best_params)
        model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=1000, early_stopping_rounds=500)

        r2 = r2_score(y_test, model.predict(X_test))
        logger.info(f"FINAL V1 RESULT {target_name} -> R2: {r2:.4f}")

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

    trainer = V1Trainer()
    trainer.train(args.target, "storage/training_data_big_sequential", args.trials)