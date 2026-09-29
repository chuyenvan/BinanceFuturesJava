package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.tradecore.Configs;
import org.junit.Test;

import static org.junit.Assert.assertEquals;

/**
 * GDV2 (docs/prereg/PREREG_GDV2_EVEN.md) — khoá tính CAUSAL của quantile cuộn trên tỉ số r:
 * q_h tại giờ h CHỈ dùng r có ts &lt; h (không nhìn tương lai, không dùng r của chính ứng viên giờ h).
 */
public class GateRollingRatioTest {

    private static final long HOUR = 3600_000L;

    /** Warm-up: trước khi buffer đủ 7 ngày dữ liệu => fallback base (không ra phân vị). */
    @Test
    public void warmupFallsBackToBase() {
        GateRollingRatio.configureForTest(0.5f, 30);
        float q = GateRollingRatio.addAndQuery(0L, 1.0f);
        assertEquals(Configs.MIN_MOMENTUM_15M, q, 1e-6f);
    }

    /** Causal: r của ứng viên giờ h KHÔNG được dùng để tính q_h (chỉ các r có ts < h). */
    @Test
    public void ownHourSampleExcludedFromItsQuantile() {
        GateRollingRatio.configureForTest(0.5f, 30);
        GateRollingRatio.addAndQuery(0L, 1.0f);
        GateRollingRatio.addAndQuery(1L, 2.0f);
        GateRollingRatio.addAndQuery(2L, 3.0f);
        float q = GateRollingRatio.addAndQuery(200L * HOUR, 0.0f);
        assertEquals(2.0f, q, 1e-6f);
    }

    /** Causal theo chiều thuận: mẫu giờ h ĐƯỢC dùng cho q_{h+1} (đã "đóng" thành quá khứ). */
    @Test
    public void pastHourSampleFeedsNextHourQuantile() {
        GateRollingRatio.configureForTest(0.5f, 30);
        GateRollingRatio.addAndQuery(0L, 1.0f);
        GateRollingRatio.addAndQuery(1L, 3.0f);
        GateRollingRatio.addAndQuery(2L, 100.0f);
        float q = GateRollingRatio.addAndQuery(200L * HOUR, 7.0f);
        assertEquals(3.0f, q, 1e-6f);
        float q2 = GateRollingRatio.addAndQuery(201L * HOUR, 0.0f);
        assertEquals(3.0f, q2, 1e-6f);
    }

    /** Phân vị theo convention floor(pct*(m-1)) (0-based, nearest-rank). */
    @Test
    public void percentileNearestRankConvention() {
        GateRollingRatio.configureForTest(0.9f, 30);
        for (int i = 0; i < 10; i++) GateRollingRatio.addAndQuery(i, (float) i);
        float q = GateRollingRatio.addAndQuery(200L * HOUR, -1.0f);
        assertEquals(8.0f, q, 1e-6f);
    }
}
