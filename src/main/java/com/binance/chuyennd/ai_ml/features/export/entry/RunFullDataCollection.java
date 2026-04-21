package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class RunFullDataCollection {
    private static final Logger LOG = LoggerFactory.getLogger(RunFullDataCollection.class);

    public static void main(String[] args) {
        try {
            new RunFullDataCollection().runSequentialCollection();
        } catch (Exception e) {
            LOG.error("Main error", e);
        }
    }

    public void runSequentialCollection() throws Exception {
        EnhancedTrainingDataCollectionManager dataManager =
                new EnhancedTrainingDataCollectionManager("storage/training_data_big_sequential");

        LOG.info("🚀 LOADING MARKET RATES...");
        TreeMap<Long, MarketDataObject> time2Rate = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();

        long currentTime = Utils.sdfFile.parse("20210101").getTime();
        long endTime = System.currentTimeMillis();

        LOG.info("⏳ STARTING SEQUENTIAL COLLECTION from {} to {}",
                Utils.normalizeDateYYYYMMDD(currentTime),
                Utils.normalizeDateYYYYMMDD(endTime));

        int processedDays = 0;

        while (currentTime <= endTime) {
            try {
                TreeMap<Long, Map<String, KlineObjectSimple>> todayData =
                        DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);
                TreeMap<Long, Map<String, KlineObjectSimple>> tomorrowData =
                        DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime + Utils.TIME_DAY);

                TreeMap<Long, Map<String, KlineObjectSimple>> lookupData = new TreeMap<>();
                if (todayData != null) lookupData.putAll(todayData);
                if (tomorrowData != null) lookupData.putAll(tomorrowData);

                if (todayData != null && !todayData.isEmpty()) {
                    processDailyData(todayData, lookupData, time2Rate, dataManager);
                }

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
        LOG.info("🎉 COMPLETED!");
    }

    private void processDailyData(TreeMap<Long, Map<String, KlineObjectSimple>> todayData,
                                  TreeMap<Long, Map<String, KlineObjectSimple>> lookupData,
                                  TreeMap<Long, MarketDataObject> rateData,
                                  EnhancedTrainingDataCollectionManager dataManager) {

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : todayData.entrySet()) {
            Long timestamp = entry.getKey();
            Map<String, KlineObjectSimple> currentMarketSnapshot = entry.getValue();

            // 🔥 THAY ĐỔI LỚN TẠI ĐÂY:
            // Gọi Manager để (1) Update History vào Extractor và (2) Lấy Basket từ logic bên trong Extractor
            List<String> targetBasket = new ArrayList<>(currentMarketSnapshot.keySet());

            // Tính toán Labels (Targets) dựa trên Basket vừa lấy được
            float ret15M = calculateBasketMaxPotential(lookupData, timestamp, 15, targetBasket);
            float ret1H = calculateBasketMaxPotential(lookupData, timestamp, 60, targetBasket);
            float ret4H = calculateBasketMaxPotential(lookupData, timestamp, 240, targetBasket);
            float ret24H = calculateBasketMaxPotential(lookupData, timestamp, 1440, targetBasket);

            float maxDD4H = calculateBasketMaxDrawdown(lookupData, timestamp, 240, targetBasket);
            float maxDD24H = calculateBasketMaxDrawdown(lookupData, timestamp, 1440, targetBasket);

            MarketDataObject rate = (rateData != null) ? rateData.get(timestamp) : null;

            // Truyền lại basket vào processMarketData (Extractor sẽ dùng lại, không cần tính lại)
            dataManager.processMarketData(timestamp, currentMarketSnapshot, rate,
                    targetBasket, ret15M, ret1H, ret4H, ret24H, maxDD4H, maxDD24H);
        }
    }
    private float calculateBasketMaxPotential(TreeMap<Long, Map<String, KlineObjectSimple>> data, Long currentTs,
                                              int minutes, List<String> basket) {
        Long endTime = currentTs + (minutes * 60000L);
        Map<String, KlineObjectSimple> currentSnapshot = data.get(currentTs);
        if (currentSnapshot == null) return 0.0f;
        Map<String, Float> entryPrices = new HashMap<>();
        for (String sym : basket)
            if (currentSnapshot.containsKey(sym)) entryPrices.put(sym, currentSnapshot.get(sym).priceClose);
        NavigableMap<Long, Map<String, KlineObjectSimple>> futureRange = data.subMap(currentTs, false, endTime, true);
        Map<String, Float> maxReturns = new HashMap<>();
        for (String sym : basket) maxReturns.put(sym, -999.0f);
        for (Map<String, KlineObjectSimple> minuteData : futureRange.values()) {
            for (String sym : basket) {
                if (minuteData.containsKey(sym) && entryPrices.containsKey(sym)) {
                    float entry = entryPrices.get(sym);
                    float currentHigh = minuteData.get(sym).maxPrice;
                    if (entry > 0) {
                        float potentialReturn = (currentHigh - entry) / entry;
                        if (potentialReturn > maxReturns.get(sym)) maxReturns.put(sym, potentialReturn);
                    }
                }
            }
        }
        float sumMaxReturn = 0;
        int count = 0;
        for (String sym : basket) {
            float ret = maxReturns.get(sym);
            if (ret != -999.0) {
                sumMaxReturn += ret;
                count++;
            }
        }
        return (count > 0) ? sumMaxReturn / count : 0.0f;
    }

    private float calculateBasketMaxDrawdown(TreeMap<Long, Map<String, KlineObjectSimple>> data, Long currentTs, int minutes, List<String> basket) {
        Long endTime = currentTs + (minutes * 60000L);
        NavigableMap<Long, Map<String, KlineObjectSimple>> range = data.subMap(currentTs, false, endTime, true);
        Map<String, Float> entryPrices = new HashMap<>();
        Map<String, KlineObjectSimple> currentParams = data.get(currentTs);
        if (currentParams == null) return 0.0f;
        for (String sym : basket) {
            if (currentParams.containsKey(sym)) {
                float p = currentParams.get(sym).priceClose;
                if (p > 0.0000001) entryPrices.put(sym, p);
            }
        }
        if (entryPrices.isEmpty()) return 0.0f;
        float worstBasketDrawdown = 0.0f;
        for (Map<String, KlineObjectSimple> minuteData : range.values()) {
            float currentMinuteSumPL = 0;
            int count = 0;
            for (String sym : entryPrices.keySet()) {
                if (minuteData.containsKey(sym) && entryPrices.containsKey(sym)) {
                    float low = minuteData.get(sym).minPrice;
                    float entry = entryPrices.get(sym);
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
        if (worstBasketDrawdown < -1.0) return -1.0f;
        return worstBasketDrawdown;
    }

}