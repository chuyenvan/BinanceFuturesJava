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
package com.binance.chuyennd.funcs;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import java.util.List;
import com.binance.client.constant.Constants;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashSet;
import java.util.Set;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class TickerHelper {

    public static final Logger LOG = LoggerFactory.getLogger(TickerHelper.class);

    public static KlineObjectNumber getTickerByTime(String symbol, String interval, long time) {
        String urlM1 = Constants.URL_TICKER.replace("xxxxxx", symbol) + interval;
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            for (List<Object> allKline : allKlines) {
                KlineObjectNumber kline = KlineObjectNumber.convertString2Kline(allKline);
                if (kline.startTime.longValue() == time) {
                    return kline;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static KlineObjectNumber getLastTicker(String symbol, String interval) {
        String urlM1 = Constants.URL_TICKER.replace("xxxxxx", symbol) + interval;
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            return KlineObjectNumber.convertString2Kline(allKlines.get(allKlines.size() - 1));
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static List<KlineObjectNumber> getTicker(String symbol, String interval) {
        String urlM1 = Constants.URL_TICKER.replace("xxxxxx", symbol) + interval;
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
                    if (maxPrice == null || maxPrice < ticker.priceMax) {
                        maxPrice = ticker.priceMax;
                    }
                    if (minPrice == null || minPrice > ticker.priceMin) {
                        minPrice = ticker.priceMin;
                    }
                }
            }
            LOG.info("Max: {} Min: {} current: {}", maxPrice, minPrice, currentPirce);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static Collection<? extends String> getAllSymbol() {
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

    public static void main(String[] args) {
//        getCurrentTrendLongTime(Contanst.SYMBOL_PAIR_BTC, 60);
//        System.out.println(getCurrentTrendWithInterval("DYDXUSDT", Contanst.INTERVAL_15M));
//        System.out.println(Utils.toJson(getLastTicker("DYDXUSDT", Contanst.INTERVAL_15M)));
//        System.out.println(Utils.toJson(getLastTicker("WLDUSDT", Contanst.INTERVAL_15M)));
//        System.out.println(Utils.toJson(getLastTicker(Contanst.SYMBOL_PAIR_BTC, Contanst.INTERVAL_15M)));
    }

    public static Double getMaxPrice(List<KlineObjectNumber> kline1Ds, int limitDay2Get) {
        Double maxPrice = null;
        int counter = 0;
        for (int i = 0; i < kline1Ds.size(); i++) {
            KlineObjectNumber kline1D = kline1Ds.get(kline1Ds.size() - 1 - i);
            counter++;
            if (counter >= limitDay2Get) {
                break;
            }
            if (maxPrice == null || maxPrice < kline1D.priceMax) {
                maxPrice = kline1D.priceMax;
            }
        }
        return maxPrice;
    }

    public static Double getMinPrice(List<KlineObjectNumber> kline1Ds, int limitDay2Get) {
        Double minPrice = null;
        int counter = 0;
        for (int i = 0; i < kline1Ds.size(); i++) {
            KlineObjectNumber kline1D = kline1Ds.get(kline1Ds.size() - 1 - i);
            counter++;
            if (counter >= limitDay2Get) {
                break;
            }
            if (minPrice == null || minPrice > kline1D.priceMin) {
                minPrice = kline1D.priceMin;
            }
        }
        return minPrice;
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
            if (price < kline.priceMax && price > kline.priceMin) {
                counter++;
            }
        }
        return counter;
    }

    public static List<KlineObjectNumber> getTotalKlineBigchange(List<KlineObjectNumber> kline15ms, Double rateBigchange) {
        List<KlineObjectNumber> results = new ArrayList<>();
        for (KlineObjectNumber kline15m : kline15ms) {
            double rate = Utils.rateOf2Double(kline15m.priceMax, kline15m.priceMin);
            if (rate >= rateBigchange) {
                results.add(kline15m);
            }
        }
        return results;
    }
}
