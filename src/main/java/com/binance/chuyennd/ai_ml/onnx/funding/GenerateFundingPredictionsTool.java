package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

public class GenerateFundingPredictionsTool {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateFundingPredictionsTool.class);

    private final TreeMap<Long, Float> time2RateDown15MAvg = new TreeMap<>();

    private static class PrepareData {
        short id;
        float[] features;

        public PrepareData(short id, float[] features) {
            this.id = id;
            this.features = features;
        }
    }

    public static void main(String[] args) throws Exception {
        // 1. Ép Java dùng tối đa năng lực CPU cho các tác vụ tính toán song song (Stream API)
        // Mặc định nó chỉ dùng ít core, ta set lên 80 để chừa lại chút cho OS
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "80");

        // 2. Tăng luồng đọc/ghi Aerospike (IO Bound)
        // Vì máy mạnh, ta có thể mở rộng băng thông đọc dữ liệu
        DataManagerAerospikeFloatSim.setThreadCount(30);


        // Cấu hình tham số lọc
        Configs.FUNDING_RATE_MIN_TRADE = -0.013;
        Configs.FUNDING_RATE_MIN_TRADE_FULL = -0.025;
        Configs.FUNDING_RATE_UP_AVG = 0.004;
        Configs.FUNDING_RATE_DOWN_AVG = -0.005;

        // Init Funding Manager
        try {
            FundingFeeManager.getInstance();
        } catch (Exception e) {
        }

        // ⚠️ CẤU HÌNH THỜI GIAN CHẠY TẠI ĐÂY
        String startTimeStr = "20210101";
        long startTime = Utils.sdfFile.parse(startTimeStr).getTime();
        long endTime = System.currentTimeMillis();

        LOG.info("🔥 STARTING FUNDING PREDICTION GENERATION (BATCH MODE + RESUME)...");
        new GenerateFundingPredictionsTool().generateToAerospike(startTime, endTime);
    }

    public void generateToAerospike(long startTime, long endTime) throws Exception {
        // 1. Load Model & Data
        String modelPath = "models_funding/Funding_Classifier_Final_v2.onnx";
        FundingOnnxInferenceManager aiBrain = new FundingOnnxInferenceManager(modelPath);
        FundingFeatureExtractor extractor = new FundingFeatureExtractor();

        LOG.info("📥 Loading Market Rates...");
        TreeMap<Long, MarketDataObject> time2MarketData = loadMarketRateData();

        LOG.info("📥 Loading Symbol Mapper...");
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        int maxId = globalMapper.values().stream().mapToInt(Short::intValue).max().orElse(0);
        AtomicInteger idCounter = new AtomicInteger(maxId);
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);

        long currentTime = startTime;
        long lastBasketTimestamp = -1;
        List<String> cachedBasket = new ArrayList<>();

        while (currentTime <= endTime) {
            int minutesToRead = 60;
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, minutesToRead);

            if (time2Tickers == null || time2Tickers.isEmpty()) {
                currentTime += 60 * Utils.TIME_MINUTE;
                continue;
            }

            // 🔥 BƯỚC 1: CHECK EXISTING (Để Skip những phút đã chạy rồi)
//            List<Long> timestampsToCheck = new ArrayList<>(time2Tickers.keySet());
//            Set<Long> existingTimestamps = DataManagerAerospikeFloatSim.checkExistingFundingPredictions(timestampsToCheck);

            int processedCount = 0;
            int skippedCount = 0;
            int generatedCount = 0;
//            long timeDebug = Utils.sdfFileHour.parse("20241202 14:22").getTime();
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                long time = timeEntry.getKey();
                if (time > endTime) break;

                Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                // LUÔN UPDATE HISTORY để indicator đúng
                extractor.updateMarketHistory(symbol2Ticker);
                updateMarketRateHistory(time, time2MarketData);

//                if (time == timeDebug) {
//                    LOG.info("Debug: {} ", Utils.normalizeDateYYYYMMDDHHmm(time));
//                }else {
//                    continue;
//                }
                // Nếu đã có data trong DB -> Skip logic tính toán nặng
