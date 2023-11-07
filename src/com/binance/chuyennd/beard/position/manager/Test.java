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
package com.binance.chuyennd.beard.position.manager;

import static com.binance.chuyennd.beard.position.manager.CreatePositionNew.symbolAvalible2Trading;
import com.binance.chuyennd.object.KlineObject;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class Test {

    public static final Logger LOG = LoggerFactory.getLogger(Test.class);
    public static final String URL_TICKER_1D = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&interval=1d";

    public static void main(String[] args) {
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER));
//        extractRateChangeInMonth();
        int numberDay = 7;
        Double rateChange = 0.1;
        
    }

    private static void extractRateChangeInMonth() {

        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        TreeMap<Double, String> rateChangeInMonth = new TreeMap<>();
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                try {
                    // only get symbol over 2 months
                    double rateChange = getStartTimeAtExchange(ticker.getSymbol());
                    rateChangeInMonth.put(rateChange, ticker.getSymbol());
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

    private static double getStartTimeAtExchange(String symbol) {

        String urlM1 = URL_TICKER_1D.replace("xxxxxx", symbol);
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            if (allKlines.size() > 31) {
                KlineObject klineFinal = KlineObject.convertString2Kline(allKlines.get(allKlines.size() - 1));
                KlineObject klineLastMonth = KlineObject.convertString2Kline(allKlines.get(allKlines.size() - 30));
                double change = Double.parseDouble(klineFinal.priceMax) - Double.parseDouble(klineLastMonth.priceMax);
                return change / Double.parseDouble(klineLastMonth.priceMax);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0;

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
                Double result = (maxPrice - minPrice)/maxPrice;
                LOG.info("{} {}: {} -> {} ", symbol, result, minPrice, maxPrice);
                return result;
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0d;
    }
}
