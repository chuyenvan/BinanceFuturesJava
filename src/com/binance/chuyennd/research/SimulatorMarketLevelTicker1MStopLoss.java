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
public class SimulatorMarketLevelTicker1MStopLoss {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorMarketLevelTicker1MStopLoss.class);
    public static final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";
    public static final String FILE_STORAGE_ORDER_ENTRIES = "storage/OrderEntries.data";

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;

    public String TIME_RUN = Configs.getString("TIME_RUN");
    public Map<Long, List<OrderTargetInfoTest>> time2Entries = new HashMap<>();

    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry = new ConcurrentHashMap();
    public ConcurrentHashMap<String, OrderTargetInfoTest> symbol2OrderRunning = new ConcurrentHashMap();

    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
        test.initData();
        if (new File(FILE_STORAGE_ORDER_ENTRIES).exists()) {
            LOG.info("Run with mode not init entry!");
            test.simulatorNotInitEntry(FILE_STORAGE_ORDER_ENTRIES);
        } else {
            LOG.info("Run with mode init entry!");
            test.simulatorWithInitEntry();
        }
    }

    public void runAOrder(String symbol, String time, OrderSide side) {
        MarketLevelChange levelChange = MarketLevelChange.SMALL_DOWN_15M;
        try {
            long startTime = Utils.sdfFileHour.parse(time).getTime();
            List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
            if (side.equals(OrderSide.BUY)) {
                createOrderBUY(symbol, tickers.get(0), levelChange, null, null);
            } else {
//                createOrderSELL(symbol, tickers.get(0), levelChange, null);
            }
//            levelChange = MarketLevelChange.SMALL_DOWN_15M;
//            createOrderBUY(symbol, tickers.get(1), levelChange, null, null);
//            levelChange = MarketLevelChange.SMALL_DOWN_15M;
//            createOrderBUY(symbol, tickers.get(2), levelChange, null, null);
            while (true) {
                for (KlineObjectSimple ticker : tickers) {
                    if (symbol2OrderRunning.isEmpty()) {
                        break;
                    }
                    startUpdateOldOrderTrading(symbol, ticker);
                    BudgetManagerSimple.getInstance().updateBalance(ticker.startTime.longValue(), allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                }
                for (OrderTargetInfoTest order : allOrderDone.values()) {
                    LOG.info("{} {} {} {} {} -> {} {}%", Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate),
                            order.side, order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart),
                            order.priceEntry, order.priceTP, Utils.formatDouble(Utils.rateOf2Double(order.priceTP, order.priceEntry) * 100, 3));
                }
                if (symbol2OrderRunning.isEmpty()) {
                    break;
                }
                startTime = tickers.get(tickers.size() - 1).startTime.longValue();
                tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    public void simulatorWithInitEntry(String... inputs) throws ParseException {
        Long timeWriteData = null;
        if (inputs.length > 1) {
            TIME_RUN = inputs[0];
            timeWriteData = Utils.sdfFileHour.parse(inputs[1]).getTime();
        }
        LOG.info("TimeWriteData: {}", timeWriteData);
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();

        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
//                LOG.info("Read file ticker: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
//                        if (time == Utils.sdfFileHour.parse("20241106 14:42").getTime()) {
//                            System.out.println("Debug");
//                        }
                        Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                        Map<String, Double> symbol2MaxPrice = new HashMap<>();
                        Map<String, Double> symbol2MinPrice = new HashMap<>();
                        Set<String> symbolScam = new HashSet<>();
                        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                            String symbol = entry1.getKey();
                            if (Constants.diedSymbol.contains(symbol)) {
                                continue;
                            }

                            KlineObjectSimple ticker = entry1.getValue();
                            // update order Old
                            startUpdateOldOrderTrading(symbol, ticker);

                            if (!Utils.isTickerAvailable(ticker)) {
                                continue;
                            }
                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                            if (tickers == null) {
                                tickers = new ArrayList<>();
                                symbol2LastTickers.put(symbol, tickers);
                            }
                            tickers.add(ticker);
                            if (tickers.size() > 400) {
                                for (int i = 0; i < 100; i++) {
                                    tickers.remove(0);
                                }
                            }
                            Double priceMax = null;
                            Double minPrice = null;
                            for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                                int index = tickers.size() - i - 1;
                                if (index >= 0) {
                                    KlineObjectSimple kline = tickers.get(index);
                                    if (Math.abs(Utils.rateOf2Double(kline.priceClose, kline.priceOpen)) > Configs.RATE_TICKER_MAX_SCAN_ORDER) {
                                        symbolScam.add(symbol);
                                    }
                                    if (priceMax == null || priceMax < kline.maxPrice) {
                                        priceMax = kline.maxPrice;
                                    }
                                    if (minPrice == null || minPrice > kline.minPrice) {
                                        minPrice = kline.minPrice;
                                    }
                                }
                            }
                            symbol2MaxPrice.put(symbol, priceMax);
                            symbol2MinPrice.put(symbol, minPrice);
                        }
                        MarketDataObject marketData;
                        marketData = MarketBigChangeDetectorTest.calMarketData(symbol2Ticker, symbol2MaxPrice, symbol2MinPrice);
                        if (timeWriteData != null && timeWriteData.equals(time)) {
                            String fileName = "storage/data/rateMax15M/" + Utils.normalizeDateYYYYMMDD(time)
                                    + "/" + time + "_test";
                            Storage.writeObject2File(fileName, marketData.rate2Max);
                            fileName = "storage/data/rateDown1M/" + Utils.normalizeDateYYYYMMDD(time)
                                    + "/" + time + "_test";
                            Storage.writeObject2File(fileName, marketData.rateDown2Symbols);
                            LOG.info("Finish 2 write data! {}", fileName);
                            System.exit(1);
                        }
//                        Set<String> symbolLocked = getSymbolLocked();
//                        LOG.info("Check level market: {} DownAvg: {}% UpAvg:{}% DownAvg15M:{}%  UpAvg15M:{}% btcRate: {}% btcRate15M: {}%",
//                                Utils.normalizeDateYYYYMMDDHHmm(time),
//                                Utils.formatDouble(marketData.rateDownAvg * 100, 3), Utils.formatDouble(marketData.rateUpAvg * 100, 3),
//                                Utils.formatDouble(marketData.rateDown15MAvg * 100, 3), Utils.formatDouble(marketData.rateUp15MAvg * 100, 3),
//                                Utils.formatDouble(marketData.rateBtc * 100, 3), Utils.formatDouble(marketData.rateBtcDown15M * 100, 3));
                        if (marketData != null) {
                            MarketLevelChange levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                                    marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg, marketData.rateUp15MAvg,
                                    marketData.rateBtcDown15M);
                            if (levelChange != null) {
                                Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                                if (
                                        levelChange.equals(MarketLevelChange.SMALL_DOWN)
                                                || levelChange.equals(MarketLevelChange.SMALL_UP)
                                                || levelChange.equals(MarketLevelChange.TINY_DOWN)
                                                || levelChange.equals(MarketLevelChange.TINY_UP)
                                ) {
                                    numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL / 2;
                                }
                                List<String> symbol2BUY = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(marketData.rate2Max,
                                        numberOrder, symbol2Ticker, null);
                                symbol2BUY = addSpecialSymbol(symbol2BUY, levelChange, symbol2Ticker);
                                LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2BUY);
                                // check create order new
                                for (String symbol : symbol2BUY) {
                                    KlineObjectSimple ticker = entry.getValue().get(symbol);
                                    createOrderBUY(symbol, ticker, levelChange, marketData, null);
                                }

                            } else {
                                levelChange = MarketBigChangeDetectorTest.getMarketStatus15M(marketData.rateDown15MAvg,
                                        marketData.rateUp15MAvg, marketData.rateBtcDown15M);
                                if (levelChange != null) {
                                    List<String> symbol2BUY = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(marketData.rate2Max,
                                            Configs.NUMBER_ENTRY_EACH_SIGNAL / 2, symbol2Ticker, null);

                                    LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2BUY);
                                    // check create order new
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = entry.getValue().get(symbol);
                                        createOrderBUY(symbol, ticker, levelChange, marketData, null);
                                    }

                                }
