package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.tradecore.Configs;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * D3 — Chặn OFF-BY-ONE nến (dùng close nến CHƯA chốt = look-ahead nội nến).
 *
 * <p>Cơ chế (VERIFY, rẻ, KHÔNG chạm Aerospike): đọc cờ static {@link Configs#BLOCK_INTRABAR_LOOKAHEAD}.
 * Cờ này phải luôn {@code true} khi backtest/sim/WFO thật — đặt {@code false} chỉ để đo "trước/sau khi
 * bịt" ({@code Configs} L133-136). Nếu cờ = false lúc chạy WFO thì mọi PnL có thể chứa ảo giác
 * look-ahead → verdict vô nghĩa.</p>
 *
 * <p>Nguồn canonical: {@code DATA_VALIDATION_FRAMEWORK §2 (D3)} — mức BLOCK. Đây là loại VERIFY-flag
 * (không quét dữ liệu), tương ứng {@code BacktestIntegrityGuard} trong bản đồ code
 * ({@code VALIDATION_TEST_ROADMAP §2}).</p>
 */
public final class D3IntrabarLookaheadValidator implements DataValidator {

    @Override
    public CheckId id() {
        return CheckId.D3;
    }

    /**
     * Kiểm cờ {@link Configs#BLOCK_INTRABAR_LOOKAHEAD} đang bật.
     *
     * @param ctx ngữ cảnh (không dùng — check này chỉ đọc cờ static)
     * @return PASS nếu cờ = true; FAIL (BLOCK) nếu cờ = false (đang mở đường look-ahead nội nến)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        boolean guardOn = Configs.BLOCK_INTRABAR_LOOKAHEAD;

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("BLOCK_INTRABAR_LOOKAHEAD", guardOn);
        metrics.put("expected", Boolean.TRUE);

        if (!guardOn) {
            return ValidationResult.fail(id(),
                    "Configs.BLOCK_INTRABAR_LOOKAHEAD = false — guard look-ahead nội nến ĐANG TẮT: "
                            + "PnL/verdict có thể chứa ảo giác look-ahead. Bật lại = true trước khi WFO/HPO.",
                    metrics);
        }
        return ValidationResult.pass(id(),
                "Guard look-ahead nội nến BẬT (BLOCK_INTRABAR_LOOKAHEAD = true).", metrics);
    }
}
