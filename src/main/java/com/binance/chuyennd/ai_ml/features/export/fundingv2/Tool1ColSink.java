package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedOutputStream;
import java.io.Closeable;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.Arrays;
import java.util.zip.GZIPOutputStream;

/**
 * TASK-251 — ghi TOOL1 (40 feature) ra định dạng <b>T1C2</b> (columnar + quantize int16/int32 +
 * byte-split + delta) thay cho row-major float32 170 B/record, để cắt quota Kaggle.
 *
 * <p><b>[2026-08-08] T1C1 → T1C2 — thêm cột int32 THÍCH ỨNG.</b> Đo thật quý 2024Q3 (12 chunk): 3 cột
 * vượt ngưỡng sai số 5e-3 vì IQR cực nhỏ quanh 0 nhưng đuôi rất xa, làm bước lượng tử int16 quá thô —
 * f20 fundingRateTrend (range/IQR=2175, err 1.70e-2), f24 fundingSum24h (1319, 1.02e-2), f26
 * volumeZCoin (1575, 1.23e-2). Biến đổi log1p KHÔNG cứu được (đo: 1.69e-2 / 1.01e-2 / 1.40e-2). Giải
 * pháp: cột nào có {@code (hi-lo)/IQR} vượt ngưỡng thì lưu int32 (xem {@link #WIDE_RATIO_THRESHOLD};
 * ngưỡng ban đầu 640 đã hạ xuống 300 [2026-08-07] sau khi đo thật quý 2024Q3 thấy f20 vẫn lỗi 5.319e-3
 * &gt; 5e-3 ở ngưỡng cũ — xem javadoc của {@code WIDE_RATIO_THRESHOLD}).
 * <b>Khác biệt so với T1C1:</b> magic {@code T1C2}; ngay SAU {@code stepMin} có thêm {@code wideMask}
 * (int64 LE, bit j = 1 ⇒ cột j là int32); cột int32 chiếm {@code 4*R} byte, byte-split thành 4 stream
 * liên tiếp (toàn bộ byte 3, byte 2, byte 1, byte 0), delta wraparound trên int32, sentinel
 * {@link #WIDE_SENTINEL}, scale {@code 4.2e9/(hi-lo)} map về [-2.1e9, +2.1e9]. Cột bit=0 giữ NGUYÊN
 * layout T1C1. Reader {@code ml/lib/tool1_col.py} đọc được cả T1C1 cũ, T1C2 mới và {@code .bin.gz} cũ
 * — nhận diện theo MAGIC, không tin đuôi file.
 *
 * <p><b>Vì sao đổi (số đo THẬT trên 1.176.470 record quý 2024Q2, không suy đoán):</b> row-major
 * float32 sau gzip = 105.96 B/record; T1C1 sau gzip = 27.97 B/record → <b>giảm 3.79 lần</b>. Sai số
 * lượng tử hoá xấu nhất chỉ 0.0038 IQR của cột (nhỏ hơn nhiễu tick nhiều bậc).
 *
 * <p><b>4 kỹ thuật tạo ra khác biệt</b> (thiếu bất kỳ cái nào thì gần như vô ích):
 * <ol>
 *   <li><b>Columnar</b>: gom {@link #CHUNK_ROWS} record rồi ghi từng CỘT liền nhau → giá trị cùng
 *       thang đo nằm cạnh nhau → gzip nén tốt hơn hẳn row-major (row-major xen kẽ 40 thang đo khác
 *       nhau, entropy cao).</li>
 *   <li><b>Quantize int16 theo min/max của CHÍNH chunk</b> (chế độ "full"): 4 byte float32 → 2 byte.
 *       TUYỆT ĐỐI KHÔNG winsorize/clip theo percentile — đã đo: winsorize gây sai số 450 lần IQR mà
 *       file lại TO HƠN (clip làm mất tính đơn điệu cục bộ → delta xấu đi).</li>
 *   <li><b>Delta theo hàng liền trước</b>: sau khi sort (symbol, t), feature của cùng 1 coin ở 2 phút
 *       liên tiếp gần như bằng nhau → delta ≈ 0.</li>
 *   <li><b>Byte-split</b>: ghi TOÀN BỘ byte cao của cột trước, rồi TOÀN BỘ byte thấp. Byte cao của
 *       chuỗi delta nhỏ gần như toàn 0x00/0xFF → gzip ăn cực mạnh. Đây là thứ biến 2 B/ô thành ~0.7
 *       B/ô sau nén.</li>
 * </ol>
 *
 * <p><b>Mỗi chunk TỰ MÔ TẢ ĐẦY ĐỦ</b> (magic + rowCount + nCols + baseMs + stepMin + colMeta) → file
 * KHÔNG có header toàn cục, nên gộp nhiều file part chỉ là nối byte (sau khi giải nén gzip). Reader
 * Python: {@code ml/lib/tool1_col.py}.
 *
 * <p><b>ENDIAN — điểm dễ sai nhất:</b> mọi số nguyên/thực nhiều byte đều <b>LITTLE-ENDIAN</b>
 * (định dạng cũ dùng {@code DataOutputStream} = BIG-endian). Reader numpy dùng dtype {@code "<i4"},
 * {@code "<i8"}, {@code "<f8"}.
 *
 * <p><b>Không thread-safe</b> — mỗi thread/partition giữ sink riêng (giống {@code QuarterSink} và
 * {@code LabelPbSink}).
 *
 * <p><b>RAM</b>: 200k × 40 float = 32MB buffer cột + ~2MB scratch. Job export chạy {@code -Xmx10g}.
 */
