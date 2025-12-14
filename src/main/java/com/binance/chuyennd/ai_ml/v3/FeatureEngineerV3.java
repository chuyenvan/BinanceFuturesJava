package com.binance.chuyennd.ai_ml.v3;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.LinkedList;

public class FeatureEngineerV3 {
    private static final Logger LOG = LoggerFactory.getLogger(FeatureEngineerV3.class);

    // Buffer lưu 30 cây nến gần nhất
    private final LinkedList<MarketFeaturesV3> historyBuffer = new LinkedList<>();
    private final int WINDOW_SIZE = 24;

    public float[] processAndGetInputArray(MarketFeaturesV3 current) {
        // 1. Update Buffer
        historyBuffer.addLast(current);
        if (historyBuffer.size() > 30) historyBuffer.removeFirst();

        // Chưa đủ dữ liệu -> Skip
        if (historyBuffer.size() < WINDOW_SIZE) return null;

        // 2. Tính toán Features Phái sinh
        // A. Lag Features cơ bản [rsi14, mom1H, vol1H, fund] x [1, 3]
        double rsi14_lag1 = getLag("rsi14", 1);
        double rsi14_lag3 = getLag("rsi14", 3);
        double mom1H_lag1 = getLag("momentum1H", 1);
        double mom1H_lag3 = getLag("momentum1H", 3);
        double vol1H_lag1 = getLag("volatility1H", 1);
        double vol1H_lag3 = getLag("volatility1H", 3);
        double fund_lag1  = getLag("fundingRateRaw", 1);
        double fund_lag3  = getLag("fundingRateRaw", 3);

        // 🔥 B. NEW LAG FEATURES (Bổ sung cho khớp 52)
        // Dự đoán thiếu Lag của Basket
        double bskMom1H_lag1 = getLag("basketMomentum1H", 1);
        double bskMom1H_lag3 = getLag("basketMomentum1H", 3);
        double bskRsi14_lag1 = getLag("basketRsi14", 1);
        double bskRsi14_lag3 = getLag("basketRsi14", 3);

        // C. Rolling Z-Score
        double mom1H_zscore = calZScore("momentum1H", current.momentum1H);
        double vol1H_zscore = calZScore("volatility1H", current.volatility1H);

        // D. Interaction Features
        double sharpe_proxy = current.momentum1H / (current.volatility1H + 1e-9);
        double vol_confirmed_mom = current.momentum1H * current.volumeSpike;
        double crypto_overheat = current.rsi14 * current.fundingRateRaw;
        double rel_strength_btc = current.momentum1H / (current.btcDominance + 1e-9);

        // 3. Xây dựng mảng Float (Tăng size từ 48 -> 52)
        float[] vector = new float[52];
        int i = 0;

        // --- PART 1: BASE FEATURES (33 features) ---
        // Group 1: BTC Macro
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

        vector[i++] = (float) current.rsi14;
        vector[i++] = (float) current.volumeSpike;
        vector[i++] = (float) current.distMA20;

        // Group 2: Breadth
        vector[i++] = (float) current.advanceDeclineRatio;
        vector[i++] = (float) current.percentAboveMA20;
        vector[i++] = (float) current.volumeRatioUpDown;
        vector[i++] = (float) current.marketBreadthStrength;
        vector[i++] = (float) current.btcDominance;

        // Group 3: Basket
        vector[i++] = (float) current.basketMomentum15M;
        vector[i++] = (float) current.basketMomentum1H;
        vector[i++] = (float) current.basketRsi14;
        vector[i++] = (float) current.basketVolSpike;

        // Group 4: Funding
        vector[i++] = (float) current.fundingRateRaw;
        vector[i++] = (float) current.fundingRateAvg24H;
        vector[i++] = (float) current.fundingRateTrend;

        // Group 5: Time
        vector[i++] = (float) current.hourOfDay;
        vector[i++] = (float) current.dayOfWeek;
        vector[i++] = (float) current.weekOfMonth;
        vector[i++] = (float) current.monthOfYear;

        // --- PART 2: LAG FEATURES (12 features - Cũ 8 + Mới 4) ---
        vector[i++] = (float) rsi14_lag1;
        vector[i++] = (float) rsi14_lag3;
        vector[i++] = (float) mom1H_lag1;
        vector[i++] = (float) mom1H_lag3;
        vector[i++] = (float) vol1H_lag1;
        vector[i++] = (float) vol1H_lag3;
        vector[i++] = (float) fund_lag1;
        vector[i++] = (float) fund_lag3;
        // Thêm 4 lag mới vào đây
        vector[i++] = (float) bskMom1H_lag1;
        vector[i++] = (float) bskMom1H_lag3;
        vector[i++] = (float) bskRsi14_lag1;
        vector[i++] = (float) bskRsi14_lag3;

        // --- PART 3: ROLLING FEATURES (2 features) ---
        vector[i++] = (float) mom1H_zscore;
        vector[i++] = (float) vol1H_zscore;

        // --- PART 4: INTERACTION FEATURES (4 features) ---
        vector[i++] = (float) sharpe_proxy;
        vector[i++] = (float) vol_confirmed_mom;
        vector[i++] = (float) crypto_overheat;
        vector[i++] = (float) rel_strength_btc;

        // Log kiểm tra 1 lần đầu tiên để chắc chắn size = 52
        // LOG.info("Vector size created: {}", i);

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

    private double getVal(MarketFeaturesV3 f, String field) {
        switch (field) {
            case "rsi14": return f.rsi14;
            case "momentum1H": return f.momentum1H;
            case "volatility1H": return f.volatility1H;
            case "fundingRateRaw": return f.fundingRateRaw;
            // Case mới cho Basket
            case "basketMomentum1H": return f.basketMomentum1H;
            case "basketRsi14": return f.basketRsi14;
            default: return 0.0;
        }
    }
}