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

import com.binance.chuyennd.indicators.MACD;
import com.binance.chuyennd.indicators.RelativeStrengthIndex;
import com.binance.chuyennd.indicators.SimpleMovingAverage;
import com.binance.chuyennd.object.*;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
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
 * @author pc
 */
public class TickerFuturesHelper {

    public static final String FILE_DATA_TICKER = "storage/data/ticker/symbols-INTERVAL.data";
    public static final String FILE_DATA_TICKER_TIME = "storage/data/ticker/symbols-INTERVAL-TIME.data";
    public static final Logger LOG = LoggerFactory.getLogger(TickerFuturesHelper.class);

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
        String urlM1 = Constants.URL_TICKER_FUTURES.replace("xxxxxx", symbol) + interval;
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

    public static KlineObjectNumber getTickersByTime(String symbol, String interval, long time) {
        String urlM1 = Constants.URL_TICKER_FUTURES.replace("xxxxxx", symbol) + interval;
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            for (int i = 0; i < allKlines.size(); i++) {
                KlineObjectNumber kline = KlineObjectNumber.convertString2Kline(allKlines.get(i));
                if (kline.startTime == time) {
                    return kline;
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static KlineObjectNumber getLastTicker(String symbol, String interval) {
        String urlM1 = Constants.URL_TICKER_FUTURES.replace("xxxxxx", symbol) + interval;
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
        String urlM1 = Constants.URL_TICKER_FUTURES.replace("xxxxxx", symbol) + interval;
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
        String urlM1 = Constants.URL_TICKER_FUTURES.replace("xxxxxx", symbol) + interval;
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

    public static List<KlineObjectNumber> getTickerMacd(String symbol, String interval) {
        String urlM1 = Constants.URL_TICKER_FUTURES.replace("xxxxxx", symbol) + interval;
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
        String url = Constants.URL_TICKER_FUTURES_STARTTIME.replace("xxxxxx", symbol) + interval;
        List<KlineObjectNumber> results = new ArrayList();
        Long time = startTime;
        while (true) {
            try {
                String urlData = url.replace("tttttt", time.toString());
                String respon = HttpRequest.getContentFromUrl(urlData);
                if (StringUtils.isEmpty(respon) || StringUtils.length(respon) < 100) {
                    LOG.info("Error respon of sym: {} {}", symbol, new Date(time));
                    break;
                }
                try {
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
                    LOG.info("Error respon of sym: {} {}", respon, new Date(time));
                    e.printStackTrace();
                    break;
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return results;
    }

    public static List<KlineObjectNumber> getTickerWithStartTime(String symbol, String interval, Long startTime) {
        String url = Constants.URL_TICKER_FUTURES_STARTTIME.replace("xxxxxx", symbol) + interval;
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

    public static List<KlineObjectSimple> getTickerSimpleWithStartTime(String symbol, String interval, Long startTime) {
        String url = Constants.URL_TICKER_FUTURES_STARTTIME.replace("xxxxxx", symbol) + interval;
        List<KlineObjectSimple> results = new ArrayList();
        try {
            String urlData = url.replace("tttttt", startTime.toString());
            String respon = HttpRequest.getContentFromUrl(urlData);
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            for (List<Object> allKline : allKlines) {
                results.add(KlineObjectSimple.convertString2Kline(allKline));
            }

        } catch (Exception e) {
            e.printStackTrace();
        }

        return results;
    }

    public static TreeMap<Double, Double> getFundingFeeWithStartTime(String symbol, Long startTime) {
        String url = Constants.URL_FUNDING_FEE_FUTURES_START_TIME.replace("xxxxxx", symbol);
        TreeMap<Double, Double> results = new TreeMap<>();
        try {
            String urlData = url.replace("tttttt", startTime.toString());
            String respon = HttpRequest.getContentFromUrl(urlData);
            List<Map<Object, Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            for (Map<Object, Object> objs : allKlines) {
                results.put(Double.parseDouble(objs.get("fundingTime").toString()), Double.parseDouble(objs.get("fundingRate").toString()));
            }

        } catch (Exception e) {
            LOG.info("Error get funding fee: {} {}", symbol, startTime);
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

    public static TreeMap<Double, String> getSymbolVolumeLower() {
        TreeMap<Double, String> results = new TreeMap<Double, String>();
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                results.put(Double.parseDouble(ticker.getQuoteVolume()), ticker.getSymbol());
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
                symbol2Volume24hr.put(ticker.getSymbol(), Double.valueOf(ticker.getQuoteVolume()));
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
//        testGetTicker24hr();
        TreeMap<Double, String> volume2Symbol = getSymbolVolumeLower();
        for (Double volume: volume2Symbol.keySet()){
            LOG.info("{} {} ", volume2Symbol.get(volume), volume/1E6);
        }
//        LOG.info("{}", TickerFuturesHelper.getFundingFeeWithStartTime("OCEANUSDT", 1731916800000L));
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

    public static Double getMaxPrice(List<KlineObjectNumber> kline1Ds, int startIndex, int numberTicker) {
        Double maxPrice = null;
        for (int i = startIndex; i < startIndex + numberTicker; i++) {
            if (i >= kline1Ds.size()) {
                break;
            }
            KlineObjectNumber kline1D = kline1Ds.get(i);
            if (maxPrice == null || maxPrice < kline1D.maxPrice) {
                maxPrice = kline1D.maxPrice;
            }
        }
        return maxPrice;
    }

    public static KlineObjectNumber extractKline(List<KlineObjectNumber> tickers, int numberTicker, int startIndex) {
        Double maxPrice = null;
        int counter = 0;
        Double minPrice = null;
        Double lastPrice = null;
        Double openPrice = null;
        Double timeStart = null;

        Double timeEnd = null;
        Double totalUsdt = 0d;
        if (startIndex < 0) {
            startIndex = 0;
        }
        for (int i = startIndex; i < tickers.size(); i++) {
            KlineObjectNumber ticker = tickers.get(i);
            counter++;
            if (counter > numberTicker) {
                break;
            }
            if (openPrice == null) {
                openPrice = ticker.priceOpen;
            }
            lastPrice = ticker.priceClose;
            if (minPrice == null || minPrice > ticker.minPrice) {
                minPrice = ticker.minPrice;
            }
            if (maxPrice == null || maxPrice < ticker.maxPrice) {
                maxPrice = ticker.maxPrice;
            }
            if (timeStart == null) {
                timeStart = ticker.startTime;
            }
            timeEnd = ticker.endTime;
            totalUsdt += ticker.totalUsdt;
        }
        KlineObjectNumber result = new KlineObjectNumber();
        result.maxPrice = maxPrice;
        result.minPrice = minPrice;
        result.priceClose = lastPrice;
        result.priceOpen = openPrice;
        result.startTime = timeStart;
        result.endTime = timeEnd;
        result.totalUsdt = totalUsdt;
        return result;
    }

    public static KlineObjectNumber extractKline(List<KlineObjectNumber> tickers, Long startTime) {
        Double maxPrice = null;
        Double minPrice = null;
        Double lastPrice = null;
        Double openPrice = null;
        Double timeMin = null;
        Double timeMax = null;
        for (int i = 0; i < tickers.size(); i++) {
            KlineObjectNumber ticker = tickers.get(i);
            if (ticker.startTime > startTime) {
                if (openPrice == null) {
                    openPrice = ticker.priceOpen;
                }
                lastPrice = ticker.priceClose;
                if (minPrice == null || minPrice > ticker.minPrice) {
                    minPrice = ticker.minPrice;
                    timeMin = ticker.startTime;
                }
                if (maxPrice == null || maxPrice < ticker.maxPrice) {
                    maxPrice = ticker.maxPrice;
                    timeMax = ticker.startTime;
                }
            }
        }
        KlineObjectNumber result = new KlineObjectNumber();
        result.maxPrice = maxPrice;
        result.minPrice = minPrice;
        result.startTime = timeMin;
        result.endTime = timeMax;
        result.priceClose = lastPrice;
        result.priceOpen = openPrice;
        return result;
    }

    public static KlineObjectNumber extractKlineWithNumberEnd(List<KlineObjectNumber> tickers, int numberKline) {
        Double maxPrice = null;
        Double minPrice = null;
        Double lastPrice = null;
        Double openPrice = null;
        Double timeStart = null;
        Double timeEnd = null;
        Double totalUsdt = 0d;
        for (int i = tickers.size() - numberKline; i < tickers.size(); i++) {
            KlineObjectNumber ticker = tickers.get(i);
            if (openPrice == null) {
                openPrice = ticker.priceOpen;
            }
            lastPrice = ticker.priceClose;
            if (minPrice == null || minPrice > ticker.minPrice) {
                minPrice = ticker.minPrice;
            }
            if (maxPrice == null || maxPrice < ticker.maxPrice) {
                maxPrice = ticker.maxPrice;
            }
            if (timeStart == null) {
                timeStart = ticker.startTime;
            }
            timeEnd = ticker.endTime;
            totalUsdt += ticker.totalUsdt;
        }
        KlineObjectNumber result = new KlineObjectNumber();
        result.maxPrice = maxPrice;
        result.minPrice = minPrice;
        result.startTime = timeStart;
        result.endTime = timeEnd;
        result.priceClose = lastPrice;
        result.priceOpen = openPrice;
        result.totalUsdt = totalUsdt;
        return result;
    }


    public static KlineObjectNumber extractKline24hr(List<KlineObjectNumber> tickers, Long startTime) {
        Double maxPrice = null;
        Double minPrice = null;
        Double lastPrice = null;
        Double openPrice = null;
        Double timeStart = null;
        Double timeEnd = null;
        Double totalUsdt = 0d;
        Long timeCheck = startTime - Utils.TIME_DAY;
        for (int i = 0; i < tickers.size(); i++) {
            KlineObjectNumber ticker = tickers.get(i);
            if (ticker.startTime >= timeCheck && ticker.endTime < startTime) {
                totalUsdt += ticker.totalUsdt;
                if (openPrice == null) {
                    openPrice = ticker.priceOpen;
                }
                if (timeStart == null) {
                    timeStart = ticker.startTime;
                }
                timeEnd = ticker.endTime;
                lastPrice = ticker.priceClose;
                if (minPrice == null || minPrice > ticker.minPrice) {
                    minPrice = ticker.minPrice;
                }
                if (maxPrice == null || maxPrice < ticker.maxPrice) {
                    maxPrice = ticker.maxPrice;
                }
            }
        }
        KlineObjectNumber result = new KlineObjectNumber();
        result.maxPrice = maxPrice;
        result.minPrice = minPrice;
        result.startTime = timeStart;
        result.endTime = timeEnd;
        result.priceClose = lastPrice;
        result.priceOpen = openPrice;
        result.totalUsdt = totalUsdt;
        return result;
    }

    public static KlineObjectNumber extractKlineByTime(List<KlineObjectNumber> tickers, Long startTime, Long time) {
        Double maxPrice = null;
        Double minPrice = null;
        Double lastPrice = null;
        Double openPrice = null;
        Double timeStart = null;
        Double timeEnd = null;
        Double totalUsdt = 0d;
        Long timeCheck = startTime - time;
        for (int i = 0; i < tickers.size(); i++) {
            KlineObjectNumber ticker = tickers.get(i);
            if (ticker.startTime >= timeCheck && ticker.endTime < startTime) {
                totalUsdt += ticker.totalUsdt;
                if (openPrice == null) {
                    openPrice = ticker.priceOpen;
                }
                if (timeStart == null) {
                    timeStart = ticker.startTime;
                }
                timeEnd = ticker.endTime;
                lastPrice = ticker.priceClose;
                if (minPrice == null || minPrice > ticker.minPrice) {
                    minPrice = ticker.minPrice;
                }
                if (maxPrice == null || maxPrice < ticker.maxPrice) {
                    maxPrice = ticker.maxPrice;
                }
            }
        }
        KlineObjectNumber result = new KlineObjectNumber();
        result.maxPrice = maxPrice;
        result.minPrice = minPrice;
        result.startTime = timeStart;
        result.endTime = timeEnd;
        result.priceClose = lastPrice;
        result.priceOpen = openPrice;
        result.totalUsdt = totalUsdt;
        return result;
    }

    public static KlineObjectNumber extractKlineByNumberTicker(List<KlineObjectNumber> tickers, int index, int numberTicker) {
        if (index < numberTicker) {
            return null;
        }
        Double maxPrice = null;
        Double minPrice = null;
        Double lastPrice = null;
        Double openPrice = null;
        Double timeStart = null;
        Double timeEnd = null;
        Double totalUsdt = 0d;

        for (int i = index - numberTicker; i < index; i++) {
            KlineObjectNumber ticker = tickers.get(i);
            totalUsdt += ticker.totalUsdt;
            if (openPrice == null) {
                openPrice = ticker.priceOpen;
            }
            if (timeStart == null) {
                timeStart = ticker.startTime;
            }
            timeEnd = ticker.endTime;
            lastPrice = ticker.priceClose;
            if (minPrice == null || minPrice > ticker.minPrice) {
                minPrice = ticker.minPrice;
            }
            if (maxPrice == null || maxPrice < ticker.maxPrice) {
                maxPrice = ticker.maxPrice;
            }
        }
        KlineObjectNumber result = new KlineObjectNumber();
        result.maxPrice = maxPrice;
        result.minPrice = minPrice;
        result.startTime = timeStart;
        result.endTime = timeEnd;
        result.priceClose = lastPrice;
        result.priceOpen = openPrice;
        result.totalUsdt = totalUsdt;
        return result;
    }

    public static KlineObjectSimple extractKlineSimpleByNumberTicker(List<KlineObjectSimple> tickers, int index, int numberTicker) {
        if (index < numberTicker) {
            return null;
        }
        Double maxPrice = null;
        Double minPrice = null;
        Double lastPrice = null;
        Double openPrice = null;
        Double timeStart = null;
        Double totalUsdt = 0d;

        for (int i = index - numberTicker; i < index; i++) {
            KlineObjectSimple ticker = tickers.get(i);
            totalUsdt += ticker.totalUsdt;
            if (openPrice == null) {
                openPrice = ticker.priceOpen;
            }
            if (timeStart == null) {
                timeStart = ticker.startTime;
            }
            lastPrice = ticker.priceClose;
            if (minPrice == null || minPrice > ticker.minPrice) {
                minPrice = ticker.minPrice;
            }
            if (maxPrice == null || maxPrice < ticker.maxPrice) {
                maxPrice = ticker.maxPrice;
            }
        }
        KlineObjectSimple result = new KlineObjectSimple();
        result.maxPrice = maxPrice;
        result.minPrice = minPrice;
        result.startTime = timeStart;
        result.priceClose = lastPrice;
        result.priceOpen = openPrice;
        result.totalUsdt = totalUsdt;
        return result;
    }

    public static KlineObjectNumber extractKlineByNumberTicker(List<KlineObjectNumber> tickers, int index, int numberTicker, int numberAgo) {
        if (index < numberTicker) {
            return null;
        }
        Double maxPrice = null;
        Double minPrice = null;
        Double lastPrice = null;
        Double openPrice = null;
        Double timeStart = null;
        Double timeEnd = null;
        Double totalUsdt = 0d;

        for (int i = index - numberTicker; i < index - numberAgo; i++) {
            KlineObjectNumber ticker = tickers.get(i);
            totalUsdt += ticker.totalUsdt;
            if (openPrice == null) {
                openPrice = ticker.priceOpen;
            }
            if (timeStart == null) {
                timeStart = ticker.startTime;
            }
            timeEnd = ticker.endTime;
            lastPrice = ticker.priceClose;
            if (minPrice == null || minPrice > ticker.minPrice) {
                minPrice = ticker.minPrice;
            }
            if (maxPrice == null || maxPrice < ticker.maxPrice) {
                maxPrice = ticker.maxPrice;
            }
        }
        KlineObjectNumber result = new KlineObjectNumber();
        result.maxPrice = maxPrice;
        result.minPrice = minPrice;
        result.startTime = timeStart;
        result.endTime = timeEnd;
        result.priceClose = lastPrice;
        result.priceOpen = openPrice;
        result.totalUsdt = totalUsdt;
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

    public static List<KlineObjectNumber> getTotalKlineBigChange(List<KlineObjectNumber> kline15ms, Double rateBigChange) {
        List<KlineObjectNumber> results = new ArrayList<>();
        for (KlineObjectNumber kline15m : kline15ms) {
            double rate = Utils.rateOf2Double(kline15m.maxPrice, kline15m.minPrice);
            if (rate >= rateBigChange) {
                results.add(kline15m);
            }
        }
        return results;
    }

    public static List<TrendObject> extractTopBottomObjectInTicker(List<KlineObjectNumber> tickers) {
        List<TrendObject> objects = new ArrayList<>();
        int period = 5;
        // tìm đáy hoặc đỉnh đầu tiên
        KlineObjectNumber lastTickerCheck = tickers.get(0);
        TrendState state = TrendState.TOP;
        if (tickers.get(0).priceOpen > tickers.get(0).priceClose) {
            state = TrendState.BOTTOM;
        }
        int start;
        for (start = 0; start < tickers.size(); start++) {
            if (start + period > tickers.size()) {
                break;
            }
            // tìm đỉnh gần nhất
            if (state.equals(TrendState.TOP)) {
                boolean top = true;
                for (int j = start; j < period + start; j++) {
                    if (tickers.get(j).maxPrice > lastTickerCheck.maxPrice) {
                        lastTickerCheck = tickers.get(j);
                        start = j;
                        top = false;
                        break;
                    }
                }
                if (top) {
                    objects.add(new TrendObject(state, lastTickerCheck));
                    lastTickerCheck = tickers.get(start + 1);
                    state = TrendState.BOTTOM;
                }
            } else {// tìm đáy gần nhất
                boolean bottom = true;
                for (int j = start; j < period + start; j++) {
                    if (tickers.get(j).minPrice < lastTickerCheck.minPrice) {
                        lastTickerCheck = tickers.get(j);
                        start = j;
                        bottom = false;
                        break;
                    }
                }
                if (bottom) {
                    objects.add(new TrendObject(state, lastTickerCheck));
                    lastTickerCheck = tickers.get(start + 1);
                    state = TrendState.TOP;
                }
            }
            if (!objects.isEmpty()) {
                break;
            }
        }
        // tìm các đỉnh, đáy tiếp theo
        for (int i = start; i < tickers.size(); i++) {
            // tìm đỉnh gần nhất
            if (state.equals(TrendState.TOP)) {
                boolean top = true;
                for (int j = i; j < period + i; j++) {
                    if (j >= tickers.size()) {
                        top = false;
                        break;
                    }
                    if (tickers.get(j).maxPrice > lastTickerCheck.maxPrice) {
                        lastTickerCheck = tickers.get(j);
                        i = j;
                        top = false;
                        break;
                    }
                }
                if (top) {
                    objects.add(new TrendObject(state, lastTickerCheck));
                    lastTickerCheck = tickers.get(i + 1);
                    state = TrendState.BOTTOM;
                }
            } else {// tìm đáy gần nhất
                boolean top = true;
                for (int j = i; j < period + i; j++) {
                    if (j >= tickers.size()) {
                        top = false;
                        break;
                    }
                    if (tickers.get(j).minPrice < lastTickerCheck.minPrice) {
                        lastTickerCheck = tickers.get(j);
                        i = j;
                        top = false;
                        break;
                    }
                }
                if (top) {
                    objects.add(new TrendObject(state, lastTickerCheck));
                    lastTickerCheck = tickers.get(i + 1);
                    state = TrendState.TOP;
                }
            }
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
            Collection<? extends String> symbols = TickerFuturesHelper.getAllSymbol();
            for (String symbol : symbols) {
                symbol2Kline1Ds.put(symbol, TickerFuturesHelper.getTicker(symbol, interval));
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
                        LOG.info("Update kline: {}/{}", counter, allSymbols.size());
                        if (tickers == null) {
                            LOG.info("Get s new: {}", symbol.replace("USDT", ""));
                            tickers = new ArrayList<>();
                            symbol2Klines.put(symbol, tickers);
                            tickers.addAll(TickerFuturesHelper.getTickerWithStartTimeFull(symbol, interval, 0));
                        } else {
                            tickers.remove(tickers.size() - 1);
                            tickers.addAll(TickerFuturesHelper.getTickerWithStartTimeFull(symbol, interval, startTimeNew));
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
        Collection<? extends String> symbols = TickerFuturesHelper.getAllSymbol();
        int counter = 0;
        for (String symbol : symbols) {
            counter++;
            LOG.info("Get k: {}/{}", counter, symbols.size());
            symbol2Klines.put(symbol, TickerFuturesHelper.getTickerWithStartTime(symbol, interval, startTime));
        }
        Storage.writeObject2File(fileName, symbol2Klines);
        return symbol2Klines;

    }

    public static Map<String, List<KlineObjectNumber>> getAllKlineMonth() throws ParseException {
        String interval = Constants.INTERVAL_1MONTH;
        Long startTime = Utils.sdfFile.parse("20200101").getTime();
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
                        LOG.info("Update kline: {}/{}", counter, allSymbols.size());
                        if (tickers == null) {
                            LOG.info("Get s new: {}", symbol.replace("USDT", ""));
                            tickers = new ArrayList<>();
                            symbol2Klines.put(symbol, tickers);
                            tickers.addAll(TickerFuturesHelper.getTickerWithStartTimeFull(symbol, interval, 0));
                        } else {
                            tickers.remove(tickers.size() - 1);
                            tickers.addAll(TickerFuturesHelper.getTickerWithStartTimeFull(symbol, interval, startTimeNew));
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
        Collection<? extends String> symbols = TickerFuturesHelper.getAllSymbol();
        int counter = 0;
        for (String symbol : symbols) {
            counter++;
            LOG.info("Get k: {}/{}", counter, symbols.size());
            symbol2Klines.put(symbol, TickerFuturesHelper.getTickerWithStartTime(symbol, interval, startTime));
        }
        Storage.writeObject2File(fileName, symbol2Klines);
        return symbol2Klines;

    }

    public static Map<String, List<KlineObjectNumber>> getAllKlineStartTime(String interval, Long startTime, Long
            timeUpdate) {
        String fileName = FILE_DATA_TICKER_TIME.replace("INTERVAL", interval);
        fileName = fileName.replace("TIME", startTime.toString());
        Map<String, List<KlineObjectNumber>> symbol2Klines;
        File fileStorage = new File(fileName);
        if (fileStorage.exists()) {
            try {
                symbol2Klines = (Map<String, List<KlineObjectNumber>>) Storage.readObjectFromFile(fileName);
                long startTimeNew = fileStorage.lastModified();
                if (startTimeNew + timeUpdate < System.currentTimeMillis()) {
                    int counter = 0;
                    Set<String> allSymbols = ClientSingleton.getInstance().getAllSymbol();
                    for (String symbol : allSymbols) {
                        if (Constants.diedSymbol.contains(symbol)) {
                            continue;
                        }
                        List<KlineObjectNumber> tickers = symbol2Klines.get(symbol);
                        counter++;
//                        LOG.info("Update kline: {}/{}", counter, allSymbols.size());
                        if (tickers == null) {
                            LOG.info("Get s new: {}", symbol);
                            tickers = new ArrayList<>();
                            symbol2Klines.put(symbol, tickers);
                            tickers.addAll(TickerFuturesHelper.getTickerWithStartTimeFull(symbol, interval, 0));
                        } else {
                            tickers.remove(tickers.size() - 1);
                            tickers.addAll(TickerFuturesHelper.getTickerWithStartTimeFull(symbol, interval, startTimeNew));
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
        Collection<? extends String> symbols = TickerFuturesHelper.getAllSymbol();
        int counter = 0;
        for (String symbol : symbols) {
            counter++;
//            LOG.info("Get kline: {}/{}", counter, symbols.size());
            symbol2Klines.put(symbol, TickerFuturesHelper.getTickerWithStartTime(symbol, interval, startTime));
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

    public static List<SideWayObject> extractSideWayObject(List<KlineObjectNumber> tickers, Double
            rangeSizeTarget, Integer minimunKline) {
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

    private static void testGetTicker24hr() throws ParseException {

//        List<KlineObjectNumber> tickers = TickerHelper.getTicker("BTCUSDT", Constants.INTERVAL_15M);
        long time = Utils.sdfFileHour.parse("20240207 07:01").getTime();
        for (String symbol : getAllSymbol()) {
            KlineObjectNumber lastTicker24hr = getTickerLastDuration(symbol, time, Utils.TIME_DAY);
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

    public static KlineObjectNumber getTickerLastDuration(String symbol, long startTime, long duration) {
        List<KlineObjectNumber> tickers = getTickerWithStartTime(symbol, Constants.INTERVAL_15M, startTime - duration);
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
                if ((lastTicker.startTime - result.startTime) > duration) {
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

    public static Double getRateChangeOfTicker(KlineObjectNumber ticker) {
        return Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
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

    public static Double calMa(List<KlineObjectNumber> tickers, int i, int numberMA) {
        if (i < numberMA) {
            return null;
        } else {
            Double totalPrice = 0d;
            for (int j = i - numberMA; j < i; j++) {
                KlineObjectNumber ticker = tickers.get(j);
                totalPrice += ticker.priceClose;
            }
            return totalPrice / numberMA;
        }
    }

    public static Double calRSI(List<KlineObjectNumber> tickers, int index, int period) {
        if (index < period) {
            return null;
        } else {
            List<Double> data = extractDataRsi(tickers, index, period);
            double[] gain = new double[data.size()];
            double[] loss = new double[data.size()];

            for (int i = 1; i < data.size(); i++) {
                double priceDiff = data.get(i) - data.get(i - 1);
                gain[i] = (priceDiff > 0) ? priceDiff : 0;
                loss[i] = (priceDiff < 0) ? -priceDiff : 0;
            }
            double avgGain = 0;
            double avgLoss = 0;
            for (int i = 1; i <= period; i++) {
                avgGain += gain[i];
                avgLoss += loss[i];
            }
            avgGain /= period;
            avgLoss /= period;
            double rs = (avgLoss != 0) ? avgGain / avgLoss : Double.POSITIVE_INFINITY;
            return 100 - (100 / (1 + rs));
        }
    }

    private static List<Double> extractDataRsi(List<KlineObjectNumber> tickers, int i, int period) {
        List<Double> results = new ArrayList<>();
        for (int j = i - period; j < i + 1; j++) {
            results.add(tickers.get(j).priceClose);
        }
        return results;
    }

    public static Boolean isButton(List<KlineObjectNumber> tickers, int index, Integer period) {
        Long lastBottom = 0l;
//        Integer period = 30;
        if (index < period || tickers.get(index - period).rsi == null) {
            return false;
        }
        Double rsiAvg = calAvgRsi(tickers, index - period, period);
        KlineObjectNumber before2Ticker = tickers.get(index - 5);
        KlineObjectNumber before1Ticker = tickers.get(index - 4);
        KlineObjectNumber beforeTicker = tickers.get(index - 3);
        KlineObjectNumber ticker = tickers.get(index - 2);
        KlineObjectNumber afterTicker = tickers.get(index - 1);
        KlineObjectNumber after1Ticker = tickers.get(index);

        if (afterTicker.rsi > ticker.rsi
                && after1Ticker.rsi > afterTicker.rsi
                && ticker.rsi < beforeTicker.rsi
                && beforeTicker.rsi < before1Ticker.rsi
                && beforeTicker.rsi < before2Ticker.rsi
                && rsiAvg - ticker.rsi > 10
                && ticker.rsi <= 40
        ) {
            return true;
        }
        return false;
    }

    private static Double calAvgRsi(List<KlineObjectNumber> tickers, int i, int duration) {
        Double total = 0d;
        for (int j = i; j < i + duration; j++) {
            KlineObjectNumber ticker = tickers.get(j);
            total += ticker.rsi;
        }
        return total / duration;
    }

    public static boolean isMacdTrendBuy(MACDEntry[] entries, int i) {
        MACDEntry lastEntrie = entries[i - 1];
        MACDEntry entrie = entries[i];
        if (lastEntrie.getHistogram() < 0
                && entrie.getHistogram() > 0
                && lastEntrie.getSignal() < 0
        ) {
            return true;
        }
        return false;
    }


    public static List<KlineObjectNumber> updateIndicator(List<KlineObjectNumber> allTickers) {
        RsiEntry[] rsi = RelativeStrengthIndex.calculateRSI(allTickers, 14);
        MACDEntry[] entries = MACD.calculate(allTickers, 12, 26, 9);
        IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(allTickers, 20);
        Map<Double, Double> time2Rsi = new HashMap<>();
        Map<Double, Double> time2Ma = new HashMap<>();
        Map<Double, MACDEntry> time2Macd = new HashMap<>();
        for (RsiEntry rs : rsi) {
            time2Rsi.put(rs.startTime, rs.getRsi());
        }
        for (MACDEntry entry : entries) {
            time2Macd.put(entry.startTime, entry);
        }
        for (IndicatorEntry sma : smaEntries) {
            time2Ma.put(sma.startTime, sma.getValue());
        }
        for (KlineObjectNumber ticker : allTickers) {
            Double time = ticker.startTime;
            ticker.rsi = time2Rsi.get(time);
            ticker.ma20 = time2Ma.get(time);
            MACDEntry macd = time2Macd.get(time);
            if (macd != null) {
                ticker.macd = macd.getMacd();
                ticker.signal = macd.getSignal();
                ticker.histogram = macd.getHistogram();
            }
        }
        return allTickers;
    }

    public static KlineObjectSimple extractTickerPriceMin24h(List<KlineObjectSimple> tickers, KlineObjectSimple tickerPriceMin24h) {
        if (tickers.size() < 500) {
            return null;
        }
        KlineObjectSimple lastTicker = tickers.get(tickers.size() - 1);
        if (tickerPriceMin24h == null || tickerPriceMin24h.startTime < lastTicker.startTime - Utils.TIME_DAY) {
            tickerPriceMin24h = lastTicker;
            for (int i = 1; i < tickers.size(); i++) {
                if (tickerPriceMin24h == null || tickerPriceMin24h.minPrice > tickers.get(i).minPrice) {
                    tickerPriceMin24h = tickers.get(i);
                }
                if (i >= 1440) {
                    break;
                }
            }
        } else {
            if (tickerPriceMin24h.minPrice > lastTicker.minPrice) {
                tickerPriceMin24h = lastTicker;
            }
        }
        return tickerPriceMin24h;
    }

    public static KlineObjectSimple extractTickerVolumeMax24h(List<KlineObjectSimple> tickers, KlineObjectSimple tickerVolumeMax24h) {
        if (tickers.size() < 500) {
            return null;
        }
        KlineObjectSimple lastTicker = tickers.get(tickers.size() - 1);
        if (tickerVolumeMax24h == null || tickerVolumeMax24h.startTime < lastTicker.startTime - Utils.TIME_DAY) {
            tickerVolumeMax24h = lastTicker;
            for (int i = 1; i < tickers.size(); i++) {
                if (tickerVolumeMax24h == null || tickerVolumeMax24h.totalUsdt < tickers.get(i).totalUsdt) {
                    tickerVolumeMax24h = tickers.get(i);
                }
                if (i >= 1440) {
                    break;
                }
            }
        } else {
            if (tickerVolumeMax24h.totalUsdt < lastTicker.totalUsdt) {
                tickerVolumeMax24h = lastTicker;
            }
        }
        return tickerVolumeMax24h;
    }
}
