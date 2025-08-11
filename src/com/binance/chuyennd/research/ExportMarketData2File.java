/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
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
        test.exportMarketEntries();
//        test.exportFundingFeeBuy();
    }

    private void exportFundingFeeBuy() throws ParseException {
        Long timeStart = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
        TreeMap<Long, Set<String>> time2SymbolFundingBuy = new TreeMap<>();
        while (true) {
            time2SymbolFundingBuy.put(timeStart, FundingFeeManager.getInstance().getFundingBuyNew(timeStart));
            timeStart += Utils.TIME_MINUTE;
            if (timeStart > System.currentTimeMillis() - Utils.TIME_HOUR) {
                break;
            }
            if (timeStart == Utils.getDate(timeStart)) {
                LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(timeStart));
            }
        }
//        Storage.writeObject2File(Configs.FILE_ENTRY_FUNDING_BUY, time2SymbolFundingBuy);
    }

    public void exportBtcTrendReverse() {
        TreeMap<Long, Double> timeBtcReverse;
        List<KlineObjectSimple> ticker1Ms =
                (List<KlineObjectSimple>) StorageSnappy.readObjectFromFile(Configs.FOLDER_TICKER_1M + Constants.SYMBOL_PAIR_BTC);
        Long timeExport = ticker1Ms.get(0).startTime.longValue();
        if (!new File(Configs.FILE_ENTRY_BTC_REVERSE).exists()) {
            timeBtcReverse = new TreeMap<>();
        } else {
            timeBtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);
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
        StorageSnappy.writeObject2File(Configs.FILE_ENTRY_BTC_REVERSE, timeBtcReverse);
    }

    public void exportMarketEntries() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Long timeExport = startTime;
        long endTime = System.currentTimeMillis();
        TreeMap<Long, MarketRateChange> time2MarketRateChange;
        TreeMap<Long, MarketDataObject> time2MarketData;

        if (!new File(Configs.FILE_MARKET_RATE_CHANGE).exists()) {
            time2MarketRateChange = new TreeMap<>();
        } else {
            time2MarketRateChange = (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
            timeExport = time2MarketRateChange.lastKey();
            startTime = Utils.getDate(time2MarketRateChange.lastKey());
        }
        if (!new File(Configs.FILE_ENTRY_MARKET_LEVEL).exists()) {
            time2MarketData = new TreeMap<>();
        } else {
            time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
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
//                            time2SymbolFundingBuy.put(time, FundingFeeManager.getInstance().getFundingBuyNew(time));
//                            if (time == Utils.sdfFileHour.parse("20250603 11:00").getTime()) {
//                                System.out.println("Debug");
//                            }
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            Map<String, Double> symbol2MaxPrice = new HashMap<>();
                            Map<String, Double> symbol2MinPrice = new HashMap<>();
                            TreeMap<Double, String> rate2Max = new TreeMap<>();

                            for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {

                                String symbol = entry1.getKey();
//                                if (StringUtils.equals(symbol, "NEIROETHUSDT")) {
//                                    System.out.println("Debug");
//                                }
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


                            if (time2MarketRateChange.isEmpty() || time2MarketRateChange.lastKey() < time) {
                                MarketDataObject marketData;
                                marketData = MarketBigChangeDetectorTest.calMarketData(symbol2Ticker, symbol2MaxPrice, symbol2MinPrice);
                                if (marketData != null) {
                                    MarketLevelChange levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                                            marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg);
                                    if (levelChange != null) {
                                        marketData.rate2Min.clear();
                                        marketData.level = levelChange;
                                        time2MarketData.put(time, marketData);
                                    }
                                    time2MarketRateChange.put(time, new MarketRateChange(marketData.rateDownAvg, marketData.rateDown15MAvg,
                                            marketData.rateUpAvg));

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
        StorageSnappy.writeObject2File(Configs.FILE_ENTRY_MARKET_LEVEL, time2MarketData);
        StorageSnappy.writeObject2File(Configs.FILE_MARKET_RATE_CHANGE, time2MarketRateChange);


    }

    public MarketDataObject cloneDataWithRateMin15m(MarketDataObject marketData) {
        MarketDataObject result = new MarketDataObject(marketData.rateDownAvg, marketData.rateUpAvg, marketData.rateBtc,
                marketData.level, marketData.symbolsTopDown);
        result.rateDown15MAvg = marketData.rateDown15MAvg;
        result.rateBtcUp15M = marketData.rateBtcUp15M;
        result.rateBtcDown15M = marketData.rateBtcDown15M;
        result.rate2Min = marketData.rate2Min;
        return result;
    }


}
