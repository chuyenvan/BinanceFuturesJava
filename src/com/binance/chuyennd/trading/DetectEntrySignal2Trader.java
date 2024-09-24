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

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.SubscriptionErrorHandler;
import com.binance.client.constant.Constants;
import com.binance.client.exception.BinanceApiException;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.event.SymbolTickerEvent;
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
public class DetectEntrySignal2Trader {

    public static final Logger LOG = LoggerFactory.getLogger(DetectEntrySignal2Trader.class);
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    public BinanceOrderTradingManager orderManager = new BinanceOrderTradingManager();
    public Set<? extends String> allSymbol;

    public ConcurrentHashMap<String, List<KlineObjectNumber>> symbol2Tickers = new ConcurrentHashMap<>();

    public static void main(String[] args) throws InterruptedException, ParseException {
//        new DetectEntrySignal2Trader().getTickerBySymbol("QNTUSDT");
//        String symbol = "MAGICUSDT";
        new DetectEntrySignal2Trader().testCreateOrder("REEFUSDT");
//        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1M);
//        new DetectEntrySignal2Trader().createOrderBuyRequest(symbol, tickers.get(tickers.size() - 1), tickers.get(tickers.size() - 2), MarketLevelChange.BIG_UP);
//        System.out.println(getOrderMarketLevelRunning());
    }

