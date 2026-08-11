package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedInputStream;
import java.io.EOFException;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.GZIPInputStream;
import java.util.zip.ZipException;

/**
 * TASK-251 — CONVERT OFFLINE định dạng TOOL1 CŨ ({@code .bin.gz}) sang MỚI ({@code .t1c.gz}).
 *
 * <p><b>Vì sao cần:</b> đã có sẵn nhiều quý xuất ở định dạng cũ nằm trên đĩa Oracle và trên Kaggle.
 * Convert chỉ đọc-ghi file, KHÔNG đụng Aerospike ⇒ rẻ hơn export lại hàng chục lần (export phải quét
 * lại toàn bộ key funding + tính lại 40 feature).
 *
 * <p><b>Định dạng vào</b> (sinh bởi {@code DataOutputStream}, BIG-ENDIAN, bọc GZIP):
 * {@code long ts (8B) + short symId (2B) + float32 × 40 (160B)} = <b>170 B/record</b>, row-major.
 * <br><b>Định dạng ra</b>: T1C2 (LITTLE-ENDIAN, columnar + quantize int16/int32 + byte-split + delta),
 * xem {@link Tool1ColSink} — cột nào có {@code range/IQR > 640} thì tự động dùng int32, quyết định
 * theo TỪNG CHUNK. Reader Python: {@code ml/lib/tool1_col.py} (đọc được cả .bin.gz cũ, T1C1 và T1C2).
 *
 * <p><b>ENDIAN là chỗ dễ sai nhất</b>: vào BIG-endian, ra LITTLE-endian. Ở đây byte vào được giải mã
 * THỦ CÔNG theo big-endian (không dùng {@code DataInputStream} để tránh 1 lời gọi ảo/field, và để
 * đọc theo lô 170×N byte thay vì 42 lời gọi read/record).
 *
 * <p><b>Streaming, KHÔNG load cả file</b>: file thật ~11 GB sau giải nén. Bộ nhớ thực dùng =
 * buffer đọc {@value #BATCH_RECORDS}×170 B (~0.7 MB) + buffer cột của {@link Tool1ColSink}
 * (200k × 40 float ≈ 32 MB + phụ trợ ≈ 6 MB). Chạy thoải mái với {@code -Xmx512m}.
 *
 * <p><b>TOÀN VẸN — 3 quy tắc:</b>
 * <ol>
 *   <li>Ghi ra {@code <out>.tmp} rồi mới {@code rename} thành {@code <out>}: KHÔNG bao giờ tồn tại
 *       file {@code .t1c.gz} "hoàn chỉnh-giả" nếu quá trình gãy giữa chừng.</li>
 *   <li>File nguồn CỤT (job crash ⇒ gzip cụt, hoặc record cuối thiếu byte): giữ {@code k} record đầy
 *       đủ đã đọc được, ghi ra bình thường, và log <b>WARNING</b> nêu rõ số byte thừa bị bỏ. Không
 *       im lặng nuốt lỗi.</li>
 *   <li>Gzip stream HỎNG ({@link ZipException}: sai CRC/ISIZE/header/khối deflate) ⇒ FAIL, exit code
 *       ≠ 0, xoá file tạm. Không ghi ra {@code .t1c.gz} rồi báo thành công.</li>
 * </ol>
 *
 * <p><b>Cách dùng:</b>
 * <pre>
 *   # 1 file
 *   java -Xmx1g -cp binance-java-sdk-*.jar \
 *        com.binance.chuyennd.ai_ml.features.export.fundingv2.ConvertTool1BinToCol \
 *        in/features_x_to_y.bin.gz out/features_x_to_y.t1c.gz
 *
 *   # cả thư mục (mọi *.bin.gz / *.bin, bỏ qua *.part*)
 *   java -Xmx1g -cp ... ConvertTool1BinToCol inDir outDir
 *
 *   # tuỳ chọn: --stepMin=1 (mặc định) | --allowOffGrid
 * </pre>
 */
public final class ConvertTool1BinToCol {

    private static final Logger LOG = LoggerFactory.getLogger(ConvertTool1BinToCol.class);

    /** Kích thước 1 record định dạng cũ: 8 (ts) + 2 (sym) + 40×4 (feature). */
    public static final int REC_BYTES = 170;

    /** Số record đọc 1 lô. 4096×170 ≈ 0.7 MB — đủ để amortize lời gọi read, không tốn RAM. */
    private static final int BATCH_RECORDS = 4096;

    /** Bước log tiến độ. */
    private static final long PROGRESS_EVERY = 5_000_000L;