public class Tool1ColSink implements Closeable {

    private static final Logger LOG = LoggerFactory.getLogger(Tool1ColSink.class);

    /** Số record gom vào 1 chunk. Khớp {@code LabelPbSink.CHUNK_ROWS}; PHẢI ≤ 2^18 (giới hạn sort key). */
    public static final int CHUNK_ROWS = 200_000;

    /** Số cột feature — khớp cứng {@code ExportFeaturesForPythonTool.convertFeaturesToArray()}. */
    public static final int N_COLS = 40;

    /** Mã đánh dấu ô NaN/Inf. Nằm NGOÀI dải hợp lệ [-32000, +32000] nên không bao giờ nhập nhằng. */
    public static final short SENTINEL = -32768;

    /** Biên độ q của giá trị hữu hạn: [-QLIM, +QLIM]. Chừa khoảng trống cho SENTINEL. */
    private static final int QLIM = 32000;

    /** Số mức lượng tử hoá = 2*QLIM. lo→-QLIM, hi→+QLIM. */
    private static final double QSPAN = 64000.0;

    /** Mã đánh dấu ô NaN/Inf của cột WIDE (int32). Nằm ngoài [-WIDE_QLIM, +WIDE_QLIM]. */
    public static final int WIDE_SENTINEL = Integer.MIN_VALUE;

    /** Biên độ q của cột WIDE: [-2.1e9, +2.1e9] (chừa chỗ cho WIDE_SENTINEL và tránh tràn int). */
    private static final int WIDE_QLIM = 2_100_000_000;

    /** Số mức lượng tử hoá của cột WIDE = 2*WIDE_QLIM. */
    private static final double WIDE_QSPAN = 4.2e9;

