package com.binance.chuyennd.ai_ml.wfo.framework;

import java.util.List;

/**
 * WFO FRAMEWORK — INTERFACE TỔNG (Uni chốt: "framework chung làm nền tảng kiểu interface tổng, các WFO
 * thực tế là implements chi tiết").
 *
 * <p>Một {@code WfoTask} mô tả MỘT loại WFO (strategy / model / ...). Framework (worker + coordinator)
 * không cần biết chi tiết — chỉ gọi 4 method dưới. Thêm loại WFO mới = thêm 1 implements, KHÔNG sửa
 * worker/coordinator.
 *
 * <p>Vòng đời:
 * <ol>
 *   <li>{@link #type()} — định danh loại (khớp {@code WfoJob.type}); worker dispatch theo đây.</li>
 *   <li>{@link #buildJobs()} — coordinator gọi 1 lần lúc init: sinh danh sách job (mỗi cửa sổ/fold = 1 job).</li>
 *   <li>{@link #runJob(WfoJob, WfoContext)} — worker gọi cho mỗi job đã claim: chạy → trả result JSON.</li>
 *   <li>{@link #aggregate(List)} — coordinator gọi khi tất cả DONE: gom result → verdict + report.</li>
 * </ol>
 *
 * <p>Mọi I/O nặng (load dataset, ONNX session) đi qua {@link WfoContext} để tái dùng giữa các job trong
 * cùng worker (không load lại mỗi job).
 */
public interface WfoTask {

    /** Định danh loại WFO, khớp WfoJob.type. Vd "strategy_window". */
    String type();

    /** Sinh danh sách job cho toàn chiến dịch WFO (mỗi cửa sổ/fold = 1 job). Chạy 1 lần lúc init. */
    List<WfoJob> buildJobs();

    /**
     * Chạy MỘT job đã claim. Trả result JSON (sẽ lưu vào job.result khi DONE).
     * Ném exception nếu lỗi → framework xử lý retry/FAILED.
     */
    String runJob(WfoJob job, WfoContext ctx) throws Exception;

    /**
     * Gom kết quả mọi job DONE → tính tổng hợp (WFE, %cửa-sổ-dương...) + VERDICT (PASS/FAIL theo ngưỡng
     * pre-registered) → trả report dạng Markdown (coordinator ghi file).
     */
    String aggregate(List<WfoJob> doneJobs);
}
