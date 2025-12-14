package com.binance.chuyennd.ai_ml.onnx; // Lưu ý package

import com.binance.chuyennd.ai_ml.v3.AiPredictionDataV3;
import com.binance.chuyennd.ai_ml.v3.OnnxInferenceManagerV3;
import com.binance.chuyennd.ai_ml.v4.AiPredictionDataV4;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class AIRejectFilter {
    private static final Logger LOG = LoggerFactory.getLogger(AIRejectFilter.class);

    // --- CẤU HÌNH 1: CORE (1H & RISK) ---
    // --- Test #22 / 50 --- [Risk: -0.0262 | 1H: 0.0213 | 15M: 0.0044 | 4H: -0.0024]

    private  double HARD_RISK_LIMIT = -0.0262; // -0.04;     // Sập > 5% là Rủi ro cao
    private  double MIN_PRED_RETURN_1H = 0.0213; //0.01;   // Lãi 1H tối thiểu 1%
    private  double HIGH_RETURN_THRESHOLD = 0.04;// Lãi > 4% là Kèo Siêu Thơm

    // --- CẤU HÌNH 2: BỔ SUNG (15M, 4H, 24H) ---
    private  double MIN_MOMENTUM_15M = 0.001;    // 15M phải tăng ít nhất 0.1% (Đang có đà)
    private  double MIN_TREND_4H = 0.005;        // 4H phải tăng ít nhất 0.5% (Thuận xu hướng)
    private  double DEAD_TREND_24H = -0.05;      // 24H sập quá 5% thì né ra (Downtrend dài)

    public enum FilterDecision {PASS, REJECT}

    public static class FilterResult {
        public FilterDecision decision;
        public String reason;

        public FilterResult(FilterDecision decision, String reason) {
            this.decision = decision;
            this.reason = reason;
        }
    }

    public  FilterResult checkSignal(OnnxInferenceManager.PredictionResult prediction) {
        // Lấy đủ 4 chỉ số Return và 1 chỉ số Risk
        return evaluate(
                prediction.return15M,
                prediction.return1H,
                prediction.return4H,
                prediction.return24H,
                prediction.riskDrawdown4H
        );
    }
    public FilterResult checkSignalV3(AiPredictionDataV3 prediction) {
        return evaluate(
                prediction.p15M,
                prediction.p1H,
                prediction.p4H,
                0.0f, // V3 không có 24H -> Truyền 0.0 để bỏ qua check 24H
                prediction.maxDD4H // Map maxDrawdown4H vào Risk
        );
    }
    public FilterResult checkSignalV4(AiPredictionDataV4 prediction) {
        return evaluate(
                prediction.p15M,
                prediction.p1H,
                prediction.p4H,
                prediction.p24H,
                prediction.maxDD4H // Map maxDrawdown4H vào Risk
        );
    }
    public  FilterResult checkSignal(AiPredictionData prediction) {
        // Lấy đủ 4 chỉ số Return và 1 chỉ số Risk
        return evaluate(
                prediction.predReturn15M,
                prediction.predReturn1H,
                prediction.predReturn4H,
                prediction.predReturn24H,
                prediction.predRisk4H
        );
    }

    // Hàm thiết lập tham số nhanh cho bộ tối ưu
    public  void setConfig(double risk, double min1h, double highRet, double min15m, double min4h, double dead24h) {
        HARD_RISK_LIMIT = risk;
        MIN_PRED_RETURN_1H = min1h;
        HIGH_RETURN_THRESHOLD = highRet;
        MIN_MOMENTUM_15M = min15m;
        MIN_TREND_4H = min4h;
        DEAD_TREND_24H = dead24h;
    }

    private  FilterResult evaluate(double pred15M, double pred1H, double pred4H, double pred24H, double risk4H) {

        // ---------------------------------------------------------
        // BƯỚC 1: KIỂM TRA SINH TỒN (Risk vs Reward Khủng)
        // ---------------------------------------------------------
        if (risk4H <= HARD_RISK_LIMIT) {
            // Nếu Rủi ro cao (sập > 5%), chỉ vào nếu Lợi nhuận cực khủng (> 4%)
            if (pred1H > HIGH_RETURN_THRESHOLD) {
                return new FilterResult(FilterDecision.PASS, "HIGH RISK HIGH REWARD: Chấp nhận rủi ro để ăn dày");
            }
            return new FilterResult(FilterDecision.REJECT, String.format("DANGER: Risk %.2f%% quá cao, Return %.2f%% không đủ bù", risk4H * 100, pred1H * 100));
        }

        // ---------------------------------------------------------
        // BƯỚC 2: KIỂM TRA LỰC CHÍNH (1H)
        // ---------------------------------------------------------
        if (pred1H <= MIN_PRED_RETURN_1H) {
            return new FilterResult(FilterDecision.REJECT, String.format("WEAK 1H: Lãi %.2f%% < 1%% (Sideway)", pred1H * 100));
        }

        // ---------------------------------------------------------
        // BƯỚC 3: KIỂM TRA ĐÀ TĂNG NGẮN HẠN (15M Check)
        // ---------------------------------------------------------
        // Nếu 1H ngon nhưng 15M đang xìu (< 0.1%), coi chừng là đỉnh sóng hồi
        if (pred15M < MIN_MOMENTUM_15M) {
            return new FilterResult(
                    FilterDecision.REJECT,
                    String.format("BAD MOMENTUM: 1H ngon nhưng 15M yếu (%.2f%%) -> Dễ bị Bull Trap", pred15M * 100)
            );
        }

        // ---------------------------------------------------------
        // BƯỚC 4: KIỂM TRA XU HƯỚNG TRUNG HẠN (4H Check)
        // ---------------------------------------------------------
        // Nếu 1H ngon nhưng 4H lại đỏ hoặc tăng quá yếu (< 0.5%),
        // chứng tỏ đây chỉ là cú nảy con mèo chết (Dead Cat Bounce)
        // TRỪ KHI: 1H cực mạnh (> 3%) thì có thể phá trend 4H -> Cho qua
        if (pred4H < MIN_TREND_4H && pred1H < 0.03) {
            return new FilterResult(
                    FilterDecision.REJECT,
                    String.format("AGAINST TREND: 4H yếu (%.2f%%) -> Ngược dòng nước", pred4H * 100)
            );
        }

        // ---------------------------------------------------------
        // BƯỚC 5: KIỂM TRA "THIÊN NGA ĐEN" DÀI HẠN (24H Check)
        // ---------------------------------------------------------
        // Nếu 24H dự báo sập hầm > 5%, thì mọi cú hồi 1H đều là để bán
        if (pred24H < DEAD_TREND_24H) {
            return new FilterResult(
                    FilterDecision.REJECT,
                    String.format("MACRO DUMP: 24H quá xấu (%.2f%%) -> Không bắt dao", pred24H * 100)
            );
        }

        // ---------------------------------------------------------
        // PASS: HỘI TỤ ĐỦ CÁC YẾU TỐ
        // ---------------------------------------------------------
        return new FilterResult(
                FilterDecision.PASS,
                String.format("PERFECT: 15M(%.2f%%) -> 1H(%.2f%%) -> 4H(%.2f%%)", pred15M * 100, pred1H * 100, pred4H * 100)
        );
    }
}