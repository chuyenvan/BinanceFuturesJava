package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * B3 — Chặn PURGE/EMBARGO NGẮN HƠN MAX HOLDING: khe embargo phải ≥ thời gian giữ lệnh lớn nhất
 * thực đo. Nếu embargo &lt; max holding, mẫu OOS đầu fold còn "dính" kết quả của lệnh mở trong vùng
 * train → rò rỉ tương lai (spec §2 nhóm B, {@code DATA_VALIDATION_FRAMEWORK §5.2}).
 *
 * <p><b>Cơ chế đo được ở tầng preflight:</b> so <b>embargo khai báo</b> (purge của pipeline,
 * mặc định 288 bước × 15m = 72h — {@code gen_funding_wf_predictions.py} PURGE_STEPS +
 * {@code WFO_DATAFLOW §2b}) với <b>max holding danh nghĩa</b> = cửa sổ của horizon selector đang
 * dùng ({@code WFO_SEL_HORIZON_IDX}: 0=4h,1=12h,2=24h,3=72h → 16/48/96/288 bước). Nếu embargo &lt;
 * horizon → FAIL ngay (không cần sim).</p>
 *
 * <p><b>TODO-verify (data thật):</b> "max holding THỰC ĐO" chuẩn phải lấy từ sim (thời gian giữ lệnh
 * dài nhất quan sát trong {@code StrategyWfoTask.runJob}), vì exit logic (SL/TP/timeout) có thể giữ
 * lệnh LÂU HƠN cửa sổ horizon danh nghĩa. Preflight không chạy sim nên chỉ kiểm được sàn danh nghĩa;
 * khi có thống kê holding thật, truyền vào (vd qua {@code ExpectedRanges}/env) để siết chặt. Đồng thời
 * xác nhận giá trị purge thật của pipeline (đọc env {@code PURGE_STEPS} nếu có, KHÔNG hardcode verdict).</p>
 */
public final class B3EmbargoValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(B3EmbargoValidator.class);

    /** 1 bar = 15 phút. Nguồn: {@code gen_funding_wf_predictions.py} GRID_MS. */
    private static final long GRID_MS = 15L * 60 * 1000;

    /** Purge/embargo mặc định (bước 15m). Nguồn: PURGE_STEPS=288 ({@code WFO_DATAFLOW §2b}). */
    private static final int DEFAULT_PURGE_STEPS = 288;

    /** Số bước 15m cho từng horizon selector (H_STEPS trong {@code gen_funding_wf_predictions.py}). */
    private static final int[] HORIZON_STEPS = {16, 48, 96, 288}; // 4h, 12h, 24h, 72h
    private static final String[] HORIZON_NAME = {"4h", "12h", "24h", "72h"};

    @Override
    public CheckId id() {
        return CheckId.B3;
    }

    @Override
    public boolean expensive() {
        return true;
    }

    /**
     * So embargo (purge) khai báo với max holding danh nghĩa của horizon đang dùng.
     *
     * @param ctx ngữ cảnh (đọc env {@code PURGE_STEPS}, {@code WFO_SEL_HORIZON_IDX})
     * @return FAIL (BLOCK) nếu embargo &lt; max holding; PASS kèm số bước/ms hai bên để đối chiếu
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        int purgeSteps = readIntEnv(ctx, "PURGE_STEPS", DEFAULT_PURGE_STEPS);
        int horizonIdx = readIntEnv(ctx, "WFO_SEL_HORIZON_IDX", 1); // mặc định 12h (khớp WFO_DATAFLOW §4)
        if (horizonIdx < 0 || horizonIdx >= HORIZON_STEPS.length) {
            // Cấu hình sai → coi là lỗi hạ tầng/cấu hình, KHÔNG đoán.
            throw new IllegalStateException("B3: WFO_SEL_HORIZON_IDX ngoài phạm vi [0..3]: " + horizonIdx);
        }
        int holdingSteps = HORIZON_STEPS[horizonIdx];
        long embargoMs = purgeSteps * GRID_MS;
        long holdingMs = holdingSteps * GRID_MS;

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("purgeSteps", purgeSteps);
        metrics.put("embargoMs", embargoMs);
        metrics.put("embargoHours", embargoMs / 3_600_000L);
        metrics.put("horizon", HORIZON_NAME[horizonIdx]);
        metrics.put("holdingSteps", holdingSteps);
        metrics.put("holdingMs", holdingMs);
        metrics.put("holdingHours", holdingMs / 3_600_000L);
        metrics.put("maxHoldingSource", "NOMINAL_HORIZON"); // TODO-verify: thay bằng đo thật từ sim.

        if (embargoMs < holdingMs) {
            return ValidationResult.fail(id(),
                    "Embargo (" + (embargoMs / 3_600_000L) + "h) < max holding danh nghĩa horizon "
                            + HORIZON_NAME[horizonIdx] + " (" + (holdingMs / 3_600_000L) + "h) — nguy cơ leak biên fold.",
                    metrics);
        }
        LOG.info("B3 OK: embargo {}h >= holding danh nghĩa {}h (horizon {}).",
                embargoMs / 3_600_000L, holdingMs / 3_600_000L, HORIZON_NAME[horizonIdx]);
        return ValidationResult.pass(id(),
                "Embargo (" + (embargoMs / 3_600_000L) + "h) >= max holding danh nghĩa ("
                        + (holdingMs / 3_600_000L) + "h). TODO: siết bằng holding THỰC ĐO từ sim.", metrics);
    }

    /**
     * Đọc env số nguyên với mặc định (không ném lỗi khi thiếu — dùng mặc định pipeline đã biết).
     *
     * @param ctx ngữ cảnh
     * @param key tên env
     * @param def giá trị mặc định
     * @return giá trị nguyên
     * @throws IllegalStateException nếu env có mặt nhưng không phải số (cấu hình hỏng → NEEDS_HUMAN)
     */
    private static int readIntEnv(PreflightContext ctx, String key, int def) {
        String v = ctx.env(key);
        if (v == null || v.trim().isEmpty()) {
            return def;
        }
        try {
            return Integer.parseInt(v.trim());
        } catch (NumberFormatException e) {
            throw new IllegalStateException("B3: env " + key + " không phải số: '" + v + "'", e);
        }
    }
}
