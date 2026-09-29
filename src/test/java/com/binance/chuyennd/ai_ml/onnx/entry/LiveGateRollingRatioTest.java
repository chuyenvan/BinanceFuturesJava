package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.tradecore.Configs;
import org.junit.After;
import org.junit.Test;

import java.util.Random;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * LIVE gate ratio (GDV2) — parity sim↔live (bit-identical q_t), causal, warm-up, off-by-default.
 *
 * <p>Parity là CẤP CLASS: cùng chuỗi (ts, r) đầu vào ⇒ q_t và quyết định pass bit-identical giữa
 * {@link GateRollingRatio} (sim) và {@link LiveGateRollingRatio} (live) — nhờ dùng CHUNG {@link GateRatioBuffer}.
 */
public class LiveGateRollingRatioTest {

    private static final long HOUR = 3600_000L;
    private static final long MIN = 60_000L;

    @After
    public void tearDown() {
        GateRollingRatio.configureForTest(0.5f, 30);   // reset sim về trạng thái xác định
        LiveGateRollingRatio.resetForTest();
    }

    /** Warm-up: trước khi buffer đủ 7 ngày ⇒ fallback base. */
    @Test
    public void warmupFallsBackToBase() {
        LiveGateRollingRatio.configureForTest(0.5f, 30);
        float q = LiveGateRollingRatio.addAndQuery(0L, 1.0f);
        assertEquals(Configs.MIN_MOMENTUM_15M, q, 1e-6f);
    }

    /** Causal: r của ứng viên giờ h KHÔNG được dùng để tính q_h. */
    @Test
    public void ownHourSampleExcludedFromItsQuantile() {
        LiveGateRollingRatio.configureForTest(0.5f, 30);
        LiveGateRollingRatio.addAndQuery(0L, 1.0f);
        LiveGateRollingRatio.addAndQuery(1L, 2.0f);
        LiveGateRollingRatio.addAndQuery(2L, 3.0f);
        float q = LiveGateRollingRatio.addAndQuery(200L * HOUR, 0.0f);
        assertEquals(2.0f, q, 1e-6f);
    }

    /** TẮT khi chưa khởi tạo / không có key. */
    @Test
    public void offByDefaultBeforeInit() {
        LiveGateRollingRatio.resetForTest();
        assertFalse(LiveGateRollingRatio.isOn());
    }

    /** Bật khi configureForTest (dùng cho parity). */
    @Test
    public void onAfterConfigureForTest() {
        LiveGateRollingRatio.configureForTest(0.5f, 30);
        assertTrue(LiveGateRollingRatio.isOn());
    }

    /**
     * PARITY: cùng chuỗi (ts, r) (≈31 ngày, warm-up → armed) ⇒ q_t bit-identical giữa sim và live.
     * Dùng floatToIntBits để bắt mọi sai khác 1 ULP.
     */
    @Test
    public void paritySimLiveBitIdenticalOverOneMonth() {
        float pct = 0.99995083f;
        int days = 90;
        GateRollingRatio.configureForTest(pct, days);
        LiveGateRollingRatio.configureForTest(pct, days);

        long base = 1_700_000_000_000L;
        Random rnd = new Random(20260929L);
        int total = 31 * 24 * 60;   // 31 ngày, 1 mẫu/phút
        for (int i = 0; i < total; i++) {
            long ts = base + i * MIN;
            float r = rnd.nextFloat() * 0.01f;
            float qSim = GateRollingRatio.addAndQuery(ts, r);
            float qLive = LiveGateRollingRatio.addAndQuery(ts, r);
            assertEquals("q_t lệch tại i=" + i + " (ts=" + ts + ")",
                    Float.floatToIntBits(qSim), Float.floatToIntBits(qLive));
        }
    }

    /**
     * PARITY qua threshold: cùng (ts, p15, sp) ⇒ cùng r ⇒ cùng q_t (đường dùng thật của entryGate).
     * Không gọi appendRecord ở đây (không cần persist cho parity core).
     */
    @Test
    public void parityThresholdSameQ() {
        float pct = 0.9f;
        int days = 90;
        GateRollingRatio.configureForTest(pct, days);
        LiveGateRollingRatio.configureForTest(pct, days);

        // warm-up: nạp đủ 7 ngày (giờ 0..7×24) với r tăng dần
        for (long h = 0; h < 8 * 24; h++) {
            long ts = h * HOUR;
            float sp = 0.3f;
            float p15 = 0.008f + (h % 50) * 0.0001f;
            float qSim = GateRollingRatio.threshold(ts, p15, sp);
            float qLive = LiveGateRollingRatio.threshold(ts, p15, sp);
            assertEquals("threshold q lệch tại h=" + h,
                    Float.floatToIntBits(qSim), Float.floatToIntBits(qLive));
        }
    }
}
