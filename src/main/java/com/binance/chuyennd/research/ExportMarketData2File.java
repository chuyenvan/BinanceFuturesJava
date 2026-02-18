/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.text.ParseException;
import java.util.*;

/**
 * @author pc
 */
public class ExportMarketData2File {

    public static final Logger LOG = LoggerFactory.getLogger(ExportMarketData2File.class);
    public String TIME_RUN = Configs.getString("TIME_RUN");


    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        ExportMarketData2File test = new ExportMarketData2File();
//        test.exportBtcTrendReverse();
        test.exportMarketEntries("20251215");
//        test.exportFundingFeeBuy();
    }



    public void exportMarketEntries(String timeRun) throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        if (timeRun != null) {
            startTime = Utils.sdfFile.parse(timeRun).getTime() + 7 * Utils.TIME_HOUR;
        }
        Long timeExport = startTime;
        long endTime = System.currentTimeMillis();
        TreeMap<Long, MarketDataObject> time2MarketData;
        if (!new File(Configs.FILE_ENTRY_MARKET_LEVEL).exists()) {
            time2MarketData = new TreeMap<>();
        } else {
            time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
            timeExport = time2MarketData.lastKey();
            startTime = Utils.getDate(time2MarketData.lastKey());
        }

        LOG.info("Export market entry: {}", Utils.normalizeDateYYYYMMDDHHmm(timeExport));
        Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
        List<KlineObjectSimple> btcTicker1Msg = new ArrayList<>();
        //get data - ĐÃ SỬA: đọc từ Aerospike thay vì file
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                LOG.info("Read data from Aerospike: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));

                // ĐỌC TỪ AEROSPIKE THAY VÌ FILE
                time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);

                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();

                        try {
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            Map<String, Double> symbol2MaxPrice = new HashMap<>();
                            Map<String, Double> symbol2MinPrice = new HashMap<>();
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

                                Double priceMax = null;
                                Double minPrice = null;
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

//                            if (time2MarketData.isEmpty() || time2MarketData.lastKey() < time) {
                            MarketDataObject marketData;
                            marketData = MarketBigChangeDetector.calMarketData(symbol2Ticker, symbol2MaxPrice, symbol2MinPrice);
                            if (marketData != null) {
                                MarketLevelChange levelChange = MarketBigChangeDetector.getMarketStatus1M(marketData.rateDownAvg,
                                        marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg);
                                if (levelChange != null) {
                                    time2MarketData.put(time, marketData);
                                } else {
                                    time2MarketData.put(time, new MarketDataObject(marketData.rateDownAvg,
                                            marketData.rateUpAvg, marketData.rateDown15MAvg));
                                }
                            }
//                            }
                        } catch (Exception e) {
                            LOG.info("Error process time: {}", Utils.normalizeDateYYYYMMDDHHmm(time));
                            e.printStackTrace();
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            startTime += Utils.TIME_DAY;
            if (startTime > endTime) {
                break;
            }
        }

        // 3. Lưu ra 1 file duy nhất
        // Configs.FILE_ENTRY_MARKET_LEVEL: Đường dẫn file bạn muốn lưu
        String filePath = Configs.FILE_ENTRY_MARKET_LEVEL;
        // Gọi hàm lưu Snappy cũ của bạn
        StorageSnappy.writeObject2File(Configs.FILE_ENTRY_MARKET_LEVEL, time2MarketData);
        // Log kết quả
        LOG.info("Refactor done. Exported " + time2MarketData.size() + " entries to single file: " + filePath);
    }

}
