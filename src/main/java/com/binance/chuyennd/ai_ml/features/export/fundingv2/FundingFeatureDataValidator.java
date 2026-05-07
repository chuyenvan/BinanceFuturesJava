package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager;
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

import java.io.*;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.zip.GZIPInputStream;

public class FundingFeatureDataValidator {
    private static final Logger LOG = LoggerFactory.getLogger(FundingFeatureDataValidator.class);

    public static void main(String[] args) throws Exception {
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "4");
        DataManagerAerospikeFloatSim.setThreadCount(4);

        // Chọn ngày kiểm tra
        String targetDay = "20210103";
        long targetStartTs = Utils.sdfFile.parse(targetDay).getTime();

        // 🔥 SỬA LỖI WARMUP: Lùi đúng 3 ngày (từ 29/12) y hệt code Export
        long warmupStartTs = targetStartTs - (3 * 24 * 60 * 60 * 1000L);
        long endTs = targetStartTs + (24 * 60 * 60 * 1000L);

        // 🔥 KIỂM TRA 10 PHÚT LIÊN TIẾP (Ví dụ từ 08:30 đến 08:39 sáng)
        List<Long> randomTimestamps = new ArrayList<>();
        // Giả sử ta lấy mốc bắt đầu là 08:30 (8 * 60 + 30 = 510 phút tính từ đầu ngày)
        long startTimeBlock = targetStartTs + (510 * 60000L);

        for (int i = 0; i < 10; i++) {
            randomTimestamps.add(startTimeBlock + (i * 60000L));
        }
        long maxTargetTime = Collections.max(randomTimestamps);

        LOG.info("🎯 DANH SÁCH 10 MỐC THỜI GIAN SẼ KIỂM TOÁN:");
        for (Long t : randomTimestamps) LOG.info("- " + Utils.normalizeDateYYYYMMDDHHmm(t));

        // =========================================================================
        // 🔎 BƯỚC MỚI: ĐỌC DỮ LIỆU FEATURE TỪ FILE BIN.GZ
        // =========================================================================
        String featureFilePath = "features_export_python/features_2021.bin.gz";
        LOG.info("📂 Đang trích xuất Feature từ file {}...", featureFilePath);
        Map<Long, Map<Short, float[]>> fileFeaturesMap = loadTargetFeaturesFromFile(featureFilePath, randomTimestamps, maxTargetTime);
        LOG.info("✅ Đã load xong Feature từ file gốc.");

        String modelPath = "models_funding/Funding_Classifier_Final_Fixed.onnx";

