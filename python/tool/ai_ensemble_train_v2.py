# -*- coding: utf-8 -*-
import os
# Limit Cores to 4
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.ensemble import VotingRegressor
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
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import lightgbm as lgb
    from onnxmltools.convert import convert_lightgbm
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False

try:
    from catboost import CatBoostRegressor
    HAS_CAT = True
except ImportError:
    HAS_CAT = False

warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.StreamHandler()])
logger = logging.getLogger(__name__)

class SuperEnsembleTrainer:
    def __init__(self, model_dir="ai_models_reg_final"):
        self.model_dir = model_dir
        self.scaler = StandardScaler()
        os.makedirs(model_dir, exist_ok=True)
        logger.info(f"Models will be saved to: {self.model_dir}")

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

        potential_new_cols = ['basketMomentum15M', 'basketMomentum1H', 'basketRsi14', 'basketVolSpike',
                              'riskAdjustedMom1H', 'basketAlpha15M', 'rsiDivergence']
        for col in potential_new_cols:
            if col in df.columns: numeric_features.append(col)

        valid_features = [c for c in numeric_features if c in df.columns]
        valid_features = [c for c in valid_features if c not in ['var95_1H', 'expectedShortfall1H']]

        if not valid_features: return None, None

        X = df[valid_features].replace([np.inf, -np.inf], np.nan).fillna(0).astype('float32')
        if target_col_name not in df.columns: return None, None
        y = df[target_col_name].replace([np.inf, -np.inf], np.nan)
        valid_mask = y.notna()
        return X[valid_mask].values, y[valid_mask].values

    def load_data_fast(self, data_directory, target_name, max_files=0):
        logger.info(f"Scanning data in {data_directory}...")
        all_files = sorted([os.path.join(data_directory, f) for f in os.listdir(data_directory) if f.endswith(".csv")])
        if max_files > 0: all_files = all_files[:max_files]

        X_list, y_list = [], []

        def load_single(fp):
            try:
                df = pd.read_csv(fp)
                if len(df) == 0: return None, None
                return self.preprocess_data(df, target_name)
            except: return None, None

        with ThreadPoolExecutor(max_workers=16) as executor:
            future_to_file = {executor.submit(load_single, f): f for f in all_files}
            for future in as_completed(future_to_file):
                X_chunk, y_chunk = future.result()
                if X_chunk is not None:
                    X_list.append(X_chunk)
                    y_list.append(y_chunk)

        if not X_list: return None, None
        logger.info("Concatenating...")
        X_all = np.vstack(X_list)
        y_all = np.hstack(y_list)
        del X_list, y_list; gc.collect()

        logger.info("Fitting Scaler...")
        X_scaled = self.scaler.fit_transform(X_all)
        return X_scaled, y_all

    # --- OPTIMIZE LIGHTGBM (SMART MODE) ---
    def optimize_lightgbm(self, X_train, y_train, X_valid, y_valid, n_trials=30):
        logger.info(f"TUNING LIGHTGBM (SMART MODE - {n_trials} TRIALS)...")
        best_r2 = -float('inf')
        best_params = {}

        for i in range(n_trials):
            params = {
                'n_estimators': 2500,
                'learning_rate': 10 ** np.random.uniform(np.log10(0.01), np.log10(0.1)),
                'num_leaves': np.random.randint(30, 120),
                'max_depth': np.random.randint(5, 12),
                'subsample': np.random.uniform(0.6, 0.9),
                'colsample_bytree': np.random.uniform(0.6, 0.9),
                'reg_alpha': 10 ** np.random.uniform(-2, 1),
                'reg_lambda': 10 ** np.random.uniform(-2, 1),
                'n_jobs': 4, 'random_state': 42, 'verbosity': -1
            }

            try:
                model = lgb.LGBMRegressor(**params)
                model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)],
                          eval_metric='l2', callbacks=[lgb.early_stopping(50, verbose=False)])

                preds = model.predict(X_valid)
                r2 = r2_score(y_valid, preds)

                if r2 > best_r2:
                    best_r2 = r2
                    best_params = params
                    logger.info(f"LGBM Trial {i}: New Best R2: {r2:.4f}")
            except Exception as e:
                pass

        return best_params

    # --- OPTIMIZE CATBOOST (SMART MODE) ---
    def optimize_catboost(self, X_train, y_train, X_valid, y_valid, n_trials=30):
        logger.info(f"TUNING CATBOOST (SMART MODE - {n_trials} TRIALS)...")
        best_r2 = -float('inf')
        best_params = {}

        for i in range(n_trials):
            params = {
                'iterations': 2500,
                'learning_rate': 10 ** np.random.uniform(np.log10(0.01), np.log10(0.1)),
                'depth': np.random.randint(4, 10),
                'l2_leaf_reg': np.random.randint(1, 10),
                'subsample': np.random.uniform(0.6, 0.9),
                'thread_count': 4, 'random_state': 42, 'verbose': 0, 'allow_writing_files': False
            }

            try:
                model = CatBoostRegressor(**params)
                model.fit(X_train, y_train, eval_set=(X_valid, y_valid), early_stopping_rounds=50)

                preds = model.predict(X_valid)
                r2 = r2_score(y_valid, preds)

                if r2 > best_r2:
                    best_r2 = r2
                    best_params = params
                    logger.info(f"CatBoost Trial {i}: New Best R2: {r2:.4f}")
            except Exception as e:
                pass

        return best_params

    def train_super_ensemble(self, X, y, target_name, optimize=True):
        split = int(len(X) * 0.9)
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]

        # --- 1. XGBOOST ULTRA ---
        xgb_params = {
            'n_estimators': 15000,
            'learning_rate': 0.005,
            'max_depth': 10,
            'min_child_weight': 5,
            'subsample': 0.75,
            'colsample_bytree': 0.75,
            'reg_alpha': 0.1,
            'reg_lambda': 5.0,
            'n_jobs': 4,
            'tree_method': 'hist',
            'random_state': 42,
            'early_stopping_rounds': 100
        }

        logger.info("Training XGBoost (Ultra Deep)...")
        xgb_model = xgb.XGBRegressor(**xgb_params)
        xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
        r2_xgb = r2_score(y_test, xgb_model.predict(X_test))
        logger.info(f"XGBoost Ultra R2: {r2_xgb:.4f}")

        # --- 2. LIGHTGBM ---
        lgbm_model = None
        if HAS_LGBM:
            if optimize:
                best_params = self.optimize_lightgbm(X_train, y_train, X_test, y_test, n_trials=30)
                if best_params:
                    logger.info("Upgrading LightGBM params to Ultra Mode...")
                    best_params['n_estimators'] = 15000
                    best_params['learning_rate'] = 0.005
                    lgbm_params = best_params
                else:
                    lgbm_params = {'n_estimators': 15000, 'learning_rate': 0.005, 'n_jobs': 4}
            else:
                lgbm_params = {'n_estimators': 15000, 'learning_rate': 0.005, 'n_jobs': 4}

            logger.info("Training LightGBM (Final Ultra Fit)...")
            lgbm_model = lgb.LGBMRegressor(**lgbm_params)
            lgbm_model.fit(X_train, y_train, eval_set=[(X_test, y_test)],
                           callbacks=[lgb.early_stopping(200, verbose=False)])
            r2_lgbm = r2_score(y_test, lgbm_model.predict(X_test))
            logger.info(f"LightGBM Ultra R2: {r2_lgbm:.4f}")

        # --- 3. CATBOOST ---
        cat_model = None
        if HAS_CAT:
            if optimize:
                best_params = self.optimize_catboost(X_train, y_train, X_test, y_test, n_trials=30)
                if best_params:
                    logger.info("Upgrading CatBoost params to Ultra Mode...")
                    best_params['iterations'] = 15000
                    best_params['learning_rate'] = 0.005
                    cat_params = best_params
                else:
                    cat_params = {'iterations': 15000, 'learning_rate': 0.005, 'thread_count': 4, 'verbose': 0}
            else:
                cat_params = {'iterations': 15000, 'learning_rate': 0.005, 'thread_count': 4, 'verbose': 0}

            logger.info("Training CatBoost (Final Ultra Fit)...")
            cat_model = CatBoostRegressor(**cat_params)
            cat_model.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=200)
            r2_cat = r2_score(y_test, cat_model.predict(X_test))
            logger.info(f"CatBoost Ultra R2: {r2_cat:.4f}")

        # --- 4. ENSEMBLE ---
        estimators = [('xgb', xgb_model)]
        weights = [r2_xgb]

        if lgbm_model is not None:
            estimators.append(('lgbm', lgbm_model))
            weights.append(r2_lgbm)
        if cat_model is not None:
            estimators.append(('cat', cat_model))
            weights.append(r2_cat)

        final_estimators = []
        final_weights = []
        for est, w in zip(estimators, weights):
            if w > 0:
                final_estimators.append(est)
                final_weights.append(w)

        if not final_estimators:
            final_estimators = estimators
            final_weights = weights

        total_weight = sum(final_weights)
        if total_weight > 0:
            final_weights = [w / total_weight for w in final_weights]

        logger.info(f"Ensembling with Weights: {final_weights}")

        # --- [FIX BUG] REMOVE EARLY STOPPING BEFORE VOTING REGRESSOR ---
        # VotingRegressor se fit lai, ma khong co eval_set, nen se crash neu con early_stopping_rounds
        logger.info("Preparing models for Voting (Disabling early stopping)...")

        # Fix cho XGBoost (Quan trong nhat)
        try:
            # Set early_stopping_rounds = None de tranh loi AssertionError
            # Set n_estimators = best_iteration de no khong chay du 15000 vong neu da dung som
            if hasattr(xgb_model, 'best_iteration') and xgb_model.best_iteration is not None:
                 xgb_model.set_params(n_estimators=xgb_model.best_iteration)
            xgb_model.set_params(early_stopping_rounds=None)
        except:
            pass

        # Fix cho LightGBM
        if lgbm_model is not None:
            try:
                # LGBM thuc ra truyen early_stopping qua fit(), nhung safety first
                lgbm_model.set_params(n_estimators=lgbm_model.best_iteration_)
            except:
                pass

        # Fix cho CatBoost
        if cat_model is not None:
            try:
                # CatBoost hoi khac, nhung VotingRegressor thuong khong refit sau, no clone params
                # O day ta set truc tiep vao estimators
                pass
            except:
                pass

        # Tao ensemble
        ensemble = VotingRegressor(estimators=final_estimators, weights=final_weights, n_jobs=1)
        ensemble.fit(X_train, y_train)

        final_preds = ensemble.predict(X_test)
        final_r2 = r2_score(y_test, final_preds)
        final_mae = mean_absolute_error(y_test, final_preds)

        logger.info(f"FINAL ENSEMBLE RESULT {target_name} -> R2: {final_r2:.4f}, MAE: {final_mae:.5f}")

        # EXPORT
        clean_name = target_name.replace("future", "").replace("Next", "")
        initial_type = [('float_input', OnnxFloatTensorType([None, X_train.shape[1]]))]

        logger.info("Exporting Models...")
        onnx_xgb = convert_xgboost(xgb_model, initial_types=initial_type)
        with open(f"{self.model_dir}/Model_Regressor_{clean_name}_XGB.onnx", "wb") as f: f.write(onnx_xgb.SerializeToString())

        if lgbm_model is not None:
            onnx_lgbm = convert_lightgbm(lgbm_model, initial_types=initial_type)
            with open(f"{self.model_dir}/Model_Regressor_{clean_name}_LGBM.onnx", "wb") as f: f.write(onnx_lgbm.SerializeToString())

        if cat_model is not None:
            cat_model.save_model(f"{self.model_dir}/Model_Regressor_{clean_name}_Cat.onnx", format="onnx")

        initial_type_skl = [('float_input', SklFloatTensorType([None, X_train.shape[1]]))]
        onnx_scaler = convert_sklearn(self.scaler, initial_types=initial_type_skl)
        with open(f"{self.model_dir}/Scaler_{clean_name}.onnx", "wb") as f: f.write(onnx_scaler.SerializeToString())

        with open(f"{self.model_dir}/Model_Regressor_{clean_name}.onnx", "wb") as f: f.write(onnx_xgb.SerializeToString())

        with open(f"{self.model_dir}/Weights_{clean_name}.txt", "w") as f:
            f.write("\n".join([str(w) for w in final_weights]))

        logger.info("ALL DONE.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', default='storage/training_data_big_sequential')
    parser.add_argument('--model-dir', default='ai_models_reg_final')
    parser.add_argument('--target', type=str, required=True)
    parser.add_argument('--max-files', type=int, default=0)
    args = parser.parse_args()

    trainer = SuperEnsembleTrainer(model_dir=args.model_dir)
    X, y = trainer.load_data_fast(args.data_dir, args.target, args.max_files)
    if X is not None:
        trainer.train_super_ensemble(X, y, args.target)

if __name__ == "__main__":
    main()
