package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
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
        return evaluate(prediction.predReturn15M, prediction.predReturn24H, prediction.predRisk4H,
                Configs.MIN_MOMENTUM_15M, Configs.MIN_MOMENTUM_24H, Configs.HARD_RISK_LIMIT_4H);
    }

    // ==============================================================
    // LUỒNG 2: DÙNG RIÊNG CHO PREDICT_SYMBOL_TRADE (ĐỘNG)
    // ==============================================================
    public FilterResult checkSignalDynamic(AiPredictionData prediction, Float symbolPred) {
        if (symbolPred == null) {
            return checkSignal(prediction); // Fallback về cứng nếu lỗi
        }

        if (prediction.predReturn15M < Configs.MIN_MOMENTUM_15M && symbolPred > Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: pred 15m %.2f%% thap (Min %.2f%%)", prediction.predReturn15M * 100, Configs.MIN_MOMENTUM_15M * 100));
        }
        // Lấy baseline
        float baselineProb = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD;

        // 🔥 LOGIC MỚI: Tính toán dựa trên Configs
        float scaleFactor = (symbolPred / baselineProb) * Configs.AI_DYNAMIC_MULTIPLIER;

        // Chặn Trần/Sàn bằng Configs
        scaleFactor = Math.max(Configs.AI_DYNAMIC_MIN, Math.min(scaleFactor, Configs.AI_DYNAMIC_MAX));

        float dynamic_15M = Configs.MIN_MOMENTUM_15M * scaleFactor;
        float dynamic_24H = Configs.MIN_MOMENTUM_24H * scaleFactor;
        float dynamic_Risk4H = Configs.HARD_RISK_LIMIT_4H / scaleFactor;

        return evaluate(prediction.predReturn15M, prediction.predReturn24H, prediction.predRisk4H,
                dynamic_15M, dynamic_24H, dynamic_Risk4H);
    }

    // 🔥 HÀM MỚI: Chỉ nhận 3 tham số
    public void setConfig(float risk, float min15m, float min24h) {
        Configs.HARD_RISK_LIMIT_4H = risk;
        Configs.MIN_MOMENTUM_15M = min15m;
        Configs.MIN_MOMENTUM_24H = min24h;
    }

    /**
     * LOGIC ĐÁNH GIÁ LÕI
     */
    private FilterResult evaluate(float pred15M, float pred24H, float risk4H,
                                  float thres15M, float thres24H, float thresRisk) {

        if (risk4H <= thresRisk) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: MaxDD 4H %.2f%% quá cao (Limit %.2f%%)", risk4H * 100, thresRisk * 100));
        }
        if (pred15M < thres15M) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("BAD MOMENTUM: 15M chưa nảy mạnh (%.2f%% < %.2f%%)", pred15M * 100, thres15M * 100));
        }
        if (pred24H < thres24H) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("MACRO DUMP: 24H quá xấu (%.2f%% < %.2f%%)", pred24H * 100, thres24H * 100));
        }

        return new FilterResult(FilterDecision.PASS,
                String.format("PERFECT: 15M(%.2f%%) | 24H(%.2f%%) | DD4H(%.2f%%)", pred15M * 100, pred24H * 100, risk4H * 100));
    }
}