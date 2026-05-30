package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager15M;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class RunFullDataCollection15M {
    private static final Logger LOG = LoggerFactory.getLogger(RunFullDataCollection15M.class);

    public static void main(String[] args) {
        try {
            SimpleSymbolMapper.getInstance().init();
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
        TreeMap<Long, Map<Short, KlineObjectSimple>> rollingWindow = new TreeMap<>();

        rollingWindow.putAll(DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTime - Utils.TIME_DAY, 96));
        rollingWindow.putAll(DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTime, 96));

        while (currentTime <= endTime) {
            try {
                rollingWindow.putAll(DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTime + Utils.TIME_DAY, 96));
                rollingWindow.putAll(DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTime + 2 * Utils.TIME_DAY, 96));

                for (long ts = currentTime; ts < currentTime + Utils.TIME_DAY; ts += 15 * 60000L) {
                    Map<Short, KlineObjectSimple> currentSnapshot = rollingWindow.get(ts);
                    if (currentSnapshot == null) continue;

                    HistoryManager15M.getInstance().updateHistory(currentSnapshot);
                    List<Short> targetBasket = HistoryManager15M.getInstance().findPotentialLosersShort(ts);
                    MarketDataObject15M rate = DataManagerAerospikeFloatSim.getMarketData15MAtTime(ts);

                    // 🔥 4. TÍNH LÃI/LỖ THỰC CHIẾN (Block 15m: 4 = 1H, 16 = 4H)
                    float ret1H = calculateBasketMaxPotential(rollingWindow, ts, 4, targetBasket);
                    float ret4H = calculateBasketMaxPotential(rollingWindow, ts, 16, targetBasket);
                    float maxDD4H = calculateBasketMaxDrawdown(rollingWindow, ts, 16, targetBasket);

                    // 5. Gửi lên Manager
                    dataManager.processMarketData(ts, rollingWindow, rate, targetBasket, ret1H, ret4H, maxDD4H);
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

    /**
     * 🔥 ĐÃ CHỮA BỆNH "GOD MODE": Tính Lãi/Lỗ của CẢ RỔ tại cùng 1 nến tương lai.
     * Sau đó mới tìm Nến Tương Lai mang lại Lãi Cả Rổ cao nhất.
     */
    private float calculateBasketMaxPotential(TreeMap<Long, Map<Short, KlineObjectSimple>> data, Long currentTs,
                                              int blockCount, List<Short> basket) {
        Long endTime = currentTs + (blockCount * 15 * 60000L);
        NavigableMap<Long, Map<Short, KlineObjectSimple>> futureRange = data.subMap(currentTs, false, endTime, true);

        Map<Short, Float> entryPrices = new HashMap<>();
        Map<Short, KlineObjectSimple> currentSnapshot = data.get(currentTs);
        if (currentSnapshot == null) return 0.0f;

        for (Short symId : basket) {
            if (currentSnapshot.containsKey(symId)) {
                float p = currentSnapshot.get(symId).priceClose;
                if (p > 0) entryPrices.put(symId, p);
            }
        }
        if (entryPrices.isEmpty()) return 0.0f;

        float maxBasketReturn = 0.0f;

        // Quét từng nến tương lai (Ví dụ lúc 2h15, 2h30...)
        for (Map<Short, KlineObjectSimple> minuteData : futureRange.values()) {
            float currentStepSumRet = 0;
            int count = 0;

            // Tính Lãi của toàn bộ rổ NẾU chốt lời đồng loạt tại cái nến này
            for (Short symId : entryPrices.keySet()) {
                if (minuteData.containsKey(symId)) {
                    float currentHigh = minuteData.get(symId).maxPrice;
                    float entry = entryPrices.get(symId);
                    if (currentHigh > 0) {
                        currentStepSumRet += (currentHigh - entry) / entry;
                        count++;
                    }
                }
            }

            // Tìm mốc thời gian cho ra Lãi Trung Bình Rổ cao nhất
            if (count > 0) {
                float currentStepAvgRet = currentStepSumRet / count;
                if (currentStepAvgRet > maxBasketReturn) {
                    maxBasketReturn = currentStepAvgRet;
                }
            }
        }
        return maxBasketReturn;
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
                if (minuteData.containsKey(symId)) {
                    float low = minuteData.get(symId).minPrice;
                    float entry = entryPrices.get(symId);
                    if (low > 0) {
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