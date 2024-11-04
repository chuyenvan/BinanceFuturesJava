/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.bak;

import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.MarketBigChangeDetector;
import com.binance.chuyennd.mongo.TickerMongoHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
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
public class SimulatorTradingByBtcSignalCandleReverse {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorTradingByBtcSignalCandleReverse.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";
    public final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public final Double NUMBER_HOURS_STOP_MIN = Configs.getDouble("NUMBER_HOURS_STOP_MIN");
    public Double RATE_LOSS_AVG_STOP_ALL = Configs.getDouble("RATE_LOSS_AVG_STOP_ALL");
    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
    public final String TIME_RUN = Configs.getString("TIME_RUN");


    public static void main(String[] args) throws ParseException, IOException {
        SimulatorTradingByBtcSignalCandleReverse test = new SimulatorTradingByBtcSignalCandleReverse();
        test.initData();
        test.simulatorAllSymbol();
    }


    private void simulatorAllSymbol() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;

        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers;
//            List<Long> timeBtcTrend = MarketBigChangeDetector.detectBtcTrendBigUp();
            try {
                time2Tickers = TickerMongoHelper.getInstance().getDataFromDb(startTime);
                for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
                    Long time = entry.getKey();
                    Map<String, KlineObjectNumber> symbol2Ticker = entry.getValue();
                    // check and stop all when market dump
                    checkAndStopAll(symbol2Ticker);
                    // update order Old
                    for (Map.Entry<String, KlineObjectNumber> entry1 : symbol2Ticker.entrySet()) {
                        String symbol = entry1.getKey();
                        KlineObjectNumber ticker = entry1.getValue();
                        startUpdateOldOrderTrading(symbol, ticker);
                    }

//                    if (timeBtcTrend.contains(time)) {
//                        List<String> symbol2Trade = MarketBigChangeDetector.getTopSymbol2TradeBtcSignal(entry.getValue(), 20);
//                        LOG.info("{} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), symbol2Trade);
//                        // check create order new
//                        for (String symbol : symbol2Trade) {
//                            checkAndCreateOrderNew(symbol2Ticker.get(symbol), symbol);
//                        }
//                    }
                    BudgetManagerTest.getInstance().updateBalance(time, allOrderDone);
                    BudgetManagerTest.getInstance().updateInvesting();

                }
                Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
                Long finalStartTime1 = startTime;
                buildReport(finalStartTime1);
                startTime += Utils.TIME_DAY;
                if (startTime > System.currentTimeMillis()) {
                    break;
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
        Long finalStartTime = startTime;
        buildReport(finalStartTime);
        BudgetManagerTest.getInstance().printBalanceIndex();
        exitWhenDone();

    }