    private ConvertTool1BinToCol() {
    }

    // ======================= CLI =======================

    public static void main(String[] args) {
        int code;
        try {
            code = run(args);
        } catch (Throwable t) {
            LOG.error("CONVERT THẤT BẠI: {}", t.toString(), t);
            code = 1;
        }
        if (code != 0) {
            System.exit(code);
        }
    }

    private static int run(String[] args) throws IOException {
        int stepMin = 1;
        boolean allowOffGrid = false;
        List<String> pos = new ArrayList<>();
        for (String a : args) {
            if (a.startsWith("--stepMin=")) {
                stepMin = Integer.parseInt(a.substring("--stepMin=".length()).trim());
            } else if ("--allowOffGrid".equals(a)) {
                allowOffGrid = true;
            } else if (a.startsWith("--")) {
                LOG.error("Tham số không hiểu: {}", a);
                return 2;
            } else {
                pos.add(a);
            }
        }
        if (pos.size() != 2) {
            LOG.error("Cú pháp: ConvertTool1BinToCol <in .bin.gz | inDir> <out .t1c.gz | outDir> "
                    + "[--stepMin=1] [--allowOffGrid]");
            return 2;
        }
        File in = new File(pos.get(0));
        File out = new File(pos.get(1));
        if (!in.exists()) {
            LOG.error("Không thấy đường dẫn vào: {}", in.getAbsolutePath());
            return 2;
        }
        return in.isDirectory()
                ? convertDir(in, out, stepMin, allowOffGrid)
                : (convertOne(in, out, stepMin, allowOffGrid) ? 0 : 1);
    }

    /** Convert hàng loạt. Một file lỗi KHÔNG dừng cả mẻ, nhưng exit code cuối cùng ≠ 0. */
    private static int convertDir(File inDir, File outDir, int stepMin, boolean allowOffGrid) {
        File[] all = inDir.listFiles();
        if (all == null) {
            LOG.error("Không đọc được thư mục {}", inDir.getAbsolutePath());
            return 2;
        }
        List<File> src = new ArrayList<>();
        for (File f : all) {
            String nm = f.getName();
            if (!f.isFile()) continue;
            if (nm.contains(".part")) {
                LOG.warn("BỎ QUA {} — file .part (job export đang ghi dở, chưa có gzip trailer).", nm);
                continue;
            }
            if (nm.endsWith(".bin.gz") || nm.endsWith(".bin")) src.add(f);
        }
        src.sort((a, b) -> a.getName().compareTo(b.getName()));
        if (src.isEmpty()) {
            LOG.error("Thư mục {} không có file *.bin.gz / *.bin nào.", inDir.getAbsolutePath());
            return 2;
        }
        if (!outDir.exists() && !outDir.mkdirs()) {
            LOG.error("Không tạo được thư mục ra {}", outDir.getAbsolutePath());
            return 2;
        }
        LOG.info("CONVERT THƯ MỤC: {} file từ {} -> {}", src.size(), inDir.getAbsolutePath(),
                outDir.getAbsolutePath());
        int failed = 0;
        for (int i = 0; i < src.size(); i++) {
            File f = src.get(i);
            String base = f.getName().endsWith(".bin.gz")
                    ? f.getName().substring(0, f.getName().length() - ".bin.gz".length())
                    : f.getName().substring(0, f.getName().length() - ".bin".length());
            File dst = new File(outDir, base + ".t1c.gz");
            LOG.info("[{}/{}] {}", i + 1, src.size(), f.getName());
            boolean ok;
            try {
                ok = convertOne(f, dst, stepMin, allowOffGrid);
            } catch (Exception e) {
                LOG.error("[{}/{}] {} LỖI: {}", i + 1, src.size(), f.getName(), e.toString(), e);
                ok = false;
            }
            if (!ok) failed++;
        }
        LOG.info("XONG MẺ: {} thành công / {} lỗi trên tổng {} file", src.size() - failed, failed,
                src.size());
        return failed == 0 ? 0 : 1;
    }

    // ======================= phần lõi =======================

