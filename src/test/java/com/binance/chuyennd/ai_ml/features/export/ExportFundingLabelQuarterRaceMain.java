package com.binance.chuyennd.ai_ml.features.export;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.LongAdder;

/**
 * TASK-251 — TÁI HIỆN RACE "gộp quý quá sớm" của {@link ExportFundingLabel}, chạy được trên máy
 * Windows, KHÔNG cần Aerospike/Oracle/Kaggle.
 *
 * <p><b>Bug thật đo được trên production log</b> (quý 20241001_to_20250101): 4 partition ghi song
 * song, log có tới 9 lần "đóng file quý" cho CÙNG một quý, và dòng "✅ Đã gộp quý" xuất hiện SAU
 * lần đóng thứ 4 — trong khi 5 lần đóng còn lại (gồm nguyên 1 partition 11.859.598 dòng) xảy ra
 * SAU đó. Tổng thật 40.575.661 dòng, file gộp chỉ 28.660.118 ⇒ mất 29,37%.
 *
 * <p><b>Hai lỗi cộng hưởng, cả hai đều được test này bắt:</b>
 * <ol>
 *   <li>{@code sinkFor()} mở lại file quý đã đóng bằng {@code new FileOutputStream(path)} (GHI ĐÈ,
 *       không append) ⇒ mất sạch phần đã ghi trước đó của partition ấy.</li>
 *   <li>{@code closeSink()} đếm số LẦN ĐÓNG chứ không đếm số PARTITION PHÂN BIỆT ⇒ 1 partition
 *       đóng-mở-đóng nhiều lượt cũng đẩy bộ đếm chạm {@code nParts} ⇒ gộp khi partition khác còn
 *       đang ghi; sau khi gộp, file {@code .partN} bị xoá, mọi dòng ghi tiếp KHÔNG bao giờ vào
 *       file cuối.</li>
 * </ol>
 *
 * <p><b>Vì sao lại có chuyện mở lại quý đã đóng</b> (không phải giả định — chính là mô hình mà test
 * này mô phỏng): anchor được ghi vào file quý theo {@code tEpoch} LÚC TẠO, nhưng chỉ EMIT khi coin
 * có nến mới vượt {@code t + H_MAX}. Coin có GAP dữ liệu vài tuần/tháng (hoặc coin chết, chỉ được
 * flush ở cuối day-loop) sẽ emit anchor của quý CŨ khi day-loop đã đi rất xa ⇒ quý đó đã bị
 * {@code closeQuartersUpTo()} đóng từ lâu.
 *
 * <p><b>Cách chạy</b> (giống {@code Tool1ColRoundTripMain}):
 * <pre>
 *   mvn -DskipTests test-compile
 *   java -cp "target/classes;target/test-classes;&lt;deps&gt;" \
 *        com.binance.chuyennd.ai_ml.features.export.ExportFundingLabelQuarterRaceMain target/label_race
 * </pre>
 * Exit code 0 = PASS (mọi quý khớp CHÍNH XÁC), 1 = FAIL (in rõ quý nào lệch bao nhiêu dòng).
 *
 * <p>Test KHÔNG mô phỏng lại thuật toán ghi quý — nó gọi THẲNG các hàm production
 * ({@code sinkFor}/{@code closeQuartersUpTo}/{@code closeAllRemaining}/{@code mergeAllQuarters}),
 * nên FAIL/PASS phản ánh đúng code thật.
 */
public final class ExportFundingLabelQuarterRaceMain {

    private static final Logger LOG = LoggerFactory.getLogger(ExportFundingLabelQuarterRaceMain.class);

    private static final int N_PARTS = 4;
    private static final long DAY_MS = 24L * 3600_000L;
    /** Số dòng "bình thường" mỗi partition ghi cho mỗi ngày. */
    private static final int ROWS_PER_DAY = 40;
    /** Cứ mỗi {@value} ngày, partition emit thêm vài anchor CŨ (mô phỏng coin có gap / coin chết). */
    private static final int LATE_EVERY_DAYS = 30;
    private static final int LATE_ROWS = 7;
    /** Anchor "đến muộn" thuộc thời điểm cách hiện tại 150 ngày (chắc chắn thuộc quý đã đóng). */
    private static final long LATE_BACK_MS = 150 * DAY_MS;
    /** Partition p ngủ p*SLOW_MS_PER_PART ms mỗi ngày -> 4 partition LỆCH PHA rõ rệt (part3 chậm nhất). */
    private static final int SLOW_MS_PER_PART = 4;

