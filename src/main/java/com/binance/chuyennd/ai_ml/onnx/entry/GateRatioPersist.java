package com.binance.chuyennd.ai_ml.onnx.entry;

import org.xerial.snappy.Snappy;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
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

        Records(long[] ts, float[] r) {
            this.ts = ts;
            this.r = r;
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

    /** Ghi LẠI toàn bộ file (compact/khởi tạo): xoá cũ, ghi tất cả record thành các chunk. */
    static void writeFresh(String path, long[] ts, float[] r) throws IOException {
        File f = new File(path);
        File parent = f.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("khong tao duoc thu muc " + parent);
        }
        if (f.exists() && !f.delete()) {
            throw new IOException("khong xoa duoc file cu " + path);
        }
        append(path, ts, r);
    }

    /** Đọc toàn bộ file, verify CRC32 từng chunk, trả record có ts >= minTs. Dừng ở chunk cuối hợp lệ. */
    static Records load(String path, long minTs) throws IOException {
        File f = new File(path);
        if (!f.exists()) return new Records(new long[0], new float[0]);
        byte[] all = Files.readAllBytes(f.toPath());
        List<byte[]> chunks = new ArrayList<>();
        int off = 0;
        while (off + HEADER_BYTES <= all.length) {
            ByteBuffer head = ByteBuffer.wrap(all, off, HEADER_BYTES).order(ByteOrder.BIG_ENDIAN);
            int magic = head.getInt();
            int len = head.getInt();
            int crc = head.getInt();
            off += HEADER_BYTES;
            if (magic != MAGIC) {
                throw new IOException("magic sai tai offset " + (off - HEADER_BYTES));
            }
            if (off + len > all.length) {
                break;   // chunk cuối ghi dở (crash) -> bỏ qua phần đuôi
            }
            byte[] comp = new byte[len];
            System.arraycopy(all, off, comp, 0, len);
            off += len;
            if (crc32(comp) != crc) {
                throw new IOException("CRC32 lech tai chunk cuoi (file hong?)");
            }
            chunks.add(Snappy.uncompress(comp));
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
        return new Records(ts, r);
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
