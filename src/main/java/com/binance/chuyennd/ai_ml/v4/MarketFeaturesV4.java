package com.binance.chuyennd.ai_ml.v4;

import java.io.Serializable;

public class MarketFeaturesV4 implements Serializable {
    private static final long serialVersionUID = 4L;

    // Vector Input cho ONNX (Đã qua xử lý Lag, Cyclical...)
    public float[] onnxInputData;

    public long timestamp;
    public String dateKey;

    // === BASE FEATURES ===
    public double momentum1M, momentum5M, momentum15M, momentum1H, momentum4H, momentum24H, momentumAcceleration;
    public double trendStrengthETH, trendConsistency;
    public double volatility1M, volatility15M, volatility1H, volatility4H, volatility24H, volatilityTermStructure; // Thêm volatility4H
    public double rsi14, volumeSpike, distMA20;
    public double advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, btcDominance;
    public double basketMomentum15M, basketMomentum1H, basketRsi14, basketVolSpike;
    public double fundingRateRaw, fundingRateAvg24H, fundingRateTrend;
    public int hourOfDay, dayOfWeek, weekOfMonth, monthOfYear;

    // Thêm trường Volume để tính Price Impact
    public double totalUsdt;

    // === LABELS ===
    public String regimeLabel; // Để debug

    public MarketFeaturesV4() {}
}