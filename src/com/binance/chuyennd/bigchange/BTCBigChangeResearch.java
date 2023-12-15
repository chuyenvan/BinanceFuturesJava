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
package com.binance.chuyennd.bigchange;

import com.binance.chuyennd.research.Test;
import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.chuyennd.funcs.TickerHelper;
import com.binance.chuyennd.object.KlineObject;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.PositionRisk;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class BTCBigChangeResearch {

    public static final Logger LOG = LoggerFactory.getLogger(Test.class);
    public static final String URL_TICKER_1D = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&interval=1d";
    public static final String URL_TICKER_15M = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&interval=15m";
    public static final Double RATE_BIG_CHANGE_TEST = Configs.getDouble("RateBigChangeTest");

    public static PositionRisk getPositionBySymbol(String symbol) {
        List<PositionRisk> positionInfos = ClientSingleton.getInstance().syncRequestClient.getPositionRisk(symbol);
        PositionRisk position = null;
        if (positionInfos != null && !positionInfos.isEmpty()) {
            position = positionInfos.get(0);
        }
        return position;
    }

   

    private static void extractKline_23h9_11_2023(long time) {

        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        TreeMap<Double, String> rateChangeTicker = new TreeMap<>();
        Map<String, KlineObject> symbol2Kline = new HashMap<String, KlineObject>();
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                try {
                    // only get symbol over 2 months
                    KlineObject kline = getTickerByTime(ticker.getSymbol(), time);
                    symbol2Kline.put(ticker.getSymbol(), kline);
                    Double rateChange = (Double.parseDouble(kline.priceMin) - Double.parseDouble(kline.priceMax)) / Double.parseDouble(kline.priceMax);
                    rateChangeTicker.put(rateChange, ticker.getSymbol());
                } catch (Exception e) {

                }
            }
        }
        for (Map.Entry<Double, String> entry : rateChangeTicker.entrySet()) {
            Object rate = entry.getKey();
            Object symbol = entry.getValue();
            KlineObject kline = symbol2Kline.get(symbol);
            if (kline != null) {
                LOG.info("{} -> {} max: {} min: {} open: {} close: {}",
                        symbol, rate, kline.priceMax, kline.priceMin, kline.priceOpen, kline.priceClose);
            } else {
                LOG.info("{} -> {}", symbol, rate);
            }
        }
    }

  

    private static KlineObject getTickerByTime(String symbol, long time) {

        String urlM1 = URL_TICKER_15M.replace("xxxxxx", symbol);
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            for (List<Object> allKline : allKlines) {
                KlineObject kline = KlineObject.convertString2Kline(allKline);
                if (kline.startTime.longValue() == time) {
                    return kline;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;

    }

    private static void detectSideWayWithDayAndRange(int numberDay, Double rateChange) {
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        TreeMap<Double, String> rateChangeInMonth = new TreeMap<>();
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                try {
                    // only get symbol over 2 months
                    Double rangeRate = getRange(ticker.getSymbol(), numberDay, rateChange);
                    rateChangeInMonth.put(rangeRate, ticker.getSymbol());
                } catch (Exception e) {

                }
            }
        }
        for (Map.Entry<Double, String> entry : rateChangeInMonth.entrySet()) {
            Object rate = entry.getKey();
            Object symbol = entry.getValue();
            LOG.info("{} -> {}", symbol, rate);
        }
    }

    private static Double getRange(String symbol, int numberDay, Double rateChangeInMonth) {
        String urlM1 = URL_TICKER_1D.replace("xxxxxx", symbol);
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            if (allKlines.size() > 31) {
                Double maxPrice = 0d;
                Double minPrice = 0d;
                for (int i = 0; i < numberDay; i++) {

                    KlineObject kline = KlineObject.convertString2Kline(allKlines.get(allKlines.size() - i - 1));
                    if (maxPrice < Double.parseDouble(kline.priceMax)) {
                        maxPrice = Double.parseDouble(kline.priceMax);
                    }
                    if (minPrice > Double.parseDouble(kline.priceMin) || minPrice == 0) {
                        minPrice = Double.parseDouble(kline.priceMin);
                    }
                }
//                Double result = (maxPrice - minPrice) / maxPrice;
                Double currentPrice = ClientSingleton.getInstance().getCurrentPrice(symbol);
                Double result = (currentPrice - minPrice) / currentPrice;
                LOG.info("{} {}: {} -> {} {}", symbol, result, minPrice, maxPrice, currentPrice);
                return result;
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0d;
    }

    private static List<List<Object>> getTicker15MbySymbol(String symbol) {
        String urlM1 = URL_TICKER_15M.replace("xxxxxx", symbol);
        String respon = HttpRequest.getContentFromUrl(urlM1);
        return Utils.gson.fromJson(respon, List.class);
    }

    private static void extractKlineBigChangeWithBTC() {

        Map<Double, TreeMap<Double, String>> rateChangeTickers = new TreeMap<>();
        Map<Double, Map<String, KlineObjectNumber>> symbol2Kline = new HashMap<>();
        List<List<Object>> tickers = getTicker15MbySymbol("BTCUSDT");
        for (List<Object> ticker : tickers) {
            KlineObjectNumber kline = KlineObjectNumber.convertString2Kline(ticker);
            if ((kline.maxPrice - kline.minPrice) / kline.minPrice > 0.025) {
                LOG.info("bigchange: {} -> {}", new Date(kline.startTime.longValue()), Utils.toJson(kline));
                rateChangeTickers.put(kline.startTime, new TreeMap<>());
                Double rateChange = (kline.priceOpen - kline.priceClose) / kline.priceOpen;
                rateChangeTickers.get(kline.startTime).put(rateChange, "BTCUSDT");
                symbol2Kline.put(kline.startTime, new HashMap());
            }
        }
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);

        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                try {
                    List<List<Object>> tickerSymbols = getTicker15MbySymbol(ticker.getSymbol());
                    for (List<Object> tickerSymbol : tickerSymbols) {
                        KlineObjectNumber kline = KlineObjectNumber.convertString2Kline(tickerSymbol);
                        if (rateChangeTickers.containsKey(kline.startTime)) {
                            TreeMap<Double, String> rateChangeTicker = rateChangeTickers.get(kline.startTime);
                            Double rateChange = (kline.priceOpen - kline.priceClose) / kline.priceOpen;
                            rateChangeTicker.put(rateChange, ticker.getSymbol());
                            symbol2Kline.get(kline.startTime).put(ticker.getSymbol(), kline);
                        }
                    }
                } catch (Exception e) {

                }
            }
        }
        for (Map.Entry<Double, TreeMap<Double, String>> entry : rateChangeTickers.entrySet()) {
            Double time = entry.getKey();
            TreeMap<Double, String> rateChangeTicker = entry.getValue();
            for (Map.Entry<Double, String> entry1 : rateChangeTicker.entrySet()) {
                Double rate = entry1.getKey();
                String symbol = entry1.getValue();
                KlineObjectNumber kline = symbol2Kline.get(time).get(symbol);
                if (kline != null) {
                    LOG.info(" {} {} -> {} max: {} min: {} open: {} close: {}", new Date(time.longValue()),
                            symbol, rate, kline.maxPrice, kline.minPrice, kline.priceOpen, kline.priceClose);
                } else {
                    LOG.info("{} {} -> {}", new Date(time.longValue()), symbol, rate
                    );
                }
            }
        }

    }

    private static void extractKlineBigChangeOfBTC(String intervel, Double rate) {
        List<KlineObjectNumber> tickers = TickerHelper.getTicker("BTCUSDT", intervel);
        for (KlineObjectNumber kline : tickers) {
            if ((kline.maxPrice - kline.minPrice) / kline.minPrice > rate) {
                LOG.info("bigchange: {} -> {}", new Date(kline.startTime.longValue()), Utils.toJson(kline));
            }
        }

    }

    private static void extractKlineTrendBTCWithRate(Double rate) {
        List<KlineObjectNumber> tickers = TickerHelper.getTicker("BTCUSDT", "1h");
        OrderSide trend = null;
        KlineObjectNumber trendKline = null;
        for (KlineObjectNumber currentKline : tickers) {
            if (trendKline == null) {
                trendKline = currentKline;
            } else {
                if (trend == null) {
                    if (trendKline.priceClose > trendKline.priceOpen) {
                        trend = OrderSide.BUY;
                    } else {
                        trend = OrderSide.SELL;
                    }
                } else {
                    // doi chieu
                    Double currentRate = (currentKline.priceClose - trendKline.priceOpen) / trendKline.priceOpen;
                    if (trend.equals(OrderSide.BUY)) {
                        if (currentKline.priceClose < trendKline.priceOpen) {
                            trend = OrderSide.SELL;
                            trendKline = currentKline;
                        } else {
                            if (Math.abs(currentRate) > rate) {
                                LOG.info("bigchange:start {} rate:{} end: {} priceStart: {} priceEnd: {}",
                                        new Date(trendKline.startTime.longValue()), currentRate,
                                        new Date(currentKline.startTime.longValue()), trendKline.priceOpen, currentKline.priceClose);
                                trendKline = currentKline;
                            }
                        }
                    } else {
                        if (currentKline.priceClose > trendKline.priceOpen) {
                            trend = OrderSide.BUY;
                            trendKline = currentKline;
                        } else {
                            if (currentRate > rate) {
                                LOG.info("bigchange:start {} rate:{} end: {} priceStart: {} priceEnd: {}",
                                        new Date(trendKline.startTime.longValue()), currentRate,
                                        new Date(currentKline.startTime.longValue()), trendKline.priceOpen, currentKline.priceClose);
                                trendKline = currentKline;
                            }
                        }

                    }
                }
            }

        }
    }

    private static void startThreadDetectBigChangeBTCInMinute() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadDetectBigChangeBTCInMinute");
            LOG.info("Start ThreadDetectBigChangeBTCInMinute !");
            Set<String> symbols = new HashSet<>();
            symbols.addAll(TickerHelper.getAllSymbol());
            while (true) {
                try {
                    if (System.currentTimeMillis() % Utils.TIME_MINUTE <= Utils.TIME_SECOND) {
                        LOG.info("Detect bigchane in month kline!");
                        KlineObjectNumber ticker = TickerHelper.getLastTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1M);
                        Double rate = (ticker.maxPrice - ticker.minPrice) / ticker.minPrice;
                        if (rate > RATE_BIG_CHANGE_TEST) {
                            LOG.info("{} {} {}", "BTCUSDT", rate, Utils.toJson(ticker));
                            printDataAllSymbolNextMinute(ticker, symbols);
                        }
                    }
                    Thread.sleep(Utils.TIME_SECOND);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadDetectBigChangeBTCInMinute: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

   

    private static void printDataAllSymbolNextMinute(KlineObjectNumber ticker, Set<String> symbols) {
        try {
            int numberMinuteCheckRateChange = 10;
            Thread.sleep(numberMinuteCheckRateChange * Utils.TIME_MINUTE);
            TreeMap<Double, String> rate2Symbol = new TreeMap<>();
            Map<String, Double> symbol2Rate = new HashMap<>();
            OrderSide side = OrderSide.BUY;
            if (ticker.priceClose < ticker.priceOpen) {
                side = OrderSide.SELL;
            }
            for (String symbol : symbols) {
                try {
                    List<KlineObjectNumber> tickers = TickerHelper.getTicker(symbol, Constants.INTERVAL_1M);
                    Double maxPrice = null;
                    Double minPrice = null;
                    KlineObjectNumber klineCheckPoint = tickers.get(tickers.size() - 1 - numberMinuteCheckRateChange);
                    for (int i = 0; i < numberMinuteCheckRateChange + 1; i++) {
                        KlineObjectNumber kline = tickers.get(tickers.size() - 1 - i);
                        if (maxPrice == null || kline.maxPrice > maxPrice) {
                            maxPrice = kline.maxPrice;
                        }
                        if (minPrice == null || kline.minPrice < minPrice) {
                            minPrice = kline.minPrice;
                        }
                    }
                    Double rateDown = (klineCheckPoint.priceOpen - minPrice) / klineCheckPoint.priceOpen;
                    Double rateUp = (maxPrice - klineCheckPoint.priceOpen) / klineCheckPoint.priceOpen;
                    Double rateChange = 0d;
                    if (side.equals(OrderSide.BUY)) {
                        rateChange = rateUp;
                        symbol2Rate.put(symbol, rateDown);
                    } else {
                        rateChange = rateDown;
                        symbol2Rate.put(symbol, rateUp);
                    }
                    rate2Symbol.put(rateChange, symbol);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            for (Map.Entry<Double, String> entry : rate2Symbol.entrySet()) {
                Double rate = entry.getKey();
                String symbol = entry.getValue();
                LOG.info("{} {} {}", symbol, rate, symbol2Rate.get(symbol));
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
     public static void main(String[] args) throws InterruptedException {
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER));
//        System.out.println(getPositionBySymbol("DYDXUSDT"));
//        long time = Utils.getStartTime(0) - Utils.TIME_HOUR;
//        System.out.println(Utils.gson.toJson(getTickerByTime("BTCUSDT", time)));
//        extractKline_23h9_11_2023(time);
//        extractKlineBigChangeWithBTC();
//        extractKlineBigChangeOfBTC(Contanst.INTERVAL_1M, 0.025);
        startThreadDetectBigChangeBTCInMinute();
//        for (int i = 0; i < 10; i++) {
//            System.out.println(System.currentTimeMillis() % Utils.TIME_MINUTE);
//            Thread.sleep(Utils.TIME_SECOND);
//        }
//        Double rate = 0.05;
//        extractKlineTrendBTCWithRate(rate);
//        extractRateChangeInMonth();
//        System.out.println(Utils.gson.toJson(ClientSingleton.getInstance().syncRequestClient.getBalance()));
//        int numberDay = 15;
//        Double rateChange = 0.1;
//        detectSideWayWithDayAndRange(numberDay, rateChange);
//        long timeout = 10000;
//        while (true) {
//            System.out.println(new Date() + " " + getDataWithTimeOut(timeout));
//        }

    }
}
