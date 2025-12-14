package com.binance.chuyennd.ai_ml.v3;

import java.io.Serializable;
import java.util.Locale;

public class MarketFeaturesV3 implements Serializable {
    private static final long serialVersionUID = 3L; // Version 3

    // 🔥 Mảng chứa vector Input cho ONNX (Đã qua xử lý Lag/Rolling)
    public float[] onnxInputData;

    public long timestamp;
    public String dateKey;

    // === BASE FEATURES (Giống V1/V2) ===
    public double momentum1M, momentum5M, momentum15M, momentum1H, momentum4H, momentum24H, momentumAcceleration;
    public double trendStrengthETH, trendConsistency;
    public double volatility1M, volatility15M, volatility1H, volatility24H, volatilityTermStructure;
    public String volatilityRegime;
    public double rsi14, volumeSpike, distMA20;
    public double advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, btcDominance;
    public double basketMomentum15M, basketMomentum1H, basketRsi14, basketVolSpike;
    public double fundingRateRaw, fundingRateAvg24H, fundingRateTrend;
    public int hourOfDay, dayOfWeek, weekOfMonth, monthOfYear;

    // === TARGETS / LABELS (Dùng khi Training/Debug) ===
    public String regimeLabel;
    public double futureReturn15M, futureReturn1H, futureReturn4H, futureReturn24H;
    public double maxDrawdownNext4H, maxDrawdownNext24H;

    public MarketFeaturesV3() {}
}