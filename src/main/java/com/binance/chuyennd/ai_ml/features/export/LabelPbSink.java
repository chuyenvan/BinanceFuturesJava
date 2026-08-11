package com.binance.chuyennd.ai_ml.features.export;

import com.binance.chuyennd.ai_ml.features.export.pb.FundingLabelProto.HorizonCols;
import com.binance.chuyennd.ai_ml.features.export.pb.FundingLabelProto.LabelChunk;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedOutputStream;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * TASK-251 — ghi LABEL ra protobuf columnar thay cho CSV, để cắt quota Kaggle.
 *
 * <p><b>Vì sao đổi (số đo thật, không suy đoán):</b> Kaggle tính quota private dataset theo BẢN NÉN
 * NỘI BỘ của nó (≈ gzip), KHÔNG theo size file thô. Đo trên 3M dòng label thật rồi push lên Kaggle
 * verify: CSV 601MB thô → quota 161.8MB; protobuf row-based → quota 163.2MB (KHÔNG giảm gì!);
 * protobuf columnar + delta-giữa-horizon + scale 1e-5 → quota 46.5MB = <b>giảm 3.48 lần</b>.
 * Chi tiết xem {@code src/main/proto/funding_label.proto} và tasks/251-...md Phần 35.
 *
 * <p><b>3 kỹ thuật tạo ra khác biệt</b> (thiếu bất kỳ cái nào thì protobuf gần như vô ích):
 * <ol>
 *   <li><b>Columnar</b>: gom {@link #CHUNK_ROWS} dòng thành 1 {@link LabelChunk}, mỗi cột 1 mảng
 *       packed → dữ liệu cùng kiểu nằm liền nhau → nén tốt hơn hẳn row-based.</li>
 *   <li><b>Delta giữa horizon</b>: {@code maxFav} là running max nên {@code maxFav_12h} thường BẰNG
 *       {@code maxFav_4h}. Lưu h0 rồi (h1−h0), (h2−h1)… → phần lớn = 0 → nén cực tốt. {@code nBars}
 *       lưu THIẾU HỤT so với kỳ vọng (đủ nến ⇒ 0).</li>
 *   <li><b>Sort trong chunk theo (symbol, t)</b>: đo thật 3.50x (sort-trong-chunk) &gt; 3.49x (sort
 *       toàn cục) &gt; 2.96x (không sort). Chỉ cần buffer 1 chunk (~21MB), KHÔNG phải buffer cả quý —
 *       nên vẫn giữ được kiến trúc partition + đóng-file-theo-quý hiện có.</li>
 * </ol>
 *
 * <p><b>Mỗi chunk TỰ CHỨA dictionary symbol của nó</b> → gộp nhiều file part của cùng 1 quý chỉ là
 * NỐI BYTE thuần (không cần remap sym_id, không cần parse lại). Đây là lý do
 * {@code ExportFundingLabel.mergeQuarter} sau khi đổi sang protobuf lại ĐƠN GIẢN và NHANH hơn bản
 * CSV cũ (bản cũ phải đọc/ghi lại từng dòng text).
 *
 * <p><b>Không thread-safe</b> — mỗi partition-thread giữ sink riêng, đúng như QuarterSink cũ.
 */
public class LabelPbSink {

    private static final Logger LOG = LoggerFactory.getLogger(LabelPbSink.class);

    /** Số dòng gom vào 1 chunk. 200k đo ra tỉ lệ nén tốt nhất; RAM ~21MB/sink (26 int × 4B × 200k). */
    public static final int CHUNK_ROWS = 200_000;

    /** Hệ số nhân ratio trước khi làm tròn về int. 100000 = 1e-5 (Uni chốt sau khi xem tác động thật:
     *  sai số ≤ 0.05 basis point, nhỏ hơn fee taker 4bps tới 80 lần). Ghi thẳng vào chunk để reader
     *  không phải đoán — muốn đổi precision chỉ cần sửa hằng số này, reader tự thích ứng. */
    public static final int SCALE = 100_000;

    private final OutputStream out;
    private final long baseMs;
    private final int stepMin;
    private final int nH;
    private final String[] horizons;
    /** Số nến KỲ VỌNG của từng horizon = H_MINUTES[h] / stepMin. Dùng làm mốc để lưu thiếu hụt. */
    private final int[] nBarsExpect;

    // ---- buffer 1 chunk, layout columnar sẵn để khỏi tạo 200k object ----
    private final int[] symId = new int[CHUNK_ROWS];
    private final int[] tIdx = new int[CHUNK_ROWS];
    private final int[] nullMask = new int[CHUNK_ROWS];
    private final int[][] maxFav, maxAdv, thitFav, thitAdv, retEnd, nBars;
    private int n = 0;

    /** Dictionary symbol tích luỹ dần; ghi lại vào MỖI chunk (vài KB, không đáng kể so với chunk ~8MB). */
    private final Map<String, Integer> symDict = new LinkedHashMap<>();

    private long totalRows = 0;

    public LabelPbSink(String path, long baseMs, int stepMin, String[] horizons, int[] hMinutes)
            throws Exception {
        this(path, baseMs, stepMin, horizons, hMinutes, false);
    }

    /**
     * @param append TRUE ⇒ mở file ở chế độ NỐI THÊM thay vì ghi đè.
     *
     * <p><b>Vì sao phải có tham số này (bug thật TASK-251):</b> 1 partition có thể MỞ LẠI file quý mà
     * chính nó đã đóng — anchor của coin có gap dữ liệu / coin chết được emit rất trễ so với lúc tạo.
     * Bản cũ luôn {@code new FileOutputStream(path)} (TRUNCATE) nên lần mở lại XOÁ SẠCH phần đã ghi
     * trước đó. Định dạng file là chuỗi chunk {@code writeDelimitedTo} tự-mô-tả, nên NỐI THÊM là hợp
     * lệ tuyệt đối (đọc lại vẫn đúng, y như việc gộp file part bằng nối byte).
     */
    public LabelPbSink(String path, long baseMs, int stepMin, String[] horizons, int[] hMinutes,
                       boolean append) throws Exception {
        this.out = new BufferedOutputStream(new FileOutputStream(path, append), 1 << 20);
        this.baseMs = baseMs;
        this.stepMin = stepMin;
        this.horizons = horizons;
        this.nH = horizons.length;
        this.nBarsExpect = new int[nH];
        for (int h = 0; h < nH; h++) nBarsExpect[h] = hMinutes[h] / stepMin;
        this.maxFav = new int[nH][CHUNK_ROWS];
        this.maxAdv = new int[nH][CHUNK_ROWS];
        this.thitFav = new int[nH][CHUNK_ROWS];
        this.thitAdv = new int[nH][CHUNK_ROWS];
        this.retEnd = new int[nH][CHUNK_ROWS];
        this.nBars = new int[nH][CHUNK_ROWS];
    }

    /** Giá trị float "rỗng" theo đúng quy ước của CSV cũ ({@code ExportFundingLabel.f()} ghi chuỗi rỗng). */
    private static boolean isEmpty(float v) {
        return Float.isNaN(v) || v == -Float.MAX_VALUE || v == Float.MAX_VALUE;
    }

    private int scaled(float v) {
        return isEmpty(v) ? 0 : Math.round(v * SCALE);
    }

    /**
     * Thêm 1 dòng label. Mảng đầu vào dài đúng {@code horizons.length}.
     *
     * @param tHitFavMin/tHitAdvMin offset PHÚT THẬT (đã nhân stepMin ở phía gọi, giống CSV cũ)
     * @param retEndSet false ⇒ không có close đúng mốc (gap) ⇒ ô rỗng
     */
    public void add(String sym, long tEpoch, float[] mf, float[] ma, int[] tHitFavMin,
                    int[] tHitAdvMin, float[] re, boolean[] retEndSet, int[] nb) throws Exception {
        Integer sid = symDict.get(sym);
        if (sid == null) {
            sid = symDict.size();
            symDict.put(sym, sid);
        }
        symId[n] = sid;
        tIdx[n] = (int) ((tEpoch - baseMs) / (stepMin * 60_000L));
        int mask = 0;
        for (int h = 0; h < nH; h++) {
            if (isEmpty(mf[h])) mask |= 1 << (h * 3);
            if (isEmpty(ma[h])) mask |= 1 << (h * 3 + 1);
            if (!retEndSet[h] || isEmpty(re[h])) mask |= 1 << (h * 3 + 2);
            maxFav[h][n] = scaled(mf[h]);
            maxAdv[h][n] = scaled(ma[h]);
            thitFav[h][n] = tHitFavMin[h];
            thitAdv[h][n] = tHitAdvMin[h];
            retEnd[h][n] = retEndSet[h] ? scaled(re[h]) : 0;
            nBars[h][n] = nBarsExpect[h] - nb[h];   // đủ nến ⇒ 0 ⇒ nén cực tốt
        }
        nullMask[n] = mask;
        n++;
        totalRows++;
        if (n == CHUNK_ROWS) flushChunk();
    }

    /**
     * Sắp xếp buffer theo (symbol, t) rồi ghi ra 1 {@link LabelChunk} đã delta-hoá.
     *
     * <p>Sort không dùng comparator (tránh boxing 200k Integer): gói {@code (symId, tIdx, viTri)} vào
     * 1 long duy nhất rồi {@link Arrays#sort(long[])} — vì symId nằm ở bit cao nhất, thứ tự long chính
     * là thứ tự (symbol, t, ổn định). Giới hạn: symId &lt; 2^28, tIdx &lt; 2^18 (=262143 bước; 1 quý
     * dài nhất trên lưới 1 phút = 132.480 bước, còn dư gấp đôi), CHUNK_ROWS ≤ 2^18.
     */
    private void flushChunk() throws Exception {
        if (n == 0) return;
        long[] key = new long[n];
        for (int i = 0; i < n; i++) {
            key[i] = ((long) symId[i] << 36) | ((long) tIdx[i] << 18) | i;
        }
        Arrays.sort(key);

        LabelChunk.Builder c = LabelChunk.newBuilder()
                .setBaseMs(baseMs)
                .setStepMin(stepMin)
                .setScale(SCALE)
                .setRowCount(n);
        for (String s : symDict.keySet()) c.addSymbols(s);
        for (String h : horizons) c.addHorizons(h);

        int prevSym = 0, prevT = 0;
        HorizonCols.Builder[] hb = new HorizonCols.Builder[nH];
        for (int h = 0; h < nH; h++) hb[h] = HorizonCols.newBuilder();

        for (int k = 0; k < n; k++) {
            int i = (int) (key[k] & 0x3FFFF);
            c.addSymId(symId[i] - prevSym);
            prevSym = symId[i];
            c.addTIdx(tIdx[i] - prevT);
            prevT = tIdx[i];
            c.addNullMask(nullMask[i]);
            for (int h = 0; h < nH; h++) {
                // h0 = giá trị gốc; h>0 = delta so với horizon liền trước (thường = 0)
                hb[h].addMaxFav(h == 0 ? maxFav[0][i] : maxFav[h][i] - maxFav[h - 1][i]);
                hb[h].addMaxAdv(h == 0 ? maxAdv[0][i] : maxAdv[h][i] - maxAdv[h - 1][i]);
                hb[h].addThitFav(h == 0 ? thitFav[0][i] : thitFav[h][i] - thitFav[h - 1][i]);
                hb[h].addThitAdv(h == 0 ? thitAdv[0][i] : thitAdv[h][i] - thitAdv[h - 1][i]);
                hb[h].addRetEnd(h == 0 ? retEnd[0][i] : retEnd[h][i] - retEnd[h - 1][i]);
                hb[h].addNBarsDeficit(nBars[h][i]);
            }
        }
        for (int h = 0; h < nH; h++) c.addH(hb[h]);
        c.build().writeDelimitedTo(out);
        n = 0;
    }

    public long rows() {
        return totalRows;
    }

    public void close() throws Exception {
        flushChunk();
        out.close();
    }
}
