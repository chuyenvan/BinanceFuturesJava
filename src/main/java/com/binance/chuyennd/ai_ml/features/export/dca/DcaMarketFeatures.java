package com.binance.chuyennd.ai_ml.features.export.dca;

public class DcaMarketFeatures {
    // --- GROUP 1: MARKET POSITION ---
    public double distFromHigh24H;
    public double distMA20;

    // --- GROUP 2: RELATIVE STRENGTH ---
    public double instantAlpha;
    public double recoveryElasticity;

    // --- GROUP 3: MARKET CONTEXT (BREADTH) ---
    public double crashVelocity;
    public double globalRateDownAvg;
    public double advanceDeclineRatio;
    public double btcDominance;
    public double marketBreadthStrength;

    // --- GROUP 4: MACRO (BTC & ETH) ---
    public double btcMomentum15M;
    public double btcMomentum1H;
    public double btcMomentum4H;
    public double btcMomentum24H;
    public double btcMomentumAcceleration;

    public double ethMomentum15M;
    public double ethMomentum4H;

    // --- GROUP 5: COIN SPECIFIC TECHNICALS ---
    // Momentum riêng của coin
    public double momentum15M;
    public double momentum1H;
    public double momentum4H;
    public double momentum24H;

    public double rsi1H;
    public double rsiChange;          // RSI(Now) - RSI(1H Ago)
    public double volumeAnomaly;      // Vol 1H / Avg Vol 1H
    public double volumeRatio15M_24H; // Vol 15M / Vol 24H
    public double distFromLow24H;
    public double maxRateChange60M;
    public double volatilityShock;
    public double volatilityTermStructure;

    // --- GROUP 6: BASKET SPECIFIC ---
    public double basketMomentum15M;
    public double basketMomentum1H;
    public double basketMomentum24H;
    public double basketRsi14;
    public double basketVolSpike;

    // --- GROUP 7: FUNDING ---
    public double coinFundingRate; // Funding riêng của coin
    public double fundingRateRaw;  // Funding trung bình Basket
    public double fundingRateAvg24H;
    public double fundingRateTrend;

    // --- GROUP 8: TIME ---
    public int hourOfDay;
    public int dayOfWeek;
    public int weekOfMonth;
    public int monthOfYear;

    // --- LABELS (TARGETS) ---
    public int isPump20Pct3D; // 1 nếu tăng >= 20% trong 3 ngày
    public int isDump30Pct3D; // 1 nếu giảm <= -30% trong 3 ngày
}