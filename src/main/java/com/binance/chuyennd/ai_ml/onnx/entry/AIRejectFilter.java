package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AIRejectFilter {
    private static final Logger LOG = LoggerFactory.getLogger(AIRejectFilter.class);

    // --- CẤU HÌNH HIỆN TẠI (ĐÃ TINH GỌN XUỐNG 3 THAM SỐ) ---
    private float HARD_RISK_LIMIT_4H = -0.09985f;
    private float MIN_MOMENTUM_15M   = 0.016f;
    private float MIN_MOMENTUM_24H   = 0.02f;

//    private float HARD_RISK_LIMIT_4H = -0.10425f;
//    private float MIN_MOMENTUM_15M   = 0.025f;
//    private float MIN_MOMENTUM_24H   = 0.03049f;

    public enum FilterDecision {PASS, REJECT}

    public static class FilterResult {
        public FilterDecision decision;
        public String reason;

        public FilterResult(FilterDecision decision, String reason) {
            this.decision = decision;
            this.reason = reason;
        }
    }

    // --- HỖ TRỢ V2 (PredictionResult cũ) ---
    public FilterResult checkSignal(OnnxInferenceManager.PredictionResult prediction) {
        return evaluate(
                prediction.return15M,
                prediction.return24H,
                prediction.riskDrawdown4H
        );
    }

    // --- HỖ TRỢ V2 (AiPredictionData cũ) ---
    public FilterResult checkSignal(AiPredictionData prediction) {
        return evaluate(
                prediction.predReturn15M,
                prediction.predReturn24H,
                prediction.predRisk4H
        );
    }

    // 🔥 HÀM MỚI: Chỉ nhận 3 tham số
    public void setConfig(float risk, float min15m, float min24h) {
        HARD_RISK_LIMIT_4H = risk;
        MIN_MOMENTUM_15M = min15m;
        MIN_MOMENTUM_24H = min24h;
    }

    /**
     * LOGIC ĐÁNH GIÁ CHUNG (Đã gọt bỏ các if không dùng)
     */
    private FilterResult evaluate(float pred15M, float pred24H, float risk4H) {

        // 1. KIỂM TRA SINH TỒN (Risk Limit)
        if (risk4H <= HARD_RISK_LIMIT_4H) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: MaxDD 4H %.2f%% quá cao (Limit %.2f%%)",
                            risk4H * 100, HARD_RISK_LIMIT_4H * 100));
        }

        // 2. KIỂM TRA ĐÀ TĂNG NGẮN HẠN (15M) - QUAN TRỌNG NHẤT
        if (pred15M < MIN_MOMENTUM_15M) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("BAD MOMENTUM: 15M chưa nảy mạnh (%.2f%% < %.2f%%) -> Chờ xác nhận thêm",
                            pred15M * 100, MIN_MOMENTUM_15M * 100));
        }

        // 3. KIỂM TRA MACRO (24H)
        if (pred24H < MIN_MOMENTUM_24H) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("MACRO DUMP: 24H quá xấu (%.2f%% < %.2f%%) -> Không bắt dao rơi",
                            pred24H * 100, MIN_MOMENTUM_24H * 100));
        }

        // PASS
        return new FilterResult(FilterDecision.PASS,
                String.format("PERFECT: 15M(%.2f%%) | 24H(%.2f%%) | DD4H(%.2f%%)",
                        pred15M * 100, pred24H * 100, risk4H * 100));
    }
}