    /**
     * Convert 1 file. Trả về {@code true} nếu file đích đã được tạo (kể cả trường hợp nguồn bị cụt —
     * lúc đó đã có WARNING nêu rõ), {@code false} nếu FAIL (file tạm đã bị xoá).
     */
    public static boolean convertOne(File in, File out, int stepMin, boolean allowOffGrid) {
        Path outPath = out.toPath().toAbsolutePath();
        Path tmpPath = Paths.get(outPath.toString() + ".tmp");
        Path parent = outPath.getParent();
        long t0 = System.currentTimeMillis();
        long rows = 0;
        boolean truncatedGzip = false;
        int trailingBytes = 0;
        long offGrid = 0;
        Tool1ColSink sink = null;
        try {
            if (parent != null) {
                Files.createDirectories(parent);
            }
            Files.deleteIfExists(tmpPath);
            sink = new Tool1ColSink(tmpPath.toString(), stepMin);

            final long stepMs = stepMin * 60_000L;
            final byte[] buf = new byte[BATCH_RECORDS * REC_BYTES];
            final float[] f40 = new float[Tool1ColSink.N_COLS];
            int have = 0;
            long tsResidue = Long.MIN_VALUE;
            long nextLog = PROGRESS_EVERY;

            try (InputStream raw = new FileInputStream(in);
                 InputStream gz = in.getName().endsWith(".gz")
                         ? new GZIPInputStream(new BufferedInputStream(raw, 1 << 20), 1 << 16)
                         : new BufferedInputStream(raw, 1 << 20)) {

                boolean eof = false;
                while (!eof) {
                    int r;
                    try {
                        r = gz.read(buf, have, buf.length - have);
                    } catch (EOFException e) {
                        // GZIPInputStream ném EOFException("Unexpected end of ZLIB input stream")
                        // khi member gzip bị CẮT CỤT (job crash giữa chừng). Dữ liệu đã giải nén
                        // được TRƯỚC đó vẫn hợp lệ ⇒ giữ lại, chỉ cảnh báo.
                        truncatedGzip = true;
                        break;
                    }
                    if (r < 0) {
                        eof = true;
                    } else {
                        have += r;
                    }
                    int full = have / REC_BYTES;
                    for (int k = 0; k < full; k++) {
                        int off = k * REC_BYTES;
                        long ts = getLongBE(buf, off);
                        int sym = (short) (((buf[off + 8] & 0xFF) << 8) | (buf[off + 9] & 0xFF));
                        int p = off + 10;
                        for (int j = 0; j < Tool1ColSink.N_COLS; j++, p += 4) {
                            f40[j] = Float.intBitsToFloat(getIntBE(buf, p));
                        }
                        long res = Math.floorMod(ts, stepMs);
                        if (tsResidue == Long.MIN_VALUE) {
                            tsResidue = res;
                        } else if (res != tsResidue) {
                            offGrid++;
                        }
                        sink.add(ts, sym, f40);
                        rows++;
                    }
                    int used = full * REC_BYTES;
                    int rest = have - used;
                    if (rest > 0 && used > 0) {
                        System.arraycopy(buf, used, buf, 0, rest);
                    }
                    have = rest;
                    if (have == buf.length) {
                        // không thể xảy ra (buf là bội số của REC_BYTES) — chặn vòng lặp vô hạn
                        throw new IllegalStateException("Buffer đầy mà không tách được record nào");
                    }
                    if (rows >= nextLog) {
                        long ms = Math.max(1L, System.currentTimeMillis() - t0);
                        LOG.info("  ... {} record | {} rec/s | {} chunk", rows,
                                String.format("%.0f", rows * 1000.0 / ms), sink.chunks());
                        nextLog += PROGRESS_EVERY;
                    }
                }
            }
            trailingBytes = have;

            // --- các bất thường: PHẢI nói ra, không nuốt ---
            if (truncatedGzip) {
                LOG.warn("NGUỒN BỊ CỤT (gzip stream kết thúc đột ngột — job export nhiều khả năng đã "
                                + "crash): {} — đã giữ {} record ĐẦY ĐỦ đầu tiên, BỎ {} byte dở dang ở cuối. "
                                + "File ra {} là dữ liệu THẬT nhưng THIẾU phần đuôi của nguồn.",
                        in.getAbsolutePath(), rows, trailingBytes, out.getName());
            } else if (trailingBytes > 0) {
                LOG.warn("NGUỒN THỪA {} byte ở cuối (không đủ 1 record {} B — record cuối bị ghi dở): "
                                + "{} — đã giữ {} record đầy đủ, BỎ {} byte đó.",
                        trailingBytes, REC_BYTES, in.getAbsolutePath(), rows, trailingBytes);
            }
            if (offGrid > 0) {
                String msg = "ts KHÔNG nằm trên lưới " + stepMin + " phút: " + offGrid + "/" + rows
                        + " record có ts%" + stepMs + " khác record đầu (=" + tsResidue + "). Định dạng "
                        + "T1C1 mã hoá ts thành tIdx=(ts-base)/stepMs nên phần dư SẼ BỊ MẤT vĩnh viễn.";
                if (!allowOffGrid) {
                    throw new IllegalStateException(msg + " Dừng để tránh hỏng ts âm thầm. Nếu CHẤP NHẬN "
                            + "làm tròn xuống thì chạy lại với --allowOffGrid.");
                }
                LOG.warn("{} --allowOffGrid đang BẬT nên vẫn ghi, ts sẽ bị làm tròn xuống.", msg);
            }
            if (rows == 0) {
                LOG.warn("Nguồn {} không có record hợp lệ nào — vẫn tạo {} rỗng (0 chunk).",
                        in.getAbsolutePath(), out.getName());
            }

            sink.close();
            sink = null;
            Files.move(tmpPath, outPath, StandardCopyOption.REPLACE_EXISTING);

            long ms = Math.max(1L, System.currentTimeMillis() - t0);
            long inSize = in.length();
            long outSize = Files.size(outPath);
            LOG.info("OK {} -> {} | {} record trong {} s ({} rec/s) | vào {} B ({} B/rec) "
                            + "-> ra {} B ({} B/rec) | GIẢM {}x{}",
                    in.getName(), out.getName(), rows, String.format("%.1f", ms / 1000.0),
                    String.format("%.0f", rows * 1000.0 / ms),
                    inSize, rows > 0 ? String.format("%.2f", inSize / (double) rows) : "n/a",
                    outSize, rows > 0 ? String.format("%.2f", outSize / (double) rows) : "n/a",
                    outSize > 0 ? String.format("%.2f", inSize / (double) outSize) : "n/a",
                    truncatedGzip ? "  [CẢNH BÁO: nguồn bị cụt, xem WARN phía trên]" : "");
            return true;

        } catch (ZipException e) {
            // CRC/ISIZE sai, header hỏng, khối deflate hỏng: dữ liệu đã giải nén KHÔNG đáng tin.
            LOG.error("GZIP HỎNG ở {}: {} — KHÔNG tạo file {} (đã đọc được {} record trước khi hỏng, "
                            + "nhưng không thể tin nội dung). Cần re-export file này.",
                    in.getAbsolutePath(), e.toString(), out.getName(), rows, e);
            closeQuietly(sink);
            deleteQuietly(tmpPath);
            return false;
        } catch (Exception e) {
            LOG.error("LỖI khi convert {} -> {} (đã xử lý {} record): {}", in.getAbsolutePath(),
                    out.getAbsolutePath(), rows, e.toString(), e);
            closeQuietly(sink);
            deleteQuietly(tmpPath);
            return false;
        }
    }

