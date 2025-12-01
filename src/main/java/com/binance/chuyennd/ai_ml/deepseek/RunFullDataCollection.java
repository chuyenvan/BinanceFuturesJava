package com.binance.chuyennd.ai_ml.deepseek;

import com.binance.chuyennd.aerospike.DataManagerAerospike;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.chuyennd.research.FundingFeeManager;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.io.File;
import java.util.*;

public class RunFullDataCollection {
    private static final Logger LOG = LoggerFactory.getLogger(RunFullDataCollection.class);

    public static void main(String[] args) {
        try {
            // 1. Init Funding Fee (Bắt buộc)
            FundingFeeManager.getInstance();

            // 2. Chạy thu thập tuần tự
            new RunFullDataCollection().runSequentialCollection();

        } catch (Exception e) {
            LOG.error("Main error", e);
        }
    }

    public void runSequentialCollection() throws Exception {
        // Lưu vào thư mục Sequential để phân biệt
        EnhancedTrainingDataCollectionManager dataManager =
                new EnhancedTrainingDataCollectionManager("storage/training_data_big_sequential");

        LOG.info("🚀 LOADING MARKET RATES...");
        TreeMap<Long, MarketRateChange> time2Rate = loadMarketRateData();

        long currentTime = Utils.sdfFile.parse("20210101").getTime();
        long endTime = System.currentTimeMillis();

        LOG.info("⏳ STARTING SEQUENTIAL COLLECTION from {} to {}",
                Utils.normalizeDateYYYYMMDD(currentTime),
                Utils.normalizeDateYYYYMMDD(endTime));

        int processedDays = 0;
        int totalSamples = 0;

        // VÒNG LẶP CHÍNH: CHẠY TỪNG NGÀY MỘT
        while (currentTime <= endTime) {
            try {
                // 1. Load dữ liệu hôm nay và ngày mai
                TreeMap<Long, Map<String, KlineObjectSimple>> todayData =
                        DataManagerAerospike.readDataFromAerospike1M(currentTime);
                TreeMap<Long, Map<String, KlineObjectSimple>> tomorrowData =
                        DataManagerAerospike.readDataFromAerospike1M(currentTime + Utils.TIME_DAY);

                // 2. Gộp vào Lookup Data (để tính Label tương lai 24h)
                TreeMap<Long, Map<String, KlineObjectSimple>> lookupData = new TreeMap<>();
                if (todayData != null) lookupData.putAll(todayData);
                if (tomorrowData != null) lookupData.putAll(tomorrowData);

                // 3. Xử lý (Nếu có dữ liệu)
                if (todayData != null && !todayData.isEmpty()) {
                    processDailyData(todayData, lookupData, time2Rate, dataManager);
                }

                // 4. Export định kỳ (Mỗi 5 ngày export 1 lần để giải phóng RAM)
                processedDays++;
                if (processedDays % 5 == 0) {
                    dataManager.exportCollectedData();
                    int currentTotal = dataManager.getCollectedCount();
                    LOG.info("✅ Processed {} days. Cumulative Samples: {}", processedDays, currentTotal);
                }

            } catch (Exception e) {
                LOG.warn("⚠️ Error processing day {}: {}", Utils.normalizeDateYYYYMMDD(currentTime), e.getMessage());
            }

            // Tăng thời gian lên 1 ngày
            currentTime += Utils.TIME_DAY;
        }

        // Export nốt phần còn lại cuối cùng
        dataManager.exportCollectedData();
        LOG.info("🎉 COMPLETED! Total Days: {} | Total Samples: {}", processedDays, dataManager.getCollectedCount());
    }

