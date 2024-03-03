/*
 * Copyright 2023 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.client;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.object.TrendObject;
import com.binance.chuyennd.object.TrendObjectDetail;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.object.sw.SideWayObject;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import java.util.List;
import com.binance.client.constant.Constants;
import java.io.File;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import kotlin.collections.ArrayDeque;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class TickerSpotHelper {

    public static final String FILE_DATA_TICKER = "storage/data/ticker/symbols-INTERVAL.data";
    public static final String FILE_DATA_TICKER_TIME = "storage/data/ticker/symbols-INTERVAL-TIME.data";
    public static final Logger LOG = LoggerFactory.getLogger(TickerSpotHelper.class);

    public static TreeMap<Double, String> getMaxRateWithTime(long timeCheckPoint, OrderSide side, String interval,
            int numberKline, long startTime, Map<String, List<KlineObjectNumber>> allSymbolTickers) {
        TreeMap<Double, String> rate2Symbol = new TreeMap<>();
        for (Map.Entry<String, List<KlineObjectNumber>> entry : allSymbolTickers.entrySet()) {
            String symbol = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            try {
                Double maxPrice = null;
                Double minPrice = null;
                Double priceOpen = null;
                KlineObjectNumber klineCheckPoint = null;
                KlineObjectNumber klineCheckPoint24hr = null;
//                long timeCheckPoint24hrAgo = timeCheckPoint - 1 * Utils.TIME_HOUR;
                long timeCheckPoint24hrAgo = timeCheckPoint;
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber ticker = tickers.get(i);
                    if (ticker.startTime.longValue() == timeCheckPoint24hrAgo) {
                        klineCheckPoint24hr = ticker;
                    }
                    if (ticker.startTime.longValue() == timeCheckPoint) {
                        klineCheckPoint = ticker;
                        priceOpen = klineCheckPoint.priceClose;
                        for (int j = i + 1; j < i + 1 + numberKline; j++) {
                            if (j < tickers.size()) {
                                ticker = tickers.get(j);
                                if (maxPrice == null || ticker.maxPrice > maxPrice) {
                                    maxPrice = ticker.maxPrice;
                                }
                                if (minPrice == null || ticker.minPrice < minPrice) {
                                    minPrice = ticker.minPrice;
                                }
                            }
                        }
                    }
                }
                if (klineCheckPoint24hr == null) {
                    klineCheckPoint24hr = klineCheckPoint;
                }
                if (priceOpen != null) {
                    Double rateDown = (priceOpen - minPrice) / priceOpen;
                    Double rateUp = (maxPrice - priceOpen) / priceOpen;
                    double rateKlineCheckPoint = 100 * Utils.rateOf2Double(klineCheckPoint24hr.priceOpen, klineCheckPoint.priceClose);
                    if (side.equals(OrderSide.BUY)) {
                        rate2Symbol.put(rateUp, symbol + "#" + priceOpen + "#" + maxPrice + "#" + minPrice + "#" + Utils.rateOf2Double(klineCheckPoint.maxPrice, klineCheckPoint.minPrice) + "#" + rateKlineCheckPoint);
                    } else {
                        rateKlineCheckPoint = 100 * Utils.rateOf2Double(klineCheckPoint.priceClose, klineCheckPoint24hr.priceOpen);
                        rate2Symbol.put(rateDown, symbol + "#" + priceOpen + "#" + minPrice + "#" + maxPrice + "#" + Utils.rateOf2Double(klineCheckPoint.maxPrice, klineCheckPoint.minPrice) + "#" + rateKlineCheckPoint);
                    }
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return rate2Symbol;
    }

    public static KlineObjectNumber getTickerByTime(String symbol, String interval, long time) {
        String urlM1 = Constants.URL_TICKER_SPOT.replace("xxxxxx", symbol) + interval;
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            for (List<Object> allKline : allKlines) {
                KlineObjectNumber kline = KlineObjectNumber.convertString2Kline(allKline);
                if (kline.startTime.longValue() <= time && kline.endTime >= time) {
                    return kline;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static List<KlineObjectNumber> getTickersByTime(String symbol, String interval, long time) {
        String urlM1 = Constants.URL_TICKER_SPOT.replace("xxxxxx", symbol) + interval;
        String respon = HttpRequest.getContentFromUrl(urlM1);
        List<KlineObjectNumber> results = new ArrayList();
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            for (List<Object> allKline : allKlines) {
                results.add(KlineObjectNumber.convertString2Kline(allKline));

            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return results;
    }

    public static KlineObjectNumber getLastTicker(String symbol, String interval) {
        String urlM1 = Constants.URL_TICKER_SPOT.replace("xxxxxx", symbol) + interval;
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            return KlineObjectNumber.convertString2Kline(allKlines.get(allKlines.size() - 1));
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static OrderSide getCurrentSide(String symbol, String interval) {
        String urlM1 = Constants.URL_TICKER_SPOT.replace("xxxxxx", symbol) + interval;
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            KlineObjectNumber kline = KlineObjectNumber.convertString2Kline(allKlines.get(allKlines.size() - 1));
            OrderSide orderSide = OrderSide.BUY;
            if (kline.priceOpen > kline.priceClose) {
                orderSide = OrderSide.SELL;
            }
            return orderSide;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static List<KlineObjectNumber> getTicker(String symbol, String interval) {
        String urlM1 = Constants.URL_TICKER_SPOT.replace("xxxxxx", symbol) + interval;
        String respon = HttpRequest.getContentFromUrl(urlM1);
        List<KlineObjectNumber> results = new ArrayList();
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            for (List<Object> allKline : allKlines) {
                results.add(KlineObjectNumber.convertString2Kline(allKline));

            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return results;
    }

    public static List<KlineObjectNumber> getTickerWithStartTimeFull(String symbol, String interval, long startTime) {
        String url = Constants.URL_TICKER_SPOT_STARTTIME.replace("xxxxxx", symbol) + interval;
        List<KlineObjectNumber> results = new ArrayList();
        Long time = startTime;
        while (true) {
            try {
                String urlData = url.replace("tttttt", time.toString());
                String respon = HttpRequest.getContentFromUrl(urlData);
                List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
                for (List<Object> allKline : allKlines) {
                    results.add(KlineObjectNumber.convertString2Kline(allKline));
                }
                if (results.get(results.size() - 1).endTime.longValue() > System.currentTimeMillis()) {
                    break;
                } else {
                    time = results.get(results.size() - 1).endTime.longValue() + 1;
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return results;
    }

    public static List<KlineObjectNumber> getTickerWithStartTime(String symbol, String interval, Long startTime) {
        String url = Constants.URL_TICKER_SPOT_STARTTIME.replace("xxxxxx", symbol) + interval;
        List<KlineObjectNumber> results = new ArrayList();
        try {
            String urlData = url.replace("tttttt", startTime.toString());
            String respon = HttpRequest.getContentFromUrl(urlData);
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            for (List<Object> allKline : allKlines) {
                results.add(KlineObjectNumber.convertString2Kline(allKline));
            }

        } catch (Exception e) {
            e.printStackTrace();
        }

        return results;
    }

    public static OrderSide getCurrentTrendWithInterval(String symbol, String interval) {
        try {
            KlineObjectNumber ticker = getLastTicker(symbol, interval);
            if (ticker.priceClose > ticker.priceOpen) {
                return OrderSide.BUY;
            } else {
                return OrderSide.SELL;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static OrderSide getCurrentTrendLongTime(String symbol, Integer numberDay) {
        try {
            List<KlineObjectNumber> tickers = getTicker(symbol, Constants.INTERVAL_1D);
            Double maxPrice = null;
            Double minPrice = null;
            Double currentPirce = tickers.get(tickers.size() - 1).priceClose;
            if (tickers.size() > 60) {
                for (int i = 0; i < 60; i++) {
                    KlineObjectNumber ticker = tickers.get(tickers.size() - 1 - i);
                    if (maxPrice == null || maxPrice < ticker.maxPrice) {
                        maxPrice = ticker.maxPrice;
                    }
                    if (minPrice == null || minPrice > ticker.minPrice) {
                        minPrice = ticker.minPrice;
                    }
                }
            }
            LOG.info("Max: {} Min: {} current: {}", maxPrice, minPrice, currentPirce);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static Set<String> getAllSymbol() {
        Set<String> results = new HashSet<>();
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                results.add(ticker.getSymbol());
            }
        }
        return results;
    }

    public static Map<String, Double> getAllVolume24hr() {
        Map<String, Double> symbol2Volume24hr = new HashMap<>();
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                symbol2Volume24hr.put(ticker.getSymbol(), Double.parseDouble(ticker.getQuoteVolume()));
            }
        }
        return symbol2Volume24hr;
    }

    public static Map<String, Double> getAllLastPrice() {
        Map<String, Double> symbol2Volume24hr = new HashMap<>();
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                symbol2Volume24hr.put(ticker.getSymbol(), Double.parseDouble(ticker.getLastPrice()));
            }
        }
        return symbol2Volume24hr;
    }

    public static Map<String, TickerStatistics> getAllTicker24hr() {
        Map<String, TickerStatistics> symbol2Ticker24hr = new HashMap<>();
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                symbol2Ticker24hr.put(ticker.getSymbol(), ticker);
            }
        }
        return symbol2Ticker24hr;
    }

    public static void main(String[] args) throws ParseException {
//        System.out.println(TickerHelper.getCurrentSide("BIGTIMEUSDT", Constants.INTERVAL_1D));

//        Map<String, List<KlineObjectNumber>> symbol2Tickers = TickerHelper.getAllKlineStartTime(Constants.INTERVAL_15M, Utils.getStartTimeDayAgo(300));
//        System.out.println("Done: " + symbol2Tickers.size());
//        for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Tickers.entrySet()) {
//            Object symbol = entry.getKey();
//            List<KlineObjectNumber> tickers = entry.getValue();
//            LOG.info("{} {}", symbol, tickers.size());
//        }
        testGetTicker();
//        getCurrentTrendLongTime(Contanst.SYMBOL_PAIR_BTC, 60);
//        System.out.println(getCurrentTrendWithInterval("DYDXUSDT", Contanst.INTERVAL_15M));
//        System.out.println(Utils.toJson(getLastTicker("DYDXUSDT", Contanst.INTERVAL_15M)));
//        System.out.println(Utils.toJson(getLastTicker("WLDUSDT", Contanst.INTERVAL_15M)));
//        System.out.println(Utils.toJson(getLastTicker(Contanst.SYMBOL_PAIR_BTC, Contanst.INTERVAL_15M)));
    }

    public static Double getMaxPrice(List<KlineObjectNumber> kline1Ds, int numberTicker) {
        Double maxPrice = null;
        int counter = 0;
        for (int i = 0; i < kline1Ds.size(); i++) {
            KlineObjectNumber kline1D = kline1Ds.get(kline1Ds.size() - 1 - i);
            counter++;
            if (counter >= numberTicker) {
                break;
            }
            if (maxPrice == null || maxPrice < kline1D.maxPrice) {
                maxPrice = kline1D.maxPrice;
            }
        }
        return maxPrice;
    }

    public static KlineObjectNumber extractKline(List<KlineObjectNumber> kline1Ds, int numberTicker, int startIndex) {
        Double maxPrice = null;
        int counter = 0;
        Double minPrice = null;
        Double lastPrice = null;
        if (startIndex < 0) {
            startIndex = 0;
        }
        for (int i = startIndex; i < kline1Ds.size(); i++) {
            KlineObjectNumber kline1D = kline1Ds.get(i);
            counter++;
            if (counter > numberTicker) {
                break;
            }
            lastPrice = kline1D.priceClose;
            if (minPrice == null || minPrice > kline1D.minPrice) {
                minPrice = kline1D.minPrice;
            }
            if (maxPrice == null || maxPrice < kline1D.maxPrice) {
                maxPrice = kline1D.maxPrice;
            }
        }
        KlineObjectNumber result = new KlineObjectNumber();
        result.maxPrice = maxPrice;
        result.minPrice = minPrice;
        result.priceClose = lastPrice;
        return result;
    }

    public static Double getMinPrice(List<KlineObjectNumber> kline1Ds, int numberTicker) {
        Double minPrice = null;
        int counter = 0;
        for (int i = 0; i < kline1Ds.size(); i++) {
            KlineObjectNumber kline1D = kline1Ds.get(kline1Ds.size() - 1 - i);
            counter++;
            if (counter >= numberTicker) {
                break;
            }
            if (minPrice == null || minPrice > kline1D.minPrice) {
                minPrice = kline1D.minPrice;
            }
        }
        return minPrice;
    }

    public static Double getPriceChange(List<KlineObjectNumber> klines, int numberTicker) {
        return klines.get(klines.size() - 1 - numberTicker).priceOpen - klines.get(klines.size() - 1).priceClose;
    }

    public static int getTotalCurrentPriceInKline(List<KlineObjectNumber> klines, Double price, Integer totalKlineCalculator) {
        int counter = 0;
        int index = 0;
        for (int i = 0; i < klines.size(); i++) {
            index++;
            if (index >= totalKlineCalculator) {
                break;
            }
            KlineObjectNumber kline = klines.get(klines.size() - 1 - i);
            if (price < kline.maxPrice && price > kline.minPrice) {
                counter++;
            }
        }
        return counter;
    }

    public static List<KlineObjectNumber> getTotalKlineBigchange(List<KlineObjectNumber> kline15ms, Double rateBigchange) {
        List<KlineObjectNumber> results = new ArrayList<>();
        for (KlineObjectNumber kline15m : kline15ms) {
            double rate = Utils.rateOf2Double(kline15m.maxPrice, kline15m.minPrice);
            if (rate >= rateBigchange) {
                results.add(kline15m);
            }
        }
        return results;
    }

    public static List<TrendObject> extractTopBottomObjectInTicker(List<KlineObjectNumber> tickers, Double rateCheck) {
        List<TrendObject> objects = new ArrayList<>();
        KlineObjectNumber lastTickerCheck = tickers.get(0);
        TrendState state = TrendState.UP;
        if (tickers.get(0).priceOpen > tickers.get(0).priceClose) {
            state = TrendState.DOWN;
        }
        for (KlineObjectNumber ticker : tickers) {
            if (state.equals(TrendState.UP)) {
                if (Utils.rateOf2Double(lastTickerCheck.maxPrice, ticker.maxPrice) > rateCheck) {
                    if (lastTickerCheck.maxPrice > ticker.maxPrice) {
                        objects.add(new TrendObject(state, lastTickerCheck));
                    } else {
                        objects.add(new TrendObject(state, ticker));
                    }
                    state = TrendState.DOWN;
                }
            } else {
                if (Utils.rateOf2Double(ticker.minPrice, lastTickerCheck.minPrice) > rateCheck) {
                    if (lastTickerCheck.minPrice < ticker.minPrice) {
                        objects.add(new TrendObject(state, lastTickerCheck));
                    } else {
                        objects.add(new TrendObject(state, ticker));
                    }
                    state = TrendState.UP;
                }
            }
            lastTickerCheck = ticker;
        }
        objects.add(new TrendObject(state, lastTickerCheck));
        return objects;
    }

    public static Map<String, List<KlineObjectNumber>> getAllKlineWithUpdateTime(String interval, long time2Update) {
        String fileName = FILE_DATA_TICKER.replace("INTERVAL", interval);
        File fileStorage = new File(fileName);
        if (fileStorage.exists() && fileStorage.lastModified() > System.currentTimeMillis() - time2Update) {
            return (Map<String, List<KlineObjectNumber>>) Storage.readObjectFromFile(fileName);
        } else {
            Map<String, List<KlineObjectNumber>> symbol2Kline1Ds = new HashMap<>();
            Collection<? extends String> symbols = TickerSpotHelper.getAllSymbol();
            for (String symbol : symbols) {
                symbol2Kline1Ds.put(symbol, TickerSpotHelper.getTicker(symbol, interval));
            }
            Storage.writeObject2File(fileName, symbol2Kline1Ds);
            return symbol2Kline1Ds;
        }
    }

    public static Map<String, List<KlineObjectNumber>> getAllKlineStartTime(String interval, Long startTime) {
        String fileName = FILE_DATA_TICKER_TIME.replace("INTERVAL", interval);
        fileName = fileName.replace("TIME", startTime.toString());
        Map<String, List<KlineObjectNumber>> symbol2Klines;
        File fileStorage = new File(fileName);
        if (fileStorage.exists()) {
            try {
                symbol2Klines = (Map<String, List<KlineObjectNumber>>) Storage.readObjectFromFile(fileName);
                List<KlineObjectNumber> btcTickers = symbol2Klines.get(Constants.SYMBOL_PAIR_BTC);
                if (btcTickers.get(btcTickers.size() - 1).endTime.longValue() + Utils.TIME_DAY < System.currentTimeMillis()) {
                    long startTimeNew = btcTickers.get(btcTickers.size() - 1).startTime.longValue();
                    int counter = 0;
                    Set<String> allSymbols = ClientSingleton.getInstance().getAllSymbol();
                    for (String symbol : allSymbols) {
                        List<KlineObjectNumber> tickers = symbol2Klines.get(symbol);
                        counter++;
//                        LOG.info("Update kline: {}/{}", counter, allSymbols.size());
                        if (tickers == null) {
                            LOG.info("Get s new: {}", symbol.replace("USDT", ""));
                            tickers = new ArrayList<>();
                            symbol2Klines.put(symbol, tickers);
                            tickers.addAll(TickerSpotHelper.getTickerWithStartTimeFull(symbol, interval, 0));
                        } else {
                            tickers.remove(tickers.size() - 1);
                            tickers.addAll(TickerSpotHelper.getTickerWithStartTimeFull(symbol, interval, startTimeNew));
                        }
                    }
                    Storage.writeObject2File(fileName, symbol2Klines);
                }
                return symbol2Klines;
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        symbol2Klines = new HashMap<>();
        Collection<? extends String> symbols = TickerSpotHelper.getAllSymbol();
        int counter = 0;
        for (String symbol : symbols) {
            counter++;
            LOG.info("Get k: {}/{}", counter, symbols.size());
            symbol2Klines.put(symbol, TickerSpotHelper.getTickerWithStartTime(symbol, interval, startTime));
        }
        Storage.writeObject2File(fileName, symbol2Klines);
        return symbol2Klines;

    }

    public static Map<String, List<KlineObjectNumber>> getAllKlineStartTime(String interval, Long startTime, Long timeUpdate) {
        String fileName = FILE_DATA_TICKER_TIME.replace("INTERVAL", interval);
        fileName = fileName.replace("TIME", startTime.toString());
        Map<String, List<KlineObjectNumber>> symbol2Klines;
        File fileStorage = new File(fileName);
        if (fileStorage.exists()) {
            try {
                symbol2Klines = (Map<String, List<KlineObjectNumber>>) Storage.readObjectFromFile(fileName);
                List<KlineObjectNumber> btcTickers = symbol2Klines.get(Constants.SYMBOL_PAIR_BTC);
                if (btcTickers.get(btcTickers.size() - 1).endTime.longValue() + timeUpdate < System.currentTimeMillis()) {
                    long startTimeNew = btcTickers.get(btcTickers.size() - 1).startTime.longValue();
                    int counter = 0;
                    Set<String> allSymbols = ClientSingleton.getInstance().getAllSymbol();
                    for (String symbol : allSymbols) {
                        List<KlineObjectNumber> tickers = symbol2Klines.get(symbol);
                        counter++;
//                        LOG.info("Update kline: {}/{}", counter, allSymbols.size());
                        if (tickers == null) {
                            LOG.info("Get s new: {}", symbol);
                            tickers = new ArrayList<>();
                            symbol2Klines.put(symbol, tickers);
                            tickers.addAll(TickerSpotHelper.getTickerWithStartTimeFull(symbol, interval, 0));
                        } else {
                            tickers.remove(tickers.size() - 1);
                            tickers.addAll(TickerSpotHelper.getTickerWithStartTimeFull(symbol, interval, startTimeNew));
                        }
                    }
                    Storage.writeObject2File(fileName, symbol2Klines);
                }
                return symbol2Klines;
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        symbol2Klines = new HashMap<>();
        Collection<? extends String> symbols = TickerSpotHelper.getAllSymbol();
        int counter = 0;
        for (String symbol : symbols) {
            counter++;
//            LOG.info("Get kline: {}/{}", counter, symbols.size());
            symbol2Klines.put(symbol, TickerSpotHelper.getTickerWithStartTime(symbol, interval, startTime));
        }
        Storage.writeObject2File(fileName, symbol2Klines);
        return symbol2Klines;

    }

    public static long nomalizeTimeWithExchange(long time) {
        return time + 7 * Utils.TIME_HOUR;
    }

    public static void updateTimeOfTrend(List<TrendObjectDetail> btcTrends) {
        for (int i = 0; i < btcTrends.size(); i++) {
            TrendObjectDetail trendInfo = btcTrends.get(i);
            trendInfo.startTimeTrend = trendInfo.topBottonObjects.get(0).kline.startTime.longValue();
            trendInfo.endTimeTrend = trendInfo.topBottonObjects.get(trendInfo.topBottonObjects.size() - 1).kline.endTime.longValue();
            if (i == btcTrends.size() - 1) {
                trendInfo.timeNextTrend = System.currentTimeMillis();
            } else {
                TrendObjectDetail nextTrendInfo = btcTrends.get(i + 1);
                trendInfo.timeNextTrend = nextTrendInfo.topBottonObjects.get(nextTrendInfo.topBottonObjects.size() - 1).kline.endTime.longValue();
            }
        }
    }

    public static List<TrendObjectDetail> detectTrendByKline(List<TrendObject> btcTrends, Double rateOfSideWay) {
        List<TrendObjectDetail> sWs = new ArrayList<>();
        List<TrendObject> listObjectProcessing = new ArrayList<>();
        for (TrendObject btcTrend : btcTrends) {
            listObjectProcessing.add(btcTrend);
            if (listObjectProcessing.size() > 1) {
                TrendObject lastObjectInListSW = listObjectProcessing.get(listObjectProcessing.size() - 2);
                Double rateChange = rateOf2UpDownObject(btcTrend, lastObjectInListSW);
                // trend -> add start+end => object con la sw tinh car start cua trend. end tren = start trend or sw
                if (Math.abs(rateChange) > rateOfSideWay) {
                    TrendState trend = TrendState.TREND_UP;
                    if (rateChange < 0) {
                        trend = TrendState.TREND_DOWN;
                    }
                    // check sw before trend
                    TrendObjectDetail swObjectTrend = new TrendObjectDetail(trend, new ArrayList());
                    swObjectTrend.topBottonObjects.add(listObjectProcessing.get(listObjectProcessing.size() - 2));
                    swObjectTrend.topBottonObjects.add(listObjectProcessing.get(listObjectProcessing.size() - 1));
                    if (listObjectProcessing.size() > 2) {
                        TrendObjectDetail swObjectSW = new TrendObjectDetail(TrendState.SIDEWAY, new ArrayDeque<>());
                        int sizeList = listObjectProcessing.size();
                        for (int i = 0; i < sizeList - 2; i++) {
                            swObjectSW.topBottonObjects.add(listObjectProcessing.get(0));
                            if (listObjectProcessing.size() > 2) {
                                listObjectProcessing.remove(0);
                            }
                        }
                        swObjectSW.topBottonObjects.add(listObjectProcessing.get(0));
                        sWs.add(swObjectSW);
                    }
                    listObjectProcessing.remove(0);
                    sWs.add(swObjectTrend);
                }
            }
        }
        if (listObjectProcessing.size() > 1) {
            TrendObjectDetail swObjectSW = new TrendObjectDetail(TrendState.SIDEWAY, new ArrayDeque<>());
            for (TrendObject listObjectProcessing1 : listObjectProcessing) {
                swObjectSW.topBottonObjects.add(listObjectProcessing1);
            }
            sWs.add(swObjectSW);
        }
        updateTimeOfTrend(sWs);
        return sWs;
    }

    public static Double rateOf2UpDownObject(TrendObject btcTrend, TrendObject lastObjectInListSW) {
        Double rateChange;
        if (btcTrend.status.equals(TrendState.UP)) {
            rateChange = Utils.rateOf2Double(btcTrend.kline.priceClose, lastObjectInListSW.kline.priceOpen);
        } else {
            rateChange = Utils.rateOf2Double(btcTrend.kline.priceOpen, lastObjectInListSW.kline.priceClose);
        }
        return rateChange;
    }

    public static List<SideWayObject> extractSideWayObject(List<KlineObjectNumber> tickers, Double rangeSizeTarget, Integer minimunKline) {
        List<SideWayObject> objects = new ArrayList<>();
        try {
            KlineObjectNumber start = tickers.get(0);
            Double maxPrice = start.maxPrice;
            Double minPrice = start.minPrice;
            int index = 0;
            for (int i = 0; i < tickers.size(); i++) {
                KlineObjectNumber ticker = tickers.get(i);
//                if (ticker.startTime.longValue() == Utils.sdfFileHour.parse("20231214 02:45").getTime()) {
//                    System.out.println("debug");
//                }
                // check range > size target => set new start and check number kline over minimum kline -> sideway
                if (Utils.rateOf2Double(ticker.maxPrice, minPrice) > rangeSizeTarget
                        || Utils.rateOf2Double(maxPrice, ticker.minPrice) > rangeSizeTarget) {

                    if (i - index >= minimunKline) {
                        objects.add(new SideWayObject(maxPrice, minPrice, Utils.rateOf2Double(maxPrice, minPrice), start, tickers.get(i - 1)));
                    }
                    // set new start
                    start = ticker;
                    index = i;
                    maxPrice = start.maxPrice;
                    minPrice = start.minPrice;
                } else {
                    if (ticker.maxPrice > maxPrice) {
                        maxPrice = ticker.maxPrice;
                    }
                    if (minPrice > ticker.minPrice) {
                        minPrice = ticker.minPrice;
                    }
                }
            }
            if (tickers.size() - 1 - index >= minimunKline) {
                objects.add(new SideWayObject(maxPrice, minPrice, Utils.rateOf2Double(maxPrice, minPrice), start, tickers.get(tickers.size() - 1)));
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return objects;
    }

    private static void testGetTicker() throws ParseException {

//        List<KlineObjectNumber> tickers = TickerHelper.getTicker("BTCUSDT", Constants.INTERVAL_15M);
        long time = Utils.sdfFileHour.parse("20240207 07:01").getTime();
        for (String symbol : getAllSymbol()) {
            KlineObjectNumber lastTicker24hr = getTickerLast24h(symbol, time);
            Double tickerChange = Utils.rateOf2Double(lastTicker24hr.priceClose, lastTicker24hr.priceOpen) * 10000;
            double rate = tickerChange.longValue();
            LOG.info("{} -> {}", symbol, rate / 100 + "%");
        }
    }

    public static Double getAvgLastVolume24h(List<KlineObjectNumber> tickers, int startIndex) {
        try {
            int counter = 0;
            Double total = 0.0;
            if (startIndex == 0) {
                return 0.0;
            }
            KlineObjectNumber firstTicker = tickers.get(startIndex - 1);
            while (true) {
                counter++;
                int index = startIndex - counter;
                if (index < 0) {
                    break;
                }
                KlineObjectNumber ticker = tickers.get(index);
                if ((firstTicker.startTime - ticker.startTime) >= Utils.TIME_DAY) {
                    break;
                }
//                LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), ticker.totalUsdt);
                total += ticker.totalUsdt;

            }
            return total / (counter - 1);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0.0;
    }

    public static KlineObjectNumber getTickerLast24h(String symbol, long startTime) {
        List<KlineObjectNumber> tickers = getTickerWithStartTime(symbol, Constants.INTERVAL_15M, startTime - Utils.TIME_DAY);
        Integer startIndex = 0;
        for (int i = 0; i < tickers.size(); i++) {
            KlineObjectNumber ticker = tickers.get(i);
            if (ticker.startTime <= startTime && ticker.endTime > startTime) {
                startIndex = i;
                break;
            }
        }
        try {
            int counter = 0;
            Double maxPrice;
            Double minPrice;
            Double lastPrice;
            Double totalUsdt = 0.0;
            if (startIndex == 0) {
                return null;
            }

            KlineObjectNumber lastTicker = tickers.get(startIndex - 1);
            lastPrice = lastTicker.priceClose;
            maxPrice = lastTicker.maxPrice;
            minPrice = lastTicker.minPrice;
            totalUsdt += lastTicker.totalUsdt;
            KlineObjectNumber result = tickers.get(startIndex - 1);
            while (true) {
                counter++;
                int index = startIndex - counter;
                if (index < 0) {
                    break;
                }
                result = tickers.get(index);
                if ((lastTicker.startTime - result.startTime) > Utils.TIME_DAY) {
                    break;
                }
                totalUsdt += result.totalUsdt;
                if (maxPrice < result.maxPrice) {
                    maxPrice = result.maxPrice;
                }
                if (minPrice > result.minPrice) {
                    minPrice = result.minPrice;
                }
            }
            result.maxPrice = maxPrice;
            result.minPrice = minPrice;
            result.priceClose = lastPrice;
            result.totalUsdt = totalUsdt;
            return result;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static Double getAvgLastVolume7D(List<KlineObjectNumber> tickers, int startIndex) {
        try {
            int counter = 0;
            Double total = 0.0;
            if (startIndex == 0) {
                return 0.0;
            }
            KlineObjectNumber firstTicker = tickers.get(startIndex - 1);
            while (true) {
                counter++;
                int index = startIndex - counter;
                if (index < 0) {
                    break;
                }
                KlineObjectNumber ticker = tickers.get(index);
                if ((firstTicker.startTime - ticker.startTime) >= 7 * Utils.TIME_DAY) {
                    break;
                }
//                LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), ticker.totalUsdt);
                total += ticker.totalUsdt;

            }
            return total / (counter - 1);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0.0;
    }

    public static OrderSide getSideOfTicer(KlineObjectNumber ticker) {
        OrderSide result = OrderSide.BUY;
        if (ticker.priceClose < ticker.priceOpen) {
            result = OrderSide.SELL;
        }
        return result;
    }

    public static Map<String, Long> getDateReleaseAllSymbol() {
        Map<String, Long> result = new HashMap<>();
        for (String sym : getAllSymbol()) {
            result.put(sym, getDateReleseASymbol(sym));
        }
        return result;
    }

    public static Long getDateReleseASymbol(String sym) {
        List<KlineObjectNumber> tickers = getTicker(sym, Constants.INTERVAL_1MONTH);
        if (tickers != null && !tickers.isEmpty()) {
            return tickers.get(0).startTime.longValue();
        }
        return 0L;
    }
}
