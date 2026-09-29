package com.binance.chuyennd.ai_ml.onnx.entry;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.util.Random;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

/**
 * {@link GateRatioPersist} — file append-only (Snappy + CRC32): roundtrip, lọc minTs, phát hiện hỏng CRC,
 * bỏ qua chunk cuối ghi dở (crash).
 */
public class GateRatioPersistTest {

    private File dir;
    private String path;

    @Before
    public void setUp() throws IOException {
        dir = Files.createTempDirectory("gate-ratio-test").toFile();
        path = new File(dir, "gate_ratio_live.bin").getAbsolutePath();
    }

    @After
    public void tearDown() {
        File f = new File(path);
        if (f.exists()) f.delete();
        if (dir.exists()) dir.delete();
    }

    private static long[] ts(long... v) {
        return v;
    }

    private static float[] r(float... v) {
        return v;
    }

    @Test
    public void roundtrip() throws IOException {
        long[] a = {1_700_000_000_000L, 1_700_000_060_000L, 1_700_000_120_000L};
        float[] b = {0.001f, 0.002f, 0.003f};
        GateRatioPersist.append(path, a, b);
        GateRatioPersist.append(path, ts(1_700_000_180_000L), r(0.004f));
        GateRatioPersist.Records rec = GateRatioPersist.load(path, 0L);
        assertEquals(4, rec.ts.length);
        for (int i = 0; i < 3; i++) {
            assertEquals(a[i], rec.ts[i]);
            assertEquals(Float.floatToIntBits(b[i]), Float.floatToIntBits(rec.r[i]));
        }
        assertEquals(1_700_000_180_000L, rec.ts[3]);
        assertEquals(Float.floatToIntBits(0.004f), Float.floatToIntBits(rec.r[3]));
    }

    @Test
    public void minTsFilter() throws IOException {
        long[] a = {1_700_000_000_000L, 1_700_001_000_000L, 1_700_002_000_000L};
        float[] b = {1f, 2f, 3f};
        GateRatioPersist.append(path, a, b);
        GateRatioPersist.Records rec = GateRatioPersist.load(path, 1_700_001_000_000L);
        assertEquals(2, rec.ts.length);
        assertEquals(1_700_001_000_000L, rec.ts[0]);
        assertEquals(1_700_002_000_000L, rec.ts[1]);
    }

    @Test
    public void emptyWhenFileMissing() throws IOException {
        GateRatioPersist.Records rec = GateRatioPersist.load(path, 0L);
        assertEquals(0, rec.ts.length);
    }

    @Test
    public void corruptedChecksumDetected() throws IOException {
        long[] a = {1_700_000_000_000L, 1_700_000_060_000L, 1_700_000_120_000L};
        float[] b = {1f, 2f, 3f};
        GateRatioPersist.append(path, a, b);
        // bóp méo 1 byte trong vùng nén của chunk (sau 12 byte header)
        byte[] all = Files.readAllBytes(new File(path).toPath());
        all[GateRatioPersist.HEADER_BYTES] ^= 0x7F;
        Files.write(new File(path).toPath(), all);
        try {
            GateRatioPersist.load(path, 0L);
            fail("phải ném IOException khi CRC lệch");
        } catch (IOException expected) {
            assertTrue(expected.getMessage().contains("CRC"));
        }
    }

    @Test
    public void truncatedTailIgnored() throws IOException {
        long[] a = new long[1000];
        float[] b = new float[1000];
        Random rnd = new Random(7L);
        for (int i = 0; i < 1000; i++) {
            a[i] = 1_700_000_000_000L + i * 60_000L;
            b[i] = rnd.nextFloat();
        }
        // ghi 2 chunk (mỗi 1000 record) rồi cắt cụt giữa chunk thứ 2
        GateRatioPersist.append(path, a, b);
        GateRatioPersist.append(path, a, b);
        byte[] all = Files.readAllBytes(new File(path).toPath());
        byte[] truncated = new byte[all.length / 2];
        System.arraycopy(all, 0, truncated, 0, truncated.length);
        Files.write(new File(path).toPath(), truncated);
        // đọc được chunk đầu (1000 record), bỏ qua đuôi ghi dở, không ném
        GateRatioPersist.Records rec = GateRatioPersist.load(path, 0L);
        assertEquals(1000, rec.ts.length);
    }
}
