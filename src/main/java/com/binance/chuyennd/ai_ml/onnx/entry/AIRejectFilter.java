package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * Lọc tín hiệu entry dựa trên AI prediction.
 *
 * <p>TASK (2026-08-08): đã bỏ hẳn nhánh RISK/DD4H dựa trên {@code predRisk4H} — cột này không
 * còn model nào đứng sau (chỉ là carry-forward từ gate cũ, không phải dự đoán mới), giữ lại làm
 * lá chắn live là rủi ro giả. Filter bây giờ CHỈ còn gate MOM15. {@code Configs.FILTER_MODE} và
 * {@code Configs.HARD_RISK_LIMIT_4H} vẫn còn tồn tại (dùng bởi HPO/genome ở nơi khác, xoá sẽ lệch
 * index gene) nhưng KHÔNG còn ảnh hưởng quyết định PASS/REJECT ở đây nữa.
 *
 * Mode (Configs.FILTER_MODE) — chỉ còn tác dụng lên MOM15:
 *   E, OFF = tắt MOM15 (= tắt hết filter, vì RISK đã bỏ)
 *   mọi mode khác (A/B/C/D/F...) = bật MOM15 (RISK không còn phân biệt được các mode này nữa)
 */
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

    public FilterResult checkSignal(AiPredictionData prediction) {
        return evaluate(prediction.predReturn15M, Configs.MIN_MOMENTUM_15M);
    }

    // ==============================================================
    // LUỒNG 2: DÙNG RIÊNG CHO PREDICT_SYMBOL_TRADE (ĐỘNG)
    // ==============================================================
    public FilterResult checkSignalDynamic(AiPredictionData prediction, Float symbolPred) {
        if (symbolPred == null) {
            return checkSignal(prediction); // Fallback về cứng nếu lỗi
        }

        // EARLY check — chỉ chạy khi gate MOM15 bật
        if (!Configs.GATE_MARKET_OFF   // [2026-08-29 DEV pivot] tat gate MOM15 muc thi truong
                && resolveCheckMom15(Configs.FILTER_MODE)
                && prediction.predReturn15M < Configs.MIN_MOMENTUM_15M
                && symbolPred > Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD) {
            mom15RejectCount.incrementAndGet();
            earlyHardGateReject.incrementAndGet();
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: pred 15m %.2f%% thap (Min %.2f%%)",
                            prediction.predReturn15M * 100, Configs.MIN_MOMENTUM_15M * 100));
        }

        float baselineProb = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD;
        float scaleFactor = (symbolPred / baselineProb) * Configs.AI_DYNAMIC_MULTIPLIER;
        // [OFF-CỨNG] AI_DYNAMIC_MAX thuộc cụm phẳng → bỏ cận TRÊN clamp (chỉ còn cận dưới AI_DYNAMIC_MIN).
        if (Configs.OFF_FLAT_HARD) {
            scaleFactor = Math.max(Configs.AI_DYNAMIC_MIN, scaleFactor);
        } else {
            scaleFactor = Math.max(Configs.AI_DYNAMIC_MIN, Math.min(scaleFactor, Configs.AI_DYNAMIC_MAX));
        }
        float dynamic_15M = Configs.MIN_MOMENTUM_15M * scaleFactor;
        return evaluate(prediction.predReturn15M, dynamic_15M);
    }

    /** Giữ signature cũ để không vỡ caller (BackTestEngineCombined/MarketThresholds/BenchmarkSpeedTest) —
     *  {@code risk} chỉ còn ghi vào Configs.HARD_RISK_LIMIT_4H cho log/HPO đọc, KHÔNG còn dùng để lọc. */
    public void setConfig(float risk, float min15m) {
        Configs.HARD_RISK_LIMIT_4H = risk;
        Configs.MIN_MOMENTUM_15M = min15m;
    }

    /**
     * LOGIC ĐÁNH GIÁ LÕI — chỉ còn nhánh MOM15. Nhánh RISK (DD4H/predRisk4H) đã bỏ hẳn 2026-08-08:
     * predRisk4H không còn model đứng sau (carry-forward từ gate cũ), dùng làm lá chắn live là rủi ro giả.
     */
    private FilterResult evaluate(float pred15M, float thres15M) {
        boolean checkMom15 = resolveCheckMom15(Configs.FILTER_MODE);

        if (checkMom15 && pred15M < thres15M) {
            mom15RejectCount.incrementAndGet();
            return new FilterResult(FilterDecision.REJECT,
                    String.format("BAD MOMENTUM: 15M chưa nảy mạnh (%.2f%% < %.2f%%)", pred15M * 100, thres15M * 100));
        }
        return new FilterResult(FilterDecision.PASS,
                String.format("PERFECT: 15M(%.2f%%)", pred15M * 100));
    }

    /** MOM15 tắt cho mode E, OFF; bật cho tất cả còn lại (kể cả F). RISK đã bỏ nên không còn resolveCheckRisk. */
    static boolean resolveCheckMom15(String mode) {
        return !("E".equals(mode) || "OFF".equals(mode));
    }
}
