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
package com.binance.chuyennd.helper;

import com.binance.chuyennd.object.*;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.*;

import java.math.BigDecimal;
import java.util.List;

import com.binance.client.constant.Constants;

import java.text.ParseException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import com.binance.client.model.event.CandlestickEvent;
import com.binance.client.model.market.FundingRate;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @author pc
 */
public class TickerFuturesHelper {

    public static final Logger LOG = LoggerFactory.getLogger(TickerFuturesHelper.class);



    public static KlineObjectNumber getTickerByTime(String symbol, String interval, long time) {
        String urlM1 = Constants.URL_TICKER_FUTURES_STARTTIME.replace("xxxxxx", symbol) + interval;
        String urlData = urlM1.replace("tttttt", String.valueOf(time));
        String respon = HttpRequest.getContentFromUrl(urlData);
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



    public static List<KlineObjectNumber> getTickerWithStartTimeFull(String symbol, String interval, long startTime) {
        String url = Constants.URL_TICKER_FUTURES_STARTTIME.replace("xxxxxx", symbol) + interval;
        List<KlineObjectNumber> results = new ArrayList();
        Long time = startTime;
        while (true) {
            try {
                String urlData = url.replace("tttttt", time.toString());
                String respon = HttpRequest.getContentFromUrl(urlData);
                if (StringUtils.isEmpty(respon) || StringUtils.length(respon) < 100) {
//                    LOG.info("Error respon of sym: {} {}", symbol, new Date(time));
                    break;
                }
                try {
                    List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
                    for (List<Object> allKline : allKlines) {
                        results.add(KlineObjectNumber.convertString2Kline(allKline));
                    }
                    if (results.get(results.size() - 1).endTime> System.currentTimeMillis()) {
                        break;
                    } else {
                        time = results.get(results.size() - 1).endTime + 1;
                    }
                } catch (Exception e) {
//                    LOG.info("Error respon of sym: {} {}", respon, new Date(time));
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



    public static CandlestickEvent convertString2Candle(String symbol, List<Object> kline) {
        CandlestickEvent result = new CandlestickEvent();
        result.setSymbol(symbol);
        Float startTime = (Float) kline.get(0);
        result.setStartTime(startTime.longValue());
        result.setOpen(new BigDecimal(Float.valueOf(kline.get(1).toString())));
        result.setHigh(new BigDecimal(Float.valueOf(kline.get(2).toString())));
        result.setLow(new BigDecimal(Float.valueOf(kline.get(3).toString())));
        result.setClose(new BigDecimal(Float.valueOf(kline.get(4).toString())));
        Float endTime = (Float) kline.get(6);
        result.setCloseTime(endTime.longValue());
        result.setVolume(new BigDecimal(Float.valueOf(kline.get(7).toString())));
        return result;
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
            LOG.info("Error get ticker {} {}", Utils.normalizeDateYYYYMMDDHHmm(startTime), symbol);
            e.printStackTrace();
        }

        return results;
    }

    public static TreeMap<Long, FundingRate> getFundingFeeWithStartTime(String symbol, Long startTime) {
        String url = Constants.URL_FUNDING_FEE_FUTURES_START_TIME.replace("xxxxxx", symbol);
        TreeMap<Long, FundingRate> results = new TreeMap<>();
        try {
            String urlData = url.replace("tttttt", startTime.toString());
            String respon = HttpRequest.getContentFromUrl(urlData);
            if (respon.length() > 100) {
                List<Map<Object, Object>> allKlines = Utils.gson.fromJson(respon, List.class);
                for (Map<Object, Object> objs : allKlines) {
                    try {
                        if (objs.get("markPrice").equals("")){
                            objs.put("markPrice", "0");
                        }
                        results.put(Utils.getHour(new BigDecimal(objs.get("fundingTime").toString()).longValue()),
                                Utils.gson.fromJson(objs.toString(), FundingRate.class));
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            }

        } catch (Exception e) {
            LOG.info("Error get funding fee: {} {}", symbol, startTime);
            e.printStackTrace();
        }

        return results;
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

    public static TreeMap<Float, String> getSymbolVolumeLower() {
        TreeMap<Float, String> results = new TreeMap<Float, String>();
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                results.put(Float.parseFloat(ticker.getQuoteVolume()), ticker.getSymbol());
            }
        }
        return results;
    }
    public static TreeMap<String, Float> getSymbolPrice() {
        TreeMap<String, Float>  results = new TreeMap<>();
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                results.put( ticker.getSymbol(),Float.parseFloat(ticker.getLastPrice()));
            }
        }
        return results;
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
        TreeMap<Float, String> volume2Symbol = getSymbolVolumeLower();
        for (Float volume : volume2Symbol.keySet()) {
            LOG.info("{} {} ", volume2Symbol.get(volume), volume / 1E6);
        }
//        LOG.info("{}", TickerFuturesHelper.getFundingFeeWithStartTime("OCEANUSDT", 1731916800000L));
//        getCurrentTrendLongTime(Contanst.SYMBOL_PAIR_BTC, 60);
//        System.out.println(getCurrentTrendWithInterval("DYDXUSDT", Contanst.INTERVAL_15M));
//        System.out.println(Utils.toJson(getLastTicker("DYDXUSDT", Contanst.INTERVAL_15M)));
//        System.out.println(Utils.toJson(getLastTicker("WLDUSDT", Contanst.INTERVAL_15M)));
//        System.out.println(Utils.toJson(getLastTicker(Contanst.SYMBOL_PAIR_BTC, Contanst.INTERVAL_15M)));
    }

    public static KlineObjectNumber extractKlineByNumberTicker(List<KlineObjectNumber> tickers, int index, int numberTicker, int numberAgo) {
        if (index < numberTicker) {
            return null;
        }
        Float maxPrice = null;
        Float minPrice = null;
        Float lastPrice = null;
        Float openPrice = null;
        Long timeStart = null;
        Long timeEnd = null;
        Float totalUsdt = 0f;

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
