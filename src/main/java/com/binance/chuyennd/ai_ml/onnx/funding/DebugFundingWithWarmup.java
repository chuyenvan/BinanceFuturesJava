package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;

public class DebugFundingWithWarmup {
    private static final Logger LOG = LoggerFactory.getLogger(DebugFundingWithWarmup.class);

    public static void main(String[] args) throws Exception {
        // Cấu hình
        Configs.FUNDING_RATE_MIN_TRADE = -0.013;
        Configs.FUNDING_RATE_MIN_TRADE_FULL = -0.025;
        Configs.FUNDING_RATE_UP_AVG = 0.004;
        Configs.FUNDING_RATE_DOWN_AVG = -0.005;
//        Configs.NUMBER_RATE_DOWN_HISTORY_TRADE = 60; // Quan trọng cho bộ nhớ Rate

        // 1. Setup thời gian Target
        String targetTimeStr = "20210103 04:00";
        long targetTime = new SimpleDateFormat("yyyyMMdd HH:mm").parse(targetTimeStr).getTime();

        // 2. Setup thời gian Warmup (Lùi lại 24h để đủ data tính Feature Momentum24H)
        long warmupTime = targetTime - (24 * 60 * 60 * 1000L);

        LOG.info("🔥 START WARMUP from {} to {}", Utils.normalizeDateYYYYMMDDHHmm(warmupTime), targetTimeStr);

        // Load toàn bộ Market Rate Data (Load 1 lần cho nhanh)
        TreeMap<Long, MarketDataObject> time2MarketData =
                (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);

        // Init Extractor & Cache
        FundingFeatureExtractor extractor = new FundingFeatureExtractor();
        TreeMap<Long, Float> time2RateDown15MAvg = new TreeMap<>();
        List<String> cachedBasket = new ArrayList<>();
        long lastBasketTime = -1;

        // --- VÒNG LẶP WARMUP + CHECK ---
        long currentTime = warmupTime;

        // Đọc từng block 4 tiếng cho đỡ tốn RAM
        while (currentTime <= targetTime) {
            long endTimeBlock = Math.min(currentTime + 4 * 60 * 60 * 1000L, targetTime);
            int minutesToRead = (int) ((endTimeBlock - currentTime) / Utils.TIME_MINUTE) + 1;

            // Đọc Kline từ Aerospike
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, minutesToRead);

            if (time2Tickers == null || time2Tickers.isEmpty()) {
                currentTime = endTimeBlock + Utils.TIME_MINUTE;
                continue;
            }

            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                long time = entry.getKey();
                if (time > targetTime) break;

                Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();

                // 1. UPDATE HISTORY (Cốt lõi của Warmup)
                extractor.updateMarketHistory(symbol2Ticker);

                // 2. UPDATE MARKET RATE HISTORY
                MarketDataObject mData = time2MarketData.get(time);
                if (mData != null) {
                    time2RateDown15MAvg.put(time, mData.rateDown15MAvg);
                    // Giữ size history chuẩn
                    while (time2RateDown15MAvg.size() > Configs.NUMBER_RATE_DOWN_HISTORY_TRADE) {
                        time2RateDown15MAvg.remove(time2RateDown15MAvg.firstKey());
                    }
                }

                // 3. NẾU LÀ THỜI ĐIỂM TARGET -> CHECK KỸ
                if (time == targetTime) {
                    LOG.info("🎯 REACHED TARGET TIME: {}", targetTimeStr);
                    checkTargetTime(time, mData, time2RateDown15MAvg, symbol2Ticker, extractor, cachedBasket);
                    return; // Xong việc
                }

                // Update Basket logic (giống tool thật)
                if (time != lastBasketTime) {
                    cachedBasket = extractor.identifyTargetBasket(symbol2Ticker);
                    lastBasketTime = time;
                }
            }
            currentTime = endTimeBlock + Utils.TIME_MINUTE;
        }
    }

    private static void checkTargetTime(long time, MarketDataObject mData,
                                        TreeMap<Long, Float> time2RateDown15MAvg,
                                        Map<String, KlineObjectSimple> symbol2Ticker,
                                        FundingFeatureExtractor extractor,
                                        List<String> basket) {

        // 1. Check Data Availability
        if (mData == null) {
            LOG.error("❌ FAIL: No Market Data (Snappy) for target time!");
            return;
        }
        if (symbol2Ticker == null || !symbol2Ticker.containsKey("BTCUSDT")) {
            LOG.error("❌ FAIL: No Kline Data (or missing BTC) for target time!");
            return;
        }

        // 2. Check Condition IsMet
        Float minRate60M = Collections.min(time2RateDown15MAvg.values());
        boolean isCondMet = MarketBigChangeDetector.isFundingFeeTrade(
                mData.rateDown15MAvg, mData.rateDownAvg, mData.rateUpAvg, minRate60M);

        LOG.info("📊 CONDITION CHECK:");
        LOG.info("   rateDown15M: {}", mData.rateDown15MAvg);
        LOG.info("   minRate60M : {} (History size: {})", minRate60M, time2RateDown15MAvg.size());
        LOG.info("   => isMet   : {}", isCondMet);

        if (!isCondMet) {
            LOG.error("❌ SKIP REASON: Condition False!");
            return;
        }

        // 3. Test Extract Feature (Thử 1 coin đại diện)
        String testSymbol = "BTCUSDT"; // Hoặc coin nào đang hot lúc đó
        OrderTargetInfoTest dummy = new OrderTargetInfoTest(null, 100d, null, 1d, 10, testSymbol, time, time, OrderSide.BUY);
        dummy.lastEntry = 100d;

        FundingMarketFeatures f = extractor.extractFeatures(time, dummy, symbol2Ticker, basket, mData);

        if (f == null) {
            LOG.error("❌ SKIP REASON: Extract Features returned NULL!");
        } else {
            LOG.info("✅ SUCCESS: Features extracted!");
            LOG.info("   Momentum24H: {}", f.momentum24H);
            LOG.info("   RSI: {}", f.rsi1H);
            if (f.momentum24H == 0 && f.rsi1H == 0) {
                LOG.warn("⚠️ WARNING: Features are Zero! Warmup might be insufficient?");
            }
        }
    }
}