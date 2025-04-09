/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.bigchange.test.TraceOrderDone;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * @author pc
 */
public class SellTicker1MStatisticResearch {

    public static final Logger LOG = LoggerFactory.getLogger(SellTicker1MStatisticResearch.class);
    public static final String FILE_STORAGE_ORDER_DONE = "storage/SellTicker1MStatisticResearch.data";

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;

    public String TIME_RUN = Configs.getString("TIME_RUN");
    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrderRunning = new ConcurrentHashMap();

    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        SellTicker1MStatisticResearch test = new SellTicker1MStatisticResearch();
        test.initData();
        test.simulatorWithInitEntry();
    }

    public void simulatorWithInitEntry() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
            try {
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                LOG.info("Read file ticker: {} orderRunning:{} orders done:{} orders {}", Utils.normalizeDateYYYYMMDDHHmm(startTime),
                        counterOrderRunning(), allOrderDone.size(), Utils.statisticRateSuccessTree(allOrderDone));
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                        Map<String, Double> symbol2MaxPrice = new HashMap<>();
                        Map<String, Double> symbol2MinPrice = new HashMap<>();
                        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                            String symbol = entry1.getKey();
                            if (Constants.diedSymbol.contains(symbol)) {
                                continue;
                            }
                            KlineObjectSimple ticker = entry1.getValue();
                            if (!Utils.isTickerAvailable(ticker)) {
                                continue;
                            }
                            // update order Old
                            startUpdateOldOrderTrading(symbol, ticker);

                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                            if (tickers == null) {
                                tickers = new ArrayList<>();
                                symbol2LastTickers.put(symbol, tickers);
                            }
                            tickers.add(ticker);
                            int sizeRemove = 25;
                            if (tickers.size() > sizeRemove) {
                                for (int i = 0; i < 5; i++) {
                                    tickers.remove(0);
                                }
                            }
                            Double priceMax = null;
                            Double minPrice = null;
                            for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                                int index = tickers.size() - i - 1;
                                if (index >= 0) {
                                    KlineObjectSimple kline = tickers.get(index);
                                    if (priceMax == null) {
                                        priceMax = kline.maxPrice;
                                    }
                                    priceMax = Math.max(priceMax, kline.maxPrice);

                                    if (minPrice == null) {
                                        minPrice = kline.minPrice;
                                    }
                                    minPrice = Math.min(minPrice, kline.minPrice);
                                }
                            }
                            symbol2MaxPrice.put(symbol, priceMax);
                            symbol2MinPrice.put(symbol, minPrice);
                        }
                        MarketDataObject marketData = MarketBigChangeDetectorTest.calMarketData(symbol2Ticker, symbol2MaxPrice, symbol2MinPrice);
                        if (marketData != null) {
                            if (marketData.rateUpAvg > 0.015 || marketData.rateUp15MAvg > 0.01) {
                                Set<String> symbolLocked = new HashSet<>();
                                MarketLevelChange levelChange = MarketLevelChange.ORDER_SELL;
                                List<String> symbol2BUY = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(marketData.rate2Min, levelChange,
                                        2, symbol2Ticker, symbolLocked);
                                // check create order new
                                for (String symbol : symbol2BUY) {
                                    KlineObjectSimple ticker = entry.getValue().get(symbol);
                                    createOrderSell(symbol, ticker, levelChange, marketData);
                                }
                            }
                        }
                    }
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
        // add all order running to done
        for (List<OrderTargetInfoTest> orderRunning : symbol2OrderRunning.values()) {
            for (OrderTargetInfoTest orderInfo : orderRunning) {
                orderInfo.priceTP = orderInfo.lastPrice;
                allOrderDone.put(-orderInfo.timeStart + allOrderDone.size(), orderInfo);
            }
        }
        try {
            Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-" + Configs.TIME_AFTER_ORDER_2_SL, allOrderDone);
            TraceOrderDone.printOrderRunningNew(allOrderDone);
        } catch (Exception e) {
            e.printStackTrace();
        }
//        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-" + Configs.TIME_AFTER_ORDER_2_SL, allOrderDone);
    }

    private Integer counterOrderRunning() {
        int counter = 0;
        for (List<OrderTargetInfoTest> orders : symbol2OrderRunning.values()) {
            counter += orders.size();
        }
        return counter;
    }


    public void initData() throws IOException, ParseException {
        // clear Data Old
        allOrderDone = new TreeMap<>();
        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
            FileUtils.delete(new File(FILE_STORAGE_ORDER_DONE));
        }

    }

    private void startUpdateOldOrderTrading(String symbol, KlineObjectSimple ticker) {
        List<OrderTargetInfoTest> orders = symbol2OrderRunning.get(symbol);
        List<OrderTargetInfoTest> ordersDone = new ArrayList<>();
        if (orders != null) {
            for (OrderTargetInfoTest order : orders) {
                if (order.timeStart < ticker.startTime.longValue()) {
                    order.updatePriceByKlineSimple(ticker);
                    order.updateStatusNew();
                    // update for over time/ over loss
                    if (order.status.equals(OrderTargetStatus.REQUEST)
                            && (order.timeUpdate - order.timeStart > Utils.TIME_DAY * 30
                            || order.calRateLoss() < -5)) {
                        order.priceTP = order.lastPrice;
                        order.status = OrderTargetStatus.STOP_LOSS_DONE;
                    }
                    if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                            || order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                            || order.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                        allOrderDone.put(-order.timeStart + allOrderDone.size(), order);
                        LOG.info("Order done: {} {} -> {} {}% {} {} {}", order.symbol, order.priceEntry,
                                order.priceTP, Utils.formatPercent(order.calRateTp()), Utils.normalizeDateYYYYMMDDHHmm(order.timeStart),
                                order.calTp(), order.status);
                        ordersDone.add(order);
                    } else {
                        order.updateTPSL();
                    }
                }
            }
            if (!ordersDone.isEmpty()) {
                orders.removeAll(ordersDone);
            }
        }
    }

    public void createOrderSell(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange, MarketDataObject marketData) {

        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudgetSell();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
        String log = OrderSide.SELL + " " + symbol + " entry: " + entry +
                " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantityTest(budget, leverage, entry, symbol);

        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
            Double minBtcTrade = 0.002;
            if (quantity < minBtcTrade) {
                quantity = minBtcTrade;
            }
        }
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.SELL);
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        order.marketLevelChange = levelChange;
        if (marketData != null) {
            marketData.rateDown2Symbols.clear();
            marketData.rate2Max.clear();
            marketData.rate2Min.clear();
            marketData.symbol2PriceMax15M.clear();
            order.marketData = marketData;
        }
        List<OrderTargetInfoTest> orders = symbol2OrderRunning.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);
        LOG.info(log);
        symbol2OrderRunning.put(symbol, orders);
    }
}
