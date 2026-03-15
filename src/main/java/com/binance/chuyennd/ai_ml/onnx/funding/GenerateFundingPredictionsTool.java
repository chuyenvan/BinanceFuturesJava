package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

public class GenerateFundingPredictionsTool {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateFundingPredictionsTool.class);

    private static class PrepareData {
        short id;
        float[] features;

        public PrepareData(short id, float[] features) {
            this.id = id;
            this.features = features;
        }
    }

    /**
     * 🔥 HÀM QUAN TRỌNG: Cấu hình SIÊU LỎNG để đảm bảo sinh dư Data cho HPO.
     * Cấu hình này phải nới lỏng hơn tất cả các biên (bounds) lớn nhất mà HPO có thể quét tới.
     */
    private static void setLooseConfigsForGeneration() {
        LOG.info("🔧 Áp dụng cấu hình SIÊU LỎNG để sinh Data bao phủ toàn bộ HPO...");
        // HPO min trade quét tới -0.015 -> Ta mở rộng đến -0.008
        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = -0.008f;
        // HPO min full quét tới -0.020 -> Ta mở rộng đến -0.012
        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = -0.012f;
        // HPO up avg quét tới 0.004 -> Ta mở rộng đến 0.002
        Configs.PREDICT_SYMBOL_RATE_UP_AVG = 0.002f;
        // HPO down avg quét tới -0.004 -> Ta mở rộng đến -0.002
        Configs.PREDICT_SYMBOL_RATE_DOWN_AVG = -0.002f;
        Configs.NUMBER_RATE_DOWN_HISTORY_TRADE = 60;
    }

    public static void main(String[] args) throws Exception {
        // 1. Cấu hình số luồng (4 Core)
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "4");
        DataManagerAerospikeFloatSim.setThreadCount(4);

        // 2. Ép cấu hình siêu lỏng để Generate Data
        setLooseConfigsForGeneration();

        // Cấu hình thời gian chạy
        String startTimeStr = "20210101";
        long startTime = Utils.sdfFile.parse(startTimeStr).getTime();
        long endTime = System.currentTimeMillis();

        String mode = args.length > 0 ? args[0] : "worker";

        if ("init".equalsIgnoreCase(mode)) {
            AerospikeTaskCoordinator.initTasks(startTime, endTime);
            return;
        }

        new GenerateFundingPredictionsTool().processDistributedTasks();
    }

    public void processDistributedTasks() throws Exception {
        String modelPath = "models_funding/Funding_Classifier_Final_Fixed.onnx";

        // Load Data Market Rate
        TreeMap<Long, MarketDataObject> time2MarketData =  DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();

        LOG.info("📥 Loading Symbol Mapper...");
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);

        try (FundingOnnxInferenceManager aiBrain = new FundingOnnxInferenceManager(modelPath)) {
            int consecutiveFailures = 0;
            while (true) {
                AerospikeTaskCoordinator.TaskRange task = AerospikeTaskCoordinator.claimNextTask();

                if (task == null) {
                    consecutiveFailures++;
                    LOG.info("📭 Queue is empty. Attempt {}/3...", consecutiveFailures);
                    if (consecutiveFailures >= 3) {
                        LOG.info("✅ ALL TASKS COMPLETED.");
                        break;
                    }
                    Thread.sleep(5000);
                    continue;
                }
                consecutiveFailures = 0;

                LOG.info("🚀 Processing Task: {} -> {}",
                        Utils.normalizeDateYYYYMMDDHHmm(task.start),
                        Utils.normalizeDateYYYYMMDDHHmm(task.end));

                try {
                    generateToAerospike(task.start, task.end, aiBrain, time2MarketData, symbolMap);
                } catch (Exception e) {
                    LOG.error("❌ Error processing task " + task.start, e);
                }
            }
        }
        LOG.info("👋 Worker shutdown cleanly.");
        System.exit(0);
    }

    private void generateToAerospike(
            long startTime,
            long endTime,
            FundingOnnxInferenceManager aiBrain,
            TreeMap<Long, MarketDataObject> time2MarketData,
            ConcurrentHashMap<String, Short> symbolMap
    ) {
        FundingFeatureExtractor extractor = new FundingFeatureExtractor();


        // --- GIAI ĐOẠN 1: WARMUP ---
        long warmupStartTime = startTime - (24 * 60 * 60 * 1000L);
        LOG.info("🔥 WARMUP: {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(warmupStartTime), Utils.normalizeDateYYYYMMDDHHmm(startTime));

        runDataLoop(warmupStartTime, startTime, time2MarketData, null, symbolMap, true, extractor);

        LOG.info("✅ WARMUP DONE. Generating...");

        // --- GIAI ĐOẠN 2: GENERATION ---
        runDataLoop(startTime, endTime, time2MarketData, aiBrain, symbolMap, false, extractor);

        LOG.info("🎉 DONE TASK: {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(startTime), Utils.normalizeDateYYYYMMDDHHmm(endTime));
    }

    private void runDataLoop(long start, long end,
                             TreeMap<Long, MarketDataObject> time2MarketData,
                             FundingOnnxInferenceManager aiBrain,
                             ConcurrentHashMap<String, Short> symbolMap,
                             boolean isWarmup,
                             FundingFeatureExtractor extractor
    ) {
        long currentTime = start;
        long lastBasketTimestamp = -1;
        List<String> cachedBasket = new ArrayList<>();

        while (currentTime < end) {
            int minutesToRead = 1440;
            if (currentTime + minutesToRead * Utils.TIME_MINUTE > end) {
                minutesToRead = (int) ((end - currentTime) / Utils.TIME_MINUTE) + 1;
            }

            Set<Long> existingTimestamps = new HashSet<>();
            if (!isWarmup) {
                List<Long> timestampsToCheck = new ArrayList<>();
                for(int i=0; i<minutesToRead; i++) timestampsToCheck.add(currentTime + i * Utils.TIME_MINUTE);
                existingTimestamps = DataManagerAerospikeFloatSim.checkExistingFundingPredictions(timestampsToCheck);
            }

            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, minutesToRead);

            if (time2Tickers == null || time2Tickers.isEmpty()) {
                currentTime += minutesToRead * Utils.TIME_MINUTE;
                continue;
            }

            int generatedCount = 0;
            int processedCount = 0;

            for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                long time = timeEntry.getKey();
                if (time >= end) break;

                Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                // 1. UPDATE HISTORY
                extractor.updateMarketHistory(symbol2Ticker);

                if (isWarmup || existingTimestamps.contains(time)) continue;

                processedCount++;
                if (time != lastBasketTimestamp) {
                    cachedBasket = extractor.identifyTargetBasket(symbol2Ticker);
                    lastBasketTimestamp = time;
                }
                final List<String> currentBasket = cachedBasket;
                Set<String> symbolFundingBuy = symbol2Ticker.keySet();

                // 3. FEATURE EXTRACTION
                List<PrepareData> batchInput = symbolFundingBuy.parallelStream()
                        .map(symbol -> {
                            try {
                                Short symId = symbolMap.get(symbol);
                                if (symId == null) return null;

                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (ticker == null || !Utils.isTickerAvailable(ticker)) return null;

                                OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                                        Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                                );
                                dummyOrder.lastEntry = ticker.priceClose;

                                FundingMarketFeatures features = extractor.extractFeatures(
                                        time, dummyOrder, symbol2Ticker, currentBasket, time2MarketData.get(time)
                                );

                                if (features != null) {
                                    return new PrepareData(symId, aiBrain.extractFeaturesToArray(features));
                                }
                            } catch (Exception e) {
                                LOG.error("Error processing " + symbol, e);
                            }
                            return null;
                        })
                        .filter(Objects::nonNull)
                        .collect(Collectors.toList());

                if (batchInput.isEmpty()) continue;

                // 4. PREDICTION
                Map<Short, float[]> finalResults = new ConcurrentHashMap<>();
                int chunkSize = 20;
                List<List<PrepareData>> chunks = new ArrayList<>();
                for (int i = 0; i < batchInput.size(); i += chunkSize) {
                    chunks.add(batchInput.subList(i, Math.min(batchInput.size(), i + chunkSize)));
                }

                chunks.parallelStream().forEach(chunk -> {
                    try {
                        List<float[]> featureList = chunk.stream().map(p -> p.features).collect(Collectors.toList());
                        List<float[]> chunkResults = aiBrain.predictBatch(featureList);

                        if (chunkResults.size() == chunk.size()) {
                            for (int i = 0; i < chunk.size(); i++) {
                                finalResults.put(chunk.get(i).id, chunkResults.get(i));
                            }
                        }
                    } catch (Exception e) {
                        LOG.error("Prediction error", e);
                    }
                });

                if (!finalResults.isEmpty()) {
                    DataManagerAerospikeFloatSim.saveFundingPredictions1M(time, finalResults);
                    generatedCount += finalResults.size();
                }
            }

            if (!isWarmup && (generatedCount > 0 || processedCount > 0)) {
                LOG.info("   ✅ Block: {} | Gen: {} records | Processed: {} mins",
                        Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.lastKey()), generatedCount, processedCount);
            }

            long lastKey = time2Tickers.lastKey();
            time2Tickers = null;
            if (generatedCount > 0) System.gc();
            currentTime = lastKey + Utils.TIME_MINUTE;
        }
    }



    // --- THÊM HÀM NÀY CHO SIMULATOR GỌI (CHẠY BÙ) ---
    public void generateAndSave(Long lastTimestamp) throws Exception {
        // 🔥 Gọi Config siêu lỏng trước khi chạy bù
        setLooseConfigsForGeneration();

        String modelPath = "models_funding/Funding_Classifier_Final_Fixed.onnx";

        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();

        LOG.info("📥 Loading Symbol Mapper cho Funding Tool...");
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);

        long currentTime;
        if (lastTimestamp != null && lastTimestamp > 0) {
            currentTime = Utils.getDate(lastTimestamp);
            LOG.info("🔄 Resuming Funding Predictions từ ngày: {}", Utils.normalizeDateYYYYMMDDHHmm(currentTime));
        } else {
            currentTime = Utils.sdfFile.parse("20210101").getTime();
            LOG.info("🚀 STARTING FUNDING PREDICTION GENERATION FROM SCRATCH...");
        }

        long endTime = System.currentTimeMillis();

        try (FundingOnnxInferenceManager aiBrain = new FundingOnnxInferenceManager(modelPath)) {
            generateToAerospike(currentTime, endTime, aiBrain, time2MarketData, symbolMap);
        }
    }
}