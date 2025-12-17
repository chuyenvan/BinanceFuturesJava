package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
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

    // [MỚI] Map lưu thời gian lần cuối lấy mẫu của từng coin để check cooldown 2h
    private final Map<String, Long> symbolLastSampledTime = new HashMap<>();

    public static void main(String[] args) throws Exception {
        new RunDcaDataCollection().run();
    }

    public void run() throws Exception {
        DcaDataCollectionManager manager = new DcaDataCollectionManager("storage/training_data_dca_2m_smart");

        LOG.info("🚀 Loading Market Rates...");
        TreeMap<Long, MarketRateChange> time2Rate = loadMarketRateData();

        long currentTime = Utils.sdfFile.parse("20210101").getTime();
        long endTime = System.currentTimeMillis();

        LOG.info("⏳ START DCA COLLECTION (Target ~2M Samples, 2H Cooldown): {} -> {}",
                Utils.normalizeDateYYYYMMDD(currentTime), Utils.normalizeDateYYYYMMDD(endTime));

        while (currentTime <= endTime) {
            try {
                // Load 4 ngày dữ liệu (Hiện tại + 3 ngày tương lai)
                TreeMap<Long, Map<String, KlineObjectSimple>> dataDay0 = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);
                TreeMap<Long, Map<String, KlineObjectSimple>> dataDay1 = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime + Utils.TIME_DAY);
                TreeMap<Long, Map<String, KlineObjectSimple>> dataDay2 = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime + 2 * Utils.TIME_DAY);
                TreeMap<Long, Map<String, KlineObjectSimple>> dataDay3 = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime + 3 * Utils.TIME_DAY);

                TreeMap<Long, Map<String, KlineObjectSimple>> lookupData = new TreeMap<>();
                if (dataDay0 != null) lookupData.putAll(dataDay0);
                if (dataDay1 != null) lookupData.putAll(dataDay1);
                if (dataDay2 != null) lookupData.putAll(dataDay2);
                if (dataDay3 != null) lookupData.putAll(dataDay3);

                if (dataDay0 != null) {
                    processDay(dataDay0, lookupData, time2Rate, manager);
                }

                manager.exportData();

                LOG.info("✅ Day {} finished. Total samples: {}",
                        Utils.normalizeDateYYYYMMDD(currentTime), manager.getCollectedCount());

            } catch (Exception e) {
                LOG.error("Error day {}", Utils.normalizeDateYYYYMMDD(currentTime), e);
            }
            currentTime += Utils.TIME_DAY;
        }
        LOG.info("🎉 COMPLETED! Final dataset size: {}", manager.getCollectedCount());
    }

    private void processDay(TreeMap<Long, Map<String, KlineObjectSimple>> dayData,
                            TreeMap<Long, Map<String, KlineObjectSimple>> lookupData,
                            TreeMap<Long, MarketRateChange> rateData,
                            DcaDataCollectionManager manager) {

        long nextProcessingTime = 0;

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : dayData.entrySet()) {
            Long timestamp = entry.getKey();

            if (timestamp < nextProcessingTime) continue;

            Map<String, KlineObjectSimple> snapshot = entry.getValue();
            manager.updateHistory(snapshot);

            // [UPDATE] Gọi hàm sinh lệnh mới có check cooldown
            List<OrderTargetInfoTest> stuckOrders = generateSyntheticStuckOrders(timestamp, snapshot);

            for (OrderTargetInfoTest order : stuckOrders) {
                MarketRateChange rate = rateData != null ? rateData.get(timestamp) : null;
                // [UPDATE] Trong manager sẽ tự nhân bản ra 5-10 mẫu (samples) cho mỗi order này
                manager.processSimulatedOrder(timestamp, order, rate, snapshot, lookupData);
            }

            // [UPDATE] Random interval: 5 đến 15 phút (Trung bình 10p)
            // Quét dày hơn vì ta đã lọc cooldown 2h, nên cần quét nhiều lần để bắt được nhiều coin khác nhau
            int skipMinutes = 5 + rand.nextInt(11);
            nextProcessingTime = timestamp + (skipMinutes * 60000L);
        }
    }

    private List<OrderTargetInfoTest> generateSyntheticStuckOrders(long currentTs,
                                                                   Map<String, KlineObjectSimple> snapshot) {
        List<String> candidates = new ArrayList<>();
        long cooldownMillis = 2 * 60 * 60 * 1000L; // 2 giờ

        // 1. Lọc danh sách coin thỏa mãn điều kiện
        for (Map.Entry<String, KlineObjectSimple> entry : snapshot.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple currentKline = entry.getValue();

            // Lọc volume rác
            if (currentKline.totalUsdt < 30000) continue;

            // [MỚI] Check Cooldown: Nếu vừa lấy mẫu trong 2h qua thì bỏ qua
            Long lastTime = symbolLastSampledTime.get(symbol);
            if (lastTime != null && (currentTs - lastTime) < cooldownMillis) {
                continue;
            }

            candidates.add(symbol);
        }

        // 2. Chọn ngẫu nhiên 2 coin từ danh sách candidates
        Collections.shuffle(candidates);
        int maxCoinsToPick = 2; // Chỉ lấy 2 coin mỗi lần quét (vì mỗi coin sẽ đẻ ra ~7.5 mẫu)
        List<String> selectedSymbols = candidates.subList(0, Math.min(candidates.size(), maxCoinsToPick));

        List<OrderTargetInfoTest> orders = new ArrayList<>();

        for (String symbol : selectedSymbols) {
            KlineObjectSimple currentKline = snapshot.get(symbol);

            // Cập nhật thời gian lấy mẫu để tính cooldown lần sau
            symbolLastSampledTime.put(symbol, currentTs);

            // [UPDATE] Tạo 5 đến 10 kịch bản Drawdown khác nhau cho coin này
            // Mục tiêu: "Tăng số batch lên kiểu 5 + random 5"
            int numberOfScenarios = 2 + rand.nextInt(6); // 5 đến 10

            for (int i = 0; i < numberOfScenarios; i++) {
                // Random DD từ 5% đến 80%
                double minDD = 0.05;
                double maxDD = 0.80;
                double dd = minDD + (maxDD - minDD) * rand.nextDouble();

                double assumedEntryPrice = currentKline.priceClose / (1.0 - dd);
                long assumedStartTime = currentTs - (long)(dd * 100 * 3600 * 1000);

                OrderTargetInfoTest order = new OrderTargetInfoTest(
                        null, assumedEntryPrice, null, 100.0, 10, symbol,
                        assumedStartTime, currentTs, OrderSide.BUY
                );
                orders.add(order);
            }
        }

        return orders;
    }

    private TreeMap<Long, MarketRateChange> loadMarketRateData() throws Exception {
        if (!new File(Configs.FILE_MARKET_RATE_CHANGE).exists()) return new TreeMap<>();
        return (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
    }
}