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
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.GZIPInputStream;

public class FundingFeatureDataValidatorByInput {
    private static final Logger LOG = LoggerFactory.getLogger(FundingFeatureDataValidatorByInput.class);

    // Giữ sai số 1%
    private static final float ALLOWED_ERROR_MARGIN = 0.01f;
    private static final String FEATURES_DIR = "features_export_python/";

    public static void main(String[] args) throws Exception {
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "4");
        DataManagerAerospikeFloatSim.setThreadCount(4);

        // Chỉ nhận 1 tham số là Ngày cần test
        String targetDay = "20260104";
        if (args.length >= 1) {
            targetDay = args[0];
        }

        long targetStartTs = Utils.sdfFile.parse(targetDay).getTime();
        long endTs = targetStartTs + (24 * 60 * 60 * 1000L); // Giới hạn quét trong 24h của ngày đó

        // ========================================================
        // 1. TỰ ĐỘNG TÌM FILE PHÙ HỢP VỚI NGÀY TARGET
        // ========================================================
        String featureFilePath = null;
        File dir = new File(FEATURES_DIR);
        File[] files = dir.listFiles((d, name) -> name.startsWith("features_") && name.endsWith(".bin.gz"));
        Pattern pattern = Pattern.compile("features_(\\d{8})_to_(\\d{8})\\.bin\\.gz");

        if (files != null) {
            for (File f : files) {
                Matcher m = pattern.matcher(f.getName());
                if (m.find()) {
                    long fStart = Utils.sdfFile.parse(m.group(1)).getTime();
                    long fEnd = Utils.sdfFile.parse(m.group(2)).getTime();

                    // Nếu targetStartTs nằm trong khoảng của file này
                    if (targetStartTs >= fStart && targetStartTs < fEnd) {
                        featureFilePath = f.getAbsolutePath();
                        break;
                    }
                }
            }
        }

        if (featureFilePath == null) {
            LOG.error("❌ KHÔNG TÌM THẤY FILE NÀO CHỨA DỮ LIỆU CỦA NGÀY: {}", targetDay);
            System.exit(1);
        }

        LOG.info("🎯 Tìm thấy file chứa ngày {}: {}", targetDay, new File(featureFilePath).getName());

        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(targetStartTs);
        int targetYear = cal.get(Calendar.YEAR);

        // 🔥 ĐỒNG BỘ WARMUP: Quét từ đầu năm để nuôi CoinRank chuẩn xác nhất

        long warmupStartTs = targetStartTs - (48 * 3600000L);

        // Random 10 thời điểm trong ngày đó để test
        List<Long> randomTimestamps = new ArrayList<>();
        long startTimeBlock = targetStartTs + (510 * 60000L);
        for (int i = 0; i < 10; i++) {
            // Ép về đúng phút chẵn
            long testTime = ((startTimeBlock + (i * 60000L)) / 60000L) * 60000L;
            randomTimestamps.add(testTime);
        }
        long maxTargetTime = Collections.max(randomTimestamps);

        LOG.info("📂 Đang trích xuất Feature từ file {}...", new File(featureFilePath).getName());
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
            long totalMatchCount = 0;
            long totalCheckCount = 0;

            // Biến đếm cho Feature
            long totalFeatureCheckCount = 0;
            long matchFeatureCount = 0;

            LOG.info("🔥 BẮT ĐẦU CHẠY WARMUP TỪ " + Utils.normalizeDateYYYYMMDDHHmm(warmupStartTs) + " ĐỂ ĐỒNG BỘ TRẠNG THÁI...");

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

                    // 2. CHẶN NẾU ĐANG WARMUP
                    if (time < targetStartTs) continue;

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

                        // 4. PHẢI GỌI EXTRACT LIÊN TỤC MỖI PHÚT ĐỂ NUÔI CACHE
                        FundingMarketFeatures features = extractor.extractFeatures(
                                time, dummyOrder, symbol2Ticker, time2MarketData.get(time), basket
                        );

                        // 5. CHỈ THỰC SỰ ĐỐI CHIẾU NẾU LÀ PHÚT TEST
                        if (isTestMinute && features != null) {
                            float[] featureArray = aiBrain.extractFeaturesToArray(features);

                            if (fileFeaturesAtTime != null && fileFeaturesAtTime.containsKey(symId)) {
                                float[] fileFeatures = fileFeaturesAtTime.get(symId);
                                for (int k = 0; k < 21; k++) {
                                    totalFeatureCheckCount++;

                                    float javaVal = featureArray[k];
                                    float fileVal = fileFeatures[k];

                                    // SỬA LỖI ĐẾM SỐ 0
                                    if (javaVal == 0 && fileVal == 0) {
                                        matchFeatureCount++;
                                        continue;
                                    }

                                    float diffPercent = (fileVal != 0) ? Math.abs((javaVal - fileVal) / fileVal) : 1.0f;
                                    if (diffPercent > ALLOWED_ERROR_MARGIN && Math.abs(javaVal - fileVal) > 0.0001) {
                                        LOG.error("❌ LỆCH FEATURE [{} - {}] Cột [{}]: Java = {} | File.bin = {} | Lệch = {}%",
                                                symbol, Utils.normalizeDateYYYYMMDDHHmm(time), k, javaVal, fileVal, (diffPercent * 100));
                                    } else {
                                        matchFeatureCount++;
                                    }
                                }
                            }

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

                                float predDiffPercent = (pyPred != 0) ? Math.abs((javaPred - pyPred) / pyPred) : 1.0f;
                                if ((javaPred == 0 && pyPred == 0) || predDiffPercent <= ALLOWED_ERROR_MARGIN) {
                                    minuteMatchCount++;
                                    totalMatchCount++;
                                } else {
                                    LOG.error(String.format("❌ LỆCH PREDICT [%s]: Java = %.6f | Python(AS) = %.6f | Lệch = %.4f%%",
                                            symbol, javaPred, pyPred, predDiffPercent * 100));
                                }
                            }
                        }
                    }
                    if (isTestMinute) LOG.info("✅ KẾT QUẢ MỐC {}: Khớp Predict {} / {} symbols", Utils.normalizeDateYYYYMMDDHHmm(time), minuteMatchCount, minuteTotalCheck);
                }
                currentTime = time2Tickers.lastKey() + Utils.TIME_MINUTE;
            }

            LOG.info("=========================================================");
            LOG.info("🏁 TỔNG KẾT KIỂM TOÁN DỮ LIỆU NGÀY {}:", targetDay);
            LOG.info("   - File đã dùng: {}", new File(featureFilePath).getName());
            LOG.info("   - Tổng Feature so sánh: {} (Khớp {})", totalFeatureCheckCount, matchFeatureCount);
            LOG.info("   - Tổng Predict so sánh: {} (Khớp {})", totalCheckCount, totalMatchCount);
            LOG.info("   - Tỷ lệ khớp Feature: {}%",
                    totalFeatureCheckCount > 0 ? String.format("%.2f", (float)matchFeatureCount/totalFeatureCheckCount * 100) : "N/A");
            LOG.info("   - Tỷ lệ khớp Predict: {}%",
                    totalCheckCount > 0 ? String.format("%.2f", (float)totalMatchCount/totalCheckCount * 100) : "N/A");
            LOG.info("=========================================================");
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
                        dis.skipBytes(86);
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