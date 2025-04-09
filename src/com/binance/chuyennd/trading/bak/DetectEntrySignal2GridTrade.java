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
package com.binance.chuyennd.trading.bak;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
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
public class DetectEntrySignal2GridTrade {

    public static final Logger LOG = LoggerFactory.getLogger(DetectEntrySignal2GridTrade.class);
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    public Set<? extends String> allSymbol;
    //    public Set<String> symbolVolumeLower = new HashSet<>();

    public ConcurrentHashMap<String, List<KlineObjectNumber>> symbol2Tickers = new ConcurrentHashMap<>();

    public static void main(String[] args) throws InterruptedException, ParseException {
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
                    allSymbol.removeAll(Constants.diedSymbol);
                    allSymbol.remove(Constants.SYMBOL_PAIR_BTC);
                }
                if (isTimeGetData()) {
                    try {
                        LOG.info("Start get data of market! {}", new Date());
                        Long startTime = Utils.getMinute(System.currentTimeMillis() -
                                (Configs.NUMBER_TICKER_CAL_RATE_CHANGE + 5) * Utils.TIME_MINUTE);
                        allSymbol.remove(Constants.SYMBOL_PAIR_BTC);
                        for (String symbol : allSymbol) {
                            if (Constants.btcReverseSymbol.contains(symbol)) {
                                executorService.execute(() -> getTickerBySymbol(symbol, startTime - 100 * Utils.TIME_MINUTE));
                            } else {
                                executorService.execute(() -> getTickerBySymbol(symbol, startTime));
                            }
                        }
                        executorService.execute(() -> getTickerBySymbol(Constants.SYMBOL_PAIR_BTC, startTime - 340 * Utils.TIME_MINUTE));
//                        executorService.execute(() -> checkMarketLevelChange2Trade());

                    } catch (Exception e) {
                        LOG.error("ERROR during ThreadDetectMarketLevel2Trader: {}", e);
                        e.printStackTrace();
                    }
                }

                try {
                    Thread.sleep(Utils.TIME_SECOND / 10);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectEntrySignal2GridTrade.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }




    public static Double calMarginRunning(String symbol) {
        if (BudgetManager.getInstance().symbol2Margin.get(symbol) != null) {
            return BudgetManager.getInstance().symbol2Margin.get(symbol);
        }
        return 0d;
    }


    public boolean isTimeGetData() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 0 && miniSecond < 100;
    }

    public boolean isTimeProcessPositionQuick() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 40 && miniSecond < 100;
    }

    private void initData() {
        allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        allSymbol.removeAll(Constants.diedSymbol);
        symbol2Tickers.clear();
    }

    public void getTickerBySymbol(String symbol, Long time) {
        try {
            List<KlineObjectNumber> tickers = TickerFuturesHelper.getTickerWithStartTime(symbol, Constants.INTERVAL_1M, time);
            if (!tickers.isEmpty()) {
                if (tickers.get(tickers.size() - 1).endTime.longValue() > System.currentTimeMillis()) {
                    tickers.remove(tickers.size() - 1);
                }
                symbol2Tickers.put(symbol, tickers);
            }
        } catch (Exception e) {
            LOG.info("Error get ticker of:{}", symbol);
            e.printStackTrace();
        }
    }


}
