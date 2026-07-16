package com.binance.chuyennd.ai_ml.validation.preflight;

/**
 * Mức nghiêm trọng của một kết quả validate trong Data Preflight Gate.
 *
 * <p>Theo {@code docs/DATA_VALIDATION_FRAMEWORK.md} §2: mỗi loại lỗi khai báo mức mặc định
 * là {@link #BLOCK} (fail = DỪNG, không cho HPO/WFO chạy) hoặc {@link #WARN}
 * (ghi report, vẫn cho chạy). Ngưỡng BLOCK/WARN từng loại là ĐỀ XUẤT — chờ Uni chốt (§4).</p>
 */
public enum Severity {
    /** Lỗi nghiêm trọng: fail-fast, chặn HPO/WFO khởi động. */
    BLOCK,
    /** Cảnh báo: ghi vào report nhưng KHÔNG chặn chạy. */
    WARN
}
