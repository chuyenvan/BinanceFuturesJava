/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
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
public class BuyTicker1MStatisticResearch {

    public static final Logger LOG = LoggerFactory.getLogger(BuyTicker1MStatisticResearch.class);
    public static final String FILE_STORAGE_ORDER_DONE = "storage/Ticker1MStatisticResearch.data";

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;

    public String TIME_RUN = Configs.getString("TIME_RUN");
    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrderRunning = new ConcurrentHashMap();

    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        BuyTicker1MStatisticResearch test = new BuyTicker1MStatisticResearch();
        test.initData();
        test.simulatorWithInitEntry();
    }

    public static boolean isTimeGetData() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 0 && miniSecond < 10;
    }


    public void simulatorWithInitEntry() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        TreeMap<Long, MarketDataObject> time2MarketData = (TreeMap<Long, MarketDataObject>) Storage.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                LOG.info("Read file ticker: {} orderRunning:{} orders done:{} orders {}", Utils.normalizeDateYYYYMMDDHHmm(startTime),
                        counterOrderRunning(), allOrderDone.size(), Utils.statisticRateSuccessTree(allOrderDone));
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
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
                        }
                        MarketDataObject marketData;
                        marketData = time2MarketData.get(time);

                        Set<String> symbolLocked = new HashSet<>();

                        MarketLevelChange levelChange;
                        if (marketData != null) {
                            levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                                    marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg, marketData.rateUp15MAvg,
                                    marketData.rateBtcDown15M);
                            if (levelChange != null) {
                                Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                                if (levelChange.equals(MarketLevelChange.BIG_UP)
                                        || levelChange.equals(MarketLevelChange.BIG_DOWN)) {
                                    numberOrder = numberOrder * 2;
                                }
                                if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                                        || levelChange.equals(MarketLevelChange.MEDIUM_UP)
                                ) {
                                    numberOrder = numberOrder * 2;
                                }
                                if (levelChange.equals(MarketLevelChange.TINY_DOWN)
                                        || levelChange.equals(MarketLevelChange.SMALL_DOWN)
                                ) {
                                    numberOrder = numberOrder * 2;
                                }

                                List<String> symbol2BUY = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(marketData.rate2Max, levelChange,
                                        numberOrder, symbol2Ticker, symbolLocked);

                                LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2BUY);
                                // check create order new
                                for (String symbol : symbol2BUY) {
                                    KlineObjectSimple ticker = entry.getValue().get(symbol);
                                    createOrderBUY(symbol, ticker, levelChange, marketData);
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
//        Storage.writeObject2File("storage/time2rate24hAvg.data", time2Rate24h);
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-" + Configs.TIME_AFTER_ORDER_2_SL, allOrderDone);
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
                    if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                            || order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                            || order.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                        allOrderDone.put(-order.timeStart + allOrderDone.size(), order);
                        LOG.info("Order done: {} {} -> {} {}% {} {} {}", order.symbol, order.priceEntry,
                                order.priceTP, Utils.formatPercent(order.calRateTp()), Utils.normalizeDateYYYYMMDDHHmm(order.timeStart),
                                order.calTp(), order.status);
                        BudgetManagerSimple.getInstance().updatePnl(order);
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

    public void createOrderBUY(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange, MarketDataObject marketData) {

        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
        String log = OrderSide.BUY + " " + symbol + " entry: " + entry +
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
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BUY);
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        order.marketLevelChange = levelChange;
        order.marketData = marketData;
        List<OrderTargetInfoTest> orders = symbol2OrderRunning.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);
        LOG.info(log);
        symbol2OrderRunning.put(symbol, orders);
    }
}