    // ======================= tiện ích =======================

    /** Đọc long BIG-ENDIAN — khớp {@code DataOutputStream.writeLong} của định dạng cũ. */
    private static long getLongBE(byte[] b, int off) {
        return ((long) (b[off] & 0xFF) << 56)
                | ((long) (b[off + 1] & 0xFF) << 48)
                | ((long) (b[off + 2] & 0xFF) << 40)
                | ((long) (b[off + 3] & 0xFF) << 32)
                | ((long) (b[off + 4] & 0xFF) << 24)
                | ((long) (b[off + 5] & 0xFF) << 16)
                | ((long) (b[off + 6] & 0xFF) << 8)
                | ((long) (b[off + 7] & 0xFF));
    }

    /** Đọc int BIG-ENDIAN — khớp {@code DataOutputStream.writeFloat} (= writeInt của floatToIntBits). */
    private static int getIntBE(byte[] b, int off) {
        return ((b[off] & 0xFF) << 24)
                | ((b[off + 1] & 0xFF) << 16)
                | ((b[off + 2] & 0xFF) << 8)
                | (b[off + 3] & 0xFF);
    }

    private static void closeQuietly(Tool1ColSink sink) {
        if (sink == null) return;
        try {
            sink.close();
        } catch (Exception e) {
            LOG.warn("Bỏ qua lỗi khi đóng sink dở dang: {}", e.toString());
        }
    }

    private static void deleteQuietly(Path p) {
        try {
            if (Files.deleteIfExists(p)) {
                LOG.warn("Đã xoá file tạm dở dang {}", p);
            }
        } catch (IOException e) {
            LOG.error("KHÔNG xoá được file tạm {} — hãy xoá tay trước khi chạy lại: {}", p, e.toString());
        }
    }
}
