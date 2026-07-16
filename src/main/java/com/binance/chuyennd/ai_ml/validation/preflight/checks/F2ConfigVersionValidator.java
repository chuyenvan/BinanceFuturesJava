package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.hpo.master.RunHpoMaster_Distributed;
import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * F2 — Chặn CONFIG VERSION DRIFT.
 *
 * <p>Cơ chế (VERIFY, rẻ, KHÔNG chạm Aerospike): so {@code CONFIG_VERSION} hiện tại trong code
 * ({@link RunHpoMaster_Distributed#CONFIG_VERSION}) với giá trị MONG ĐỢI. Drift = code chạy version
 * X nhưng cache HPO/stamp lại của version Y → worker đọc điểm cũ trong {@code hpo_results_<ver>} =
 * run vô nghĩa (bài học nền: mỗi lần logic sim đổi thì bump version để bỏ cache, xem chuỗi comment
 * v10→v11→v12 trong {@code RunHpoMaster_Distributed}). {@code DATA_VALIDATION_FRAMEWORK §4b}: F2 nâng
 * WARN → BLOCK.</p>
 *
 * <p>Nguồn "expected": ưu tiên {@code ctx.env("EXPECTED_CONFIG_VERSION")} (do run/stamp bơm vào — đây
 * là nguồn ĐÚNG để bắt drift giữa dataset đã validate và code hiện tại). Nếu env KHÔNG có, fallback
 * so với baseline hằng số {@link #BASELINE_CONFIG_VERSION} (chép cứng version tại thời điểm viết
 * validator, 2026-07-11) — chỉ đủ bắt trường hợp ai đó sửa CONFIG_VERSION mà quên cập nhật baseline.</p>
 *
 * <p>TODO(verify): nguồn "expected" chuẩn PHẢI là pre-register (ValidationStamp / ExpectedRanges /
 * validate_criteria.md), KHÔNG phải hằng số chép tay. Khi cơ chế stamp bơm được version vào
 * {@code ctx.env}, xoá nhánh fallback baseline. Baseline hiện chép từ
 * {@code RunHpoMaster_Distributed.CONFIG_VERSION = "v12"}.</p>
 */
public final class F2ConfigVersionValidator implements DataValidator {

    /** Tên env chứa version mong đợi (do run/stamp bơm vào — nguồn ưu tiên). */
    private static final String ENV_EXPECTED_VERSION = "EXPECTED_CONFIG_VERSION";

    /**
     * Baseline chép cứng tại thời điểm viết (2026-07-11) — khớp
     * {@link RunHpoMaster_Distributed#CONFIG_VERSION}. TODO(verify): thay bằng nguồn pre-register.
     */
    private static final String BASELINE_CONFIG_VERSION = "v12";

    @Override
    public CheckId id() {
        return CheckId.F2;
    }

    /**
     * So {@code CONFIG_VERSION} hiện tại của code với version mong đợi.
     *
     * @param ctx ngữ cảnh (đọc env {@code EXPECTED_CONFIG_VERSION} nếu có)
     * @return PASS nếu khớp; FAIL (BLOCK) nếu drift. Khi thiếu env expected, so với baseline hằng số
     *         và kèm cảnh báo TODO trong message (không bịa PASS ngoài phạm vi kiểm được)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        String actual = RunHpoMaster_Distributed.CONFIG_VERSION;
        String envExpected = ctx.env(ENV_EXPECTED_VERSION);
        boolean fromEnv = envExpected != null && !envExpected.trim().isEmpty();
        String expected = fromEnv ? envExpected.trim() : BASELINE_CONFIG_VERSION;

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("actual", actual);
        metrics.put("expected", expected);
        metrics.put("expectedSource", fromEnv ? "env:" + ENV_EXPECTED_VERSION : "baseline-constant(TODO)");

        boolean match = actual != null && actual.equals(expected);
        if (!match) {
            return ValidationResult.fail(id(),
                    "CONFIG_VERSION drift: code = '" + actual + "' nhưng mong đợi = '" + expected
                            + "' (nguồn: " + metrics.get("expectedSource") + "). Cache HPO/stamp lệch version = "
                            + "run vô nghĩa — đồng bộ version hoặc bump/regen cache trước khi WFO/HPO.", metrics);
        }
        if (!fromEnv) {
            return ValidationResult.pass(id(),
                    "CONFIG_VERSION = '" + actual + "' khớp baseline hằng số. "
                            + "TODO: thiếu env " + ENV_EXPECTED_VERSION + " — chưa kiểm được drift so pre-register/stamp.",
                    metrics);
        }
        return ValidationResult.pass(id(),
                "CONFIG_VERSION = '" + actual + "' khớp expected từ env (" + ENV_EXPECTED_VERSION + ").", metrics);
    }
}
