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
import com.binance.client.model.trade.Order;
import org.apache.commons.lang.StringUtils;
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
                        executorService.execute(() -> DcaHelper.startCheckAndProcessDca(symbol2Tickers));
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
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_TIME_2_MARKET_LEVEL,
                                time.toString(), levelChange.name());
                        levelChange = changeLevelByHistory(time, levelChange);
                        if (levelChange != null) {
                            // check and dca all order running when big down
                            if (levelChange.equals(MarketLevelChange.BIG_DOWN)
                                    || levelChange.equals(MarketLevelChange.MAYBE_BIG_DOWN_AFTER)
                                    || levelChange.equals(MarketLevelChange.MEDIUM_DOWN)) {
                                BinanceOrderTradingManager.checkAndDca();
                            }
                            // create new order
                            List<String> symbol2Trade = MarketBigChangeDetector.getTopSymbol2TradeWithRateChange(symbol2LastTicker, 20, levelChange);
                            LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), levelChange, symbol2Trade);
                            for (String symbol : symbol2Trade) {
                                try {
                                    KlineObjectNumber ticker = symbol2LastTicker.get(symbol);
                                    createOrderBuyRequest(symbol, ticker, levelChange);
                                } catch (Exception e) {
                                    e.printStackTrace();
                                }
                            }
                        }
                    } else {
                        // check not position running
                        MarketLevelChange orderMarketRunning = getOrderMarketLevelRunning();
                        TreeMap<Double, String> rateChange2Symbol = new TreeMap<>();
                        TreeMap<Double, String> rateChange2SymbolExtend = new TreeMap<>();
                        TreeMap<Double, String> rateChange2SymbolUnder5 = new TreeMap<>();
                        List<String> symbolSellCouples = new ArrayList<>();
                        if (orderMarketRunning == null || orderMarketRunning.equals(MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND)) {
                            for (Map.Entry<String, List<KlineObjectNumber>> entry1 : symbol2Tickers.entrySet()) {
                                String symbol = entry1.getKey();
                                List<KlineObjectNumber> tickers = entry1.getValue();
                                KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
                                // check sell
                                if (MarketBigChangeDetector.isSignalSELL(tickers, tickers.size() - 1)) {
                                    symbolSellCouples.add(symbol);
                                }
                                // check buy
                                List<Integer> altReverseStatus = MarketBigChangeDetector.getStatusTradingAlt15M(tickers, tickers.size() - 1);
                                if (altReverseStatus.contains(1)) {
                                    rateChange2Symbol.put(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen), symbol);
                                }
                                if (altReverseStatus.contains(2)) {
                                    rateChange2SymbolExtend.put(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen), symbol);
                                }
                                if (altReverseStatus.contains(3)) {
                                    rateChange2SymbolUnder5.put(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen), symbol);
                                }
                            }
                            try {
                                Utils.sendSms2Telegram("Check alt reverse : " + Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis() - 15
                                        * Utils.TIME_MINUTE) + " number alt:" + rateChange2Symbol.values() + " "
                                        + rateChange2SymbolExtend.values() + " " + rateChange2SymbolUnder5.values());
                            } catch (Exception e) {
                                e.printStackTrace();
                            }
                            if (rateChange2Symbol.size() >= 5) {
                                levelChange = MarketLevelChange.ALT_BIG_CHANGE_REVERSE;
                                int counter = 0;
                                for (Map.Entry<Double, String> entry2 : rateChange2Symbol.entrySet()) {
                                    String symbol = entry2.getValue();
                                    LOG.info("Alt reverse: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol);
                                    KlineObjectNumber ticker = symbol2LastTicker.get(symbol);
                                    createOrderBuyRequest(symbol, ticker, levelChange);
                                    counter++;
                                    if (counter >= 6) {
                                        break;
                                    }
                                }
                            } else {
                                if (orderMarketRunning == null) {
                                    if (!rateChange2SymbolExtend.isEmpty()) {
                                        levelChange = MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND;
                                        int counter = 0;
                                        for (Map.Entry<Double, String> entry2 : rateChange2SymbolExtend.entrySet()) {
                                            String symbol = entry2.getValue();
                                            LOG.info("Alt Reverse extend: {} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange,
                                                    symbol, rateChange2SymbolExtend.size());
                                            KlineObjectNumber ticker = symbol2LastTicker.get(symbol);
                                            createOrderBuyRequest(symbol, ticker, levelChange);
                                            counter++;
                                            if (counter >= 5) {
                                                break;
                                            }
                                        }
                                    } else {
                                        levelChange = MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND;
                                        for (Map.Entry<Double, String> entry2 : rateChange2SymbolUnder5.entrySet()) {
                                            if (BinanceFuturesClientSingleton.getInstance().getAllOpenOrderInfos().size() < 3) {
                                                String symbol = entry2.getValue();
                                                LOG.info("Alt reverse2: {} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange,
                                                        symbol, rateChange2Symbol.size());
                                                KlineObjectNumber ticker = symbol2LastTicker.get(symbol);
                                                createOrderBuyRequest(symbol, ticker, levelChange);
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        levelChange = MarketLevelChange.ALT_SIGNAL_SELL;
                        for (String symbol : symbolSellCouples) {
                            LOG.info("Alt Sell: {} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange,
                                    symbol, rateChange2Symbol.size());
                            createOrderSELLRequest(symbol, symbol2LastTicker.get(symbol), levelChange);
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
        LOG.info("Finish check level change of market 2 trade: {}", new Date());
    }

    private MarketLevelChange getOrderMarketLevelRunning() {
        List<Order> orders = BinanceFuturesClientSingleton.getInstance().getAllOpenOrderInfos();
        if (orders.isEmpty()) {
            return null;
        }
        MarketLevelChange level = MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND;
        for (Order order : orders) {
            String marketLevel = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_POS_MARKET_LEVEL, order.getSymbol());
            if (!StringUtils.equals(marketLevel, MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND.toString())) {
                level = MarketLevelChange.MULTI_LEVEL_MARKET_RUNNING;
            }
        }
        return level;
    }

    private void createOrderBuyRequest(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange) {
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
        if (levelChange.equals(MarketLevelChange.ALT_BIG_CHANGE_REVERSE)
                || levelChange.equals(MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND)) {
            budget = budget * 4;
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

    private void createOrderSELLRequest(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange) {
        LOG.info("Market level:{} {} {}", levelChange, symbol, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
        Double rateTarget = RATE_TARGET;
        Double budget = BudgetManager.getInstance().getBudget();
        Double priceEntry = ticker.priceClose;
        Double priceTarget = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, rateTarget);
        Double quantity = Utils.calQuantity(budget, BudgetManager.getInstance().getLeverage(), priceEntry, symbol);
        if (quantity != null && quantity != 0) {
            OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
                    priceTarget, quantity, BudgetManager.getInstance().getLeverage(), symbol, ticker.startTime.longValue(),
                    ticker.startTime.longValue(), OrderSide.SELL, Constants.TRADING_TYPE_VOLUME_MINI);
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

    private void initData() {
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

    private MarketLevelChange changeLevelByHistory(Long time, MarketLevelChange levelChange) {
        Long time2Get;
        String lastLevel;
        int counter = 0;
        while (true) {
            try {
                counter++;
                time2Get = time - counter * 15 * Utils.TIME_MINUTE;
                lastLevel = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_TIME_2_MARKET_LEVEL, time2Get.toString());
                if (StringUtils.isNotEmpty(lastLevel)) {
                    break;
                }
                if (counter > 16) {
                    break;
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        if (StringUtils.isNotEmpty(lastLevel)) {
            if (levelChange.equals(MarketLevelChange.MAYBE_BIG_DOWN_AFTER)) {
                return null;
            }
        }
        return levelChange;
    }


}
