package com.binance.chuyennd.ai_ml.features.export.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

public class RunFundingDataCollection {
    private static final Logger LOG = LoggerFactory.getLogger(RunFundingDataCollection.class);

    // Cache data để lookup tương lai
    private final Map<Long, TreeMap<Long, Map<String, KlineObjectSimple>>> dataCache = new HashMap<>();


    public static void main(String[] args) throws Exception {
        // 1. CẤU HÌNH THAM SỐ (Override Configs theo yêu cầu)
        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = -0.013f;
        Configs.PREDICT_SYMBOL_RATE_DOWN_15M = -0.025f;
        Configs.PREDICT_SYMBOL_RATE_UP_AVG = 0.004f;
        Configs.PREDICT_SYMBOL_RATE_DOWN_AVG = -0.005f;

        new RunFundingDataCollection().run();
    }

    public void run() throws Exception {
        // Folder lưu data
        FundingDataCollectionManager manager = new FundingDataCollectionManager("storage/training_data_funding");

        LOG.info("🚀 Loading Market Rates...");
        TreeMap<Long, MarketDataObject> time2Rate =  DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        LOG.info("🚀 Loading Market Rates Done: {}", time2Rate.size());

        long startTime = Utils.sdfFile.parse("20210101").getTime();
        long warmUpTime = startTime - Utils.TIME_DAY;
        long endTime = System.currentTimeMillis();
        long currentTime = warmUpTime;

        while (currentTime <= endTime) {
            try {
                long t0 = System.currentTimeMillis();

                // 1. Lấy Data Hôm Nay (T)
                if (!dataCache.containsKey(currentTime)) {
                    TreeMap<Long, Map<String, KlineObjectSimple>> d = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);
                    if (d != null) dataCache.put(currentTime, d);
                }
                TreeMap<Long, Map<String, KlineObjectSimple>> dataDay0 = dataCache.get(currentTime);

                // 2. Chuẩn bị Lookup Data (T -> T+3 ngày để check 72h)
                TreeMap<Long, Map<String, KlineObjectSimple>> lookupData = new TreeMap<>();
                if (dataDay0 != null) lookupData.putAll(dataDay0);

                for (int i = 1; i <= 3; i++) {
                    long nextDay = currentTime + ((long) i * Utils.TIME_DAY);
                    if (nextDay > endTime) break;

                    if (!dataCache.containsKey(nextDay)) {
                        TreeMap<Long, Map<String, KlineObjectSimple>> dNext = DataManagerAerospikeFloatSim.readDataFromAerospike1M(nextDay);
                        if (dNext != null) dataCache.put(nextDay, dNext);
                    }
                    TreeMap<Long, Map<String, KlineObjectSimple>> dNextCache = dataCache.get(nextDay);
                    if (dNextCache != null) {
                        lookupData.putAll(dNextCache);
                    }
                }

                // 3. XÓA DATA CŨ
                long prevDay = currentTime - Utils.TIME_DAY;
                dataCache.remove(prevDay);

                // 4. Xử lý dữ liệu
                if (dataDay0 != null) {
                    processDay(dataDay0, lookupData, time2Rate, manager, currentTime >= startTime);
                }

                // 5. Export
                if (currentTime >= startTime) {
                    manager.exportData();
                    LOG.info("✅ Funding Day {} done. Count: {} Labels: {}",
                            Utils.normalizeDateYYYYMMDD(currentTime),
                            manager.getCollectedCount(), manager.getLabelReport());
                }

            } catch (Exception e) {
                LOG.error("Error processing day " + currentTime, e);
                e.printStackTrace();
            }
            currentTime += Utils.TIME_DAY;
        }
    }

    private void processDay(TreeMap<Long, Map<String, KlineObjectSimple>> dayData,
                            TreeMap<Long, Map<String, KlineObjectSimple>> lookupData,
                            TreeMap<Long, MarketDataObject> time2Rate,
                            FundingDataCollectionManager manager,
                            boolean isCollecting) {

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : dayData.entrySet()) {
            Long timestamp = entry.getKey();
            Map<String, KlineObjectSimple> snapshot = entry.getValue();

            // Cập nhật lịch sử feature extractor (luôn chạy để đảm bảo tính liên tục của indicator)
            manager.updateHistory(snapshot);

            MarketDataObject marketData = time2Rate.get(timestamp);
            if (marketData == null) continue;

            // --- LOGIC GIỐNG SIMULATOR ---


            if (!isCollecting) continue;
            try {


                    // 3. Lấy danh sách coin tiềm năng từ
                    for (String symbol : snapshot.keySet()) {
                        KlineObjectSimple ticker = snapshot.get(symbol);

                        // Lọc cơ bản
                        if (!Utils.isTickerAvailable(ticker)) continue;

                        if (ticker.totalUsdt < 10000) continue;
                        // 🔥🔥🔥 UPDATE LOGIC LỌC TỐC ĐỘ RƠI 🔥🔥🔥
                        // 1. Tính Rate 1M: (Close - Open) / Open
                        float rate1m = (ticker.priceClose - ticker.priceOpen) / ticker.priceOpen;
                        // 2. Tính Rate 15M từ Manager (dùng History)
                        float rate15m = manager.getReturn(symbol, 15);
                        if (rate1m >= -0.004 && rate15m >= -0.015)
                            continue; // Phải giảm > 0.5% trong 1 phút này


                        try {
                            // Tạo lệnh giả lập tại giá Close
                            OrderTargetInfoTest order = new OrderTargetInfoTest(
                                    null, ticker.priceClose, null, 100.0f, 10, symbol,
                                    timestamp, timestamp, OrderSide.BUY
                            );
                            order.lastPrice = ticker.priceClose;

                            // 🔥 CẬP NHẬT GỌI HÀM: Truyền thêm 'marketData' vào cuối
                            manager.processSample(timestamp, order, snapshot, lookupData, marketData);

                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }


}