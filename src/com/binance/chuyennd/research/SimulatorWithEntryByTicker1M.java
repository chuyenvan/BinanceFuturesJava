/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.io.FileUtils;
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
public class SimulatorWithEntryByTicker1M {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorWithEntryByTicker1M.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestEntryDone.data";

    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
    public ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning = new ConcurrentHashMap();


    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        SimulatorWithEntryByTicker1M test = new SimulatorWithEntryByTicker1M();
        test.initData();
        test.simulatorEntryByTime();
    }


    private void simulatorEntryByTime() throws ParseException {
        String fileMarketChangeLevelData = "target/entry/volumeBigSignalBuy.data";
        Map<String, KlineObjectSimple> symbol2LastTicker = new HashMap<>();
        TreeMap<Long, List<String>> time2Entry = null;
        Set<Long> dateOfEntry = new HashSet<>();
        if (new File(fileMarketChangeLevelData).exists()) {
            time2Entry = (TreeMap<Long, List<String>>) Storage.readObjectFromFile(fileMarketChangeLevelData);
        }
        if (time2Entry == null) {
            System.exit(1);
        }
        for (Long time : time2Entry.keySet()) {
            dateOfEntry.add(Utils.getDate(time));
        }
        Long startTime = Utils.getDate(time2Entry.firstKey());
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                if (!orderRunning.isEmpty() || dateOfEntry.contains(startTime)) {
                    LOG.info("Read file ticker: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                    time2Tickers = DataManager.readDataFromFile1M(startTime);
                    if (time2Tickers != null) {
                        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                            Long time = entry.getKey();
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            // update order Old
                            for (String symbol : orderRunning.keySet()) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                startUpdateOldOrderTrading(symbol, ticker);
                            }

                            if (time2Entry.get(time) != null) {
                                List<String> symbol2Trade = time2Entry.get(time);
                                LOG.info("{} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), symbol2Trade);
                                // check create order new
                                for (String symbol : symbol2Trade) {
                                    KlineObjectSimple ticker = entry.getValue().get(symbol);
                                    if (orderRunning.containsKey(symbol)) {
                                        LOG.info("Error symbol 2 trade: {} {}", Utils.normalizeDateYYYYMMDDHHmm(time),
                                                Utils.toJson(orderRunning.get(symbol)));
                                    } else {
                                        createOrderBUYTarget(symbol, ticker);
                                    }
                                }
                            }
                            symbol2LastTicker.putAll(entry.getValue());

                            if (time % Utils.TIME_DAY == 0) {
                                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, orderRunning, true);
                            } else {
                                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, orderRunning, false);
                            }
                            BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            Long finalStartTime1 = startTime;
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                BudgetManagerSimple.getInstance().updateBalance(finalStartTime1, allOrderDone, orderRunning, false);
                break;
            }
        }
        // add all order running to done
        for (OrderTargetInfoTest orderInfo : orderRunning.values()) {
            orderInfo.priceTP = orderInfo.lastPrice;
            allOrderDone.put(orderInfo.timeStart + "-" + orderInfo.symbol, orderInfo);
        }
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-"
                + Configs.TIME_AFTER_ORDER_2_TP + "-" + Configs.TIME_AFTER_ORDER_2_SL, allOrderDone);
        BudgetManagerSimple.getInstance().printBalanceIndex();


    }


    public void initData() throws IOException, ParseException {
        // clear Data Old
        allOrderDone = new ConcurrentHashMap<>();
        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
            FileUtils.delete(new File(FILE_STORAGE_ORDER_DONE));
        }
    }


    public StringBuilder calReportRunning(Long currentTime) {
        StringBuilder builder = new StringBuilder();
        Double totalLoss = 0d;
        Double totalBuy = 0d;
        Double totalSell = 0d;
        Integer dcaTotal = 0;
        TreeMap<Double, OrderTargetInfoTest> pnl2OrderInfo = new TreeMap<>();
        for (String symbol : orderRunning.keySet()) {
            OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
            if (orderInfo != null) {
                Double pnl = orderInfo.calProfit();
                pnl2OrderInfo.put(pnl, orderInfo);
                if (orderInfo.dynamicTP_SL != null && orderInfo.dynamicTP_SL > 0) {
                    dcaTotal++;
                }
            }
        }
        int counterLog = 0;
        for (Map.Entry<Double, OrderTargetInfoTest> entry : pnl2OrderInfo.entrySet()) {
            Double pnl = entry.getKey();
            OrderTargetInfoTest orderInfo = entry.getValue();
            Double ratePercent = orderInfo.calRateLoss() * 100;
            totalLoss += ratePercent;
            if (orderInfo.side.equals(OrderSide.BUY)) {
                totalBuy += ratePercent;
            } else {
                totalSell += ratePercent;
            }

            if (counterLog < 105) {
                counterLog++;
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart)).append(" ").
                        append(Utils.normalizeDateYYYYMMDDHHmm(currentTime)).append(" margin:")
                        .append(orderInfo.calMargin().longValue()).append(" ")
                        .append(orderInfo.side).append(" ").append(orderInfo.symbol)
                        .append(" ").append(" dcaLevel:").append(orderInfo.dynamicTP_SL).append(" ")
                        .append(orderInfo.priceEntry).append("->").append(orderInfo.lastPrice).append(" ").
                        append(ratePercent.longValue()).append("%").append(" ").append(pnl.longValue()).append("$").append("\n");
            }
        }

        builder.append("Total: ").append(totalLoss.longValue()).append("%");
        builder.append(" Buy: ").append(totalBuy.longValue()).append("%");
        builder.append(" Sell: ").append(totalSell.longValue()).append("%");
        builder.append(" dcaRunning: ").append(dcaTotal).append("%");
        return builder;
    }


    private void startUpdateOldOrderTrading(String symbol, KlineObjectSimple ticker) {

        OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
        if (orderInfo != null) {
            if (orderInfo.timeStart < ticker.startTime.longValue()) {
                orderInfo.updatePriceByKlineSimple(ticker);
                orderInfo.updateStatusNew(ticker);
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


    public void createOrderBUYTarget(String symbol, KlineObjectSimple ticker) {
        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
        String log = OrderSide.BUY + " " + symbol + " entry: " + entry +
                " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);
//        Double priceTarget = Utils.calPriceTarget(symbol, entry, OrderSide.BUY, 3 * Configs.RATE_TARGET);
//        Double priceSTL = Utils.calPriceTarget(symbol, entry, OrderSide.SELL, 3 * Configs.RATE_TARGET);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BUY);
//        order.priceSL = priceSTL;
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        orderRunning.put(symbol, order);
        BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());
        LOG.info(log);
    }

}
