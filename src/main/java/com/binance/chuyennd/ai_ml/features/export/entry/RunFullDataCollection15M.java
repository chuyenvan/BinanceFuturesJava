package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager15M;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager15M;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class RunFullDataCollection15M {
    private static final Logger LOG = LoggerFactory.getLogger(RunFullDataCollection15M.class);

    public static void main(String[] args) {
        try {
            // Nhớ khởi tạo Mapper!
            com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper.getInstance().init();
            new RunFullDataCollection15M().runCollection();
        } catch (Exception e) {
            LOG.error("Main error", e);
        }
    }

    public void runCollection() throws Exception {
        EnhancedTrainingDataCollectionManager15M dataManager =
                new EnhancedTrainingDataCollectionManager15M("storage/training_data_15m");

        long currentTime = Utils.sdfFile.parse("20210105").getTime();
        long endTime = System.currentTimeMillis() - 2 * Utils.TIME_DAY;

        LOG.info("⏳ BẮT ĐẦU THU THẬP DATA TRAIN 15M TỪ {} ĐẾN {}",
                Utils.normalizeDateYYYYMMDD(currentTime), Utils.normalizeDateYYYYMMDD(endTime));

        int processedDays = 0;

        // 🔥 Đã chuyển sang MAP<SHORT, KLINE>
        TreeMap<Long, Map<Short, KlineObjectSimple>> rollingWindow = new TreeMap<>();
        ComprehensiveMarketFeatureExtractor15M featureExtractor = new ComprehensiveMarketFeatureExtractor15M();

        rollingWindow.putAll(DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTime - Utils.TIME_DAY, 96));
        rollingWindow.putAll(DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTime, 96));

        while (currentTime <= endTime) {
            try {
                rollingWindow.putAll(DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTime + Utils.TIME_DAY, 96));
                rollingWindow.putAll(DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTime + 2 * Utils.TIME_DAY, 96));

                for (long ts = currentTime; ts < currentTime + Utils.TIME_DAY; ts += 15 * 60000L) {
                    Map<Short, KlineObjectSimple> currentSnapshot = rollingWindow.get(ts);
                    if (currentSnapshot == null) continue;

                    // 1. Bơm Data vào History (Toàn Short)
                    HistoryManager15M.getInstance().updateHistory(currentSnapshot);

                    // 2. Lấy Rổ Coin (Toàn Short)
                    List<Short> targetBasket = CoinRankManager15M.getInstance().getTopCoinShort(ts);

                    // 3. Đọc MDO 15M
                    MarketDataObject15M rate = DataManagerAerospikeFloatSim.getMarketData15MAtTime(ts);

                    // 4. Tính Lãi/Lỗ Tương lai
                    float ret4H = calculateBasketMaxPotential(rollingWindow, ts, 16, targetBasket);
                    float ret24H = calculateBasketMaxPotential(rollingWindow, ts, 96, targetBasket);
                    float maxDD12H = calculateBasketMaxDrawdown(rollingWindow, ts, 48, targetBasket);

                    // 5. Gửi lên Manager (Manager bác sửa tham số basket thành List<Short> là xong nhé)
                    dataManager.processMarketData(ts, rollingWindow, rate, targetBasket, ret4H, ret24H, maxDD12H);
                }

                long staleDay = currentTime - 2 * Utils.TIME_DAY;
                rollingWindow.headMap(staleDay, true).clear();

                processedDays++;
                if (processedDays % 5 == 0) {
                    dataManager.exportCollectedData();
                    LOG.info("✅ Processed {} days. Cumulative Samples: {}", processedDays, dataManager.getCollectedCount());
                }

            } catch (Exception e) {
                LOG.warn("⚠️ Error processing day {}: {}", Utils.normalizeDateYYYYMMDD(currentTime), e.getMessage());
            }
            currentTime += Utils.TIME_DAY;
        }

        dataManager.exportCollectedData();
        LOG.info("🎉 HOÀN TẤT THU THẬP DỮ LIỆU!");
    }

    // 🔥 Các hàm tính Label ở dưới đổi String sym -> Short symId
    private float calculateBasketMaxPotential(TreeMap<Long, Map<Short, KlineObjectSimple>> data, Long currentTs,
                                              int blockCount, List<Short> basket) {
        Long endTime = currentTs + (blockCount * 15 * 60000L);
        Map<Short, KlineObjectSimple> currentSnapshot = data.get(currentTs);
        if (currentSnapshot == null) return 0.0f;

        Map<Short, Float> entryPrices = new HashMap<>();
        for (Short symId : basket)
            if (currentSnapshot.containsKey(symId)) entryPrices.put(symId, currentSnapshot.get(symId).priceClose);

        NavigableMap<Long, Map<Short, KlineObjectSimple>> futureRange = data.subMap(currentTs, false, endTime, true);
        Map<Short, Float> maxReturns = new HashMap<>();
        for (Short symId : basket) maxReturns.put(symId, -999.0f);

        for (Map<Short, KlineObjectSimple> minuteData : futureRange.values()) {
            for (Short symId : basket) {
                if (minuteData.containsKey(symId) && entryPrices.containsKey(symId)) {
                    float entry = entryPrices.get(symId);
                    float currentHigh = minuteData.get(symId).maxPrice;
                    if (entry > 0) {
                        float potentialReturn = (currentHigh - entry) / entry;
                        if (potentialReturn > maxReturns.get(symId)) maxReturns.put(symId, potentialReturn);
                    }
                }
            }
        }
        float sumMaxReturn = 0; int count = 0;
        for (Short symId : basket) {
            float ret = maxReturns.get(symId);
            if (ret != -999.0f) { sumMaxReturn += ret; count++; }
        }
        return (count > 0) ? sumMaxReturn / count : 0.0f;
    }

    private float calculateBasketMaxDrawdown(TreeMap<Long, Map<Short, KlineObjectSimple>> data, Long currentTs,
                                             int blockCount, List<Short> basket) {
        Long endTime = currentTs + (blockCount * 15 * 60000L);
        NavigableMap<Long, Map<Short, KlineObjectSimple>> range = data.subMap(currentTs, false, endTime, true);

        Map<Short, Float> entryPrices = new HashMap<>();
        Map<Short, KlineObjectSimple> currentParams = data.get(currentTs);
        if (currentParams == null) return 0.0f;
        for (Short symId : basket) {
            if (currentParams.containsKey(symId)) {
                float p = currentParams.get(symId).priceClose;
                if (p > 0) entryPrices.put(symId, p);
            }
        }
        if (entryPrices.isEmpty()) return 0.0f;
        float worstBasketDrawdown = 0.0f;
        for (Map<Short, KlineObjectSimple> minuteData : range.values()) {
            float currentMinuteSumPL = 0;
            int count = 0;
            for (Short symId : entryPrices.keySet()) {
                if (minuteData.containsKey(symId) && entryPrices.containsKey(symId)) {
                    float low = minuteData.get(symId).minPrice;
                    float entry = entryPrices.get(symId);
                    if (low > 0 && entry > 0) {
                        float dd = (low - entry) / entry;
                        if (dd < -1.0) dd = -1.0f;
                        if (dd > 10.0) dd = 0.0f;
                        currentMinuteSumPL += dd;
                        count++;
                    }
                }
            }
            if (count > 0) {
                float currentMinuteAvgPL = currentMinuteSumPL / count;
                if (currentMinuteAvgPL < worstBasketDrawdown) worstBasketDrawdown = currentMinuteAvgPL;
            }
        }
        return worstBasketDrawdown < -1.0f ? -1.0f : worstBasketDrawdown;
    }
}