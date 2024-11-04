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

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
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
        String symbol = "BTCUSDT";
//        new DetectEntrySignal2Trader().testCreateOrder("BNBUSDT");
        List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1M);
        new DetectEntrySignal2Trader().createOrderBuyRequest(symbol, tickers.get(tickers.size() - 1),
                MarketLevelChange.BTC_TREND_REVERSE);
//        System.out.println(getOrderMarketLevelRunning());
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
                        executorService.execute(() -> orderManager.processManagerPosition());
                        LOG.info("Start get data of market! {}", new Date());
                        Long startTime = Utils.getMinute(System.currentTimeMillis() - 300 * Utils.TIME_MINUTE);
//                                (Configs.NUMBER_TICKER_CAL_RATE_CHANGE + 5) * Utils.TIME_MINUTE);
                        for (String symbol : allSymbol) {
                            if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
                                continue;
                            }
                            executorService.execute(() -> getTickerBySymbol(symbol, startTime));
                        }
                        executorService.execute(() -> getTickerBySymbol(Constants.SYMBOL_PAIR_BTC, startTime));
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
                    Double btcMax15M = null;

                    for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Tickers.entrySet()) {
                        try {
                            String symbol = entry.getKey();
                            if (Constants.diedSymbol.contains(symbol)) {
                                continue;
                            }
                            List<KlineObjectNumber> tickers = entry.getValue();
                            KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
                            if (!Utils.isTickerAvailable(ticker)) {
                                continue;
                            }
                            symbol2FinalTicker.put(symbol, ticker);
                            Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                            rateDown2Symbols.put(rateChange, symbol);
                            rateUp2Symbols.put(-rateChange, symbol);
                            Double priceMax = null;
                            Double minPrice = null;
                            for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                                int index = tickers.size() - i - 1;
                                if (index >= 0) {
                                    KlineObjectNumber kline = tickers.get(index);
                                    if (priceMax == null || priceMax < kline.maxPrice) {
                                        priceMax = kline.maxPrice;
                                    }
                                    if (minPrice == null || minPrice > kline.minPrice) {
                                        minPrice = kline.minPrice;
                                    }
                                }
                            }
                            if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
                                btcMax15M = priceMax;
                            }
                            if (Constants.specialSymbol.contains(symbol)) {
                                continue;
                            }
                            rateDown15M2Symbols.put(Utils.rateOf2Double(tickers.get(tickers.size() - 1).priceClose, priceMax), symbol);
                            rateUp15M2Symbols.put(-Utils.rateOf2Double(tickers.get(tickers.size() - 1).priceClose, minPrice), symbol);

                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                    Double rateDownAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown2Symbols, 50);
                    Double rateUpAvg = -MarketBigChangeDetector.calRateChangeAvg(rateUp2Symbols, 50);
                    Double rateDown15MAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown15M2Symbols, 50);
                    Double rateUp15MAvg = -MarketBigChangeDetector.calRateChangeAvg(rateUp15M2Symbols, 50);
                    Double rateBtcDown15M = Utils.rateOf2Double(btcTicker.priceClose, btcMax15M);
                    MarketLevelChange levelChange = MarketBigChangeDetector.getMarketStatus1M(rateDownAvg, rateUpAvg, btcRateChange
                            , rateDown15MAvg, rateUp15MAvg, rateBtcDown15M);
                    LOG.info("Check level market: {} DownAvg: {}% UpAvg:{}% DownAvg15M:{}%  UpAvg15M:{}% btcRate: {}% btcRate15M: {}% {}",
                            Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                            Utils.formatDouble(rateDownAvg * 100, 3), Utils.formatDouble(rateUpAvg * 100, 3),
                            Utils.formatDouble(rateDown15MAvg * 100, 3), Utils.formatDouble(rateUp15MAvg * 100, 3),
                            Utils.formatDouble(btcRateChange * 100, 3), Utils.formatDouble(rateBtcDown15M * 100, 3)
                            , levelChange);
                    LOG.info("Market level change: {} level: {} symbols:{}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                            levelChange, symbol2FinalTicker.size());
                    Set<String> symbolLocked = new HashSet<>();
                    symbolLocked.addAll(BudgetManager.getInstance().symbolLocked);
                    if (levelChange != null) {
                        List<String> symbol2BUY = MarketBigChangeDetector.getTopSymbol(rateDown15M2Symbols,
                                Configs.NUMBER_ENTRY_EACH_SIGNAL, symbol2FinalTicker, symbolLocked);
                        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                                || levelChange.equals(MarketLevelChange.SMALL_UP)
                                || levelChange.equals(MarketLevelChange.TINY_DOWN)
                                || levelChange.equals(MarketLevelChange.TINY_UP)
                        ) {
                            while (symbol2BUY.size() > Configs.NUMBER_ENTRY_EACH_SIGNAL / 2) {
                                symbol2BUY.remove(symbol2BUY.size() - 1);
                            }
                        }
                        symbol2BUY = addSpecialSymbol(symbol2BUY, levelChange, symbol2FinalTicker);

                        LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()), levelChange, symbol2BUY);
                        for (String symbol : symbol2BUY) {
                            try {
                                KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                                createOrderBuyRequest(symbol, ticker, levelChange);
                            } catch (Exception e) {
                                e.printStackTrace();
                            }
                        }
                    } else {
                        // big change 15m
                        levelChange = MarketBigChangeDetector.getMarketStatus15M(rateDown15MAvg, rateUp15MAvg, rateBtcDown15M);
                        if (levelChange != null) {
                            symbolLocked.addAll(BudgetManager.getInstance().symbolLoss);
                            List<String> symbol2BUY = MarketBigChangeDetector.getTopSymbol(rateDown15M2Symbols,
                                    Configs.NUMBER_ENTRY_EACH_SIGNAL / 2, symbol2FinalTicker, symbolLocked);
                            LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()), levelChange, symbol2BUY);
                            for (String symbol : symbol2BUY) {
                                try {
                                    KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                                    createOrderBuyRequest(symbol, ticker, levelChange);
                                } catch (Exception e) {
                                    e.printStackTrace();
                                }
                            }
                        }

                        // btc reverse
                        btcTickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BTC);
                        if (MarketBigChangeDetector.isBtcReverse(btcTickers, rateDown15MAvg)
                                && rateDown15MAvg <= -0.018
                                && rateBtcDown15M <= -0.007
                        ) {
                            List<String> symbol2BUY = MarketBigChangeDetector.getTopSymbol(rateDown15M2Symbols,
                                    Configs.NUMBER_ENTRY_EACH_SIGNAL, symbol2FinalTicker, symbolLocked);
                            symbol2BUY.add(Constants.SYMBOL_PAIR_BTC);
                            levelChange = MarketLevelChange.BTC_REVERSE;
                            // check create order new
                            for (String symbol : symbol2BUY) {
                                KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                                createOrderBuyRequest(symbol, ticker, levelChange);
                            }
                        }
                        // btc trend reverse
                        if (MarketBigChangeDetector.isBtcTrendReverse(btcTickers)) {
                            levelChange = MarketLevelChange.BTC_TREND_REVERSE;
                            List<String> symbol2BUY = new ArrayList<>();
                            symbol2BUY.add(Constants.SYMBOL_PAIR_BTC);
                            symbol2BUY.add(Constants.SYMBOL_PAIR_BNB);
                            symbol2BUY.add(Constants.SYMBOL_PAIR_XRP);
                            for (String symbol : symbol2BUY) {
                                KlineObjectNumber ticker = symbol2FinalTicker.get(symbol);
                                createOrderBuyRequest(symbol, ticker, levelChange);
                            }
                        }
                    }

                    Long time = btcTicker.startTime.longValue();
                    Storage.writeObject2File("storage/data/rateMax15M/" + Utils.normalizeDateYYYYMMDD(time)
                            + "/" + time, rateDown15M2Symbols);
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

    private List<String> addSpecialSymbol(List<String> symbol2BUY, MarketLevelChange levelChange,
                                          Map<String, KlineObjectNumber> symbol2Ticker) {
        if (levelChange != null && levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            KlineObjectNumber tickerBtc = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
            if (tickerBtc != null && Utils.rateOf2Double(tickerBtc.priceClose, tickerBtc.priceOpen) < -0.03) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_BTC);
            }
            KlineObjectNumber tickerSol = symbol2Ticker.get(Constants.SYMBOL_PAIR_SOL);
            if (tickerSol != null && Utils.rateOf2Double(tickerSol.priceClose, tickerSol.priceOpen) < -0.02) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_SOL);
            }
            KlineObjectNumber tickerBNB = symbol2Ticker.get(Constants.SYMBOL_PAIR_BNB);
            if (tickerBNB != null && Utils.rateOf2Double(tickerBNB.priceClose, tickerBNB.priceOpen) < -0.015) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_BNB);
            }
            KlineObjectNumber tickerXRP = symbol2Ticker.get(Constants.SYMBOL_PAIR_XRP);
            if (tickerXRP != null && Utils.rateOf2Double(tickerXRP.priceClose, tickerXRP.priceOpen) < -0.03) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_XRP);
            }
        }
        if (levelChange != null && levelChange.equals(MarketLevelChange.MEDIUM_DOWN)) {
            KlineObjectNumber tickerBNB = symbol2Ticker.get(Constants.SYMBOL_PAIR_BNB);
            if (tickerBNB != null && Utils.rateOf2Double(tickerBNB.priceClose, tickerBNB.priceOpen) < -0.024) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_BNB);
            }
            KlineObjectNumber tickerXRP = symbol2Ticker.get(Constants.SYMBOL_PAIR_XRP);
            if (tickerXRP != null && Utils.rateOf2Double(tickerXRP.priceClose, tickerXRP.priceOpen) < -0.03) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_XRP);
            }
        }
        if (levelChange != null
                && (levelChange.equals(MarketLevelChange.BIG_UP)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP)
        )) {
            symbol2BUY.add(Constants.SYMBOL_PAIR_BTC);
            symbol2BUY.add(Constants.SYMBOL_PAIR_BNB);
            symbol2BUY.add(Constants.SYMBOL_PAIR_XRP);
        }
        return symbol2BUY;
    }

    public void createOrderBuyRequest(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange) {
        LOG.info("Market level:{} {} {}", levelChange, symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
        Double budget = BudgetManager.getInstance().getBudget();
        Double marginRunning = 0d;
        try {
            marginRunning = BudgetManager.getInstance().getPositionInitialMargin();
        } catch (Exception e) {
            e.printStackTrace();
        }
        if (levelChange.equals(MarketLevelChange.BIG_UP)) {
            budget = budget * 2;
        }
        if (marginRunning <= 20 * BudgetManagerSimple.getInstance().getBudget()
                && (levelChange.equals(MarketLevelChange.BIG_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP))
        ) {
            budget = budget * 2;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                || levelChange.equals(MarketLevelChange.SMALL_UP)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                || levelChange.equals(MarketLevelChange.TINY_DOWN)
        ) {
            budget = budget;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP_15M)
                || levelChange.equals(MarketLevelChange.TINY_UP)
                || levelChange.equals(MarketLevelChange.TINY_DOWN_15M)
                || levelChange.equals(MarketLevelChange.BTC_REVERSE)
        ) {
            budget = budget / 2;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_UP_15M)
                || levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
        ) {
            budget = budget / 6;
        }
        if (marginRunning > 15 * BudgetManagerSimple.getInstance().getBudget()
                && (levelChange.equals(MarketLevelChange.MEDIUM_UP_15M)
                || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                || levelChange.equals(MarketLevelChange.SMALL_UP_15M)
                || levelChange.equals(MarketLevelChange.TINY_DOWN_15M))
        ) {
            budget = budget / 2;
        }
        if (marginRunning > 35 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 2;
        }
        if (marginRunning > 45 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 3;
        }
        if (marginRunning > 55 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 4;
        }
        Double priceEntry = ticker.priceClose;
        Double quantity = Utils.calQuantity(budget, BudgetManager.getInstance().getLeverage(symbol), priceEntry, symbol);
        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
            if (quantity < 0.002) {
                quantity = 0.002;
            }
        }
        if (quantity != null && quantity != 0) {
            OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
                    null, quantity, BudgetManager.getInstance().getLeverage(symbol), symbol, ticker.startTime.longValue(),
                    ticker.startTime.longValue(), OrderSide.BUY, Constants.TRADING_TYPE_VOLUME_MINI);
            orderTrade.marketLevel = levelChange;
            LOG.info("Push redis order: {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                    symbol, levelChange, budget.longValue(), ticker.priceClose);
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
        Double quantity = Utils.calQuantity(budget, BudgetManager.getInstance().getLeverage(symbol), priceEntry, symbol);
        if (quantity != null && quantity != 0) {
            OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
                    priceTarget, quantity, BudgetManager.getInstance().getLeverage(symbol), symbol, ticker.startTime.longValue(),
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
                if (tickers.get(tickers.size() - 1).endTime.longValue() > System.currentTimeMillis()) {
//                    KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
//                    KlineObjectNumber lastTicker = tickers.get(tickers.size() - 2);
//                    LOG.info("Remove {} {} {} {} {} {} {} {}", symbol,ticker.priceOpen,
//                            Utils.normalizeDateYYYYMMDDHHmmss(ticker.startTime.longValue()),
//                            Utils.normalizeDateYYYYMMDDHHmmss(ticker.endTime.longValue()),
//                            Utils.normalizeDateYYYYMMDDHHmmss(System.currentTimeMillis()),
//                            Utils.normalizeDateYYYYMMDDHHmmss(lastTicker.startTime.longValue()),
//                            lastTicker.priceOpen,
//                            Utils.normalizeDateYYYYMMDDHHmmss(time));
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
