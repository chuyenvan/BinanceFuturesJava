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

import com.binance.chuyennd.position.manager.PositionHelper;
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
public class DetectBigChangeForTrading {

    public static final Logger LOG = LoggerFactory.getLogger(DetectBigChangeForTrading.class);
    public static final String URL_TICKER_15M = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&interval=15m";
    public static double RATE_BIG_CHANGE;

    public static void main(String[] args) throws IOException {
        checkBigChange2Trading();
//        checkBigChangeAndTradeARound();

    }

    private static void checkBigChange2Trading() {
        // init connection
        ClientSingleton.getInstance();
        new Thread(() -> {
            Thread.currentThread().setName("DetectBigChangeForTrading");
            RATE_BIG_CHANGE = Configs.getDouble("RateBigChange");
            LOG.info("Start thread DetectBigChangeForTrading with rate: {}!", RATE_BIG_CHANGE);
            while (true) {
                try {
                    if (isTimeRun()) {
                        checkBigChangeAndTradeARound();
                        Thread.sleep(Utils.TIME_MINUTE);
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadBigBeardTrading: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(15 * Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectBigChangeForTrading.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private static boolean getData(String symbol) {
        String urlM1 = URL_TICKER_15M.replace("xxxxxx", symbol);
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            KlineObject klineCloseObjectFinal = KlineObject.convertString2Kline(allKlines.get(allKlines.size() - 2));
            Double rateChange;
            Double priceClose = Double.valueOf(klineCloseObjectFinal.priceClose);
            Double priceOpen = Double.valueOf(klineCloseObjectFinal.priceOpen);

            if (priceClose < priceOpen) {
                rateChange = priceOpen - priceClose;
            } else {
                rateChange = priceClose - priceOpen;
            }
            double rateChangeTicker = rateChange / priceOpen;
            double priceEntryTarget;
            if (rateChangeTicker > RATE_BIG_CHANGE) {
                Utils.sendSms2Telegram(symbol + " big change: " + Utils.formatPercent(rateChangeTicker) + " " + new Date(klineCloseObjectFinal.startTime.longValue()));
                LOG.info("Big change {}: rate: {}/{}% Open: {} Close: {} TimeOpen: {} ", symbol, rateChangeTicker,
                        Utils.formatPercent(rateChangeTicker), priceOpen, priceClose, new Date(klineCloseObjectFinal.startTime.longValue()));
                priceEntryTarget = priceClose;
                OrderSide orderSide = OrderSide.BUY;
                if (priceClose > priceOpen) {
                    orderSide = OrderSide.SELL;
                }
//                PositionHelper.getInstance().addOrderByTarget(symbol, orderSide, priceEntryTarget);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    private static boolean isTimeRun() {
        return Utils.getCurrentMinute() % 15 == 1;
    }

    private static void checkBigChangeAndTradeARound() {
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
    }

}
