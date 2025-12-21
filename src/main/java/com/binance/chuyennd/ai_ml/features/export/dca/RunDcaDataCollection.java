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
        // Folder lưu data tinh gọn (Clean Data)
        DcaDataCollectionManager manager = new DcaDataCollectionManager("storage/training_data_dca_clean_1h");

        LOG.info("🚀 Loading Market Rates...");
        TreeMap<Long, MarketRateChange> time2Rate = loadMarketRateData();

        long startTime = Utils.sdfFile.parse("20210101").getTime();
        long warmUpTime = startTime - Utils.TIME_DAY; // Load trước 1 ngày để warm-up indicator
        long endTime = System.currentTimeMillis();
        long currentTime = warmUpTime;

        while (currentTime <= endTime) {
            try {
                // 1. Load Data Hôm Nay
                TreeMap<Long, Map<String, KlineObjectSimple>> dataDay0 = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);

                // 2. Chuẩn bị Lookup Data (Dùng để soi tương lai tính Label)
                TreeMap<Long, Map<String, KlineObjectSimple>> lookupData = new TreeMap<>();
                if (dataDay0 != null) lookupData.putAll(dataDay0);

                // 🔥 [PHẦN BỔ SUNG QUAN TRỌNG]: LOAD DỮ LIỆU 3 NGÀY TIẾP THEO 🔥
                // Vì Label MaxDrop nhìn về tương lai 3 ngày (72h)
                for (int i = 1; i <= 3; i++) {
                    long nextDay = currentTime + ((long) i * Utils.TIME_DAY);
                    if (nextDay > endTime) break; // Không load quá ngày hiện tại

                    TreeMap<Long, Map<String, KlineObjectSimple>> dataNext = DataManagerAerospikeFloatSim.readDataFromAerospike1M(nextDay);
                    if (dataNext != null) {
                        lookupData.putAll(dataNext);
                    }
                }

                // 3. Xử lý dữ liệu
                if (dataDay0 != null) {
                    processDay(dataDay0, lookupData, time2Rate, manager, currentTime >= startTime);
                }

                // 4. Export & Log
                if (currentTime >= startTime) {
                    manager.exportData();
                    LOG.info("✅ Day {} done. Cumulative Count: {}",
                            Utils.normalizeDateYYYYMMDD(currentTime), manager.getCollectedCount());
                }
            } catch (Exception e) {
                LOG.error("Error processing day " + currentTime, e);
            }
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

            // Luôn update history để chỉ báo (RSI, MA) liên tục
            manager.updateHistory(snapshot);

            if (!isCollecting) continue;

            MarketRateChange rate = rateData != null ? rateData.get(timestamp) : null;

            // BỎ FILTER MarketBigChangeDetector để lấy cả dữ liệu ngày thường

            List<OrderTargetInfoTest> stuckOrders = generateDeepStuckOrders(timestamp, snapshot);
            for (OrderTargetInfoTest order : stuckOrders) {
                manager.processSimulatedOrder(timestamp, order, rate, snapshot, lookupData);
            }
        }
    }

    private List<OrderTargetInfoTest> generateDeepStuckOrders(long currentTs, Map<String, KlineObjectSimple> snapshot) {
        List<String> candidates = new ArrayList<>();

        // 🔥 CẤU HÌNH TINH GỌN DATA (Tránh tràn RAM)
        // 1. Cooldown 60 phút: Mỗi coin chỉ lấy mẫu 1 lần/giờ
        long cooldownMillis = (11 + rand.nextInt(10)) * 60 * 1000L;

        for (Map.Entry<String, KlineObjectSimple> entry : snapshot.entrySet()) {
            // Lọc Volume 50k (Chỉ lấy coin có thanh khoản ổn)
            if (entry.getValue().totalUsdt < 10000) continue;

            Long lastTime = symbolLastSampledTime.get(entry.getKey());
            if (lastTime != null && (currentTs - lastTime) < cooldownMillis) continue;
            candidates.add(entry.getKey());
        }

        Collections.shuffle(candidates);

        // 2. Lấy Top 40 coin ngẫu nhiên mỗi giờ
        int maxCoinsToPick = 10;

        List<String> selectedSymbols = candidates.subList(0, Math.min(candidates.size(), maxCoinsToPick));
        List<OrderTargetInfoTest> orders = new ArrayList<>();

        for (String symbol : selectedSymbols) {
            KlineObjectSimple currentKline = snapshot.get(symbol);
            symbolLastSampledTime.put(symbol, currentTs);

            // Sinh 1 trạng thái ngẫu nhiên (1-1 Mapping)
            double drawdownPercent = generateWeightedDrawdown();
            double assumedEntryPrice = currentKline.priceClose / (1.0 - drawdownPercent);
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