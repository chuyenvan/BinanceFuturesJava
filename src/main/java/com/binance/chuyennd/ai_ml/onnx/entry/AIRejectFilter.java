package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;

public class AIRejectFilter {

    public enum FilterDecision {
        PASS,
        REJECT
    }

    public static class FilterResult {
        public FilterDecision decision;
        public String reason;
        public FilterResult(FilterDecision decision, String reason) {
            this.decision = decision;
            this.reason = reason;
        }
    }

    // 🔥 ĐÃ BỎ: private float HARD_RISK_LIMIT_4H = -0.1f;
    private float MIN_MOMENTUM_15M = 0.015f;
    private float MIN_MOMENTUM_24H = 0.02f;

    // 🔥 CẬP NHẬT: Constructor chỉ còn 2 tham số
    public void setConfig(float min15m, float min24h) {
        this.MIN_MOMENTUM_15M = min15m;
        this.MIN_MOMENTUM_24H = min24h;
    }

    public FilterResult checkSignal(AiPredictionData predict) {
        if (predict == null) return new FilterResult(FilterDecision.REJECT, "Null Prediction");

        // 🔥 ĐÃ BỎ ĐOẠN CHECK RISK 4H

        // 2. CHECK MOMENTUM 15M (Vận tốc ngắn hạn)
        if (predict.predReturn15M < MIN_MOMENTUM_15M) {
            return new FilterResult(FilterDecision.REJECT, "Low Momentum 15M");
        }

        // 3. CHECK MOMENTUM 24H (Xu hướng dài hạn)
        if (predict.predReturn24H < MIN_MOMENTUM_24H) {
            return new FilterResult(FilterDecision.REJECT, "Low Momentum 24H");
        }

        return new FilterResult(FilterDecision.PASS, "OK");
    }

    public FilterResult checkSignalDynamic(AiPredictionData predict, float symbolPredVal) {
        if (predict == null) return new FilterResult(FilterDecision.REJECT, "Null Prediction");

        // 🔥 ĐÃ BỎ ĐOẠN CHECK RISK 4H DYNAMIC

        // 2. CHECK MOMENTUM 15M TÙY CHỈNH THEO ĐỘ NGON CỦA COIN
        float dynamicMin15M = MIN_MOMENTUM_15M;
        if (symbolPredVal > 0.04f) dynamicMin15M = MIN_MOMENTUM_15M - 0.005f;
        if (symbolPredVal > 0.06f) dynamicMin15M = MIN_MOMENTUM_15M - 0.010f;
        if (predict.predReturn15M < dynamicMin15M) {
            return new FilterResult(FilterDecision.REJECT, "Low Momentum 15M (Dynamic)");
        }

        // 3. CHECK MOMENTUM 24H TÙY CHỈNH THEO ĐỘ NGON CỦA COIN
        float dynamicMin24H = MIN_MOMENTUM_24H;
        if (symbolPredVal > 0.04f) dynamicMin24H = MIN_MOMENTUM_24H - 0.01f;
        if (symbolPredVal > 0.06f) dynamicMin24H = MIN_MOMENTUM_24H - 0.02f;
        if (predict.predReturn24H < dynamicMin24H) {
            return new FilterResult(FilterDecision.REJECT, "Low Momentum 24H (Dynamic)");
        }

        return new FilterResult(FilterDecision.PASS, "OK DYNAMIC");
    }
}