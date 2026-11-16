package com.binance.chuyennd.ai_ml.onnx.entry;

import java.io.IOException;
import java.lang.reflect.Method;
import java.util.Arrays;

/**
 * [E2E_REPLAY] cau test (CHI test) cho harness replay ngay sap: bat {@link LiveGateRollingRatio} that voi file persist tam,
 * nap buffer khoi dau, doc q cua gio (khong nap), flush va doc lai moi ban ghi da nap. Khong doi code production.
 */
public final class E2eGateSupport {

    private E2eGateSupport() {
    }

    /** Ghi buffer khoi dau (sap xep ts tang, on dinh) vao file persist tam roi nap bang loadPersistedAndSeed(now). */
    public static void start(float pct, int days, String persistPath, long[] ts, float[] r, long now) throws IOException {
        Integer[] idx = new Integer[ts.length];
        for (int i = 0; i < idx.length; i++) idx[i] = i;
        Arrays.sort(idx, (a, b) -> Long.compare(ts[a], ts[b]));
        long[] st = new long[ts.length];
        float[] sr = new float[ts.length];
        for (int i = 0; i < idx.length; i++) {
            st[i] = ts[idx[i]];
            sr[i] = r[idx[i]];
        }
        LiveGateRollingRatio.configureForTest(pct, days);
        LiveGateRollingRatio.setPersistFileForTest(persistPath);
        GateRatioPersist.writeFresh(persistPath, st, sr);
        LiveGateRollingRatio.loadPersistedAndSeed(now);
    }

    /** q (thrBase) cua gio chua ts — KHONG nap r (= thresholdCheckOnly, cung q ma threshold() se tra). */
    public static float qPeek(long ts, float p15, float sp) {
        return LiveGateRollingRatio.thresholdCheckOnly(ts, p15, sp);
    }

    public static int size() {
        return LiveGateRollingRatio.bufferSizeForTest();
    }

    /** Flush ban ghi dang cho roi doc lai toan bo file persist: [long[] ts, float[] r]. */
    public static Object[] flushAndLoad(String persistPath) throws Exception {
        Method m = LiveGateRollingRatio.class.getDeclaredMethod("flush");
        m.setAccessible(true);
        m.invoke(null);
        return loadRaw(persistPath);
    }

    /** Doc file buffer (dinh dang gate_ratio_live.bin): [long[] ts, float[] r]. */
    public static Object[] loadRaw(String path) throws IOException {
        GateRatioPersist.Records rec = GateRatioPersist.load(path, Long.MIN_VALUE);
        if (rec.droppedChunks != 0) throw new IOException("buffer hong: droppedChunks=" + rec.droppedChunks);
        return new Object[]{rec.ts.clone(), rec.r.clone()};
    }

    public static void reset() {
        LiveGateRollingRatio.resetForTest();
    }
}
