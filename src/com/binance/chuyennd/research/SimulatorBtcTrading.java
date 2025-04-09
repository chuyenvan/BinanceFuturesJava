/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
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
public class SimulatorBtcTrading {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorBtcTrading.class);
    public static final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;
    public String symbol = Constants.SYMBOL_PAIR_BTC;

    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry = new ConcurrentHashMap();
    public ConcurrentHashMap<String, OrderTargetInfoTest> symbol2OrderRunning = new ConcurrentHashMap();


    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        SimulatorBtcTrading test = new SimulatorBtcTrading();
        test.initData();
        test.simulatorWithInitEntry();
    }


    public void simulatorWithInitEntry(String... inputs) throws ParseException {
        List<KlineObjectSimple> tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(
                Configs.FOLDER_TICKER_1M + symbol);
        Map<Long, MarketDataObject> time2MarketData = (Map<Long, MarketDataObject>)
                Storage.readObjectFromFile("storage/market_data/time2market.data");
        Double rateTrend = 0.01;
        Integer duration = 360;
        String fileNameBtcReverse = "storage/btc/btcReverse-" + rateTrend + "-" + duration;
        TreeMap<Long, Double> timeBtcReverse = (TreeMap<Long, Double>) Storage.readObjectFromFile(fileNameBtcReverse);
        for (int i = 0; i < tickers.size(); i++) {
            KlineObjectSimple ticker = tickers.get(i);
            Long time = ticker.startTime.longValue();
            MarketDataObject marketData = time2MarketData.get(time);

            startUpdateOldOrderTrading(symbol, ticker);

//            if (marketData != null) {
//                MarketLevelChange levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
//                        marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg, marketData.rateUp15MAvg,
//                        marketData.rateBtcDown15M);
//                if (levelChange != null) {
//                    createOrderBUY(ticker, levelChange);
//                }
//            }
//            Double rateBtcTrendReverse = timeBtcReverse.get(time);
//
//            if (rateBtcTrendReverse != null) {
//                MarketLevelChange levelChange = MarketLevelChange.BTC_TREND_REVERSE;
//                createOrderBUY(ticker, levelChange);
//            }

            MarketLevelChange levelChange = MarketLevelChange.BTC_TREND_REVERSE;
            if (symbol2OrderRunning.isEmpty()) {
                if (i > 15) {
                    Double maxPrice = ticker.maxPrice;
                    for (int j = 0; j < 15; j++) {
                        KlineObjectSimple tickerOld = tickers.get(i - j - 1);
                        maxPrice = Math.max(tickerOld.maxPrice, maxPrice);
                    }
                    if (Utils.rateOf2Double(ticker.priceClose, maxPrice) < -0.01) {
                        createOrderBUY(ticker, levelChange);
                    }
                }
            } else {
                Double rateNextOrder = calRateNextOrder(symbol2OrderRunning.get(symbol));
                if (Utils.rateOf2Double(ticker.priceClose, symbol2OrderRunning.get(symbol).tickerOpen.priceClose) < rateNextOrder) {
                    createOrderBUY(ticker, levelChange);
                }
            }
            if (time % Utils.TIME_DAY == 0) {
                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, true);
            } else {
                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
            }
        }
        BudgetManagerSimple.getInstance().updateBalance(tickers.get(tickers.size() - 1).startTime.longValue(),
                allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
        // add all order running to done
        for (
                List<OrderTargetInfoTest> orderRunning : symbol2OrdersEntry.values()) {
            for (OrderTargetInfoTest orderInfo : orderRunning) {
                orderInfo.maxPrice = symbol2OrderRunning.get(orderInfo.symbol).maxPrice;
                orderInfo.lastPrice = symbol2OrderRunning.get(orderInfo.symbol).lastPrice;
                orderInfo.priceTP = orderInfo.lastPrice;
                orderInfo.minPrice = symbol2OrderRunning.get(orderInfo.symbol).minPrice;
                orderInfo.timeUpdate = symbol2OrderRunning.get(orderInfo.symbol).timeUpdate;
                allOrderDone.put(-orderInfo.timeUpdate + allOrderDone.size(), orderInfo);
            }
        }

        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-"
                + Configs.TIME_AFTER_ORDER_2_SL, allOrderDone);
        Storage.writeObject2File("storage/orderRunning.data", symbol2OrderRunning);
        Storage.writeObject2File("storage/BalanceIndex.data", BudgetManagerSimple.getInstance().balanceIndex);
        BudgetManagerSimple.getInstance().printBalanceIndex();

    }

    private Double calRateNextOrder(OrderTargetInfoTest order) {
        double rate = -0.01;
        Double rateBudget = order.calMargin() / BudgetManagerSimple.getInstance().getBudget();
        return rate * rateBudget;
    }


    public void initData() throws IOException, ParseException {
        // clear Data Old
        allOrderDone = new TreeMap<>();
        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
            FileUtils.delete(new File(FILE_STORAGE_ORDER_DONE));
        }

    }

    private void startUpdateOldOrderTrading(String symbol, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
        if (orderMulti != null) {
            if (orderMulti.timeStart < ticker.startTime.longValue()) {
                orderMulti.updatePriceByKlineSimple(ticker);
                orderMulti.updateStatusNew();
                orderMulti.updateFundingFee(ticker.startTime.longValue() + Utils.TIME_MINUTE);
                if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                        || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                        || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                    List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
                    orders.get(0).time2FundingFee.putAll(orderMulti.time2FundingFee);
                    for (OrderTargetInfoTest order : orders) {
                        order.timeUpdate = orderMulti.timeUpdate;
                        order.status = orderMulti.status;
                        order.priceTP = orderMulti.priceTP;
                        order.maxPrice = orderMulti.maxPrice;
                        order.minPrice = orderMulti.minPrice;
                        allOrderDone.put(-order.timeUpdate + allOrderDone.size(), order);
                        LOG.info("Order done: {}\t{}\t{}\t{} -> {}\t{}%\t{}", order.side, order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart),
                                order.priceEntry, order.priceTP, Utils.formatPercent(Utils.rateOf2Double(order.priceTP, order.priceEntry)), order.status);
                        BudgetManagerSimple.getInstance().updatePnl(order);
                    }
                    if (orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-"
                                + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), allOrderDone);
                    }
                    symbol2OrdersEntry.remove(symbol);
                    symbol2OrderRunning.remove(symbol);

                } else {
                    orderMulti.updateTPSL();
                }
            }
        }
    }

    private OrderTargetInfoTest mergeOrder(List<OrderTargetInfoTest> orders, KlineObjectSimple ticker) {
        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        String symbol = orders.get(0).symbol;
        Double quantity = 0d;
        String priceEntry = "";
        Double margin = 0d;
        for (OrderTargetInfoTest orderInfo : orders) {
            time2Order.put(orderInfo.timeStart, orderInfo);
            margin += orderInfo.priceEntry * orderInfo.quantity;
            quantity += orderInfo.quantity;
            priceEntry += orderInfo.priceEntry + "-";
        }
        double entry = margin / quantity;
        OrderTargetInfoTest orderResult = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry,
                null, quantity, BudgetManagerSimple.getInstance().getLeverage(),
                time2Order.lastEntry().getValue().symbol,
                time2Order.lastEntry().getKey(),
                time2Order.lastEntry().getKey(), orders.get(0).side);
        orderResult.minPrice = ticker.priceClose;
        orderResult.lastPrice = ticker.priceClose;
        orderResult.maxPrice = ticker.priceClose;
        orderResult.tickerOpen = time2Order.lastEntry().getValue().tickerOpen;
        orderResult.marketLevelChange = time2Order.lastEntry().getValue().marketLevelChange;

        if (orders.size() > 2) {
            LOG.info("Merger orders of {}: {} -> {}", orders.get(0).symbol, priceEntry, orderResult.priceEntry);
        }
        return orderResult;
    }


    public void createOrderBUY(KlineObjectSimple ticker, MarketLevelChange levelChange) {
        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();


        if (levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
                || levelChange.equals(MarketLevelChange.SMALL_UP)
                || levelChange.equals(MarketLevelChange.TINY_DOWN)
                || levelChange.equals(MarketLevelChange.TINY_UP)
                || levelChange.equals(MarketLevelChange.BIG_UP)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP)
                || levelChange.equals(MarketLevelChange.SMALL_DOWN)
        ) {
            if (calMarginRunning(symbol) < BudgetManagerSimple.getInstance().getBudget()) {
                budget = budget / 2;
            } else {
                budget = budget / 6;
            }
        }
        if (calMarginRunning(symbol) > 3 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 2;
        }
        if (calMarginRunning(symbol) > 5 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 2;
        }
        if (calMarginRunning(symbol) > 10 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 2;
        }
        if (calMarginRunning(symbol) > 15 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 2;
        }
        if (calMarginRunning(symbol) > 20 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 2;
        }
        if (calMarginRunning(symbol) > 25 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 2;
        }
        if (calMarginRunning() > 30 * BudgetManagerSimple.getInstance().getBudget()
        ) {
            if (levelChange.equals(MarketLevelChange.BIG_DOWN)
                    || levelChange.equals(MarketLevelChange.MEDIUM_DOWN)) {
                budget = budget / 4;
            } else {
                return;
            }
        }

        String log = OrderSide.BUY + " " + symbol + " entry: " + entry +
                " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantityTest(budget, leverage, entry, symbol);

        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
            Double minBtcTrade = 0.001;
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
        order.rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
        order.ordersRunning = counterOrderRunning();
        order.unProfitTotal = BudgetManagerSimple.getInstance().calUnrealizedProfitMin(symbol2OrderRunning.values());
        order.slTotal = BudgetManagerSimple.getInstance().calProfitLossMax(symbol2OrderRunning.values());
        order.marginRunning = BudgetManagerSimple.getInstance().calPositionMargin(symbol2OrderRunning.values());
        order.marginRealRunning = BudgetManagerSimple.getInstance().calPositionMarginReal(symbol2OrderRunning.values());

        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);
        LOG.info(log);
        symbol2OrdersEntry.put(symbol, orders);
        symbol2OrderRunning.put(symbol, mergeOrder(orders, ticker));

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
            if (order.priceSL == null || order.priceSL < order.priceEntry) {
                marginTotal += order.calMargin();
            }
        }
        return marginTotal;
    }


    private Double calMarginRunning(String symbol) {
        Double marginTotal = 0d;
        OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
        if (order != null) {
            return order.calMargin();
        }
        return marginTotal;
    }

    private Set<String> getSymbolRunning(MarketLevelChange level) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.marketLevelChange.equals(level) &&
                    order.timeUpdate - order.timeStart < 30 * Utils.TIME_MINUTE
            ) {
                hashSet.add(order.symbol);
            }
        }
        return hashSet;
    }

    private Set<String> getSymbolLockByMargin(Long time) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            int rateBudgetMax = 2;
            if (order.calMargin() >= BudgetManagerSimple.getInstance().getBudget() * rateBudgetMax) {
                hashSet.add(order.symbol);
            }
        }
        return hashSet;
    }

    private Set<String> getSymbolLockBySide(OrderSide side) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.side.equals(side)) {
                hashSet.add(order.symbol);
            }
        }
        return hashSet;
    }
}
