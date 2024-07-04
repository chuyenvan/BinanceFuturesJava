/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.btctd.BreadDetectObject;
import com.binance.chuyennd.indicators.SimpleMovingAverage1DManager;
import com.binance.chuyennd.mongo.TickerMongoHelper;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.educa.chuyennd.funcs.BreadFunctions;
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
public class SimulatorTradingVolumeMiniSLDynamic {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorTradingVolumeMiniSLDynamic.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";
    public final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public final Double RATE_MA_MAX = Configs.getDouble("RATE_MA_MAX");
    public final Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");
    public final Double NUMBER_HOURS_STOP_MIN = Configs.getDouble("NUMBER_HOURS_STOP_MIN");
    public final Double NUMBER_HOURS_STOP_MAX = Configs.getDouble("NUMBER_HOURS_STOP_MAX");
    public final Double RATE_SUCCESS_STATISTIC = Configs.getDouble("RATE_SUCCESS_STATISTIC");
    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
    public ConcurrentHashMap<String, KlineObjectNumber> symbol2Ticker = new ConcurrentHashMap<>();
    //    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    public Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");
    public final String TIME_RUN = Configs.getString("TIME_RUN");


    public static void main(String[] args) throws ParseException, IOException {
        SimulatorTradingVolumeMiniSLDynamic test = new SimulatorTradingVolumeMiniSLDynamic();
        test.initData();
        test.simulatorAllSymbol();
    }


    private void simulatorAllSymbol() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;

        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers;
            try {
                time2Tickers = TickerMongoHelper.getInstance().getDataFromDb(startTime);
                for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
                    Long time = entry.getKey();
                    symbol2Ticker.clear();
                    symbol2Ticker.putAll(entry.getValue());

                    for (Map.Entry<String, KlineObjectNumber> entry1 : symbol2Ticker.entrySet()) {
                        String symbol = entry1.getKey();
                        if (Constants.diedSymbol.contains(symbol)) {
                            continue;
                        }
                        processTradeATicker(symbol);
                    }
                    BudgetManagerTest.getInstance().updateBalance(time, allOrderDone);
                    BudgetManagerTest.getInstance().updateInvesting();

                }
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
        RedisHelper.getInstance().get().del(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER);
        allOrderDone = new ConcurrentHashMap<>();
        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
            FileUtils.delete(new File(FILE_STORAGE_ORDER_DONE));
        }
        SimpleMovingAverage1DManager.getInstance();
        if (RATE_SUCCESS_STATISTIC != 0) {
            BreadFunctions.updateVolumeRateChange(NUMBER_HOURS_STOP_MIN.intValue()
                    , RATE_SUCCESS_STATISTIC);
        }
        try {
            Thread.sleep(15 * Utils.TIME_SECOND);
        } catch (InterruptedException e) {
        }
    }


    public StringBuilder calReportRunning(Long currentTime) {
        StringBuilder builder = new StringBuilder();
        Double totalLoss = 0d;
        Double totalBuy = 0d;
        Double totalSell = 0d;
        Integer dcaTotal = 0;
        TreeMap<Double, OrderTargetInfoTest> pnl2OrderInfo = new TreeMap<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER)) {
            String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol);
            if (json != null) {
                OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
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
        reportRunning.append(" Running: ").append(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER).size()).append(" orders");
        LOG.info(reportRunning.toString());
