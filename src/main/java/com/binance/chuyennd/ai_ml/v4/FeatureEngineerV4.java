package com.binance.chuyennd.ai_ml.v4;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.LinkedList;

public class FeatureEngineerV4 {
    private static final Logger LOG = LoggerFactory.getLogger(FeatureEngineerV4.class);

    // Buffer 30 nến để tính Rolling/Lag
    private final LinkedList<MarketFeaturesV4> historyBuffer = new LinkedList<>();
    private final int WINDOW_SIZE = 24;

    public float[] processAndGetInputArray(MarketFeaturesV4 current) {
        // 1. Update Buffer
        historyBuffer.addLast(current);
        if (historyBuffer.size() > 30) historyBuffer.removeFirst();

        // Chưa đủ dữ liệu -> Skip
        if (historyBuffer.size() < WINDOW_SIZE) return null;

        // --- TÍNH TOÁN FEATURES PHÁI SINH (Khớp Python) ---

        // A. Lag Features [1, 3]
        double rsi14_lag1 = getLag("rsi14", 1);
        double rsi14_lag3 = getLag("rsi14", 3);
        double mom1H_lag1 = getLag("momentum1H", 1);
        double mom1H_lag3 = getLag("momentum1H", 3);
        double vol1H_lag1 = getLag("volatility1H", 1);
        double vol1H_lag3 = getLag("volatility1H", 3);
        double fund_lag1  = getLag("fundingRateRaw", 1);
        double fund_lag3  = getLag("fundingRateRaw", 3);

        // B. Rolling Z-Score (Window 24)
        double mom1H_zscore = calZScore("momentum1H", current.momentum1H);
        double vol1H_zscore = calZScore("volatility1H", current.volatility1H);

        // C. Cyclical Time (Thay thế cho hourOfDay/dayOfWeek thô)
        double hour_sin = Math.sin(2 * Math.PI * current.hourOfDay / 24.0);
        double hour_cos = Math.cos(2 * Math.PI * current.hourOfDay / 24.0);
        double day_sin  = Math.sin(2 * Math.PI * current.dayOfWeek / 7.0);
        double day_cos  = Math.cos(2 * Math.PI * current.dayOfWeek / 7.0);

        // D. Interaction Features
        // Price Impact 4H: Volatility / (Momentum * Volume)
        double price_impact = current.volatility4H / (Math.abs(current.momentum4H) * current.totalUsdt + 1e-9);

        double sharpe_proxy = current.momentum1H / (current.volatility1H + 1e-9);
        double vol_confirmed_mom = current.momentum1H * current.volumeSpike;
        double crypto_overheat = current.rsi14 * current.fundingRateRaw;
        double rel_strength_btc = current.momentum1H / (current.btcDominance + 1e-9);

        // 3. XÂY DỰNG MẢNG FLOAT
        // Thứ tự: Base(NoTime) -> Lags -> ZScore -> Cyclical -> Interaction
        // Tổng cộng ~53 features (Cần check log Python để chắc chắn thứ tự, đây là thứ tự chuẩn logic)

        float[] vector = new float[53];
        int i = 0;

        // --- PART 1: BASE NUMERIC (Bỏ Time Int, Bỏ String) ---
        vector[i++] = (float) current.momentum1M;
        vector[i++] = (float) current.momentum5M;
        vector[i++] = (float) current.momentum15M;
        vector[i++] = (float) current.momentum1H;
        vector[i++] = (float) current.momentum4H;
        vector[i++] = (float) current.momentum24H;
        vector[i++] = (float) current.momentumAcceleration;
        vector[i++] = (float) current.trendStrengthETH;
        vector[i++] = (float) current.trendConsistency;

        vector[i++] = (float) current.volatility1M;
        vector[i++] = (float) current.volatility15M;
        vector[i++] = (float) current.volatility1H;
        vector[i++] = (float) current.volatility24H;
        vector[i++] = (float) current.volatilityTermStructure;

        vector[i++] = (float) current.advanceDeclineRatio;
        vector[i++] = (float) current.percentAboveMA20;
        vector[i++] = (float) current.volumeRatioUpDown;
        vector[i++] = (float) current.marketBreadthStrength;
        vector[i++] = (float) current.btcDominance;

        vector[i++] = (float) current.rsi14;
        vector[i++] = (float) current.volumeSpike;
        vector[i++] = (float) current.distMA20;

        vector[i++] = (float) current.fundingRateRaw;
        vector[i++] = (float) current.fundingRateAvg24H;
        vector[i++] = (float) current.fundingRateTrend;

        vector[i++] = (float) current.weekOfMonth; // Giữ lại nếu Python không drop
        vector[i++] = (float) current.monthOfYear; // Giữ lại nếu Python không drop

        vector[i++] = (float) current.basketMomentum15M;
        vector[i++] = (float) current.basketMomentum1H;
        vector[i++] = (float) current.basketRsi14;
        vector[i++] = (float) current.basketVolSpike;

        // --- PART 2: LAGS (8) ---
        vector[i++] = (float) rsi14_lag1;
        vector[i++] = (float) rsi14_lag3;
        vector[i++] = (float) mom1H_lag1;
        vector[i++] = (float) mom1H_lag3;
        vector[i++] = (float) vol1H_lag1;
        vector[i++] = (float) vol1H_lag3;
        vector[i++] = (float) fund_lag1;
        vector[i++] = (float) fund_lag3;

        // --- PART 3: Z-SCORES (2) ---
        vector[i++] = (float) mom1H_zscore;
        vector[i++] = (float) vol1H_zscore;

        // --- PART 4: CYCLICAL (4) ---
        vector[i++] = (float) hour_sin;
        vector[i++] = (float) hour_cos;
        vector[i++] = (float) day_sin;
        vector[i++] = (float) day_cos;

        // --- PART 5: INTERACTION (5) ---
        vector[i++] = (float) price_impact;
        vector[i++] = (float) sharpe_proxy;
        vector[i++] = (float) vol_confirmed_mom;
        vector[i++] = (float) crypto_overheat;
        vector[i++] = (float) rel_strength_btc;

        return vector;
    }

    // --- Helpers ---
    private double getLag(String field, int lag) {
        int idx = historyBuffer.size() - 1 - lag;
        if (idx < 0) return 0.0;
        return getVal(historyBuffer.get(idx), field);
    }

    private double calZScore(String field, double currentVal) {
        if (historyBuffer.size() < WINDOW_SIZE) return 0.0;
        double sum = 0, sumSq = 0;
        for (int i = 0; i < WINDOW_SIZE; i++) {
            double val = getVal(historyBuffer.get(historyBuffer.size() - 1 - i), field);
            sum += val;
            sumSq += val * val;
        }
        double mean = sum / WINDOW_SIZE;
        double variance = (sumSq / WINDOW_SIZE) - (mean * mean);
        double std = Math.sqrt(Math.max(0, variance));
        return (currentVal - mean) / (std + 1e-9);
    }

    private double getVal(MarketFeaturesV4 f, String field) {
        switch (field) {
            case "rsi14": return f.rsi14;
            case "momentum1H": return f.momentum1H;
            case "volatility1H": return f.volatility1H;
            case "fundingRateRaw": return f.fundingRateRaw;
            default: return 0.0;
        }
    }
}