    /**
     * Ngưỡng {@code (hi-lo)/IQR} để chuyển 1 cột sang int32.
     *
     * <p><b>Vì sao 640 KHÔNG còn an toàn — hạ xuống 300 [2026-08-07]:</b> sai số lượng tử hoá int16 là
     * HẰNG SỐ theo cột, bằng {@code 0.5/scale = range/128000}. Tỉ số kiểm chứng của cả pipeline là
     * {@code max|err|/IQR}, tức {@code (range/IQR)/128000}. Ngưỡng 640 nhắm ĐÚNG BẰNG 5e-3
     * ({@code 640/128000 = 5e-3}) nên KHÔNG chừa biên: IQR/range của cột được tính theo TỪNG CHUNK,
     * lệch nhẹ so với IQR/range tính trên mẫu lớn là đủ để vượt ngưỡng chấp nhận. Đo thật trên dữ liệu
     * quý 2024Q3 sau khi convert xong rồi verify: cột f20 fundingRateTrend cho sai số thực đo
     * <b>5.319e-3</b> &gt; 5e-3 mặc dù range/IQR của nó (≈2175) đã vượt xa 640 — bằng chứng ngưỡng 640
     * không đủ biên an toàn cho sai lệch IQR chunk-vs-toàn-mẫu ngay cả với cột đã vượt rõ. Ngưỡng mới
     * {@code 300 → 300/128000 ≈ 2.3e-3}, chừa biên hơn 2 lần so với mục tiêu 5e-3 để hấp thụ sai lệch
     * IQR giữa chunk và toàn mẫu. Dung lượng KHÔNG còn là ràng buộc (dự phóng ổ đĩa 45/100 GB), nên ưu
     * tiên độ chính xác hơn kích thước file — hạ ngưỡng khiến nhiều cột hơn chuyển sang int32.
     *
     * <p><b>Vì sao phải THÍCH ỨNG theo chunk, không hard-code danh sách cột:</b> đo thật quý 2024Q3
     * (12 chunk, range/IQR đo được): f20=2175, f24=1319, f26=1575 (vượt xa ngay cả ngưỡng cũ); f11=437,
     * f17=406, f25=400, f37=618, f22=109, f23=142, f19=99 (chỉ vượt ngưỡng MỚI 300, không vượt ngưỡng
     * cũ 640) — quý khác có thể lệch thêm. log1p KHÔNG cứu được (đã đo: f20 còn 1.69e-2). Quyết định
     * theo từng chunk cũng TỰ NHẤT QUÁN: quyết định dùng range/IQR CỦA CHÍNH chunk, mà sai số của chunk
     * cũng tính trên range CỦA CHÍNH chunk.
     */
    private static final double WIDE_RATIO_THRESHOLD = 300.0;

    /** T1C2 = T1C1 + trường wideMask (int64 LE, ngay sau stepMin) + cột int32 tuỳ chọn. */
    private static final byte[] MAGIC = {'T', '1', 'C', '2'};

    private final String path;
    private final OutputStream out;
    private final int stepMin;
    private final long stepMs;

    // ---- buffer 1 chunk, layout columnar sẵn để khỏi tạo 200k object ----
    private final long[] tsBuf = new long[CHUNK_ROWS];
    private final int[] symBuf = new int[CHUNK_ROWS];
    private final float[][] colBufF = new float[N_COLS][CHUNK_ROWS];
    private int n = 0;

    // ---- scratch dùng lại giữa các chunk (không cấp phát trong vòng lặp nóng) ----
    private final byte[] scratch8 = new byte[8];
    private final double[] lo = new double[N_COLS];
    private final double[] scale = new double[N_COLS];
    private final int[] tIdx = new int[CHUNK_ROWS];
    private final long[] sortKey = new long[CHUNK_ROWS];
    private final short[] q = new short[CHUNK_ROWS];
    private final int[] q32 = new int[CHUNK_ROWS];
    private final byte[] i32Buf = new byte[4 * CHUNK_ROWS];
    private final byte[] colBytes = new byte[2 * CHUNK_ROWS];
    /** Bản sao giá trị hữu hạn của 1 cột để sort tính IQR (không đụng colBufF). */
    private final float[] iqrBuf = new float[CHUNK_ROWS];
    /** wide[j] = cột j của chunk HIỆN TẠI lưu int32 (bit j của wideMask). */
    private final boolean[] wide = new boolean[N_COLS];

    private long totalRows = 0;
    private int chunkCount = 0;

    /**
     * @param path    đường dẫn file đích (quy ước tên: {@code features_<start>_to_<end>.t1c.gz})
     * @param stepMin bước lưới thời gian tính bằng PHÚT dùng để mã hoá {@code tIdx}. Canonical = 1
     *                (ghi thẳng vào chunk để reader không phải đoán). Không phải "lưới lấy mẫu" —
     *                dữ liệu có thể thưa hơn, {@code tIdx} chỉ cần chia hết là được.
     */
    public Tool1ColSink(String path, int stepMin) throws IOException {
        if (stepMin <= 0) {
            throw new IllegalArgumentException("stepMin phải > 0, nhận: " + stepMin);
        }
        this.path = path;
        this.stepMin = stepMin;
        this.stepMs = stepMin * 60_000L;
        this.out = new BufferedOutputStream(
                new GZIPOutputStream(new FileOutputStream(path), 1 << 16), 1 << 20);
    }

