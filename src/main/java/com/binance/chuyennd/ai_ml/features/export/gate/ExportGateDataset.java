package com.binance.chuyennd.ai_ml.features.export.gate;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.NavigableMap;
import java.util.TreeMap;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

/**
 * XUẤT DATASET GATE (feature + label) RA **MỘT FILE DUY NHẤT** — không train, không predict.
 *
 * <p><b>Vì sao tách khỏi {@link WFOGateRunner}</b>: replay Aerospike là nút cổ chai (~30-45s/ngày,
 * cả dải 2021→2026 mất nhiều giờ). Trước đây replay bị KHOÁ CỨNG bên trong vòng WFO nên mỗi lần đổi
 * code train là phải replay lại từ đầu. Tách ra: replay 1 lần → 1 file → đẩy Kaggle → train per-fold
 * ngay trên Kaggle, đổi code train bao nhiêu lần cũng không đụng lại Aerospike.
 *
 * <p><b>Nội dung file</b> (header do {@link #csvHeader()} sinh):
 * {@code timestamp,<34 cột feature theo MarketFeatures.toCSVHeader>,label_oldbasket}.
 * <ul>
 *   <li>{@code timestamp} — epoch ms, BẮT BUỘC có để downstream cắt fold theo cutoff.</li>
 *   <li>33/34 cột là feature số (V3FULL); {@code volatilityRegime} là chuỗi (không nằm trong V3FULL).</li>
 *   <li>{@code label_oldbasket} — max gain trung bình 15 phút tới của rổ {@code findPotentialLosers(ts)}.</li>
 * </ul>
 * <b>KHÔNG có {@code predRisk4H}</b> — trường đó là output của model TĨNH train batch full range (rò rỉ),
 * đã bỏ khỏi pipeline gate.
 *
 * <p><b>Purge khi train per-fold</b>: label nhìn tới +15 phút ⇒ dòng train cuối cùng liếm 15 phút vào
 * block OOS. Phía train (Kaggle) PHẢI cắt {@code train = df[df.timestamp < cutoff_ms - }
 * {@link #LABEL_HORIZON_MS}{@code ]} và assert {@code train.timestamp.max() < cutoff_ms - LABEL_HORIZON_MS}.
 * Export KHÔNG tự purge (giữ nguyên dữ liệu thô để mọi cutoff đều cắt được từ cùng 1 file).
 *
 * <p><b>Kiểm tra hậu-export</b>: đọc lại file, ĐẾM SỐ DÒNG và so với số dòng đã emit (verify size là
 * KHÔNG đủ — bài học từ bug merge label). Lệch ⇒ log ERROR + exit code 1.
 *
 * <p>Args: {@code [start=20210101] [end=20260701] [outFile]}. Đuôi {@code .gz} ⇒ tự gzip.
 */
public class ExportGateDataset {

    static final Logger LOG = LoggerFactory.getLogger(ExportGateDataset.class);

    /** Horizon của label (nhìn tới +15 phút) = purge tối thiểu khi cắt fold train/OOS. */
    public static final long LABEL_HORIZON_MS = 15 * 60_000L;
    static final int WARMUP_HOURS = 48;
    static final String DEFAULT_START = "20210101";
    static final String DEFAULT_END = "20260701";

    /** Nhận mỗi dòng đã emit (dùng khi caller muốn giữ store trong RAM). Có thể null. */
    public interface RowSink {
        void accept(long ts, MarketFeatures features, float label);
    }

    public static void main(String[] args) {
        try {
            DataManagerAerospikeFloatSim.setThreadCount(4);
            String start = args.length > 0 ? args[0] : DEFAULT_START;
            String end = args.length > 1 ? args[1] : DEFAULT_END;
            String home = System.getProperty("user.home");
            String outFile = args.length > 2 ? args[2] : home + "/claudedata/gate_dataset_full.csv.gz";

            long fairStart = Utils.sdfFile.parse(start).getTime();
            long evalEnd = Utils.sdfFile.parse(end).getTime();
            File parent = new File(outFile).getParentFile();
            if (parent != null) {
                parent.mkdirs();
            }

            LOG.info("🚀 EXPORT GATE DATASET | {} -> {} | out={}", start, end, outFile);
            LOG.info("   header: {}", csvHeader());
            long emitted = replayToCsv(fairStart, evalEnd, outFile, null);

            if (emitted <= 0) {
                LOG.error("⛔ Không emit được dòng nào — dừng (exit 1).");
                System.exit(1);
            }

            long onDisk = countDataLines(outFile);
            long bytes = new File(outFile).length();
            LOG.info("🔎 VERIFY: emit={} dòng | file={} dòng data | {} bytes", emitted, onDisk, bytes);
            if (onDisk != emitted) {
                LOG.error("⛔ LỆCH SỐ DÒNG: emit={} nhưng file có {} dòng data (chênh {}). File KHÔNG dùng được.",
                        emitted, onDisk, onDisk - emitted);
                System.exit(1);
            }
            LOG.info("✅ EXPORT OK: {} dòng data + 1 header -> {}", emitted, outFile);
            LOG.info("   Bước tiếp: đẩy file lên Kaggle, train per-fold với purge >= {} ms ({} phút).",
                    LABEL_HORIZON_MS, LABEL_HORIZON_MS / 60_000L);
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("❌ ExportGateDataset FAIL", e);
            System.exit(1);
        }
    }

