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
public class StatisticMarketLevelTicker1M {

    public static final Logger LOG = LoggerFactory.getLogger(StatisticMarketLevelTicker1M.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/" + StatisticMarketLevelTicker1M.class.getSimpleName() + ".data";


    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;

    public final String TIME_RUN = Configs.getString("TIME_RUN");
        public ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning = new ConcurrentHashMap();
    public static final String LABLE_TOP_TICKER_DOWN = "LABLE_TOP_TICKER_DOWN";
    public static final String LABLE_TOP_4H_DOWN = "LABLE_TOP_4H_DOWN";
    public static final String LABLE_TOP_20D_DOWN = "LABLE_TOP_20D_DOWN";
    public static final String LABLE_TOP_20D_UP = "LABLE_TOP_20D_UP";
    public ConcurrentHashMap<String, ConcurrentHashMap<String, OrderTargetInfoTest>> lable2OrdersRunning = new ConcurrentHashMap();
    public ConcurrentHashMap<Long, MarketLevelChange> time2MarketLevelChange = new ConcurrentHashMap<>();


    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        StatisticMarketLevelTicker1M test = new StatisticMarketLevelTicker1M();
        test.initData();
        test.simulatorAllSymbol();

//        test.debugAOrder();

        // for test number order/signal
//        for (Integer j = 0; j < 5; j++) {
//            for (Integer i = 0; i < 5; i++) {
////            Configs.NUMBER_ENTRY_EACH_SIGNAL = numberOrder;
//                Configs.TIME_AFTER_ORDER_2_TP = j * 5 + 1;
//                Configs.TIME_AFTER_ORDER_2_SL = i * 5 + 1;
//                BudgetManagerSimple.getInstance().updateBudget(null);
//                BudgetManagerSimple.getInstance().resetHistory();
////            LOG.info("Set number order and update budget: {} orders -> budget: {}", Configs.NUMBER_ENTRY_EACH_SIGNAL,
////                    BudgetManagerSimple.getInstance().getBudget());
//                test.initData();
//                test.simulatorAllSymbol();
//                Thread.sleep(Utils.TIME_MINUTE);
//            }
//        }


    }

