/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.bigchange.test;

import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Utils;
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
public class TraceDetailAllDataWithTime {

    public static final Logger LOG = LoggerFactory.getLogger(TraceDetailAllDataWithTime.class);

    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone = new ConcurrentHashMap<>();
    public ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning = new ConcurrentHashMap();
    public Map<String, KlineObjectSimple> symbol2Ticker24h = new HashMap<>();
    public Map<String, KlineObjectSimple> symbol2Ticker12h = new HashMap<>();
    public Map<String, KlineObjectSimple> symbol2Ticker4h = new HashMap<>();
    public Map<String, KlineObjectSimple> symbol2Ticker15m = new HashMap<>();

    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        TraceDetailAllDataWithTime test = new TraceDetailAllDataWithTime();
        test.simulatorEntryByTime("20240902", "06:59", "Buy");
    }


    public void simulatorEntryByTime(String timeInput1, String timeInput2, String side) throws ParseException {
        String timeInput = timeInput1.trim() + " " + timeInput2.trim();
        Long time = Utils.sdfFileHour.parse(timeInput).getTime();
        Long startTime = Utils.getDate(time - Utils.TIME_DAY);
        // data ticker
        TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManager.readDataFromFile1M(startTime);
        TreeMap<Long, Map<String, KlineObjectSimple>> dataNextDate = DataManager.readDataFromFile1M(startTime + Utils.TIME_DAY);
        TreeMap<Long, Map<String, KlineObjectSimple>> dataNext1Date = DataManager.readDataFromFile1M(startTime + 2 * Utils.TIME_DAY);
        TreeMap<Long, Map<String, KlineObjectSimple>> dataNext2Date = DataManager.readDataFromFile1M(startTime + 3 * Utils.TIME_DAY);
        if (dataNextDate != null) {
            time2Tickers.putAll(dataNextDate);
        }
        if (null != dataNext1Date) {
            time2Tickers.putAll(dataNext1Date);
        }
        if (dataNext2Date != null) {
            time2Tickers.putAll(dataNext2Date);
        }

        try {

            // statistic data
            for (int i = 0; i < 1440; i++) {
                Long timeStatistic = time - Utils.TIME_DAY + (i + 1) * Utils.TIME_MINUTE;
                Map<String, KlineObjectSimple> symbol2Ticker = time2Tickers.get(timeStatistic);
                for (String symbol : symbol2Ticker.keySet()) {
                    KlineObjectSimple ticker = time2Tickers.get(timeStatistic).get(symbol);
                    // statistic 24h
                    if (time - timeStatistic <= Utils.TIME_DAY) {
                        KlineObjectSimple ticker24h = symbol2Ticker24h.get(symbol);
                        if (ticker24h == null) {
                            ticker24h = ticker;
                        } else {
                            ticker24h = Utils.updateTickerByTicker(ticker24h, ticker);
                        }
                        symbol2Ticker24h.put(symbol, ticker24h);
                    }
                    // statistic 12h
                    if (time - timeStatistic <= 12 * Utils.TIME_HOUR) {
                        KlineObjectSimple tickerStatistic = symbol2Ticker12h.get(symbol);
                        if (tickerStatistic == null) {
                            tickerStatistic = ticker;
                        } else {
                            tickerStatistic = Utils.updateTickerByTicker(tickerStatistic, ticker);
                        }
                        symbol2Ticker12h.put(symbol, tickerStatistic);
                    }
                    // statistic 4h
                    if (time - timeStatistic <= 4 * Utils.TIME_HOUR) {
                        KlineObjectSimple tickerStatistic = symbol2Ticker4h.get(symbol);
                        if (tickerStatistic == null) {
                            tickerStatistic = ticker;
                        } else {
                            tickerStatistic = Utils.updateTickerByTicker(tickerStatistic, ticker);
                        }
                        symbol2Ticker4h.put(symbol, tickerStatistic);
                    }
                    //statistic 15m
                    if (time - timeStatistic <= 15 * Utils.TIME_MINUTE) {
                        KlineObjectSimple ticker15m = symbol2Ticker15m.get(symbol);
                        if (ticker15m == null) {
                            ticker15m = ticker;
                        } else {
                            ticker15m = Utils.updateTickerByTicker(ticker15m, ticker);
                        }
                        symbol2Ticker15m.put(symbol, ticker15m);
                    }
                }
            }
            // create order
            for (String symbol : time2Tickers.get(time).keySet()) {
                KlineObjectSimple ticker = time2Tickers.get(time).get(symbol);
                KlineObjectSimple lastTicker = time2Tickers.get(time - Utils.TIME_MINUTE).get(symbol);
                if (StringUtils.equalsIgnoreCase(side, "BUY")) {
                    createOrderBUYTarget(symbol, ticker, lastTicker);
                } else {
                    createOrderSELL(symbol, ticker);
                }
            }

            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                if (entry.getKey() <= time) {
                    continue;
                }
                // update all Order
                for (String symbol : orderRunning.keySet()) {
                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                    startUpdateOldOrderTrading(symbol, ticker);
                }
            }


        } catch (Exception e) {
            e.printStackTrace();
        }

        // add all order running to done
        for (OrderTargetInfoTest orderInfo : orderRunning.values()) {
            orderInfo.priceTP = orderInfo.lastPrice;
            allOrderDone.put(orderInfo.timeStart + "-" + orderInfo.symbol, orderInfo);
        }
        // write 2 file
        writeOrder2File();


    }

    private void writeOrder2File() {
        ArrayList<Object> lines = new ArrayList<>();
        lines.add("sym,side,entry,tp,sl,min,rate,max,rate,profit,status,start,end,rate_ticker,volume,quantity,pnl,time");
        for (OrderTargetInfoTest order : allOrderDone.values()) {
            Double profit = Utils.rateOf2Double(order.priceTP, order.priceEntry);
            if (order.side.equals(OrderSide.SELL)) {
                profit = -Utils.rateOf2Double(order.priceTP, order.priceEntry);
            }
            StringBuilder builder = new StringBuilder();
            builder.append(order.symbol.replace("USDT", "")).append(",");
            builder.append(order.side).append(",");
            builder.append(order.priceEntry).append(",");
            builder.append(order.priceTP).append(",");
            builder.append(order.priceSL).append(",");
            builder.append(order.minPrice).append(",");
            builder.append(Utils.rateOf2Double(order.minPrice, order.priceEntry)).append(",");
            builder.append(order.maxPrice).append(",");
            builder.append(Utils.rateOf2Double(order.maxPrice, order.priceEntry)).append(",");
            builder.append(Utils.formatDouble(profit * 100, 3)).append(",");
            builder.append(order.status.toString()).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)).append(",");
            builder.append(Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate)).append(",");
            builder.append(Utils.rateOf2Double(order.tickerOpen.priceClose, order.tickerOpen.priceOpen)).append(",");
            builder.append(order.tickerOpen.totalUsdt).append(",");
            builder.append(order.quantity).append(",");
            builder.append(order.calTp()).append(",");
            builder.append((order.timeUpdate - order.timeStart) / Utils.TIME_MINUTE).append(",");
