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
package com.binance.chuyennd.testing;

import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class DetectSymbolBigChangeInTime {

    public static final Logger LOG = LoggerFactory.getLogger(DetectSymbolBigChangeInTime.class);
    public static long TIME_DETECT;
    public static Double PERCENT_BIGCHANGE;
    public static Double RATE_STOPLOSS;
    public static Map<String, TickerStatistics> lastTickerByTime = new HashMap<>();

    public static void main(String[] args) {
        startThreadDetectSymbolBigChangeInTime();
    }

    private static void startThreadDetectSymbolBigChangeInTime() {
        TIME_DETECT = Configs.getInt("TimeMinuteCheck") * Utils.TIME_SECOND;
        PERCENT_BIGCHANGE = Configs.getDouble("PercentBigChange");
        RATE_STOPLOSS = Configs.getDouble("StopLossRate");

        new Thread(() -> {
            Thread.currentThread().setName("ThreadDetectSymbolBigChangeInTime");
            LOG.info("Start thread ThreadDetectSymbolBigChangeInTime {} seconds -> {}%", TIME_DETECT / Utils.TIME_SECOND, PERCENT_BIGCHANGE * 100);
            while (true) {
                try {
                    String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
                    List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
                    for (Object futurePrice : futurePrices) {
                        TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
                        if (ticker.getLastPrice().equals(ticker.getHighPrice())) {
                            LOG.info("Symbol price api erorr: {}", ticker.getSymbol());
                        } else {
                            TickerStatistics tickerBefore = lastTickerByTime.get(ticker.getSymbol());
                            if (tickerBefore != null) {
                                Double price = Double.valueOf(ticker.getLastPrice());
                                Double beforePrice = Double.valueOf(tickerBefore.getLastPrice());
                                double percentChange = (beforePrice - price) / beforePrice;
                                if (Math.abs(percentChange) > PERCENT_BIGCHANGE) {
                                    Utils.sendSms2Telegram(ticker.getSymbol() + " had change: " + beforePrice + "->" + price + " percent: " + percentChange);
//                                    LOG.info("Warning symbol: {} lastPrice: {} currentPrice:{} percent: {}%", ticker.getSymbol(),
//                                            beforePrice, price, Utils.formatPercent(percentChange));

                                    OrderSide orderSide = OrderSide.BUY;
                                    if (percentChange > 0.01) {
                                        percentChange = 0.01;
                                    }
                                    if (percentChange < -0.01) {
                                        percentChange = -0.01;
                                    }
                                    Double stopLoss = price - percentChange * RATE_STOPLOSS * price;
                                    Double takeProfit = beforePrice;
                                    if (percentChange < 0) {
                                        orderSide = OrderSide.SELL;
                                    }
//                                    PositionManagerChangeInTime.getInstance().addOrderByTarget(ticker.getSymbol(),
//                                            stopLoss, price, takeProfit, orderSide, Double.valueOf(ticker.getPriceChangePercent()));
                                } else {
//                                    LOG.info("Check symbol: {} lastPrice: {} currentPrice:{} percent: {}%", ticker.getSymbol(),
//                                            beforePrice, price, Utils.formatPercent(percentChange));
                                }
                            }
                            lastTickerByTime.put(ticker.getSymbol(), ticker);
                        }
                    }
                    Thread.sleep(TIME_DETECT);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadDetectSymbolBigChangeInTime{}", e);
                    e.printStackTrace();
                }
            }
        }).start();

    }
}
