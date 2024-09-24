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
package com.binance.chuyennd.bigchange.statistic;

import com.educa.chuyennd.funcs.BreadFunctions;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.statistic24hr.Volume24hrManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.CandlestickInterval;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.event.CandlestickEvent;
import java.util.Collection;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class BtcBreadBigChange15M {

    public static final Logger LOG = LoggerFactory.getLogger(BtcBreadBigChange15M.class);
    public Double TOTAL_RATE_CHANGE_WITHBREAD_2TRADING = Configs.getDouble("TOTAL_RATE_CHANGE_WITHBREAD_2TRADING");
    public Double RATE_CHANGE_WITHBREAD_2TRADING = Configs.getDouble("RATE_CHANGE_WITHBREAD_2TRADING");
    public Double BTC_BREAD_BIGCHANE_15M = Configs.getDouble("BTC_BREAD_BIGCHANE_15M");
    public Integer LEVERAGE_ORDER_BEARD = Configs.getInt("LEVERAGE_ORDER_BEARD");
    public Integer NUMBER_TICKER_TO_TRADE = Configs.getInt("NUMBER_TICKER_TO_TRADE");
    public Double BUDGET_PER_ORDER = Configs.getDouble("BUDGET_PER_ORDER");
    public AtomicBoolean isTrading = new AtomicBoolean(false);
    public BreadDetectObject lastBreadTrader = null;
    public Long EVENT_TIME = Utils.TIME_MINUTE * 1;
    public Long lastTimeBreadTrader = 0l;
//    private static final ExecutorService executor = Executors.newFixedThreadPool(Configs.getInt("nThreadTrading"));
    public Collection<? extends String> allSymbol;

    public static void main(String[] args) {
        new BtcBreadBigChange15M().startThreadDetectBreadBigChange2Trade();
//        Long startTime = 1695574800000L;
//        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);
//        new BtcBreadBigChange15M().test(allSymbolTickers);
    }

    public void startThreadDetectBreadBigChange2Trade() {
        // init data
        Volume24hrManager.getInstance();
        allSymbol = TickerFuturesHelper.getAllSymbol();
        allSymbol.removeAll(Constants.diedSymbol);

        // thread listen and detect bread big change 
        SubscriptionClient client = SubscriptionClient.create();
        client.subscribeCandlestickEvent("btcusdt", CandlestickInterval.ONE_MINUTE, ((event) -> {
            if (event.getStartTime() > lastTimeBreadTrader + NUMBER_TICKER_TO_TRADE * EVENT_TIME) {
//                process(event);
            } else {
                LOG.info("Not process because is Trading for bigchange: {}", Utils.toJson(lastBreadTrader));
            }
        }), null);
    }

    private void process(CandlestickEvent event) {
        try {
            BreadDetectObject breadData = BreadFunctions.calBreadData(event, BTC_BREAD_BIGCHANE_15M);
            if (breadData.orderSide != null && breadData.totalRate >= TOTAL_RATE_CHANGE_WITHBREAD_2TRADING
                    && breadData.rateChange > RATE_CHANGE_WITHBREAD_2TRADING && !isTrading.get()) {
                lastTimeBreadTrader = event.getStartTime();
                lastBreadTrader = breadData;
                LOG.info("Bigchange: {} {} bread above:{} bread below:{} totalRate:{}", new Date(event.getStartTime()), breadData.orderSide,
                        breadData.breadAbove, breadData.breadBelow, breadData.totalRate);
                isTrading.set(true);
                startThreadTradingAlt(breadData.orderSide);
            } else {
                LOG.info("{} {} bread above:{} bread below:{} totalRate:{}", new Date(event.getStartTime()),
                        breadData.orderSide, breadData.breadAbove, breadData.breadBelow, breadData.totalRate);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    public void startThreadTradingAlt(OrderSide orderSide) {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadTradingAltBreadBtcBigChan");
            LOG.info("Start ThreadTradingAltBreadBtcBigChan !");
            try {
                for (String symbol : allSymbol) {
                    if (ClientSingleton.getInstance().getBalanceAvalible() <= BUDGET_PER_ORDER) {
                        LOG.info("Break because balance not enough!");
                        break;
                    }
                    Double lastPrice = Volume24hrManager.getInstance().symbol2LastPrice.get(symbol);
                    if (lastPrice == null) {
                        lastPrice = ClientSingleton.getInstance().getCurrentPrice(symbol);
                    }
                    newOrderWithSide(symbol, orderSide, lastPrice);
                }
                isTrading.set(false);
            } catch (Exception e) {
                LOG.error("ERROR during ThreadTradingAltBreadBtcBigChan: {}", e);
                e.printStackTrace();
            }

        }).start();
    }

    private void test(Map<String, List<KlineObjectNumber>> allSymbolTickers) {
        List<KlineObjectNumber> allKlines = allSymbolTickers.get(Constants.SYMBOL_PAIR_BTC);
        for (KlineObjectNumber allKline : allKlines) {
            BreadDetectObject breadData = BreadFunctions.calBreadDataBtc(allKline, TOTAL_RATE_CHANGE_WITHBREAD_2TRADING);
            if (breadData.orderSide != null && breadData.totalRate >= TOTAL_RATE_CHANGE_WITHBREAD_2TRADING && !isTrading.get()) {
                LOG.info("Bigchange: {} {} bread above:{} bread below:{} rateChange:{}", new Date(allKline.startTime.longValue()), breadData.orderSide,
                        breadData.breadAbove, breadData.breadBelow, breadData.totalRate);
                isTrading.set(true);
                startThreadTradingAltTest(breadData.orderSide, allSymbolTickers, allKline.startTime.longValue());
            }
        }
    }

    private void newOrderWithSide(String symbol, OrderSide orderSide, Double lastPrice) {
//        OrderTargetInfo orderInfo = new OrderTargetInfo();
//        orderInfo.leverage = LEVERAGE_ORDER_BEARD;
//        orderInfo.priceEntry = lastPrice;
//        orderInfo.status = OrderStatus.NEW;
//        orderInfo.symbol = symbol;
//        orderInfo.timeStart = System.currentTimeMillis();
//        orderInfo.timeUpdate = System.currentTimeMillis();        
    }

    private void startThreadTradingAltTest(OrderSide orderSide, Map<String, List<KlineObjectNumber>> allSymbolTickers, long startTime) {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadTradingAltBreadBtcBigChan");
            LOG.info("Start ThreadTradingAltBreadBtcBigChan !");
            try {
                for (String symbol : allSymbol) {
                    Double lastPrice = getLastPrice(allSymbolTickers.get(symbol), startTime);
                    if (lastPrice == null) {
                        LOG.info("Price null not trade: {}", symbol, startTime);
                        continue;
                    }
                    newOrderWithSide(symbol, orderSide, lastPrice);
                }
                isTrading.set(false);
            } catch (Exception e) {
                LOG.error("ERROR during ThreadTradingAltBreadBtcBigChan: {}", e);
                e.printStackTrace();
            }

        }).start();
    }

    private Double getLastPrice(List<KlineObjectNumber> tickers, long startTime) {
        for (KlineObjectNumber ticker : tickers) {
            if (ticker.startTime.longValue() == startTime) {
                return ticker.priceClose;
            }
        }
        return null;
    }

}
