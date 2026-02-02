package com.binance.chuyennd.ai_ml.onnx.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
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
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

public class GenerateFundingPredictionsTool {
    private static final Logger LOG = LoggerFactory.getLogger(GenerateFundingPredictionsTool.class);

    // Các biến dùng chung cho logic xử lý
    private final TreeMap<Long, Float> time2RateDown15MAvg = new TreeMap<>();
    private FundingOnnxInferenceManager aiBrain;
    private FundingFeatureExtractor extractor;
    private TreeMap<Long, MarketDataObject> time2MarketData;
    private ConcurrentHashMap<String, Short> symbolMap;
    private AtomicInteger idCounter;

    // Class phụ để giữ cặp ID và Features
    private static class PrepareData {
        short id;
        float[] features;
        public PrepareData(short id, float[] features) { this.id = id; this.features = features; }
    }

    public static void main(String[] args) throws Exception {

        // Cấu hình tham số lọc
        Configs.FUNDING_RATE_MIN_TRADE = -0.013;
        Configs.FUNDING_RATE_MIN_TRADE_FULL = -0.025;
        Configs.FUNDING_RATE_UP_AVG = 0.004;
        Configs.FUNDING_RATE_DOWN_AVG = -0.005;

        // Init Funding Manager
        try { FundingFeeManager.getInstance(); } catch (Exception e) {}

        // ⚠️ CẤU HÌNH THỜI GIAN TỔNG (Ví dụ chạy từ 2021 đến nay)
        // Các Session sẽ tự động chia nhau các tháng trong khoảng này
        String startTimeStr = "2021-01-01 00:00:00";
        long globalStartTime = Utils.sdfFile.parse(startTimeStr).getTime();
        long globalEndTime = System.currentTimeMillis();

        LOG.info("🔥 STARTING FUNDING GEN (PARALLEL MONTH MODE)...");
        new GenerateFundingPredictionsTool().generateMonthByMonth(globalStartTime, globalEndTime);
    }

    public void generateMonthByMonth(long globalStart, long globalEnd) throws Exception {
        // 1. INIT CÁC COMPONENT (Chỉ init 1 lần)
        String modelPath = "models_funding/Funding_Classifier_Final.onnx";
        this.aiBrain = new FundingOnnxInferenceManager(modelPath);
        this.extractor = new FundingFeatureExtractor();

        LOG.info("📥 Loading Market Rates...");
        this.time2MarketData = loadMarketRateData();

        LOG.info("📥 Loading Symbol Mapper...");
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        int maxId = globalMapper.values().stream().mapToInt(Short::intValue).max().orElse(0);
        this.idCounter = new AtomicInteger(maxId);
        this.symbolMap = new ConcurrentHashMap<>(globalMapper);

        // 2. VÒNG LẶP THEO THÁNG
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(globalStart);
        // Reset về đầu tháng để đảm bảo check đúng
        cal.set(Calendar.DAY_OF_MONTH, 1);
        cal.set(Calendar.HOUR_OF_DAY, 0);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);

        long currentMonthStart = cal.getTimeInMillis();
        SimpleDateFormat sdfMonth = new SimpleDateFormat("yyyy-MM");

        while (currentMonthStart < globalEnd) {
            // Tính thời gian kết thúc tháng hiện tại
            cal.add(Calendar.MONTH, 1);
            long nextMonthStart = cal.getTimeInMillis();
            long currentMonthEnd = nextMonthStart - 1; // 23:59:59 ngày cuối tháng

            String monthStr = sdfMonth.format(new Date(currentMonthStart));

            // 🔥 BƯỚC KIỂM TRA QUAN TRỌNG: Check ngày đầu tiên của tháng
            if (isMonthProcessed(currentMonthStart)) {
                LOG.info("⏩ Tháng {} đã có dữ liệu (Skipping)...", monthStr);
                currentMonthStart = nextMonthStart;
                continue; // Nhảy sang tháng sau
            }

            LOG.info("▶️ Đang chạy Tháng {} ({} -> {})...",
                    monthStr,
                    Utils.normalizeDateYYYYMMDDHHmm(currentMonthStart),
                    Utils.normalizeDateYYYYMMDDHHmm(currentMonthEnd));

            // 🔥 CHẠY DỮ LIỆU CHO THÁNG NÀY
            processPeriod(currentMonthStart, currentMonthEnd);

            // Xong tháng này, nhảy sang tháng sau
            currentMonthStart = nextMonthStart;
        }