    private void checkAndStopAll(Map<String, KlineObjectNumber> symbol2Ticker) {
        try {
            Set<String> symbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER);
            Double rateLossTotal = 0d;
            Double rateLossCurrent = 0d;
            if (symbols.size() < 10) {
                return;
            }
            for (String symbol : symbols) {
                String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol);
                if (StringUtils.isNotEmpty(json)) {
                    OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
                    if (orderInfo != null) {
                        KlineObjectNumber ticker = symbol2Ticker.get(symbol);
                        rateLossTotal += Utils.rateOf2Double(ticker.priceClose, orderInfo.priceEntry);
                        rateLossCurrent += Utils.rateOf2Double(orderInfo.lastPrice, orderInfo.priceEntry);
                    }
                }
            }
            LOG.info("Check stop All: {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(
                            symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC).startTime.longValue()),
                    rateLossTotal / symbols.size() < -RATE_LOSS_AVG_STOP_ALL / 100,
                    rateLossTotal / symbols.size(), -RATE_LOSS_AVG_STOP_ALL / 100);
            if (rateLossTotal / symbols.size() < -RATE_LOSS_AVG_STOP_ALL / 100) {
                LOG.info("Stop all order because market big dump: {}", Utils.normalizeDateYYYYMMDDHHmm(
                        symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC).startTime.longValue()));
                Double rateChange = RATE_LOSS_AVG_STOP_ALL / 100 + rateLossCurrent / symbols.size();
                for (String symbol : symbols) {
                    String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol);
                    if (StringUtils.isNotEmpty(json)) {
                        OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
                        KlineObjectNumber ticker = symbol2Ticker.get(symbol);
                        Double priceCloseNew = orderInfo.lastPrice - orderInfo.priceEntry * rateChange;
                        LOG.info("StopAll: {} lastPriceOld: {} lastPrice:{} priceClose:{}", symbol, orderInfo.lastPrice, priceCloseNew, ticker.priceClose);
                        ticker.priceClose = priceCloseNew;
                        stopLossOrder(symbol, ticker);
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void exitWhenDone() {
        try {
            Thread.sleep(10 * Utils.TIME_MINUTE);
            System.exit(1);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void initData() throws IOException, ParseException {
        // clear Data Old
        RedisHelper.getInstance().get().del(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER);
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
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER)) {
            String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol);
            if (json != null) {
                OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
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
            if (order.dynamicTP_SL != null && order.dynamicTP_SL > 0) {
                totalDca++;
                if (order.dynamicTP_SL >= 2) {
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
        reportRunning.append(" Running: ").append(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER).size()).append(" orders");
        LOG.info(reportRunning.toString());
//        LOG.info(Utils.toJson(symbol2Counter));
//        Utils.sendSms2Telegram(reportRunning.toString());
    }

    private void startUpdateOldOrderTrading(String symbol, KlineObjectNumber ticker) {

        String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol);
        // update order old
        if (StringUtils.isNotEmpty(json)) {
            OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
            if (orderInfo.timeStart < ticker.startTime.longValue()) {
                orderInfo.updatePriceByKline(ticker);
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    allOrderDone.put(ticker.startTime.longValue() + "-" + symbol, orderInfo);
                    RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol);
                } else {
                    if (orderInfo.timeStart < ticker.startTime - Utils.TIME_HOUR * NUMBER_HOURS_STOP_MIN) {
                        stopLossOrder(symbol, ticker);
                    } else {
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol, Utils.toJson(orderInfo));
                    }
                }
            }
        }
    }

    private void checkAndCreateOrderNew(KlineObjectNumber ticker, String symbol) {
        String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol);
        // update order old
        if (!StringUtils.isNotEmpty(json)) {
            if (BudgetManagerTest.getInstance().isAvailableTrade()) {
                createOrderNew(symbol, ticker);
            } else {
                LOG.info("Stop trade because capital over: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            }
        }

    }

    private void stopLossOrder(String symbol, KlineObjectNumber ticker) {
        String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol);
        if (StringUtils.isNotEmpty(json)) {
            OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
            orderInfo.priceTP = ticker.priceClose;
            orderInfo.status = OrderTargetStatus.STOP_LOSS_DONE;
            LOG.info("Stop order: {} {} {} {} {}!", Utils.toJson(symbol), orderInfo.priceEntry, orderInfo.priceTP,
                    Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart), Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            orderInfo.timeUpdate = ticker.startTime.longValue();
            orderInfo.tickerClose = ticker;
            allOrderDone.put(ticker.startTime.longValue() + "-" + orderInfo.symbol, orderInfo);
            RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, orderInfo.symbol);
        }
    }

    private void createOrderNew(String symbol, KlineObjectNumber ticker) {

        Double entry = ticker.priceClose;
        Double rateTarget = RATE_TARGET;
        Double budget = BudgetManagerTest.getInstance().getBudget();
        Integer leverage = BudgetManagerTest.getInstance().getLeverage();

        Double priceTp = Utils.calPriceTarget(symbol, entry, OrderSide.BUY, rateTarget);
        String log = OrderSide.BUY + " " + symbol + " entry: " + entry + " target: " + priceTp + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.endTime.longValue(), OrderSide.BUY);
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = ticker;
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol, Utils.toJson(order));
        BudgetManagerTest.getInstance().updateInvesting();
        LOG.info(log);
    }


}
