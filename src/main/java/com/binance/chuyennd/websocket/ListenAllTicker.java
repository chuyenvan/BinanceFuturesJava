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

import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
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

import java.io.File;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * @author pc
 */
public class ListenAllTicker {

    public static final Logger LOG = LoggerFactory.getLogger(ListenAllTicker.class);
    public ConcurrentHashMap<String, TreeMap<Long, KlineObjectSimple>> symbol2Tickers = new ConcurrentHashMap<>();
    public final ConcurrentHashMap<String, Double> symbol2Price = new ConcurrentHashMap<>();
    public static final String FILE_TICKER_1M_STORAGE = "storage/tickers/symbol2ticker1Ms";
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    public SubscriptionClient client;
    private static volatile ListenAllTicker INSTANCE = null;

    public static ListenAllTicker getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new ListenAllTicker();
            if (new File(FILE_TICKER_1M_STORAGE).exists()) {
                try {
                    INSTANCE.symbol2Tickers = (ConcurrentHashMap<String, TreeMap<Long, KlineObjectSimple>>)
                            StorageSnappy.readObjectFromFile(FILE_TICKER_1M_STORAGE);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            if (INSTANCE.symbol2Tickers == null) {
                INSTANCE.initData();
            }
            INSTANCE.client = SubscriptionClient.create();
            INSTANCE.startThreadUpdateTicker();
            INSTANCE.startThreadWriteTickerData();
//            INSTANCE.startUserDataStream();
        }
        return INSTANCE;
    }

    private void initData() {
        try {
            LOG.info("Start get data of market for init {}", new Date());
            Long startTime = Utils.getMinute(System.currentTimeMillis() -
                    (Configs.NUMBER_TICKER_CAL_RATE_CHANGE * 4 + 5) * Utils.TIME_MINUTE);
            Set<String> allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
            allSymbol.removeAll(Constants.diedSymbol);
            allSymbol.remove(Constants.SYMBOL_PAIR_BTC);
            executorService.execute(() -> initTickerBySymbol(Constants.SYMBOL_PAIR_BTC,
                    startTime - Configs.BTC_TREND_REVERSE_DURATION
                            * Utils.TIME_MINUTE));
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
            List<KlineObjectSimple> candles = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
            TreeMap<Long, KlineObjectSimple> time2Candle = new TreeMap<>();
            for (KlineObjectSimple candle : candles) {
                time2Candle.put(candle.startTime.longValue(), candle);
            }
            symbol2Tickers.put(symbol, time2Candle);
            if (symbol.equals(Constants.SYMBOL_PAIR_ETH)) {
                LOG.info("Init ticker {} {} {}", symbol, time2Candle.size(), Utils.normalizeDateYYYYMMDDHHmm(time2Candle.firstKey()));
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void main(String[] args) {

//        ListenAllTicker.getInstance().startThreadMonitor();
        String symbol = "BTCUSDT";
        List<KlineObjectSimple> tickers = ListenAllTicker.getInstance().getTickerBySymbol(symbol);
        if (tickers != null) {
            int index = tickers.size() - 1;
            for (int i = 0; i < 15; i++) {
                if (index - i < 0) {
                    break;
                }
                KlineObjectSimple tickerCheck = tickers.get(index - i);
                if (Utils.rateOf2Double(tickerCheck.maxPrice, tickerCheck.minPrice) > 0.001) {
                    LOG.info("{} True", symbol);
                    return;
                }
            }
        }
        LOG.info("{} False", symbol);
        return;
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

        List<List<String>> sublist = Utils.subList(symbols, 170);
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

    public void startThreadWriteTickerData() {
        new Thread(() -> {
            Thread.currentThread().setName("startThreadWriteTickerData");
            LOG.info("Start thread startThreadWriteTickerData");
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_SECOND * 5);
                    if (Utils.getCurrentSecond() > 15 && Utils.getCurrentSecond() < 20) {
                        writeTickerData2File();
                    }

                } catch (Exception ex) {
                    LOG.info("Write ticker to file error: {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
                    ex.printStackTrace();
                }
            }
        }).start();
    }

    private void writeTickerData2File() {
        // 1. Tạo một bản sao của dữ liệu cần ghi
        ConcurrentHashMap<String, TreeMap<Long, KlineObjectSimple>> tickersToSave = new ConcurrentHashMap<>();
        // 2. Sử dụng synchronized để đảm bảo tạo bản sao một cách an toàn
        //    Khối lệnh này chỉ chạy trong vài mili giây, rất nhanh.
        synchronized (symbol2Tickers) {
            // Tạo một ConcurrentHashMap mới
            tickersToSave.putAll(symbol2Tickers);
        }
        // 3. Ghi "bản sao" này ra file.
        //    Trong lúc này, `symbol2LastTickers` gốc vẫn có thể được cập nhật thoải mái.
        StorageSnappy.writeObject2File(FILE_TICKER_1M_STORAGE, tickersToSave);
    }

    public ConcurrentHashMap<String, List<KlineObjectSimple>> getAllTicker() {
        ConcurrentHashMap<String, List<KlineObjectSimple>> result = new ConcurrentHashMap<>();
        int counterError = 0;
        for (String symbol : symbol2Tickers.keySet()) {
            try {
                TreeMap<Long, KlineObjectSimple> tickers = symbol2Tickers.get(symbol);
//                int numberMax = Configs.BTC_TREND_REVERSE_DURATION + 5;
                List<KlineObjectSimple> list = new ArrayList<>();
//                while (tickers.size() > numberMax) {
////                LOG.info("Remove: {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(tickers.firstKey()), tickers.size());
//                    tickers.remove(tickers.firstKey());
//                }

                synchronized (tickers) {
                    list.addAll(tickers.values());
                }

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
            if (counterError > 100) {
                Utils.reset("Reset by ticker error over 100 " + counterError);
            }
        }
        return result;
    }

    public List<KlineObjectSimple> getTickerBySymbol(String symbol) {
        TreeMap<Long, KlineObjectSimple> tickers = symbol2Tickers.get(symbol);
        List<KlineObjectSimple> result = new ArrayList<>();
        if (tickers != null) {
            synchronized (tickers) {
                try {
                    result.addAll(tickers.values());
                } catch (Exception e) {
                }
            }
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
        TreeMap<Long, KlineObjectSimple> tickers = symbol2Tickers.get(event.getSymbol());
        if (tickers == null) {
            tickers = new TreeMap<>();
        }
        tickers.put(event.getStartTime(), convertEvent2Kline(event));
        int numberMax = Configs.BTC_TREND_REVERSE_DURATION + 5;
        while (tickers.size() > numberMax) {
            tickers.remove(tickers.firstKey());
        }
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
        TreeMap<Long, KlineObjectSimple> tickers = symbol2Tickers.get(event.getSymbol());
        if (tickers == null) {
            tickers = new TreeMap<>();
        }
        Long time = Utils.getMinute(event.getEventTime());
        KlineObjectSimple kline = tickers.get(time);
        Double lastPrice = event.getLastPrice().doubleValue();
        if (kline == null) {
            kline = new KlineObjectSimple();
            kline.startTime = time.doubleValue();
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

    private static KlineObjectSimple convertEvent2Kline(CandlestickEvent event) {
        KlineObjectSimple result = new KlineObjectSimple();
        result.startTime = event.getStartTime().doubleValue();
        result.priceOpen = event.getOpen().doubleValue();
        result.maxPrice = event.getHigh().doubleValue();
        result.minPrice = event.getLow().doubleValue();
        result.priceClose = event.getClose().doubleValue();
        result.totalUsdt = event.getVolume().doubleValue();
        return result;
    }


}