//            builder.append(symbol2Ticker15m.get(order.symbol).totalUsdt / order.tickerOpen.totalUsdt).append(",");
            builder.append(buildDataStatistic(symbol2Ticker24h.get(order.symbol), order.tickerOpen));
            builder.append(buildDataStatistic(symbol2Ticker12h.get(order.symbol), order.tickerOpen));
            builder.append(buildDataStatistic(symbol2Ticker4h.get(order.symbol), order.tickerOpen));
            builder.append(buildDataStatistic(symbol2Ticker15m.get(order.symbol), order.tickerOpen));

            lines.add(builder.toString());
        }
        try {
            FileUtils.writeLines(new File("storage/order_by_time.csv"), lines);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private String buildDataStatistic(KlineObjectSimple tickerStatistic, KlineObjectNumber tickerTrade) {
        StringBuilder builder = new StringBuilder();
        KlineObjectNumber ticker;
        if (tickerStatistic == null) {
            ticker = tickerTrade;
        } else {
            ticker = Utils.convertKlineSimple(tickerStatistic);
        }
        builder.append(ticker.totalUsdt).append(",");
        builder.append(ticker.maxPrice).append(",");
        builder.append(Utils.formatDouble(Utils.rateOf2Double(tickerTrade.priceClose, ticker.maxPrice), 4)).append(",");
//        builder.append(ticker.minPrice).append(",");
//        builder.append(Utils.formatDouble(Utils.rateOf2Double(tickerTrade.priceClose, ticker.minPrice), 4)).append(",");
//        builder.append(ticker.priceOpen).append(",");
//        builder.append(Utils.formatDouble(Utils.rateOf2Double(tickerTrade.priceClose, ticker.priceOpen), 4)).append(",");
        return builder.toString();
    }


    private void startUpdateOldOrderTrading(String symbol, KlineObjectSimple ticker) {

        OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
        if (orderInfo != null && ticker != null) {
            if (orderInfo.timeStart < ticker.startTime.longValue()) {
                orderInfo.updatePriceByKlineSimple(ticker);
                orderInfo.updateStatusNew();
//                orderInfo.updateStatusFixTPSL();
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                        || orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                        || orderInfo.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                    allOrderDone.put(orderInfo.timeStart + "-" + symbol, orderInfo);
                    BudgetManagerSimple.getInstance().updatePnl(orderInfo);
                    orderRunning.remove(symbol);
                } else {
                    orderInfo.updateTPSL();
                }
            }
        }
    }


    public void createOrderBUYTarget(String symbol, KlineObjectSimple ticker, KlineObjectSimple lastTicker) {
        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage(symbol);
        String log = OrderSide.BUY + " " + symbol + " entry: " + entry +
                " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BUY);
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        order.tickerClose = Utils.convertKlineSimple(lastTicker);
        orderRunning.put(symbol, order);
        BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());
        LOG.info(log);
    }

    private void createOrderSELL(String symbol, KlineObjectSimple ticker) {
        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage(symbol);
        String log = OrderSide.SELL + " " + symbol + " entry: " + entry + " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.SELL);
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        orderRunning.put(symbol, order);
        BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());
        LOG.info(log);
    }
}
