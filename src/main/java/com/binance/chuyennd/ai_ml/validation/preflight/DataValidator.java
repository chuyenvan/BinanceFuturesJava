package com.binance.chuyennd.ai_ml.validation.preflight;

/**
 * Contract cho MỘT loại check trong Data Preflight Gate (19 loại — {@link CheckId}).
 *
 * <p>Mỗi validator = 1 class riêng (đúng thiết kế "mỗi loại 1 class"), stateless, chỉ đọc dữ liệu
 * (KHÔNG sửa/ghi data thật). Ném exception = lỗi hạ tầng (client null, file thiếu) → gate coi là
 * NEEDS_HUMAN, KHÔNG suy diễn PASS. Trả {@link ValidationResult} passed=false = phát hiện lỗi dữ liệu.</p>
 */
public interface DataValidator {

    /** @return loại lỗi mà validator này phụ trách. */
    CheckId id();

    /**
     * Chạy check trên ngữ cảnh cho trước.
     *
     * @param ctx handle Aerospike/đường dẫn/expected ranges (không tự lấy riêng — chống lệch nguồn)
     * @return kết quả kèm SỐ ĐO để đối chiếu; KHÔNG được trả PASS suông không số
     * @throws Exception khi lỗi hạ tầng (I/O, client) — gate xử lý thành NEEDS_HUMAN
     */
    ValidationResult validate(PreflightContext ctx) throws Exception;

    /**
     * @return true nếu check ĐẮT (random-sample phân tầng). Mặc định lấy từ {@link CheckId#expensive()};
     *         override nếu implementation thực tế khác.
     */
    default boolean expensive() {
        return id().expensive();
    }
}
