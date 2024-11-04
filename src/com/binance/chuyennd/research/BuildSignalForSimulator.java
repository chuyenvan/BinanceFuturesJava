/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
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
public class BuildSignalForSimulator {

    public static final Logger LOG = LoggerFactory.getLogger(BuildSignalForSimulator.class);

    public static void main(String[] args) throws ParseException, IOException {
        BuildSignalForSimulator test = new BuildSignalForSimulator();
        test.statisticAll();
    }

    private void statisticAll() throws ParseException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<Long, MarketDataObject> timesTradeMarket = new HashMap<>();
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
            try {
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                LOG.info("Read file: {} {}", Utils.normalizeDateYYYYMMDD(startTime), timesTradeMarket.size());
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        Map<String, Double> symbol2MaxPrice = new HashMap<>();
                        Map<String, Double> symbol2MinPrice = new HashMap<>();
                        Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                        // update order Old
                        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                            String symbol = entry1.getKey();
                            if (Constants.diedSymbol.contains(symbol)) {
                                continue;
                            }
                            KlineObjectSimple ticker = entry1.getValue();

                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                            if (tickers == null) {
                                tickers = new ArrayList<>();
                                symbol2LastTickers.put(symbol, tickers);
                            }
                            tickers.add(ticker);
                            if (tickers.size() > 500) {
                                for (int i = 0; i < 200; i++) {
                                    tickers.remove(0);
                                }
                            }
                            Double priceMax = null;
                            Double priceMin = null;
                            for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                                int index = tickers.size() - i - 1;
                                if (index >= 0) {
                                    KlineObjectSimple kline = tickers.get(index);
                                    if (priceMax == null || priceMax < kline.maxPrice) {
                                        priceMax = kline.maxPrice;
                                    }
                                    if (priceMin == null || priceMin > kline.minPrice) {
                                        priceMin = kline.minPrice;
                                    }
                                }
                            }
                            symbol2MaxPrice.put(symbol, priceMax);
                            symbol2MinPrice.put(symbol, priceMin);
                        }
                        MarketDataObject marketData = calMarketData(symbol2Ticker, symbol2MaxPrice, symbol2MinPrice);
                        MarketLevelChange levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                                marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg, marketData.rateUp15MAvg, marketData.rateBtcDown15M);
                        if (levelChange != null) {
                            marketData.level = levelChange;
                            timesTradeMarket.put(time, marketData);
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
        Storage.writeObject2File("target/entry/time2Market_" + Configs.NUMBER_TICKER_CAL_RATE_CHANGE + ".data", timesTradeMarket);

    }


    private MarketDataObject calMarketData(Map<String, KlineObjectSimple> symbol2Ticker,
                                           Map<String, Double> symbol2MaxPrice, Map<String, Double> symbol2MinPrice) {
        TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateTotal2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
        TreeMap<Double, String> rate2Max = new TreeMap<>();
        TreeMap<Double, String> rate2Min = new TreeMap<>();
        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = entry1.getValue();
            if (Utils.isTickerAvailable(ticker)) {
                Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                rateDown2Symbols.put(rateChange, symbol);
                rateUp2Symbols.put(-rateChange, symbol);
                rateTotal2Symbols.put(Utils.rateOf2Double(ticker.minPrice, ticker.maxPrice), symbol);
                Double maxPrice = symbol2MaxPrice.get(symbol);
                if (maxPrice != null) {
                    rate2Max.put(Utils.rateOf2Double(ticker.priceClose, maxPrice), symbol);
                }
                Double minPrice = symbol2MinPrice.get(symbol);
                if (minPrice != null) {
                    rate2Min.put(Utils.rateOf2Double(minPrice, ticker.priceClose), symbol);
                }
            }
        }

        KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
        Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
        Double rateChangeDownAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateDown2Symbols, 50);
        Double rateChangeUpAvg = -MarketBigChangeDetectorTest.calRateLossAvg(rateUp2Symbols, 50);
        List<String> symbolsTopDown = MarketBigChangeDetectorTest.getTopSymbolSimple(rateDown2Symbols,
                Configs.NUMBER_ENTRY_EACH_SIGNAL, null);
        MarketDataObject result = new MarketDataObject(rateChangeDownAvg, rateChangeUpAvg,  btcRateChange, btcTicker.totalUsdt,
                null, symbolsTopDown);
        result.rateDown2Symbols = rateDown2Symbols;
        result.rateUp2Symbols = rateTotal2Symbols;
        result.rate2Max = rate2Max;
        return result;
    }

}
