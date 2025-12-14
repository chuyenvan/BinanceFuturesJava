package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.aerospike.DataManagerAerospike;
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

    public static void main(String[] args) throws Exception {
        new RunDcaDataCollection().run();
    }

    public void run() throws Exception {
        DcaDataCollectionManager manager = new DcaDataCollectionManager("storage/training_data_dca");

        LOG.info("🚀 Loading Market Rates...");
        TreeMap<Long, MarketRateChange> time2Rate = loadMarketRateData();

        long currentTime = Utils.sdfFile.parse("20210101").getTime();
        long endTime = System.currentTimeMillis();

        LOG.info("⏳ START DCA COLLECTION: {} -> {}", Utils.normalizeDateYYYYMMDD(currentTime), Utils.normalizeDateYYYYMMDD(endTime));

        while (currentTime <= endTime) {
            try {
                // Load data 2 ngày liên tiếp để có thể nhìn tương lai 24h
                TreeMap<Long, Map<String, KlineObjectSimple>> currentData = DataManagerAerospike.readDataFromAerospike1M(currentTime);
                TreeMap<Long, Map<String, KlineObjectSimple>> nextDayData = DataManagerAerospike.readDataFromAerospike1M(currentTime + Utils.TIME_DAY);

                TreeMap<Long, Map<String, KlineObjectSimple>> lookupData = new TreeMap<>();
                if (currentData != null) lookupData.putAll(currentData);
                if (nextDayData != null) lookupData.putAll(nextDayData);

                if (currentData != null) {
                    processDay(currentData, lookupData, time2Rate, manager);
                }

                // Export định kỳ
                manager.exportData();

            } catch (Exception e) {
                LOG.error("Error day {}", Utils.normalizeDateYYYYMMDD(currentTime), e);
            }
            currentTime += Utils.TIME_DAY;
        }
    }

    private void processDay(TreeMap<Long, Map<String, KlineObjectSimple>> dayData,
                            TreeMap<Long, Map<String, KlineObjectSimple>> lookupData,
                            TreeMap<Long, MarketRateChange> rateData,
                            DcaDataCollectionManager manager) {

        // Duyệt từng phút (hoặc nhảy cóc 15p/lần để giảm tải)
        long lastProcessedTime = 0;

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : dayData.entrySet()) {
            Long timestamp = entry.getKey();

            // Optimization: Chỉ check 15 phút một lần để tạo mẫu, không cần từng phút
            if (timestamp - lastProcessedTime < 15 * 60000) continue;
            lastProcessedTime = timestamp;

            Map<String, KlineObjectSimple> snapshot = entry.getValue();

            // 1. Cập nhật lịch sử giá cho Extractor
            manager.updateHistory(snapshot);

            // 2. TẠO LỆNH GIẢ LẬP (Synthetic Orders)
            // Tìm các coin đang giảm so với 4H trước -> Giả sử ta bị kẹt lệnh ở đó
            List<OrderTargetInfoTest> stuckOrders = generateSyntheticStuckOrders(timestamp, snapshot, manager);

            // 3. Xử lý từng lệnh kẹt
            for (OrderTargetInfoTest order : stuckOrders) {
                MarketRateChange rate = rateData != null ? rateData.get(timestamp) : null;
                manager.processSimulatedOrder(timestamp, order, rate, snapshot, lookupData);
            }
        }
    }

    // Giả lập: Tìm coin giảm giá, giả vờ ta đã mua ở giá cao 4H trước
    private List<OrderTargetInfoTest> generateSyntheticStuckOrders(long currentTs,
                                                                   Map<String, KlineObjectSimple> snapshot,
                                                                   DcaDataCollectionManager manager) {
        List<OrderTargetInfoTest> orders = new ArrayList<>();

        for (Map.Entry<String, KlineObjectSimple> entry : snapshot.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple currentKline = entry.getValue();

            // Bỏ qua coin rác vol nhỏ
            if (currentKline.totalUsdt < 50000) continue;

            // Hack: Lấy giá 4 tiếng trước từ History của Extractor (nếu có access)
            // Hoặc đơn giản: Giả định Entry = Max Price của 4H gần nhất (tình huống đu đỉnh)
            // Ở đây ta giả định Entry cao hơn giá hiện tại 3% - 15% (Random hoặc Logic)

            // Logic tạo mẫu đa dạng:
            // Tạo 1 lệnh giả định mua giá cao hơn 3% (mới lỗ)
            // Tạo 1 lệnh giả định mua giá cao hơn 10% (lỗ sâu)

            double[] drawdownsToSimulate = {0.03, 0.08, 0.15}; // Giả sử đang lỗ 3%, 8%, 15%

            for (double dd : drawdownsToSimulate) {
                double assumedEntryPrice = currentKline.priceClose / (1.0 - dd);

                // Giả lập thời gian vào lệnh (tương ứng với mức lỗ, lỗ càng sâu thời gian càng lâu)
                long assumedStartTime = currentTs - (long)(dd * 100 * 3600 * 1000);

                OrderTargetInfoTest order = new OrderTargetInfoTest(
                        null, assumedEntryPrice, null, 100.0, 10, symbol,
                        assumedStartTime, currentTs, OrderSide.BUY
                );
                orders.add(order);
            }
        }
        // Chỉ lấy mẫu ngẫu nhiên khoảng 20 lệnh mỗi lần quét để tránh quá tải data
        Collections.shuffle(orders);
        return orders.subList(0, Math.min(orders.size(), 20));
    }

    private TreeMap<Long, MarketRateChange> loadMarketRateData() throws Exception {
        if (!new File(Configs.FILE_MARKET_RATE_CHANGE).exists()) return new TreeMap<>();
        return (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
    }
}