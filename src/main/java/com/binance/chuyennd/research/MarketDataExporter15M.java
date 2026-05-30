package com.binance.chuyennd.research;

import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class MarketDataExporter15M {

    public static final Logger LOG = LoggerFactory.getLogger(MarketDataExporter15M.class);

    // Ở khung 15m, 16 cây nến = 4 Giờ
    private static final int LOOKBACK_4H_CANDLES = 16;

    public static void main(String[] args) throws ParseException {
        new MarketDataExporter15M().exportMarketEntries(null);
    }

    public void exportMarketEntries(Long timeRun) throws ParseException {
        Long startTime = Utils.sdfFile.parse("20210101").getTime() + 7 * Utils.TIME_HOUR; // Default start time

        if (timeRun != null && timeRun > 0) {
            startTime = Utils.getDate(timeRun);
        }

        long endTime = System.currentTimeMillis();

        LOG.info("🚀 Export Market Data 15M (Looking back 4H) starting from: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));

        Map<Short, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
        WritePolicy writePolicy = new WritePolicy();
        writePolicy.sendKey = true;

        // Lặp qua từng ngày
        while (startTime <= endTime) {
            // 96 block 15m mỗi ngày
            TreeMap<Long, Map<Short, KlineObjectSimple>> time2Tickers;
            TreeMap<Long, MarketDataObject15M> dailyMarketData = new TreeMap<>();

            try {
                LOG.info("Read data 15M from Aerospike (.224): {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));

                // Gọi hàm đọc nến 15m (Bác đã thêm ở bước trước vào DataManagerAerospikeFloatSim)
                time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike15mCustom(startTime, 96);

                if (time2Tickers != null && !time2Tickers.isEmpty()) {
                    for (Map.Entry<Long, Map<Short, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();

                        if (timeRun != null && time <= timeRun) continue;

                        try {
                            Map<Short, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            Map<Short, Float> symbol2MaxPrice = new HashMap<>();
                            Map<Short, Float> symbol2MinPrice = new HashMap<>();

                            for (Map.Entry<Short, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                                Short symbol = entry1.getKey();
                                if (Constants.diedSymbol.contains(symbol)) {
                                    continue;
                                }
                                KlineObjectSimple ticker = entry1.getValue();
                                if (!Utils.isTickerAvailable(ticker)) {
                                    continue;
                                }

                                List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                if (tickers == null) {
                                    tickers = new ArrayList<>();
                                    symbol2LastTickers.put(symbol, tickers);
                                }
                                tickers.add(ticker);

                                // Giữ lại đủ số lượng nến để tính 4H
                                int sizeRemove = LOOKBACK_4H_CANDLES + 5;
                                if (tickers.size() > sizeRemove) {
                                    tickers.remove(0);
                                }

                                Float priceMax = null;
                                Float minPrice = null;

                                // Duyệt ngược 16 nến (4 giờ)
                                int loopCount = Math.min(tickers.size(), LOOKBACK_4H_CANDLES);
                                for (int i = 0; i < loopCount; i++) {
                                    int index = tickers.size() - i - 1;
                                    KlineObjectSimple kline = tickers.get(index);

                                    if (priceMax == null || priceMax < kline.maxPrice) {
                                        priceMax = kline.maxPrice;
                                    }
                                    if (minPrice == null || minPrice > kline.minPrice) {
                                        minPrice = kline.minPrice;
                                    }
                                }

                                symbol2MaxPrice.put(symbol, priceMax);
                                symbol2MinPrice.put(symbol, minPrice);
                            }

                            // Gọi hàm mới tính MarketData15M
                            MarketDataObject15M marketData = MarketBigChangeDetector.calMarketData15M(symbol2Ticker, symbol2MaxPrice, symbol2MinPrice);
                            if (marketData != null) {
                                dailyMarketData.put(time, marketData);
                            }
                        } catch (Exception e) {
                            LOG.error("Error process time: {}", Utils.normalizeDateYYYYMMDDHHmm(time), e);
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }

            // GHI DỮ LIỆU LÊN AEROSPIKE (Khuyên dùng set mới trên Node 224 hoặc 226)
            if (!dailyMarketData.isEmpty()) {
                DataManagerAerospikeFloatSim.saveMarketDataBatch15M(dailyMarketData, writePolicy);
                LOG.info("✅ Saved {} market entries (15M format) to Aerospike for day {}.", dailyMarketData.size(), Utils.normalizeDateYYYYMMDD(startTime));
            }

            startTime += Utils.TIME_DAY;
        }

        LOG.info("🎉 Export Market Data 15M to Aerospike DONE!");
    }


}