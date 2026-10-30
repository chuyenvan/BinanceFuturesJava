package com.binance.chuyennd.ai_ml.onnx.entry;

/** [V12 R4j] cau test cho package khac (chi test): bat/tat LiveGateRollingRatio va doc co buffer. */
public final class GateRatioTestSupport {

    private GateRatioTestSupport() {
    }

    public static void configure(float pct, int days) {
        LiveGateRollingRatio.configureForTest(pct, days);
    }

    public static int size() {
        return LiveGateRollingRatio.bufferSizeForTest();
    }

    public static void reset() {
        LiveGateRollingRatio.resetForTest();
    }
}
