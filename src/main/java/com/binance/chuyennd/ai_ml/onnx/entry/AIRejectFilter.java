package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * Lọc tín hiệu entry dựa trên AI prediction.
 * Mode (Configs.FILTER_MODE):
 *   A   = full (RISK + MOM15) — baseline live
 *   B   = bỏ RISK (backward-compat ablation cũ)
 *   C   = giữ RISK, MOM24 đã bỏ (backward-compat, tương đương A)
 *   D   = bỏ RISK (backward-compat ablation cũ)
 *   E   = tắt MOM15, giữ RISK — đo riêng tác dụng gate 15m
 *   F   = chỉ MOM15, bỏ RISK — gate 15m standalone
 *   OFF = tắt hết filter — sàn tuyệt đối
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
    /** Tách nhánh: REJECT do risk 4H (risk4H<=thresRisk). */
    public static final AtomicInteger riskReject = new AtomicInteger(0);

    /** Reset counter trước mỗi ablation run. */
    public static void resetCounters() {
        mom15RejectCount.set(0);
        earlyHardGateReject.set(0);
        riskReject.set(0);
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

        // EARLY check — chỉ chạy khi gate MOM15 bật
        if (resolveCheckMom15(Configs.FILTER_MODE)
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
        float dynamic_Risk4H = Configs.HARD_RISK_LIMIT_4H / scaleFactor;
        return evaluate(prediction.predReturn15M, prediction.predRisk4H, dynamic_15M, dynamic_Risk4H);
    }

    public void setConfig(float risk, float min15m) {
        Configs.HARD_RISK_LIMIT_4H = risk;
        Configs.MIN_MOMENTUM_15M = min15m;
    }

    /**
     * LOGIC ĐÁNH GIÁ LÕI — 2 nhánh: RISK (DD4H) + MOM15. MOM24 đã bỏ hẳn khỏi hệ.
     * Mode A/C: checkRisk=true checkMom15=true.
     * Mode B/D: checkRisk=false (backward-compat). Mode E: checkMom15=false.
     * Mode F: chỉ MOM15 (checkRisk=false). Mode OFF: tắt hết.
     */
    private FilterResult evaluate(float pred15M, float risk4H, float thres15M, float thresRisk) {
        String mode = Configs.FILTER_MODE;
        boolean checkRisk  = resolveCheckRisk(mode);
        boolean checkMom15 = resolveCheckMom15(mode);

        if (checkRisk && risk4H <= thresRisk) {
            riskReject.incrementAndGet();
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: MaxDD 4H %.2f%% quá cao (Limit %.2f%%)", risk4H * 100, thresRisk * 100));
        }
        if (checkMom15 && pred15M < thres15M) {
            mom15RejectCount.incrementAndGet();
            return new FilterResult(FilterDecision.REJECT,
                    String.format("BAD MOMENTUM: 15M chưa nảy mạnh (%.2f%% < %.2f%%)", pred15M * 100, thres15M * 100));
        }
        return new FilterResult(FilterDecision.PASS,
                String.format("PERFECT: 15M(%.2f%%) | DD4H(%.2f%%)", pred15M * 100, risk4H * 100));
    }

    /** RISK bật cho mode A, C; tắt cho B, D, F, OFF. E: giữ RISK (tắt MOM15). */
    static boolean resolveCheckRisk(String mode) {
        return !("B".equals(mode) || "D".equals(mode) || "F".equals(mode) || "OFF".equals(mode));
    }

    /** MOM15 tắt cho mode E, OFF; bật cho tất cả còn lại (kể cả F = chỉ MOM15). */
    static boolean resolveCheckMom15(String mode) {
        return !("E".equals(mode) || "OFF".equals(mode));
    }
}
