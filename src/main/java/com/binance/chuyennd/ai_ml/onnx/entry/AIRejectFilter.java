package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AIRejectFilter {
    private static final Logger LOG = LoggerFactory.getLogger(AIRejectFilter.class);

    // =========================================================================
    // LỊCH SỬ CẤU HÌNH (PARAMETER HISTORY)
    // =========================================================================
    // --- Test #22 (Manual): Profit ~?? ---
    // [Risk: -0.0262 | 1H: 0.0213 | 15M: 0.0044 | 4H: -0.0024]

    // --- Test #HPO_1 (18/12/2025): Score 71,344 ---
    // [Risk: -0.0288 | 1H: 0.0217 | High: 0.042 | 15M: 0.0065 | 4H: 0.017]

    // --- Test #HPO_2_DeepSearch (19/12/2025): Score 198,922 🏆🏆 ---
    // AI đã thay đổi chiến thuật hoàn toàn: "Bắt dao sâu nhưng chờ xác nhận mạnh"
    // 1. Risk nới xuống -5.6% (Chấp nhận giảm sâu).
    // 2. Momentum 15M tăng vọt lên 1.35% (Yêu cầu cú nảy hồi cực mạnh mới vào).
    // 3. Trend 4H giảm xuống 0.35% (Không quan trọng trend dài, chỉ cần sóng hồi ngắn).
    // =========================================================================

    // --- CẤU HÌNH HIỆN TẠI (BEST FOUND SCORE 198K) ---
    private double HARD_RISK_LIMIT = -0.04745;      // Chấp nhận MaxDD lên tới 5.6%
    private double MIN_PRED_RETURN_1H = 0.02602;    // Lãi 1H > 1.6% là vào (Thấp hơn mức 2.1% cũ)
    private double HIGH_RETURN_THRESHOLD = 0.05949; // Chỉ kèo siêu tưởng (>8.5%) mới được phá rào Risk

    // --- CẤU HÌNH BỔ SUNG ---
    private double MIN_MOMENTUM_15M = 0.01750 ;      // 15M phải tăng cực mạnh > 1.35% (Key factor!)
    private double MIN_TREND_4H = 0.01680;          // 4H chỉ cần xanh nhẹ > 0.35% là được
    private double DEAD_TREND_24H = -0.05;          // 24H sập quá 5% thì né (Giữ nguyên)


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
                prediction.return1H,
                prediction.return4H,
                prediction.return24H,
                prediction.riskDrawdown4H
        );
    }

    // --- HỖ TRỢ V2 (AiPredictionData cũ) ---
    public FilterResult checkSignal(AiPredictionData prediction) {
        return evaluate(
                prediction.predReturn15M,
                prediction.predReturn1H,
                prediction.predReturn4H,
                prediction.predReturn24H,
                prediction.predRisk4H
        );
    }

    // Hàm thiết lập tham số nhanh cho bộ tối ưu (Backtest Engine gọi vào đây)
    public void setConfig(double risk, double min1h, double highRet, double min15m, double min4h, double dead24h) {
        HARD_RISK_LIMIT = risk;
        MIN_PRED_RETURN_1H = min1h;
        HIGH_RETURN_THRESHOLD = highRet;
        MIN_MOMENTUM_15M = min15m;
        MIN_TREND_4H = min4h;
        DEAD_TREND_24H = dead24h;
    }

    /**
     * LOGIC ĐÁNH GIÁ CHUNG CHO MỌI PHIÊN BẢN
     */
    private FilterResult evaluate(double pred15M, double pred1H, double pred4H, double pred24H, double risk4H) {

        // 1. KIỂM TRA SINH TỒN (Risk vs Reward)
        if (risk4H <= HARD_RISK_LIMIT) {
            // Nếu rủi ro cao (sâu hơn -5.6%), chỉ vào nếu lợi nhuận cực khủng (> 8.5%)
            if (pred1H > HIGH_RETURN_THRESHOLD) {
                return new FilterResult(FilterDecision.PASS, "HIGH RISK HIGH REWARD: Chấp nhận rủi ro để ăn dày");
            }
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: MaxDD %.2f%% quá cao (Limit %.2f%%), Return %.2f%% không đủ bù",
                            risk4H * 100, HARD_RISK_LIMIT * 100, pred1H * 100));
        }

        // 2. KIỂM TRA LỰC CHÍNH (1H)
        if (pred1H <= MIN_PRED_RETURN_1H) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("WEAK 1H: Lãi %.2f%% < %.2f%% (Sideway/Yếu)", pred1H * 100, MIN_PRED_RETURN_1H * 100));
        }

        // 3. KIỂM TRA ĐÀ TĂNG NGẮN HẠN (15M) - QUAN TRỌNG NHẤT
        // HPO yêu cầu 15M phải > 1.35%. Nếu chưa hồi mạnh -> Reject.
        if (pred15M < MIN_MOMENTUM_15M) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("BAD MOMENTUM: 1H ngon nhưng 15M chưa nảy mạnh (%.2f%% < %.2f%%) -> Chờ xác nhận thêm",
                            pred15M * 100, MIN_MOMENTUM_15M * 100));
        }

        // 4. KIỂM TRA XU HƯỚNG TRUNG HẠN (4H)
        // HPO hạ thấp tiêu chuẩn 4H xuống 0.35% -> Chỉ cần không sập là được.
        // Trừ khi 1H cực mạnh (> 3%) thì có thể phá trend.
        if (pred4H < MIN_TREND_4H && pred1H < 0.03) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("AGAINST TREND: 4H quá yếu (%.2f%% < %.2f%%) -> Ngược dòng nước",
                            pred4H * 100, MIN_TREND_4H * 100));
        }

        // 5. KIỂM TRA MACRO (24H)
        if (pred24H < DEAD_TREND_24H) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("MACRO DUMP: 24H quá xấu (%.2f%%) -> Không bắt dao rơi", pred24H * 100));
        }

        // PASS
        return new FilterResult(FilterDecision.PASS,
                String.format("PERFECT 198K: 15M(%.2f%%) -> 1H(%.2f%%) -> 4H(%.2f%%) | DD(%.2f%%)",
                        pred15M * 100, pred1H * 100, pred4H * 100, risk4H * 100));
    }
}