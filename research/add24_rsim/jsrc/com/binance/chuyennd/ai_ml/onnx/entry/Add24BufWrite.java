package com.binance.chuyennd.ai_ml.onnx.entry;

import java.io.IOException;

/** ADD24 R-SIM (DEV-B, test-only): ghi buffer warm-up (ts, r) bang GateRatioPersist.writeFresh cua JAR. r tinh bang CUNG
 *  bieu thuc LiveGateRollingRatio.threshold (hang so EntryGate cua jar, nap tu env). */
public final class Add24BufWrite {
    private Add24BufWrite() {
    }

    public static float ratio(float p15, float sp) {
        float factor = Math.max(com.binance.chuyennd.tradecore.EntryGate.DYN_MIN,
                (sp / com.binance.chuyennd.tradecore.EntryGate.SCORE_BASE) * com.binance.chuyennd.tradecore.EntryGate.DYN_MULT);
        float gs = com.binance.chuyennd.tradecore.EntryGate.GATE_REGIME_ADAPTIVE
                ? com.binance.chuyennd.tradecore.EntryGate.CURRENT_REGIME_SCALE : com.binance.chuyennd.tradecore.EntryGate.GATE_DYN_SCALE;
        return p15 / (factor * gs);
    }

    public static void write(String path, long[] ts, float[] r) throws IOException {
        GateRatioPersist.writeFresh(path, ts, r);
    }

    /** R-SIM: LiveGateRollingRatio.init() (that, env) TRUOC harness, roi nap buffer warm-up bang GateRatioBuffer.bulkAdd cua jar
     *  (CUNG ham loadPersistedAndSeed dung khi restart). Ly do: init() loc persist theo System.currentTimeMillis() (gio that 11/2026)
     *  => moi ban ghi 2026Q1-Q3 bi bo. Tra [isOn, size]. */
    public static Object[] initAndBulkAdd(long[] ts, float[] r) throws Exception {
        LiveGateRollingRatio.init();
        java.lang.reflect.Field bf = LiveGateRollingRatio.class.getDeclaredField("buffer");
        bf.setAccessible(true);
        Object buf = bf.get(null);
        java.lang.reflect.Method m = buf.getClass().getDeclaredMethod("bulkAdd", long[].class, float[].class);
        m.setAccessible(true);
        m.invoke(buf, ts, r);
        return new Object[]{LiveGateRollingRatio.isOn(), LiveGateRollingRatio.bufferSizeForTest()};
    }
}
