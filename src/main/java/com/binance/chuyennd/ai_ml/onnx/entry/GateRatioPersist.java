package com.binance.chuyennd.ai_ml.onnx.entry;

import org.xerial.snappy.Snappy;
import org.xerial.snappy.SnappyError;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.CRC32;

/**
 * File persist cho buffer `(ts, r)` của gate rolling live — APPEND-ONLY, nén Snappy, có CRC32.
 *
 * <p>Định dạng (nối tiếp các chunk):
 * <pre>
 *   chunk = MAGIC(4B) | LEN(4B, độ dài bytes nén) | CRC32(4B, của bytes nén) | COMPRESSED(LEN)
 *   COMPRESSED = Snappy.compress( RAW )
 *   RAW = chuỗi record 12B: TS(8B big-endian long) | R(4B big-endian float-bits)
 * </pre>
 * Chunk là đơn vị append nhỏ nhất: mỗi lần flush ghi một chunk nguyên vẹn ⇒ crash giữa chừng chỉ mất
 * chunk CUỐI (chưa ghi hết), không làm hỏng các chunk trước (CRC32 phát hiện hỏng).
 *
 * <p>[GATE-PERSIST-ROBUST 2026-10-12] Chunk hỏng GIỮA file (CRC lệch / magic sai / LEN âm / Snappy lỗi —
 * vd đĩa đầy ghi dở một chunk rồi các flush sau append tiếp) KHÔNG còn làm hỏng cả file: {@link #load}
 * bỏ chunk đó, resync tới MAGIC kế tiếp và đọc tiếp; số chunk/byte bị bỏ trả trong {@link Records}.
 * File sạch ⇒ kết quả byte-identical bản cũ.
 *
 * <p>Mục đích: buffer sống qua restart theo lịch {@code ThreadAutoRestartProgram} (JVM tự restart 4h/lần)
 * — restart không được làm mất 90 ngày dữ liệu.
 */
final class GateRatioPersist {

    static final int MAGIC = 0x47525231;   // "GRR1"
    static final int RECORD_BYTES = 12;    // 8 (ts) + 4 (r)
    static final int HEADER_BYTES = 12;    // MAGIC + LEN + CRC32

    /** Kết quả load. */
    static final class Records {
        long[] ts;
        float[] r;
        /** Số chunk hỏng bị bỏ (CRC lệch / magic sai / LEN âm / Snappy lỗi). 0 với file sạch. */
        int droppedChunks;
        /** Tổng số byte bị bỏ qua do chunk hỏng (không tính đuôi ghi dở cuối file). */
        long droppedBytes;

        Records(long[] ts, float[] r) {
            this(ts, r, 0, 0L);
        }

        Records(long[] ts, float[] r, int droppedChunks, long droppedBytes) {
            this.ts = ts;
            this.r = r;
            this.droppedChunks = droppedChunks;
            this.droppedBytes = droppedBytes;
        }
    }

    private GateRatioPersist() {
    }

