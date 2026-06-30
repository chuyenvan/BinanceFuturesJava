package com.binance.chuyennd.ai_ml.wfo.framework;

/**
 * WFO FRAMEWORK — NGỮ CẢNH dùng chung trong MỘT worker JVM, tái dùng giữa nhiều job (không load lại
 * dataset/ONNX mỗi job). Worker tạo 1 lần, truyền vào mọi {@link WfoTask#runJob}.
 *
 * <p>dataset = 3 khối offline (load 1 lần/JVM). Các tài nguyên nặng khác (ONNX cache cho model-WFO)
 * có thể thêm sau mà không đổi interface.
 */
public class WfoContext {
    public final WfoDataset dataset;
    public final String workerId;   // host/pid định danh worker (cho lease/owner)

    public WfoContext(WfoDataset dataset, String workerId) {
        this.dataset = dataset;
        this.workerId = workerId;
    }
}
