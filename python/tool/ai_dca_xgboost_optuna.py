# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score, roc_auc_score
from onnxmltools.convert import convert_xgboost, convert_sklearn
from onnxmltools.convert.common.data_types import FloatTensorType as OnnxFloatTensorType
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType as SklFloatTensorType
import logging
import warnings
import gc
import argparse
import optuna

# --- CẤU HÌNH SỐ LUỒNG (CORE) TẠI ĐÂY ---
N_JOBS = 2  # <--- Sửa thành 2 ở đây

os.environ["OMP_NUM_THREADS"] = str(N_JOBS)
os.environ["OPENBLAS_NUM_THREADS"] = str(N_JOBS)
os.environ["MKL_NUM_THREADS"] = str(N_JOBS)

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class DcaTrainer:
    def __init__(self, model_dir="ai_models_dca_v1"):
        self.model_dir = model_dir
        self.scaler = StandardScaler()
        os.makedirs(model_dir, exist_ok=True)

    def preprocess_data(self, df, target_col_name):
        # ... (Giữ nguyên phần này) ...
        # --- FEATURE LIST DCA (UPDATED) ---
        feature_columns = [
            'currentDrawdown', 'lossVelocity1H',
            'dcaImpactRatio',
            'instantAlpha', 'recoveryElasticity', 'dangerIndex',
            'crashVelocity', 'globalRateDownAvg', 'fundingRate',
            'btcMomentum15M', 'btcMomentum1H', 'btcMomentum4H', 'btcMomentum24H',
            'btcMomentumAcceleration', 'ethTrendStrength',
            'rsi1H', 'volumeAnomaly', 'distFromLow24H', 'maxRateChange60M'
        ]

        valid_features = [c for c in feature_columns if c in df.columns]
        if len(valid_features) < len(feature_columns) * 0.8:
            return None, None

        X = df[valid_features].replace([np.inf, -np.inf], np.nan).fillna(0).astype('float32')

        if target_col_name not in df.columns:
            return None, None

        y = df[target_col_name].replace([np.inf, -np.inf], np.nan)
        valid_mask = y.notna()
        return X[valid_mask].values, y[valid_mask].values

    def load_data(self, data_directory, target_name, max_files=0):
        # ... (Giữ nguyên phần này) ...
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
        logger.info(f"✅ Loaded TOTAL: {len(X_all)} samples.")
        logger.info("Fitting Scaler...")
        X_scaled = self.scaler.fit_transform(X_all)
        return X_scaled, y_all

    def optimize_xgboost(self, X_train, y_train, X_valid, y_valid, n_trials, is_classification):
        model_type = "CLASSIFICATION" if is_classification else "REGRESSION"
        logger.info(f"OPTIMIZING DCA XGBOOST ({model_type}) - {n_trials} trials...")

        dtrain = xgb.DMatrix(X_train, label=y_train)
        dvalid = xgb.DMatrix(X_valid, label=y_valid)

        def objective(trial):
            params = {
                'verbosity': 0,
                'tree_method': 'hist',
                'n_jobs': N_JOBS,  # <--- SỬA: Dùng biến N_JOBS
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
                'max_depth': trial.suggest_int('max_depth', 4, 10),
                'min_child_weight': trial.suggest_int('min_child_weight', 10, 200),
                'subsample': trial.suggest_float('subsample', 0.6, 0.9),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.9),
                'reg_alpha': trial.suggest_float('reg_alpha', 1e-2, 10.0, log=True),
                'reg_lambda': trial.suggest_float('reg_lambda', 1e-2, 10.0, log=True),
            }

            if is_classification:
                params['objective'] = 'binary:logistic'
                params['eval_metric'] = 'auc'
            else:
                params['objective'] = 'reg:squarederror'
                params['eval_metric'] = 'rmse'

            pruning_callback = optuna.integration.XGBoostPruningCallback(trial, "valid-" + params['eval_metric'])

            model = xgb.train(params, dtrain, num_boost_round=2000,
                              evals=[(dvalid, 'valid')],
                              early_stopping_rounds=50,
                              verbose_eval=False,
                              callbacks=[pruning_callback])

            preds = model.predict(dvalid)

            if is_classification:
                return roc_auc_score(y_valid, preds)
            else:
                return r2_score(y_valid, preds)

        study = optuna.create_study(direction="maximize")
        study.optimize(objective, n_trials=n_trials)
        logger.info(f"Best Params: {study.best_params}")
        return study.best_params

    def train(self, target_name, data_dir, n_trials):
        is_classification = "Recoverable" in target_name

        X, y = self.load_data(data_dir, target_name)
        if X is None: return

        split = int(len(X) * 0.9)
        X_train, X_test, y_train, y_test = X[:split], X[split:], y[:split], y[split:]

        # 1. TÌM THAM SỐ
        best_params = self.optimize_xgboost(X_train, y_train, X_test, y_test, n_trials, is_classification)

        # 2. TRAIN FINAL
        logger.info("Training FINAL DCA Model...")
        best_params['n_estimators'] = 5000
        best_params['learning_rate'] = max(0.005, best_params['learning_rate'] * 0.8)
        best_params['n_jobs'] = N_JOBS # <--- SỬA: Dùng biến N_JOBS

        if is_classification:
            model = xgb.XGBClassifier(**best_params)
            eval_metric = "auc"
        else:
            model = xgb.XGBRegressor(**best_params)
            eval_metric = "rmse"

        model.fit(X_train, y_train,
                  eval_set=[(X_test, y_test)],
                  eval_metric=eval_metric,
                  verbose=500,
                  early_stopping_rounds=200)

        # 3. ĐÁNH GIÁ
        preds = model.predict(X_test)
        if is_classification:
            preds_proba = model.predict_proba(X_test)[:, 1]
            auc = roc_auc_score(y_test, preds_proba)
            acc = accuracy_score(y_test, preds)
            logger.info(f"FINAL RESULT {target_name} -> AUC: {auc:.4f} | ACC: {acc:.4f}")
        else:
            r2 = r2_score(y_test, preds)
            mae = mean_absolute_error(y_test, preds)
            logger.info(f"FINAL RESULT {target_name} -> R2: {r2:.4f} | MAE: {mae:.6f}")

        # 4. EXPORT
        clean_name = target_name.replace("label", "")

        onnx_model = convert_xgboost(model, initial_types=[('float_input', OnnxFloatTensorType([None, X.shape[1]]))])
        with open(f"{self.model_dir}/Model_DCA_{clean_name}.onnx", "wb") as f:
            f.write(onnx_model.SerializeToString())

        onnx_scaler = convert_sklearn(self.scaler, initial_types=[('float_input', SklFloatTensorType([None, X.shape[1]]))])
        with open(f"{self.model_dir}/Scaler_DCA_{clean_name}.onnx", "wb") as f:
            f.write(onnx_scaler.SerializeToString())

        logger.info(f"✅ Model saved to {self.model_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True, default="labelIsRecoverable3D")
    parser.add_argument('--trials', type=int, default=100) # <--- Đã sửa thành 100
    parser.add_argument('--dir', type=str, default="storage/training_data_dca_2m_smart")
    args = parser.parse_args()

    trainer = DcaTrainer()
    trainer.train(args.target, args.dir, args.trials)