//                                 btc reverse
                                List<KlineObjectSimple> btcTickers = symbol2LastTickers.get(Constants.SYMBOL_PAIR_BTC);
                                if (MarketBigChangeDetectorTest.isBtcReverseVolume(btcTickers)
                                        && marketData.rateDown15MAvg <= -0.018
                                        && marketData.rateBtcDown15M <= -0.007
                                ) {
                                    levelChange = MarketLevelChange.BTC_REVERSE;
                                    List<String> symbol2BUY = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(marketData.rate2Max,
                                            Configs.NUMBER_ENTRY_EACH_SIGNAL, symbol2Ticker, null);
                                    // check create order new
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = entry.getValue().get(symbol);
                                        createOrderBUY(symbol, ticker, levelChange, marketData, null);
                                    }
                                }
                                // BTC trend reverse
                                if (MarketBigChangeDetectorTest.isBtcTrendReverse(symbol2LastTickers.get(Constants.SYMBOL_PAIR_BTC))) {
                                    levelChange = MarketLevelChange.BTC_TREND_REVERSE;
                                    ArrayList<String> symbol2BUY = new ArrayList<>();
                                    symbol2BUY.add(Constants.SYMBOL_PAIR_BTC);
                                    symbol2BUY.add(Constants.SYMBOL_PAIR_BNB);
                                    symbol2BUY.add(Constants.SYMBOL_PAIR_XRP);
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = entry.getValue().get(symbol);
                                        createOrderBUY(symbol, ticker, levelChange, marketData, null);
                                    }

                                }
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

        String reportMinProfit = statisticResult(allOrderDone);
        LOG.info("Update-{}-{} {}", Configs.TIME_AFTER_ORDER_2_SL, BudgetManagerSimple.getInstance().levelRun, reportMinProfit);
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-"
                + Configs.TIME_AFTER_ORDER_2_SL + "-" + Configs.RATE_TICKER_MAX_SCAN_ORDER, allOrderDone);
        Storage.writeObject2File("storage/orderRunning.data", symbol2OrderRunning);
        Storage.writeObject2File("storage/BalanceIndex.data", BudgetManagerSimple.getInstance().balanceIndex);
        Storage.writeObject2File(FILE_STORAGE_ORDER_ENTRIES, time2Entries);
        BudgetManagerSimple.getInstance().printBalanceIndex();
    }


    private void simulatorNotInitEntry(String fileName) throws ParseException {

        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<Long, List<OrderTargetInfoTest>> time2Entries = (Map<Long, List<OrderTargetInfoTest>>) Storage.readObjectFromFile(fileName);
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
                                createOrderBUY(order.symbol, ticker, order.marketLevelChange, order.marketData, null);
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

        String reportMinProfit = statisticResult(allOrderDone);
        LOG.info("Update-{}-{} {}", Configs.TIME_AFTER_ORDER_2_SL, BudgetManagerSimple.getInstance().levelRun, reportMinProfit);
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-"
                + Configs.TIME_AFTER_ORDER_2_SL + "-" + Configs.RATE_TICKER_MAX_SCAN_ORDER, allOrderDone);
        Storage.writeObject2File("storage/orderRunning.data", symbol2OrderRunning);
        BudgetManagerSimple.getInstance().printBalanceIndex();
    }

    private Set<String> getSymbolLocked() {
        Set<String> hashSet = new HashSet<>();
//        for (String symbol : symbol2OrdersEntry.keySet()) {
//            OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
//            if (orderMulti != null) {
////                if (orderMulti.calMargin() >= 5 * BudgetManagerSimple.getInstance().getBudget()
////                        && orderMulti.calRateLoss() < -0) {
////                    hashSet.add(symbol);
////                }
//                if (orderMulti.calRateLoss() < -0.1) {
//                    hashSet.add(symbol);
//                }
//            }
//        }
        return hashSet;
    }


    private List<String> addSpecialSymbol(List<String> symbol2BUY, MarketLevelChange levelChange,
                                          Map<String, KlineObjectSimple> symbol2Ticker) {
        if (levelChange != null && (levelChange.equals(MarketLevelChange.BIG_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN))
        ) {
            for (String symbol : Constants.specialSymbol) {
                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                if (ticker != null && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.015) {
                    symbol2BUY.add(symbol);
                }
            }
        }
        if (levelChange != null
                && (levelChange.equals(MarketLevelChange.BIG_UP)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP)
                || levelChange.equals(MarketLevelChange.SMALL_UP)
        )) {
            symbol2BUY.add(Constants.SYMBOL_PAIR_BTC);
            symbol2BUY.add(Constants.SYMBOL_PAIR_BNB);
            symbol2BUY.add(Constants.SYMBOL_PAIR_XRP);
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

    private Double calRateLoss(OrderTargetInfoTest order) {
        Double rate = 0d;
        if (order != null) {
            return order.calRateLoss();
        }
        return rate;
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
                null, quantity, BudgetManagerSimple.getInstance().getLeverage(symbol),
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


    public void createOrderBUY(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange,
                               MarketDataObject marketData, Double maxPrice15M) {

        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage(symbol);
        Double marginRunning = calMarginRunning();
        if (levelChange.equals(MarketLevelChange.BIG_UP)
                || levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            if (!Constants.specialSymbol.contains(symbol)) {
                budget = budget * 2;
            }
        }
        if (marginRunning <= 30 * BudgetManagerSimple.getInstance().getBudget()
                && (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP))
        ) {
            if (!Constants.specialSymbol.contains(symbol)) {
                budget = budget * 2;
            }
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                || levelChange.equals(MarketLevelChange.SMALL_UP)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                || levelChange.equals(MarketLevelChange.TINY_DOWN)
        ) {
            budget = budget;
            if (Constants.specialSymbol.contains(symbol)) {
                budget = budget / 2;
            }
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                || levelChange.equals(MarketLevelChange.TINY_UP)
                || levelChange.equals(MarketLevelChange.TINY_DOWN_15M)
        ) {
            budget = budget / 2;
        }

        if (levelChange.equals(MarketLevelChange.SMALL_UP_15M)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP_15M)
                || levelChange.equals(MarketLevelChange.BTC_REVERSE)
                || levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
        ) {
            budget = budget / 6;
        }

        if (levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)) {
            if (calMarginRunning(symbol) < BudgetManagerSimple.getInstance().getBudget() / 2) {
                budget = budget * 2;
            }
        }

        if (marginRunning < 10 * BudgetManagerSimple.getInstance().getBudget()) {
            if (levelChange.equals(MarketLevelChange.TINY_DOWN)
                    || levelChange.equals(MarketLevelChange.TINY_UP)
                    || levelChange.equals(MarketLevelChange.SMALL_DOWN)
                    || levelChange.equals(MarketLevelChange.SMALL_UP)
            ) {
                budget = budget * 2;
            }
        }

        if (marginRunning > 40 * BudgetManagerSimple.getInstance().getBudget()) {
            if (levelChange.equals(MarketLevelChange.BIG_UP)
                    || levelChange.equals(MarketLevelChange.BIG_DOWN)
                    || levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                    || levelChange.equals(MarketLevelChange.MEDIUM_UP)
            ) {
                budget = budget / 2;
            }
        }
        if (marginRunning > 50 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 2;
        }
        if (marginRunning > 60 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 4;
        }


        String log = OrderSide.BUY + " " + symbol + " entry: " + entry +
                " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);

        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
            if (quantity < 0.002) {
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
        order.ordersRunning = counterOrderRunning();
        order.unProfitTotal = BudgetManagerSimple.getInstance().calUnrealizedProfitMin(symbol2OrderRunning.values());
        order.slTotal = BudgetManagerSimple.getInstance().calProfitLossMax(symbol2OrderRunning.values());
        order.marginRunning = BudgetManagerSimple.getInstance().calPositionMargin(symbol2OrderRunning.values());
        if (marketData != null) {
            marketData.rateDown2Symbols.clear();
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
        symbol2OrderRunning.put(symbol, mergeOrder(orders, ticker));
        // update list entry to write file
        List<OrderTargetInfoTest> entries = time2Entries.get(order.timeStart);
        if (entries == null) {
            entries = new ArrayList<>();
        }
        entries.add(order);
        time2Entries.put(order.timeStart, entries);

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

    private Double calMarginRunning(String symbol) {
        Double marginTotal = 0d;
        OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
        if (order != null) {
            return order.calMargin();
        }
        return marginTotal;
    }

    private Set<String> getSymbolRunningBUYLoss() {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.calRateLoss() < 0) {
                hashSet.add(order.symbol);
            }
        }
        return hashSet;
    }

    private Set<String> getSymbolRunningBUYLoss(Double rateLoss) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.side.equals(OrderSide.BUY)) {
                if (order.calRateLoss() < rateLoss) {
                    hashSet.add(order.symbol);
                }
            }
        }
        return hashSet;
    }

    //    private Set<String> getSymbolLockByMargin(Integer rate) {
//        Set<String> hashSet = new HashSet<>();
//        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
//            if (order.side.equals(OrderSide.BUY)) {
//                if (order.calMargin() > BudgetManagerSimple.getInstance().getBudget() * rate) {
//                    hashSet.add(order.symbol);
//                }
//            }
//        }
//        return hashSet;
//    }
    private Set<String> getSymbolRunningSELLLoss(Double rateLoss) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.side.equals(OrderSide.SELL)) {
                if (order.calRateLoss() < rateLoss) {
                    hashSet.add(order.symbol);
                }
            }
        }
        return hashSet;
    }
}
