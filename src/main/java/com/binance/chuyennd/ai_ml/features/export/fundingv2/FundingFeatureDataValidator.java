package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager;
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

import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.zip.GZIPInputStream;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class FundingFeatureDataValidator {
    private static final Logger LOG = LoggerFactory.getLogger(FundingFeatureDataValidator.class);
    private static final float ALLOWED_ERROR_MARGIN = 0.01f;
    private static final String FEATURES_DIR = "features_export_python/";
    private static final SimpleDateFormat sdfFile = new SimpleDateFormat("yyyyMMdd");
    private static final String MODEL_PATH = "models_funding/Funding_Classifier_Final_Fixed.onnx";

    private static class FileTask {
        String filePath;
        long startTs;
        long endTs;
        List<Long> randomTestTimes = new ArrayList<>();
        Map<Long, Map<Short, float[]>> fileFeaturesMap = new HashMap<>();

        long matchFeatureCount = 0;
        long matchPredictCount = 0;
        long totalCheckCount = 0;
        long totalFeatureCheckCount = 0;
    }

    public static void main(String[] args) throws Exception {
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "4");
        DataManagerAerospikeFloatSim.setThreadCount(4);
        new FundingFeatureDataValidator().runValidation();
    }

    public void runValidation() throws Exception {
        LOG.info("🔍 ĐANG TÌM KIẾM CÁC FILE FEATURES TRONG {}", FEATURES_DIR);
        File dir = new File(FEATURES_DIR);
        File[] files = dir.listFiles((d, name) -> name.startsWith("features_") && name.endsWith(".bin.gz"));

        if (files == null || files.length == 0) {
            LOG.error("❌ Không tìm thấy file features nào!");
            return;
        }

        List<FileTask> tasks = new ArrayList<>();
        Pattern pattern = Pattern.compile("features_(\\d{8})_to_(\\d{8})\\.bin\\.gz");
        Random rand = new Random(System.currentTimeMillis());

        for (File f : files) {
            Matcher m = pattern.matcher(f.getName());
            if (m.find()) {
                FileTask task = new FileTask();
                task.filePath = f.getAbsolutePath();
                task.startTs = sdfFile.parse(m.group(1)).getTime();
                task.endTs = sdfFile.parse(m.group(2)).getTime() - Utils.TIME_MINUTE;

                long range = task.endTs - task.startTs;
                for (int i = 0; i < 3; i++) {
                    long randomOffset = (long) (rand.nextDouble() * range);
                    long rawTime = task.startTs + randomOffset;
                    long testTime = (rawTime / 60000L) * 60000L;
                    task.randomTestTimes.add(testTime);
                }
                Collections.sort(task.randomTestTimes);
                tasks.add(task);
            }
        }

        tasks.sort(Comparator.comparingLong(t -> t.startTs));
        LOG.info("✅ TÌM THẤY {} FILES. SẼ TIẾN HÀNH LOAD CUỐN CHIẾU TỪNG FILE...", tasks.size());

        LOG.info("📥 Đang tải Market Data & Symbol Mapper...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);

        long globalWarmupTs = tasks.get(0).startTs - (48 * 3600000L);
        long globalEndTs = tasks.get(tasks.size() - 1).endTs;

        LOG.info("🚀 BẮT ĐẦU CHẠY VALIDATION LIÊN TỤC TỪ WARMUP ĐẾN KẾT THÚC!");

        CoinRankManager.getInstance().resetCache();
        HistoryManager.getInstance().resetCache();

        try (FundingOnnxInferenceManager aiBrain = new FundingOnnxInferenceManager(MODEL_PATH)) {
            FundingDataCollectionManager.FundingFeatureExtractorV2 extractor = new FundingDataCollectionManager.FundingFeatureExtractorV2();
            long currentReadTs = globalWarmupTs;

            int taskIndex = 0;
            FileTask currentTask = tasks.get(0);

            long maxTestTime = Collections.max(currentTask.randomTestTimes);
            LOG.info("📂 Đang trích xuất 3 mốc test từ File: {}", new File(currentTask.filePath).getName());
            currentTask.fileFeaturesMap = loadTargetFeaturesFromFile(currentTask.filePath, currentTask.randomTestTimes, maxTestTime);
            LOG.info("   - Sẽ test ở 3 mốc: {}", getFormattedTimes(currentTask.randomTestTimes));

            long globalTotalPredictMatch = 0;
            long globalTotalPredictCheck = 0;
            long globalTotalFeatureCheck = 0;
            long globalTotalFeatureMatch = 0;

            while (currentReadTs <= globalEndTs) {
                int minutesToRead = 1440;
                if (currentReadTs + minutesToRead * Utils.TIME_MINUTE > globalEndTs) {
                    minutesToRead = (int) ((globalEndTs - currentReadTs) / Utils.TIME_MINUTE) + 1;
                }
                if (minutesToRead <= 0) break;

                TreeMap<Long, Map<String, KlineObjectSimple>> chunkData = DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentReadTs, minutesToRead);

                if (chunkData != null && !chunkData.isEmpty()) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : chunkData.entrySet()) {
                        long time = entry.getKey();
                        Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();

                        extractor.updateMarketHistory(symbol2Ticker);
                        final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);

                        if (time < tasks.get(0).startTs) continue;

                        if (time > currentTask.endTs && taskIndex < tasks.size() - 1) {
                            printTaskSummary(currentTask);
                            currentTask.fileFeaturesMap.clear();
                            taskIndex++;
                            currentTask = tasks.get(taskIndex);

                            long nextMaxTestTime = Collections.max(currentTask.randomTestTimes);
                            LOG.info("📂 Đang trích xuất 3 mốc test từ File: {}", new File(currentTask.filePath).getName());
                            currentTask.fileFeaturesMap = loadTargetFeaturesFromFile(currentTask.filePath, currentTask.randomTestTimes, nextMaxTestTime);
                            LOG.info("   - Sẽ test ở 3 mốc: {}", getFormattedTimes(currentTask.randomTestTimes));
                        }

                        if (currentTask.randomTestTimes.contains(time)) {
                            LOG.info("=========================================");
                            LOG.info("🔎 ĐANG KIỂM TOÁN MỐC: " + Utils.normalizeDateYYYYMMDDHHmm(time));

                            Map<Short, float[]> fileFeaturesAtTime = currentTask.fileFeaturesMap.get(time);
                            Map<Short, float[]> dbPredictions = DataManagerAerospikeFloatSim.getFundingPredictionAtTime(time);

                            int minuteMatchPredict = 0;
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
                                    float[] javaArray = convertFeaturesToArray(features);
                                    boolean featureMatch = true;

                                    if (fileFeaturesAtTime != null && fileFeaturesAtTime.containsKey(symId)) {
                                        float[] fileArray = fileFeaturesAtTime.get(symId);
                                        for (int k = 0; k < 21; k++) {
                                            currentTask.totalFeatureCheckCount++;
                                            globalTotalFeatureCheck++;

                                            float javaVal = javaArray[k];
                                            float fileVal = fileArray[k];

                                            // 🔥 FIX BUGS ĐẾM SỐ 0
                                            if (javaVal == 0 && fileVal == 0) {
                                                currentTask.matchFeatureCount++;
                                                globalTotalFeatureMatch++;
                                                continue;
                                            }

                                            float diffPercent = (fileVal != 0) ? Math.abs((javaVal - fileVal) / fileVal) : 1.0f;
                                            if (diffPercent > ALLOWED_ERROR_MARGIN && Math.abs(javaVal - fileVal) > 0.0001) {
                                                LOG.error("❌ LỆCH FEATURE [{} - {}] Cột [{}]: Java = {} | File = {} | Lệch = {}%",
                                                        symbol, Utils.normalizeDateYYYYMMDDHHmm(time), k, javaVal, fileVal, (diffPercent * 100));
                                                featureMatch = false;
                                            } else {
                                                currentTask.matchFeatureCount++;
                                                globalTotalFeatureMatch++;
                                            }
                                        }
                                    }

                                    if (!featureMatch) continue;

                                    float javaPred = 0;
                                    try {
                                        List<float[]> batchInput = Collections.singletonList(javaArray);
                                        List<float[]> javaResult = aiBrain.predictBatch(batchInput);
                                        if (javaResult != null && !javaResult.isEmpty()) javaPred = javaResult.get(0)[0];
                                    } catch (Exception e) {}

                                    if (dbPredictions != null && dbPredictions.containsKey(symId)) {
                                        float pyPred = dbPredictions.get(symId)[0];
                                        currentTask.totalCheckCount++;
                                        globalTotalPredictCheck++;
                                        minuteTotalCheck++;

                                        float predDiffPercent = (pyPred != 0) ? Math.abs((javaPred - pyPred) / pyPred) : 1.0f;
                                        if ((javaPred == 0 && pyPred == 0) || predDiffPercent <= ALLOWED_ERROR_MARGIN) {
                                            currentTask.matchPredictCount++;
                                            globalTotalPredictMatch++;
                                            minuteMatchPredict++;
                                        } else {
                                            LOG.error(String.format("❌ LỆCH PREDICT [%s]: Java = %.6f | Python(AS) = %.6f | Lệch = %.4f%%",
                                                    symbol, javaPred, pyPred, predDiffPercent * 100));
                                        }
                                    }
                                }
                            }
                            LOG.info("✅ KẾT QUẢ MỐC {}: Khớp Predict {} / {} symbols", Utils.normalizeDateYYYYMMDDHHmm(time), minuteMatchPredict, minuteTotalCheck);
                        }
                    }
                }
                currentReadTs += minutesToRead * Utils.TIME_MINUTE;
            }

            printTaskSummary(currentTask);

            LOG.info("=========================================================");
            LOG.info("🏆 TỔNG KẾT TOÀN CHIẾN DỊCH KIỂM TOÁN:");
            LOG.info("   - Tổng số files đã test: {}", tasks.size());
            LOG.info("   - TỔNG FEATURES ĐÃ SO SÁNH: {} (Khớp: {})", globalTotalFeatureCheck, globalTotalFeatureMatch);
            LOG.info("   - TỔNG PREDICTIONS KIỂM TRA: {}", globalTotalPredictCheck);
            LOG.info("   - TỔNG PREDICTIONS KHỚP: {} / {} (Tỷ lệ: {}%)",
                    globalTotalPredictMatch, globalTotalPredictCheck,
                    globalTotalPredictCheck > 0 ? String.format("%.2f", (float)globalTotalPredictMatch/globalTotalPredictCheck * 100) : "N/A");
            LOG.info("=========================================================");

            // --- BỔ SUNG: IN RA CÁC FILE LỆCH ---
            List<String> badFiles = new ArrayList<>();
            for (FileTask t : tasks) {
                long featDiff = t.totalFeatureCheckCount - t.matchFeatureCount;
                long predDiff = t.totalCheckCount - t.matchPredictCount;
                if (featDiff > 0 || predDiff > 0) {
                    badFiles.add(String.format("%s (Lệch Feature: %d, Lệch Predict: %d)", new File(t.filePath).getName(), featDiff, predDiff));
                }
            }

            if (!badFiles.isEmpty()) {
                LOG.warn("⚠️ DANH SÁCH CÁC FILE BỊ LỆCH DỮ LIỆU CẦN KIỂM TRA LẠI:");
                for (String bf : badFiles) {
                    LOG.warn("   -> {}", bf);
                }
            } else {
                LOG.info("🎉 HOÀN HẢO! TẤT CẢ CÁC FILE ĐỀU KHỚP NHAU 100%!");
            }

        }
        System.exit(0);
    }

    private void printTaskSummary(FileTask task) {
        LOG.info("---------------------------------------------------------");
        LOG.info("📋 TỔNG KẾT FILE: {}", new File(task.filePath).getName());
        LOG.info("   - Features kiểm tra: {} (Khớp {})", task.totalFeatureCheckCount, task.matchFeatureCount);
        LOG.info("   - Predicts kiểm tra: {} (Khớp {})", task.totalCheckCount, task.matchPredictCount);
        LOG.info("---------------------------------------------------------");
    }

    private static Map<Long, Map<Short, float[]>> loadTargetFeaturesFromFile(String filePath, List<Long> targetTimes, long maxTime) {
        Map<Long, Map<Short, float[]>> result = new HashMap<>();
        boolean isGzip = filePath.endsWith(".gz");
        try (InputStream is = new FileInputStream(filePath);
             BufferedInputStream bis = new BufferedInputStream(is, 1024 * 1024);
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
            LOG.error("Lỗi khi đọc file binary " + filePath, e);
        }
        return result;
    }

    private float[] convertFeaturesToArray(FundingMarketFeatures f) {
        return new float[]{
                f.btcMomentum1H, f.btcMomentum4H, f.btcMomentum24H, f.btcDominance, f.marketBreadthStrength,
                f.rateDown15MAvg, f.momentum1H, f.momentum4H, f.momentum24H, f.rsi1H, f.distFromLow24H, f.volatilityShock,
                f.basketMomentum15M, f.basketMomentum1H, f.basketMomentum24H, f.basketRsi14, f.basketVolSpike,
                f.coinFundingRate, f.basketFundingAvg, f.fundingRateAvg24H, f.fundingRateTrend
        };
    }

    private String getFormattedTimes(List<Long> times) {
        StringBuilder sb = new StringBuilder();
        for (long t : times) sb.append(Utils.normalizeDateYYYYMMDDHHmm(t)).append(", ");
        return sb.length() > 0 ? sb.substring(0, sb.length() - 2) : "";
    }
}