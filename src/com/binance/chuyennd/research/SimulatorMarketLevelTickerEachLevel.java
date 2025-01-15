/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

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
public class SimulatorMarketLevelTickerEachLevel {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorMarketLevelTickerEachLevel.class);
    public String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;
    public static final String FILE_STORAGE_ORDER_ENTRIES = "storage/OrderEntries.data";
    public final String TIME_RUN = Configs.getString("TIME_RUN");
    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry = new ConcurrentHashMap();
    public ConcurrentHashMap<String, OrderTargetInfoTest> symbol2OrderRunning = new ConcurrentHashMap();


    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        SimulatorMarketLevelTickerEachLevel test = new SimulatorMarketLevelTickerEachLevel();


        EnumSet<MarketLevelChange> all = EnumSet.allOf(MarketLevelChange.class);
        List<MarketLevelChange> list = new ArrayList<>(all.size());
        for (MarketLevelChange s : all) {
            list.add(s);
        }

        for (MarketLevelChange level : list) {
            BudgetManagerSimple.getInstance().resetHistory();
            BudgetManagerSimple.getInstance().levelRun = level;
            test.FILE_STORAGE_ORDER_DONE = "storage/level/OrderTestDone-" + level;
            String fileData = test.FILE_STORAGE_ORDER_DONE + "-"
                    + Configs.TIME_AFTER_ORDER_2_SL ;
            if (new File(fileData).exists()) {
                continue;
            }
            test.initData();
            test.simulatorAllSymbol();
        }

    }

    public void runAOrder(String symbol, String time) {
        MarketLevelChange levelChange = MarketLevelChange.MEDIUM_DOWN;
        try {
            long startTime = Utils.sdfFileHour.parse(time).getTime();
            List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
            createOrderBUYTarget(symbol, tickers.get(0), levelChange, null, null);
            for (KlineObjectSimple ticker : tickers) {
                LOG.info("Process time: {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
                if (symbol2OrderRunning.isEmpty()) {
                    break;
                }
                startUpdateOldOrderTrading(symbol, ticker);
            }
            for (OrderTargetInfoTest order : allOrderDone.values()) {
                LOG.info("{} {} {} {} -> {} {}%", order.side, order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart),
                        order.priceEntry, order.priceTP, Utils.formatDouble(Utils.rateOf2Double(order.priceTP, order.priceEntry) * 100, 3));
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    private void simulatorAllSymbol() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<Long, List<OrderTargetInfoTest>> time2Entries = (Map<Long, List<OrderTargetInfoTest>>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_ENTRIES);
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                LOG.info("Read file ticker: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                time2Tickers = DataManager.readDataFromFile1M(startTime);
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
                            // update order Old
                            startUpdateOldOrderTrading(symbol, ticker);
                        }
                        List<OrderTargetInfoTest> orders = time2Entries.get(time);
                        if (orders != null) {
                            for (OrderTargetInfoTest order : orders) {
                                KlineObjectSimple ticker = entry.getValue().get(order.symbol);
                                createOrderBUYTarget(order.symbol, ticker, order.marketLevelChange, order.marketData, null);
                            }
                        }

                        if (time % Utils.TIME_DAY == 0) {
                            BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, true);
                        } else {
                            BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            Long finalStartTime1 = startTime;
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                BudgetManagerSimple.getInstance().updateBalance(finalStartTime1, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                break;
            }
        }
        // add all order running to done
        for (List<OrderTargetInfoTest> orderRunning : symbol2OrdersEntry.values()) {
            for (OrderTargetInfoTest orderInfo : orderRunning) {
                orderInfo.maxPrice = symbol2OrderRunning.get(orderInfo.symbol).maxPrice;
                orderInfo.lastPrice = symbol2OrderRunning.get(orderInfo.symbol).lastPrice;
                orderInfo.priceTP = orderInfo.lastPrice;
                orderInfo.minPrice = symbol2OrderRunning.get(orderInfo.symbol).minPrice;
                orderInfo.timeUpdate = symbol2OrderRunning.get(orderInfo.symbol).timeUpdate;
                allOrderDone.put(-orderInfo.timeUpdate + allOrderDone.size(), orderInfo);
            }
        }
        String reportMinProfit = "";
        if (allOrderDone.size() > 0) {
            reportMinProfit = statisticResult(allOrderDone);
        }
        LOG.info("Update-{}-{} {}", Configs.TIME_AFTER_ORDER_2_SL, BudgetManagerSimple.getInstance().levelRun, reportMinProfit);
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-"
                + Configs.TIME_AFTER_ORDER_2_SL , allOrderDone);
        Storage.writeObject2File("storage/orderRunning.data", symbol2OrderRunning);
        BudgetManagerSimple.getInstance().printBalanceIndex();
    }

    private Set<String> getSymbolLocked() {
        Set<String> hashSet = new HashSet<>();
        for (String symbol : symbol2OrdersEntry.keySet()) {
            OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
            if (orderMulti != null && orderMulti.calMargin() >= 3 * BudgetManagerSimple.getInstance().getBudget()) {
                hashSet.add(symbol);
            }
        }
        return hashSet;
    }


    private List<String> addSpecialSymbol(List<String> symbol2BUY, MarketLevelChange levelChange, Map<String, KlineObjectSimple> symbol2Ticker) {
        if (levelChange != null && levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            KlineObjectSimple tickerBtc = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
            if (tickerBtc != null && Utils.rateOf2Double(tickerBtc.priceClose, tickerBtc.priceOpen) < -0.03) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_BTC);
            }
            KlineObjectSimple tickerSol = symbol2Ticker.get(Constants.SYMBOL_PAIR_SOL);
            if (tickerSol != null && Utils.rateOf2Double(tickerSol.priceClose, tickerSol.priceOpen) < -0.02) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_SOL);
            }
            KlineObjectSimple tickerBNB = symbol2Ticker.get(Constants.SYMBOL_PAIR_BNB);
            if (tickerBNB != null && Utils.rateOf2Double(tickerBNB.priceClose, tickerBNB.priceOpen) < -0.015) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_BNB);
            }
            KlineObjectSimple tickerXRP = symbol2Ticker.get(Constants.SYMBOL_PAIR_XRP);
            if (tickerXRP != null && Utils.rateOf2Double(tickerXRP.priceClose, tickerXRP.priceOpen) < -0.03) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_XRP);
            }
        }
        if (levelChange != null && levelChange.equals(MarketLevelChange.MEDIUM_DOWN)) {
            KlineObjectSimple tickerBNB = symbol2Ticker.get(Constants.SYMBOL_PAIR_BNB);
            if (tickerBNB != null && Utils.rateOf2Double(tickerBNB.priceClose, tickerBNB.priceOpen) < -0.024) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_BNB);
            }
            KlineObjectSimple tickerXRP = symbol2Ticker.get(Constants.SYMBOL_PAIR_XRP);
            if (tickerXRP != null && Utils.rateOf2Double(tickerXRP.priceClose, tickerXRP.priceOpen) < -0.03) {
                symbol2BUY.add(Constants.SYMBOL_PAIR_XRP);
            }
        }
        return symbol2BUY;
    }

    public String statisticResult(TreeMap<Long, OrderTargetInfoTest> time2Order) {
        Map<MarketLevelChange, List<OrderTargetInfoTest>> level2Orders = new HashMap<>();
        List<Double> pnls = new ArrayList<>();
        List<Double> pnlNotMays = new ArrayList<>();
        List<Double> pnlNot2021 = new ArrayList<>();
        List<Double> pnl2024 = new ArrayList<>();
        Map<Double, String> pnl2Info = new HashMap<>();
        for (OrderTargetInfoTest orderInfo : time2Order.values()) {
            List<OrderTargetInfoTest> orders = level2Orders.get(orderInfo.marketLevelChange);
            if (orders == null) {
                orders = new ArrayList<>();
            }
            orders.add(orderInfo);
            level2Orders.put(orderInfo.marketLevelChange, orders);
            Double tp = orderInfo.calTp();
            pnl2Info.put(tp, orderInfo.symbol + "-" + Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart));
            pnls.add(tp);
            if (!StringUtils.equals(Utils.sdfFile.format(new Date(orderInfo.timeStart)), "20210519")) {
                pnlNotMays.add(tp);
            }
            if (!StringUtils.startsWith(Utils.sdfFile.format(new Date(orderInfo.timeStart)), "2021")) {
                pnlNot2021.add(tp);
            }
            if (StringUtils.startsWith(Utils.sdfFile.format(new Date(orderInfo.timeStart)), "2024")) {
                pnl2024.add(tp);
            }
        }
        TreeMap<Double, MarketLevelChange> rateProfit2Level = new TreeMap<>();
        for (MarketLevelChange level : level2Orders.keySet()) {
            List<OrderTargetInfoTest> orders = level2Orders.get(level);
            rateProfit2Level.put(-calRateProfit(orders), level);
        }
        StringBuilder builder = new StringBuilder();
        for (Double rate : rateProfit2Level.keySet()) {
            MarketLevelChange level = rateProfit2Level.get(rate);
            builder.append(level)
                    .append(" -> ")
                    .append(level2Orders.get(level).size())
                    .append(" ")
                    .append(Utils.formatDouble(-rate * 100, 3)).append("\t");
        }
        return "\tProfitMinAll: " + Utils.findMinSubarraySum(pnls.toArray(new Double[0]))
                + " " + pnl2Info.get(Utils.findMinSubarraySumIndex(pnls.toArray(new Double[0])))
                + "\tMinNotMay: " + Utils.findMinSubarraySum(pnlNotMays.toArray(new Double[0]))
                + " " + pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNotMays.toArray(new Double[0])))
                + "\tMinNot2021: " + Utils.findMinSubarraySum(pnlNot2021.toArray(new Double[0]))
                + " " + pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNot2021.toArray(new Double[0])))
                + "\tMin2024: " + Utils.findMinSubarraySum(pnl2024.toArray(new Double[0]))
                + " " + pnl2Info.get(Utils.findMinSubarraySumIndex(pnl2024.toArray(new Double[0]))) + "\t" + builder;

    }

    private Double calRateProfit(List<OrderTargetInfoTest> orders) {
        Double rate = 0d;
        Double total = 0d;
        for (OrderTargetInfoTest order : orders) {
            total += order.calRateTp();
        }
        if (!orders.isEmpty()) {
            return total / orders.size();
        }
        return rate;
    }


    private void exitWhenDone() {
        try {
//            Storage.writeObject2File(FILE_STORAGE_MARKET_DATA, time2MarketData);
            Thread.sleep(10 * Utils.TIME_SECOND);
            System.exit(1);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void initData() throws IOException, ParseException {
        // clear Data Old
        allOrderDone = new TreeMap<>();
        symbol2OrdersEntry.clear();
        symbol2OrderRunning.clear();
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
        for (List<OrderTargetInfoTest> orderRunning : symbol2OrdersEntry.values()) {
            for (OrderTargetInfoTest orderInfo : orderRunning) {
                if (orderInfo != null) {
                    Double pnl = orderInfo.calProfit();
                    pnl2OrderInfo.put(pnl, orderInfo);
                    if (orderInfo.dynamicTP_SL != null && orderInfo.dynamicTP_SL > 0) {
                        dcaTotal++;
                    }
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

    public List<OrderTargetInfoTest> getOrdersRunning() {
        List<OrderTargetInfoTest> orderRunning = new ArrayList<>();
        for (List<OrderTargetInfoTest> orders : symbol2OrdersEntry.values()) {
            if (orders != null && !orders.isEmpty()) {
                orderRunning.addAll(orders);
            }
        }
        return orderRunning;
    }

    private void startUpdateOldOrderTrading(String symbol, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
        if (orderMulti != null) {
            if (orderMulti.timeStart < ticker.startTime.longValue()) {
                orderMulti.updatePriceByKlineSimple(ticker);
                orderMulti.updateStatusNew(null);
                if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                        || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                        || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                    List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
                    for (OrderTargetInfoTest order : orders) {
                        order.timeUpdate = orderMulti.timeUpdate;
                        order.status = orderMulti.status;
                        order.priceTP = orderMulti.priceTP;
                        order.maxPrice = orderMulti.maxPrice;
                        order.minPrice = orderMulti.minPrice;
                        allOrderDone.put(-order.timeUpdate + allOrderDone.size(), order);
                        LOG.info("Order done: {} {} {} {} -> {} {}%", order.side, order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart),
                                order.priceEntry, order.priceTP, Utils.formatPercent(Utils.rateOf2Double(order.priceTP, order.priceEntry)));
                        BudgetManagerSimple.getInstance().updatePnl(order);
                    }
                    symbol2OrdersEntry.remove(symbol);
                    symbol2OrderRunning.remove(symbol);
                } else {
                    orderMulti.updateTPSL(null);
                }
            }
        }
    }

    private OrderTargetInfoTest mergeOrder(List<OrderTargetInfoTest> orders) {
        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        Double entryTotal = 0d;
        Double quantity = 0d;
        String priceEntry = "";
        for (OrderTargetInfoTest orderInfo : orders) {
            time2Order.put(orderInfo.timeStart, orderInfo);
            entryTotal += orderInfo.priceEntry;
            quantity += orderInfo.quantity;
            priceEntry += orderInfo.priceEntry + "-";
        }
        double entry = entryTotal / time2Order.size();
        OrderTargetInfoTest orderResult = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry,
                null, quantity, 10, time2Order.lastEntry().getValue().symbol, time2Order.lastEntry().getKey(),
                time2Order.lastEntry().getKey(), OrderSide.BUY);

        orderResult.minPrice = entry;
        orderResult.lastPrice = entry;
        orderResult.maxPrice = entry;
        orderResult.tickerOpen = time2Order.lastEntry().getValue().tickerOpen;
        orderResult.marketLevelChange = time2Order.lastEntry().getValue().marketLevelChange;
        if (orders.size() > 2) {
            LOG.info("Merger orders of {}: {} -> {}", orders.get(0).symbol, priceEntry, orderResult.priceEntry);
        }
        return orderResult;
    }


    public void createOrderBUYTarget(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange,
                                     MarketDataObject marketData, Double maxPrice15M) {
        if (!levelChange.equals(BudgetManagerSimple.getInstance().levelRun)) {
            return;
        }
        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage(symbol);
        Double marginRunning = calMarginRunning();
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
        ) {
            budget = budget / 2;
        }
        if (levelChange.equals(MarketLevelChange.BTC_REVERSE)
                || levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
//                || levelChange.equals(MarketLevelChange.SMALL_UP_15M)
        ) {
            budget = budget / 3;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_UP_15M)
        ) {
            budget = budget / 6;
        }
        if (marginRunning > 15 * BudgetManagerSimple.getInstance().getBudget()
                && (levelChange.equals(MarketLevelChange.MEDIUM_UP_15M)
                || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                || levelChange.equals(MarketLevelChange.SMALL_UP_15M)
                || levelChange.equals(MarketLevelChange.TINY_DOWN_15M))
                || levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
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
        String log = OrderSide.BUY + " " + symbol + " entry: " + entry +
                " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);

        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)){
            if (quantity <0.002){
                quantity = 0.002;
            }
        }
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BUY);

        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        order.marketLevelChange = levelChange;
        order.rateChange = maxPrice15M;
        if (marketData != null) {
            marketData.rate2Max.clear();
            marketData.symbol2PriceMax15M.clear();
            order.marketData = marketData;
        }
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);
        LOG.info(log);
        symbol2OrdersEntry.put(symbol, orders);
        symbol2OrderRunning.put(symbol, mergeOrder(orders));

        BudgetManagerSimple.getInstance().updateMaxOrderRunning(counterOrderRunning());
    }

    private Integer counterOrderRunning() {
        Integer counter = 0;
        for (List<OrderTargetInfoTest> orders : symbol2OrdersEntry.values()) {
            if (orders != null) {
                counter += orders.size();
            }
        }
        return counter;
    }

    private Double calMarginRunning() {
        Double marginTotal = 0d;
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            marginTotal += order.calMargin();
        }
        return marginTotal;
    }


    private Double calUnProfitOrderRunning(MarketLevelChange... levels) {
        Double unProfit = 0d;
        List<MarketLevelChange> levelNotCheck = new ArrayList<>();
        for (MarketLevelChange level : levels) {
            levelNotCheck.add(level);
        }
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order != null && !levelNotCheck.contains(order.marketLevelChange)) {
                unProfit = order.calProfit();
            }
        }
        return unProfit;
    }
}