    /** Append MỘT chunk (batch các record) vào cuối file. Tạo file nếu chưa có. */
    static void append(String path, long[] ts, float[] r) throws IOException {
        if (ts.length == 0) return;
        byte[] raw = encode(ts, r);
        byte[] comp = Snappy.compress(raw);
        byte[] head = ByteBuffer.allocate(HEADER_BYTES).order(ByteOrder.BIG_ENDIAN)
                .putInt(MAGIC).putInt(comp.length).putInt(crc32(comp)).array();
        File f = new File(path);
        File parent = f.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("khong tao duoc thu muc " + parent);
        }
        try (FileOutputStream fos = new FileOutputStream(f, true)) {
            fos.write(head);
            fos.write(comp);
        }
    }

    /**
     * Ghi LẠI toàn bộ file (compact/khởi tạo/sửa file hỏng). Record được ghi vào {@code <path>.tmp} rồi
     * rename đè (atomic nếu FS hỗ trợ) ⇒ lỗi giữa chừng (vd đĩa đầy) KHÔNG làm mất file cũ. Nội dung file
     * kết quả giống bản cũ (xoá rồi append một chunk); ts rỗng ⇒ xoá file như bản cũ.
     */
    static void writeFresh(String path, long[] ts, float[] r) throws IOException {
        File f = new File(path);
        File parent = f.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("khong tao duoc thu muc " + parent);
        }
        if (ts.length == 0) {
            if (f.exists() && !f.delete()) {
                throw new IOException("khong xoa duoc file cu " + path);
            }
            return;
        }
        File tmp = new File(path + ".tmp");
        if (tmp.exists() && !tmp.delete()) {
            throw new IOException("khong xoa duoc file tam " + tmp);
        }
        try {
            append(tmp.getPath(), ts, r);
            try {
                Files.move(tmp.toPath(), f.toPath(),
                        StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            } catch (AtomicMoveNotSupportedException e) {
                Files.move(tmp.toPath(), f.toPath(), StandardCopyOption.REPLACE_EXISTING);
            }
        } finally {
            if (tmp.exists() && !tmp.delete()) {
                tmp.deleteOnExit();
            }
        }
    }

    /**
     * Đọc toàn bộ file, verify CRC32 từng chunk, trả record có ts >= minTs.
     *
     * <ul>
     *   <li>Chunk hợp lệ ⇒ giữ (thứ tự file).</li>
     *   <li>Chunk hỏng (magic sai / LEN âm / CRC lệch / Snappy lỗi) ⇒ KHÔNG ném: bỏ chunk, tìm byte pattern
     *       MAGIC kế tiếp từ {@code start+1} (resync) rồi đọc tiếp; tăng {@code droppedChunks}, cộng
     *       {@code droppedBytes} (= khoảng byte bị nhảy qua). Không còn MAGIC ⇒ bỏ tới cuối file.</li>
     *   <li>Chunk cuối ghi dở ({@code start+12+LEN > length}) ⇒ như bản cũ: bỏ đuôi, KHÔNG tính hỏng — trừ
     *       khi sau đó còn MAGIC (đuôi "ghi dở" thật ra là chunk hỏng giữa file, vd đĩa đầy rồi append tiếp)
     *       ⇒ xử lý như chunk hỏng (resync).</li>
     * </ul>
     * File sạch ⇒ kết quả giống hệt bản cũ, droppedChunks = droppedBytes = 0.
     */
    static Records load(String path, long minTs) throws IOException {
        File f = new File(path);
        if (!f.exists()) return new Records(new long[0], new float[0]);
        byte[] all = Files.readAllBytes(f.toPath());
        List<byte[]> chunks = new ArrayList<>();
        int droppedChunks = 0;
        long droppedBytes = 0L;
        int off = 0;
        while (off + HEADER_BYTES <= all.length) {
            final int start = off;
            ByteBuffer head = ByteBuffer.wrap(all, start, HEADER_BYTES).order(ByteOrder.BIG_ENDIAN);
            int magic = head.getInt();
            int len = head.getInt();
            int crc = head.getInt();
            boolean truncated = false;
            if (magic == MAGIC && len >= 0) {
                long end = (long) start + HEADER_BYTES + len;
                if (end > all.length) {
                    truncated = true;   // chunk cuối ghi dở (crash) — hoặc chunk hỏng giữa file
                } else {
                    byte[] comp = new byte[len];
                    System.arraycopy(all, start + HEADER_BYTES, comp, 0, len);
                    byte[] raw = null;
                    if (crc32(comp) == crc) {
                        raw = uncompressOrNull(comp);
                    }
                    if (raw != null) {
                        chunks.add(raw);
                        off = (int) end;
                        continue;
                    }
                }
            }
            // chunk hỏng / ghi dở: resync tới MAGIC kế tiếp
            int next = indexOfMagic(all, start + 1);
            if (next < 0) {
                if (!truncated) {
                    droppedChunks++;
                    droppedBytes += all.length - start;
                }
                break;   // truncated ⇒ hành vi cũ: bỏ đuôi ghi dở
            }
            droppedChunks++;
            droppedBytes += next - start;
            off = next;
        }
        int total = 0;
        for (byte[] c : chunks) total += c.length / RECORD_BYTES;
        ByteBuffer raw = ByteBuffer.allocate(total * RECORD_BYTES).order(ByteOrder.BIG_ENDIAN);
        for (byte[] c : chunks) raw.put(c, 0, (c.length / RECORD_BYTES) * RECORD_BYTES);
        raw.flip();
        long[] tsAll = new long[total];
        float[] rAll = new float[total];
        int i = 0;
        while (raw.remaining() >= RECORD_BYTES) {
            tsAll[i] = raw.getLong();
            rAll[i] = Float.intBitsToFloat(raw.getInt());
            i++;
        }
        int n = 0;
        for (int j = 0; j < total; j++) if (tsAll[j] >= minTs) n++;
        long[] ts = new long[n];
        float[] r = new float[n];
        int k = 0;
        for (int j = 0; j < total; j++) {
            if (tsAll[j] >= minTs) {
                ts[k] = tsAll[j];
                r[k] = rAll[j];
                k++;
            }
        }
        return new Records(ts, r, droppedChunks, droppedBytes);
    }

    /** Snappy.uncompress; lỗi giải nén ⇒ null (coi như chunk hỏng). */
    private static byte[] uncompressOrNull(byte[] comp) {
        try {
            return Snappy.uncompress(comp);
        } catch (IOException | RuntimeException | SnappyError e) {
            return null;
        }
    }

    /** Vị trí đầu tiên ≥ from của byte pattern MAGIC (big-endian "GRR1"), -1 nếu không có. */
    static int indexOfMagic(byte[] a, int from) {
        final byte b0 = (byte) (MAGIC >>> 24);
        final byte b1 = (byte) (MAGIC >>> 16);
        final byte b2 = (byte) (MAGIC >>> 8);
        final byte b3 = (byte) MAGIC;
        for (int p = Math.max(0, from); p + 4 <= a.length; p++) {
            if (a[p] == b0 && a[p + 1] == b1 && a[p + 2] == b2 && a[p + 3] == b3) return p;
        }
        return -1;
    }

    private static byte[] encode(long[] ts, float[] r) {
        ByteBuffer bb = ByteBuffer.allocate(ts.length * RECORD_BYTES).order(ByteOrder.BIG_ENDIAN);
        for (int i = 0; i < ts.length; i++) {
            bb.putLong(ts[i]);
            bb.putInt(Float.floatToIntBits(r[i]));
        }
        return bb.array();
    }

    private static int crc32(byte[] b) {
        CRC32 c = new CRC32();
        c.update(b);
        return (int) c.getValue();
    }
}
