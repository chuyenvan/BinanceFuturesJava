package com.binance.chuyennd.ai_ml.onnx.entry;

import org.junit.After;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;

import static org.junit.Assert.*;

/** [V12 R4h] GATE_BUFFER_SEED: kiem md5/dinh dang/khoang thoi gian (fail-fast), tron seed + persist sau seed, idempotent. */
public class GateSeedR4hTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();
    static final long DAY = 86_400_000L, H = 3_600_000L;
    static final long NOW = 1_793_400_000_000L;

    @After
    public void tearDown() {
        LiveGateRollingRatio.resetForTest();
    }

    private File seed(long from, long to, long step) throws Exception {
        int n = (int) ((to - from) / step) + 1;
        long[] ts = new long[n];
        float[] r = new float[n];
        for (int i = 0; i < n; i++) {
            ts[i] = from + i * step;
            r[i] = 0.001f * (i % 97);
        }
        File f = tmp.newFile();
        GateRatioPersist.writeFresh(f.getPath(), ts, r);
        return f;
    }

    @Test
    public void checkSeedRejects() throws Exception {
        File f = seed(NOW - 91 * DAY, NOW - 2 * H, H);
        String md5 = LiveGateRollingRatio.md5Hex(f);
        GateRatioPersist.Records rec = GateRatioPersist.load(f.getPath(), Long.MIN_VALUE);
        assertNull(LiveGateRollingRatio.checkSeed(f, md5, rec, NOW, 90, 24));
        assertNotNull("thieu md5", LiveGateRollingRatio.checkSeed(f, null, rec, NOW, 90, 24));
        assertTrue(LiveGateRollingRatio.checkSeed(f, "0123456789abcdef0123456789abcdef", rec, NOW, 90, 24).contains("md5"));
        assertTrue("qua cu", LiveGateRollingRatio.checkSeed(f, md5, rec, NOW + 30 * H, 90, 24).contains("qua cu"));
        assertTrue("tuong lai", LiveGateRollingRatio.checkSeed(f, md5, rec, NOW - 3 * H, 90, 24).contains("tuong lai"));
        File shortF = seed(NOW - 30 * DAY, NOW - H, H);
        GateRatioPersist.Records rs = GateRatioPersist.load(shortF.getPath(), Long.MIN_VALUE);
        assertTrue("khong phu 90 ngay", LiveGateRollingRatio.checkSeed(shortF, LiveGateRollingRatio.md5Hex(shortF), rs, NOW, 90, 24)
                .contains("khong phu"));
        File junk = tmp.newFile();
        java.nio.file.Files.write(junk.toPath(), new byte[]{1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13});
        GateRatioPersist.Records rj = GateRatioPersist.load(junk.getPath(), Long.MIN_VALUE);
        assertNotNull("dinh dang sai", LiveGateRollingRatio.checkSeed(junk, LiveGateRollingRatio.md5Hex(junk), rj, NOW, 90, 24));
        assertNotNull("khong co file", LiveGateRollingRatio.checkSeed(new File(tmp.getRoot(), "x"), md5, null, NOW, 90, 24));
    }

    @Test
    public void applyMergesPersistAfterSeed_backupOnce_idempotent() throws Exception {
        File f = seed(NOW - 91 * DAY, NOW - 2 * H, H);
        String md5 = LiveGateRollingRatio.md5Hex(f);
        File persist = new File(tmp.getRoot(), "gate_ratio_live.bin");
        // persist cu (v1.1): 90 ngay ban ghi khac + 2 ban ghi SAU cuoi seed
        long[] pts = {NOW - 50 * DAY, NOW - 10 * DAY, NOW - 90 * 60_000L, NOW - 30 * 60_000L};
        float[] pr = {9f, 9f, 0.5f, 0.6f};
        GateRatioPersist.writeFresh(persist.getPath(), pts, pr);
        LiveGateRollingRatio.configureForTest(0.999950829f, 90);
        LiveGateRollingRatio.setPersistFileForTest(persist.getPath());
        assertNull(LiveGateRollingRatio.applySeedFile(f.getPath(), md5, 24, NOW));
        int nSeedInWin = 0;
        for (long t = NOW - 91 * DAY; t <= NOW - 2 * H; t += H) if (t >= NOW - 90 * DAY) nSeedInWin++;
        assertEquals("seed trong cua so + 2 ban ghi persist sau seed", nSeedInWin + 2, LiveGateRollingRatio.bufferSizeForTest());
        File[] bak = tmp.getRoot().listFiles((d, n) -> n.startsWith("gate_ratio_live.bin.preseed_"));
        assertEquals(1, bak.length);
        GateRatioPersist.Records after = GateRatioPersist.load(persist.getPath(), NOW - 90 * DAY);
        assertEquals(nSeedInWin + 2, after.ts.length);
        // restart: cung seed => khong sao luu / viet lai them
        long mtime = persist.lastModified();
        Thread.sleep(20);
        LiveGateRollingRatio.configureForTest(0.999950829f, 90);
        LiveGateRollingRatio.setPersistFileForTest(persist.getPath());
        assertNull(LiveGateRollingRatio.applySeedFile(f.getPath(), md5, 24, NOW));
        assertEquals(nSeedInWin + 2, LiveGateRollingRatio.bufferSizeForTest());
        assertEquals(1, tmp.getRoot().listFiles((d, n) -> n.startsWith("gate_ratio_live.bin.preseed_")).length);
        assertEquals("idempotent: khong viet lai", mtime, persist.lastModified());
        // md5 sai => fail (khong dung buffer)
        assertNotNull(LiveGateRollingRatio.applySeedFile(f.getPath(), "ffffffffffffffffffffffffffffffff", 24, NOW));
    }

    @Test
    public void lagHours() {
        assertEquals(24, LiveGateRollingRatio.parseLagHours(null));
        assertEquals(6, LiveGateRollingRatio.parseLagHours("6"));
        assertEquals(24, LiveGateRollingRatio.parseLagHours("-1"));
        assertEquals(24, LiveGateRollingRatio.parseLagHours("x"));
    }
}
