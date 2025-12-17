# -*- coding: utf-8 -*-
import os
# SET CUNG 2 CORE
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["VECLIB_MAXIMUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"

import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostRegressor
from sklearn.ensemble import VotingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score
from onnxmltools.convert import convert_xgboost, convert_lightgbm, convert_sklearn
from onnxmltools.convert.common.data_types import FloatTensorType as OnnxFloatTensorType
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType as SklFloatTensorType
import logging
import warnings
import argparse
import optuna

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class V2Trainer:
    def __init__(self, model_dir="ai_models_reg_v2"):
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

        for col in ['basketMomentum15M', 'basketMomentum1H', 'basketRsi14', 'basketVolSpike',
                    'riskAdjustedMom1H', 'basketAlpha15M', 'rsiDivergence']:
            if col in df.columns: numeric_features.append(col)

        valid_features = [c for c in numeric_features if c in df.columns and c not in ['var95_1H', 'expectedShortfall1H']]
        if not valid_features: return None, None

        X = df[valid_features].replace([np.inf, -np.inf], np.nan).fillna(0).astype('float32')

        if target_col_name not in df.columns:
            if "future" + target_col_name in df.columns: target_col_name = "future" + target_col_name
            elif target_col_name.startswith("maxDrawdown") and target_col_name.replace("maxDrawdown", "maxDrawdownNext") in df.columns:
                target_col_name = target_col_name.replace("maxDrawdown", "maxDrawdownNext")

        if target_col_name not in df.columns: return None, None
        y = df[target_col_name].replace([np.inf, -np.inf], np.nan)
        return X[y.notna()].values, y[y.notna()].values

    def load_data(self, data_directory, target_name):
        logger.info(f"Scanning data in {data_directory}...")
        all_files = sorted([f for f in os.listdir(data_directory) if f.endswith(".csv")])
        X_list, y_list = [], []
        for f in all_files:
            try:
                df = pd.read_csv(os.path.join(data_directory, f))
                if len(df) < 50: continue
                X, y = self.preprocess_data(df, target_name)
                if X is not None: X_list.append(X); y_list.append(y)
            except: pass
        if not X_list: return None, None
        X_all, y_all = np.vstack(X_list), np.hstack(y_list)
        logger.info(f"Loaded {len(X_all)} samples.")
        return self.scaler.fit_transform(X_all), y_all

    # --- OPTIMIZERS ---
    def optimize_xgb(self, X_train, y_train, X_valid, y_valid, trials):
        logger.info("Optimizing XGBoost...")
        def obj(trial):
            params = {
                'verbosity': 0, 'objective': 'reg:squarederror', 'tree_method': 'hist', 'n_jobs': 2,
                'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
                'max_depth': trial.suggest_int('max_depth', 3, 10), # Giam depth max xuong 10
                'subsample': trial.suggest_float('subsample', 0.6, 0.95),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.95),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 10.0, log=True)
            }
            model = xgb.XGBRegressor(n_estimators=2000, early_stopping_rounds=50, **params)
            model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], verbose=False)
            return r2_score(y_valid, model.predict(X_valid))

        study = optuna.create_study(direction='maximize')
        study.optimize(obj, n_trials=trials)
        return study.best_params

    def optimize_lgbm(self, X_train, y_train, X_valid, y_valid, trials):
        logger.info("Optimizing LightGBM...")
        def obj(trial):
            params = {
                'n_estimators': 2000, 'verbosity': -1, 'n_jobs': 2,
                'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
                'num_leaves': trial.suggest_int('num_leaves', 20, 100),
                'subsample': trial.suggest_float('subsample', 0.6, 0.95),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.95),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-3, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-3, 10.0, log=True)
            }
            model = lgb.LGBMRegressor(**params)
            model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], callbacks=[lgb.early_stopping(50, verbose=False)])
            return r2_score(y_valid, model.predict(X_valid))

        study = optuna.create_study(direction='maximize')
        study.optimize(obj, n_trials=trials)
        return study.best_params

    def train(self, target_name, data_dir, n_trials):
        X, y = self.load_data(data_dir, target_name)
        if X is None: return

        split = int(len(X) * 0.9)
        X_train, X_test, y_train, y_test = X[:split], X[split:], y[:split], y[split:]

        # ==========================================
        # 1. XGBOOST (OPTIMIZE & TRAIN)
        # ==========================================
        best_xgb = self.optimize_xgb(X_train, y_train, X_test, y_test, n_trials)
        logger.info(f"Best XGB Params: {best_xgb}")

        # APPLY BEST PARAMS + ULTRA SETTINGS
        final_xgb_params = best_xgb.copy()
        final_xgb_params['n_estimators'] = 8000 # Tang so cay len de hoc ky hon
        final_xgb_params['learning_rate'] = 0.005 # Ep toc do hoc cham lai
        final_xgb_params['n_jobs'] = 2
        final_xgb_params['tree_method'] = 'hist'

        logger.info("Training Final XGBoost...")
        xgb_model = xgb.XGBRegressor(**final_xgb_params)
        xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=1000, early_stopping_rounds=200)
        r2_xgb = r2_score(y_test, xgb_model.predict(X_test))

        # ==========================================
        # 2. LIGHTGBM (OPTIMIZE & TRAIN)
        # ==========================================
        best_lgbm = self.optimize_lgbm(X_train, y_train, X_test, y_test, n_trials)
        logger.info(f"Best LGBM Params: {best_lgbm}")

        final_lgbm_params = best_lgbm.copy()
        final_lgbm_params['n_estimators'] = 8000
        final_lgbm_params['learning_rate'] = 0.005
        final_lgbm_params['n_jobs'] = 2

        logger.info("Training Final LightGBM...")
        lgbm_model = lgb.LGBMRegressor(**final_lgbm_params)
        lgbm_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], callbacks=[lgb.early_stopping(200, verbose=False)])
        r2_lgbm = r2_score(y_test, lgbm_model.predict(X_test))

        # ==========================================
        # 3. CATBOOST (USE HARDCODED BUT SAFE)
        # ==========================================
        # CatBoost rat trau, kho can Optuna hon, dung safe config
        logger.info("Training Final CatBoost (Safe Config)...")
        cat_model = CatBoostRegressor(iterations=8000, learning_rate=0.005, depth=6, thread_count=2, verbose=0)
        cat_model.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=200)
        r2_cat = r2_score(y_test, cat_model.predict(X_test))

        logger.info(f"Scores -> XGB: {r2_xgb:.4f}, LGBM: {r2_lgbm:.4f}, Cat: {r2_cat:.4f}")

        # ==========================================
        # 4. ENSEMBLE
        # ==========================================
        estimators = [('xgb', xgb_model), ('lgbm', lgbm_model), ('cat', cat_model)]
        weights = [r2_xgb, r2_lgbm, r2_cat]

        valid_ests, valid_weights = [], []
        for est, w in zip(estimators, weights):
            if w > 0.01: # Chi lay model nao co R2 > 1%
                valid_ests.append(est); valid_weights.append(w)

        if not valid_ests:
            logger.warning("All models failed R2 check. Using fallback.")
            valid_ests, valid_weights = estimators, [1.0, 1.0, 1.0]

        total = sum(valid_weights)
        norm_weights = [w/total for w in valid_weights]
        logger.info(f"Ensemble Weights: {norm_weights}")

        # Remove early stopping param to avoid VotingRegressor crash
        for name, model in valid_ests:
            try: model.set_params(early_stopping_rounds=None)
            except: pass

        ensemble = VotingRegressor(estimators=valid_ests, weights=norm_weights, n_jobs=1)
        ensemble.fit(X_train, y_train)

        final_r2 = r2_score(y_test, ensemble.predict(X_test))
        logger.info(f"FINAL V2 ENSEMBLE {target_name} -> R2: {final_r2:.4f}")

        # EXPORT
        clean_name = target_name.replace("future", "").replace("Next", "")
        if "maxDrawdown" in target_name: clean_name = target_name.replace("Next", "")

        initial_type = [('float_input', OnnxFloatTensorType([None, X.shape[1]]))]

        with open(f"{self.model_dir}/Model_Regressor_{clean_name}_XGB.onnx", "wb") as f:
            f.write(convert_xgboost(xgb_model, initial_types=initial_type).SerializeToString())
        with open(f"{self.model_dir}/Model_Regressor_{clean_name}_LGBM.onnx", "wb") as f:
            f.write(convert_lightgbm(lgbm_model, initial_types=initial_type).SerializeToString())
        with open(f"{self.model_dir}/Weights_{clean_name}.txt", "w") as f:
            f.write("\n".join([str(w) for w in norm_weights]))
        skl_type = [('float_input', SklFloatTensorType([None, X.shape[1]]))]
        with open(f"{self.model_dir}/Scaler_{clean_name}.onnx", "wb") as f:
            f.write(convert_sklearn(self.scaler, initial_types=skl_type).SerializeToString())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--trials', type=int, default=50)
    args = parser.parse_args()

    trainer = V2Trainer()
    trainer.train(args.target, "storage/training_data_big_sequential", args.trials)