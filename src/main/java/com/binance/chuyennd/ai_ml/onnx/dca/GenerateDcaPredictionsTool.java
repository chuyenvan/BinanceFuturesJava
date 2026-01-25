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

public class GenerateDcaPredictionsTool {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateDcaPredictionsTool.class);

    public static void main(String[] args) throws Exception {
        // Cấu hình: Chạy từ 2021 đến hiện tại
        String startTimeStr = "2021-01-01 00:00:00";
        long startTime = Utils.sdfFile.parse(startTimeStr).getTime();
        long endTime = System.currentTimeMillis();

        LOG.info("🔥 STARTING AEROSPKE GENERATION (Max Cores)...");
        new GenerateDcaPredictionsTool().generateToAerospike(startTime, endTime);
    }

    public void generateToAerospike(long startTime, long endTime) throws Exception {
        // 1. Load Model AI
        DcaOnnxInferenceManager dcaBrain = new DcaOnnxInferenceManager(Configs.FILE_AI_DCA_MODEL);

        // 2. Load Feature Extractor
        DcaFeatureExtractor extractor = new DcaFeatureExtractor();

        // 3. Load Global Mapper từ Aerospike
        LOG.info("📥 Loading Symbol Mapper from Aerospike...");
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();

        // Tìm Max ID hiện tại để tăng dần
        int maxId = globalMapper.values().stream().mapToInt(Short::intValue).max().orElse(0);
        AtomicInteger idCounter = new AtomicInteger(maxId);

        // Dùng ConcurrentMap để update thread-safe
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);

        long currentTime = startTime;
        long lastBasketTimestamp = -1;
        List<String> cachedBasket = new ArrayList<>();

        LOG.info("🚀 PROCESSING DATA: {} -> {}", Utils.normalizeDateYYYYMMDD(startTime), Utils.normalizeDateYYYYMMDD(endTime));

        // --- LOOP TIME (TUẦN TỰ) ---
        while (currentTime <= endTime) {
            // Đọc 1 ngày data (1440 phút)
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);

            if (time2Tickers == null || time2Tickers.isEmpty()) {
                currentTime += Utils.TIME_HOUR;
                continue;
            }

            // Duyệt từng phút
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                long time = timeEntry.getKey();
                if (time > endTime) break;

                Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                // a. Update History (Tuần tự - Main Thread)
                extractor.updateMarketHistory(symbol2Ticker);

                if (time != lastBasketTimestamp) {
                    cachedBasket = extractor.identifyTargetBasket(time);
                    lastBasketTimestamp = time;
                }
                final List<String> currentBasket = cachedBasket;

                // b. Predict Song Song (Parallel Stream - All Cores)
                ConcurrentHashMap<Short, float[]> framePredictions = new ConcurrentHashMap<>(symbol2Ticker.size());

                symbol2Ticker.entrySet().parallelStream().forEach(entry -> {
                    String symbol = entry.getKey();
                    KlineObjectSimple ticker = entry.getValue();

                    // Lấy ID hoặc tạo mới
                    short symId = symbolMap.computeIfAbsent(symbol, k -> {
                        short newId = (short) idCounter.incrementAndGet();
                        // Lưu ID mới vào Aerospike (Async - Fire & Forget)
                        DataManagerAerospikeFloatSim.saveSymbolMapping(k, newId);
                        return newId;
                    });

                    // Dummy Order
                    OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                            OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0,
                            Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                    );
                    dummyOrder.lastEntry = ticker.priceClose;

                    try {
                        DcaMarketFeatures features = extractor.extractFeatures(
                                time, dummyOrder, null, symbol2Ticker, currentBasket
                        );

                        if (features != null) {
                            DcaPredictionResult res = dcaBrain.predict(features);
                            framePredictions.put(symId, new float[]{
                                    res.predictedMaxDrawdown,
                                    res.predictedMaxRise,
                                    res.probPump20Pct,
                                    res.probDump30Pct
                            });
                        }
                    } catch (Exception e) {}
                });

                // c. Ghi vào Aerospike (Ngay lập tức)
                if (!framePredictions.isEmpty()) {
                    DataManagerAerospikeFloatSim.saveDcaPredictions1M(time, new HashMap<>(framePredictions));
                }
            }

            // Log tiến độ
            if (time2Tickers.size() > 0) {
                long lastTimeInBlock = time2Tickers.lastKey();
                LOG.info("   ✅ Saved block until: {} | Symbols: {}", Utils.normalizeDateYYYYMMDDHHmm(lastTimeInBlock), symbolMap.size());
                currentTime = lastTimeInBlock + Utils.TIME_MINUTE;
            } else {
                currentTime += Utils.TIME_MINUTE;
            }
        }

        dcaBrain.close();
        DataManagerAerospikeFloatSim.closeConnection();
        DataManagerAerospikeFloatSim.closeConnection();
        LOG.info("🎉 DONE GENERATION!");
    }
}