    /**
     * Header CSV: {@code MarketFeatures.toCSVHeader()} đã gồm {@code timestamp,...,futureReturn15M,maxDrawdownNext4H}
     * → cắt 2 cột label cũ, thay bằng {@code label_oldbasket}. Khớp 1-1 với {@code toCSVRow()} cắt tương ứng.
     */
    public static String csvHeader() {
        String base = new MarketFeatures().toCSVHeader();
        int cut = base.indexOf(",futureReturn15M");
        if (cut > 0) {
            base = base.substring(0, cut);
        }
        return base + ",label_oldbasket";
    }

    /**
     * Replay mọi phút trong [fairStart, evalEnd] (warmup {@value #WARMUP_HOURS}h trước đó) và ghi
     * feature + label ra 1 file CSV. Trả về SỐ DÒNG DATA đã ghi (không kể header).
     *
     * <p>NGUỒN SỰ THẬT DUY NHẤT cho cặp (feature, label) của gate — {@link WFOGateRunner} gọi lại hàm này
     * để tránh 2 bản logic label lệch nhau.
     *
     * @param sink nhận từng dòng để caller giữ RAM store; null = chỉ ghi file (nhẹ RAM).
     */
    public static long replayToCsv(long fairStart, long evalEnd, String outFile, RowSink sink) throws Exception {
        long warmupStart = fairStart - WARMUP_HOURS * Utils.TIME_HOUR;
        TreeMap<Long, MarketDataObject> time2Rate = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        ComprehensiveMarketFeatureExtractor extractor = new ComprehensiveMarketFeatureExtractor();
        double featChecksum = 0;
        long nRows = 0;
        long nSkippedNullFeature = 0;
        long firstTs = -1;
        long lastTs = -1;

        try (BufferedWriter w = openWriter(outFile)) {
            w.write(csvHeader());
            w.newLine();

            long day = Utils.getDate(warmupStart);
            long lastDay = Utils.getDate(evalEnd);
            int dayCount = 0;
            while (day <= lastDay) {
                try {
                    TreeMap<Long, Map<String, KlineObjectSimple>> today =
                            DataManagerAerospikeFloatSim.readDataFromAerospike1M(day);
                    TreeMap<Long, Map<String, KlineObjectSimple>> tomorrow =
                            DataManagerAerospikeFloatSim.readDataFromAerospike1M(day + Utils.TIME_DAY);
                    TreeMap<Long, Map<String, KlineObjectSimple>> lookup = new TreeMap<>();
                    if (today != null) {
                        lookup.putAll(today);
                    }
                    if (tomorrow != null) {
                        lookup.putAll(tomorrow);
                    }
                    if (today == null) {
                        day += Utils.TIME_DAY;
                        continue;
                    }

                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : today.entrySet()) {
                        long ts = e.getKey();
                        Map<String, KlineObjectSimple> snap = e.getValue();
                        HistoryManager.getInstance().updateHistory(snap);
                        CoinRankManager.getInstance().getTopCoin(ts);
                        if (ts < fairStart || ts > evalEnd) {
                            continue;
                        }

                        // MỌI PHÚT (không de-overlap — downstream cần đủ độ phủ để backtest per-minute)
                        MarketFeatures f = extractor.extractAllFeatures(ts, snap, time2Rate.get(ts));
                        if (f == null) {
                            nSkippedNullFeature++;
                            continue;
                        }

                        List<String> basketOld = HistoryManager.getInstance().findPotentialLosers(ts);
                        float label = basketMaxGain(lookup, ts, basketOld);

                        // toCSVRow bắt đầu bằng timestamp + kết thúc bằng 2 cột label cũ → cắt 2 cột cuối,
                        // thêm label_oldbasket. KHỚP csvHeader(). KHÔNG thêm ts thừa.
                        String row = f.toCSVRow();
                        int idx = nthLastComma(row, 2);
                        if (idx > 0) {
                            row = row.substring(0, idx);
                        }
                        w.write(row);
                        w.write(',');
                        w.write(fmt(label));
                        w.newLine();

                        nRows++;
                        if (firstTs < 0) {
                            firstTs = ts;
                        }
                        lastTs = ts;
                        featChecksum += f.momentum15M + f.volatility15M + f.basketVolSpike;
                        if (sink != null) {
                            sink.accept(ts, f, label);
                        }
                    }
                } catch (Exception ex) {
                    LOG.warn("⚠️ Lỗi ngày {}: {}", Utils.normalizeDateYYYYMMDD(day), ex.getMessage());
                }
                day += Utils.TIME_DAY;
                if (++dayCount % 30 == 0) {
                    LOG.info("... replay {} ngày | rows={} | day={}", dayCount, nRows,
                            Utils.normalizeDateYYYYMMDD(day));
                }
            }
        }
        LOG.info("   replay xong: rows={} | skip(feature null)={} | range {} .. {}", nRows, nSkippedNullFeature,
                firstTs < 0 ? "-" : Utils.normalizeDateYYYYMMDD(firstTs),
                lastTs < 0 ? "-" : Utils.normalizeDateYYYYMMDD(lastTs));
        LOG.info("   featChecksum={} (so 2 lần chạy để check determinism)", String.format(Locale.US, "%.6f", featChecksum));
        return nRows;
    }

    /** Đếm SỐ DÒNG DATA (không kể header) đọc lại từ file đã ghi. Verify size là KHÔNG đủ. */
    public static long countDataLines(String path) throws Exception {
        long lines = 0;
        try (BufferedReader r = openReader(path)) {
            while (r.readLine() != null) {
                lines++;
            }
        }
        return lines > 0 ? lines - 1 : 0;   // trừ header
    }

    private static BufferedWriter openWriter(String path) throws Exception {
        OutputStream os = new FileOutputStream(path);
        if (path.endsWith(".gz")) {
            os = new GZIPOutputStream(os, 1 << 16);
        }
        return new BufferedWriter(new OutputStreamWriter(os, StandardCharsets.UTF_8), 1 << 20);
    }

    private static BufferedReader openReader(String path) throws Exception {
        InputStream is = new FileInputStream(path);
        if (path.endsWith(".gz")) {
            is = new GZIPInputStream(is, 1 << 16);
        }
        return new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8), 1 << 20);
    }

    /** Label gate: max gain trung bình trong 15 phút tới của rổ coin. Nguồn sự thật duy nhất. */
    static float basketMaxGain(TreeMap<Long, Map<String, KlineObjectSimple>> data, long ts, List<String> basket) {
        if (basket == null || basket.isEmpty()) {
            return 0f;
        }
        NavigableMap<Long, Map<String, KlineObjectSimple>> future = data.subMap(ts, false, ts + LABEL_HORIZON_MS, true);
        if (future.isEmpty()) {
            return 0f;
        }
        Map<String, KlineObjectSimple> atT = data.get(ts);
        if (atT == null) {
            return 0f;
        }
        float sum = 0;
        int cnt = 0;
        for (String sym : basket) {
            KlineObjectSimple k0 = atT.get(sym);
            if (k0 == null || k0.priceClose <= 0) {
                continue;
            }
            float entry = (float) k0.priceClose;
            float maxGain = 0;
            for (Map<String, KlineObjectSimple> snap : future.values()) {
                KlineObjectSimple k = snap.get(sym);
                if (k != null && k.maxPrice > 0) {
                    float g = (float) ((k.maxPrice - entry) / entry);
                    if (g > maxGain) {
                        maxGain = g;
                    }
                }
            }
            sum += maxGain;
            cnt++;
        }
        return cnt > 0 ? sum / cnt : 0f;
    }

    static int nthLastComma(String s, int n) {
        int count = 0;
        for (int i = s.length() - 1; i >= 0; i--) {
            if (s.charAt(i) == ',' && ++count == n) {
                return i;
            }
        }
        return -1;
    }

    static String fmt(float v) {
        if (Float.isNaN(v) || Float.isInfinite(v)) {
            return "0.000000";
        }
        return String.format(Locale.US, "%.8f", v);
    }
}