    private ExportFundingLabelQuarterRaceMain() {
    }

    public static void main(String[] args) throws Exception {
        String outDir = args.length > 0 ? args[0] : "target/label_race";
        File dir = new File(outDir);
        cleanDir(dir);
        if (!dir.exists() && !dir.mkdirs()) {
            LOG.error("Không tạo được thư mục {}", dir.getAbsolutePath());
            System.exit(2);
        }
        String outPath = outDir + "/race_label.csv";   // .csv chỉ là tên tham số, file thật là .pb

        long start = dayEpoch(2024, 1, 1);
        long end = dayEpoch(2025, 7, 1);

        // Kế toán ĐỘC LẬP của test: quý -> số dòng đã ghi vào (mọi partition cộng lại).
        ConcurrentHashMap<Long, LongAdder> expected = new ConcurrentHashMap<>();
        ExportFundingLabel.QuarterRegistry reg = new ExportFundingLabel.QuarterRegistry(N_PARTS);

        List<Thread> threads = new ArrayList<>();
        List<Throwable> errors = java.util.Collections.synchronizedList(new ArrayList<>());
        for (int p = 0; p < N_PARTS; p++) {
            final int partIdx = p;
            final long s0 = start, e0 = end;
            Thread t = new Thread(() -> {
                try {
                    runPartition(partIdx, s0, e0, outPath, reg, expected);
                } catch (Throwable ex) {
                    errors.add(ex);
                }
            }, "race-part" + p);
            threads.add(t);
            t.start();
        }
        for (Thread t : threads) t.join();
        if (!errors.isEmpty()) {
            LOG.error("Partition ném exception — test KHÔNG kết luận được", errors.get(0));
            System.exit(2);
        }

        int bad = ExportFundingLabel.mergeAllQuarters(outPath, N_PARTS, reg);
        LOG.info("mergeAllQuarters báo {} quý lỗi", bad);

        // ===== KIỂM CHỨNG: số dòng THỰC trong file quý cuối cùng phải KHỚP CHÍNH XÁC =====
        Map<Long, Long> exp = new TreeMap<>();
        for (Map.Entry<Long, LongAdder> e : expected.entrySet()) exp.put(e.getKey(), e.getValue().sum());

        long totalExp = 0, totalGot = 0;
        int nBad = 0;
        for (Map.Entry<Long, Long> e : exp.entrySet()) {
            long qStart = e.getKey();
            long qEnd = ExportFundingLabel.quarterEndEpoch(qStart);
            String finalPath = ExportFundingLabel.quarterFinalPath(outPath, qStart, qEnd);
            long got = ExportFundingLabel.countRowsInPb(finalPath);
            long want = e.getValue();
            totalExp += want;
            if (got > 0) totalGot += got;
            if (got == want) {
                LOG.info("  ✅ quý {}: {} dòng (khớp)", ExportFundingLabel.quarterSuffix(qStart, qEnd), got);
            } else {
                nBad++;
                LOG.error("  ❌ quý {}: file cuối có {} dòng, ĐÃ GHI VÀO {} dòng -> LỆCH {} ({}%){}",
                        ExportFundingLabel.quarterSuffix(qStart, qEnd), got, want, want - got,
                        String.format(java.util.Locale.US, "%.2f", 100.0 * (want - got) / want),
                        got < 0 ? "  [KHÔNG CÓ FILE QUÝ CUỐI — chưa từng được gộp]" : "");
            }
        }
        // Rác còn sót: .partN chưa được gộp = dữ liệu mồ côi.
        File[] leftovers = dir.listFiles((d, n) -> n.contains(".part"));
        if (leftovers != null && leftovers.length > 0) {
            for (File f : leftovers) {
                LOG.error("  ❌ file .part MỒ CÔI (đã gộp xong nhưng vẫn còn dữ liệu ghi thêm): {} ({} bytes, {} dòng)",
                        f.getName(), f.length(), ExportFundingLabel.countRowsInPb(f.getPath()));
            }
            nBad += leftovers.length;
        }

        LOG.info("TỔNG: đã ghi {} dòng | trong file quý cuối {} dòng | {} quý | {} quý LỆCH",
                totalExp, totalGot, exp.size(), nBad);
        if (nBad == 0 && bad == 0) {
            LOG.info("KẾT QUẢ: PASS — mọi quý khớp CHÍNH XÁC, không mất dòng nào.");
            System.exit(0);
        }
        LOG.error("KẾT QUẢ: FAIL — mất {} dòng ({}%) do race gộp quý.",
                totalExp - totalGot, String.format(java.util.Locale.US, "%.2f",
                        totalExp == 0 ? 0.0 : 100.0 * (totalExp - totalGot) / totalExp));
        System.exit(1);
    }