    /**
     * Thêm 1 record. Mảng {@code f40} được COPY vào buffer cột nên phía gọi tái dùng được.
     *
     * @param ts    epoch ms của mốc
     * @param symId id symbol (dải short: [-32768, 32767] — khớp {@code writeShort} của định dạng cũ)
     * @param f40   đúng {@link #N_COLS} phần tử, thứ tự của {@code convertFeaturesToArray()}
     */
    public void add(long ts, int symId, float[] f40) throws IOException {
        if (f40 == null || f40.length != N_COLS) {
            throw new IllegalArgumentException("f40 phải có đúng " + N_COLS + " phần tử, nhận: "
                    + (f40 == null ? "null" : String.valueOf(f40.length)));
        }
        tsBuf[n] = ts;
        symBuf[n] = symId;
        for (int j = 0; j < N_COLS; j++) {
            colBufF[j][n] = f40[j];
        }
        n++;
        totalRows++;
        if (n == CHUNK_ROWS) {
            flushChunk();
        }
    }

    /** Tổng số record đã nhận (kể cả phần chưa flush). */
    public long rows() {
        return totalRows;
    }

    /** Số chunk đã ghi (dùng cho log/kiểm tra). */
    public int chunks() {
        return chunkCount;
    }

    @Override
    public void close() throws IOException {
        // finally BẮT BUỘC: nếu flushChunk() ném (dữ liệu nguồn hỏng → tIdx/symId ngoài dải) mà
        // không đóng stream thì trên Windows file .tmp bị giữ handle ⇒ KHÔNG xoá được, để lại rác
        // ".t1c.gz.tmp" cạnh dữ liệu thật. Phát hiện khi test ConvertTool1BinToCol với file gzip hỏng.
        try {
            flushChunk();
        } finally {
            out.close();
        }
        long size = new File(path).length();
        LOG.info("Tool1ColSink đóng {}: {} record | {} chunk | {} bytes ({} B/record sau gzip)",
                path, totalRows, chunkCount, size,
                totalRows > 0 ? String.format("%.2f", size / (double) totalRows) : "n/a");
    }

    // ======================= phần lõi =======================