    private void testCreateOrder(String symbol) throws ParseException {
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1M);
        KlineObjectNumber lastTicker = null;
        KlineObjectNumber ticker = null;
        for (KlineObjectNumber t : tickers) {
            if (t.startTime.longValue() == Utils.sdfFileHour.parse("20240812 14:00").getTime()) {
                ticker = t;
                break;
            }
            lastTicker = t;
        }
        if (ticker != null) {
            Double rateTarget;
            rateTarget = Utils.rateOf2Double(ticker.priceOpen, ticker.priceClose) / 2;
            if (lastTicker != null
                    && Utils.rateOf2Double(lastTicker.priceClose, lastTicker.priceOpen) < 0) {
                rateTarget = Utils.rateOf2Double(lastTicker.priceOpen, ticker.priceClose) / 2;
            }
//            createOrderBuyRequest(symbol, ticker, rateTarget, MarketLevelChange.MEDIUM_DOWN);
        }
    }

    public void start() throws InterruptedException, ParseException {
        initData();
        startThreadDetectMarketLevel2Trader();
    }


    public void startThreadDetectMarketLevel2Trader() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadDetectMarketLevel2Trader");
            LOG.info("Start thread ThreadDetectMarketLevel2Trader  target: {}", Configs.RATE_TARGET);
            int counter = 0;
            while (true) {
                counter++;
                if (counter % 36000 == 0) {
                    allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
                }
                if (isTimeGetData()) {
                    try {
                        symbol2Tickers.clear();
                        LOG.info("Start get data of market! {}", new Date());
                        Long startTime = Utils.getMinute(System.currentTimeMillis() - (Configs.NUMBER_TICKER_CAL_RATE_CHANGE + 1) * Utils.TIME_MINUTE);
                        for (String symbol : allSymbol) {
                            if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
                                continue;
                            }
                            executorService.execute(() -> getTickerBySymbol(symbol, startTime));
                        }
                        executorService.execute(() -> getTickerBySymbol(Constants.SYMBOL_PAIR_BTC, startTime - 4 * Utils.TIME_MINUTE));
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
                    Thread.sleep(Utils.TIME_SECOND / 10);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectEntrySignal2Trader.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private void checkMarketLevelChange2Trade() {
        while (true) {
            if (symbol2Tickers.containsKey(Constants.SYMBOL_PAIR_BTC)) {
                try {
                    Map<String, KlineObjectNumber> symbol2FinalTicker = new HashMap<>();
                    TreeMap<Double, String> rateDown15M2Symbols = new TreeMap<>();
                    TreeMap<Double, String> rateUp15M2Symbols = new TreeMap<>();
                    TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
                    TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();

                    List<KlineObjectNumber> btcTickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BTC);
                    KlineObjectNumber btcTicker = btcTickers.get(btcTickers.size() - 1);
                    Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);

                    for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Tickers.entrySet()) {
                        try {
                            String symbol = entry.getKey();
                            if (Constants.diedSymbol.contains(symbol)) {
                                continue;
                            }
                            List<KlineObjectNumber> values = entry.getValue();
                            KlineObjectNumber finalTicker = values.get(values.size() - 1);
                            symbol2FinalTicker.put(symbol, finalTicker);
                            Double rateChange = Utils.rateOf2Double(finalTicker.priceClose, finalTicker.priceOpen);
                            rateDown2Symbols.put(rateChange, symbol);
                            rateUp2Symbols.put(-rateChange, symbol);
                            Double priceMax = null;
                            Double priceMin = null;
                            for (int i = 0; i < values.size() - 1; i++) {
                                KlineObjectNumber ticker = values.get(i);
                                if (priceMax == null || priceMax < ticker.maxPrice) {
                                    priceMax = ticker.maxPrice;
                                }
                                if (priceMin == null || priceMin > ticker.minPrice) {
                                    priceMin = ticker.minPrice;
                                }
                            }
                            rateDown15M2Symbols.put(Utils.rateOf2Double(values.get(values.size() - 1).priceClose, priceMax), symbol);
                            rateUp15M2Symbols.put(-Utils.rateOf2Double(values.get(values.size() - 1).priceClose, priceMin), symbol);
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                    Double rateDownAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown2Symbols, 50);
                    Double rateUpAvg = -MarketBigChangeDetector.calRateChangeAvg(rateUp2Symbols, 50);
                    Double rateDown15MAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown15M2Symbols, 50);
                    Double rateUp15MAvg = -MarketBigChangeDetector.calRateChangeAvg(rateUp15M2Symbols, 50);
                    MarketLevelChange levelChange = MarketBigChangeDetector.getMarketStatus1M(rateDownAvg, rateUpAvg, btcRateChange);
                    LOG.info("Check level market: {} DownAvg: {}% UpAvg:{}% DownAvg15M:{}%  UpAvg15M:{}% btcRate: {}% {}",
                            Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                            Utils.formatDouble(rateDownAvg * 100, 2), Utils.formatDouble(rateUpAvg * 100, 2),
                            Utils.formatDouble(rateDown15MAvg * 100, 2), Utils.formatDouble(rateUp15MAvg * 100, 2),
                            Utils.formatDouble(btcRateChange * 100, 2), levelChange);
                    LOG.info("Market level change: {} level: {} symbols:{}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                            levelChange, symbol2FinalTicker.size());
                    if (levelChange != null) {
                        Set<String> symbolsRunning = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING);
                        List<String> symbol2Trade = MarketBigChangeDetector.getTopSymbol(rateDown15M2Symbols,
                                Configs.NUMBER_ENTRY_EACH_SIGNAL, symbolsRunning);
                        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                                || levelChange.equals(MarketLevelChange.SMALL_UP)) {
                            while (symbol2Trade.size() > Configs.NUMBER_ENTRY_EACH_SIGNAL / 2) {
                                symbol2Trade.remove(symbol2Trade.size() - 1);
                            }
                        }
                        LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), levelChange, symbol2Trade);
                        for (String symbol : symbol2Trade) {
                            try {
                                KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                                createOrderBuyRequest(symbol, ticker, levelChange);
                            } catch (Exception e) {
                                e.printStackTrace();
                            }
                        }
                    } else {
                        if (BudgetManager.getInstance().totalOrderRunning == 0
                                || (BudgetManager.getInstance().rateLossAvg >= 0.005 && BudgetManager.getInstance().totalOrder15MRunning < 2)) {

                            levelChange = MarketBigChangeDetector.getMarketStatus15M(rateDown15MAvg, rateUp15MAvg, rateUpAvg);
                            if (levelChange != null) {
                                Set<String> symbolsRunning = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING);
                                List<String> symbol2Trade = MarketBigChangeDetector.getTopSymbol(rateDown15M2Symbols,
                                        Configs.NUMBER_ENTRY_EACH_SIGNAL, symbolsRunning);
                                while (symbol2Trade.size() > Configs.NUMBER_ENTRY_EACH_SIGNAL / 2) {
                                    symbol2Trade.remove(symbol2Trade.size() - 1);
                                }
                                LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), levelChange, symbol2Trade);
                                for (String symbol : symbol2Trade) {
                                    try {
                                        KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                                        createOrderBuyRequest(symbol, ticker, levelChange);
                                    } catch (Exception e) {
                                        e.printStackTrace();
                                    }
                                }
                            }
                        }

                        btcTickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BTC);
                        Set<String> symbolsRunning = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING);
                        if (MarketBigChangeDetector.isBtcReverse(btcTickers)) {
                            List<String> symbol2Trade = MarketBigChangeDetectorTest.getTopSymbolSimple(rateDown15M2Symbols,
                                    Configs.NUMBER_ENTRY_EACH_SIGNAL, symbolsRunning);
                            levelChange = MarketLevelChange.BTC_REVERSE;
                            while (symbol2Trade.size() > Configs.NUMBER_ENTRY_EACH_SIGNAL / 2) {
                                symbol2Trade.remove(symbol2Trade.size() - 1);
                            }
                            // check create order new
                            for (String symbol : symbol2Trade) {
                                KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                                createOrderBuyRequest(symbol, ticker, levelChange);
                            }
                        }
                    }
                    executorService.execute(() -> orderManager.processManagerPosition(symbol2FinalTicker));
                } catch (Exception e) {
                    e.printStackTrace();
                }
                // exit while true
                break;
            }
            try {
                Thread.sleep(Utils.TIME_SECOND / 10);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        LOG.info("Finish check level change of market 2 trade: {}", new Date());
    }

    private void createOrderBuyRequest(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange) {
        LOG.info("Market level:{} {} {}", levelChange, symbol, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
        Double budget = BudgetManager.getInstance().getBudget();
        if (levelChange.equals(MarketLevelChange.BIG_DOWN)
                || levelChange.equals(MarketLevelChange.BIG_UP)) {
            budget = budget * 2;
        }
        Double priceEntry = ticker.priceClose;
        Double quantity = Utils.calQuantity(budget, BudgetManager.getInstance().getLeverage(), priceEntry, symbol);
        if (quantity != null && quantity != 0) {
            OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
                    null, quantity, BudgetManager.getInstance().getLeverage(), symbol, ticker.startTime.longValue(),
                    ticker.startTime.longValue(), OrderSide.BUY, Constants.TRADING_TYPE_VOLUME_MINI);
            orderTrade.marketLevel = levelChange;
            RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
        } else {
            LOG.info("{} {} quantity false", symbol, quantity);
        }
    }

    private void createOrderSELLRequest(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange) {
        LOG.info("Market level:{} {} {}", levelChange, symbol, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
        Double rateTarget = Configs.RATE_TARGET;
        Double budget = BudgetManager.getInstance().getBudget();
        budget = budget * 2;
        Double priceEntry = ticker.priceClose;
        Double priceTarget = Utils.calPriceTarget(symbol, priceEntry, OrderSide.SELL, rateTarget);
        Double quantity = Utils.calQuantity(budget, BudgetManager.getInstance().getLeverage(), priceEntry, symbol);
        if (quantity != null && quantity != 0) {
            OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
                    priceTarget, quantity, BudgetManager.getInstance().getLeverage(), symbol, ticker.startTime.longValue(),
                    ticker.startTime.longValue(), OrderSide.SELL, Constants.TRADING_TYPE_VOLUME_MINI);
            orderTrade.marketLevel = levelChange;
            RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
        } else {
            LOG.info("{} {} quantity false", symbol, quantity);
        }
    }


    public boolean isTimeGetData() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 0
//                && miniSecond > 400
                && miniSecond < 100;
    }

    public boolean isTimeTrader() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 0 && miniSecond < 100;
    }

    private void initData() {
        allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        symbol2Tickers.clear();
    }

    private void getTickerBySymbol(String symbol, Long time) {
        try {
            List<KlineObjectNumber> tickers = TickerFuturesHelper.getTickerWithStartTime(symbol, Constants.INTERVAL_1M, time);
            if (!tickers.isEmpty()) {
                if (tickers.get(tickers.size() - 1).endTime.longValue() > System.currentTimeMillis()){
                    tickers.remove(tickers.size() - 1);
                }
                symbol2Tickers.put(symbol, tickers);
//                LOG.info("Get ticker of {} {} success", symbol, Utils.normalizeDateYYYYMMDDHHmm(time));
            }
        } catch (Exception e) {
            LOG.info("Error get ticker of:{}", symbol);
            e.printStackTrace();
        }
    }


}
