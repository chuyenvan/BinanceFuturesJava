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
import java.util.zip.CRC32;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

/**
 * {@link GateRatioPersist} — file append-only (Snappy + CRC32): roundtrip, lọc minTs, chunk hỏng (CRC/magic/
 * LEN/Snappy) bị bỏ + resync (GATE-PERSIST-ROBUST), bỏ qua chunk cuối ghi dở (crash).
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

    /** Chunk duy nhất CRC lệch ⇒ KHÔNG ném (GATE-PERSIST-ROBUST): bỏ chunk, 0 record, dropped=1. */
    @Test
    public void corruptedChecksumDetected() throws IOException {
        long[] a = {1_700_000_000_000L, 1_700_000_060_000L, 1_700_000_120_000L};
        float[] b = {1f, 2f, 3f};
        GateRatioPersist.append(path, a, b);
        // bóp méo 1 byte trong vùng nén của chunk (sau 12 byte header)
        byte[] all = Files.readAllBytes(new File(path).toPath());
        all[GateRatioPersist.HEADER_BYTES] ^= 0x7F;
        Files.write(new File(path).toPath(), all);
        GateRatioPersist.Records rec = GateRatioPersist.load(path, 0L);
        assertEquals(0, rec.ts.length);
        assertEquals(1, rec.droppedChunks);
        assertEquals(all.length, rec.droppedBytes);
    }

    // ============================================================
    // [GATE-PERSIST-ROBUST 2026-10-12] resync qua chunk hỏng
    // ============================================================

    /** Bytes của MỘT chunk chứa n record bắt đầu từ ts0 (ghi qua append vào file phụ). */
    private byte[] chunk(long ts0, int n, long seed) throws IOException {
        long[] a = new long[n];
        float[] b = new float[n];
        Random rnd = new Random(seed);
        for (int i = 0; i < n; i++) {
            a[i] = ts0 + i * 60_000L;
            b[i] = rnd.nextFloat() * 2f - 0.5f;
        }
        File tmp = new File(dir, "chunk_" + seed + ".bin");
        try {
            GateRatioPersist.append(tmp.getAbsolutePath(), a, b);
            return Files.readAllBytes(tmp.toPath());
        } finally {
            tmp.delete();
        }
    }

    private static byte[] concat(byte[]... parts) {
        int n = 0;
        for (byte[] p : parts) n += p.length;
        byte[] out = new byte[n];
        int o = 0;
        for (byte[] p : parts) {
            System.arraycopy(p, 0, out, o, p.length);
            o += p.length;
        }
        return out;
    }

    private void writeFile(byte[] bytes) throws IOException {
        Files.write(new File(path).toPath(), bytes);
    }

    /** Record (ts, r) của các chunk sạch theo thứ tự — qua load từng chunk riêng. */
    private GateRatioPersist.Records expected(byte[]... cleanChunks) throws IOException {
        File tmp = new File(dir, "expected.bin");
        try {
            Files.write(tmp.toPath(), concat(cleanChunks));
            return loadOld(tmp.getAbsolutePath(), 0L);
        } finally {
            tmp.delete();
        }
    }

    private static void assertSameRecords(GateRatioPersist.Records exp, GateRatioPersist.Records got) {
        assertEquals(exp.ts.length, got.ts.length);
        for (int i = 0; i < exp.ts.length; i++) {
            assertEquals(exp.ts[i], got.ts[i]);
            assertEquals(Float.floatToIntBits(exp.r[i]), Float.floatToIntBits(got.r[i]));
        }
    }

    /** Bản sao NGUYÊN VĂN thuật toán load cũ (HEAD 94319636) — tham chiếu byte-identical cho file sạch. */
    private static GateRatioPersist.Records loadOld(String p, long minTs) throws IOException {
        byte[] all = Files.readAllBytes(new File(p).toPath());
        java.util.List<byte[]> chunks = new java.util.ArrayList<>();
        int off = 0;
        while (off + GateRatioPersist.HEADER_BYTES <= all.length) {
            ByteBuffer head = ByteBuffer.wrap(all, off, GateRatioPersist.HEADER_BYTES).order(ByteOrder.BIG_ENDIAN);
            int magic = head.getInt();
            int len = head.getInt();
            int crc = head.getInt();
            off += GateRatioPersist.HEADER_BYTES;
            if (magic != GateRatioPersist.MAGIC) throw new IOException("magic sai");
            if (off + len > all.length) break;
            byte[] comp = new byte[len];
            System.arraycopy(all, off, comp, 0, len);
            off += len;
            if (crc32(comp) != crc) throw new IOException("CRC32 lech");
            chunks.add(org.xerial.snappy.Snappy.uncompress(comp));
        }
        int total = 0;
        for (byte[] c : chunks) total += c.length / GateRatioPersist.RECORD_BYTES;
        ByteBuffer raw = ByteBuffer.allocate(total * GateRatioPersist.RECORD_BYTES).order(ByteOrder.BIG_ENDIAN);
        for (byte[] c : chunks) {
            raw.put(c, 0, (c.length / GateRatioPersist.RECORD_BYTES) * GateRatioPersist.RECORD_BYTES);
        }
        raw.flip();
        java.util.List<Long> ts = new java.util.ArrayList<>();
        java.util.List<Float> r = new java.util.ArrayList<>();
        while (raw.remaining() >= GateRatioPersist.RECORD_BYTES) {
            long t = raw.getLong();
            float v = Float.intBitsToFloat(raw.getInt());
            if (t >= minTs) {
                ts.add(t);
                r.add(v);
            }
        }
        long[] tsA = new long[ts.size()];
        float[] rA = new float[r.size()];
        for (int i = 0; i < tsA.length; i++) {
            tsA[i] = ts.get(i);
            rA[i] = r.get(i);
        }
        return new GateRatioPersist.Records(tsA, rA);
    }

    private static int crc32(byte[] b) {
        CRC32 c = new CRC32();
        c.update(b);
        return (int) c.getValue();
    }

    /** (a) File sạch nhiều chunk (+ lọc minTs) ⇒ kết quả giống hệt thuật toán cũ, dropped = 0. */
    @Test
    public void cleanMultiChunkIdenticalToOld() throws IOException {
        byte[] f = concat(chunk(1_700_000_000_000L, 500, 1L), chunk(1_700_100_000_000L, 3, 2L),
                chunk(1_700_200_000_000L, 4096, 3L), chunk(1_700_900_000_000L, 1, 4L),
                chunk(1_701_000_000_000L, 777, 5L));
        writeFile(f);
        for (long minTs : new long[]{0L, 1_700_100_060_000L, 1_700_250_000_000L, Long.MAX_VALUE}) {
            GateRatioPersist.Records got = GateRatioPersist.load(path, minTs);
            assertSameRecords(loadOld(path, minTs), got);
            assertEquals(0, got.droppedChunks);
            assertEquals(0L, got.droppedBytes);
        }
        assertEquals(500 + 3 + 4096 + 1 + 777, GateRatioPersist.load(path, 0L).ts.length);
    }

    /** (b) Chunk GIỮA CRC lệch ⇒ giữ các chunk khác, dropped = 1, droppedBytes = cỡ chunk hỏng. */
    @Test
    public void middleChunkCrcCorruptKeepsOthers() throws IOException {
        byte[] c1 = chunk(1_700_000_000_000L, 300, 11L);
        byte[] c2 = chunk(1_700_100_000_000L, 300, 12L);
        byte[] c3 = chunk(1_700_200_000_000L, 300, 13L);
        byte[] bad = c2.clone();
        bad[GateRatioPersist.HEADER_BYTES + bad.length / 3] ^= 0x55;
        writeFile(concat(c1, bad, c3));
        GateRatioPersist.Records got = GateRatioPersist.load(path, 0L);
        assertSameRecords(expected(c1, c3), got);
        assertEquals(600, got.ts.length);
        assertEquals(1, got.droppedChunks);
        assertEquals(c2.length, got.droppedBytes);
    }

    /** (c) MAGIC hỏng giữa file ⇒ resync tới MAGIC kế tiếp, giữ chunk trước + sau. */
    @Test
    public void middleMagicCorruptResyncs() throws IOException {
        byte[] c1 = chunk(1_700_000_000_000L, 200, 21L);
        byte[] c2 = chunk(1_700_100_000_000L, 200, 22L);
        byte[] c3 = chunk(1_700_200_000_000L, 200, 23L);
        byte[] c4 = chunk(1_700_300_000_000L, 200, 24L);
        byte[] bad = c2.clone();
        bad[1] = 'X';   // "GXR1"
        writeFile(concat(c1, bad, c3, c4));
        GateRatioPersist.Records got = GateRatioPersist.load(path, 0L);
        assertSameRecords(expected(c1, c3, c4), got);
        assertEquals(1, got.droppedChunks);
        assertEquals(c2.length, got.droppedBytes);
        // magic hỏng ở chunk ĐẦU tiên
        byte[] bad1 = c1.clone();
        bad1[0] = 0;
        writeFile(concat(bad1, c2, c3));
        got = GateRatioPersist.load(path, 0L);
        assertSameRecords(expected(c2, c3), got);
        assertEquals(1, got.droppedChunks);
    }

    /**
     * Kịch bản đĩa đầy 10-12: chunk ghi dở (header + một phần payload) rồi các flush sau append chunk nguyên
     * vẹn ⇒ LEN của chunk dở "nuốt" sang chunk sau (CRC lệch hoặc vượt cuối file) ⇒ resync, giữ chunk sau.
     */
    @Test
    public void diskFullPartialChunkThenAppendsRecovered() throws IOException {
        byte[] c1 = chunk(1_700_000_000_000L, 400, 31L);
        byte[] c2 = chunk(1_700_100_000_000L, 400, 32L);
        byte[] c3 = chunk(1_700_200_000_000L, 400, 33L);
        byte[] c4 = chunk(1_700_300_000_000L, 50, 34L);
        byte[] partial = java.util.Arrays.copyOf(c2, c2.length / 2);
        // (i) phần sau đủ dài: LEN chunk dở nằm trong file ⇒ CRC lệch
        writeFile(concat(c1, partial, c3, c4));
        GateRatioPersist.Records got = GateRatioPersist.load(path, 0L);
        assertSameRecords(expected(c1, c3, c4), got);
        assertEquals(1, got.droppedChunks);
        assertEquals(partial.length, got.droppedBytes);
        // (ii) phần sau ngắn: LEN chunk dở vượt cuối file ⇒ vẫn resync (không bỏ c4 như bản cũ)
        writeFile(concat(c1, partial, c4));
        got = GateRatioPersist.load(path, 0L);
        assertSameRecords(expected(c1, c4), got);
        assertEquals(1, got.droppedChunks);
        assertEquals(partial.length, got.droppedBytes);
        // (iii) chỉ ghi được 5 byte header rồi append tiếp
        writeFile(concat(c1, java.util.Arrays.copyOf(c2, 5), c3));
        got = GateRatioPersist.load(path, 0L);
        assertSameRecords(expected(c1, c3), got);
        assertEquals(1, got.droppedChunks);
        assertEquals(5L, got.droppedBytes);
    }

    /** (d) Chunk CUỐI ghi dở ⇒ như bản cũ: bỏ đuôi, KHÔNG tính hỏng (dropped = 0). */
    @Test
    public void truncatedLastChunkKeepsOldBehavior() throws IOException {
        byte[] c1 = chunk(1_700_000_000_000L, 300, 41L);
        byte[] c2 = chunk(1_700_100_000_000L, 300, 42L);
        byte[] c3 = chunk(1_700_200_000_000L, 300, 43L);
        for (int cut : new int[]{1, 5, GateRatioPersist.HEADER_BYTES, GateRatioPersist.HEADER_BYTES + 7,
                c3.length / 2, c3.length - 1}) {
            writeFile(concat(c1, c2, java.util.Arrays.copyOf(c3, cut)));
            GateRatioPersist.Records got = GateRatioPersist.load(path, 0L);
            assertSameRecords(loadOld(path, 0L), got);
            assertSameRecords(expected(c1, c2), got);
            assertEquals(0, got.droppedChunks);
            assertEquals(0L, got.droppedBytes);
        }
    }

    /** LEN âm (bản cũ: NegativeArraySizeException) và payload không phải Snappy (CRC khớp) ⇒ chunk hỏng. */
    @Test
    public void negativeLenAndSnappyErrorDropped() throws IOException {
        byte[] c1 = chunk(1_700_000_000_000L, 100, 51L);
        byte[] c3 = chunk(1_700_200_000_000L, 100, 53L);
        byte[] neg = ByteBuffer.allocate(GateRatioPersist.HEADER_BYTES + 8).order(ByteOrder.BIG_ENDIAN)
                .putInt(GateRatioPersist.MAGIC).putInt(-5).putInt(0).putLong(0x0102030405060708L).array();
        writeFile(concat(c1, neg, c3));
        GateRatioPersist.Records got = GateRatioPersist.load(path, 0L);
        assertSameRecords(expected(c1, c3), got);
        assertEquals(1, got.droppedChunks);
        assertEquals(neg.length, got.droppedBytes);

        byte[] garbage = new byte[64];
        java.util.Arrays.fill(garbage, (byte) 0xFF);
        byte[] snap = concat(ByteBuffer.allocate(GateRatioPersist.HEADER_BYTES).order(ByteOrder.BIG_ENDIAN)
                .putInt(GateRatioPersist.MAGIC).putInt(garbage.length).putInt(crc32(garbage)).array(), garbage);
        writeFile(concat(c1, snap, c3));
        got = GateRatioPersist.load(path, 0L);
        assertSameRecords(expected(c1, c3), got);
        assertEquals(1, got.droppedChunks);
        assertEquals(snap.length, got.droppedBytes);
    }

    /** writeFresh ghi qua file tạm + rename: kết quả = 1 chunk sạch, không để lại .tmp. */
    @Test
    public void writeFreshAtomicNoTmpLeft() throws IOException {
        writeFile(concat(chunk(1_700_000_000_000L, 10, 61L), new byte[]{1, 2, 3}));
        long[] a = {1_700_000_000_000L, 1_700_000_060_000L};
        float[] b = {0.5f, -0.25f};
        GateRatioPersist.writeFresh(path, a, b);
        assertTrue(!new File(path + ".tmp").exists());
        GateRatioPersist.Records got = GateRatioPersist.load(path, 0L);
        assertEquals(0, got.droppedChunks);
        assertEquals(2, got.ts.length);
        assertEquals(a[1], got.ts[1]);
        assertEquals(Float.floatToIntBits(b[1]), Float.floatToIntBits(got.r[1]));
    }
}
