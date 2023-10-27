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
package com.binance.chuyennd.beard;

import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.chuyennd.object.KlineObject;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import java.io.IOException;
import java.util.Date;
import java.util.List;
import java.util.logging.Level;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class DetectBeardForTrading {

    public static final Logger LOG = LoggerFactory.getLogger(DetectBeardForTrading.class);
    public static final String URL_KLINE_M15 = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&interval=15m";
    public static double RATE_BIG_BEARD;

    public static void main(String[] args) throws IOException {
        checkBigBeard();

//        isTimeRun();
//        getData("OGNUSDT");
    }

    private static void checkBigBeard() {
        // init connection
        ClientSingleton.getInstance();
        new Thread(() -> {
            Thread.currentThread().setName("ThreadBigBeardTrading");
            LOG.info("Start thread ThreadBigBeardTrading!");
            RATE_BIG_BEARD = Configs.getDouble("RateBigBeard");
            while (true) {
                try {
                    if (isTimeRun()) {
                        LOG.info("Start detect symbol is beard big! {}", new Date());
                        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
                        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
                        for (Object futurePrice : futurePrices) {
                            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
                            if (ticker.getLastPrice().equals(ticker.getHighPrice())) {
                                LOG.info("Symbol price api erorr: {}", ticker.getSymbol());
                            } else {
                                // get all 1d 
                                // get price max, min, current, rate change
                                getData(ticker.getSymbol());
                            }
                        }
                        Thread.sleep(Utils.TIME_MINUTE);
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadBigBeardTrading: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(15 * Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectBeardForTrading.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private static boolean getData(String symbol) {
        String urlM1 = URL_KLINE_M15.replace("xxxxxx", symbol);
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            KlineObject klineCloseObjectFinal = KlineObject.convertString2Kline(allKlines.get(allKlines.size() - 2));
            Double beardAbove;
            Double beardBelow;
            Double priceClose = Double.valueOf(klineCloseObjectFinal.priceClose);
            Double priceOpen = Double.valueOf(klineCloseObjectFinal.priceOpen);
            Double priceMax = Double.valueOf(klineCloseObjectFinal.priceMax);
            Double priceMin = Double.valueOf(klineCloseObjectFinal.priceMin);
            if (priceClose > priceOpen) {
                beardAbove = priceMax - priceClose;
                beardBelow = priceOpen - priceMin;
            } else {
                beardAbove = priceMax - priceOpen;
                beardBelow = priceClose - priceMin;
            }
            double rateChangeAbove = beardAbove / priceClose;
            double rateChangeBelow = beardBelow / priceClose;
            double priceEntryTarget;
            if (rateChangeAbove > RATE_BIG_BEARD) {
                Utils.sendSms2Telegram(symbol + " big above beard change: " + Utils.formatPercent(beardAbove) + " " + new Date(klineCloseObjectFinal.startTime.longValue()));
                LOG.info("Big beard above {}: beard/rate: {}/{}% Open: {} Max: {} Close: {} TimeOpen: {} ", symbol, Utils.normalPrice2Api(beardAbove),
                        Utils.formatPercent(rateChangeAbove), priceOpen, priceMax, priceClose, new Date(klineCloseObjectFinal.startTime.longValue()));
                priceEntryTarget = priceClose;
                if (priceClose < priceOpen) {
                    priceEntryTarget = priceOpen;
                }
                PositionManagerTradingBeard.getInstance().addOrderByTarget(symbol, OrderSide.SELL, priceEntryTarget);
            } else {
                if (rateChangeBelow > RATE_BIG_BEARD) {
                    Utils.sendSms2Telegram(symbol + " big below beard change: " + Utils.formatPercent(beardBelow) + " " + new Date(klineCloseObjectFinal.startTime.longValue()));
                    LOG.info("Big beard below {}: beard/rate: {}/{}% Open: {} Max: {} Close: {} TimeOpen: {} ", symbol, Utils.normalPrice2Api(beardBelow),
                            Utils.formatPercent(rateChangeBelow), priceOpen, priceMax, priceClose, new Date(klineCloseObjectFinal.startTime.longValue()));
                    priceEntryTarget = priceClose;
                    if (priceClose > priceOpen) {
                        priceEntryTarget = priceOpen;
                    }
                    PositionManagerTradingBeard.getInstance().addOrderByTarget(symbol, OrderSide.BUY, priceEntryTarget);
                }
            }
        } catch (Exception e) {
        }
        return false;
    }

    private static boolean isTimeRun() {
        return Utils.getCurrentMinute() % 15 == 0;
    }

}
