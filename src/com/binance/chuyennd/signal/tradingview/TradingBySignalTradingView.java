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
package com.binance.chuyennd.signal.tradingview;

import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import com.google.gson.internal.LinkedTreeMap;
import java.io.IOException;
import java.util.Collection;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentSkipListSet;
import java.util.logging.Level;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class TradingBySignalTradingView {

    public static final Logger LOG = LoggerFactory.getLogger(TradingBySignalTradingView.class);
    private final ConcurrentSkipListSet<String> allSymbol = new ConcurrentSkipListSet<>();
    public static final String URL_SIGNAL_TRADINGVIEW = "http://172.25.80.128:8002/";
    public final String URL_TICKER_15M = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&interval=15m";
    public static Integer LIMIT_ORDER_RUN_FOR_TEST = Configs.getInt("LimitOrderRunTest");
    public static Integer counter = 0;

    public static void main(String[] args) throws IOException {
        new TradingBySignalTradingView().checkStrongSignal2Trading();
//        new TradingBySignalTradingView().getStrongSignal2Trading();
//        System.out.println(new TradingBySignalTradingView().getReconmendation("BTCUSDT"));
    }

    private void checkStrongSignal2Trading() {
        new Thread(() -> {
            Thread.currentThread().setName("StrongSignal2Trading");
            LOG.info("Start thread StrongSignal2Trading!");
            while (true) {
                try {
                    if (counter >= LIMIT_ORDER_RUN_FOR_TEST) {
                        LOG.info("Over limit to test!");
                        Thread.sleep(Utils.TIME_HOUR);
                        continue;
                    }
                    getStrongSignal2Trading();
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadBigBeardTrading: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(Utils.TIME_MINUTE);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(TradingBySignalTradingView.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private OrderSide getStrongSignalASymbol(String symbol) {
        try {
            String signalRecommendation = getReconmendation(symbol);
            if (StringUtils.isNotEmpty(signalRecommendation)) {
                OrderSide sideSignal = OrderSide.BUY;
                if (StringUtils.equalsIgnoreCase(signalRecommendation, "sell")) {
                    sideSignal = OrderSide.SELL;
                }
                return sideSignal;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private void getStrongSignal2Trading() {
        LOG.info("Start detect symbol is Strong signal! {}", new Date());
        if (allSymbol.isEmpty()) {
            allSymbol.addAll(getAllSymbol());
        }
        for (String symbol : allSymbol) {
            try {

                // check symbol had position running                        
                if (RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol) != null) {
                    String log = "Symbol " + symbol + " had order active: ";
                    LOG.info(log);
                    continue;
                }
                OrderSide sideSignal = getStrongSignalASymbol(symbol);
                if (sideSignal != null) {
                    addOrderTrading(symbol, sideSignal);
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private Collection<? extends String> getAllSymbol() {
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

    private String getReconmendation(String symbol) {
        String result = "";
        try {
            String urlSignal = URL_SIGNAL_TRADINGVIEW + symbol;
            String respon = HttpRequest.getContentFromUrl(urlSignal);
            List<LinkedTreeMap> responObjects = Utils.gson.fromJson(respon, List.class);
            if (responObjects != null && !responObjects.isEmpty()) {
                String sideSignal = responObjects.get(0).get("recommendation").toString();
                if (StringUtils.contains(sideSignal, "STRONG")) {
                    result = sideSignal.split("_")[1];
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return result;
    }

    private void addOrderTrading(String symbol, OrderSide sideSignal) {
        if (sideSignal.equals(OrderSide.BUY)) {
            String log = "Long " + symbol + " by signal tradingview";
            Utils.sendSms2Telegram(log);
            if (counter >= LIMIT_ORDER_RUN_FOR_TEST) {
                LOG.info("Over limit to test!");
                return;
            }
            PositionHelper.getInstance().addOrderBySignal(symbol, OrderSide.BUY);
            counter++;
            LOG.info(log);
        }
    }

}
