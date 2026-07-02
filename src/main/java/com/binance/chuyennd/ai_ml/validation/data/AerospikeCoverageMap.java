package com.binance.chuyennd.ai_ml.validation.data;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-002 — Coverage map ticker1m trong Aerospike (sitemap dữ liệu THẬT, thay proxy symbol_mapper).
 *
 * ĐỌC-ONLY. Quét tuần tự theo NGÀY (vì không có index symbol→time — xem BO_CODE_DIGEST §B5):
 * mỗi ngày đọc 1 lần readDataFromAerospike1M_ShortKey, đánh dấu (symbol, THÁNG) = CÓ DATA khi có
 * ticker khả dụng (Utils.isTickerAvailable). Tối ưu: mỗi (symbol,tháng) thấy 1 lần là set cờ, các phút
 * còn lại chỉ đọc boolean rồi bỏ qua.
 *
 * Xuất ./outputs/aerospike_coverage.csv: symbol, firstMonth, lastMonth, monthsCovered, gapMonths.
 *   gapMonths = tháng TRONG [firstMonth,lastMonth] nhưng KHÔNG có data (lỗ nội bộ); coin chết (không data
 *   SAU lastMonth) KHÔNG tính là gap.
 *
 * Chỉ USDT-perp (đuôi USDT, không '_'). Đọc 226 (box cần AEROSPIKE_READ_CLUSTER=226 → getReadClient→226, bản đã sync).
 * Chạy trên 226. Log SLF4J, KHÔNG System.out/printStackTrace.
 */
public class AerospikeCoverageMap {

    private static final Logger LOG = LoggerFactory.getLogger(AerospikeCoverageMap.class);

    private static final String START_DATE = "20210101";
    private static final int BASE_YEAR = 2021;
    private static final String OUT = "outputs/aerospike_coverage.csv";

    public static void main(String[] args) {
        try {
            new AerospikeCoverageMap().run();
        } catch (Exception e) {
            LOG.error("❌ CoverageMap lỗi", e);
        }
        System.exit(0);
    }

    private static boolean isUsdtPerp(String s) {
        return s != null && s.endsWith("USDT") && !s.contains("_");
    }

    private static int monthIdx(long ts) {
        Calendar c = Calendar.getInstance();   // GMT+7 (TimeZoneGuard)
        c.setTimeInMillis(ts);
        return (c.get(Calendar.YEAR) - BASE_YEAR) * 12 + c.get(Calendar.MONTH);
    }

    private static String monthLabel(int idx) {
        int y = BASE_YEAR + idx / 12;
        int m = idx % 12 + 1;
        return String.format(Locale.US, "%04d%02d", y, m);
    }

    public void run() throws Exception {
        // Đọc bản ticker đã sync trên 226 (chạy local trên 226 cho nhanh). KHÔNG ghi gì.
        LOG.info("🗺 COVERAGE MAP ticker1m | AEROSPIKE_READ_CLUSTER={} | từ {} → nay", Configs.AEROSPIKE_READ_CLUSTER, START_DATE);

        SimpleSymbolMapper mapper = SimpleSymbolMapper.getInstance();
        mapper.init();

        long startTs = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
        long endTs = System.currentTimeMillis();
        int numMonths = monthIdx(endTs) + 1;

        // Tập id USDT-perp + maxId
        Map<String, Short> all = mapper.getAllMappings();
        List<Short> targetIds = new ArrayList<>();
        int maxId = 0;
        for (Map.Entry<String, Short> e : all.entrySet()) {
            if (isUsdtPerp(e.getKey())) {
                targetIds.add(e.getValue());
                if (e.getValue() > maxId) maxId = e.getValue();
            }
        }
        LOG.info("🔎 mapper: {} symbol | USDT-perp = {} | tháng quét = {} ({}→{})",
                all.size(), targetIds.size(), numMonths, monthLabel(0), monthLabel(numMonths - 1));
        if (targetIds.isEmpty()) {
            LOG.error("⛔ Không có symbol USDT-perp trong mapper — kiểm tra mapper/cấu hình. DỪNG.");
            return;
        }

        boolean[][] cov = new boolean[maxId + 1][numMonths];   // cov[symbolId][monthIdx]

        long t0 = System.currentTimeMillis();
        int dayCount = 0, emptyDays = 0, lastMonthLogged = -1;
        for (long d = startTs; d <= endTs; d += Utils.TIME_DAY) {
            int mi = monthIdx(d);
            if (mi < 0 || mi >= numMonths) continue;

            TreeMap<Long, KlineObjectSimple[]> day;
            try {
                day = DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(d);
            } catch (Exception ex) {
                LOG.warn("⚠️ đọc ngày {} lỗi: {}", Utils.normalizeDateYYYYMMDD(d), ex.getMessage());
                continue;
            }
            dayCount++;
            if (day == null || day.isEmpty()) { emptyDays++; continue; }

            for (KlineObjectSimple[] arr : day.values()) {
                if (arr == null) continue;
                for (short id : targetIds) {
                    if (cov[id][mi]) continue;                 // đã đánh dấu tháng này → bỏ qua
                    if (id < arr.length && arr[id] != null && Utils.isTickerAvailable(arr[id])) {
                        cov[id][mi] = true;
                    }
                }
            }

            if (mi != lastMonthLogged) {                       // log tiến độ theo tháng
                lastMonthLogged = mi;
                LOG.info("   ...quét tới {} ({} ngày, {} rỗng) {}s",
                        monthLabel(mi), dayCount, emptyDays, (System.currentTimeMillis() - t0) / 1000);
            }
        }

        // Dựng CSV + summary
        new File(OUT).getParentFile().mkdirs();
        int symWithData = 0, symWithGap = 0;
        long totalCells = 0;
        try (FileWriter w = new FileWriter(OUT)) {
            w.write("symbol,firstMonth,lastMonth,monthsCovered,gapMonths\n");
            // sort theo symbol cho dễ đọc
            List<Short> sorted = new ArrayList<>(targetIds);
            sorted.sort(Comparator.comparing(mapper::getSymbol));
            for (short id : sorted) {
                int first = -1, last = -1, count = 0;
                for (int m = 0; m < numMonths; m++) {
                    if (cov[id][m]) { if (first < 0) first = m; last = m; count++; }
                }
                if (count == 0) continue;                      // không có data → bỏ khỏi coverage
                symWithData++;
                totalCells += count;
                List<String> gaps = new ArrayList<>();
                for (int m = first; m <= last; m++) if (!cov[id][m]) gaps.add(monthLabel(m));
                if (!gaps.isEmpty()) symWithGap++;
                w.write(String.format(Locale.US, "%s,%s,%s,%d,%s\n",
                        mapper.getSymbol(id), monthLabel(first), monthLabel(last), count, String.join(";", gaps)));
            }
        }

        LOG.info("✅ Đã ghi {} | USDT-perp có data = {} | có gap nội bộ = {} | tổng (symbol×tháng) = {} | {} ngày quét, {}s",
                OUT, symWithData, symWithGap, totalCells, dayCount, (System.currentTimeMillis() - t0) / 1000);
    }
}