    public void debugAOrder() {
        String symbol = "BIGTIMEUSDT";
        MarketLevelChange levelChange = MarketLevelChange.MEDIUM_DOWN;
        try {
            long startTime = Utils.sdfFileHour.parse("20240906 22:19").getTime();
            List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
            createOrderBUYTarget(symbol, tickers.get(0), levelChange);
            for (KlineObjectSimple ticker : tickers) {
                LOG.info("Process time: {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
                startUpdateOldOrderTrading(symbol, ticker);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    private void simulatorAllSymbol() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        String fileMarketChangeLevelData = "target/time_trade_market_" + Utils.sdfFile.format(new Date()) + ".data";
        Map<String, KlineObjectSimple> symbol2LastTicker = new HashMap<>();
        Map<Long, MarketDataObject> timeTradeMarket = new HashMap<>();
        Boolean modeRunWithLevelFile = false;
        if (new File(fileMarketChangeLevelData).exists()) {
            modeRunWithLevelFile = true;
            timeTradeMarket = (Map<Long, MarketDataObject>) Storage.readObjectFromFile(fileMarketChangeLevelData);

        }
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
                        // update order Old
                        for (ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning : lable2OrdersRunning.values()) {
                            for (String symbol : orderRunning.keySet()) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                startUpdateOldOrderTrading(symbol, ticker);
                            }
                        }
                        MarketDataObject marketData;
                        if (modeRunWithLevelFile) {
                            marketData = timeTradeMarket.get(time);
                        } else {
                            marketData = calMarketData(symbol2Ticker, symbol2LastTicker);
                        }
                        if (marketData != null) {
                            MarketLevelChange levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                                    marketData.rateUpAvg, marketData.rateBtc);
                            if (levelChange != null) {
                                timeTradeMarket.put(time, marketData);
                                time2MarketLevelChange.put(time, levelChange);
                                List<String> symbol2Trade = marketData.symbolsTopDown;
                                LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2Trade);
                                if (
                                        levelChange.equals(MarketLevelChange.SMALL_DOWN)
                                                || levelChange.equals(MarketLevelChange.SMALL_UP)
                                ) {
                                    while (symbol2Trade.size() > Configs.NUMBER_ENTRY_EACH_SIGNAL / 2) {
                                        symbol2Trade.remove(symbol2Trade.size() - 1);
                                    }
                                }
                                // check create order new
                                for (String symbol : marketData.symbolsTopDown) {
                                    orderRunning = lable2OrdersRunning.get(LABLE_TOP_4H_DOWN);
                                    KlineObjectSimple ticker = entry.getValue().get(symbol);
                                    if (orderRunning.containsKey(symbol)) {
                                        LOG.info("Error symbol 2 trade: {} {}", Utils.normalizeDateYYYYMMDDHHmm(time),
                                                Utils.toJson(orderRunning.get(symbol)));
                                    } else {
                                        createOrderBUYTarget(symbol, ticker, levelChange);
                                    }
                                }
                            } else {
//                            if (orderRunning.isEmpty()) {
//                                if (marketData.rateDownWithLastTicker < -0.014) {
//                                    levelChange = MarketLevelChange.SMALL_DOWN_EXTEND;
//                                }
//                                if (marketData.rateDownWithLastTicker > 0.015) {
//                                    levelChange = MarketLevelChange.SMALL_UP_EXTEND;
//                                }
//                                if (levelChange != null) {
//                                    List<String> symbol2Trade = marketData.symbolsTopDown;
//                                    LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2Trade);
//                                    while (symbol2Trade.size() > Configs.NUMBER_ENTRY_EACH_SIGNAL / 2) {
//                                        symbol2Trade.remove(symbol2Trade.size() - 1);
//                                    }
//                                    // check create order new
//                                    for (String symbol : symbol2Trade) {
//                                        KlineObjectSimple ticker = entry.getValue().get(symbol);
//                                        if (orderRunning.containsKey(symbol)) {
//                                            LOG.info("Error symbol 2 trade: {} {}", Utils.normalizeDateYYYYMMDDHHmm(time),
//                                                    Utils.toJson(orderRunning.get(symbol)));
//                                        } else {
//                                            createOrderBUYTarget(symbol, ticker, levelChange);
//                                        }
//                                    }
//                                }
//                            }
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
            } catch (Exception e) {
                e.printStackTrace();
            }
            Long finalStartTime1 = startTime;
//            buildReport(finalStartTime1);
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
        Long finalStartTime = startTime;
        buildReport(finalStartTime);
        BudgetManagerSimple.getInstance().printBalanceIndex();
        Storage.writeObject2File(fileMarketChangeLevelData, timeTradeMarket);
//        exitWhenDone();

    }


    private MarketDataObject calMarketData(Map<String, KlineObjectSimple> symbol2Ticker, Map<String, KlineObjectSimple> symbol2LastTicker) {
        TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateLast2Symbol = new TreeMap<>();
        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            if (Constants.specialSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = entry1.getValue();
            if (Utils.isTickerAvailable(ticker)) {
                Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                rateDown2Symbols.put(rateChange, symbol);
                rateUp2Symbols.put(-rateChange, symbol);
                KlineObjectSimple lastTicker = symbol2LastTicker.get(symbol);
                if (lastTicker != null) {
                    rateLast2Symbol.put(Utils.rateOf2Double(ticker.priceClose, lastTicker.priceOpen), symbol);
                }
            }
        }
        // TODO test với rate with max 20d ago
        KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
        Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
        Double rateChangeDownAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateDown2Symbols, 50);
        Double rateChangeLastDownAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateLast2Symbol, 50);
        Double rateChangeUpAvg = -MarketBigChangeDetectorTest.calRateLossAvg(rateUp2Symbols, 50);
        List<String> symbolsTopDown = MarketBigChangeDetectorTest.getTopSymbolSimple(rateDown2Symbols,
                Configs.NUMBER_ENTRY_EACH_SIGNAL, orderRunning.keySet());