        aiBrain.close();
        LOG.info("🎉 DONE ALL MONTHS!");
    }

    /**
     * Kiểm tra xem ngày đầu tiên của tháng đã có dữ liệu chưa.
     * Nếu có > 10 record thì coi như tháng này đã/đang được chạy.
     */
    private boolean isMonthProcessed(long monthStart) {
        List<Long> checkTimestamps = new ArrayList<>();
        // Kiểm tra 24h đầu tiên (1440 phút)
        long checkEnd = monthStart + Utils.TIME_DAY;
        long t = monthStart;
        while (t < checkEnd) {
            checkTimestamps.add(t);
            t += Utils.TIME_MINUTE;
        }

        // Gọi hàm check batch (đã tối ưu trong DataManager)
        Set<Long> existing = DataManagerAerospikeFloatSim.checkExistingFundingPredictions(checkTimestamps);

        // Nếu tìm thấy trên 10 phút có dữ liệu -> Coi như tháng này đã có người chạy
        return existing.size() > 10;
    }

    /**
     * Logic chạy chính cho một khoảng thời gian (cụ thể là 1 tháng)
     */
    private void processPeriod(long startTime, long endTime) {
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

            int processedCount = 0;
            int generatedCount = 0;

            for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : time2Tickers.entrySet()) {
                long time = timeEntry.getKey();
                if (time > endTime) break;

                Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                // UPDATE HISTORY
                extractor.updateMarketHistory(symbol2Ticker);
                updateMarketRateHistory(time);

                // CHECK CONDITION
                if (!isMarketConditionMet(time)) {
                    continue;
                }

                // (Optional) Check lại exist từng phút nếu muốn chắc chắn 100% không ghi đè
                // Nhưng vì đã check đầu tháng rồi nên có thể bỏ qua bước này để tăng tốc

                processedCount++;

                // BASKET
                if (time != lastBasketTimestamp) {
                    cachedBasket = extractor.identifyTargetBasket(symbol2Ticker);
                    lastBasketTimestamp = time;
                }
                final List<String> currentBasket = cachedBasket;

                // FILTER SYMBOLS
                Set<String> symbolFundingBuy = FundingFeeManager.getInstance().getFundingBuyNew(time);
                if (symbolFundingBuy == null || symbolFundingBuy.isEmpty()) continue;

                // PREPARE BATCH
                List<PrepareData> batchInput = symbolFundingBuy.parallelStream()
                        .map(symbol -> {
                            try {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (!Utils.isTickerAvailable(ticker)) return null;
                                if (ticker.totalUsdt < 20000) return null;

                                double rate1m = (ticker.priceClose - ticker.priceOpen) / ticker.priceOpen;
                                double rate15m = extractor.calculateReturn(symbol, 15);
                                if (rate1m >= -0.004 && rate15m >= -0.015) return null;

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

                                FundingMarketFeatures features = extractor.extractFeatures(
                                        time, dummyOrder, symbol2Ticker, currentBasket
                                );
                                if (features != null) {
                                    return new PrepareData(symId, aiBrain.extractFeaturesToArray(features));
                                }
                            } catch (Exception e) {}
                            return null;
                        })
                        .filter(Objects::nonNull)
                        .collect(Collectors.toList());

                if (batchInput.isEmpty()) continue;

                // RUN AI & SAVE
                List<float[]> featureList = batchInput.stream().map(p -> p.features).collect(Collectors.toList());
                List<float[]> aiResults = aiBrain.predictBatch(featureList);

                Map<Short, float[]> finalResults = new HashMap<>();
                for (int i = 0; i < batchInput.size(); i++) {
                    finalResults.put(batchInput.get(i).id, aiResults.get(i));
                }
                DataManagerAerospikeFloatSim.saveFundingPredictions1M(time, finalResults);
                generatedCount += finalResults.size();
            }

            // Log & Clean
            if (time2Tickers.size() > 0) {
                long lastTimeInBlock = time2Tickers.lastKey();
                if (generatedCount > 0) {
                    LOG.info("   ✅ Block: {} | Gen: {}", Utils.normalizeDateYYYYMMDDHHmm(lastTimeInBlock), generatedCount);
                }

                time2Tickers = null;
                if (generatedCount > 0) System.gc(); // GC mỗi khi có ghi dữ liệu mới

                currentTime = lastTimeInBlock + Utils.TIME_MINUTE;
            } else {
                currentTime += minutesToRead * Utils.TIME_MINUTE;
            }
        }
    }

    // --- Helper Methods ---
    private void updateMarketRateHistory(long time) {
        MarketDataObject marketData = time2MarketData.get(time);
        if (marketData == null) return;
        time2RateDown15MAvg.put(time, marketData.rateDown15MAvg);
        while (time2RateDown15MAvg.size() > Configs.NUMBER_RATE_DOWN_HISTORY_TRADE) {
            time2RateDown15MAvg.remove(time2RateDown15MAvg.firstKey());
        }
    }

    private boolean isMarketConditionMet(long time) {
        MarketDataObject marketData = time2MarketData.get(time);
        if (marketData == null) return false;
        Float minRate15Min60M = time2RateDown15MAvg.isEmpty() ? 0f : Collections.min(time2RateDown15MAvg.values());
        return MarketBigChangeDetector.isFundingFeeTrade(
                marketData.rateDown15MAvg,
                marketData.rateDownAvg,
                marketData.rateUpAvg,
                minRate15Min60M);
    }

    private TreeMap<Long, MarketDataObject> loadMarketRateData() throws Exception {
        if (!new File(Configs.FILE_ENTRY_MARKET_LEVEL).exists()) return new TreeMap<>();
        return (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
    }
}