    private void processDailyData(TreeMap<Long, Map<String, KlineObjectSimple>> todayData,
                                  TreeMap<Long, Map<String, KlineObjectSimple>> lookupData,
                                  TreeMap<Long, MarketRateChange> rateData,
                                  EnhancedTrainingDataCollectionManager dataManager) {

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : todayData.entrySet()) {
            Long timestamp = entry.getKey();

            // 🔥 LOGIC LỌC LỎNG (RELAXED) - LẤY NHIỀU DỮ LIỆU
            // Giảm > 0.1% và Rổ > 3 coin là lấy
            List<String> targetBasket = findPotentialLosersRelaxed(lookupData, timestamp);

            if (targetBasket.size() < 3) continue;

            // Tính toán Labels (Targets)
            double ret15M = calculateBasketMaxPotential(lookupData, timestamp, 15, targetBasket);
            double ret1H = calculateBasketMaxPotential(lookupData, timestamp, 60, targetBasket);
            double ret4H = calculateBasketMaxPotential(lookupData, timestamp, 240, targetBasket);
            double ret24H = calculateBasketMaxPotential(lookupData, timestamp, 1440, targetBasket);

            double maxDD4H = calculateBasketMaxDrawdown(lookupData, timestamp, 240, targetBasket);
            double maxDD24H = calculateBasketMaxDrawdown(lookupData, timestamp, 1440, targetBasket);

            MarketRateChange rate = (rateData != null) ? rateData.get(timestamp) : null;

            // Truyền vào Manager (Manager sẽ gọi Feature Extractor)
            // Vì chạy tuần tự, Feature Extractor sẽ tự động tích lũy History liên tục
            dataManager.processMarketData(timestamp, entry.getValue(), rate,
                    targetBasket, ret15M, ret1H, ret4H, ret24H, maxDD4H, maxDD24H);
        }
    }

    // 🔥 HÀM LỌC: LẤY NHIỀU DỮ LIỆU (RELAXED)
    private List<String> findPotentialLosersRelaxed(TreeMap<Long, Map<String, KlineObjectSimple>> dailyData, Long currentTimestamp) {
        Long startTime = currentTimestamp - (15 * 60 * 1000L);
        Map<Long, Map<String, KlineObjectSimple>> recentData = dailyData.subMap(startTime, true, currentTimestamp, true);
        if (recentData.isEmpty()) return new ArrayList<>();

        Map<String, KlineObjectSimple> currentPrices = dailyData.get(currentTimestamp);
        Map<String, Double> maxPrices15m = new HashMap<>();

        for (Map<String, KlineObjectSimple> minuteData : recentData.values()) {
            for (Map.Entry<String, KlineObjectSimple> entry : minuteData.entrySet()) {
                String symbol = entry.getKey();
                double high = entry.getValue().maxPrice;
                if (!maxPrices15m.containsKey(symbol) || high > maxPrices15m.get(symbol)) {
                    maxPrices15m.put(symbol, high);
                }
            }
        }

        List<Map.Entry<String, Double>> drops = new ArrayList<>();
        for (String symbol : currentPrices.keySet()) {
            KlineObjectSimple currentKline = currentPrices.get(symbol);
            // Vẫn lọc volume rác < 50k để đảm bảo thanh khoản
            if (currentKline.totalUsdt < 50000) continue;

            if (maxPrices15m.containsKey(symbol)) {
                double peakPrice = maxPrices15m.get(symbol);
                double currentPrice = currentKline.priceClose;

                if (peakPrice > 0) {
                    double dropFromPeak = (currentPrice - peakPrice) / peakPrice;
                    // Giảm nhẹ > 0.1% là lấy (để bắt cả sideway/scalp nhỏ)
                    if (dropFromPeak < -0.001) {
                        drops.add(new AbstractMap.SimpleEntry<>(symbol, dropFromPeak));
                    }
                }
            }
        }

        drops.sort(Map.Entry.comparingByValue());
        List<String> result = new ArrayList<>();
        int limit = Math.min(drops.size(), 60); // Lấy top 60
        for (int i = 0; i < limit; i++) result.add(drops.get(i).getKey());
        return result;
    }

    // --- CÁC HÀM TÍNH TOÁN LABEL (Giữ nguyên) ---
    private double calculateBasketMaxPotential(TreeMap<Long, Map<String, KlineObjectSimple>> data, Long currentTs, int minutes, List<String> basket) {
        Long endTime = currentTs + (minutes * 60000L);
        Map<String, KlineObjectSimple> currentSnapshot = data.get(currentTs);
        if (currentSnapshot == null) return 0.0;
        Map<String, Double> entryPrices = new HashMap<>();
        for (String sym : basket) if (currentSnapshot.containsKey(sym)) entryPrices.put(sym, currentSnapshot.get(sym).priceClose);
        NavigableMap<Long, Map<String, KlineObjectSimple>> futureRange = data.subMap(currentTs, false, endTime, true);
        Map<String, Double> maxReturns = new HashMap<>();
        for (String sym : basket) maxReturns.put(sym, -999.0);
        for (Map<String, KlineObjectSimple> minuteData : futureRange.values()) {
            for (String sym : basket) {
                if (minuteData.containsKey(sym) && entryPrices.containsKey(sym)) {
                    double entry = entryPrices.get(sym);
                    double currentHigh = minuteData.get(sym).maxPrice;
                    if (entry > 0) {
                        double potentialReturn = (currentHigh - entry) / entry;
                        if (potentialReturn > maxReturns.get(sym)) maxReturns.put(sym, potentialReturn);
                    }
                }
            }
        }
        double sumMaxReturn = 0; int count = 0;
        for (String sym : basket) { double ret = maxReturns.get(sym); if (ret != -999.0) { sumMaxReturn += ret; count++; } }
        return (count > 0) ? sumMaxReturn / count : 0.0;
    }

    private double calculateBasketMaxDrawdown(TreeMap<Long, Map<String, KlineObjectSimple>> data, Long currentTs, int minutes, List<String> basket) {
        Long endTime = currentTs + (minutes * 60000L);
        NavigableMap<Long, Map<String, KlineObjectSimple>> range = data.subMap(currentTs, false, endTime, true);

        Map<String, Double> entryPrices = new HashMap<>();
        Map<String, KlineObjectSimple> currentParams = data.get(currentTs);

        if (currentParams == null) return 0.0;

        // Lấy giá Entry
        for(String sym : basket) {
            if(currentParams.containsKey(sym)) {
                double p = currentParams.get(sym).priceClose;
                if (p > 0.0000001) entryPrices.put(sym, p);
            }
        }

        if (entryPrices.isEmpty()) return 0.0;

        double worstBasketDrawdown = 0.0; // Mặc định là 0

        // Quét từng phút để xem tài khoản (Basket) bị âm nặng nhất vào lúc nào
        for (Map<String, KlineObjectSimple> minuteData : range.values()) {
            double currentMinuteSumPL = 0; // Tổng PnL của các coin trong phút này
            int count = 0;

            for (String sym : entryPrices.keySet()) {
                if (minuteData.containsKey(sym) && entryPrices.containsKey(sym)) {
                    double low = minuteData.get(sym).minPrice; // Lấy râu nến thấp nhất
                    double entry = entryPrices.get(sym);

                    if (low > 0 && entry > 0) {
                        double dd = (low - entry) / entry;

                        // Cap ở -100% (Không thể mất quá số vốn)
                        if (dd < -1.0) dd = -1.0;
                        // Loại bỏ nhiễu dương vô lý nếu có
                        if (dd > 10.0) dd = 0.0;

                        currentMinuteSumPL += dd;
                        count++;
                    }
                }
            }

            // 🔥 QUAN TRỌNG: Phải chia trung bình cho số coin có dữ liệu trong phút đó
            if (count > 0) {
                double currentMinuteAvgPL = currentMinuteSumPL / count; // <-- ĐÂY LÀ CHỖ THIẾU TRƯỚC ĐÓ

                // Nếu phút này tài khoản sập sâu hơn kỷ lục trước đó -> Cập nhật
                if (currentMinuteAvgPL < worstBasketDrawdown) {
                    worstBasketDrawdown = currentMinuteAvgPL;
                }
            }
        }

        // Sanity Check cuối cùng
        if (worstBasketDrawdown < -1.0) return -1.0;

        return worstBasketDrawdown;
    }
    private TreeMap<Long, MarketRateChange> loadMarketRateData() throws Exception {
        if (!new File(Configs.FILE_MARKET_RATE_CHANGE).exists()) return new TreeMap<>();
        return (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
    }
}