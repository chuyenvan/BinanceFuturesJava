package com.binance.chuyennd.ai_ml.features.export.funding;

import java.io.Serializable;

public class FundingMarketFeatures implements Serializable {
    // --- TRỤC THỜI GIAN (KHÔNG phải feature train; chỉ để split theo thời gian + purge gap) ---
    public long timestamp;
    public String symbol;

    // --- GROUP 1: MARKET CONTEXT ---
    public float btcMomentum1H;
    public float btcMomentum4H;
    public float btcMomentum24H;
    public float btcDominance;
    public float marketBreadthStrength;

    // --- GROUP 2: MARKET-RATEDOWN + COIN SPECIFIC ---
    public float rateDownAvg;    // market-MDO rateDownAvg (cũ: momentum1M — nhãn coin SAI, thực là market)
    public float rateDown15MAvg; // market-MDO rateDown15MAvg (cũ: momentum15M — nhãn coin SAI, thực là market)
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
    public float basketFundingAvg;
    public float fundingRateAvg24H;
    public float fundingRateTrend;

    // --- LABELS (TARGET) ---
    // 0: Fail, 1: 72H, 2: 24H, 3: 4H, 4: 15M
    public int label6;   // Target 6%
    public int label40;  // Target 40%
}