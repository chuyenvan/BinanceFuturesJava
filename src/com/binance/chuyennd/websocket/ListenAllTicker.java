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
package com.binance.chuyennd.websocket;

import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.statistic24hr.Volume24hrManager;
import com.binance.chuyennd.trading.DetectEntrySignal2TradeNormal;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.CandlestickInterval;
import com.binance.client.model.event.CandlestickEvent;
import com.binance.client.model.event.SymbolTickerEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;

/**
 * @author pc
 */
public class ListenAllTicker {

    public static final Logger LOG = LoggerFactory.getLogger(ListenAllTicker.class);
    public static final ConcurrentHashMap<String, TreeMap<Long, CandlestickEvent>> symbol2Tickers = new ConcurrentHashMap<>();
    public static final ConcurrentHashMap<String, Double> symbol2Price = new ConcurrentHashMap<>();
    private static volatile ListenAllTicker INSTANCE = null;

    public static ListenAllTicker getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new ListenAllTicker();
            INSTANCE.initData();
            INSTANCE.startThreadUpdateTicker();
        }
        return INSTANCE;
    }

    private void initData() {

    }

    public static void main(String[] args) {
            ListenAllTicker.getInstance().startThreadMonitor();
    }

    public void startThreadUpdateTicker() {
        SubscriptionClient client = SubscriptionClient.create();
        List<String> symbols = new ArrayList<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS)) {
            symbols.add(symbol.toLowerCase());
        }
        List<List<String>> sublist = Utils.subList(symbols, 100);
        for (List<String> list : sublist) {
            client.subscribeAllCandlestickEvent(list, CandlestickInterval.ONE_MINUTE, ((event) -> {
//                LOG.info("Update ticker: {}", Utils.gson.toJson(event));
                updateDate(event);
            }), null);
        }
    }

    public void startThreadListenASymbol(String symbol) {
        SubscriptionClient client = SubscriptionClient.create();
        client.subscribeCandlestickEvent(symbol.toLowerCase(), CandlestickInterval.ONE_MINUTE, ((event) -> {
            updateDate(event);
        }), null);

    }


    public void startThreadMonitor() {
        new Thread(() -> {
            Thread.currentThread().setName("startThreadMonitor");
            LOG.info("Start thread startThreadMonitor  target: {}", Configs.RATE_TARGET);
            while (true) {
                if (isTimeGetData()) {
                    try {
                        TreeMap<Long, CandlestickEvent> tickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BTC);
                        LOG.info("Total symbols: {}", symbol2Tickers.size());
                        if (tickers != null) {
                            for (CandlestickEvent ticker : tickers.values()) {
                                LOG.info("{} {} {} {} {} {}", ticker.getSymbol(), Utils.normalizeDateYYYYMMDDHHmm(ticker.getStartTime()),
                                        ticker.getOpen(), ticker.getHigh(), ticker.getLow(), ticker.getClose());
                            }
                        }
                        tickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BNB);
                        if (tickers != null) {
                            for (CandlestickEvent ticker : tickers.values()) {
                                LOG.info("{} {} {} {} {} {}", ticker.getSymbol(), Utils.normalizeDateYYYYMMDDHHmm(ticker.getStartTime()),
                                        ticker.getOpen(), ticker.getHigh(), ticker.getLow(), ticker.getClose());
                            }
                        }
                        tickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_ETH);
                        if (tickers != null) {
                            for (CandlestickEvent ticker : tickers.values()) {
                                LOG.info("{} {} {} {} {} {}", ticker.getSymbol(), Utils.normalizeDateYYYYMMDDHHmm(ticker.getStartTime()),
                                        ticker.getOpen(), ticker.getHigh(), ticker.getLow(), ticker.getClose());
                            }
                        }
                        tickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_XRP);
                        if (tickers != null) {
                            for (CandlestickEvent ticker : tickers.values()) {
                                LOG.info("{} {} {} {} {} {}", ticker.getSymbol(), Utils.normalizeDateYYYYMMDDHHmm(ticker.getStartTime()),
                                        ticker.getOpen(), ticker.getHigh(), ticker.getLow(), ticker.getClose());
                            }
                        }
                    } catch (Exception e) {
                        LOG.error("ERROR during ThreadDetectMarketLevel2Trader: {}", e);
                        e.printStackTrace();
                    }
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND / 10);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectEntrySignal2TradeNormal.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    public static boolean isTimeGetData() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 0 && miniSecond > 200 && miniSecond < 300;
    }

    private static void updateDate(CandlestickEvent event) {
        TreeMap<Long, CandlestickEvent> tickers = symbol2Tickers.get(event.getSymbol());
        if (tickers == null) {
            tickers = new TreeMap<>();
        }
        tickers.put(event.getStartTime(), event);
        symbol2Tickers.put(event.getSymbol(), tickers);
        symbol2Price.put(event.getSymbol(), event.getClose().doubleValue());
        if (Constants.specialSymbol.contains(event.getSymbol())) {
            LOG.info("{} {}", event.getSymbol(), symbol2Price.get(event.getSymbol()));
        }
    }


}