    /**
     * Sort buffer theo (symId, tIdx) rồi ghi ra 1 chunk T1C1.
     *
     * <p>Sort không dùng comparator (tránh boxing 200k Integer): gói {@code (symId, tIdx, viTri)} vào
     * 1 long rồi {@link Arrays#sort(long[], int, int)} — symId nằm bit cao nhất nên thứ tự long CHÍNH
     * LÀ thứ tự (symbol, t, ổn định). Bố cục bit: symId+32768 ở bit 48..63 (16 bit), tIdx ở bit 18..47
     * (30 bit = 2000 năm ở lưới 1 phút), chỉ số hàng ở bit 0..17 (18 bit ≥ CHUNK_ROWS).
     */
    private void flushChunk() throws IOException {
        if (n == 0) {
            return;
        }
        final int R = n;

        // --- baseMs = min(ts) trong chunk; tIdx = số bước kể từ baseMs ---
        long base = Long.MAX_VALUE;
        for (int i = 0; i < R; i++) {
            if (tsBuf[i] < base) base = tsBuf[i];
        }
        for (int i = 0; i < R; i++) {
            long d = (tsBuf[i] - base) / stepMs;
            if (d < 0 || d > 0x3FFFFFFFL) {
                throw new IllegalStateException("tIdx=" + d + " vượt 30 bit (ts=" + tsBuf[i]
                        + ", baseMs=" + base + ", stepMin=" + stepMin + ") — chunk trải quá dài?");
            }
            int s = symBuf[i];
            if (s < Short.MIN_VALUE || s > Short.MAX_VALUE) {
                throw new IllegalStateException("symId=" + s + " ngoài dải short — sort key sẽ hỏng.");
            }
            tIdx[i] = (int) d;
            sortKey[i] = ((long) (s + 32768) << 48) | ((long) tIdx[i] << 18) | i;
        }
        Arrays.sort(sortKey, 0, R);

        // --- colMeta: min/max/IQR chỉ trên giá trị HỮU HẠN (bỏ NaN/Inf), theo TỪNG CHUNK ---
        long wideMask = 0L;
        for (int j = 0; j < N_COLS; j++) {
            float[] c = colBufF[j];
            double mn = Double.POSITIVE_INFINITY;
            double mx = Double.NEGATIVE_INFINITY;
            int m = 0;
            for (int i = 0; i < R; i++) {
                float v = c[i];
                if (v == v && !Float.isInfinite(v)) {   // v == v loại NaN
                    if (v < mn) mn = v;
                    if (v > mx) mx = v;
                    iqrBuf[m++] = v;
                }
            }
            wide[j] = false;
            if (mn > mx) {              // không có giá trị hữu hạn nào → mọi ô sẽ là SENTINEL
                lo[j] = 0.0;
                scale[j] = 1.0;
                continue;
            }
            double range = mx - mn;
            if (range > 0) {
                // IQR trên chính chunk này (sort tại chỗ trên bản sao) — nội suy tuyến tính, KHỚP
                // np.percentile mặc định của test Python, để 2 bên nói cùng một con số.
                java.util.Arrays.sort(iqrBuf, 0, m);
                double iqr = pct(iqrBuf, m, 0.75) - pct(iqrBuf, m, 0.25);
                // iqr == 0 (gần như mọi giá trị bằng nhau) mà range > 0 ⇒ tỉ số vô cực ⇒ chắc chắn wide.
                wide[j] = (iqr <= 0) || (range / iqr > WIDE_RATIO_THRESHOLD);
            }
            if (mx <= mn) mx = mn + 1e-9;   // cột hằng số → tránh chia 0
            lo[j] = mn;
            scale[j] = (wide[j] ? WIDE_QSPAN : QSPAN) / (mx - mn);
            if (wide[j]) wideMask |= 1L << j;
        }

        // --- header chunk (LITTLE-ENDIAN toàn bộ) ---
        out.write(MAGIC);
        writeI32(R);
        writeI32(N_COLS);
        writeI64(base);
        writeI32(stepMin);
        writeI64(wideMask);      // T1C2: bit j = 1 ⇒ cột j lưu int32 (4*R byte) thay vì int16 (2*R byte)
        for (int j = 0; j < N_COLS; j++) {
            writeF64(lo[j]);
            writeF64(scale[j]);
        }

        // --- dTidx / dSym (int32 CÓ DẤU: dTidx âm khi sang symbol mới, tIdx nhảy về đầu) ---
        int prev = 0;
        for (int k = 0; k < R; k++) {
            int i = (int) (sortKey[k] & 0x3FFFFL);
            putI32(i32Buf, k << 2, tIdx[i] - prev);
            prev = tIdx[i];
        }
        out.write(i32Buf, 0, R << 2);

        prev = 0;
        for (int k = 0; k < R; k++) {
            int i = (int) (sortKey[k] & 0x3FFFFL);
            putI32(i32Buf, k << 2, symBuf[i] - prev);
            prev = symBuf[i];
        }
        out.write(i32Buf, 0, R << 2);

        // --- 40 cột: cột thường 2*R byte (int16), cột WIDE 4*R byte (int32) ---
        for (int j = 0; j < N_COLS; j++) {
            float[] c = colBufF[j];
            final double l = lo[j];
            final double s = scale[j];
            if (wide[j]) {
                for (int k = 0; k < R; k++) {
                    int i = (int) (sortKey[k] & 0x3FFFFL);
                    float v = c[i];
                    int qv;
                    if (v != v || Float.isInfinite(v)) {
                        qv = WIDE_SENTINEL;
                    } else {
                        double t = Math.rint(((double) v - l) * s - (double) WIDE_QLIM);
                        if (t > WIDE_QLIM) t = WIDE_QLIM;
                        else if (t < -WIDE_QLIM) t = -WIDE_QLIM;
                        qv = (int) t;
                    }
                    q32[k] = qv;
                }
                // delta 1 bước (WRAPAROUND mod 2^32 — int Java vốn wrap, cùng lý do như int16 bên dưới)
                // + byte-split 4 stream: toàn bộ byte 3, rồi byte 2, byte 1, byte 0.
                int prevQ32 = 0;
                for (int k = 0; k < R; k++) {
                    int d = q32[k] - prevQ32;
                    prevQ32 = q32[k];
                    i32Buf[k] = (byte) (d >>> 24);
                    i32Buf[R + k] = (byte) (d >>> 16);
                    i32Buf[2 * R + k] = (byte) (d >>> 8);
                    i32Buf[3 * R + k] = (byte) d;
                }
                out.write(i32Buf, 0, R << 2);
                continue;
            }
            for (int k = 0; k < R; k++) {
                int i = (int) (sortKey[k] & 0x3FFFFL);
                float v = c[i];
                short qv;
                if (v != v || Float.isInfinite(v)) {
                    qv = SENTINEL;
                } else {
                    long t = Math.round(((double) v - l) * s - 32000.0);
                    if (t > QLIM) t = QLIM;
                    else if (t < -QLIM) t = -QLIM;
                    qv = (short) t;
                }
                q[k] = qv;
            }
            // delta 1 bước + byte-split (toàn bộ byte cao trước, rồi toàn bộ byte thấp)
            short prevQ = 0;   // ⇒ d[0] = q[0] - 0 = q[0], đúng spec
            for (int k = 0; k < R; k++) {
                // (short) = WRAPAROUND mod 65536, KHÔNG phải clamp. Bắt buộc phải wrap:
                // q ∈ [-32768, +32000] nên hiệu 2 ô liền nhau có thể tới ±64768 (vd ô NaN
                // = -32768 đứng cạnh ô +32000) — clamp về ±32767 sẽ LÀM HỎNG VĨNH VIỄN mọi ô
                // phía sau (cumsum lệch). Wraparound thì cumsum-mod-65536 phục hồi CHÍNH XÁC
                // vì bản thân q luôn nằm gọn trong 1 chu kỳ int16. Với |d| ≤ 32767 (đại đa số)
                // wraparound cho ra ĐÚNG cùng byte như clamp, nên không đổi tỉ lệ nén.
                short d = (short) (q[k] - prevQ);
                prevQ = q[k];
                colBytes[k] = (byte) ((d >> 8) & 0xFF);
                colBytes[R + k] = (byte) (d & 0xFF);
            }
            out.write(colBytes, 0, R << 1);
        }

        n = 0;
        chunkCount++;
    }