    /** Mô phỏng day-loop của 1 partition: ghi dòng của ngày hiện tại + thỉnh thoảng ghi anchor CŨ
     *  (coin gap/coin chết), sau mỗi ngày gọi closeQuartersUpTo đúng như production. */
    private static void runPartition(int partIdx, long start, long end, String outPath,
                                     ExportFundingLabel.QuarterRegistry reg,
                                     ConcurrentHashMap<Long, LongAdder> expected) throws Exception {
        ExportFundingLabel.PartCtx ctx =
                new ExportFundingLabel.PartCtx(outPath, partIdx, N_PARTS, reg);
        int nH = ExportFundingLabel.H_MINUTES.length;
        float[] mf = new float[nH], ma = new float[nH], re = new float[nH];
        int[] tf = new int[nH], ta = new int[nH], nb = new int[nH];
        boolean[] reSet = new boolean[nH];
        for (int h = 0; h < nH; h++) {
            mf[h] = 0.01f * (h + 1);
            ma[h] = -0.01f * (h + 1);
            tf[h] = 15 * (h + 1);
            ta[h] = 30 * (h + 1);
            re[h] = 0.002f * (h + 1);
            reSet[h] = true;
            nb[h] = ExportFundingLabel.H_MINUTES[h];
        }

        int dayIdx = 0;
        for (long day = start; day < end; day += DAY_MS, dayIdx++) {
            if (SLOW_MS_PER_PART * partIdx > 0) Thread.sleep(SLOW_MS_PER_PART * partIdx);

            for (int i = 0; i < ROWS_PER_DAY; i++) {
                long tEpoch = day + i * 900_000L;      // trong ngày -> chắc chắn cùng quý với `day`
                write(ctx, expected, "P" + partIdx + "C" + (i % 5), tEpoch, mf, ma, tf, ta, re, reSet, nb);
            }
            // anchor "đến muộn" của quý CŨ (coin có gap dữ liệu / coin chết được flush trễ)
            if (dayIdx % LATE_EVERY_DAYS == LATE_EVERY_DAYS - 1 && day - LATE_BACK_MS >= start) {
                for (int i = 0; i < LATE_ROWS; i++) {
                    long tEpoch = day - LATE_BACK_MS + i * 900_000L;
                    write(ctx, expected, "P" + partIdx + "GAP", tEpoch, mf, ma, tf, ta, re, reSet, nb);
                }
            }
            ExportFundingLabel.closeQuartersUpTo(ctx, day);
        }
        ExportFundingLabel.closeAllRemaining(ctx);
    }

    private static void write(ExportFundingLabel.PartCtx ctx, ConcurrentHashMap<Long, LongAdder> expected,
                              String sym, long tEpoch, float[] mf, float[] ma, int[] tf, int[] ta,
                              float[] re, boolean[] reSet, int[] nb) throws Exception {
        ExportFundingLabel.QuarterSink s = ExportFundingLabel.sinkFor(ctx, tEpoch);
        s.w.add(sym, tEpoch, mf, ma, tf, ta, re, reSet, nb);
        s.rows++;
        expected.computeIfAbsent(s.qStart, k -> new LongAdder()).increment();
    }

    /** Epoch 00:00 GMT+7 của 1 ngày — CÙNG quy ước với start/end/day của ExportFundingLabel.main(). */
    private static long dayEpoch(int y, int m, int d) {
        java.util.Calendar c = java.util.Calendar.getInstance(java.util.TimeZone.getTimeZone("GMT+7"));
        c.clear();
        c.set(y, m - 1, d, 0, 0, 0);
        return c.getTimeInMillis();
    }

    private static void cleanDir(File dir) {
        File[] fs = dir.listFiles();
        if (fs == null) return;
        for (File f : fs) {
            if (f.isFile() && !f.delete()) LOG.warn("Không xoá được {}", f.getAbsolutePath());
        }
    }
}
