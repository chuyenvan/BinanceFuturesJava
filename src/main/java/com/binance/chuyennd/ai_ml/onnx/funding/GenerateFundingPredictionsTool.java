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
        // 1. Ép Java dùng tối đa năng lực CPU (TPU VM có 96 cores -> set 90)
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "90");

        // 2. Tăng luồng đọc/ghi Aerospike
        DataManagerAerospikeFloatSim.setThreadCount(60);

        // Cấu hình tham số lọc
        Configs.FUNDING_RATE_MIN_TRADE = -0.013;
        Configs.FUNDING_RATE_MIN_TRADE_FULL = -0.025;
        Configs.FUNDING_RATE_UP_AVG = 0.004;
        Configs.FUNDING_RATE_DOWN_AVG = -0.005;

        try {
            FundingFeeManager.getInstance();
        } catch (Exception e) {
        }

        // ⚠️ CẤU HÌNH THỜI GIAN
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
        // Load model & data 1 lần (tránh load lại mỗi task)
            String modelPath = "models_funding/Funding_Classifier_Final_v2.onnx";
        FundingOnnxInferenceManager aiBrain = new FundingOnnxInferenceManager(modelPath);
        TreeMap<Long, MarketDataObject> time2MarketData = loadMarketRateData();
        LOG.info("📥 Loading Symbol Mapper...");
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);
        int consecutiveFailures = 0;
        while (true) {
            // Claim task từ queue
            AerospikeTaskCoordinator.TaskRange task = AerospikeTaskCoordinator.claimNextTask();

            if (task == null) {
                // Retry 3 lần, sau đó shutdown
                if (++consecutiveFailures >= 3) break;
                Thread.sleep(10000);
                continue;
            }

            // Xử lý task
            generateToAerospike(task.start, task.end, aiBrain, time2MarketData, symbolMap);
        }
    }
    private void generateToAerospike(
            long startTime,
            long endTime,
            FundingOnnxInferenceManager aiBrain,  // ← Tái sử dụng
            TreeMap<Long, MarketDataObject> time2MarketData,  // ← Tái sử dụng
            ConcurrentHashMap<String, Short> symbolMap
    ) {
        FundingFeatureExtractor extractor = new FundingFeatureExtractor();




        long currentTime = startTime;
        long lastBasketTimestamp = -1;
        List<String> cachedBasket = new ArrayList<>();

        while (currentTime <= endTime) {
            // Đọc 2 tiếng một lần để giảm IO overhead
            int minutesToRead = 120;
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, minutesToRead);

            if (time2Tickers == null || time2Tickers.isEmpty()) {
                currentTime += 60 * Utils.TIME_MINUTE;
                continue;
            }

            int processedCount = 0;
            int generatedCount = 0;

            for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                long time = timeEntry.getKey();
                if (time > endTime) break;

                Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                // LUÔN UPDATE HISTORY (Tuần tự vì cần đúng thứ tự thời gian)
                extractor.updateMarketHistory(symbol2Ticker);
                updateMarketRateHistory(time, time2MarketData);

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
                Set<String> symbolFundingBuy = symbol2Ticker.keySet();
//                Set<String> symbolFundingBuy = FundingFeeManager.getInstance().getFundingListSymbol2Trade(time);
//                if (symbolFundingBuy == null || symbolFundingBuy.isEmpty()) continue;

                // =================================================================
                // 🔥 PHASE 1: PARALLEL FEATURE EXTRACTION (Tận dụng 96 Cores)
                // =================================================================
                List<PrepareData> batchInput = symbolFundingBuy.parallelStream() // QUAN TRỌNG: Dùng parallelStream
                        .map(symbol -> {
                            try {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (ticker == null || !Utils.isTickerAvailable(ticker)) return null;

                                short symId = SimpleSymbolMapper.getInstance().getId(symbol);

                                OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0,
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

                // =================================================================
                // 🔥 PHASE 2: PARALLEL BATCH PREDICTION (Chia nhỏ để chạy song song)
                // =================================================================
                Map<Short, float[]> finalResults = new ConcurrentHashMap<>();

                // Chia batch lớn thành các chunk nhỏ (ví dụ 10 item/chunk) để ép chạy song song nhiều luồng
                int chunkSize = 10;
                List<List<PrepareData>> chunks = new ArrayList<>();
                for (int i = 0; i < batchInput.size(); i += chunkSize) {
                    chunks.add(batchInput.subList(i, Math.min(batchInput.size(), i + chunkSize)));
                }

                // Chạy Predict song song cho từng chunk
                chunks.parallelStream().forEach(chunk -> {
                    List<float[]> featureList = chunk.stream().map(p -> p.features).collect(Collectors.toList());
                    // Gọi AI Predict cho chunk này
                    List<float[]> chunkResults = aiBrain.predictBatch(featureList);

                    for (int i = 0; i < chunk.size(); i++) {
                        finalResults.put(chunk.get(i).id, chunkResults.get(i));
                    }
                });

                // SAVE TO DB
                DataManagerAerospikeFloatSim.saveFundingPredictions1M(time, finalResults);
                generatedCount += finalResults.size();
            }

            // Log Progress
            if (time2Tickers.size() > 0) {
                long lastTimeInBlock = time2Tickers.lastKey();
                LOG.info("   ✅ Block: {} | Gen: {} candidates (Processed {} minutes)",
                        Utils.normalizeDateYYYYMMDDHHmm(lastTimeInBlock), generatedCount, processedCount);

                time2Tickers = null;
                if (processedCount > 0) System.gc();
                currentTime = lastTimeInBlock + Utils.TIME_MINUTE;
            } else {
                currentTime += minutesToRead * Utils.TIME_MINUTE;
            }
        }
        LOG.info("🎉 DONE GENERATION!");
    }

    // --- Helper Methods ---

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
                marketData.rateDown15MAvg, marketData.rateDownAvg, marketData.rateUpAvg, minRate15Min60M);
    }

    private TreeMap<Long, MarketDataObject> loadMarketRateData() throws Exception {
        if (!new File(Configs.FILE_ENTRY_MARKET_LEVEL).exists()) {
            LOG.info("Khong co file: {}", Configs.FILE_ENTRY_MARKET_LEVEL);
            return new TreeMap<>();
        }
        return (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
    }
}