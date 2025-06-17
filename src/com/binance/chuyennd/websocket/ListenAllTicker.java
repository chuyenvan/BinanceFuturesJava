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

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.chuyennd.trading.DetectEntrySignal2TradeNormal;
import com.binance.chuyennd.trading.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.CandlestickInterval;
import com.binance.client.model.event.CandlestickEvent;
import com.binance.client.model.event.SymbolTickerEvent;
import com.binance.client.model.user.OrderUpdate;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;

/**
 * @author pc
 */
public class ListenAllTicker {

    public static final Logger LOG = LoggerFactory.getLogger(ListenAllTicker.class);
    public final ConcurrentHashMap<String, TreeMap<Long, KlineObjectNumber>> symbol2Tickers = new ConcurrentHashMap<>();
    public final ConcurrentHashMap<String, Double> symbol2Price = new ConcurrentHashMap<>();
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    public SubscriptionClient client;
    private static volatile ListenAllTicker INSTANCE = null;

    public static ListenAllTicker getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new ListenAllTicker();
            INSTANCE.initData();
            INSTANCE.client = SubscriptionClient.create();
            INSTANCE.startThreadUpdateTicker();
//            INSTANCE.startUserDataStream();
        }
        return INSTANCE;
    }

    private void initData() {
        try {
            LOG.info("Start get data of market for init {}", new Date());
            Long startTime = Utils.getMinute(System.currentTimeMillis() -
                    (Configs.NUMBER_TICKER_CAL_RATE_CHANGE * 16 + 5) * Utils.TIME_MINUTE);
            Set<String> allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
            allSymbol.removeAll(Constants.diedSymbol);
            allSymbol.remove(Constants.SYMBOL_PAIR_BTC);
            executorService.execute(() -> initTickerBySymbol(Constants.SYMBOL_PAIR_BTC,
                    startTime - (Configs.BTC_TREND_REVERSE_DURATION
                            - Configs.NUMBER_TICKER_CAL_RATE_CHANGE * 16) * Utils.TIME_MINUTE));
            for (String symbol : allSymbol) {
                executorService.execute(() -> initTickerBySymbol(symbol, startTime));
            }
        } catch (Exception e) {
            LOG.error("ERROR during ThreadDetectMarketLevel2Trader: {}", e);
            e.printStackTrace();
        }
    }

    private void initTickerBySymbol(String symbol, Long startTime) {
        try {
            List<KlineObjectNumber> candles = TickerFuturesHelper.getTickerWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
            TreeMap<Long, KlineObjectNumber> time2Candle = new TreeMap<>();
            for (KlineObjectNumber candle : candles) {
                time2Candle.put(candle.startTime.longValue(), candle);
            }
            symbol2Tickers.put(symbol, time2Candle);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void main(String[] args) {
        ListenAllTicker.getInstance().startThreadMonitor();
    }

    public void startThreadUpdateTicker() {
        // update price
        client.subscribeAllTickerEvent(((events) -> {
            for (SymbolTickerEvent event : events) {
                symbol2Price.put(event.getSymbol(), event.getLastPrice().doubleValue());
                updateDate(event);
            }
        }), null);
        // update ticker
        List<String> symbols = new ArrayList<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS)) {
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            symbols.add(symbol.toLowerCase());
        }

        List<List<String>> sublist = Utils.subList(symbols, 150);
        for (List<String> list : sublist) {
            client.subscribeAllCandlestickEvent(list, CandlestickInterval.ONE_MINUTE, ((event) -> {
//                LOG.info("Update ticker: {}", Utils.gson.toJson(event));
                updateDate(event);
            }), null);
        }
    }

    public void startThreadListenASymbol(List<String> symbols) {
        LOG.info("Listen: {} new to all symbol", symbols);
        client.subscribeAllCandlestickEvent(symbols, CandlestickInterval.ONE_MINUTE, ((event) -> {
            updateDate(event);
        }), null);

    }

    private void startUserDataStream() {
        new Thread(() -> {
            String listenKey = ClientSingleton.getInstance().syncRequestClient.startUserDataStream();
            LOG.info("listenKey: {}", listenKey);

            // Keep user data stream
            ClientSingleton.getInstance().syncRequestClient.keepUserDataStream(listenKey);

            client.subscribeUserDataEvent(listenKey, ((event) -> {
                try {
                    if (event != null) {
                        LOG.info("UserStream: {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(event.getEventTime()),
                                event.getEventType(), Utils.toJson(event.getOrderUpdate()), Utils.toJson(event.getAccountUpdate()));
                        if (StringUtils.equals(event.getEventType(), "ORDER_TRADE_UPDATE")) {
                            OrderUpdate orderUpdate = event.getOrderUpdate();
                            if (orderUpdate != null
                                    && StringUtils.equals(orderUpdate.getOrderStatus(), "FILLED")
                                    && orderUpdate.getRealizedProfit().doubleValue() > 0) {
                                LOG.info("Remove symbol trade success from stream: {}", orderUpdate.getSymbol());
                                BudgetManager.getInstance().symbol2Pos.remove(orderUpdate.getSymbol());
                                BudgetManager.getInstance().symbol2Level.remove(orderUpdate.getSymbol());
                                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, orderUpdate.getSymbol());
                            }
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }), null);
        }).start();
    }

    public void startThreadMonitor() {
        new Thread(() -> {
            Thread.currentThread().setName("startThreadMonitor");
            LOG.info("Start thread startThreadMonitor");
            while (true) {
                if (isTimeGetData()) {
                    try {
                        ConcurrentHashMap<String, List<KlineObjectNumber>> symbol2Tickers = getInstance().getAllTicker();
                        Map<String, KlineObjectNumber> symbol2FinalTicker = new HashMap<>();
                        TreeMap<Double, String> rateDown15M2Symbols = new TreeMap<>();
                        TreeMap<Double, String> rateUp15M2Symbols = new TreeMap<>();
                        TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
                        TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
                        Map<String, Double> symbol2Max15m = new HashMap<>();

                        List<KlineObjectNumber> btcTickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BTC);
                        KlineObjectNumber btcTicker = btcTickers.get(btcTickers.size() - 1);
                        Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
                        Double btcMax15M = null;
                        long time = btcTicker.startTime.longValue();
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
                                // pass symbol big dump(delist/waring/monitor...)
                                if (btcRateChange > -0.002 && rateChange < -0.15) {
                                    continue;
                                }
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
                                rateDown15M2Symbols.put(Utils.rateOf2Double(tickers.get(tickers.size() - 1).priceClose, priceMax), symbol);
                                symbol2Max15m.put(symbol, priceMax);
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
                                , rateDown15MAvg);
                        LOG.info("Check level market: {} DownAvg: {}% UpAvg:{}% DownAvg15M:{}%  UpAvg15M:{}% btcRate: {}% btcRate15M: {}% {}",
                                Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                                Utils.formatDouble(rateDownAvg * 100, 3), Utils.formatDouble(rateUpAvg * 100, 3),
                                Utils.formatDouble(rateDown15MAvg * 100, 3), Utils.formatDouble(rateUp15MAvg * 100, 3),
                                Utils.formatDouble(btcRateChange * 100, 3), Utils.formatDouble(rateBtcDown15M * 100, 3)
                                , levelChange);
                        LOG.info("Market level change: {} level: {} symbols:{}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                                levelChange, symbol2FinalTicker.size());
//                        TreeMap<Long, KlineObjectNumber> tickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BTC);
//                        LOG.info("Total symbols: {}", symbol2Tickers.size());
//                        if (tickers != null) {
//                            for (KlineObjectNumber ticker : tickers.values()) {
//                                LOG.info("{} {} {} {} {} {}", Constants.SYMBOL_PAIR_BTC, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
//                                        ticker.priceOpen, ticker.maxPrice, ticker.minPrice, ticker.priceClose);
//                            }
//                        }
//                        tickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BNB);
//                        if (tickers != null) {
//                            for (CandlestickEvent ticker : tickers.values()) {
//                                LOG.info("{} {} {} {} {} {}", ticker.getSymbol(), Utils.normalizeDateYYYYMMDDHHmm(ticker.getStartTime()),
//                                        ticker.getOpen(), ticker.getHigh(), ticker.getLow(), ticker.getClose());
//                            }
//                        }
//                        tickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_ETH);
//                        if (tickers != null) {
//                            for (CandlestickEvent ticker : tickers.values()) {
//                                LOG.info("{} {} {} {} {} {}", ticker.getSymbol(), Utils.normalizeDateYYYYMMDDHHmm(ticker.getStartTime()),
//                                        ticker.getOpen(), ticker.getHigh(), ticker.getLow(), ticker.getClose());
//                            }
//                        }
//                        tickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_XRP);
//                        if (tickers != null) {
//                            for (CandlestickEvent ticker : tickers.values()) {
//                                LOG.info("{} {} {} {} {} {}", ticker.getSymbol(), Utils.normalizeDateYYYYMMDDHHmm(ticker.getStartTime()),
//                                        ticker.getOpen(), ticker.getHigh(), ticker.getLow(), ticker.getClose());
//                            }
//                        }
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

    public ConcurrentHashMap<String, List<KlineObjectNumber>> getAllTicker() {
        ConcurrentHashMap<String, List<KlineObjectNumber>> result = new ConcurrentHashMap<>();
        LOG.info("Btc ticker size: {}", symbol2Tickers.get(Constants.SYMBOL_PAIR_BTC).size());
        int counterError = 0;
        for (String symbol : symbol2Tickers.keySet()) {
            try {
                TreeMap<Long, KlineObjectNumber> tickers = symbol2Tickers.get(symbol);
                int numberMax = Configs.NUMBER_TICKER_CAL_RATE_CHANGE * 16 + 5;
                if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
                    numberMax = Configs.BTC_TREND_REVERSE_DURATION + 5;
                }
                List<KlineObjectNumber> list = new ArrayList<>();
                while (tickers.size() > numberMax) {
//                LOG.info("Remove: {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(tickers.firstKey()), tickers.size());
                    tickers.remove(tickers.firstKey());
                }
                list.addAll(tickers.values());
                if (list.size() < 1) {
                    LOG.info("Error process get ticker of: {}", symbol);
                    continue;
                }
                if (list.get(list.size() - 1).startTime == Utils.getMinute(System.currentTimeMillis())) {
//                    LOG.info("Remove last ticker: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(list.get(list.size() - 1).startTime.longValue()));
                    list.remove(list.size() - 1);
                    counterError++;
                }
                if (list.get(list.size() - 1).startTime < Utils.getMinute(System.currentTimeMillis()) - Utils.TIME_MINUTE) {
//                    LOG.info("Error last ticker: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(list.get(list.size() - 1).startTime.longValue()));
                    counterError++;
                    continue;
                }
                result.put(symbol, list);
            } catch (Exception e) {
                LOG.info("Error process get ticker of: {}", symbol);
                e.printStackTrace();
            }
        }
        if (counterError > 0) {
            LOG.info("Symbol ticker error: {}", counterError);
        }
        return result;
    }

    public boolean isTimeGetData() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 0 && miniSecond < 100;
    }

    private void updateDate(CandlestickEvent event) {
        TreeMap<Long, KlineObjectNumber> tickers = symbol2Tickers.get(event.getSymbol());
        if (tickers == null) {
            tickers = new TreeMap<>();
        }
        tickers.put(event.getStartTime(), convertEvent2Kline(event));
        symbol2Tickers.put(event.getSymbol(), tickers);
        symbol2Price.put(event.getSymbol(), event.getClose().doubleValue());
//        if (Constants.specialSymbol.contains(event.getSymbol())) {
//            LOG.info("{} {}", event.getSymbol(), symbol2Price.get(event.getSymbol()));
//        }
    }

    private void updateDate(SymbolTickerEvent event) {
        if (!StringUtils.endsWithIgnoreCase(event.getSymbol(), "usdt")) {
            return;
        }
        if (Constants.diedSymbol.contains(event.getSymbol())) {
            return;
        }
        TreeMap<Long, KlineObjectNumber> tickers = symbol2Tickers.get(event.getSymbol());
        if (tickers == null) {
            tickers = new TreeMap<>();
        }
        Long time = Utils.getMinute(event.getEventTime());
        KlineObjectNumber kline = tickers.get(time);
        Double lastPrice = event.getLastPrice().doubleValue();
        if (kline == null) {
            kline = new KlineObjectNumber();
            kline.startTime = time.doubleValue();
            kline.endTime = time.doubleValue() + Utils.TIME_MINUTE - 1;
            kline.priceOpen = lastPrice;
            kline.maxPrice = lastPrice;
            kline.minPrice = lastPrice;
            kline.priceClose = lastPrice;
            kline.totalUsdt = 0.0;
        } else {
            kline.priceClose = lastPrice;
            kline.maxPrice = Math.max(kline.maxPrice, lastPrice);
            kline.minPrice = Math.min(kline.minPrice, lastPrice);
        }
        tickers.put(time, kline);
        symbol2Tickers.put(event.getSymbol(), tickers);
    }

    private static KlineObjectNumber convertEvent2Kline(CandlestickEvent event) {
        KlineObjectNumber result = new KlineObjectNumber();
        result.startTime = event.getStartTime().doubleValue();
        result.priceOpen = event.getOpen().doubleValue();
        result.maxPrice = event.getHigh().doubleValue();
        result.minPrice = event.getLow().doubleValue();
        result.priceClose = event.getClose().doubleValue();
        result.endTime = event.getCloseTime().doubleValue();
        result.totalUsdt = event.getVolume().doubleValue();
        return result;
    }


}
