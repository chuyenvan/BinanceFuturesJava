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
    private final Map<Long, TreeMap<Long, Map<String, KlineObjectSimple>>> dataCache = new HashMap<>();
    public void run() throws Exception {
        // Folder lưu data tinh gọn (Clean Data)
        DcaDataCollectionManager manager = new DcaDataCollectionManager("storage/training_data_dca");

        LOG.info("🚀 Loading Market Rates...");
        TreeMap<Long, MarketRateChange> time2Rate = loadMarketRateData();

        LOG.info("🚀 Loading Market Rates Done {}", time2Rate.size());
        long startTime = Utils.sdfFile.parse("20210102").getTime();
        long warmUpTime = startTime - Utils.TIME_DAY; // Load trước 1 ngày để warm-up indicator
        long endTime = System.currentTimeMillis();
        long currentTime = warmUpTime;

        while (currentTime <= endTime) {
            try {
                long t0 = System.currentTimeMillis();

                // 1. Lấy Data Hôm Nay (T)
                // Kiểm tra cache trước, nếu chưa có thì load
                if (!dataCache.containsKey(currentTime)) {
                    LOG.info("📥 Loading data for day: {}", Utils.normalizeDateYYYYMMDD(currentTime));
                    TreeMap<Long, Map<String, KlineObjectSimple>> d = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);
                    if (d != null) dataCache.put(currentTime, d);
                }
                TreeMap<Long, Map<String, KlineObjectSimple>> dataDay0 = dataCache.get(currentTime);

                // 2. Chuẩn bị Lookup Data (T, T+1, T+2, T+3)
                TreeMap<Long, Map<String, KlineObjectSimple>> lookupData = new TreeMap<>();
                if (dataDay0 != null) lookupData.putAll(dataDay0);

                // Load trước các ngày tương lai nếu chưa có trong cache
                for (int i = 1; i <= 3; i++) {
                    long nextDay = currentTime + ((long) i * Utils.TIME_DAY);
                    if (nextDay > endTime) break;

                    if (!dataCache.containsKey(nextDay)) {
                        // LOG nhẹ để biết nó đang chạy, không bị treo
                        // LOG.info("   ... pre-loading future day: {}", Utils.normalizeDateYYYYMMDD(nextDay));
                        TreeMap<Long, Map<String, KlineObjectSimple>> dNext = DataManagerAerospikeFloatSim.readDataFromAerospike1M(nextDay);
                        if (dNext != null) dataCache.put(nextDay, dNext);
                    }

                    // Lấy từ cache bỏ vào lookup
                    TreeMap<Long, Map<String, KlineObjectSimple>> dNextCache = dataCache.get(nextDay);
                    if (dNextCache != null) {
                        lookupData.putAll(dNextCache);
                    }
                }

                // 3. XÓA DATA CŨ (Quan trọng để không tràn RAM)
                // Ngày T-1 không cần dùng nữa -> Xóa khỏi cache
                long prevDay = currentTime - Utils.TIME_DAY;
                dataCache.remove(prevDay);

                long tLoad = System.currentTimeMillis();

                // 4. Xử lý dữ liệu
                if (dataDay0 != null) {
                    processDay(dataDay0, lookupData, time2Rate, manager, currentTime >= startTime);
                }

                long tProcess = System.currentTimeMillis();

                // 5. Export & Log
                if (currentTime >= startTime) {
                    manager.exportData();
                    LOG.info("✅ Day {} done. Load: {}ms, Process: {}ms. Count: {}",
                            Utils.normalizeDateYYYYMMDD(currentTime),
                            (tLoad - t0), (tProcess - tLoad),
                            manager.getCollectedCount());
                } else {
                    // Log cho giai đoạn Warm-up để biết nó vẫn sống
                    LOG.info("🔥 Warm-up day {} done.", Utils.normalizeDateYYYYMMDD(currentTime));
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

        int counter = 0;
        int totalMinutes = dayData.size();

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : dayData.entrySet()) {
            Long timestamp = entry.getKey();
            Map<String, KlineObjectSimple> snapshot = entry.getValue();

            manager.updateHistory(snapshot);

            counter++;
            // 🔥 LOG NHỊP TIM: In ra mỗi 60 phút (tức là 24 lần/ngày)
            if (counter % 240 == 0) {
                LOG.info("   ⏳ Processing... {}/{} mins. Data collected: {}", counter, totalMinutes, manager.getCollectedCount());
            }

            if (!isCollecting) continue;

            MarketRateChange rate = rateData != null ? rateData.get(timestamp) : null;
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
        long cooldownMillis = 120 * 60 * 1000L;

        for (Map.Entry<String, KlineObjectSimple> entry : snapshot.entrySet()) {
            // Lọc Volume 50k (Chỉ lấy coin có thanh khoản ổn)
            if (entry.getValue().totalUsdt < 5000) continue;

            Long lastTime = symbolLastSampledTime.get(entry.getKey());
            if (lastTime != null && (currentTs - lastTime) < cooldownMillis) continue;
            candidates.add(entry.getKey());
        }

        Collections.shuffle(candidates);

        // 2. Lấy Top 40 coin ngẫu nhiên mỗi giờ
        int maxCoinsToPick = 4;

        List<String> selectedSymbols = candidates.subList(0, Math.min(candidates.size(), maxCoinsToPick));
        List<OrderTargetInfoTest> orders = new ArrayList<>();

        for (String symbol : selectedSymbols) {
            KlineObjectSimple currentKline = snapshot.get(symbol);
            symbolLastSampledTime.put(symbol, currentTs);

            // Sinh 1 trạng thái ngẫu nhiên (1-1 Mapping)
            double drawdownPercent = generateWeightedDrawdown();
            double assumedEntryPrice = currentKline.priceClose / (1.0 - drawdownPercent);
            long assumedStartTime = currentTs - (long) (drawdownPercent * 100 * 3600 * 1000);

            OrderTargetInfoTest order = new OrderTargetInfoTest(
                    null, assumedEntryPrice, null, 100.0, 10, symbol,
                    assumedStartTime, currentTs, OrderSide.BUY
            );
            order.lastPrice = currentKline.priceClose;
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