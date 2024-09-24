///*
// * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
// * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
// */
//package com.binance.chuyennd.bak;
//
//import com.binance.chuyennd.bigchange.market.MarketLevelChange;
//import com.binance.chuyennd.bigchange.statistic.data.DataManager;
//import com.binance.chuyennd.object.KlineObjectNumber;
//import com.binance.chuyennd.research.BudgetManagerSimple;
//import com.binance.chuyennd.research.BudgetManagerTest;
//import com.binance.chuyennd.research.OrderTargetInfoTest;
//import com.binance.chuyennd.trading.MarketBigChangeDetector;
//import com.binance.chuyennd.trading.OrderTargetStatus;
//import com.binance.chuyennd.utils.Configs;
//import com.binance.chuyennd.utils.Storage;
//import com.binance.chuyennd.utils.Utils;
//import com.binance.client.model.enums.OrderSide;
//import org.apache.commons.io.FileUtils;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//import java.io.File;
//import java.io.IOException;
//import java.text.ParseException;
//import java.util.*;
//import java.util.concurrent.ConcurrentHashMap;
//
///**
// * @author pc
// */
//public class SimulatorMarketLevelKLineSimpleStopLoss {
//
//    public static final Logger LOG = LoggerFactory.getLogger(SimulatorMarketLevelKLineSimpleStopLoss.class);
//    public final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";
//    public static final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
//    public static final Double RATE_TP_STOPLOSS = Configs.getDouble("RATE_TP_STOPLOSS");
//    public final Integer NUMBER_ENTRY_EACH_SIGNAL = Configs.getInt("NUMBER_ENTRY_EACH_SIGNAL");
//    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
//    public final String TIME_RUN = Configs.getString("TIME_RUN");
//    public ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning = new ConcurrentHashMap();
//    public ConcurrentHashMap<Long, MarketLevelChange> time2MarketLevelChange = new ConcurrentHashMap<>();
//
//
//    public static void main(String[] args) throws ParseException, IOException {
//        SimulatorMarketLevelKLineSimpleStopLoss test = new SimulatorMarketLevelKLineSimpleStopLoss();
//        test.initData();
//
//        test.simulatorAllSymbol();
//    }
//
//
//    private void simulatorAllSymbol() throws ParseException {
//        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
//        Map<String, List<KlineObjectNumber>> symbol2Tickers = new HashMap<>();
//        Map<String, KlineObjectNumber> symbol2LastTicker = new HashMap<>();
//
//        Boolean isStop = false;
//        //get data
//        while (true) {
//            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers;
//            try {
//                time2Tickers = DataManager.readData15mFromFile(startTime);
//                if (time2Tickers == null) {
//                    time2Tickers = new TreeMap<>();
//                    isStop = true;
//                }
//                for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
//                    Long time = entry.getKey();
//                    Map<String, KlineObjectNumber> symbol2Ticker = entry.getValue();
//                    // update order Old
//                    for (Map.Entry<String, KlineObjectNumber> entry1 : symbol2Ticker.entrySet()) {
//                        String symbol = entry1.getKey();
//                        KlineObjectNumber ticker = entry1.getValue();
//                        List<KlineObjectNumber> tickers = symbol2Tickers.get(symbol);
//                        if (tickers == null) {
//                            tickers = new ArrayList<>();
//                            symbol2Tickers.put(symbol, tickers);
//                        }
//                        tickers.add(ticker);
//                        if (tickers.size() < 20) {
//                            continue;
//                        }
//                        if (tickers.size() > 300) {
//                            for (int i = 0; i < 20; i++) {
//                                tickers.remove(0);
//                            }
//                        }
//                        startUpdateOldOrderTrading(symbol, ticker);
//
//                    }
//                    MarketLevelChange levelChange = MarketBigChangeDetector.detectLevelChange(entry.getValue());
//                    if (levelChange != null) {
//                        time2MarketLevelChange.put(time, levelChange);
//                        levelChange = changeLevelByHistory(time, levelChange);
//                        if (levelChange != null) {
//                            // dca when big down
//                            if (levelChange.equals(MarketLevelChange.BIG_DOWN)
//                                    || levelChange.equals(MarketLevelChange.MAYBE_BIG_DOWN_AFTER)
//                                    || levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
//                            ) {
//                                dcaAllOrderRunning();
//                            }
//                            int numberOrder = NUMBER_ENTRY_EACH_SIGNAL;
////                            if (levelChange.equals(MarketLevelChange.SMALL_UP)) {
////                                numberOrder = numberOrder / 2;
////                            }
//                            List<String> symbol2Trade = MarketBigChangeDetector.getTopSymbol2TradeWithRateChange(entry.getValue(), numberOrder);
////                            if (levelChange.equals(MarketLevelChange.MINI_DOWN_EXTEND)) {
////                                symbol2Trade = MarketBigChangeDetector.getTopSymbol2TradeWithRateMax(entry.getValue(), 3,
////                                        levelChange);
////                            }
//                            LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2Trade);
//                            // check create order new
//                            for (String symbol : symbol2Trade) {
//                                checkAndCreateOrderNew(symbol2Ticker.get(symbol), symbol, levelChange);
//                            }
//
//                        }
//                        symbol2LastTicker.putAll(symbol2Ticker);
//                    } else {
////                        // alt big change reverse
////                        TreeMap<Double, String> rateChange2Symbol = new TreeMap<>();
////                        TreeMap<Double, String> rateChange2SymbolExtend = new TreeMap<>();
////                        TreeMap<Double, String> rateChange2SymbolUnder5 = new TreeMap<>();
////                        List<String> symbolSellCouples = new ArrayList<>();
////                        MarketLevelChange orderMarketRunning = getOrderMarketLevelRunning();
////                        if (orderMarketRunning == null || orderMarketRunning.equals(MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND)) {
////
////
////                            for (Map.Entry<String, List<KlineObjectNumber>> entry1 : symbol2Tickers.entrySet()) {
////                                String symbol = entry1.getKey();
////                                List<KlineObjectNumber> tickers = entry1.getValue();
////                                if (tickers.size() < 100) {
////                                    continue;
////                                }
////                                if (MarketBigChangeDetectorTest.isSignalSELL(tickers, tickers.size() - 1)) {
////                                    symbolSellCouples.add(symbol);
////                                }
//                                List<Integer> altReverseStatus = MarketBigChangeDetectorTest.getSignalBuyAlt15M(tickers, tickers.size() - 1);
////                                KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
////                                if (Utils.isTickerAvailable(ticker)) {
////                                    if (altReverseStatus.contains(1)
////                                    ) {
////                                        rateChange2Symbol.put(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen), symbol);
////                                    }
////                                    if (altReverseStatus.contains(2)
////                                    ) {
////                                        rateChange2SymbolExtend.put(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen), symbol);
////                                    }
////                                    if (altReverseStatus.contains(3)
////                                    ) {
////                                        rateChange2SymbolUnder5.put(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen), symbol);
////                                    }
////                                }
////                            }
////                            List<KlineObjectNumber> btcTickers = symbol2Tickers.get(Constants.SYMBOL_PAIR_BTC);
////                            KlineObjectNumber btcStatistic24h = null;
////                            KlineObjectNumber lastBtcTicker = null;
////                            if (btcTickers != null) {
////                                btcStatistic24h = TickerFuturesHelper.extractKlineByNumberTicker(btcTickers, btcTickers.size() - 1, 96, 8);
////                                lastBtcTicker = btcTickers.get(btcTickers.size() - 1);
////                            }
////                            if (btcStatistic24h != null
////                                    && lastBtcTicker != null
////                                    && Utils.rateOf2Double(btcStatistic24h.minPrice, lastBtcTicker.minPrice) < -0.01) {
////                                if (rateChange2Symbol.size() >= 5) {
////                                    levelChange = MarketLevelChange.ALT_BIG_CHANGE_REVERSE;
////                                    int counter = 0;
////                                    for (Map.Entry<Double, String> entry2 : rateChange2Symbol.entrySet()) {
////                                        String symbol = entry2.getValue();
////                                        LOG.info("Alt: {} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange,
////                                                symbol, rateChange2Symbol.size());
////                                        checkAndCreateOrderNew(symbol2Ticker.get(symbol), symbol, levelChange);
////                                        counter++;
////                                        if (counter >= 6) {
////                                            break;
////                                        }
////                                    }
////                                } else {
////                                    if (orderRunning.isEmpty()) {
////                                        if (!rateChange2SymbolExtend.isEmpty()) {
////                                            levelChange = MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND;
////                                            int counter = 0;
////                                            for (Map.Entry<Double, String> entry2 : rateChange2SymbolExtend.entrySet()) {
////                                                String symbol = entry2.getValue();
////                                                LOG.info("Alt Reverse: {} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange,
////                                                        symbol, rateChange2SymbolExtend.size());
////                                                checkAndCreateOrderNew(symbol2Ticker.get(symbol), symbol, levelChange);
////                                                counter++;
////                                                if (counter >= 5) {
////                                                    break;
////                                                }
////                                            }
////                                        } else {
////                                            levelChange = MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND;
////                                            for (Map.Entry<Double, String> entry2 : rateChange2SymbolUnder5.entrySet()) {
////                                                if (orderRunning.size() < 3) {
////                                                    String symbol = entry2.getValue();
////                                                    LOG.info("Alt Sell: {} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange,
////                                                            symbol, rateChange2Symbol.size());
////                                                    checkAndCreateOrderNew(symbol2Ticker.get(symbol), symbol, levelChange);
////                                                }
////                                            }
////                                        }
////                                    }
////                                }
////                            }
////                        }
////                        levelChange = MarketLevelChange.ALT_SIGNAL_SELL;
////                        for (String symbol : symbolSellCouples) {
////                            LOG.info("Alt Sell: {} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange,
////                                    symbol, rateChange2Symbol.size());
////                            checkAndCreateOrderSELL(symbol2Ticker.get(symbol), symbol, levelChange);
////                        }
//                    }
//                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, orderRunning);
//                    BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());
//                }
//            } catch (Exception e) {
//                e.printStackTrace();
//            }
//            Long finalStartTime1 = startTime;
//            buildReport(finalStartTime1);
//            if (isStop) {
//                BudgetManagerSimple.getInstance().updateBalance(finalStartTime1, allOrderDone, orderRunning);
//                break;
//            }
//            startTime += Utils.TIME_DAY;
//        }
//        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
//        Long finalStartTime = startTime;
//        buildReport(finalStartTime);
//        BudgetManagerSimple.getInstance().printBalanceIndex();
//        exitWhenDone();
//
//    }
//
//    private void dcaAllOrderRunning() {
//        Set<String> symbols = orderRunning.keySet();
//        LOG.info("Check dca for: {} orders", symbols.size());
//        if (symbols.size() > 5) {
//            return;
//        }
//        for (String symbol : symbols) {
//            OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
//            if (orderInfo != null && orderInfo.side.equals(OrderSide.BUY)) {
//                orderInfo.quantity *= 2;
//                orderInfo.priceEntry = (orderInfo.priceEntry + orderInfo.lastPrice) / 2;
//                Double priceTp = Utils.calPriceTarget(orderInfo.symbol, orderInfo.priceEntry, OrderSide.BUY, RATE_TARGET);
//                orderInfo.priceTP = priceTp;
//                if (orderInfo.dynamicTP_SL == null) {
//                    orderInfo.dynamicTP_SL = 0;
//                }
//                orderInfo.dynamicTP_SL++;
//                orderRunning.put(symbol, orderInfo);
//                LOG.info("After dca {} entry: {} tp: {} quantity: {} {}",
//                        orderInfo.symbol, orderInfo.priceEntry, orderInfo.priceTP, orderInfo.quantity, Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeUpdate));
//                BudgetManagerTest.getInstance().updateInvesting();
//
//            }
//        }
//
//    }
//
//
////    private MarketLevelChange getOrderMarketLevelRunning() {
////        if (orderRunning.isEmpty()) {
////            return null;
////        }
////        MarketLevelChange level = MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND;
////        for (OrderTargetInfoTest order : orderRunning.values()) {
////            if (!order.marketLevelChange.equals(MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND)) {
////                level = MarketLevelChange.MULTI_LEVEL_MARKET_RUNNING;
////            }
////        }
////        return level;
////    }
//
//
//    private void exitWhenDone() {
//        try {
//            Thread.sleep(10 * Utils.TIME_SECOND);
//            System.exit(1);
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//    }
//
//    private void initData() throws IOException, ParseException {
//        // clear Data Old
//        allOrderDone = new ConcurrentHashMap<>();
//        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
//            FileUtils.delete(new File(FILE_STORAGE_ORDER_DONE));
//        }
//
//    }
//
//
//    public StringBuilder calReportRunning(Long currentTime) {
//        StringBuilder builder = new StringBuilder();
//        Double totalLoss = 0d;
//        Double totalBuy = 0d;
//        Double totalSell = 0d;
//        Integer dcaTotal = 0;
//        TreeMap<Double, OrderTargetInfoTest> pnl2OrderInfo = new TreeMap<>();
//        for (String symbol : orderRunning.keySet()) {
//            OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
//            if (orderInfo != null) {
//                Double pnl = orderInfo.calProfit();
//                pnl2OrderInfo.put(pnl, orderInfo);
//                if (orderInfo.dynamicTP_SL != null && orderInfo.dynamicTP_SL > 0) {
//                    dcaTotal++;
//                }
//            }
//        }
//        int counterLog = 0;
//        for (Map.Entry<Double, OrderTargetInfoTest> entry : pnl2OrderInfo.entrySet()) {
//            Double pnl = entry.getKey();
//            OrderTargetInfoTest orderInfo = entry.getValue();
//            Double ratePercent = orderInfo.calRateLoss() * 100;
//            totalLoss += ratePercent;
//            if (orderInfo.side.equals(OrderSide.BUY)) {
//                totalBuy += ratePercent;
//            } else {
//                totalSell += ratePercent;
//            }
//
//            if (counterLog < 105) {
//                counterLog++;
//                builder.append(Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart)).append(" ").
//                        append(Utils.normalizeDateYYYYMMDDHHmm(currentTime)).append(" margin:")
//                        .append(orderInfo.calMargin().longValue()).append(" ")
//                        .append(orderInfo.side).append(" ").append(orderInfo.symbol)
//                        .append(" ").append(" dcaLevel:").append(orderInfo.dynamicTP_SL).append(" ")
//                        .append(orderInfo.priceEntry).append("->").append(orderInfo.lastPrice).append(" ").
//                        append(ratePercent.longValue()).append("%").append(" ").append(pnl.longValue()).append("$").append("\n");
//            }
//        }
//
//        builder.append("Total: ").append(totalLoss.longValue()).append("%");
//        builder.append(" Buy: ").append(totalBuy.longValue()).append("%");
//        builder.append(" Sell: ").append(totalSell.longValue()).append("%");
//        builder.append(" dcaRunning: ").append(dcaTotal).append("%");
//        return builder;
//    }
//
//    public void buildReport(Long currentTime) {
//        StringBuilder reportRunning = calReportRunning(currentTime);
//        if (allOrderDone == null) {
//            allOrderDone = new ConcurrentHashMap<>();
//        }
//        reportRunning.append(" Success: ").append(allOrderDone.size() * RATE_TARGET * 100).append("%");
//        int totalBuy = 0;
//        int totalSell = 0;
//        int totalDca = 0;
//        int totalSL = 0;
//        Map<String, Integer> symbol2Counter = new HashMap<>();
//        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
//        for (OrderTargetInfoTest order : allOrderDone.values()) {
////            LOG.info("{} {} {} {} {} ", order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart), order.priceEntry, order.priceTP
////                    , order.dcaLevel);
//            time2Order.put(order.timeStart, order);
//            Integer counter = symbol2Counter.get(order.symbol);
//            if (counter == null) {
//                counter = 0;
//            }
//            counter++;
//            symbol2Counter.put(order.symbol, counter);
//            if (order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
//                totalSL++;
//            }
//            if (order.side.equals(OrderSide.BUY)) {
//                totalBuy++;
//            } else {
//                totalSell++;
//            }
//            if (order.dynamicTP_SL != null && order.dynamicTP_SL > 0) {
//                totalDca++;
//            }
//        }
//        List<String> lines = new ArrayList<>();
//        for (Map.Entry<Long, OrderTargetInfoTest> entry : time2Order.entrySet()) {
//            Long time = entry.getKey();
//            OrderTargetInfoTest order = entry.getValue();
//            lines.add(Utils.normalizeDateYYYYMMDDHHmm(time) + "," + order.priceEntry + "," + order.priceTP + "," + Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate));
//        }
//        try {
//            FileUtils.writeLines(new File("target/allOrderDone.csv"), lines);
//        } catch (IOException e) {
//            e.printStackTrace();
//        }
//        reportRunning.append(" Buy: ").append(totalBuy * RATE_TARGET * 100).append("%");
//        reportRunning.append(" Sell: ").append(totalSell * RATE_TARGET * 100).append("%");
//        reportRunning.append(" SL: ").append(totalSL).append(" ");
//        reportRunning.append(" dcaDone: ").append(totalDca).append(" ");
//        reportRunning.append(" Running: ").append(orderRunning.size()).append(" orders");
//        LOG.info(reportRunning.toString());
////        LOG.info(Utils.toJson(symbol2Counter));
////        Utils.sendSms2Telegram(reportRunning.toString());
//    }
//
//    private void startUpdateOldOrderTrading(String symbol, KlineObjectNumber ticker) {
//
//        OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
//        if (orderInfo != null) {
//            if (orderInfo.timeStart < ticker.startTime.longValue()) {
//                orderInfo.updatePriceByKline(ticker);
//                orderInfo.updateStatus();
//                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
//                        || orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
//                    allOrderDone.put(orderInfo.timeUpdate + "-" + symbol, orderInfo);
//                    orderRunning.remove(symbol);
//                }
//            }
//        }
//    }
//
//
//    private void checkAndCreateOrderNew(KlineObjectNumber ticker, String symbol, MarketLevelChange levelChange) {
//        OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
//        if (orderInfo == null) {
//            if (levelChange != null) {
//                if ((BudgetManagerSimple.getInstance().isAvailableTrade() )
//                        || levelChange.equals(MarketLevelChange.BIG_DOWN)
//                        || levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
//                        || levelChange.equals(MarketLevelChange.BIG_UP)
//                        || levelChange.equals(MarketLevelChange.MEDIUM_UP)
//                ) {
//                    createOrderBUY(symbol, ticker, levelChange);
//                } else {
//                    LOG.info("Stop trade because capital over: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
//                }
//            }
//        }
//    }
//
//    private void checkAndCreateOrderSELL(KlineObjectNumber ticker, String symbol, MarketLevelChange levelChange) {
//        OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
//        if (orderInfo == null) {
//            if (BudgetManagerSimple.getInstance().isAvailableTrade()) {
//                createOrderSELL(symbol, ticker, levelChange);
//            } else {
//                LOG.info("Stop trade because capital over: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
//            }
//        }
//    }
//
//    private void stopLossOrder(String symbol, KlineObjectNumber ticker) {
//        OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
//        if (orderInfo != null) {
//            // Check dca truoc
////            Double rateLoss = Utils.rateOf2Double(ticker.priceClose, orderInfo.priceEntry);
////            if (orderInfo.dcaLevel == null && rateLoss < -0.15) {
////                orderInfo = DcaHelper.dcaOrder(orderInfo, ticker, RATE_TARGET);
////                orderRunning.put(symbol, orderInfo);
////            } else {
//            // ko dca -> stoploss
//            orderInfo.priceTP = ticker.priceClose;
//            orderInfo.status = OrderTargetStatus.STOP_LOSS_DONE;
//            LOG.info("Stop order: {} {} {} {} {}!", Utils.toJson(symbol), orderInfo.priceEntry, orderInfo.priceTP,
//                    Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart), Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
//            orderInfo.timeUpdate = ticker.endTime.longValue();
//            orderInfo.tickerClose = ticker;
////            allOrderDone.put(ticker.startTime.longValue() + "-" + orderInfo.symbol, orderInfo);
//            allOrderDone.put(orderInfo.timeUpdate + "-" + orderInfo.symbol, orderInfo);
//            orderRunning.remove(orderInfo.symbol);
////            }
//        }
//    }
//
//    private void createOrderBUY(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange) {
//
//        Double entry = ticker.priceClose;
//        Double rateTarget = RATE_TARGET;
//        Double budget = BudgetManagerSimple.getInstance().getBudget();
//        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
//        if (levelChange.equals(MarketLevelChange.BIG_DOWN)) {
//            rateTarget = 8 * RATE_TARGET;
//            budget = budget * 1.5;
//        }
//        if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)) {
//            rateTarget = 6 * RATE_TARGET;
//            budget = budget * 1.5;
//        }
//        if (levelChange.equals(MarketLevelChange.MAYBE_BIG_DOWN_AFTER)) {
//            rateTarget = 3 * RATE_TARGET;
//        }
//        if (levelChange.equals(MarketLevelChange.BIG_UP)) {
//            rateTarget = 3 * RATE_TARGET;
//            budget = budget * 1.5;
//        }
//        if (levelChange.equals(MarketLevelChange.MEDIUM_UP)) {
//            rateTarget = 1.5 * RATE_TARGET;
//            budget = budget * 1.5;
//        }
//
//        if (levelChange.equals(MarketLevelChange.ALT_BIG_CHANGE_REVERSE)
//                || levelChange.equals(MarketLevelChange.ALT_BIG_CHANGE_REVERSE_EXTEND)
//        ) {
//            budget = budget * 2;
//        }
//
//        Double priceTp = Utils.calPriceTarget(symbol, entry, OrderSide.BUY, rateTarget);
//        Double priceSL = Utils.calPriceTarget(symbol, entry, OrderSide.SELL, RATE_TP_STOPLOSS * rateTarget);
//
//        String log = OrderSide.BUY + " " + symbol + " entry: " + entry + " target: " + priceTp
//                + " SL: " + priceSL + " budget: " + budget
//                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
//        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);
//        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, quantity,
//                leverage, symbol, ticker.startTime.longValue(), ticker.endTime.longValue(), OrderSide.BUY);
//        order.priceSL = priceSL;
//        order.minPrice = entry;
//        order.lastPrice = entry;
//        order.maxPrice = entry;
//        order.marketLevelChange = levelChange;
//        order.lastMarketLevelChange = getLastLevelChangeString(ticker.startTime.longValue());
//        order.tickerOpen = ticker;
//        orderRunning.put(symbol, order);
//        BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());
//        LOG.info(log);
//    }
//
//    private void createOrderSELL(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange) {
//        Double entry = ticker.priceClose;
//        Double rateTarget = RATE_TARGET;
//        Double budget = BudgetManagerSimple.getInstance().getBudget();
//        budget = budget * 2;
//        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
//        Double priceTp = Utils.calPriceTarget(symbol, entry, OrderSide.SELL, rateTarget);
//        String log = OrderSide.SELL + " " + symbol + " entry: " + entry + " target: " + priceTp + " budget: " + budget
//                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
//        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);
//        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, quantity,
//                leverage, symbol, ticker.startTime.longValue(), ticker.endTime.longValue(), OrderSide.SELL);
//        order.minPrice = entry;
//        order.lastPrice = entry;
//        order.maxPrice = entry;
//        order.marketLevelChange = levelChange;
//        order.lastMarketLevelChange = getLastLevelChangeString(ticker.startTime.longValue());
//        order.tickerOpen = ticker;
//        orderRunning.put(symbol, order);
//        BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());
//        LOG.info(log);
//    }
//
//    private String getLastLevelChangeString(long time) {
//        long time2Get;
//        int counter = 0;
//        while (true) {
//            counter++;
//            time2Get = time - counter * 15 * Utils.TIME_MINUTE;
//            MarketLevelChange lastLevel = time2MarketLevelChange.get(time2Get);
//            if (lastLevel != null) {
//                return lastLevel + "_" + counter;
//            }
//            if (counter > 16) {
//                return "";
//            }
//        }
//    }
//
//
//    private MarketLevelChange changeLevelByHistory(Long time, MarketLevelChange levelChange) {
//        long time2Get;
//        MarketLevelChange lastLevel;
//        int counter = 0;
//        while (true) {
//            counter++;
//            time2Get = time - counter * 15 * Utils.TIME_MINUTE;
//            lastLevel = time2MarketLevelChange.get(time2Get);
//            if (lastLevel != null) {
//                break;
//            }
//            if (counter > 16) {
//                break;
//            }
//        }
//        if (lastLevel == null) {
//            if (levelChange.equals(MarketLevelChange.MAYBE_BIG_DOWN_AFTER)) {
//                return null;
//            }
//        }
//        return levelChange;
//    }
//
//}