//                if (existingTimestamps.contains(time)) {
//                    skippedCount++;
//                    continue;
//                }

                // CHECK ĐIỀU KIỆN THỊ TRƯỜNG
                if (!isMarketConditionMet(time, time2MarketData)) {
                    continue;
                }

                processedCount++;

                // LẤY BASKET
                if (time != lastBasketTimestamp) {
                    cachedBasket = extractor.identifyTargetBasket(symbol2Ticker);
                    lastBasketTimestamp = time;
                }
                final List<String> currentBasket = cachedBasket;

                // LỌC SYMBOL TIỀM NĂNG
                Set<String> symbolFundingBuy = FundingFeeManager.getInstance().getFundingListSymbol2Trade(time);
                if (symbolFundingBuy == null || symbolFundingBuy.isEmpty()) continue;

                // CHUẨN BỊ BATCH INPUT
                List<PrepareData> batchInput = symbolFundingBuy.stream() // Tạm bỏ parallel để log không bị lộn xộn
                        .map(symbol -> {
                            try {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);

                                // Check 1: Data Ticker
                                if (ticker == null) {
                                    LOG.info("❌ [FILTER] {}: Ticker NULL", symbol);
                                    return null;
                                }
                                if (!Utils.isTickerAvailable(ticker)) return null;


                                // Check 3: Rate Filters (QUAN TRỌNG NHẤT)
//                                double rate1m = (ticker.priceClose - ticker.priceOpen) / ticker.priceOpen;
//                                double rate15m = extractor.calculateReturn(symbol, 15);

                                // Logic: Chỉ giữ lại nếu (rate1m < -0.4%) HOẶC (rate15m < -1.5%)
                                // Tức là đang sập mạnh.
//                                if (rate1m >= -0.0065) {
//                                    // Mở comment dòng này để xem tại sao bị loại
////                                    LOG.info("❌ [FILTER RATE] {}: Rate1m={}%, Rate15m={}% (Chưa đủ sập)",
////                                            symbol, String.format("%.3f", rate1m * 100), String.format("%.3f", rate15m * 100));
//                                    return null;
//                                }

                                // Map Symbol -> Short ID
                                short symId = SimpleSymbolMapper.getInstance().getId(symbol);

                                OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0,
                                        Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                                );
                                dummyOrder.lastEntry = ticker.priceClose;

                                // Check 4: Feature Extraction
                                FundingMarketFeatures features = extractor.extractFeatures(
                                        time, dummyOrder, symbol2Ticker, currentBasket
                                );

                                if (features == null) {
//                                    LOG.info("❌ [FILTER FEATURE] {}: Extract Features NULL (Thiếu history RSI?)", symbol);
                                    return null;
                                }

                                // PASS TẤT CẢ -> LẤY
//                                LOG.info("✅ [PASS] {}: Đủ điều kiện vào AI predict", symbol);
                                return new PrepareData(symId, aiBrain.extractFeaturesToArray(features));

                            } catch (Exception e) {
                                LOG.error("Error processing " + symbol, e);
                            }
                            return null;
                        })
                        .filter(Objects::nonNull)
                        .collect(Collectors.toList());

                LOG.info("📊 DEBUG SUMMARY: Input Candidates={}, Passed Filters={}", symbolFundingBuy.size(), batchInput.size());

                if (batchInput.isEmpty()) continue;

                // RUN AI (BATCH)
                List<float[]> featureList = batchInput.stream().map(p -> p.features).collect(Collectors.toList());
                List<float[]> aiResults = aiBrain.predictBatch(featureList);

                // SAVE TO DB
                Map<Short, float[]> finalResults = new HashMap<>();
                for (int i = 0; i < batchInput.size(); i++) {
                    finalResults.put(batchInput.get(i).id, aiResults.get(i));
                }
                DataManagerAerospikeFloatSim.saveFundingPredictions1M(time, finalResults);
                generatedCount += finalResults.size();
            }

            // Log & Clean
            if (time2Tickers.size() > 0) {
                long lastTimeInBlock = time2Tickers.lastKey();
                String status = (skippedCount == time2Tickers.size()) ? "(SKIP ALL)" :
                        String.format("(Run: %d, Skip: %d, Gen: %d)", processedCount, skippedCount, generatedCount);

                LOG.info("   ✅ Block: {} | {}", Utils.normalizeDateYYYYMMDDHHmm(lastTimeInBlock), status);

                time2Tickers = null;
                // Chỉ GC nếu thực sự có chạy tính toán mới
                if (processedCount > 0) System.gc();

                currentTime = lastTimeInBlock + Utils.TIME_MINUTE;
            } else {
                currentTime += minutesToRead * Utils.TIME_MINUTE;
            }
        }

        aiBrain.close();
        LOG.info("🎉 DONE GENERATION!");
    }

    // --- Helper Methods cho gọn code ---

    private void updateMarketRateHistory(long time, TreeMap<Long, MarketDataObject> time2MarketData) {
        MarketDataObject marketData = time2MarketData.get(time);
        if (marketData == null) return;
        time2RateDown15MAvg.put(time, marketData.rateDown15MAvg);
        while (time2RateDown15MAvg.size() > Configs.NUMBER_RATE_DOWN_HISTORY_TRADE) {
            time2RateDown15MAvg.remove(time2RateDown15MAvg.firstKey());
        }
    }

    private boolean isMarketConditionMet(long time, TreeMap<Long, MarketDataObject> time2MarketData) {
        MarketDataObject marketData = time2MarketData.get(time);
        if (marketData == null) return false;

        Float minRate15Min60M = time2RateDown15MAvg.isEmpty() ? 0f : Collections.min(time2RateDown15MAvg.values());

        return MarketBigChangeDetector.isFundingFeeTrade(
                marketData.rateDown15MAvg,
                marketData.rateDownAvg,
                marketData.rateUpAvg,
                minRate15Min60M);
    }

    private TreeMap<Long, MarketDataObject> loadMarketRateData() throws Exception {
        if (!new File(Configs.FILE_ENTRY_MARKET_LEVEL).exists()) {
            LOG.info("Khong co file market data! {}", Configs.FILE_ENTRY_MARKET_LEVEL);
            return new TreeMap<>();
        }
        return (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
    }
}