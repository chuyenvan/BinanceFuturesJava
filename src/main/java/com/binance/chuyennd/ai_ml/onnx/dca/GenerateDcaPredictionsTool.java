package com.binance.chuyennd.ai_ml.onnx.dca;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.dca.DcaFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.dca.DcaMarketFeatures;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

public class GenerateDcaPredictionsTool {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateDcaPredictionsTool.class);

    public static void main(String[] args) throws Exception {
        // Resume từ điểm chết
        String startTimeStr = "2021-11-22 10:00:00";
        long startTime = Utils.sdfFile.parse(startTimeStr).getTime();
        long endTime = System.currentTimeMillis();

        LOG.info("🔥 STARTING GENERATION (BATCH MODE - NO LEAK)...");
        new GenerateDcaPredictionsTool().generateToAerospike(startTime, endTime);
    }

    // Class phụ để giữ cặp ID và Features trước khi đẩy vào AI
    private static class PrepareData {
        short id;
        float[] features;
        public PrepareData(short id, float[] features) { this.id = id; this.features = features; }
    }

    public void generateToAerospike(long startTime, long endTime) throws Exception {
        DcaOnnxInferenceManager dcaBrain = new DcaOnnxInferenceManager(Configs.FILE_AI_DCA_MODEL);
        DcaFeatureExtractor extractor = new DcaFeatureExtractor();

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

            // Batch Check Exists
            List<Long> timestampsToCheck = new ArrayList<>(time2Tickers.keySet());
            Set<Long> existingTimestamps = DataManagerAerospikeFloatSim.checkExistingDcaPredictions(timestampsToCheck);

            int skippedCount = 0;
            int processedCount = 0;

            for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                long time = timeEntry.getKey();
                if (time > endTime) break;

                Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                // 1. Update History
                extractor.updateMarketHistory(symbol2Ticker);

                if (existingTimestamps.contains(time)) {
                    skippedCount++;
                    continue;
                }

                processedCount++;
                if (time != lastBasketTimestamp) {
                    cachedBasket = extractor.identifyTargetBasket(time);
                    lastBasketTimestamp = time;
                }
                final List<String> currentBasket = cachedBasket;

                // 2. CHUẨN BỊ DỮ LIỆU (Java CPU Multi-thread)
                // Bước này an toàn vì chỉ dùng Java Heap, không đụng vào Native ONNX
                List<PrepareData> batchInput = symbol2Ticker.entrySet().parallelStream()
                        .map(entry -> {
                            try {
                                String symbol = entry.getKey();
                                KlineObjectSimple ticker = entry.getValue();

                                short symId = symbolMap.computeIfAbsent(symbol, k -> {
                                    short newId = (short) idCounter.incrementAndGet();
                                    DataManagerAerospikeFloatSim.saveSymbolMapping(k, newId);
                                    return newId;
                                });

                                OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0,
                                        Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                                );
                                dummyOrder.lastEntry = ticker.priceClose;

                                DcaMarketFeatures features = extractor.extractFeatures(
                                        time, dummyOrder, null, symbol2Ticker, currentBasket
                                );

                                if (features != null) {
                                    // Convert sang float[] ngay tại đây
                                    return new PrepareData(symId, dcaBrain.extractFeaturesToArray(features));
                                }
                            } catch (Exception e) {}
                            return null;
                        })
                        .filter(Objects::nonNull)
                        .collect(Collectors.toList());

                if (batchInput.isEmpty()) continue;

                // 3. CHẠY AI (Native Call - Single Batch)
                List<float[]> featureList = batchInput.stream().map(p -> p.features).collect(Collectors.toList());
                List<DcaPredictionResult> aiResults = dcaBrain.predictBatch(featureList);

                // 🔥 BƯỚC 4 & 5 ĐÃ SỬA: Chuyển Object về float[] để khớp với hàm Save
                Map<Short, float[]> finalResults = new HashMap<>();

                for (int i = 0; i < batchInput.size(); i++) {
                    DcaPredictionResult res = aiResults.get(i);
                    // Convert Object -> float[] [Risk, Reward, Pump, Dump]
                    // Thứ tự này phải khớp với lúc đọc lên
                    finalResults.put(batchInput.get(i).id, new float[]{
                            res.predictedMaxDrawdown,
                            res.predictedMaxRise,
                            res.probPump20Pct,
                            res.probDump30Pct
                    });
                }

                // 5. Save (Bây giờ đã đúng kiểu Map<Short, float[]>)
                DataManagerAerospikeFloatSim.saveDcaPredictions1M(time, finalResults);
            }

            // Monitor & Clean
            if (time2Tickers.size() > 0) {
                long lastTimeInBlock = time2Tickers.lastKey();
                long usedMem = (Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()) / 1024 / 1024;

                String status = (skippedCount == time2Tickers.size()) ? "(SKIP ALL)" :
                        String.format("(Run: %d, Skip: %d)", processedCount, skippedCount);

                LOG.info("   ✅ Block: {} | RAM: {}MB | {}",
                        Utils.normalizeDateYYYYMMDDHHmm(lastTimeInBlock), usedMem, status);

                time2Tickers = null;
                // Vẫn nên GC thủ công khi làm việc với lượng object lớn
                if (processedCount > 0) System.gc();

                currentTime = lastTimeInBlock + Utils.TIME_MINUTE;
            } else {
                currentTime += minutesToRead * Utils.TIME_MINUTE;
            }
        }

        dcaBrain.close();
        DataManagerAerospikeFloatSim.closeConnection();
        LOG.info("🎉 DONE GENERATION!");
    }
}