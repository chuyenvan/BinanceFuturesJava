package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.*;

public class RunDcaDataCollection {
    private static final Logger LOG = LoggerFactory.getLogger(RunDcaDataCollection.class);
    private final Random rand = new Random();
    private final Map<String, Long> symbolLastSampledTime = new HashMap<>();

    public static void main(String[] args) throws Exception {
        // Init Funding Manager
        try {
            FundingFeeManager.getInstance();
            LOG.info("✅ FundingFeeManager Initialized!");
        } catch (Exception e) {
            LOG.error("❌ Failed to init FundingFeeManager", e);
            return;
        }
        new RunDcaDataCollection().run();
    }

    public void run() throws Exception {
        // Đổi tên folder output để không lẫn với data cũ ít ỏi
        DcaDataCollectionManager manager = new DcaDataCollectionManager("storage/training_data_dca_bigdata");

        LOG.info("🚀 Loading Market Rates...");
        TreeMap<Long, MarketRateChange> time2Rate = loadMarketRateData();

        long startTime = Utils.sdfFile.parse("20210101").getTime();
        long warmUpTime = startTime - Utils.TIME_DAY;
        long endTime = System.currentTimeMillis();
        long currentTime = warmUpTime;

        while (currentTime <= endTime) {
            try {
                TreeMap<Long, Map<String, KlineObjectSimple>> dataDay0 = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);
                TreeMap<Long, Map<String, KlineObjectSimple>> lookupData = new TreeMap<>();
                if (dataDay0 != null) lookupData.putAll(dataDay0);

                // Load lookup data (giữ nguyên logic cũ của bạn để lấy data tương lai)
                // ...

                if (dataDay0 != null) {
                    processDay(dataDay0, lookupData, time2Rate, manager, currentTime >= startTime);
                }

                if (currentTime >= startTime) {
                    manager.exportData();
                    // Log rõ ràng: Ngày này lấy được bao nhiêu mẫu MỚI (New Samples)
                    // Lưu ý: getCollectedCount() là tích lũy, nên muốn xem tốc độ thì cần trừ đi số cũ.
                    LOG.info("✅ Day {} done. Cumulative Count: {}",
                            Utils.normalizeDateYYYYMMDD(currentTime), manager.getCollectedCount());
                }
            } catch (Exception e) { e.printStackTrace(); }
            currentTime += Utils.TIME_DAY;
        }
    }

    private void processDay(TreeMap<Long, Map<String, KlineObjectSimple>> dayData,
                            TreeMap<Long, Map<String, KlineObjectSimple>> lookupData,
                            TreeMap<Long, MarketRateChange> rateData,
                            DcaDataCollectionManager manager,
                            boolean isCollecting) {

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : dayData.entrySet()) {
            Long timestamp = entry.getKey();
            Map<String, KlineObjectSimple> snapshot = entry.getValue();

            // 1. Update History (Luôn chạy để chỉ báo kỹ thuật liền mạch)
            manager.updateHistory(snapshot);

            if (!isCollecting) continue;

            // 2. Lấy Market Rate (để làm feature)
            MarketRateChange rate = rateData != null ? rateData.get(timestamp) : null;

            // 🔥 THAY ĐỔI QUAN TRỌNG NHẤT: BỎ FILTER "MarketBigChangeDetector" 🔥
            // Chúng ta cần data của cả ngày thường để AI học được sự khác biệt giữa "Bình yên" và "Bão tố".
            // if (rate == null || !MarketBigChangeDetector.isDcaAlt(...)) continue;  <-- XÓA DÒNG NÀY

            // 3. Sinh giả lập
            List<OrderTargetInfoTest> stuckOrders = generateDeepStuckOrders(timestamp, snapshot);
            for (OrderTargetInfoTest order : stuckOrders) {
                manager.processSimulatedOrder(timestamp, order, rate, snapshot, lookupData);
            }
        }
    }

    private List<OrderTargetInfoTest> generateDeepStuckOrders(long currentTs, Map<String, KlineObjectSimple> snapshot) {
        List<String> candidates = new ArrayList<>();

        // Cooldown 15 phút: Đủ để bắt biến động, không quá dày
        long cooldownMillis = 15 * 60 * 1000L;

        for (Map.Entry<String, KlineObjectSimple> entry : snapshot.entrySet()) {
            // Volume > 10k: Lọc bớt rác quá nhỏ, nhưng vẫn giữ Mid-cap
            if (entry.getValue().totalUsdt < 10000) continue;

            Long lastTime = symbolLastSampledTime.get(entry.getKey());
            if (lastTime != null && (currentTs - lastTime) < cooldownMillis) continue;
            candidates.add(entry.getKey());
        }

        Collections.shuffle(candidates);

        // 🔥 TĂNG SỐ LƯỢNG MẪU: Lấy tối đa 100 coin mỗi lần quét (gần như toàn bộ market active)
        int maxCoinsToPick = 100;
        List<String> selectedSymbols = candidates.subList(0, Math.min(candidates.size(), maxCoinsToPick));

        List<OrderTargetInfoTest> orders = new ArrayList<>();

        for (String symbol : selectedSymbols) {
            KlineObjectSimple currentKline = snapshot.get(symbol);
            symbolLastSampledTime.put(symbol, currentTs);

            // Sinh ngẫu nhiên Drawdown
            double drawdownPercent = generateWeightedDrawdown();
            double assumedEntryPrice = currentKline.priceClose / (1.0 - drawdownPercent);

            // Tính ngược thời gian vào lệnh giả định
            // (Không quá quan trọng chính xác từng phút, chủ yếu để logic không bị vô lý)
            long assumedStartTime = currentTs - (long)(drawdownPercent * 100 * 3600 * 1000);

            OrderTargetInfoTest order = new OrderTargetInfoTest(
                    null, assumedEntryPrice, null, 100.0, 10, symbol,
                    assumedStartTime, currentTs, OrderSide.BUY
            );
            orders.add(order);
        }
        return orders;
    }

    private double generateWeightedDrawdown() {
        // Giữ nguyên logic phân phối lỗ (Tập trung vùng 30-70%)
        double r = rand.nextDouble();
        if (r < 0.2) return 0.05 + rand.nextDouble() * 0.25; // 5-30%
        else if (r < 0.8) return 0.30 + rand.nextDouble() * 0.40; // 30-70% (Main)
        else return 0.70 + rand.nextDouble() * 0.20; // 70-90%
    }

    private TreeMap<Long, MarketRateChange> loadMarketRateData() throws Exception {
        if (!new File(Configs.FILE_MARKET_RATE_CHANGE).exists()) return new TreeMap<>();
        return (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
    }
}