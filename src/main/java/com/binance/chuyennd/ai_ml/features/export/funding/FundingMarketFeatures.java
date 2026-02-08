package com.binance.chuyennd.ai_ml.features.export.funding;

public class FundingMarketFeatures {
    // --- GROUP 1: MARKET CONTEXT ---
    public double btcMomentum1H;
    public double btcMomentum4H;
    public double btcMomentum24H;
    public double btcDominance;
    public double marketBreadthStrength;

    // --- GROUP 2: COIN SPECIFIC ---
    public double momentum1M;  // ✅ Mới thêm
    public double momentum15M; // ✅ Lấy từ rateDown15MAvg
    public double momentum1H;
    public double momentum4H;
    public double momentum24H;
    public double rsi1H;
    public double distFromLow24H;
    public double volatilityShock;

    // --- GROUP 3: BASKET SPECIFIC ---
    public double basketMomentum15M;
    public double basketMomentum1H;
    public double basketMomentum24H;
    public double basketRsi14;
    public double basketVolSpike;

    // --- GROUP 4: FUNDING FEE ---
    public double coinFundingRate;
    public double fundingRateRaw;
    public double fundingRateAvg24H;
    public double fundingRateTrend;

    // --- LABELS (TARGET) ---
    // 0: Fail, 1: 72H, 2: 24H, 3: 4H, 4: 15M
    public int label6;   // Target 6%
    public int label40;  // Target 40%
}