        if (symbolsTopDown.size() != Configs.NUMBER_ENTRY_EACH_SIGNAL) {
            LOG.info("Error get symbol 2 trade: {} {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                    symbol2Ticker.size(), rateDown2Symbols.size(), symbolsTopDown.size(),
                    Utils.toJson(symbolsTopDown), Utils.toJson(orderRunning.keySet()));
        }
        return new MarketDataObject(rateChangeDownAvg, rateChangeUpAvg, rateChangeLastDownAvg, btcRateChange, btcTicker.totalUsdt,
                null, symbolsTopDown);
    }


    private Double calRateLossOrderRunningWithLevel(MarketLevelChange levelChange) {
        Double rateLossTotal = 0d;
        int counter = 0;
        for (OrderTargetInfoTest order : orderRunning.values()) {
            try {
                if (order.marketLevelChange.equals(levelChange)) {
                    rateLossTotal += order.calRateLoss();
                    counter++;
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        int numberCheck = Configs.NUMBER_ENTRY_EACH_SIGNAL;
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                || levelChange.equals(MarketLevelChange.SMALL_UP)) {
            numberCheck = Configs.NUMBER_ENTRY_EACH_SIGNAL / 2;
        }
        if (counter < numberCheck) {
            return 0d;
        }
        return rateLossTotal;
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
        allOrderDone = new ConcurrentHashMap<>();
        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
            FileUtils.delete(new File(FILE_STORAGE_ORDER_DONE));
        }
        lable2OrdersRunning.put(LABLE_TOP_TICKER_DOWN, new ConcurrentHashMap<>());
        lable2OrdersRunning.put(LABLE_TOP_4H_DOWN, new ConcurrentHashMap<>());
        lable2OrdersRunning.put(LABLE_TOP_20D_DOWN, new ConcurrentHashMap<>());
        lable2OrdersRunning.put(LABLE_TOP_20D_UP, new ConcurrentHashMap<>());
//        if (new File(FILE_STORAGE_MARKET_DATA).exists()) {
//            time2MarketData = (ConcurrentHashMap<Long, MarketDataObject>) Storage.readObjectFromFile(FILE_STORAGE_MARKET_DATA);
//            LOG.info("Market data:{}", time2MarketData.size());
//        } else {
//            time2MarketData = new ConcurrentHashMap<>();
//        }

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

    public void buildReport(Long currentTime) {
        StringBuilder reportRunning = calReportRunning(currentTime);
        if (allOrderDone == null) {
            allOrderDone = new ConcurrentHashMap<>();
        }
        reportRunning.append(" Success: ").append(allOrderDone.size() * Configs.RATE_TARGET * 100).append("%");
        int totalBuy = 0;
        int totalSell = 0;
        int totalDca = 0;
        int totalSL = 0;
        Map<String, Integer> symbol2Counter = new HashMap<>();
        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        for (OrderTargetInfoTest order : allOrderDone.values()) {
//            LOG.info("{} {} {} {} {} ", order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), order.priceEntry, order.priceTP
//                    , order.dcaLevel);
            time2Order.put(order.timeStart, order);
            Integer counter = symbol2Counter.get(order.symbol);
            if (counter == null) {
                counter = 0;
            }
            counter++;
            symbol2Counter.put(order.symbol, counter);
            if (order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                totalSL++;
            }
            if (order.side.equals(OrderSide.BUY)) {
                totalBuy++;
            } else {
                totalSell++;
            }
            if (order.dynamicTP_SL != null && order.dynamicTP_SL > 0) {
                totalDca++;
            }
        }
        List<String> lines = new ArrayList<>();
        for (Map.Entry<Long, OrderTargetInfoTest> entry : time2Order.entrySet()) {
            Long time = entry.getKey();
            OrderTargetInfoTest order = entry.getValue();
            lines.add(Utils.normalizeDateYYYYMMDDHHmm(time) + "," + order.priceEntry + "," + order.priceTP + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate));
        }
        try {
            FileUtils.writeLines(new File("target/allOrderDone.csv"), lines);
        } catch (IOException e) {
            e.printStackTrace();
        }
        reportRunning.append(" Buy: ").append(totalBuy * Configs.RATE_TARGET * 100).append("%");
        reportRunning.append(" Sell: ").append(totalSell * Configs.RATE_TARGET * 100).append("%");
        reportRunning.append(" SL: ").append(totalSL).append(" ");
        reportRunning.append(" dcaDone: ").append(totalDca).append(" ");
        reportRunning.append(" Running: ").append(orderRunning.size()).append(" orders");
        LOG.info(reportRunning.toString());
//        LOG.info(Utils.toJson(symbol2Counter));
//        Utils.sendSms2Telegram(reportRunning.toString());
    }

    private void startUpdateOldOrderTrading(String symbol, KlineObjectSimple ticker) {

        OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
        if (orderInfo != null) {
            if (orderInfo.timeStart < ticker.startTime.longValue()) {
                orderInfo.updatePriceByKlineSimple(ticker);
                orderInfo.updateStatusNew(ticker);
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


    public void createOrderBUYTarget(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange) {
        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
        if (levelChange.equals(MarketLevelChange.BIG_DOWN)
                || levelChange.equals(MarketLevelChange.BIG_UP)) {
            budget = budget * 2;
        }
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
        order.marketLevelChange = levelChange;
        orderRunning.put(symbol, order);
        BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());
        LOG.info(log);
    }

    private void createOrderSELL(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange) {
        Double entry = ticker.priceClose;
        Double rateTarget = Configs.RATE_TARGET;
        Double targetSL = Configs.RATE_STOP_LOSS * rateTarget;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        budget = budget * 2;
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
        Double priceTp = Utils.calPriceTarget(symbol, entry, OrderSide.SELL, rateTarget);
        Double priceSL = Utils.calPriceTarget(symbol, entry, OrderSide.BUY, targetSL);
        String log = OrderSide.SELL + " " + symbol + " entry: " + entry + " target: " + priceTp + " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.SELL);
        order.priceSL = priceSL;
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.marketLevelChange = levelChange;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        orderRunning.put(symbol, order);
        BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());
        LOG.info(log);
    }
}
