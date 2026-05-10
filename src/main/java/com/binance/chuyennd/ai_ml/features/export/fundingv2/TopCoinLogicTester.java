package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class TopCoinLogicTester {
    private static final Logger LOG = LoggerFactory.getLogger(TopCoinLogicTester.class);

    public static void main(String[] args) throws Exception {
        String targetDay = "20260104";
        long targetTs = Utils.sdfFile.parse(targetDay).getTime();

        // Mốc test cụ thể: 08:30 đến 08:39 của ngày 04/01/2026
        long startTimeBlock = targetTs + (510 * 60000L); // 510 phút = 08:30
        List<Long> testMinutes = new ArrayList<>();
        for (int i = 0; i < 10; i++) testMinutes.add(startTimeBlock + (i * 60000L));

        LOG.info("🚀 BẮT ĐẦU TEST LOGIC TOP COIN TẠI 10 PHÚT: {} ĐẾN {}",
                Utils.normalizeDateYYYYMMDDHHmm(testMinutes.get(0)),
                Utils.normalizeDateYYYYMMDDHHmm(testMinutes.get(9)));

        // =========================================================
        // KỊCH BẢN 1: MÔ PHỎNG LUỒNG EXPORT (Warmup từ 29/12 năm trước)
        // =========================================================
        long exportWarmupStart = Utils.sdfFile.parse("20251229-0000").getTime();

        LOG.info("\n=========================================================");
        LOG.info("🛠️ CHẠY KỊCH BẢN 1: EXPORT (Warmup từ {})", Utils.normalizeDateYYYYMMDDHHmm(exportWarmupStart));
        resetSystemCache();
        Map<Long, List<String>> exportTopCoinsMap = simulateAndGetTopCoins(exportWarmupStart, testMinutes);

        // =========================================================
        // KỊCH BẢN 2: MÔ PHỎNG LUỒNG VALIDATOR (Warmup lùi đúng 48 tiếng)
        // =========================================================
        long validatorWarmupStart = Utils.sdfFile.parse("20251230-0000").getTime();

        LOG.info("\n=========================================================");
        LOG.info("🛠️ CHẠY KỊCH BẢN 2: VALIDATOR (Warmup từ {})", Utils.normalizeDateYYYYMMDDHHmm(validatorWarmupStart));
        resetSystemCache();
        Map<Long, List<String>> validatorTopCoinsMap = simulateAndGetTopCoins(validatorWarmupStart, testMinutes);

        // =========================================================
        // SO SÁNH KẾT QUẢ
        // =========================================================
        LOG.info("\n=========================================================");
        LOG.info("⚔️ KẾT QUẢ ĐỐI ĐẦU 2 KỊCH BẢN TẠI TỪNG PHÚT");
        LOG.info("=========================================================");

        for (Long time : testMinutes) {
            List<String> exportList = exportTopCoinsMap.get(time);
            List<String> valList = validatorTopCoinsMap.get(time);

            if (exportList == null || valList == null || exportList.isEmpty() || valList.isEmpty()) {
                LOG.error("❌ Mốc {}: Thiếu dữ liệu (Hoặc danh sách rỗng) để so sánh!", Utils.normalizeDateYYYYMMDDHHmm(time));
                continue;
            }

            Set<String> setExport = new HashSet<>(exportList);
            Set<String> setVal = new HashSet<>(valList);

            if (setExport.equals(setVal)) {
                LOG.info("✅ Mốc {}: KHỚP 100% ({} symbols)", Utils.normalizeDateYYYYMMDDHHmm(time), exportList.size());
            } else {
                LOG.error("❌ Mốc {}: LỆCH DANH SÁCH TOP COIN!", Utils.normalizeDateYYYYMMDDHHmm(time));

                Set<String> inExportOnly = new HashSet<>(setExport); inExportOnly.removeAll(setVal);
                Set<String> inValOnly = new HashSet<>(setVal); inValOnly.removeAll(setExport);

                LOG.error("   > Lọt Top Export nhưng rớt khỏi Validator: {}", inExportOnly);
                LOG.error("   > Lọt Top Validator nhưng rớt khỏi Export: {}", inValOnly);
            }
        }

        System.exit(0);
    }

    /**
     * Dọn dẹp sạch sẽ bộ nhớ giữa 2 lần test
     */
    private static void resetSystemCache() {
        CoinRankManager.getInstance().resetCache();
        HistoryManager.getInstance().clearAll(); // Phải clear cả HistoryManager
    }

    /**
     * Hàm chạy giả lập tiến trình đọc DB và nạp vào Extractor -> HistoryManager -> CoinRankManager
     */
    private static Map<Long, List<String>> simulateAndGetTopCoins(long startTs, List<Long> testMinutes) {
        Map<Long, List<String>> result = new HashMap<>();
        long maxTestTime = Collections.max(testMinutes);
        long currentTime = startTs;

        // Khởi tạo cái máy xay thịt
        FundingFeatureExtractorV2 extractor = new FundingFeatureExtractorV2();

        while (currentTime <= maxTestTime) {
            int minutesToRead = 1440;
            if (currentTime + minutesToRead * Utils.TIME_MINUTE > maxTestTime) {
                minutesToRead = (int) ((maxTestTime - currentTime) / Utils.TIME_MINUTE) + 1;
            }

            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, minutesToRead);

            if (time2Tickers == null || time2Tickers.isEmpty()) {
                currentTime += minutesToRead * Utils.TIME_MINUTE;
                continue;
            }

            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                long time = entry.getKey();
                Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();

                // 1. Cập nhật Market History (Bơm data vào HistoryManager)
                extractor.updateMarketHistory(symbol2Ticker);

                // Lấy snapshot nếu đúng giờ test
                if (testMinutes.contains(time)) {
                    // 2. Lấy Top Coin (Lúc này nó sẽ móc data từ HistoryManager ra xài)
                    List<String> topCoins = CoinRankManager.getInstance().getTopCoin(time);
                    result.put(time, new ArrayList<>(topCoins));
                }
            }

            currentTime = time2Tickers.lastKey() + Utils.TIME_MINUTE;

            if (currentTime % (1440 * 60000L) == 0) {
                LOG.info("   ... Đã đọc DB và warmup qua ngày: {}", Utils.normalizeDateYYYYMMDDHHmm(currentTime));
            }
        }
        return result;
    }
}