package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

public class GenerateEntryDcaPredictionsLabel40Tool {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateEntryDcaPredictionsLabel40Tool.class);

    // Singleton resources cho On-Demand Label 40
    private static EntryDcaOnnxInferenceManager sharedAiBrain;
    private static ConcurrentHashMap<String, Short> sharedSymbolMap;
    private static TreeMap<Long, MarketDataObject> sharedMarketData;

    private static class PrepareData {
        short id;
        float[] features;

        public PrepareData(short id, float[] features) {
            this.id = id;
            this.features = features;
        }
    }

    public static void main(String[] args) throws Exception {
        // 1. Cấu hình số luồng (4 Core)
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "4");
        DataManagerAerospikeFloatSim.setThreadCount(4);

        // Cấu hình tham số lọc
        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = -0.013f;
        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = -0.025f;
        Configs.PREDICT_SYMBOL_RATE_UP_AVG = 0.004f;
        Configs.PREDICT_SYMBOL_RATE_DOWN_AVG = -0.005f;


        // Cấu hình thời gian chạy
        String startTimeStr = "20210101";
        long startTime = Utils.sdfFile.parse(startTimeStr).getTime();
        long endTime = System.currentTimeMillis();

        String mode = args.length > 0 ? args[0] : "worker";

        if ("init".equalsIgnoreCase(mode)) {
            AerospikeTaskCoordinator.initTasks(startTime, endTime);
            return;
        }

        new GenerateEntryDcaPredictionsLabel40Tool().processDistributedTasks();
    }

    public void processDistributedTasks() throws Exception {
        // 🔥 ĐỔI MODEL SANG LABEL 40
        String modelPath = "models_funding/Funding_Classifier_Label40_GPU_Simple.onnx";

        // Load Data Market Rate
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();

        LOG.info("📥 Loading Symbol Mapper...");
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);

        try (EntryDcaOnnxInferenceManager aiBrain = new EntryDcaOnnxInferenceManager(modelPath)) {
            int consecutiveFailures = 0;
            while (true) {
                // Có thể dùng chung Task Coordinator với Label 6 hoặc tạo set task riêng tùy logic
                // Ở đây giả sử dùng chung task range
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

                LOG.info("🚀 Processing Task Label 40: {} -> {}",
                        Utils.normalizeDateYYYYMMDDHHmm(task.start),
                        Utils.normalizeDateYYYYMMDDHHmm(task.end));

                try {
                    generateToAerospike(task.start, task.end, aiBrain, time2MarketData, symbolMap);
                } catch (Exception e) {
                    LOG.error("❌ Error processing task " + task.start, e);
                }
            }
        }
        LOG.info("👋 Worker Label 40 shutdown cleanly.");
        System.exit(0);
    }

    // =========================================================================
    // ON-DEMAND GENERATION FOR LABEL 40 (CHO SIMULATOR)
    // =========================================================================

    public static synchronized void initGlobalResources() throws Exception {
        if (sharedAiBrain != null) return;

        LOG.info("⚙️ Initializing Label 40 Resources...");
        String modelPath = "models_funding/Funding_Classifier_Label40_GPU_Simple.onnx";

        sharedAiBrain = new EntryDcaOnnxInferenceManager(modelPath);
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        sharedSymbolMap = new ConcurrentHashMap<>(globalMapper);
        DataManagerAerospikeFloatSim.setThreadCount(4);
    }

    public static void generateOnDemand(long startTime, int durationMinutes) {
        try {
            if (sharedAiBrain == null) initGlobalResources();

            long endTime = startTime + durationMinutes * Utils.TIME_MINUTE;
            LOG.warn("⚠️ TRIGGER LABEL 40 GENERATE ON-DEMAND: {} -> {}",
                    Utils.normalizeDateYYYYMMDDHHmm(startTime), Utils.normalizeDateYYYYMMDDHHmm(endTime));

            new GenerateEntryDcaPredictionsLabel40Tool().generateToAerospike(
                    startTime, endTime, sharedAiBrain, sharedMarketData, sharedSymbolMap);

        } catch (Exception e) {
            LOG.error("❌ Error generating Label 40 on-demand data", e);
        }
    }

    private void generateToAerospike(
            long startTime,
            long endTime,
            EntryDcaOnnxInferenceManager aiBrain,
            TreeMap<Long, MarketDataObject> time2MarketData,
            ConcurrentHashMap<String, Short> symbolMap
    ) {
        FundingFeatureExtractor extractor = new FundingFeatureExtractor();
        TreeMap<Long, Float> time2RateDown15MAvg = new TreeMap<>();

        // --- WARMUP ---
        long warmupStartTime = startTime - (24 * 60 * 60 * 1000L);
        LOG.info("🔥 WARMUP LABEL 40: {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(warmupStartTime), Utils.normalizeDateYYYYMMDDHHmm(startTime));

        runDataLoop(warmupStartTime, startTime, time2MarketData, null, symbolMap, true, extractor, time2RateDown15MAvg);

        LOG.info("✅ WARMUP DONE. Generating Label 40...");

        // --- GENERATION ---
        runDataLoop(startTime, endTime, time2MarketData, aiBrain, symbolMap, false, extractor, time2RateDown15MAvg);

        LOG.info("🎉 DONE TASK LABEL 40: {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(startTime), Utils.normalizeDateYYYYMMDDHHmm(endTime));
    }

    private void runDataLoop(long start, long end,
                             TreeMap<Long, MarketDataObject> time2MarketData,
                             EntryDcaOnnxInferenceManager aiBrain,
                             ConcurrentHashMap<String, Short> symbolMap,
                             boolean isWarmup,
                             FundingFeatureExtractor extractor,
                             TreeMap<Long, Float> time2RateDown15MAvg
    ) {
        long currentTime = start;

        while (currentTime < end) {
            int minutesToRead = 1440;
            if (currentTime + minutesToRead * Utils.TIME_MINUTE > end) {
                minutesToRead = (int) ((end - currentTime) / Utils.TIME_MINUTE) + 1;
            }

            // 🔥 Check existing Label 40
            Set<Long> existingTimestamps = new HashSet<>();
            if (!isWarmup) {
                List<Long> timestampsToCheck = new ArrayList<>();
                for (int i = 0; i < minutesToRead; i++) timestampsToCheck.add(currentTime + i * Utils.TIME_MINUTE);
                existingTimestamps = DataManagerAerospikeFloatSim.checkExistingFundingLabel40Predictions(timestampsToCheck);
            }

            long readStart = System.currentTimeMillis();
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, minutesToRead);
            long readDuration = System.currentTimeMillis() - readStart;

            if (time2Tickers == null || time2Tickers.isEmpty()) {
                LOG.info("⚠️ [AEROSPIKE WARNING] No data returned for block: {} -> {} (Requested {} mins). Time taken: {}ms",
                        Utils.normalizeDateYYYYMMDDHHmm(currentTime),
                        Utils.normalizeDateYYYYMMDDHHmm(currentTime + minutesToRead * Utils.TIME_MINUTE),
                        minutesToRead, readDuration);
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

                final List<String> currentBasket = CoinRankManager.getInstance().getTopCoin(time);
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
                                        time, dummyOrder, symbol2Ticker, time2MarketData.get(time)
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
                    // 🔥 GHI VÀO SET LABEL 40
                    DataManagerAerospikeFloatSim.saveFundingPredictionsLabel40(time, finalResults);
                    generatedCount += finalResults.size();
                }
            }

            if (!isWarmup && (generatedCount > 0 || processedCount > 0)) {
                LOG.info("   ✅ Block Label 40: {} | Gen: {} records | Processed: {} mins",
                        Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.lastKey()), generatedCount, processedCount);
            }

            long lastKey = time2Tickers.lastKey();
            time2Tickers = null;
            if (generatedCount > 0) System.gc();
            currentTime = lastKey + Utils.TIME_MINUTE;
        }
    }




}