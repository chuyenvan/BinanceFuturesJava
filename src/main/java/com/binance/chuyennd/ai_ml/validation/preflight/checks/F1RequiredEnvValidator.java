package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * F1 — Chặn "env thiếu → fallback im lặng".
 *
 * <p>Đây là VALIDATOR MẪU (template cho 18 loại còn lại — task 201-205): stateless, chỉ đọc
 * {@link PreflightContext}, trả {@link ValidationResult} KÈM SỐ ĐO, KHÔNG PASS suông.</p>
 *
 * <p>Bài học nền ({@code DATA_VALIDATION_FRAMEWORK §5.8}): thiếu {@code WFO_SMART_CACHE} → route
 * sang cache 18 tháng, zero-trade window CÂM; {@code WFO_FUNDING_PRED_DIR} rỗng → fallback set leaky.
 * Env bắt buộc mà thiếu = fail-fast, KHÔNG cho fallback lặng.</p>
 */
public final class F1RequiredEnvValidator implements DataValidator {

    /** Env bắt buộc phải có TRƯỚC khi WFO/HPO chạy (mở rộng khi Uni chốt §6). */
    private static final List<String> REQUIRED_ENV = Arrays.asList(
            "WFO_DATA_DIR",
            "WFO_FUNDING_PRED_DIR",
            "WFO_SMART_CACHE"
    );

    @Override
    public CheckId id() {
        return CheckId.F1;
    }

    /**
     * Kiểm mọi env bắt buộc có mặt và không rỗng.
     *
     * @param ctx ngữ cảnh (đọc env đã nạp)
     * @return FAIL (BLOCK) nếu thiếu bất kỳ env nào; PASS kèm danh sách env đã có
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        List<String> missing = new ArrayList<>();
        Map<String, Object> metrics = new LinkedHashMap<>();
        for (String key : REQUIRED_ENV) {
            // 2026-09-03: WFO_FUNDING_PRED_DIR nay khai trong TRADING_PROFILE chu khong con
            // trong env => coi profile la nguon hop le, khong bao MISSING oan.
            String val = com.binance.chuyennd.tradecore.Cfg.getOr(key, ctx.env(key));
            boolean present = val != null && !val.trim().isEmpty();
            metrics.put(key, present ? "set" : "MISSING");
            if (!present) {
                missing.add(key);
            }
        }
        metrics.put("required", REQUIRED_ENV.size());
        metrics.put("missing", missing.size());
        if (!missing.isEmpty()) {
            return ValidationResult.fail(id(),
                    "Thiếu env bắt buộc (cấm fallback im lặng): " + missing, metrics);
        }
        return ValidationResult.pass(id(), "Đủ " + REQUIRED_ENV.size() + " env bắt buộc.", metrics);
    }
}
