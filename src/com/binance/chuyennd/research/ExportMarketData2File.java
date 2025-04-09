/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.grid.Price4hManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
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
        test.exportMarketEntries();
    }

    public void exportBtcTrendReverse() {
        TreeMap<Long, Double> timeBtcReverse;
        List<KlineObjectSimple> ticker1Ms =
                (List<KlineObjectSimple>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1M + Constants.SYMBOL_PAIR_BTC);
        Long timeExport = ticker1Ms.get(0).startTime.longValue();
        if (!new File(Configs.FILE_ENTRY_BTC_REVERSE).exists()) {
            timeBtcReverse = new TreeMap<>();
        } else {
            timeBtcReverse = (TreeMap<Long, Double>) Storage.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);
            timeExport = timeBtcReverse.lastKey();
        }
        LOG.info("Export btc trend reverse: {}", Utils.normalizeDateYYYYMMDDHHmm(timeExport));
        List<KlineObjectSimple> ticker2Check = new ArrayList<>();
        for (int i = 0; i < Configs.BTC_TREND_REVERSE_DURATION; i++) {
            ticker2Check.add(ticker1Ms.get(i));
        }
        for (int i = Configs.BTC_TREND_REVERSE_DURATION; i < ticker1Ms.size(); i++) {
            ticker2Check.remove(0);
            ticker2Check.add(ticker1Ms.get(i));
            long time = ticker1Ms.get(i).startTime.longValue();
            if (timeBtcReverse.isEmpty() || timeBtcReverse.lastKey() < time) {
                Double rateBtcTrendReverse = MarketBigChangeDetectorTest.isBtcTrendReverse(
                        ticker2Check, Configs.BTC_TREND_REVERSE_RATE_MAX, Configs.BTC_TREND_REVERSE_RATE_MIN);
                if (rateBtcTrendReverse != null) {
                    timeBtcReverse.put(ticker2Check.get(ticker2Check.size() - 1).startTime.longValue(), rateBtcTrendReverse);
                }
            }
        }
        Storage.writeObject2File(Configs.FILE_ENTRY_BTC_REVERSE, timeBtcReverse);
    }

    public void exportMarketEntries() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Long timeExport = startTime;
        long endTime = Utils.sdfFile.parse("20220101").getTime();
        TreeMap<Long, MarketDataObject> time2MarketData;
        TreeMap<Long, MarketDataObject> time2SellSignal1;
        TreeMap<Long, MarketDataObject> time2SellSignal2;
        TreeMap<Long, TreeMap<Double, String>> time2RateMax2d;
        TreeMap<Long, TreeMap<Double, String>> time2RateMin2d;
        if (!new File(Configs.FILE_ENTRY_MARKET_LEVEL).exists()) {
            time2MarketData = new TreeMap<>();
            endTime = Utils.sdfFile.parse("20220101").getTime();
        } else {
            time2MarketData = (TreeMap<Long, MarketDataObject>) Storage.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
            timeExport = time2MarketData.lastKey();
            startTime = Utils.getDate(time2MarketData.lastKey()) - Utils.TIME_DAY;
            endTime = System.currentTimeMillis();
        }
        if (!new File(Configs.FILE_ENTRY_SELL_SIGNAL_1).exists()) {
            time2SellSignal1 = new TreeMap<>();
        } else {
            time2SellSignal1 = (TreeMap<Long, MarketDataObject>) Storage.readObjectFromFile(Configs.FILE_ENTRY_SELL_SIGNAL_1);
        }
        if (!new File(Configs.FILE_ENTRY_SELL_SIGNAL_2).exists()) {
            time2SellSignal2 = new TreeMap<>();
        } else {
            time2SellSignal2 = (TreeMap<Long, MarketDataObject>) Storage.readObjectFromFile(Configs.FILE_ENTRY_SELL_SIGNAL_2);
        }
        if (!new File(Configs.FILE_ENTRY_RATE_MAX_2D).exists()) {
            time2RateMax2d = new TreeMap<>();
        } else {
            time2RateMax2d = (TreeMap<Long, TreeMap<Double, String>>) Storage.readObjectFromFile(Configs.FILE_ENTRY_RATE_MAX_2D);
        }
        if (!new File(Configs.FILE_ENTRY_RATE_MIN_2D).exists()) {
            time2RateMin2d = new TreeMap<>();
        } else {
            time2RateMin2d = (TreeMap<Long, TreeMap<Double, String>>) Storage.readObjectFromFile(Configs.FILE_ENTRY_RATE_MIN_2D);
        }
        LOG.info("Export market entry: {}", Utils.normalizeDateYYYYMMDDHHmm(timeExport));
        Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                LOG.info("Read file ticker: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        try {
//                        if (time == Utils.sdfFileHour.parse("20241106 14:42").getTime()) {
//                            System.out.println("Debug");
//                        }
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            Map<String, Double> symbol2MaxPrice = new HashMap<>();
                            Map<String, Double> symbol2MinPrice = new HashMap<>();
                            TreeMap<Double, String> rate2Max = new TreeMap<>();
                            TreeMap<Double, String> rate2Max2d = new TreeMap<>();
                            TreeMap<Double, String> rate2Min2d = new TreeMap<>();

                            for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {

                                String symbol = entry1.getKey();
                                if (Constants.diedSymbol.contains(symbol)) {
                                    continue;
                                }
                                KlineObjectSimple ticker = entry1.getValue();
                                if (!Utils.isTickerAvailable(ticker)) {
                                    continue;
                                }

                                if (time == Utils.getTimeInterval5m(time)) {
                                    Double priceMin2d = Price4hManager.getInstance().getPriceMinIn2D(symbol, time);
                                    Double priceMax2d = Price4hManager.getInstance().getPriceMaxIn2D(symbol, time);
                                    if (priceMax2d != null && Utils.rateOf2Double(ticker.priceClose, priceMax2d) < -0.1
                                            && priceMin2d != null && Utils.rateOf2Double(ticker.priceClose, priceMin2d) > 0.3) {
                                        rate2Max2d.put(Utils.rateOf2Double(ticker.priceClose, priceMax2d), symbol);
                                        rate2Min2d.put(-Utils.rateOf2Double(ticker.priceClose, priceMin2d), symbol);
                                    }
                                }


                                List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                if (tickers == null) {
                                    tickers = new ArrayList<>();
                                    symbol2LastTickers.put(symbol, tickers);
                                }
                                tickers.add(ticker);
                                int sizeRemove = 25;
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
                                rate2Max.put(Utils.rateOf2Double(ticker.priceClose, priceMax), symbol);
                                symbol2MinPrice.put(symbol, minPrice);

                            }
                            if (!rate2Max2d.isEmpty()) {
                                time2RateMax2d.put(time, rate2Max2d);
                            }
                            if (!rate2Min2d.isEmpty()) {
                                time2RateMin2d.put(time, rate2Min2d);
                            }
                            if (time2MarketData.isEmpty() || time2MarketData.lastKey() < time) {
                                MarketDataObject marketData;
                                marketData = MarketBigChangeDetectorTest.calMarketData(symbol2Ticker, symbol2MaxPrice, symbol2MinPrice);
                                if (marketData != null) {
                                    if (marketData.rateDown15MAvg < -0.025) {
                                        time2SellSignal1.put(time, cloneData(marketData));
                                    }
                                    if (marketData.rateUpAvg > 0.007) {
                                        time2SellSignal2.put(time, cloneData(marketData));
                                    }
                                    MarketLevelChange levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                                            marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg, marketData.rateUp15MAvg,
                                            marketData.rateBtcDown15M);
                                    if (levelChange != null) {
                                        marketData.rate2Min.clear();
//                                        marketData.rateUp2Symbols.clear();
//                                        marketData.rateDown2Symbols.clear();
                                        time2MarketData.put(time, marketData);
                                    }

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
            startTime += Utils.TIME_DAY;
//            if (startTime > System.currentTimeMillis()) {
            if (startTime > endTime) {
                break;
            }
        }
        Storage.writeObject2File(Configs.FILE_ENTRY_MARKET_LEVEL, time2MarketData);
        Storage.writeObject2File(Configs.FILE_ENTRY_SELL_SIGNAL_1, time2SellSignal1);
        Storage.writeObject2File(Configs.FILE_ENTRY_SELL_SIGNAL_2, time2SellSignal2);
        Storage.writeObject2File(Configs.FILE_ENTRY_RATE_MAX_2D, time2RateMax2d);
        Storage.writeObject2File(Configs.FILE_ENTRY_RATE_MIN_2D, time2RateMin2d);
    }

    public MarketDataObject cloneData(MarketDataObject marketData) {
        MarketDataObject result = new MarketDataObject(marketData.rateDownAvg, marketData.rateUpAvg, marketData.rateBtc,
                marketData.volumeBtc, marketData.level, marketData.symbolsTopDown);
        result.rateDown15MAvg = marketData.rateDown15MAvg;
        result.rateUp15MAvg = marketData.rateUp15MAvg;
        result.rateBtcUp15M = marketData.rateBtcUp15M;
        result.rateBtcDown15M = marketData.rateBtcDown15M;
        result.rate2Min = marketData.rate2Min;
        return result;
    }

}
