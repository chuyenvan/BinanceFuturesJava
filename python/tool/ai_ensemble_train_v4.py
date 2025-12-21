# -*- coding: utf-8 -*-
import os
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
import gc

# CẤU HÌNH TÀI NGUYÊN
os.environ["OMP_NUM_THREADS"] = "4"  # Tăng lên 4 để tận dụng tốt hơn khi chạy Sequential
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class V5SmartTrainer:
    def __init__(self, model_dir="ai_models_reg_v5"):
        self.model_dir = model_dir
        self.scaler = StandardScaler()
        os.makedirs(model_dir, exist_ok=True)

    def preprocess_data(self, df, target_col_name):
        # Feature List chuẩn V3/V4
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

        # Basket features
        for col in ['basketMomentum15M', 'basketMomentum1H', 'basketRsi14', 'basketVolSpike',
                    'riskAdjustedMom1H', 'basketAlpha15M', 'rsiDivergence']:
            if col in df.columns: numeric_features.append(col)

        valid_features = [c for c in numeric_features if c in df.columns and c not in ['var95_1H', 'expectedShortfall1H']]
        if not valid_features: return None, None

        X = df[valid_features].replace([np.inf, -np.inf], np.nan).fillna(0).astype('float32')

        # Xử lý tên target linh hoạt
        if target_col_name not in df.columns:
            if "future" + target_col_name in df.columns: target_col_name = "future" + target_col_name
            elif target_col_name.startswith("maxDrawdown") and target_col_name.replace("maxDrawdown", "maxDrawdownNext") in df.columns:
                target_col_name = target_col_name.replace("maxDrawdown", "maxDrawdownNext")

        if target_col_name not in df.columns: return None, None
        y = df[target_col_name].replace([np.inf, -np.inf], np.nan)

        # Lọc dữ liệu lỗi
        mask = y.notna()
        return X[mask].values, y[mask].values

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

    # --- OPTIMIZER 1: XGBOOST (THE KING) ---
    def optimize_xgb(self, X_train, y_train, X_valid, y_valid, trials):
        logger.info(f"👑 Optimizing XGBoost (King) - {trials} trials...")
        dtrain = xgb.DMatrix(X_train, label=y_train)
        dvalid = xgb.DMatrix(X_valid, label=y_valid)

        def obj(trial):
            params = {
                'verbosity': 0,
                'objective': 'reg:pseudohubererror', # Sử dụng Pseudo-Huber để kháng nhiễu tốt hơn MSE
                'tree_method': 'hist',
                'n_jobs': 4,
                'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
                'max_depth': trial.suggest_int('max_depth', 4, 12),
                'subsample': trial.suggest_float('subsample', 0.6, 0.95),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.95),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.1, 10.0, log=True), # Ép Regularization mạnh hơn
                'reg_lambda': trial.suggest_float('reg_lambda', 0.1, 10.0, log=True),
                'min_child_weight': trial.suggest_int('min_child_weight', 10, 100)
            }
            # Pruning callback để dừng sớm các trial tệ
            pruning = optuna.integration.XGBoostPruningCallback(trial, "valid-mphe") # mphe: mean pseudo huber error

            model = xgb.train(params, dtrain, num_boost_round=3000, evals=[(dvalid, 'valid')],
                              early_stopping_rounds=100, verbose_eval=False, callbacks=[pruning])

            # Trả về R2 để Optuna tối ưu (Maximize)
            preds = model.predict(dvalid)
            return r2_score(y_valid, preds)

        study = optuna.create_study(direction='maximize')
        study.optimize(obj, n_trials=trials)
        return study.best_params

    # --- OPTIMIZER 2: LIGHTGBM (THE SUPPORTER) ---
    def optimize_lgbm(self, X_train, y_train, X_valid, y_valid, trials):
        logger.info(f"🛡️ Optimizing LightGBM (Supporter) - {trials // 2} trials...") # Ít trial hơn XGB
        def obj(trial):
            params = {
                'objective': 'regression',
                'metric': 'huber', # Dùng Huber loss
                'n_estimators': 2000, 'verbosity': -1, 'n_jobs': 4,
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
                'num_leaves': trial.suggest_int('num_leaves', 20, 100),
                'subsample': trial.suggest_float('subsample', 0.6, 0.9),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 0.9),
                'reg_alpha': trial.suggest_float('reg_alpha', 1.0, 20.0, log=True), # Rất mạnh tay với L1/L2
                'reg_lambda': trial.suggest_float('reg_lambda', 1.0, 20.0, log=True),
                'min_child_samples': trial.suggest_int('min_child_samples', 50, 300) # Cần nhiều data mới chia node
            }
            model = lgb.LGBMRegressor(**params)
            model.fit(X_train, y_train, eval_set=[(X_valid, y_valid)], callbacks=[lgb.early_stopping(50, verbose=False)])
            return r2_score(y_valid, model.predict(X_valid))

        study = optuna.create_study(direction='maximize')
        study.optimize(obj, n_trials=max(10, trials // 2))
        return study.best_params

    def train(self, target_name, data_dir, n_trials):
        # Load Data
        X_scaled, y = self.load_data(data_dir, target_name)
        if X_scaled is None: return

        # Split: 90% Train, 10% Test
        split = int(len(X_scaled) * 0.9)
        X_train, X_test = X_scaled[:split], X_scaled[split:]
        y_train, y_test = y[:split], y[split:]

        # ==========================================
        # 1. TRAIN XGBOOST (V3 LOGIC - MAIN MODEL)
        # ==========================================
        best_xgb_params = self.optimize_xgb(X_train, y_train, X_test, y_test, n_trials)

        # Thiết lập cấu hình "Ultra" cho XGB
        final_xgb_params = best_xgb_params.copy()
        final_xgb_params.update({
            'n_estimators': 15000,
            'learning_rate': min(best_xgb_params['learning_rate'], 0.005), # Ép learning rate nhỏ
            'n_jobs': 4,
            'tree_method': 'hist',
            'objective': 'reg:pseudohubererror' # Giữ nguyên hàm loss kháng nhiễu
        })

        logger.info("🚀 Training Final XGBoost...")
        xgb_model = xgb.XGBRegressor(**final_xgb_params)
        xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=1000, early_stopping_rounds=300)

        r2_xgb = r2_score(y_test, xgb_model.predict(X_test))
        logger.info(f"✅ XGBoost Score: {r2_xgb:.4f}")

        # ==========================================
        # 2. TRAIN LIGHTGBM (OPTIONAL SUPPORTER)
        # ==========================================
        # Chỉ train LGBM nếu XGBoost thấy "khó" (R2 thấp) hoặc để diversify
        best_lgbm_params = self.optimize_lgbm(X_train, y_train, X_test, y_test, n_trials)

        final_lgbm_params = best_lgbm_params.copy()
        final_lgbm_params.update({
            'n_estimators': 15000,
            'learning_rate': 0.005,
            'n_jobs': 4,
            'objective': 'regression',
            'metric': 'huber'
        })

        logger.info("🛡️ Training Final LightGBM...")
        lgbm_model = lgb.LGBMRegressor(**final_lgbm_params)
        lgbm_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], callbacks=[lgb.early_stopping(300, verbose=False)])

        r2_lgbm = r2_score(y_test, lgbm_model.predict(X_test))
        logger.info(f"✅ LightGBM Score: {r2_lgbm:.4f}")

        # ==========================================
        # 3. TRAIN CATBOOST (SAFE FALLBACK)
        # ==========================================
        logger.info("🐱 Training CatBoost (MAE Objective)...")
        # Dùng MAE cho CatBoost để nó khác biệt hẳn so với 2 ông kia (Diversification)
        cat_model = CatBoostRegressor(
            iterations=15000, learning_rate=0.005, depth=6,
            loss_function='MAE', # Dùng MAE để kháng nhiễu cực mạnh
            thread_count=4, verbose=0, early_stopping_rounds=300
        )
        cat_model.fit(X_train, y_train, eval_set=(X_test, y_test))
        r2_cat = r2_score(y_test, cat_model.predict(X_test))
        logger.info(f"✅ CatBoost Score: {r2_cat:.4f}")

        # ==========================================
        # 4. SMART ENSEMBLE LOGIC (CRITICAL UPGRADE)
        # ==========================================
        logger.info(f"📊 Scores -> XGB: {r2_xgb:.4f}, LGBM: {r2_lgbm:.4f}, Cat: {r2_cat:.4f}")

        estimators = []
        weights = []

        # Logic: XGBoost luôn được chọn (Base)
        estimators.append(('xgb', xgb_model))
        weights.append(r2_xgb) # Sẽ chuẩn hóa sau

        # Logic: Chỉ chọn LGBM nếu nó không quá tệ so với XGB (ít nhất bằng 60% XGB)
        # Nếu R2 âm thì loại luôn
        if r2_lgbm > max(0, r2_xgb * 0.6):
            estimators.append(('lgbm', lgbm_model))
            weights.append(r2_lgbm)
        else:
            logger.warning(f"❌ Dropping LightGBM (Score {r2_lgbm:.4f} too low compared to XGB)")

        # Logic tương tự cho CatBoost
        if r2_cat > max(0, r2_xgb * 0.6):
            estimators.append(('cat', cat_model))
            weights.append(r2_cat)
        else:
            logger.warning(f"❌ Dropping CatBoost (Score {r2_cat:.4f} too low compared to XGB)")

        # Chuẩn hóa weights
        total_w = sum(weights)
        if total_w > 0:
            norm_weights = [w / total_w for w in weights]
        else:
            # Fallback nếu tất cả đều âm (hiếm), dùng XGB 100%
            norm_weights = [1.0]
            estimators = [('xgb', xgb_model)]

        logger.info(f"⚖️ Ensemble Weights: {norm_weights}")

        # Clean params for VotingRegressor
        for _, model in estimators:
            if hasattr(model, 'set_params'):
                try: model.set_params(early_stopping_rounds=None)
                except: pass

        ensemble = VotingRegressor(estimators=estimators, weights=norm_weights, n_jobs=1)
        ensemble.fit(X_train, y_train)

        final_r2 = r2_score(y_test, ensemble.predict(X_test))
        logger.info(f"🏆 FINAL MAX RESULT {target_name} -> R2: {final_r2:.4f}")

        # ==========================================
        # 5. EXPORT ONNX
        # ==========================================
        clean_name = target_name.replace("future", "").replace("Next", "")
        if "maxDrawdown" in target_name: clean_name = target_name.replace("Next", "")

        # Save Weights info
        with open(f"{self.model_dir}/Weights_{clean_name}.txt", "w") as f:
            f.write("\n".join([str(w) for w in norm_weights]))

        # Save Scaler
        skl_type = [('float_input', SklFloatTensorType([None, X_scaled.shape[1]]))]
        with open(f"{self.model_dir}/Scaler_{clean_name}.onnx", "wb") as f:
            f.write(convert_sklearn(self.scaler, initial_types=skl_type).SerializeToString())

        # Save Models (Chỉ save những model được chọn)
        initial_type = [('float_input', OnnxFloatTensorType([None, X_scaled.shape[1]]))]

        # Save XGB (Luôn có)
        with open(f"{self.model_dir}/Model_Regressor_{clean_name}_XGB.onnx", "wb") as f:
            f.write(convert_xgboost(xgb_model, initial_types=initial_type).SerializeToString())

        # Save LGBM (Nếu được chọn)
        if any(e[0] == 'lgbm' for e in estimators):
            with open(f"{self.model_dir}/Model_Regressor_{clean_name}_LGBM.onnx", "wb") as f:
                f.write(convert_lightgbm(lgbm_model, initial_types=initial_type).SerializeToString())

        # Save CatBoost (Nếu được chọn)
        if any(e[0] == 'cat' for e in estimators):
            cat_model.save_model(f"{self.model_dir}/Model_Regressor_{clean_name}_Cat.onnx", format="onnx")

        # Cleanup
        del X_scaled, y, X_train, X_test, y_train, y_test
        gc.collect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', required=True)
    parser.add_argument('--trials', type=int, default=100) # Khuyến nghị 100 trials
    args = parser.parse_args()

    trainer = V5SmartTrainer()
    trainer.train(args.target, "storage/training_data_big_sequential", args.trials)