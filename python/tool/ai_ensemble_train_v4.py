# -*- coding: utf-8 -*-
import os
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import StackingRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import r2_score
import optuna
import logging
import warnings
import joblib

# Thư viện ONNX nâng cao
from skl2onnx import convert_sklearn, update_registered_converter
from skl2onnx.common.data_types import FloatTensorType as SklFloatTensorType
from skl2onnx.common.shape_calculator import calculate_linear_regressor_output_shapes
from onnxmltools.convert.xgboost.operator_converters import convert_xgboost as xgb_conv
from onnxmltools.convert.lightgbm.operator_converters import convert_lightgbm as lgb_conv

# Cấu hình log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
warnings.filterwarnings('ignore')

class GodModeTrainer:
    def __init__(self, model_dir="ai_models_ultra_v3"):
        self.model_dir = model_dir
        self.scaler = StandardScaler()
        os.makedirs(model_dir, exist_ok=True)
        # Đăng ký converter để đóng gói Stacking sang ONNX
        update_registered_converter(xgb.XGBRegressor, 'XGBoostRegressor',
                                    calculate_linear_regressor_output_shapes, xgb_conv)
        update_registered_converter(lgb.LGBMRegressor, 'LightGbmRegressor',
                                    calculate_linear_regressor_output_shapes, lgb_conv)

    def preprocess_data(self, df, target_name):
        # Feature list chuẩn của bạn
        feature_columns = [
            'momentum1M', 'momentum5M', 'momentum15M', 'momentum1H', 'momentum4H', 'momentum24H',
            'momentumAcceleration', 'trendStrengthBTC', 'trendStrengthETH', 'trendConsistency',
            'volatility1M', 'volatility15M', 'volatility1H', 'volatility24H', 'volatilityTermStructure',
            'volatilityRegime', 'advanceDeclineRatio', 'percentAboveMA20', 'volumeRatioUpDown',
            'marketBreadthStrength', 'btcDominance', 'rsi14', 'volumeSpike', 'distMA20',
            'fundingRateRaw', 'fundingRateAvg24H', 'fundingRateTrend',
            'hourOfDay', 'dayOfWeek', 'weekOfMonth', 'monthOfYear',
            'basketMomentum15M', 'basketMomentum1H', 'basketRsi14', 'basketVolSpike'
        ]
        valid_features = [c for c in feature_columns if c in df.columns]
        X = df[valid_features].replace([np.inf, -np.inf], np.nan).fillna(0).astype('float32')

        target_col = target_name
        if target_col not in df.columns:
            if "future" + target_col in df.columns: target_col = "future" + target_col
            elif target_col.replace("maxDrawdown", "maxDrawdownNext") in df.columns:
                target_col = target_col.replace("maxDrawdown", "maxDrawdownNext")

        y = df[target_col].replace([np.inf, -np.inf], np.nan)
        mask = y.notna()
        return X[mask].values, y[mask].values

    def optimize_base_models(self, X, y, n_trials):
        tscv = TimeSeriesSplit(n_splits=5) # 5-Fold TimeSeries

        def xgb_obj(t):
            p = {
                'learning_rate': t.suggest_float('lr', 0.001, 0.05, log=True),
                'max_depth': t.suggest_int('depth', 4, 15),
                'min_child_weight': t.suggest_int('mcw', 1, 20),
                'subsample': t.suggest_float('sub', 0.5, 0.9),
                'colsample_bytree': t.suggest_float('col', 0.5, 0.9),
                'n_estimators': 1500, 'tree_method': 'hist', 'n_jobs': 4
            }
            scores = []
            for tr_idx, va_idx in tscv.split(X):
                m = xgb.XGBRegressor(**p)
                m.fit(X[tr_idx], y[tr_idx], eval_set=[(X[va_idx], y[va_idx])],
                      early_stopping_rounds=50, verbose=False)
                scores.append(r2_score(y[va_idx], m.predict(X[va_idx])))
            return np.mean(scores)

        def lgb_obj(t):
            p = {
                'learning_rate': t.suggest_float('lr', 0.001, 0.05, log=True),
                'num_leaves': t.suggest_int('leaves', 31, 512),
                'feature_fraction': t.suggest_float('ff', 0.5, 0.9),
                'bagging_fraction': t.suggest_float('bf', 0.5, 0.9),
                'n_estimators': 1500, 'n_jobs': 4
            }
            scores = []
            for tr_idx, va_idx in tscv.split(X):
                m = lgb.LGBMRegressor(**p)
                m.fit(X[tr_idx], y[tr_idx], eval_set=[(X[va_idx], y[va_idx])],
                      early_stopping_rounds=50, verbose=False)
                scores.append(r2_score(y[va_idx], m.predict(X[va_idx])))
            return np.mean(scores)

        logger.info("🎯 Bắt đầu tối ưu XGBoost...")
        study_xgb = optuna.create_study(direction="maximize")
        study_xgb.optimize(xgb_obj, n_trials=n_trials)

        logger.info("🎯 Bắt đầu tối ưu LightGBM...")
        study_lgb = optuna.create_study(direction="maximize")
        study_lgb.optimize(lgb_obj, n_trials=n_trials)

        return study_xgb.best_params, study_lgb.best_params

    def train_ultra(self, target_name, data_dir, trials):
        # 1. Load Data (Tất cả file để đạt R2 cao nhất)
        X_list, y_list = [], []
        files = sorted(os.listdir(data_dir))
        for f in files:
            df = pd.read_csv(os.path.join(data_dir, f))
            X_tmp, y_tmp = self.preprocess_data(df, target_name)
            if X_tmp is not None: X_list.append(X_tmp); y_list.append(y_tmp)

        X_all = np.vstack(X_list); y_all = np.hstack(y_list)
        X_scaled = self.scaler.fit_transform(X_all)

        # 2. Optimize
        best_xgb, best_lgb = self.optimize_base_models(X_scaled, y_all, trials)

        # 3. Train Stacking Regressor
        logger.info("🚀 Training Ultra-Ensemble Stacking (Final Fit)...")
        # Nâng n_estimators lên cực cao cho bản cuối
        best_xgb['n_estimators'] = 30000
        best_xgb['learning_rate'] = 0.001 # Giảm siêu thấp để học cực sâu

        best_lgb['n_estimators'] = 30000
        best_lgb['learning_rate'] = 0.001

        estimators = [
            ('xgb', xgb.XGBRegressor(**best_xgb)),
            ('lgb', lgb.LGBMRegressor(**best_lgb))
        ]

        # Meta-learner là RidgeCV để tối ưu trọng số các mô hình base
        stack_model = StackingRegressor(estimators=estimators, final_estimator=RidgeCV(), cv=5, n_jobs=-1)
        stack_model.fit(X_scaled, y_all)

        final_r2 = r2_score(y_all, stack_model.predict(X_scaled))
        logger.info(f"🏆 KẾT QUẢ CUỐI CÙNG R2: {final_r2:.6f}")

        # 4. EXPORT ONNX
        clean_name = target_name.replace("future", "").replace("Next", "")
        init_type = [('float_input', SklFloatTensorType([None, X_all.shape[1]]))]

        # Xuất Model
        onnx_model = convert_sklearn(stack_model, initial_types=init_type, target_opset=12)
        with open(f"{self.model_dir}/Model_Ensemble_{clean_name}.onnx", "wb") as f:
            f.write(onnx_model.SerializeToString())

        # Xuất Scaler (Giữ nguyên chuẩn cũ cho Java)
        onnx_scaler = convert_sklearn(self.scaler, initial_types=init_type)
        with open(f"{self.model_dir}/Scaler_{clean_name}.onnx", "wb") as f:
            f.write(onnx_scaler.SerializeToString())

        logger.info(f"💾 Đã lưu ONNX tại {self.model_dir}")

if __name__ == "__main__":
    # Cấu hình target và số trial (Càng nhiều trial R2 càng tốt)
    GodModeTrainer().train_ultra("futureReturn15M", "storage/training_data_big_sequential", trials=200)