package com.binance.chuyennd.ai_ml.features.export.dca;

public class DcaMarketFeatures {
    // 1. Position Context (Giữ nguyên của DCA)
    public double currentDrawdown;
    public double lossVelocity1H;
    public double dcaImpactRatio;

    // 2. Relative Strength (Giữ nguyên của DCA)
    public double instantAlpha;
    public double recoveryElasticity;
    public double dangerIndex;

    // 3. Market Context (Cũ)
    public double crashVelocity;
    public double globalRateDownAvg;
    // public double fundingRate; // -> Đã chuyển sang Group 4 chi tiết hơn bên dưới

    // 4. Macro (BTC)
    public double btcMomentum1H;
    public double btcMomentum24H;

    // 5. Coin Specific Technicals
    public double rsi1H;
    public double volumeAnomaly;
    public double distFromLow24H;
    public double maxRateChange60M;
    public double volumeSpike;
    public double volatilityShock;

    // === GROUP 3: BASKET SPECIFIC (Clone từ MarketFeatures) ===
    // Trong DCA, Basket tạm hiểu là Coin đang xét (hoặc mở rộng so sánh với BTC)
    public double basketMomentum15M;
    public double basketMomentum1H;
    public double basketRsi14;
    public double basketVolSpike;

    // === GROUP 4: FUNDING (Clone từ MarketFeatures) ===
    public double fundingRateRaw;
    public double fundingRateAvg24H;
    public double fundingRateTrend;

    // === GROUP 5: TIME (Clone từ MarketFeatures) ===
    public int hourOfDay;
    public int dayOfWeek;
    public int weekOfMonth;
    public int monthOfYear;
}