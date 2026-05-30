package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager15M;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingFeatureExtractorV2_15M;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures15M;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Tool sinh dữ liệu dự báo Funding KHUNG 15M cho TOÀN BỘ thị trường (No Filter)
 * Chạy tịnh tiến từ 2021 đến nay.
 */
public class GenerateFundingPredictionsTool15M {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateFundingPredictionsTool15M.class);

    private static class PrepareData {
        short id;
        float[] features;

        public PrepareData(short id, float[] features) {
            this.id = id;
            this.features = features;
        }
    }

    public static void main(String[] args) throws Exception {
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "4");
        DataManagerAerospikeFloatSim.setThreadCount(4);
        SimpleSymbolMapper.getInstance().init();
        FundingFeeManager.getInstance(); // Load cache Funding Fee

        String startTimeStr = "20210101";
        long startTs = Utils.sdfFile.parse(startTimeStr).getTime();
        long endTs = System.currentTimeMillis();

        new GenerateFundingPredictionsTool15M().startGeneration(startTs, endTs);
    }

    public void startGeneration(long startTs, long endTs) throws Exception {
        // Trỏ tới Model 15M mới
        String modelPath = "models_funding/Funding_Classifier_15M_label6.onnx";

        try (FundingOnnxInferenceManager15M aiBrain = new FundingOnnxInferenceManager15M(modelPath)) {
            FundingFeatureExtractorV2_15M extractor = new FundingFeatureExtractorV2_15M();

            // --- BƯỚC 1: WARMUP 24H ---
            long warmupStart = startTs - (24 * 60 * 60 * 1000L);
            LOG.info("🔥 BẮT ĐẦU WARMUP 24H: {} -> {}",
                    Utils.normalizeDateYYYYMMDDHHmm(warmupStart), Utils.normalizeDateYYYYMMDDHHmm(startTs));
            runDataLoop(warmupStart, startTs, null, true, extractor);

            // --- BƯỚC 2: GENERATE TOÀN BỘ THỊ TRƯỜNG ---
            LOG.info("🚀 BẮT ĐẦU SINH DỮ LIỆU ALL SYMBOLS 15M TỪ 2021 ĐẾN NAY...");
            runDataLoop(startTs, endTs, aiBrain, false, extractor);
        }

        LOG.info("✅ HOÀN TẤT QUÁ TRÌNH SINH DỮ LIỆU 15M.");
        System.exit(0);
    }

    private void runDataLoop(long start, long end,
                             FundingOnnxInferenceManager15M aiBrain,
                             boolean isWarmup,
                             FundingFeatureExtractorV2_15M extractor
    ) {
        long currentTime = start;

        while (currentTime < end) {
            // Đọc dữ liệu theo block 1 ngày (96 nến 15m)
            int blocksToRead = 96;
            if (currentTime + blocksToRead * 15 * Utils.TIME_MINUTE > end) {
                blocksToRead = (int) ((end - currentTime) / (15 * Utils.TIME_MINUTE)) + 1;
            }

            // Dùng hàm 15M trực tiếp nhận Map<Short, Kline>
            TreeMap<Long, Map<Short, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTime, blocksToRead);

            if (time2Tickers.isEmpty()) {
                currentTime += blocksToRead * 15 * Utils.TIME_MINUTE;
                continue;
            }

            for (Map.Entry<Long, Map<Short, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                long time = timeEntry.getKey();
                Map<Short, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                // 1. CẬP NHẬT LỊCH SỬ 15M
                extractor.updateMarketHistory(symbol2Ticker);

                if (isWarmup) continue;

                // Load Market Data 15M trực tiếp từ Aerospike (hoặc có thể load sẵn Map trên RAM nếu đủ)
                MarketDataObject15M marketData = DataManagerAerospikeFloatSim.getMarketData15MAtTime(time);
                if (marketData == null) continue;

                // 2. TÌM BASKET BẰNG ID (SHORT)
                final List<Short> basket = HistoryManager15M.getInstance().findPotentialLosersShort(time);

                // 3. TRÍCH XUẤT ĐẶC TRƯNG PARALLEL
                List<PrepareData> batchInput = symbol2Ticker.keySet().parallelStream()
                        .map(symId -> {
                            try {
                                KlineObjectSimple ticker = symbol2Ticker.get(symId);
                                if (ticker == null || !Utils.isTickerAvailable(ticker)) return null;

                                String symbolStr = SimpleSymbolMapper.getInstance().getSymbol(symId);
                                OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                                        Configs.LEVERAGE_ORDER, symbolStr, time, time, OrderSide.BUY
                                );
                                dummyOrder.lastEntry = ticker.priceClose;

                                FundingMarketFeatures15M features = extractor.extractFeatures(
                                        time, dummyOrder, symbol2Ticker, marketData, basket
                                );

                                if (features != null) {
                                    return new PrepareData(symId, aiBrain.extractFeaturesToArray(features));
                                }
                            } catch (Exception e) {
                                LOG.error("Lỗi extract symbol ID " + symId + " tại " + time, e);
                            }
                            return null;
                        })
                        .filter(Objects::nonNull)
                        .collect(Collectors.toList());

                if (batchInput.isEmpty()) continue;

                // 4. PREDICTION THEO BATCH
                Map<Short, float[]> finalResults = new ConcurrentHashMap<>();
                int chunkSize = 20;
                for (int i = 0; i < batchInput.size(); i += chunkSize) {
                    List<PrepareData> chunk = batchInput.subList(i, Math.min(batchInput.size(), i + chunkSize));
                    List<float[]> featureList = chunk.stream().map(p -> p.features).collect(Collectors.toList());

                    try {
                        List<float[]> chunkResults = aiBrain.predictBatch(featureList);
                        for (int j = 0; j < chunkResults.size(); j++) {
                            finalResults.put(chunk.get(j).id, chunkResults.get(j));
                        }
                    } catch (Exception e) {
                        LOG.error("Lỗi AI Inference 15M tại " + time, e);
                    }
                }

                // 5. LƯU KẾT QUẢ VÀO AEROSPIKE (Nhớ định nghĩa hàm saveFundingPredictions15M)
                if (!finalResults.isEmpty()) {
                    DataManagerAerospikeFloatSim.saveFundingPredictions1M(time, finalResults);
                }
            }

            if (!isWarmup) {
                LOG.info("✅ Đã xử lý xong: {} | Last Key: {}",
                        Utils.normalizeDateYYYYMMDD(currentTime),
                        Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.lastKey()));
                System.gc();
            }

            // Bước nhảy 15 phút
            currentTime = time2Tickers.lastKey() + 15 * Utils.TIME_MINUTE;
            time2Tickers = null;
        }
    }
}