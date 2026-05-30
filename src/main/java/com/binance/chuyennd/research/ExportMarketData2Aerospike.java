/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.text.ParseException;
import java.util.*;

/**
 * @author pc
 */
public class ExportMarketData2Aerospike {

    public static final Logger LOG = LoggerFactory.getLogger(ExportMarketData2Aerospike.class);


    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        ExportMarketData2Aerospike test = new ExportMarketData2Aerospike();
//        test.exportBtcTrendReverse();
        test.exportMarketEntries(null);
//        test.exportFundingFeeBuy();
    }


    public void exportMarketEntries(Long timeRun) throws ParseException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;

        // Nếu truyền vào thời gian chạy tiếp (resume), ta cộng thêm 1 phút để tránh tính lại phút cuối cùng
        if (timeRun != null && timeRun > 0) {
            startTime = Utils.getDate(timeRun); // Trả về đầu ngày đó để quét lại cho chắc
        }

        long endTime = System.currentTimeMillis();

        LOG.info("🚀 Export market entry starting from: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));

        Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
        List<KlineObjectSimple> btcTicker1Msg = new ArrayList<>();

        // Lặp qua từng ngày
        while (startTime <= endTime) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;

            // 🔥 THAY ĐỔI: Khai báo Map chỉ lưu data của 1 ngày để ghi Batch
            TreeMap<Long, MarketDataObject15M> dailyMarketData = new TreeMap<>();

            try {
                LOG.info("Read data from Aerospike: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));

                // ĐỌC TỪ AEROSPIKE
                time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);

                if (time2Tickers != null && !time2Tickers.isEmpty()) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();

                        // Bỏ qua nếu thời gian này đã cũ hơn lastTimestamp (để không tính trùng)
                        if (timeRun != null && time <= timeRun) continue;

                        try {
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            Map<String, Float> symbol2MaxPrice = new HashMap<>();
                            Map<String, Float> symbol2MinPrice = new HashMap<>();

                            KlineObjectSimple btcTicker = symbol2Ticker.get("BTCUSDT");
                            if (btcTicker != null) {
                                btcTicker1Msg.add(btcTicker);
                            }

                            for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                                String symbol = entry1.getKey();
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

                                int sizeRemove = 100;
                                if (tickers.size() > sizeRemove) {
                                    for (int i = 0; i < 5; i++) {
                                        tickers.remove(0);
                                    }
                                }

                                Float priceMax = null;
                                Float minPrice = null;
                                for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                                    int index = tickers.size() - i - 1;
                                    if (index >= 0) {
                                        KlineObjectSimple kline = tickers.get(index);
                                        if (priceMax == null) {
                                            priceMax = kline.maxPrice;
                                        }
                                        priceMax = Math.max(priceMax, kline.maxPrice);

                                        if (minPrice == null) {
                                            minPrice = kline.minPrice;
                                        }
                                        minPrice = Math.min(minPrice, kline.minPrice);
                                    }
                                }

                                symbol2MaxPrice.put(symbol, priceMax);
                                symbol2MinPrice.put(symbol, minPrice);
                            }

                            MarketDataObject15M marketData = MarketBigChangeDetector.calMarketData(symbol2Ticker, symbol2MaxPrice, symbol2MinPrice);
                            if (marketData != null) {
                                MarketLevelChange levelChange = MarketBigChangeDetector.getMarketStatus1M(marketData.rateDownAvg,
                                        marketData.rateUpAvg, marketData.rateDown4HAvg);

                                // 🔥 THAY ĐỔI: Put data vào map của ngày thay vì map tổng
                                if (levelChange != null) {
                                    dailyMarketData.put(time, marketData);
                                } else {
                                    dailyMarketData.put(time, new MarketDataObject15M(marketData.rateDownAvg,
                                            marketData.rateUpAvg, marketData.rateDown4HAvg));
                                }
                            }
                        } catch (Exception e) {
                            LOG.info("Error process time: {}", Utils.normalizeDateYYYYMMDDHHmm(time));
                            e.printStackTrace();
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }

            // =========================================================
            // 🔥 THAY ĐỔI LỚN: GHI DỮ LIỆU LÊN AEROSPIKE SAU MỖI NGÀY
            // =========================================================
            if (!dailyMarketData.isEmpty()) {
                DataManagerAerospikeFloatSim.saveMarketDataBatch15M(dailyMarketData, null);
                LOG.info("✅ Saved {} market entries to Aerospike for day {}.", dailyMarketData.size(), Utils.normalizeDateYYYYMMDD(startTime));
            }

            startTime += Utils.TIME_DAY;
        }

        LOG.info("🎉 Export Market Data to Aerospike DONE!");
    }

}
