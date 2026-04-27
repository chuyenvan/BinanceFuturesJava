package com.binance.chuyennd.ai_ml.features.export.funding;

import java.io.Serializable;

public class FundingMarketFeatures implements Serializable {
    // --- GROUP 1: MARKET CONTEXT ---
    public float btcMomentum1H;
    public float btcMomentum4H;
    public float btcMomentum24H;
    public float btcDominance;
    public float marketBreadthStrength;

    // --- GROUP 2: COIN SPECIFIC ---
    public float momentum1M;  // ✅ Mới thêm
    public float momentum15M; // ✅ Lấy từ rateDown15MAvg
    public float momentum1H;
    public float momentum4H;
    public float momentum24H;
    public float rsi1H;
    public float distFromLow24H;
    public float volatilityShock;

    // --- GROUP 3: BASKET SPECIFIC ---
    public float basketMomentum15M;
    public float basketMomentum1H;
    public float basketMomentum24H;
    public float basketRsi14;
    public float basketVolSpike;

    // --- GROUP 4: FUNDING FEE ---
    public float coinFundingRate;
    public float fundingRateRaw;
    public float fundingRateAvg24H;
    public float fundingRateTrend;

    // --- LABELS (TARGET) ---
    // 0: Fail, 1: 72H, 2: 24H, 3: 4H, 4: 15M
    public int label6;   // Target 6%
    public int label40;  // Target 40%
}