        LOG.info("📥 Đang tải Market Data & Symbol Mapper...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);

        try (FundingOnnxInferenceManager aiBrain = new FundingOnnxInferenceManager(modelPath)) {
            FundingFeatureExtractorV2 extractor = new FundingFeatureExtractorV2();

            long currentTime = warmupStartTs;
            int totalMatchCount = 0;
            int totalCheckCount = 0;

            LOG.info("🔥 BẮT ĐẦU CHẠY WARMUP TỪ " + Utils.normalizeDateYYYYMMDDHHmm(warmupStartTs) + "...");

            while (currentTime <= endTs) {
                int minutesToRead = 1440;
                if (currentTime + minutesToRead * Utils.TIME_MINUTE > endTs) {
                    minutesToRead = (int) ((endTs - currentTime) / Utils.TIME_MINUTE) + 1;
                }
                if (minutesToRead <= 0) break;

                TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentTime, minutesToRead);
                if (time2Tickers.isEmpty()) {
                    currentTime += minutesToRead * Utils.TIME_MINUTE;
                    continue;
                }

                for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                    long time = timeEntry.getKey();
                    Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                    extractor.updateMarketHistory(symbol2Ticker);

                    if (randomTimestamps.contains(time)) {
                        LOG.info("=========================================");
                        LOG.info("🔎 ĐANG KIỂM TOÁN MỐC: " + Utils.normalizeDateYYYYMMDDHHmm(time));

                        Map<Short, float[]> dbPredictions = DataManagerAerospikeFloatSim.getFundingPredictionAtTime(time);
                        Map<Short, float[]> fileFeaturesAtTime = fileFeaturesMap.get(time);
                        final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);

                        int minuteMatchCount = 0;
                        int minuteTotalCheck = 0;

                        for (Map.Entry<String, KlineObjectSimple> tickerEntry : symbol2Ticker.entrySet()) {
                            String symbol = tickerEntry.getKey();
                            Short symId = symbolMap.get(symbol);
                            KlineObjectSimple ticker = tickerEntry.getValue();

                            if (symId == null || !Utils.isTickerAvailable(ticker)) continue;

                            OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                                    OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                                    Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                            );
                            dummyOrder.lastEntry = ticker.priceClose;

                            FundingMarketFeatures features = extractor.extractFeatures(
                                    time, dummyOrder, symbol2Ticker, time2MarketData.get(time), basket
                            );

                            if (features != null) {
                                float[] featureArray = aiBrain.extractFeaturesToArray(features);

                                // --- KIỂM TRA FEATURE TỪ FILE ---
                                if (fileFeaturesAtTime != null && fileFeaturesAtTime.containsKey(symId)) {
                                    float[] fileFeatures = fileFeaturesAtTime.get(symId);
                                    boolean featureMatch = true;
                                    for (int k = 0; k < 21; k++) {
                                        if (Math.abs(featureArray[k] - fileFeatures[k]) > 0.00001f) {
                                            LOG.error("❌ LỆCH FEATURE [{} - {}] Cột [{}]: Java đang chạy = {} | Trong File.bin = {}",
                                                    symbol, Utils.normalizeDateYYYYMMDDHHmm(time), k, featureArray[k], fileFeatures[k]);
                                            featureMatch = false;
                                        }
                                    }
                                    if(!featureMatch) continue; // Bỏ qua check Predict nếu feature đã sai từ đầu
                                } else {
                                    LOG.warn("⚠️ Không tìm thấy Symbol {} trong file Feature gốc!", symbol);
                                }

                                // --- KIỂM TRA PREDICT ---
                                float javaPred = 0;
                                try {
                                    List<float[]> batchInput = Collections.singletonList(featureArray);
                                    List<float[]> javaResult = aiBrain.predictBatch(batchInput);
                                    if (javaResult != null && !javaResult.isEmpty()) javaPred = javaResult.get(0)[0];
                                } catch (Exception e) {}

                                if (dbPredictions != null && dbPredictions.containsKey(symId)) {
                                    float pyPred = dbPredictions.get(symId)[0];
                                    minuteTotalCheck++;
                                    totalCheckCount++;

                                    if (Math.abs(javaPred - pyPred) < 0.0001f) {
                                        minuteMatchCount++;
                                        totalMatchCount++;
                                    } else {
                                        LOG.error(String.format("❌ LỆCH PREDICT [%s]: Java = %.6f | Python(AS) = %.6f", symbol, javaPred, pyPred));
                                    }
                                }
                            }
                        }
                        LOG.info("✅ KẾT QUẢ MỐC {}: Khớp {} / {} symbols", Utils.normalizeDateYYYYMMDDHHmm(time), minuteMatchCount, minuteTotalCheck);
                    }
                }
                currentTime = time2Tickers.lastKey() + Utils.TIME_MINUTE;
            }

            LOG.info("=========================================================");
            LOG.info("🏁 TỔNG KẾT KIỂM TOÁN: KHỚP {} / {} BẢN GHI", totalMatchCount, totalCheckCount);
        }
        System.exit(0);
    }

    /**
     * Helper: Đọc file .bin.gz và trích xuất đúng các mốc thời gian cần tìm
     */
    private static Map<Long, Map<Short, float[]>> loadTargetFeaturesFromFile(String filePath, List<Long> targetTimes, long maxTime) {
        Map<Long, Map<Short, float[]>> result = new HashMap<>();
        try (DataInputStream dis = new DataInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(filePath))))) {
            while (true) {
                try {
                    long time = dis.readLong();
                    short symId = dis.readShort();
                    float[] features = new float[21];
                    for (int i = 0; i < 21; i++) {
                        features[i] = dis.readFloat();
                    }

                    if (targetTimes.contains(time)) {
                        result.computeIfAbsent(time, k -> new HashMap<>()).put(symId, features);
                    }
                    // Tối ưu: Nếu file đã đọc vượt qua mốc cuối cùng cần tìm thì dừng (đỡ tốn công đọc tiếp)
                    if (time > maxTime) break;

                } catch (EOFException e) { break; }
            }
        } catch (Exception e) {
            LOG.error("Lỗi khi đọc file binary: " + e.getMessage());
        }
        return result;
    }
}