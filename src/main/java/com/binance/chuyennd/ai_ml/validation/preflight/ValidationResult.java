package com.binance.chuyennd.ai_ml.validation.preflight;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Kết quả BẤT BIẾN của một lần chạy {@link DataValidator}.
 *
 * <p>Nguyên tắc "đo không đoán" ({@code DATA_VALIDATION_FRAMEWORK.md} §1): mọi verdict phải kèm
 * SỐ ĐO ({@link #metrics}) để người/script đối chiếu — KHÔNG để validator tự tuyên "PASS" suông.
 * Dùng {@link #pass}, {@link #fail}, {@link #warn} để tạo.</p>
 */
public final class ValidationResult {

    private final CheckId checkId;
    private final boolean passed;
    private final Severity severity;
    private final String message;
    private final Map<String, Object> metrics;

    private ValidationResult(CheckId checkId, boolean passed, Severity severity,
                             String message, Map<String, Object> metrics) {
        this.checkId = checkId;
        this.passed = passed;
        this.severity = severity;
        this.message = message == null ? "" : message;
        this.metrics = metrics == null ? new LinkedHashMap<>() : new LinkedHashMap<>(metrics);
    }

    /**
     * Tạo kết quả PASS.
     *
     * @param id      loại check
     * @param message mô tả ngắn (kèm số nếu có)
     * @param metrics số đo đối chiếu (nullable)
     * @return kết quả passed=true
     */
    public static ValidationResult pass(CheckId id, String message, Map<String, Object> metrics) {
        return new ValidationResult(id, true, id.defaultSeverity(), message, metrics);
    }

    /**
     * Tạo kết quả FAIL với mức mặc định của check.
     *
     * @param id      loại check
     * @param message lý do fail (kèm số)
     * @param metrics số đo đối chiếu (nullable)
     * @return kết quả passed=false, severity = mặc định của {@code id}
     */
    public static ValidationResult fail(CheckId id, String message, Map<String, Object> metrics) {
        return new ValidationResult(id, false, id.defaultSeverity(), message, metrics);
    }

    /**
     * Tạo kết quả FAIL ở mức WARN (dùng khi Uni chốt loại này chỉ cảnh báo).
     *
     * @param id      loại check
     * @param message lý do (kèm số)
     * @param metrics số đo đối chiếu (nullable)
     * @return kết quả passed=false, severity=WARN
     */
    public static ValidationResult warn(CheckId id, String message, Map<String, Object> metrics) {
        return new ValidationResult(id, false, Severity.WARN, message, metrics);
    }

    /** @return true nếu check ĐẶT (không có lỗi). */
    public boolean passed() {
        return passed;
    }

    /** @return true nếu FAIL ở mức BLOCK (gate phải DỪNG). */
    public boolean isBlockingFailure() {
        return !passed && severity == Severity.BLOCK;
    }

    /** @return loại check. */
    public CheckId checkId() {
        return checkId;
    }

    /** @return mức nghiêm trọng của kết quả này. */
    public Severity severity() {
        return severity;
    }

    /** @return mô tả người-đọc. */
    public String message() {
        return message;
    }

    /** @return số đo đối chiếu (bản sao bất biến). */
    public Map<String, Object> metrics() {
        return new LinkedHashMap<>(metrics);
    }

    @Override
    public String toString() {
        return String.format("[%s] %s %s | %s | %s",
                checkId, severity, passed ? "PASS" : "FAIL", message, metrics);
    }
}
