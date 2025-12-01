package com.binance.chuyennd.ai_ml.onnx;


import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AIRejectFilter {
    private static final Logger LOG = LoggerFactory.getLogger(AIRejectFilter.class);

    // --- CẤU HÌNH "SMART CUT" (Mục tiêu: Chỉ lọc 5-10% tệ nhất) ---

    // 1. Ngưỡng Lợi nhuận Mạnh (Strong Profit): > 0.8%
    // Gặp lệnh này là MÚC NGAY, miễn bàn.
    private static final double STRONG_PROFIT_THRESHOLD = 0.008;

    // 2. Ngưỡng Rủi ro Tử thần (Deadly Risk): < -10%
    // Chỉ chặn khi sập cực sâu (Thiên nga đen).
    private static final double DEADLY_RISK_LIMIT = -0.10;

    // 3. Ngưỡng Lợi nhuận Tối thiểu (Min Profit): > 0.1%
    // Đủ trả phí sàn là chơi.
    private static final double MIN_PROFIT_THRESHOLD = 0.001;

    public enum FilterDecision { PASS, REJECT }

    public static class FilterResult {
        public FilterDecision decision;
        public String reason;

        public FilterResult(FilterDecision decision, String reason) {
            this.decision = decision;
            this.reason = reason;
        }
    }

//    public static FilterResult checkSignal(OnnxInferenceManager.PredictionResult prediction) {
//        return evaluate(prediction.return1H, prediction.riskDrawdown4H);
//    }

    public static FilterResult checkSignal(AiPredictionData prediction) {
        return evaluate(prediction.predReturn1H, prediction.predRisk4H);
    }

    private static FilterResult evaluate(double pred1H, double risk4H) {
        // ---------------------------------------------------------
        // QUY TẮC 1: ƯU TIÊN TUYỆT ĐỐI CHO KÈO THƠM
        // ---------------------------------------------------------
        // Nếu AI dự báo lãi > 0.8% -> PASS NGAY LẬP TỨC
        // (Cứu các lệnh 1.28%, 2.4% bị reject oan trước đó)
        if (pred1H >= STRONG_PROFIT_THRESHOLD) {
            return new FilterResult(
                    FilterDecision.PASS,
                    String.format("STRONG SIGNAL: Lãi to (%.2f%%) -> MÚC NGAY", pred1H * 100)
            );
        }

        // ---------------------------------------------------------
        // QUY TẮC 2: CHẶN TỬ THẦN (Lọc đuôi trái)
        // ---------------------------------------------------------
        // Chỉ reject khi rủi ro sập hầm quá lớn (> 10%)
        if (risk4H < DEADLY_RISK_LIMIT) {
            return new FilterResult(
                    FilterDecision.REJECT,
                    String.format("EXTREME RISK: Dự báo sập (%.2f%%) < -10%% -> NÉ GẤP", risk4H * 100)
            );
        }

        // ---------------------------------------------------------
        // QUY TẮC 3: CHẶN SIDEWAY (Lọc lệnh rác)
        // ---------------------------------------------------------
        // Nếu lãi bé tí tẹo (< 0.1%) -> Bỏ qua cho đỡ tốn phí
        if (pred1H < MIN_PROFIT_THRESHOLD) {
            return new FilterResult(
                    FilterDecision.REJECT,
                    String.format("NO PROFIT: Lãi (%.2f%%) < 0.1%% -> BỎ QUA", pred1H * 100)
            );
        }

        // ---------------------------------------------------------
        // CÒN LẠI -> PASS HẾT (Vùng trung tính)
        // ---------------------------------------------------------
        // Chấp nhận cả các lệnh R:R xấu một chút, miễn là không sập hầm.
        return new FilterResult(
                FilterDecision.PASS,
                String.format("OK: Return %.2f%% | Risk %.2f%%", pred1H * 100, risk4H * 100)
        );
    }
}