    // ======================= ghi little-endian =======================

    private void writeI32(int v) throws IOException {
        putI32(scratch8, 0, v);
        out.write(scratch8, 0, 4);
    }

    private void writeI64(long v) throws IOException {
        for (int b = 0; b < 8; b++) {
            scratch8[b] = (byte) (v >>> (8 * b));
        }
        out.write(scratch8, 0, 8);
    }

    private void writeF64(double v) throws IOException {
        writeI64(Double.doubleToLongBits(v));
    }

    /** Phân vị nội suy tuyến tính trên mảng ĐÃ SORT — khớp {@code np.percentile(..., method="linear")}
     *  để ngưỡng wide tính ở Java và số đo kiểm chứng ở Python là CÙNG một định nghĩa. */
    private static double pct(float[] sorted, int m, double p) {
        if (m == 0) return 0.0;
        if (m == 1) return sorted[0];
        double pos = p * (m - 1);
        int i0 = (int) Math.floor(pos);
        int i1 = Math.min(i0 + 1, m - 1);
        double frac = pos - i0;
        return sorted[i0] + frac * (sorted[i1] - sorted[i0]);
    }

    private static void putI32(byte[] buf, int off, int v) {
        buf[off] = (byte) v;
        buf[off + 1] = (byte) (v >>> 8);
        buf[off + 2] = (byte) (v >>> 16);
        buf[off + 3] = (byte) (v >>> 24);
    }
}
