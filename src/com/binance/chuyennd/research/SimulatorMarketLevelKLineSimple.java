/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetector;
import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.object.KlineObjectNumber;
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
public class SimulatorMarketLevelKLineSimple {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorMarketLevelKLineSimple.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";
    public final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public final Double NUMBER_HOURS_STOP_MIN = Configs.getDouble("NUMBER_HOURS_STOP_MIN");
    public final Integer NUMBER_ENTRY_EACH_SIGNAL = Configs.getInt("NUMBER_ENTRY_EACH_SIGNAL");
    public Double RATE_LOSS_AVG_STOP_ALL = Configs.getDouble("RATE_LOSS_AVG_STOP_ALL");
    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
    public final String TIME_RUN = Configs.getString("TIME_RUN");
    public ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning = new ConcurrentHashMap();


    public static void main(String[] args) throws ParseException, IOException {
        SimulatorMarketLevelKLineSimple test = new SimulatorMarketLevelKLineSimple();
        test.initData();
        test.simulatorAllSymbol();
    }


    private void simulatorAllSymbol() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        List<KlineObjectNumber> btcTickers = (List<KlineObjectNumber>)
                Storage.readObjectFromFile(DataManager.FOLDER_TICKER_15M + Constants.SYMBOL_PAIR_BTC);
        Map<String, KlineObjectNumber> lastTicker = null;
        Map<String, List<KlineObjectNumber>> symbol2Tickers = new HashMap<>();

        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers;
            try {
                time2Tickers = DataManager.readDataFromFile(startTime);
                if (time2Tickers == null) {
                    break;
                }
                for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
                    Long time = entry.getKey();
//                    if (time == Utils.sdfFileHour.parse("20230105 02:00").getTime()) {
//                        System.out.println("Debug");
//                    }
                    Map<String, KlineObjectNumber> symbol2Ticker = entry.getValue();
                    // check and stop all when market dump
                    checkAndStopAll(symbol2Ticker);
                    // update order Old
                    for (Map.Entry<String, KlineObjectNumber> entry1 : symbol2Ticker.entrySet()) {
                        String symbol = entry1.getKey();
                        KlineObjectNumber ticker = entry1.getValue();
                        List<KlineObjectNumber> tickers = symbol2Tickers.get(symbol);
                        if (tickers == null) {
                            tickers = new ArrayList<>();
                            symbol2Tickers.put(symbol, tickers);
                        }
                        tickers.add(ticker);
                        if (tickers.size() < 20) {
                            continue;
                        }
                        if (tickers.size() > 200) {
                            for (int i = 0; i < 50; i++) {
                                tickers.remove(0);
                            }
                        }
                        startUpdateOldOrderTrading(symbol, ticker);
                    }
                    MarketLevelChange levelChange = MarketBigChangeDetector.detectLevelChange(entry.getValue());
                    if (levelChange != null
//                            && !levelChange.equals(MarketLevelChange.MAYBE_BIG_DOWN_AFTER)
//                            && levelChange != MarketLevelChange.TINY
                    ) {
                        List<String> symbol2Trade;

                        if (levelChange.equals(MarketLevelChange.VOLUME_BIG_CHANGE)) {
                            symbol2Trade = MarketBigChangeDetector.getTopSymbol2TradeWithVolumeBigUp(
                                    lastTicker, entry.getValue(), NUMBER_ENTRY_EACH_SIGNAL);
                        } else {
                            symbol2Trade = MarketBigChangeDetector.getTopSymbol2Trade(entry.getValue(), NUMBER_ENTRY_EACH_SIGNAL, levelChange);
                        }
//                        List<String> symbol2Trade = MarketBigChangeDetector.getTopSymbol2TradeWithVolumeBigChange(lastTicker, entry.getValue(), 20);

                        LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2Trade);
                        // check create order new
                        for (String symbol : symbol2Trade) {
                            checkAndCreateOrderNew(symbol2Ticker.get(symbol), symbol, levelChange);
                        }
                    } else {

                        // trade btc small change reverse when no oder running
                        if (orderRunning.isEmpty()) {
                            if (MarketBigChangeDetectorTest.getStatusTradingBtc(btcTickers, time) == 1) {
                                levelChange = MarketLevelChange.BTC_SMALL_CHANGE_REVERSE;
                                List<String> symbol2Trade = MarketBigChangeDetector.getTopSymbol2TradeWithVolumeBigUp(
                                        lastTicker, entry.getValue(), NUMBER_ENTRY_EACH_SIGNAL / 2);
                                LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2Trade);
                                for (String symbol : symbol2Trade) {
                                    checkAndCreateOrderNew(symbol2Ticker.get(symbol), symbol, levelChange);
                                }
                            }
                        }
                        if (orderRunning.isEmpty()) {
                            Double rateChangeAvg = MarketBigChangeDetectorTest.calRateChangeAvg(entry.getValue());
                            if (MarketBigChangeDetectorTest.isBtcBottomReverse(btcTickers, time) && rateChangeAvg > 0.01) {
                                levelChange = MarketLevelChange.BTC_BOTTOM_REVERSE;
                                List<String> symbol2Trade = MarketBigChangeDetector.getTopSymbol2TradeWithVolumeBigUp(
                                        lastTicker, entry.getValue(), NUMBER_ENTRY_EACH_SIGNAL / 2);
                                LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2Trade);
                                for (String symbol : symbol2Trade) {
                                    checkAndCreateOrderNew(symbol2Ticker.get(symbol), symbol, levelChange);
                                }
                            }
                        }
                        if (orderRunning.isEmpty()) {
                            TreeMap<Double, String> rateChange2Symbol = new TreeMap<>();
                            for (Map.Entry<String, List<KlineObjectNumber>> entry1 : symbol2Tickers.entrySet()) {
                                String symbol = entry1.getKey();
                                List<KlineObjectNumber> tickers = entry1.getValue();
                                if (tickers.size() < 100) {
                                    continue;
                                }
                                if (MarketBigChangeDetectorTest.getStatusTradingAlt15M(tickers, tickers.size() - 1) == 1
                                ) {
                                    KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
                                    rateChange2Symbol.put(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen), symbol);
                                }
                            }
                            if (rateChange2Symbol.size() >= 5) {
                                levelChange = MarketLevelChange.ALT_BIG_CHANGE_REVERSE;
                                int counter = 0;
                                for (Map.Entry<Double, String> entry2 : rateChange2Symbol.entrySet()) {
                                    String symbol = entry2.getValue();
                                    LOG.info("Alt: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol);
                                    checkAndCreateOrderNew(symbol2Ticker.get(symbol), symbol, levelChange);
                                    counter++;
                                    if (counter >= 4) {
                                        break;
                                    }
                                }
                            }
                        }

                    }
                    lastTicker = symbol2Ticker;
                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, orderRunning);
                    BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());

                }
                Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
                Long finalStartTime1 = startTime;
                buildReport(finalStartTime1);
            } catch (Exception e) {
                e.printStackTrace();
            }
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
        Long finalStartTime = startTime;
        buildReport(finalStartTime);
        BudgetManagerSimple.getInstance().printBalanceIndex();
        exitWhenDone();

    }


    private void checkAndStopAll(Map<String, KlineObjectNumber> symbol2Ticker) {
        Set<String> symbols = orderRunning.keySet();
        Double rateLossTotal = 0d;
        Double rateLossCurrent = 0d;
        if (symbols.size() < 5) {
            return;
        }
        boolean isHaveOrderBigChangeLevel = false;
//        boolean isHaveOrderMediumChangeLevel = false;
//        boolean isHaveOrderSmallChangeLevel = false;
        for (String symbol : symbols) {
            OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
            if (orderInfo != null) {
                try {
                    KlineObjectNumber ticker = symbol2Ticker.get(symbol);
                    if (ticker != null) {
                        rateLossTotal += Utils.rateOf2Double(ticker.priceClose, orderInfo.priceEntry);
                        rateLossCurrent += Utils.rateOf2Double(orderInfo.lastPrice, orderInfo.priceEntry);
                    }
                    if (orderInfo.marketLevelChange.equals(MarketLevelChange.BIG_DOWN)) {
                        isHaveOrderBigChangeLevel = true;
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }
        double rateMax2StopAll = -RATE_LOSS_AVG_STOP_ALL / 100;
        // default 1/2 rate loss current, have big x2, have medium x1.5
        rateMax2StopAll = rateMax2StopAll / 2;
        if (isHaveOrderBigChangeLevel) {
            rateMax2StopAll = rateMax2StopAll * 2;
        }
//        else {
//            if (isHaveOrderMediumChangeLevel) {
//                rateMax2StopAll = rateMax2StopAll * 1.6;
//            } else {
//                if (isHaveOrderSmallChangeLevel) {
//                    rateMax2StopAll = rateMax2Stop5 lagtAll * 1.4;
//                } else {
//                    rateMax2StopAll = rateMax2StopAll * 1.2;
//                }
//            }
//        }
        LOG.info("Check stop All: {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(
                        symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC).startTime.longValue()),
                rateLossTotal / symbols.size() < rateMax2StopAll,
                rateLossTotal / symbols.size(), rateMax2StopAll);
        if (rateLossTotal / symbols.size() < rateMax2StopAll) {
            LOG.info("Stop all order because market big dump: {}", Utils.normalizeDateYYYYMMDDHHmm(
                    symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC).startTime.longValue()));
            Double rateChange = rateLossCurrent / symbols.size() - rateMax2StopAll;
            for (String symbol : symbols) {
                OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
                if (orderInfo != null) {
                    KlineObjectNumber ticker = symbol2Ticker.get(symbol);
                    if (ticker != null) {
                        Double priceCloseNew = orderInfo.lastPrice - orderInfo.priceEntry * rateChange;
                        LOG.info("StopAll: {} lastPriceOld: {} lastPrice:{} priceClose:{}", symbol, orderInfo.lastPrice, priceCloseNew, ticker.priceClose);
                        ticker.priceClose = priceCloseNew;
                        stopLossOrder(symbol, ticker);
                    } else {
                        LOG.info("Errorrrrrrrrrrrrrr: {} {} {}", symbol, symbol2Ticker.size(),
                                symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC).startTime.longValue());
                    }
                }
            }
        }
    }

    private void exitWhenDone() {
        try {
            Thread.sleep(10 * Utils.TIME_SECOND);
            System.exit(1);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void initData() throws IOException, ParseException {
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
                if (orderInfo.dcaLevel != null && orderInfo.dcaLevel > 0) {
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
                        .append(" ").append(" dcaLevel:").append(orderInfo.dcaLevel).append(" ")
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
        reportRunning.append(" Success: ").append(allOrderDone.size() * RATE_TARGET * 100).append("%");
        int totalBuy = 0;
        int totalSell = 0;
        int totalDca = 0;
        int totalDcaLevel2 = 0;
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
            if (order.dcaLevel != null && order.dcaLevel > 0) {
                totalDca++;
                if (order.dcaLevel >= 2) {
                    totalDcaLevel2++;
                }
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
        reportRunning.append(" Buy: ").append(totalBuy * RATE_TARGET * 100).append("%");
        reportRunning.append(" Sell: ").append(totalSell * RATE_TARGET * 100).append("%");
        reportRunning.append(" SL: ").append(totalSL).append(" ");
        reportRunning.append(" dcaDone: ").append(totalDca).append(" ");
        reportRunning.append(" Running: ").append(orderRunning.size()).append(" orders");
        LOG.info(reportRunning.toString());
//        LOG.info(Utils.toJson(symbol2Counter));
//        Utils.sendSms2Telegram(reportRunning.toString());
    }

    private void startUpdateOldOrderTrading(String symbol, KlineObjectNumber ticker) {

        OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
        if (orderInfo != null) {
            if (orderInfo.timeStart < ticker.startTime.longValue()) {
                orderInfo.updatePriceByKline(ticker);
                orderInfo.updateStatus();
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    allOrderDone.put(ticker.startTime.longValue() + "-" + symbol, orderInfo);
                    orderRunning.remove(symbol);
                } else {
                    Long time2CloseMax = Utils.TIME_HOUR * NUMBER_HOURS_STOP_MIN.longValue();
                    if (orderInfo.marketLevelChange.equals(MarketLevelChange.BIG_DOWN)
//                            || orderInfo.marketLevelChange.equals(MarketLevelChange.MEDIUM)
                    ) {
                        time2CloseMax = time2CloseMax / 4;
                    }
                    if (orderInfo.timeStart < ticker.startTime - time2CloseMax) {
                        stopLossOrder(symbol, ticker);
                    } else {
                        orderRunning.put(symbol, orderInfo);
                    }
                }
            }
        }
    }

    private void checkAndCreateOrderNew(KlineObjectNumber ticker, String symbol, MarketLevelChange levelChange) {
        OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
        if (orderInfo == null) {
            if (levelChange != null) {
                if (BudgetManagerSimple.getInstance().isAvailableTrade()
                        || levelChange.equals(MarketLevelChange.BIG_DOWN)
                        || levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                        || levelChange.equals(MarketLevelChange.BIG_UP)
                        || levelChange.equals(MarketLevelChange.MEDIUM_UP)
                ) {
                    createOrderNew(symbol, ticker, levelChange);
                } else {
                    LOG.info("Stop trade because capital over: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
                }
            }
        }

    }

    private void stopLossOrder(String symbol, KlineObjectNumber ticker) {
        OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
        if (orderInfo != null) {
            orderInfo.priceTP = ticker.priceClose;
            orderInfo.status = OrderTargetStatus.STOP_LOSS_DONE;
            LOG.info("Stop order: {} {} {} {} {}!", Utils.toJson(symbol), orderInfo.priceEntry, orderInfo.priceTP,
                    Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart), Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            orderInfo.timeUpdate = ticker.startTime.longValue();
            orderInfo.tickerClose = ticker;
            allOrderDone.put(ticker.startTime.longValue() + "-" + orderInfo.symbol, orderInfo);
            orderRunning.remove(orderInfo.symbol);
        }
    }

    private void createOrderNew(String symbol, KlineObjectNumber ticker, MarketLevelChange levelChange) {

        Double entry = ticker.priceClose;
        Double rateTarget = RATE_TARGET;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
        if (levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            rateTarget = 8 * RATE_TARGET;
            budget = budget * 1.5;
        }
        if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)) {
            rateTarget = 4 * RATE_TARGET;
            budget = budget * 1.5;
        }
//        if (levelChange.equals(MarketLevelChange.MAYBE_BIG_DOWN_AFTER)) {
//            rateTarget = 2 * RATE_TARGET;
//        }


        if (levelChange.equals(MarketLevelChange.BIG_UP)) {
            rateTarget = 2 * RATE_TARGET;
            budget = budget * 1.5;
        }
        if (levelChange.equals(MarketLevelChange.MEDIUM_UP)) {
            budget = budget * 1.5;
        }
        if (levelChange.equals(MarketLevelChange.MINI_DOWN_EXTEND)) {
            rateTarget = 0.007;
        }
        if (levelChange.equals(MarketLevelChange.VOLUME_BIG_CHANGE)) {
            rateTarget = 0.007;
        }
        if (levelChange.equals(MarketLevelChange.BTC_SMALL_CHANGE_REVERSE)) {
            rateTarget = 0.007;
        }
//        if (levelChange.equals(MarketLevelChange.BTC_BOTTOM_REVERSE)) {
//            rateTarget = 0.007;
//        }
        if (levelChange.equals(MarketLevelChange.ALT_BIG_CHANGE_REVERSE)) {
            rateTarget = 0.007;
        }


        Double priceTp = Utils.calPriceTarget(symbol, entry, OrderSide.BUY, rateTarget);

        String log = OrderSide.BUY + " " + symbol + " entry: " + entry + " target: " + priceTp + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.endTime.longValue(), OrderSide.BUY);
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.marketLevelChange = levelChange;
        order.tickerOpen = ticker;
        orderRunning.put(symbol, order);
        BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());
        LOG.info(log);
    }


}