//        LOG.info(Utils.toJson(symbol2Counter));
//        Utils.sendSms2Telegram(reportRunning.toString());
    }

    private void processTradeATicker(String symbol) {

        KlineObjectNumber ticker = symbol2Ticker.get(symbol);
        try {
//            Long timeCheck = 0l;
//            timeCheck = Utils.sdfFileHour.parse("20240529 23:30").getTime();
//            if (StringUtils.equals(symbol, "XVSUSDT") && ticker.startTime.longValue() == timeCheck) {
//                System.out.println("Debug");
//            }
            SimpleMovingAverage1DManager.getInstance().updateWithTicker(symbol, ticker);
            String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol);
            // check running
            if (StringUtils.isNotEmpty(json)) {
                OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
                if (orderInfo.timeStart < ticker.startTime.longValue()) {
                    orderInfo.updatePriceByKline(ticker);
                    orderInfo.updateStatus();
                    if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                        allOrderDone.put(ticker.startTime.longValue() + "-" + symbol, orderInfo);
                        RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol);
                        checkAndCreateOrderNew(symbol);
                    } else {
                        if (orderInfo.timeStart < ticker.startTime - Utils.TIME_HOUR * NUMBER_HOURS_STOP_MAX) {
                            LOG.info("Close order over time: {} time:{} minutes", orderInfo.symbol,
                                    (ticker.startTime - orderInfo.timeStart) / Utils.TIME_MINUTE);
                            stopLossOrder(symbol, OrderTargetStatus.STOP_LOSS_OVERTIME);
                        } else {
//                            Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol,
//                                    Utils.getDate(ticker.startTime.longValue()));
//                            if (maValue != null && ticker.priceClose < maValue) {
//                                stopLossOrder(symbol, OrderTargetStatus.STOP_LOSS_MA20);
//                            } else {
                            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol, Utils.toJson(orderInfo));
//                            }
                        }
                    }
                }
            } else {
                checkAndCreateOrderNew(symbol);
            }

        } catch (Exception e) {
            LOG.info("Error process: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            e.printStackTrace();
        }
    }

    private void checkAndCreateOrderNew(String symbol) {
        try {
            KlineObjectNumber ticker = symbol2Ticker.get(symbol);
            BreadDetectObject breadData = BreadFunctions.calBreadDataAlt(ticker, RATE_BREAD_MIN_2TRADE);
            MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(Utils.getDate(ticker.startTime.longValue()), symbol);

            Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol,
                    Utils.getDate(ticker.startTime.longValue()));
            Double rateMa = Utils.rateOf2Double(ticker.priceClose, maValue);
            if (maValue == null) {
                LOG.info("ma value null with ticker: {}", symbol);
                return;
            }
            Double rateChange = BreadFunctions.getRateChangeWithVolume(ticker.totalUsdt / 1000000);
            if (rateChange == null) {
                LOG.info("Error rateChange with ticker: {} {}", symbol, Utils.toJson(ticker));
                return;
            }
            if (BreadFunctions.isAvailableTrade(breadData, ticker, maStatus, maValue, rateChange, rateMa, RATE_MA_MAX)) {
                LOG.info("Big:{} {} {} rate:{} volume: {}", symbol, new Date(ticker.startTime.longValue()), breadData.orderSide, breadData.totalRate, ticker.totalUsdt);
                if (BudgetManagerTest.getInstance().isAvailableTrade()) {
                    createOrderNew(symbol, breadData);
                } else {
                    Boolean isClosed = checkAndCloseOrderLatestOverTimeMin(ticker);
                    if (isClosed) {
                        createOrderNew(symbol, breadData);
                    } else {
                        LOG.info("Stop trade because capital over: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private Boolean checkAndCloseOrderLatestOverTimeMin(KlineObjectNumber ticker) {
        try {
            Long timeMin = null;
            OrderTargetInfoTest orderLatest = null;
            for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER)) {
                try {
                    String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol);
                    OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
                    if (orderInfo != null) {
                        if (timeMin == null || timeMin > orderInfo.timeStart) {
                            timeMin = orderInfo.timeStart;
                            orderLatest = orderInfo;
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            if (orderLatest != null) {
                if (orderLatest.timeStart < ticker.startTime - Utils.TIME_HOUR * NUMBER_HOURS_STOP_MIN) {
                    stopLossOrder(orderLatest.symbol, OrderTargetStatus.STOP_LOSS_4_NEW);
                    LOG.info("Close order to trade new: {} time:{} minutes", orderLatest.symbol,
                            (ticker.startTime - orderLatest.timeStart) / Utils.TIME_MINUTE);
                    return true;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    private void stopLossOrder(String symbol, OrderTargetStatus statusSL) {
        KlineObjectNumber ticker = symbol2Ticker.get(symbol);
        String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol);
        if (StringUtils.isNotEmpty(json)) {
            OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
//            LOG.info("Cancel order over 30d: {} {} {}!", Utils.toJson(symbol),
//                    Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart), Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            orderInfo.priceTP = ticker.priceClose;
//            orderInfo.status = OrderTargetStatus.STOP_LOSS_DONE;
            orderInfo.status = statusSL;
            orderInfo.timeUpdate = ticker.startTime.longValue();
            orderInfo.tickerClose = ticker;
            allOrderDone.put(ticker.startTime.longValue() + "-" + orderInfo.symbol, orderInfo);
            RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, orderInfo.symbol);
        }
    }

    private void createOrderNew(String symbol, BreadDetectObject breadData) {
        KlineObjectNumber ticker = symbol2Ticker.get(symbol);
//        Double entry = ticker.priceClose * 1.002;
        Double entry = ticker.priceClose;
        Double priceTp = Utils.calPriceTarget(symbol, entry, OrderSide.BUY, RATE_TARGET);

        String log = OrderSide.BUY + " " + symbol + " entry: " + entry + " target: " + priceTp + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(BudgetManagerTest.getInstance().getBudget(), BudgetManagerTest.getInstance().getLeverage(), entry, symbol);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, quantity,
                LEVERAGE_ORDER, symbol, ticker.startTime.longValue(), ticker.endTime.longValue(), OrderSide.BUY);
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.rsi14 = ticker.rsi;
        order.ma201d = ticker.ma20;
        order.rateChange = breadData.totalRate;
        order.volume = breadData.volume;
        order.tickerOpen = ticker;
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol, Utils.toJson(order));
        BudgetManagerTest.getInstance().updateInvesting();
        LOG.info(log);
    }


}
