package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
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

    // Giữ sai số 1%
    private static final float ALLOWED_ERROR_MARGIN = 0.01f;

    public static void main(String[] args) throws Exception {
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "4");
        DataManagerAerospikeFloatSim.setThreadCount(4);

        String targetDay = "20260104";
        String featureFilePath = "features_export_python/features_2026.bin.gz";

        if (args.length >= 2) {
            targetDay = args[0];
            featureFilePath = args[1];
        }

        long targetStartTs = Utils.sdfFile.parse(targetDay).getTime();

        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(targetStartTs);
        int targetYear = cal.get(Calendar.YEAR);

        // 🔥 ĐỒNG BỘ 1: SỬ DỤNG WARMUP 48 TIẾNG (Y HỆT TOOL EXPORT)
        long startOfYearTs = Utils.sdfFile.parse(targetYear + "0101-0000").getTime();
        long warmupStartTs = startOfYearTs - (48 * 3600000L);
        long endTs = targetStartTs + (24 * 60 * 60 * 1000L);

        List<Long> randomTimestamps = new ArrayList<>();
        long startTimeBlock = targetStartTs + (510 * 60000L);
        for (int i = 0; i < 10; i++) randomTimestamps.add(startTimeBlock + (i * 60000L));
        long maxTargetTime = Collections.max(randomTimestamps);

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

                    // 1. LUÔN CẬP NHẬT LỊCH SỬ
                    extractor.updateMarketHistory(symbol2Ticker);

                    // 2. CHẶN NẾU ĐANG WARMUP (Y hệt Export)
                    if (time < startOfYearTs) continue;

                    // 3. 🔥 ĐỒNG BỘ 2: GỌI RANK MỖI PHÚT ĐỂ NUÔI STATE CỦA COINRANKMANAGER
                    final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);

                    boolean isTestMinute = randomTimestamps.contains(time);
                    if (isTestMinute) {
                        LOG.info("=========================================");
                        LOG.info("🔎 ĐANG KIỂM TOÁN MỐC: " + Utils.normalizeDateYYYYMMDDHHmm(time));
                    }

                    Map<Short, float[]> dbPredictions = isTestMinute ? DataManagerAerospikeFloatSim.getFundingPredictionAtTime(time) : null;
                    Map<Short, float[]> fileFeaturesAtTime = isTestMinute ? fileFeaturesMap.get(time) : null;

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

                        // 4. 🔥 ĐỒNG BỘ 3: PHẢI GỌI EXTRACT LIÊN TỤC MỖI PHÚT ĐỂ NUÔI CACHE BÊN TRONG (Dù không phải phút test)
                        FundingMarketFeatures features = extractor.extractFeatures(
                                time, dummyOrder, symbol2Ticker, time2MarketData.get(time), basket
                        );

                        // 5. CHỈ THỰC SỰ ĐỐI CHIẾU NẾU LÀ PHÚT TEST
                        if (isTestMinute && features != null) {
                            float[] featureArray = aiBrain.extractFeaturesToArray(features);

//                            boolean featureMatch = true;
                            if (fileFeaturesAtTime != null && fileFeaturesAtTime.containsKey(symId)) {
                                float[] fileFeatures = fileFeaturesAtTime.get(symId);
                                for (int k = 0; k < 21; k++) {
                                    float javaVal = featureArray[k];
                                    float fileVal = fileFeatures[k];
                                    if (javaVal == 0 && fileVal == 0) continue;

                                    float diffPercent = (fileVal != 0) ? Math.abs((javaVal - fileVal) / fileVal) : 1.0f;
                                    if (diffPercent > ALLOWED_ERROR_MARGIN) {
                                        LOG.error("❌ LỆCH FEATURE [{} - {}] Cột [{}]: Java = {} | File.bin = {} | Lệch = {}%",
                                                symbol, Utils.normalizeDateYYYYMMDDHHmm(time), k, javaVal, fileVal, (diffPercent * 100));
//                                        featureMatch = false;
                                    }
                                }
                            }

//                            if(!featureMatch) continue;

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

                                if (javaPred == 0 && pyPred == 0) {
                                    minuteMatchCount++;
                                    totalMatchCount++;
                                } else {
                                    float predDiffPercent = (pyPred != 0) ? Math.abs((javaPred - pyPred) / pyPred) : 1.0f;
                                    if (predDiffPercent <= ALLOWED_ERROR_MARGIN) {
                                        minuteMatchCount++;
                                        totalMatchCount++;
                                    } else {
                                        LOG.error(String.format("❌ LỆCH PREDICT [%s]: Java = %.6f | Python(AS) = %.6f | Lệch = %.4f%%",
                                                symbol, javaPred, pyPred, predDiffPercent * 100));
                                    }
                                }
                            }
                        }
                    }
                    if (isTestMinute) LOG.info("✅ KẾT QUẢ MỐC {}: Khớp {} / {} symbols", Utils.normalizeDateYYYYMMDDHHmm(time), minuteMatchCount, minuteTotalCheck);
                }
                currentTime = time2Tickers.lastKey() + Utils.TIME_MINUTE;
            }

            LOG.info("=========================================================");
            LOG.info("🏁 TỔNG KẾT KIỂM TOÁN: KHỚP {} / {} BẢN GHI", totalMatchCount, totalCheckCount);
        }
        System.exit(0);
    }
    private static Map<Long, Map<Short, float[]>> loadTargetFeaturesFromFile(String filePath, List<Long> targetTimes, long maxTime) {
        Map<Long, Map<Short, float[]>> result = new HashMap<>();
        boolean isGzip = filePath.endsWith(".gz");
        try (InputStream is = new FileInputStream(filePath);
             BufferedInputStream bis = new BufferedInputStream(is, 65536);
             DataInputStream dis = new DataInputStream(isGzip ? new GZIPInputStream(bis) : bis)) {
            while (true) {
                try {
                    long time = dis.readLong();
                    if (time > maxTime) break;
                    if (targetTimes.contains(time)) {
                        short symId = dis.readShort();
                        float[] features = new float[21];
                        for (int i = 0; i < 21; i++) features[i] = dis.readFloat();
                        result.computeIfAbsent(time, k -> new HashMap<>()).put(symId, features);
                    } else {
                        dis.skipBytes(86); // Tối ưu: Bỏ qua các byte không cần thiết
                    }
                } catch (EOFException e) {
                    break;
                }
            }
        } catch (Exception e) {
            LOG.error("Lỗi khi đọc file binary: " + e.getMessage());
        }
        return result;
    }
}