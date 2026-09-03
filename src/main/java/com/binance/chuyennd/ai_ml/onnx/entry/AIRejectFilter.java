package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * Lọc tín hiệu entry dựa trên AI prediction.
 *
 *
 */
// 2026-09-03: filter chi con MOT cong duy nhat = MOM15 (nguong dong theo score selector).
//   Nhanh RISK/DD4H bo 2026-08-08; cac co FILTER_MODE / gate-market-off / gate-rolling xoa 2026-09-03.
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

    /** Đếm số REJECT do gate MOM15 trong một ablation run. Reset bằng resetCounters() trước mỗi run. */
    public static final AtomicInteger mom15RejectCount = new AtomicInteger(0);
    /** Tách nhánh: REJECT do early-hard-gate (pred15M<MIN & symbolPred>RATE_MAX). */
    public static final AtomicInteger earlyHardGateReject = new AtomicInteger(0);

    /** Reset counter trước mỗi ablation run. */
    public static void resetCounters() {
        mom15RejectCount.set(0);
        earlyHardGateReject.set(0);
    }

    /**
     * Nguong CO SO cua gate MOM15. Nhanh B4 (docs/PREREG_B4.md, commit a0c7ad6): neu
     * {@link GateRollingThreshold} bat thi lay nguong TRUOT theo phan vi tai thoi diem cua
     * prediction; khong bat thi HANG SO Configs.MIN_MOMENTUM_15M => byte-identical voi C2b.
     */
    static float thres15M(AiPredictionData prediction) {
        return GateRollingThreshold.isOn()
                ? GateRollingThreshold.threshold(prediction.timestamp)
                : Configs.MIN_MOMENTUM_15M;
    }

    public FilterResult checkSignal(AiPredictionData prediction) {
        return evaluate(prediction.predReturn15M, thres15M(prediction));
    }

    // ==============================================================
    // LUỒNG 2: DÙNG RIÊNG CHO PREDICT_SYMBOL_TRADE (ĐỘNG)
    // ==============================================================
    public FilterResult checkSignalDynamic(AiPredictionData prediction, Float symbolPred) {
        if (symbolPred == null) {
            return checkSignal(prediction); // Fallback về cứng nếu lỗi
        }

        // EARLY check — chỉ chạy khi gate MOM15 bật
        if (prediction.predReturn15M < thres15M(prediction)
                && symbolPred > Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD) {
            mom15RejectCount.incrementAndGet();
            earlyHardGateReject.incrementAndGet();
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: pred 15m %.2f%% thap (Min %.2f%%)",
                            prediction.predReturn15M * 100, thres15M(prediction) * 100));
        }

        float baselineProb = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD;
        float scaleFactor = (symbolPred / baselineProb) * Configs.AI_DYNAMIC_MULTIPLIER;
        // AI_DYNAMIC_MAX KHONG phai tran clamp o day: no la TRAN UNG VIEN o tang 1 cua selector
        // (SimulatorMarketLevelTicker1MStopLoss). Gate chi con CAN DUOI. Xem docs/C2B_SPEC.md muc 0.
        scaleFactor = Math.max(Configs.AI_DYNAMIC_MIN, scaleFactor);
        float dynamic_15M = thres15M(prediction) * scaleFactor;
        return evaluate(prediction.predReturn15M, dynamic_15M);
    }

    /** Giữ signature cũ để không vỡ caller (BackTestEngineCombined/MarketThresholds/BenchmarkSpeedTest) —
     *  {@code risk} chỉ còn ghi vào HARD_RISK_LIMIT_4H (field da xoa) cho log/HPO đọc, KHÔNG còn dùng để lọc. */
    public void setConfig(float risk, float min15m) {
        // `risk` KHONG con duoc dung o dau ca (nhanh RISK/DD4H bo 2026-08-08, field xoa 2026-09-03);
        // giu tham so de khong phai sua 3 call-site HPO.
        Configs.MIN_MOMENTUM_15M = min15m;
    }

    /**
     * LOGIC ĐÁNH GIÁ LÕI — chỉ còn nhánh MOM15. Nhánh RISK (DD4H/predRisk4H) đã bỏ hẳn 2026-08-08:
     * predRisk4H không còn model đứng sau (carry-forward từ gate cũ), dùng làm lá chắn live là rủi ro giả.
     */
    private FilterResult evaluate(float pred15M, float thres15M) {
        if (pred15M < thres15M) {
            mom15RejectCount.incrementAndGet();
            return new FilterResult(FilterDecision.REJECT,
                    String.format("BAD MOMENTUM: 15M chưa nảy mạnh (%.2f%% < %.2f%%)", pred15M * 100, thres15M * 100));
        }
        return new FilterResult(FilterDecision.PASS,
                String.format("PERFECT: 15M(%.2f%%)", pred15M * 100));
    }

}
