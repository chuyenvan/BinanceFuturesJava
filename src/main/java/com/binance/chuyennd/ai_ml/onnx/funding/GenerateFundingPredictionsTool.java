package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Tool sinh dữ liệu dự báo Funding cho TOÀN BỘ thị trường (No Filter)
 * Chạy tịnh tiến từ 2021 đến nay.
 */
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

    public static void main(String[] args) throws Exception {
        // Cấu hình tối ưu hiệu năng
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "4");
        DataManagerAerospikeFloatSim.setThreadCount(4);

        // Thiết lập mốc thời gian chạy: Từ 01/01/2021
        String startTimeStr = "20210101";
        long startTs = Utils.sdfFile.parse(startTimeStr).getTime();
        long endTs = System.currentTimeMillis();

        new GenerateFundingPredictionsTool().startGeneration(startTs, endTs);
    }

    public void startGeneration(long startTs, long endTs) throws Exception {
        String modelPath = "models_funding/Funding_Classifier_Final_Fixed.onnx";

        LOG.info("📥 Đang tải dữ liệu Market & Mapper từ Aerospike...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);

        try (FundingOnnxInferenceManager aiBrain = new FundingOnnxInferenceManager(modelPath)) {
            FundingDataCollectionManager.FundingFeatureExtractorV2 extractor = new FundingDataCollectionManager.FundingFeatureExtractorV2();

            // --- BƯỚC 1: WARMUP 24H ---
            // (Cần thiết để các chỉ số RSI/MA có khởi đầu chính xác)
            long warmupStart = startTs - (24 * 60 * 60 * 1000L);
            LOG.info("🔥 BẮT ĐẦU WARMUP 24H: {} -> {}",
                    Utils.normalizeDateYYYYMMDDHHmm(warmupStart), Utils.normalizeDateYYYYMMDDHHmm(startTs));
            runDataLoop(warmupStart, startTs, time2MarketData, null, symbolMap, true, extractor);

            // --- BƯỚC 2: GENERATE TOÀN BỘ THỊ TRƯỜNG ---
            LOG.info("🚀 BẮT ĐẦU SINH DỮ LIỆU ALL SYMBOLS TỪ 2021 ĐẾN NAY...");
            runDataLoop(startTs, endTs, time2MarketData, aiBrain, symbolMap, false, extractor);
        }

        LOG.info("✅ HOÀN TẤT QUÁ TRÌNH SINH DỮ LIỆU.");
        System.exit(0);
    }

    private void runDataLoop(long start, long end,
                             TreeMap<Long, MarketDataObject> time2MarketData,
                             FundingOnnxInferenceManager aiBrain,
                             ConcurrentHashMap<String, Short> symbolMap,
                             boolean isWarmup,
                             FundingDataCollectionManager.FundingFeatureExtractorV2 extractor
    ) {
        long currentTime = start;

        while (currentTime < end) {
            // Đọc dữ liệu theo block 1 ngày để tối ưu hóa việc kéo data từ DB
            int minutesToRead = 1440;
            if (currentTime + minutesToRead * Utils.TIME_MINUTE > end) {
                minutesToRead = (int) ((end - currentTime) / Utils.TIME_MINUTE) + 1;
            }

            // Kiểm tra resume: Xem phút nào đã có data thì đánh dấu để skip
//            Set<Long> existingTimestamps = new HashSet<>();
//            if (!isWarmup) {
//                List<Long> timestampsToCheck = new ArrayList<>();
//                for(int i=0; i<minutesToRead; i++) timestampsToCheck.add(currentTime + i * Utils.TIME_MINUTE);
//                existingTimestamps = DataManagerAerospikeFloatSim.checkExistingFundingPredictions(timestampsToCheck);
//            }

            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, minutesToRead);

            if (time2Tickers.isEmpty()) {
                currentTime += minutesToRead * Utils.TIME_MINUTE;
                continue;
            }

            for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                long time = timeEntry.getKey();
                Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                // 1. CẬP NHẬT LỊCH SỬ (Bắt buộc làm hàng phút để duy trì tính tịnh tiến của Features)
                extractor.updateMarketHistory(symbol2Ticker);

                // 2. KIỂM TRA ĐIỀU KIỆN DỪNG/BỎ QUA
//                if (isWarmup || existingTimestamps.contains(time)) continue;
                if (isWarmup) continue;

                // 3. TRÍCH XUẤT ĐẶC TRƯNG - DÙNG CHO TOÀN BỘ COIN (NO FILTER)
                final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);
                List<PrepareData> batchInput = symbol2Ticker.keySet().parallelStream()
                        .map(symbol -> {
                            try {
                                Short symId = symbolMap.get(symbol);
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);

                                // Chỉ kiểm tra cơ bản nến có dữ liệu hay không (tránh lỗi chia cho 0 trong AI)
                                if (symId == null || ticker == null || !Utils.isTickerAvailable(ticker)) return null;

                                OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                                        Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                                );
                                dummyOrder.lastEntry = ticker.priceClose;

                                // Tính toán bộ Features (Không áp dụng filter momentum/rate ở đây)
                                FundingMarketFeatures features = extractor.extractFeatures(
                                        time, dummyOrder, symbol2Ticker, time2MarketData.get(time), basket
                                );

                                if (features != null) {
                                    return new PrepareData(symId, aiBrain.extractFeaturesToArray(features));
                                }
                            } catch (Exception e) {
                                LOG.error("Lỗi extract symbol " + symbol + " tại " + time, e);
                            }
                            return null;
                        })
                        .filter(Objects::nonNull)
                        .collect(Collectors.toList());

                if (batchInput.isEmpty()) continue;

                // 4. PREDICTION THEO BATCH (Tăng tốc độ bằng cách dự báo 20 coin một nhịp)
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
                        LOG.error("Lỗi AI Inference tại " + time, e);
                    }
                }

                // 5. LƯU KẾT QUẢ VÀO AEROSPIKE
                if (!finalResults.isEmpty()) {
                    DataManagerAerospikeFloatSim.saveFundingPredictions1M(time, finalResults);
                }
            }

            // In log tiến độ và dọn rác bộ nhớ sau mỗi block 1 ngày
            if (!isWarmup) {
                LOG.info("✅ Đã xử lý xong: {} | Last Key: {}",
                        Utils.normalizeDateYYYYMMDD(currentTime),
                        Utils.normalizeDateYYYYMMDDHHmm(time2Tickers.lastKey()));
                System.gc();
            }

            currentTime = time2Tickers.lastKey() + Utils.TIME_MINUTE;
            time2Tickers = null;
        }
    }
}