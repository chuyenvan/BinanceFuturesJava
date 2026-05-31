package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.TreeMap;

public class BenchmarkFullComparison {

    private static final Logger LOG = LoggerFactory.getLogger(BenchmarkFullComparison.class);

    // CẤU HÌNH TEST
    private static final String START_DATE = "20251001";
    // Lưu ý: Nếu để 30 ngày, Test 1 (Aerospike) có thể chạy rất lâu (vài phút).
    // Để test nhanh bạn có thể giảm xuống 5 ngày.
    private static final int DAYS_TO_TEST = 30;

    public static void main(String[] args) {
        try {
            Configs.TIME_RUN = START_DATE;
            long startTimeMillis = Utils.sdfFile.parse(START_DATE).getTime();
            long endTimeMillis = startTimeMillis + (DAYS_TO_TEST * Utils.TIME_DAY);

            LOG.info("=======================================================");
            LOG.info("===       BENCHMARK: DB vs OLD CACHE vs NEW CACHE   ===");
            LOG.info("===       Range: {} days | Start: {}      ===", DAYS_TO_TEST, START_DATE);
            LOG.info("=======================================================\n");

            // ---------------------------------------------------------
            // PHASE 0: WARMUP (Nạp dữ liệu vào RAM trước để công bằng cho 2 test sau)
            // ---------------------------------------------------------
            LOG.info("🔄 PHASE 0: WARMUP (Loading Data from Disk to RAM Store)...");
            long tStartWarmup = System.currentTimeMillis();
            for (int i = 0; i < DAYS_TO_TEST; i++) {
                long current = startTimeMillis + (i * Utils.TIME_DAY);
                // Gọi hàm này để nén dữ liệu vào RAM_STORE của HPOSmartCache
                HPOSmartCache.getData(current);
            }
            LOG.info("✅ Warmup Done. Data is locked in RAM.\n");

            cleanMemory();

            // ---------------------------------------------------------
            // TEST 1: DIRECT AEROSPIKE/DISK (Mô phỏng chưa có Cache)
            // ---------------------------------------------------------
            LOG.info("💾 TEST 1: DIRECT AEROSPIKE (No Cache, IO Heavy)");
            long tStartDB = System.currentTimeMillis();
            int countDB = 0;

            for (int i = -DAYS_TO_TEST; i < 0; i++) {
                long current = startTimeMillis + (i * Utils.TIME_DAY);
                // Gọi trực tiếp DataManager (Bỏ qua lớp Cache)
                // Hàm này sẽ phải đọc từ ổ cứng/DB và giải nén Snappy lại từ đầu
                TreeMap<Long, Map<String, KlineObjectSimple>> data =
                        DataManagerAerospikeFloatSim.readDataFromAerospike1M(current);
                if (data != null) countDB += data.size();
                // System.out.print("."); // Bỏ comment nếu muốn thấy nó chạy
            }

            long durationDB = System.currentTimeMillis() - tStartDB;
            LOG.info("   👉 Time: {} ms (Avg: {} ms/day)", durationDB, durationDB / DAYS_TO_TEST);

            cleanMemory();

            // ---------------------------------------------------------
            // TEST 2: OLD RAM CACHE (Full TreeMap Reconstruction)
            // ---------------------------------------------------------
            LOG.info("🐢 TEST 2: OLD RAM METHOD (getData - Reconstruct Full Day)");
            long tStartOld = System.currentTimeMillis();
            int countOld = 0;

            for (int i = 0; i < DAYS_TO_TEST; i++) {
                long current = startTimeMillis + (i * Utils.TIME_DAY);
                // Gọi qua Cache, nhưng lấy toàn bộ Map 1440 phút
                TreeMap<Long, Map<String, KlineObjectSimple>> data = HPOSmartCache.getData(current);
                if (data != null) countOld += data.size();
            }

            long durationOld = System.currentTimeMillis() - tStartOld;
            LOG.info("   👉 Time: {} ms (Avg: {} ms/day)", durationOld, durationOld / DAYS_TO_TEST);

            cleanMemory();

            // ---------------------------------------------------------
            // TEST 3: NEW RAM CACHE (Lazy Loading Per Minute)
            // ---------------------------------------------------------
            LOG.info("🚀 TEST 3: NEW RAM METHOD (getDataAtMinute - Simulation Loop)");
            long tStartNew = System.currentTimeMillis();
            int countNew = 0;

            // Giả lập vòng lặp Simulator thực tế: Duyệt từng phút một
            long cursor = startTimeMillis;
            while (cursor < endTimeMillis) {
                // Chỉ lấy đúng dữ liệu phút đó
                Map<String, KlineObjectSimple> minData = HPOSmartCache.getDataAtMinute(cursor);
                if (minData != null) countNew += minData.size();
                cursor += Utils.TIME_MINUTE;
            }

            long durationNew = System.currentTimeMillis() - tStartNew;
            LOG.info("   👉 Time: {} ms (Avg: {} ms/day)", durationNew, durationNew / DAYS_TO_TEST);


            // ---------------------------------------------------------
            // TỔNG KẾT
            // ---------------------------------------------------------
            LOG.info("\n=======================================================");
            LOG.info("===                  FINAL REPORT                   ===");
            LOG.info("=======================================================");
            LOG.info("1. Direct DB (Disk IO) : {} ms  (Baseline)", durationDB);
            LOG.info("2. Old Cache (TreeMap) : {} ms  ({}x faster than DB)",
                    durationOld, String.format("%.1f", (float) durationDB / durationOld));
            LOG.info("3. New Cache (Per Min) : {} ms  ({}x faster than DB)",
                    durationNew, String.format("%.1f", (float) durationDB / durationNew));

            LOG.info("\n⚡ New Method vs Old Cache: {}x FASTER",
                    String.format("%.1f", (float) durationOld / durationNew));
            LOG.info("=======================================================");

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void cleanMemory() {
        System.gc();
        try {
            Thread.sleep(1000);
        } catch (InterruptedException e) {
        }
    }
}