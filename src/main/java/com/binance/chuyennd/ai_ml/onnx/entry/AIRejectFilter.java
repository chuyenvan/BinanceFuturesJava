package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;

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
        return evaluate(prediction.predReturn15M, prediction.predRisk4H,
                Configs.MIN_MOMENTUM_15M, Configs.HARD_RISK_LIMIT_4H);
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
        float dynamic_Risk4H = Configs.HARD_RISK_LIMIT_4H / scaleFactor;

        return evaluate(prediction.predReturn15M, prediction.predRisk4H,
                dynamic_15M, dynamic_Risk4H);
    }

    public void setConfig(float risk, float min15m) {
        Configs.HARD_RISK_LIMIT_4H = risk;
        Configs.MIN_MOMENTUM_15M = min15m;
    }

    /**
     * LOGIC ĐÁNH GIÁ LÕI — chỉ còn 2 nhánh: RISK (DD4H) + MOM15. (MOM24/predReturn24H đã bỏ hẳn.)
     * FILTER_MODE: B/D bỏ nhánh RISK (để đo); A/C giữ RISK. MOM15 luôn giữ.
     * EARLY (trong checkSignalDynamic) không đụng tới đây.
     */
    private FilterResult evaluate(float pred15M, float risk4H, float thres15M, float thresRisk) {
        String mode = Configs.FILTER_MODE;
        boolean checkRisk = !("B".equals(mode) || "D".equals(mode));

        if (checkRisk && risk4H <= thresRisk) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: MaxDD 4H %.2f%% quá cao (Limit %.2f%%)", risk4H * 100, thresRisk * 100));
        }
        if (pred15M < thres15M) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("BAD MOMENTUM: 15M chưa nảy mạnh (%.2f%% < %.2f%%)", pred15M * 100, thres15M * 100));
        }

        return new FilterResult(FilterDecision.PASS,
                String.format("PERFECT: 15M(%.2f%%) | DD4H(%.2f%%)", pred15M * 100, risk4H * 100));
    }
}