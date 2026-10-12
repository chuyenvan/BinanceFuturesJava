package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.EntryGate;
import com.binance.chuyennd.utils.Utils;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

/**
 * [GATE-PERSIST-ROBUST 2026-10-12] {@link LiveGateRollingRatio}: nạp persist có chunk hỏng (giữ record, sao lưu
 * {@code .corrupt_}, viết lại file sạch, KHÔNG seed khi persist ≥ 7 ngày) + seed bỏ qua ngày không có thư mục
 * predictionSymbol mà vẫn cho tập record giống hệt thứ tự cũ. Chỉ dùng thư mục tạm + ts giả.
 */
public class LiveGateRollingRatioPersistTest {

    private static final long DAY = 86_400_000L;
    private static final long HOUR = 3600_000L;
    private static final long NOW = 1_760_000_000_000L;   // ts giả cố định

    private File dir;
    private String path;

    @Before
    public void setUp() throws IOException {
        dir = Files.createTempDirectory("gate-ratio-live-persist").toFile();
        path = new File(dir, "gate_ratio_live.bin").getAbsolutePath();
        LiveGateRollingRatio.configureForTest(0.5f, 90);
        LiveGateRollingRatio.setPersistFileForTest(path);
    }

    @After
    public void tearDown() {
        LiveGateRollingRatio.resetForTest();
        File[] fs = dir.listFiles();
        if (fs != null) for (File f : fs) f.delete();
        dir.delete();
    }

    private static long[] hourly(long from, int n) {
        long[] a = new long[n];
        for (int i = 0; i < n; i++) a[i] = from + i * HOUR;
        return a;
    }

    private static float[] vals(int n, float base) {
        float[] a = new float[n];
        for (int i = 0; i < n; i++) a[i] = base + i * 0.001f;
        return a;
    }

    private static long[] cat(long[] a, long[] b) {
        long[] o = Arrays.copyOf(a, a.length + b.length);
        System.arraycopy(b, 0, o, a.length, b.length);
        return o;
    }

    private static float[] cat(float[] a, float[] b) {
        float[] o = Arrays.copyOf(a, a.length + b.length);
        System.arraycopy(b, 0, o, a.length, b.length);
        return o;
    }

