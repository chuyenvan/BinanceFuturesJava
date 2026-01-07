# -*- coding: utf-8 -*-
import xgboost as xgb
import pandas as pd
import numpy as np
import os
import warnings
from ai_xgboost_train_model import AITradingRegressor

warnings.filterwarnings('ignore')

def get_used_feature_names(data_dir):
    """
    Lay danh sach feature thuc su duoc dung de Train (Da loai bo rac)
    """
    files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]
    if not files: return []

    # Load 1 file mau de lay Header
    df = pd.read_csv(os.path.join(data_dir, files[0]))

    # 1. Danh sach day du cac cot co the co
    all_potential_features = [
        'momentum1M', 'momentum5M', 'momentum15M', 'momentum1H', 'momentum4H', 'momentum24H',
        'momentumAcceleration', 'trendStrengthBTC', 'trendStrengthETH', 'trendConsistency',
        'volatility1M', 'volatility15M', 'volatility1H', 'volatility24H', 'volatilityTermStructure',
        'var95_1H', 'expectedShortfall1H', 'volatilityRegime',
        'advanceDeclineRatio', 'percentAboveMA20', 'volumeRatioUpDown', 'marketBreadthStrength', 'btcDominance',
        'rsi14', 'volumeSpike', 'distMA20',
        'fundingRateRaw', 'fundingRateAvg24H', 'fundingRateTrend',
        'basketMomentum15M', 'basketMomentum1H', 'basketRsi14', 'basketVolSpike',
        'hourOfDay', 'dayOfWeek', 'weekOfMonth', 'monthOfYear'
    ]

    # 2. DANH SACH CAN BO QUA (Blacklist)
    # - Cac cot String (Regime, Label)
    # - Cac cot du thua (var95, shortfall)
    ignore_list = [
        'volatilityRegime', 'marketRegime', 'regimeLabel',
        'var95_1H', 'expectedShortfall1H' # <--- BO QUA 2 COT NAY
    ]

    # 3. Loc lay danh sach cuoi cung
    # Logic: Nam trong all_potential AND Co trong CSV AND Khong nam trong ignore_list
    final_features = [f for f in all_potential_features
                      if f in df.columns and f not in ignore_list]

    return final_features

def check_importance():
    data_dir = "storage/training_data_big_sequential"
    target_name = "futureReturn15M"

    print(f"Analyzing Features in {data_dir}...")

    # 1. Lay dung danh sach ten feature (da loc)
    feature_names = get_used_feature_names(data_dir)
    print(f"Detected {len(feature_names)} active features (Removed var95/shortfall).")

    # 2. Load Data
    # Class AITradingRegressor da duoc update de bo qua 2 cot kia, nen X se khop voi feature_names
    trainer = AITradingRegressor(model_dir="ai_models_reg")
    print("Loading sample data (Top 50 files)...")
    X, y = trainer.load_and_scale_data(data_dir, target_name, max_files=50)

    if X is None:
        print("No data loaded.")
        return

    # 3. Train Quick Model
    print("Training quick XGBoost model...")
    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        n_jobs=-1,
        tree_method='hist'
    )

    model.fit(X, y)

    # 4. Get Importance
    importance = model.feature_importances_

    # Kiem tra khop lenh lan cuoi
    if len(feature_names) != len(importance):
        print(f"SIZE MISMATCH: Names={len(feature_names)}, Importance={len(importance)}")
        # Fallback
        feature_names = [f"Feat_{i}" for i in range(len(importance))]

    # 5. Hien thi ket qua
    feat_imp = pd.DataFrame({'Feature': feature_names, 'Importance': importance})
    feat_imp = feat_imp.sort_values('Importance', ascending=False)

    print("\n" + "="*40)
    print("TOP 20 MOST IMPORTANT FEATURES")
    print("="*40)
    print(feat_imp.head(20))

    print("\n" + "="*40)
    print("SPECIFIC FEATURES CHECK")
    print("="*40)
    check_list = ['rsi14', 'fundingRateRaw', 'basketRsi14', 'basketMomentum15M', 'volatility1H']
    for f in check_list:
        if f in feat_imp['Feature'].values:
            rank = feat_imp.index[feat_imp['Feature'] == f].tolist()[0]
            actual_rank = feat_imp.index.get_loc(rank) + 1
            score = feat_imp.loc[rank, 'Importance']
            print(f"{f:<20}: Rank {actual_rank:<3} | Score {score:.4f}")
        else:
            print(f"{f:<20}: NOT FOUND (Correctly Ignored)" if f in ['var95_1H'] else f"{f:<20}: NOT FOUND")

if __name__ == "__main__":
    check_importance()