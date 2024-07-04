/*
 * Copyright 2024 pc.
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
package com.binance.chuyennd.trading;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetector;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;

/**
 * @author pc
 */
public class MarketLevelChangeTrader {

    public static final Logger LOG = LoggerFactory.getLogger(MarketLevelChangeTrader.class);
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    public Set<? extends String> allSymbol;
    public Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public ConcurrentHashMap<String, List<KlineObjectNumber>> symbol2Tickers = new ConcurrentHashMap<>();

    public static void main(String[] args) throws InterruptedException, ParseException {
        new MarketLevelChangeTrader().getTickerBySymbol("QNTUSDT");
    }

    public void start() throws InterruptedException, ParseException {
        initData();
        startThreadDetectMarketLevel2Trader();
    }

    public void startThreadDetectMarketLevel2Trader() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadDetectMarketLevel2Trader");
            LOG.info("Start thread ThreadDetectMarketLevel2Trader  target: {}", RATE_TARGET);
            while (true) {
                if (isTimeGetData()) {
                    try {
                        LOG.info("Start get data of market! {}", new Date());
                        allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS);
                        symbol2Tickers.clear();
                        for (String symbol : allSymbol) {
                            executorService.execute(() -> getTickerBySymbol(symbol));
                        }
                    } catch (Exception e) {
                        LOG.error("ERROR during ThreadDetectMarketLevel2Trader: {}", e);
                        e.printStackTrace();
                    }
                }
                if (isTimeTrader()) {
                    try {
                        LOG.info("Start check level change of market for trade! {}", new Date());
                        executorService.execute(() -> checkMarketLevelChange2Trade());
                    } catch (Exception e) {
                        LOG.error("ERROR during ThreadDetectMarketLevel2Trader: {}", e);
                        e.printStackTrace();
                    }
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(MarketLevelChangeTrader.class.getName()).log(Level.SEVERE, null, ex);
                }

            }
        }).start();
    }

    private void checkMarketLevelChange2Trade() {
        while (true) {
            if (symbol2Tickers.size() >= 150) {
                try {
                    Map<String, KlineObjectNumber> symbol2LastTicker = new HashMap<>();
                    Map<String, KlineObjectNumber> lastSymbol2LastTicker = new HashMap<>();
                    for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Tickers.entrySet()) {
                        String symbol = entry.getKey();
                        List<KlineObjectNumber> values = entry.getValue();
                        symbol2LastTicker.put(symbol, values.get(values.size() - 1));
                        lastSymbol2LastTicker.put(symbol, values.get(values.size() - 2));
                    }
                    MarketLevelChange levelChange = MarketBigChangeDetector.detectLevelChangeProduction(symbol2LastTicker);
                    Long time = System.currentTimeMillis() - Utils.TIME_MINUTE * 15;
                    if (symbol2LastTicker.get(Constants.SYMBOL_PAIR_BTC) != null) {
                        time = symbol2LastTicker.get(Constants.SYMBOL_PAIR_BTC).startTime.longValue();
                    }
                    LOG.info("Market level change: {} level: {} symbols:{}", Utils.normalizeDateYYYYMMDDHHmm(time),
                            levelChange, symbol2LastTicker.size());
                    if (levelChange != null) {
                        List<String> symbol2Trade;
                        if (levelChange.equals(MarketLevelChange.VOLUME_BIG_CHANGE)) {
                            symbol2Trade = MarketBigChangeDetector.getTopSymbol2TradeWithVolumeBigUp(
                                    lastSymbol2LastTicker, symbol2LastTicker, 20);
                        } else {
                            symbol2Trade = MarketBigChangeDetector.getTopSymbol2Trade(symbol2LastTicker, 20, levelChange);
                        }
                        LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), levelChange, symbol2Trade);
                        for (String symbol : symbol2Trade) {
                            try {
                                KlineObjectNumber ticker = symbol2LastTicker.get(symbol);
                                createOrderNewRequest(symbol, ticker, levelChange);
                            } catch (Exception e) {
                                e.printStackTrace();
                            }
                        }
                    } else {
                        if (BinanceFuturesClientSingleton.getInstance().getAllOpenOrderInfos().isEmpty()) {
                            List<KlineObjectNumber> btcTickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BTC);
                            if (MarketBigChangeDetector.getStatusTradingBtc(btcTickers,
                                    btcTickers.get(btcTickers.size() - 1).startTime.longValue()) == 1) {
                                levelChange = MarketLevelChange.BTC_SMALL_CHANGE_REVERSE;
                                List<String> symbol2Trade = MarketBigChangeDetector.getTopSymbol2TradeWithVolumeBigUp(
                                        lastSymbol2LastTicker, symbol2LastTicker, 10);
                                LOG.info("Btc reverse: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2Trade);
                                for (String symbol : symbol2Trade) {
                                    try {
                                        KlineObjectNumber ticker = symbol2LastTicker.get(symbol);
                                        createOrderNewRequest(symbol, ticker, levelChange);
                                    } catch (Exception e) {
                                        e.printStackTrace();
                                    }
                                }
                            }
                        }
                        if (BinanceFuturesClientSingleton.getInstance().getAllOpenOrderInfos().isEmpty()) {
                            TreeMap<Double, String> rateChange2Symbol = new TreeMap<>();
                            for (Map.Entry<String, List<KlineObjectNumber>> entry1 : symbol2Tickers.entrySet()) {
                                String symbol = entry1.getKey();
                                List<KlineObjectNumber> tickers = entry1.getValue();
                                if (MarketBigChangeDetector.getStatusTradingAlt15M(tickers, tickers.size() - 1) == 1
                                ) {
                                    KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
                                    rateChange2Symbol.put(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen), symbol);
                                }
                            }
                            if (rateChange2Symbol.size() >= 5) {
                                levelChange = MarketLevelChange.ALT_BIG_CHANGE_REVERSE;
                                int counter = 0;
                                for (Map.Entry<Double, String> entry2 : rateChange2Symbol.entrySet()) {
                                    String symbol = entry2.getValue();
                                    LOG.info("Alt reverse: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol);
                                    KlineObjectNumber ticker = symbol2LastTicker.get(symbol);
                                    createOrderNewRequest(symbol, ticker, levelChange);
                                    counter++;
                                    if (counter >= 4) {
                                        break;
                                    }
                                }
                            }
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
                break;
            }
            try {
                Thread.sleep(Utils.TIME_SECOND);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        LOG.info("Finish check level change of market 2 trade: {}", new

                Date());
    }

    private void createOrderNewRequest(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange) {
        LOG.info("Market level:{} {} {}", levelChange, symbol, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
        Double rateTarget = RATE_TARGET;
        Double budget = BudgetManager.getInstance().getBudget();
        if (levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            rateTarget = 8 * rateTarget;
            budget = budget * 1.5;
        }
        if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)) {
            rateTarget = 4 * rateTarget;
            budget = budget * 1.5;
        }
        if (levelChange.equals(MarketLevelChange.BIG_UP)) {
            rateTarget = 2 * RATE_TARGET;
            budget = budget * 1.5;
        }
        if (levelChange.equals(MarketLevelChange.MEDIUM_UP)) {
            budget = budget * 1.5;
        }
        Double priceEntry = ticker.priceClose;
        Double priceTarget = Utils.calPriceTarget(symbol, priceEntry, OrderSide.BUY, rateTarget);
        Double quantity = Utils.calQuantity(budget, BudgetManager.getInstance().getLeverage(), priceEntry, symbol);
        if (quantity != null && quantity != 0) {
            OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
                    priceTarget, quantity, BudgetManager.getInstance().getLeverage(), symbol, ticker.startTime.longValue(),
                    ticker.startTime.longValue(), OrderSide.BUY, Constants.TRADING_TYPE_VOLUME_MINI);
            orderTrade.marketLevel = levelChange;
            RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
        } else {
            LOG.info("{} {} quantity false", symbol, quantity);
        }
    }

    public boolean isTimeGetData() {
        return Utils.getCurrentMinute() % 15 == 14 && Utils.getCurrentSecond() == 55;
    }

    public boolean isTimeTrader() {
        return Utils.getCurrentMinute() % 15 == 14 && Utils.getCurrentSecond() == 59;
    }

    private void initData() throws InterruptedException, ParseException {
        allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS);
        symbol2Tickers.clear();
    }

    private void getTickerBySymbol(String symbol) {
        try {
            List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_15M);
            if (!tickers.isEmpty()) {
                symbol2Tickers.put(symbol, tickers);
            }
        } catch (Exception e) {
            LOG.info("Error get ticker of:{}", symbol);
            e.printStackTrace();
        }
    }

}