    /** (e) Persist có chunk giữa hỏng, persist ≥ 7 ngày ⇒ giữ record, backup .corrupt_, viết lại sạch, KHÔNG seed. */
    @Test
    public void corruptPersistKeepsRecordsBackupsAndRewrites() throws IOException {
        long[] t1 = hourly(NOW - 10 * DAY, 72);
        float[] r1 = vals(72, 0.10f);
        long[] t2 = hourly(NOW - 7 * DAY, 48);
        float[] r2 = vals(48, 0.20f);
        long[] t3 = hourly(NOW - 5 * DAY, 96);
        float[] r3 = vals(96, 0.30f);
        GateRatioPersist.append(path, t1, r1);
        int len1 = (int) new File(path).length();
        GateRatioPersist.append(path, t2, r2);
        GateRatioPersist.append(path, t3, r3);
        byte[] orig = Files.readAllBytes(new File(path).toPath());
        orig[len1 + GateRatioPersist.HEADER_BYTES + 10] ^= 0x33;   // hỏng payload chunk 2
        Files.write(new File(path).toPath(), orig);

        LiveGateRollingRatio.loadPersistedAndSeed(NOW);

        assertEquals("khong seed khi persist >= 7 ngay", 0, LiveGateRollingRatio.seedCallsForTest());
        assertEquals(72 + 96, LiveGateRollingRatio.bufferSizeForTest());
        File backup = new File(path + ".corrupt_" + new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date(NOW)));
        assertTrue("phai co file sao luu " + backup, backup.exists());
        assertArrayEquals(orig, Files.readAllBytes(backup.toPath()));
        assertFalse(new File(path + ".tmp").exists());
        GateRatioPersist.Records clean = GateRatioPersist.load(path, 0L);
        assertEquals(0, clean.droppedChunks);
        assertArrayEquals(cat(t1, t3), clean.ts);
        float[] er = cat(r1, r3);
        assertEquals(er.length, clean.r.length);
        for (int i = 0; i < er.length; i++) {
            assertEquals(Float.floatToIntBits(er[i]), Float.floatToIntBits(clean.r[i]));
        }
    }

    /** File sạch ≥ 7 ngày ⇒ steady-state: không backup, không viết lại (bytes y nguyên), không seed. */
    @Test
    public void cleanPersistUntouched() throws IOException {
        GateRatioPersist.append(path, hourly(NOW - 10 * DAY, 72), vals(72, 0.1f));
        GateRatioPersist.append(path, hourly(NOW - 5 * DAY, 96), vals(96, 0.3f));
        byte[] before = Files.readAllBytes(new File(path).toPath());

        LiveGateRollingRatio.loadPersistedAndSeed(NOW);

        assertEquals(0, LiveGateRollingRatio.seedCallsForTest());
        assertEquals(168, LiveGateRollingRatio.bufferSizeForTest());
        assertArrayEquals(before, Files.readAllBytes(new File(path).toPath()));
        String[] names = dir.list();
        assertNotNull(names);
        assertEquals(1, names.length);
    }

    /** Nguồn giả: sp chỉ có ở ngày "có thư mục"; vài tick sp rỗng / p15 null; đếm lệnh gọi p15 (Aerospike). */
    private static final class FakeSource implements LiveGateRollingRatio.SeedSource {
        final Set<String> daysWithDir;
        final List<Long> p15Calls = new ArrayList<>();
        int dirChecks = 0;

        FakeSource(Set<String> daysWithDir) {
            this.daysWithDir = daysWithDir;
        }

        @Override
        public boolean dayDirExists(String yyyyMMdd) {
            dirChecks++;
            return daysWithDir.contains(yyyyMMdd);
        }

        @Override
        public Map<String, Float> symbolPred(long t) {
            if (!daysWithDir.contains(Utils.normalizeDateYYYYMMDD(t))) return null;   // file không tồn tại
            long k = t / 60_000L;
            if (k % 7 == 0) return new HashMap<>();                                  // tick sp rỗng
            Map<String, Float> m = new LinkedHashMap<>();
            m.put("AAAUSDT", 0.30f + (k % 5) * 0.01f);
            m.put("BBBUSDT", 0.10f + (k % 3) * 0.02f);
            m.put("CCCUSDT", 0.70f);
            m.put("DDDUSDT", Float.NaN);
            return m;
        }

        @Override
        public AiPredictionData p15(long t) {
            p15Calls.add(t);
            long k = t / 60_000L;
            if (k % 11 == 0) return null;                                            // thiếu p15
            return new AiPredictionData(t, 0.004f + (k % 13) * 0.0005f, 0f);
        }
    }

    /** Bản sao thứ tự CŨ (p15 trước, sp sau, không kiểm thư mục) — tham chiếu tập record. */
    private static List<Object[]> oldOrderSeed(long from, long to, int gridMin, int topK, FakeSource src) {
        List<Object[]> out = new ArrayList<>();
        long t0 = (from / 60_000L) * 60_000L;
        int guard = 0;
        for (long t = t0; t < to && guard < 200_000; t += 60_000L, guard++) {
            if ((t / 60_000L) % gridMin != 0) continue;
            AiPredictionData p15 = src.p15(t);
            if (p15 == null) continue;
            Map<String, Float> spMap = src.symbolPred(t);
            if (spMap == null || spMap.isEmpty()) continue;
            List<Map.Entry<String, Float>> sorted = new ArrayList<>(spMap.entrySet());
            sorted.sort(Map.Entry.comparingByValue());
            int n = Math.min(topK, sorted.size());
            float gs = EntryGate.GATE_REGIME_ADAPTIVE ? EntryGate.CURRENT_REGIME_SCALE : EntryGate.GATE_DYN_SCALE;
            for (int i = 0; i < n; i++) {
                Float sp = sorted.get(i).getValue();
                if (sp == null || Float.isNaN(sp)) continue;
                float factor = Math.max(EntryGate.DYN_MIN, (sp / EntryGate.SCORE_BASE) * EntryGate.DYN_MULT);
                out.add(new Object[]{t, p15.predReturn15M / (factor * gs)});
            }
        }
        return out;
    }

    /** (f) seed: bỏ qua ngày không có thư mục (không gọi p15), tập record giống hệt thứ tự cũ. */
    @Test
    public void seedSkipsDaysWithoutDirAndMatchesOldOrder() {
        long from = NOW - 5 * DAY + 123_456L;
        long to = NOW - DAY;
        Set<String> allDays = new HashSet<>();
        for (long t = (from / 60_000L) * 60_000L; t < to; t += 60_000L) allDays.add(Utils.normalizeDateYYYYMMDD(t));
        String miss1 = Utils.normalizeDateYYYYMMDD(from + DAY);
        String miss2 = Utils.normalizeDateYYYYMMDD(from + 2 * DAY + 12 * HOUR);
        Set<String> withDir = new HashSet<>(allDays);
        withDir.remove(miss1);
        withDir.remove(miss2);
        assertEquals(allDays.size() - 2, withDir.size());

        for (int topK : new int[]{2, 16}) {
            FakeSource oldSrc = new FakeSource(withDir);
            List<Object[]> exp = oldOrderSeed(from, to, 15, topK, oldSrc);
            FakeSource newSrc = new FakeSource(withDir);
            LiveGateRollingRatio.SeedResult got = LiveGateRollingRatio.collectSeed(from, to, 15, topK, newSrc);

            assertTrue(exp.size() > 0);
            assertEquals(exp.size(), got.ts.length);
            assertEquals(exp.size(), got.r.length);
            for (int i = 0; i < exp.size(); i++) {
                assertEquals(((Long) exp.get(i)[0]).longValue(), got.ts[i]);
                assertEquals(Float.floatToIntBits((Float) exp.get(i)[1]), Float.floatToIntBits(got.r[i]));
            }
            for (long t : newSrc.p15Calls) {
                String d = Utils.normalizeDateYYYYMMDD(t);
                assertTrue("goi Aerospike o ngay khong co thu muc " + d, withDir.contains(d));
                assertFalse("goi Aerospike o tick sp rong", (t / 60_000L) % 7 == 0);
            }
            assertEquals(newSrc.p15Calls.size(), got.aerospikeCalls);
            assertTrue(newSrc.p15Calls.size() < oldSrc.p15Calls.size());
            assertEquals(2, got.skippedDays);
            assertEquals("kiem thu muc 1 lan / ngay", allDays.size(), newSrc.dirChecks);
        }
    }

    /** Không ngày nào có thư mục ⇒ 0 lệnh gọi Aerospike, seed rỗng. */
    @Test
    public void seedNoDirNoAerospikeCalls() {
        FakeSource src = new FakeSource(new HashSet<>());
        LiveGateRollingRatio.SeedResult got = LiveGateRollingRatio.collectSeed(NOW - 90 * DAY, NOW, 15, 16, src);
        assertEquals(0, got.ts.length);
        assertEquals(0, got.aerospikeCalls);
        assertTrue(src.p15Calls.isEmpty());
        assertTrue(got.skippedDays >= 90);
    }
}
