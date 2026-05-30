package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.utils.Configs;

public class AIRejectFilter {
    public enum FilterDecision {PASS, REJECT}

    public static class FilterResult {
        public FilterDecision decision;
        public String reason;

        public FilterResult(FilterDecision decision, String reason) {
            this.decision = decision;
            this.reason = reason;
        }
    }

    public FilterResult checkSignal(AiPredictionData prediction) {
        // Ánh xạ lại Configs cũ vào các biến 1H và 4H mới
        return evaluate(prediction.predReturn1H, prediction.predReturn4H, prediction.predRisk4H,
                Configs.MIN_MOMENTUM_15M, Configs.MIN_MOMENTUM_24H, Configs.HARD_RISK_LIMIT_4H);
    }

    public FilterResult checkSignalDynamic(AiPredictionData prediction, Float symbolPred) {
        if (symbolPred == null) {
            return checkSignal(prediction);
        }

        if (prediction.predReturn1H < Configs.MIN_MOMENTUM_15M && symbolPred > Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: pred 1H %.2f%% thấp (Min %.2f%%)", prediction.predReturn1H * 100, Configs.MIN_MOMENTUM_15M * 100));
        }

        float baselineProb = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD;
        float scaleFactor = (symbolPred / baselineProb) * Configs.AI_DYNAMIC_MULTIPLIER;
        scaleFactor = Math.max(Configs.AI_DYNAMIC_MIN, Math.min(scaleFactor, Configs.AI_DYNAMIC_MAX));

        float dynamic_1H = Configs.MIN_MOMENTUM_15M * scaleFactor;
        float dynamic_4H = Configs.MIN_MOMENTUM_24H * scaleFactor;
        float dynamic_Risk4H = Configs.HARD_RISK_LIMIT_4H / scaleFactor;

        return evaluate(prediction.predReturn1H, prediction.predReturn4H, prediction.predRisk4H,
                dynamic_1H, dynamic_4H, dynamic_Risk4H);
    }

    public void setConfig(float risk, float min1h, float min4h) {
        Configs.HARD_RISK_LIMIT_4H = risk;
        Configs.MIN_MOMENTUM_15M = min1h; // Cột 1H
        Configs.MIN_MOMENTUM_24H = min4h; // Cột 4H
    }

    private FilterResult evaluate(float pred1H, float pred4H, float risk4H,
                                  float thres1H, float thres4H, float thresRisk) {

        if (risk4H <= thresRisk) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: MaxDD 4H %.2f%% quá cao (Limit %.2f%%)", risk4H * 100, thresRisk * 100));
        }
        if (pred1H < thres1H) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("BAD MOMENTUM: 1H chưa nảy mạnh (%.2f%% < %.2f%%)", pred1H * 100, thres1H * 100));
        }
        if (pred4H < thres4H) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("MACRO DUMP: 4H quá xấu (%.2f%% < %.2f%%)", pred4H * 100, thres4H * 100));
        }

        return new FilterResult(FilterDecision.PASS,
                String.format("PERFECT: 1H(%.2f%%) | 4H(%.2f%%) | DD4H(%.2f%%)", pred1H * 100, pred4H * 100, risk4H * 100));
    }
}