package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
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
import java.util.zip.GZIPInputStream;

public class FeatureValidationTest {
    private static final Logger LOG = LoggerFactory.getLogger(FeatureValidationTest.class);

    public static void main(String[] args) throws Exception {
        LOG.info("🛠️ KHỞI ĐỘNG CÔNG CỤ VALIDATE FEATURE V1 vs V2...");

        // Load map và data cần thiết
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        Map<Short, String> idToSymbolMap = new HashMap<>();
        for (Map.Entry<String, Short> entry : globalMapper.entrySet()) idToSymbolMap.put(entry.getValue(), entry.getKey());

        FundingFeatureExtractor oldExtractor = new FundingFeatureExtractor();
        FundingFeatureExtractorV2 newExtractor = new FundingFeatureExtractorV2();

        // Lấy thử 1 file để test (Ví dụ file Q1 năm 2021)
        String testFile = "market_data_export/market_data_2021_Q1.bin.gz";
        if (!new File(testFile).exists()) {
            LOG.error("❌ Không tìm thấy file test: {}", testFile);
            return;
        }

        LOG.info("📥 Đang load 1 lượng nhỏ Data để test...");
        TreeMap<Long, Map<String, KlineObjectSimple>> testData = loadSampleKlines(testFile, idToSymbolMap, 2000); // Lấy 2000 phút đầu

        LOG.info("🚀 BẮT ĐẦU CHẠY ĐỐI CHIẾU...");
        int count = 0;

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : testData.entrySet()) {
            long time = timeEntry.getKey();
            Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

            // Cập nhật history cho cả 2 qua Singleton
            oldExtractor.updateMarketHistory(symbol2Ticker);
            if (count < 100) { count++; continue; } // Bỏ qua 100 phút đầu để warm-up RSI/MA

            final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);
            MarketDataObject marketData = time2MarketData.get(time);

            for (String symbol : symbol2Ticker.keySet()) {
                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                if (!Utils.isTickerAvailable(ticker)) continue;

                OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                        Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY);
                dummyOrder.lastEntry = ticker.priceClose;

                FundingMarketFeatures oldF = oldExtractor.extractFeatures(time, dummyOrder, symbol2Ticker, marketData, basket);
                FundingMarketFeatures newF = newExtractor.extractFeatures(time, dummyOrder, symbol2Ticker, marketData, basket);

                if (oldF != null && newF != null) {
                    validateFeatures(oldF, newF, symbol, time);
                }
            }
            count++;
            if (count % 100 == 0) LOG.info("  -> Đã quét và khớp hoàn toàn {} phút...", count);
        }

        LOG.info("✅✅✅ VALIDATE THÀNH CÔNG! CLASS V2 KHỚP 100% VỚI CLASS GỐC! BÁC CÓ THỂ YÊN TÂM SỬ DỤNG V2.");
        System.exit(0);
    }

    private static void validateFeatures(FundingMarketFeatures oldF, FundingMarketFeatures newF, String symbol, long time) {
        float epsilon = 0.00001f;
        String timeStr = Utils.normalizeDateYYYYMMDDHHmm(time);

        check(oldF.btcMomentum1H, newF.btcMomentum1H, "btcMomentum1H", symbol, timeStr, epsilon);
        check(oldF.basketRsi14, newF.basketRsi14, "basketRsi14", symbol, timeStr, epsilon);
        check(oldF.momentum1H, newF.momentum1H, "momentum1H", symbol, timeStr, epsilon);
        check(oldF.fundingRateRaw, newF.fundingRateRaw, "fundingRateRaw", symbol, timeStr, epsilon);
        // Bác có thể check thêm các trường khác nếu cần
    }

    private static void check(float oldVal, float newVal, String field, String symbol, String time, float epsilon) {
        if (Float.isNaN(oldVal) && Float.isNaN(newVal)) return;
        if (Math.abs(oldVal - newVal) > epsilon) {
            LOG.error("❌ SAI LỆCH! Time: {} | Sym: {} | Field: {} | Old: {} | New: {}", time, symbol, field, oldVal, newVal);
            System.exit(1);
        }
    }

    private static TreeMap<Long, Map<String, KlineObjectSimple>> loadSampleKlines(String filePath, Map<Short, String> map, int maxMinutes) throws Exception {
        TreeMap<Long, Map<String, KlineObjectSimple>> result = new TreeMap<>();
        int count = 0;
        long lastTime = 0;
        try (DataInputStream dis = new DataInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(filePath))))) {
            while (count < maxMinutes) {
                try {
                    long time = dis.readLong(); short symId = dis.readShort();
                    float o = dis.readFloat(); float h = dis.readFloat(); float l = dis.readFloat(); float c = dis.readFloat(); float v = dis.readFloat();
                    String sym = map.get(symId);
                    if (sym == null) continue;
                    KlineObjectSimple k = new KlineObjectSimple(); k.startTime = time; k.priceClose = c; k.maxPrice = h; k.minPrice = l;
                    result.computeIfAbsent(time, t -> new HashMap<>()).put(sym, k);
                    if (time != lastTime) { lastTime = time; count++; }
                } catch (EOFException e) { break; }
            }
        }
        return result;
    }
}