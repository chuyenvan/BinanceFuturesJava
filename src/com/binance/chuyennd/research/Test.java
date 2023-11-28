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
package com.binance.chuyennd.research;

import com.binance.chuyennd.funcs.TickerHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.object.TopBottomObject;
import com.binance.chuyennd.object.TopBottomState;
import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.trade.Order;
import static com.sun.tools.javac.tree.TreeInfo.symbol;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class Test {

    public static final Logger LOG = LoggerFactory.getLogger(Test.class);

    public static void main(String[] args) {
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER));
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE));
//        System.out.println(PositionHelper.getPositionBySymbol("LTCUSDT"));
//        extractRateChangeInMonth();
        showStatusOrderDCA();
//        detectTopBottomObjectInTicker("BTCUSDT");
//        extractVolume();
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

        try {
            List<KlineObjectNumber> allKlines = TickerHelper.getTicker(symbol, Constants.INTERVAL_1D);
            Double maxPrice = 0d;
            Double minPrice = 0d;
            if (allKlines.size() > 61) {
                KlineObjectNumber klineFinal = allKlines.get(allKlines.size() - 1);
                for (int i = 1; i < 61; i++) {
                    KlineObjectNumber kline = allKlines.get(allKlines.size() - 1 - i);
                    if (maxPrice < kline.priceMax) {
                        maxPrice = kline.priceMax;
                    }
                    if (minPrice == 0 || minPrice > kline.priceMin) {
                        minPrice = kline.priceMin;
                    }
                }
                double change = klineFinal.priceClose - minPrice;
                return change / minPrice;
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0;

    }

    private static void detectTopBottomObjectInTicker(String symbol) {
        double rateCheck = 0.0008;
        List<KlineObjectNumber> tickers = TickerHelper.getTicker(symbol, Constants.INTERVAL_15M);
        List<TopBottomObject> objects = new ArrayList<>();
        KlineObjectNumber lastTickerCheck = tickers.get(0);
        TopBottomState state = TopBottomState.TOP;
        for (KlineObjectNumber ticker : tickers) {
            if (state.equals(TopBottomState.TOP)) {
                if (Utils.rateOf2Double(lastTickerCheck.priceMax, ticker.priceMax) > rateCheck) {
                    if (lastTickerCheck.priceMax > ticker.priceMax) {
                        objects.add(new TopBottomObject(state, lastTickerCheck));
                    } else {
                        objects.add(new TopBottomObject(state, ticker));
                    }
                    state = TopBottomState.BOTTOM;
                }
            } else {
                if (Utils.rateOf2Double(ticker.priceMin, lastTickerCheck.priceMin) > rateCheck) {
                    if (lastTickerCheck.priceMin < ticker.priceMin) {
                        objects.add(new TopBottomObject(state, lastTickerCheck));
                    } else {
                        objects.add(new TopBottomObject(state, ticker));
                    }
                    state = TopBottomState.TOP;
                }
            }
            lastTickerCheck = ticker;
        }
        int counter = 0;
        for (int i = 0; i < objects.size(); i++) {
            counter++;
            if (counter == 30) {
                break;
            }
            TopBottomObject object = objects.get(objects.size() - 1 - i);
            if (object.status.equals(TopBottomState.TOP)) {
                LOG.info(" {} {} {}", new Date(object.kline.startTime.longValue()), object.status, object.kline.priceMax);
            } else {
                LOG.info(" {} {} {}", new Date(object.kline.startTime.longValue()), object.status, object.kline.priceMin);
            }
        }
    }

    private static void extractVolume() {
        List<KlineObjectNumber> tickers = TickerHelper.getTicker("CYBERUSDT", Constants.INTERVAL_1D);
        KlineObjectNumber lastTicker = tickers.get(0);
        for (KlineObjectNumber ticker : tickers) {
            LOG.info("Date {} Volume: {} , rate: {}", new Date(ticker.startTime.longValue()), ticker.volume, Utils.rateOf2Double(ticker.volume, lastTicker.volume));
            lastTicker = ticker;
        }
    }

    private static void showStatusOrderDCA() {
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER)) {
            Order orderDCA = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER, symbol), Order.class);
            Order orderDcaInfo = PositionHelper.getInstance().readOrderInfo(symbol, orderDCA.getOrderId());
            LOG.info("{} {} {}", symbol, orderDcaInfo.getOrderId(), orderDcaInfo.getStatus());
        }
    }

}
