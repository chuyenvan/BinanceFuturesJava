package com.binance.chuyennd.ai_ml.features.export.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.TreeMap;

public class RunFundingDataCollection15M {
    private static final Logger LOG = LoggerFactory.getLogger(RunFundingDataCollection15M.class);

    public static void main(String[] args) throws Exception {
        SimpleSymbolMapper.getInstance().init(); // Bắt buộc Init Symbol Map
        new RunFundingDataCollection15M().run();
    }

    public void run() throws Exception {
        FundingDataCollectionManager15M manager = new FundingDataCollectionManager15M("storage/training_data_funding_15m");

        // 🔥 Khởi tạo Funding Manager trước để tránh null
        LOG.info("📥 Đang nạp Funding Fee Data vào RAM...");
        com.binance.chuyennd.research.FundingFeeManager.getInstance();

        long startTime = Utils.sdfFile.parse("20210105").getTime(); // Lùi lại 5 ngày để Warmup
        long endTime = System.currentTimeMillis() - 4 * Utils.TIME_DAY; // Trừ hao 3 ngày tương lai
        long currentTime = startTime;

        TreeMap<Long, Map<Short, KlineObjectSimple>> dataCache = new TreeMap<>();

        // Load mồi T và T+1, T+2, T+3
        for (int i = -1; i <= 3; i++) {
            dataCache.putAll(DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTime + (i * Utils.TIME_DAY), 96));
        }

        while (currentTime <= endTime) {
            try {
                // Đọc gối đầu ngày T+4
                dataCache.putAll(DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(currentTime + (4 * Utils.TIME_DAY), 96));

                // Quét 96 block 15m của ngày hiện tại
                for (long ts = currentTime; ts < currentTime + Utils.TIME_DAY; ts += 15 * 60000L) {
                    Map<Short, KlineObjectSimple> snapshot = dataCache.get(ts);
                    if (snapshot == null) continue;

                    // 1. Cập nhật History Manager để tính Indicator
                    manager.updateHistory(snapshot);

                    MarketDataObject15M marketData = DataManagerAerospikeFloatSim.getMarketData15MAtTime(ts);
                    if (marketData == null) continue;

                    // 2. Lọc coin có tốc độ rơi mạnh ở nến 15m
                    for (Map.Entry<Short, KlineObjectSimple> entry : snapshot.entrySet()) {
                        short symId = entry.getKey();
                        KlineObjectSimple ticker = entry.getValue();

                        if (ticker.totalUsdt < 50000) continue; // Vol 15m phải > 50k

                        // Tính tốc độ rơi của nến 15m
                        float rate15m = (ticker.priceClose - ticker.priceOpen) / ticker.priceOpen;

                        // 🔥 FILTER: Chỉ lưu mẫu nếu nến 15m rơi mạnh > 1.5% HOẶC Market đang rơi
                        if (rate15m > -0.015f && marketData.rateDown4HAvg > -0.02f) continue;

                        String symbolStr = SimpleSymbolMapper.getInstance().getSymbol(symId);

                        OrderTargetInfoTest order = new OrderTargetInfoTest(
                                null, ticker.priceClose, null, 100.0f, 10, symbolStr,
                                ts, ts, OrderSide.BUY
                        );
                        order.lastPrice = ticker.priceClose;

                        manager.processSample(ts, order, snapshot, dataCache, marketData);
                    }
                }

                // Xóa data ngày T-2 để giải phóng RAM
                long staleDay = currentTime - 2 * Utils.TIME_DAY;
                dataCache.headMap(staleDay, true).clear();

                manager.exportData();
                LOG.info("✅ Funding Day {} done. Count: {} | Labels: {}",
                        Utils.normalizeDateYYYYMMDD(currentTime),
                        manager.getCollectedCount(), manager.getLabelReport());

            } catch (Exception e) {
                LOG.error("Error processing day " + currentTime, e);
            }
            currentTime += Utils.TIME_DAY;
        }
    }
}