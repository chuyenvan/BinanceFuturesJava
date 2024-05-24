/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.btctd.BreadDetectObject;
import com.binance.chuyennd.indicators.SimpleMovingAverageManager;
import com.binance.chuyennd.mongo.TickerMongoHelper;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
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
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * @author pc
 */
public class SimulatorTradingVolumeMiniStopLoss {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorTradingVolumeMiniStopLoss.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";
    public final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public final Double RATE_MA_MAX = Configs.getDouble("RATE_MA_MAX");
    public final Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");
    public final Integer NUMBER_HOURS_STOP_TRADE = Configs.getInt("NUMBER_HOURS_STOP_TRADE");
    public final Double RATE_SUCCESS_STATISTIC = Configs.getDouble("RATE_SUCCESS_STATISTIC");
    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    public Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");

    public final String SYMBOL_RUN = Configs.getString("SYMBOL_RUN");
    public final String TIME_RUN = Configs.getString("TIME_RUN");


    public static void main(String[] args) throws ParseException, IOException {
        SimulatorTradingVolumeMiniStopLoss test = new SimulatorTradingVolumeMiniStopLoss();
        test.initData();
        test.simulatorAllSymbol();
    }


    private void simulatorAllSymbol() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        boolean modeRunAll = StringUtils.equalsIgnoreCase(SYMBOL_RUN, "ALL");
        LOG.info("Mode running all symbol: {} -> {}", modeRunAll, SYMBOL_RUN);
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers;
            try {
                if (!modeRunAll) {
                    time2Tickers = TickerMongoHelper.getInstance().getDataFromDb(startTime, SYMBOL_RUN);
                } else {
                    time2Tickers = TickerMongoHelper.getInstance().getDataFromDb(startTime);
                }

                for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
                    Long time = entry.getKey();
                    Map<String, KlineObjectNumber> symbol2Ticker = entry.getValue();
                    for (Map.Entry<String, KlineObjectNumber> entry1 : symbol2Ticker.entrySet()) {
                        String symbol = entry1.getKey();
                        KlineObjectNumber ticker = entry1.getValue();
                        if (modeRunAll) {
                            executorService.execute(() -> startThreadTestTradingSimulatorBySymbol(symbol, ticker));
                        } else {
                            if (StringUtils.equals(symbol, SYMBOL_RUN)) {
                                executorService.execute(() -> startThreadTestTradingSimulatorBySymbol(symbol, ticker));
                            }
                        }
                    }
                    executorService.execute(() -> BudgetManagerTest.getInstance().updateBalance(time, allOrderDone));
                    executorService.execute(() -> BudgetManagerTest.getInstance().updateInvesting());

                }
                Long finalStartTime1 = startTime;
                executorService.execute(() -> buildReport(finalStartTime1));
                startTime += Utils.TIME_DAY;
                if (startTime > System.currentTimeMillis()) {
                    break;
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        executorService.execute(() -> Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone));
        Long finalStartTime = startTime;
        executorService.execute(() -> buildReport(finalStartTime));
        executorService.execute(() -> BudgetManagerTest.getInstance().printBalanceIndex());
        executorService.execute(() -> exitWhenDone());

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
        SimpleMovingAverageManager.getInstance();
        if (RATE_SUCCESS_STATISTIC != 0) {
            BreadFunctions.updateVolumeRateChange(NUMBER_HOURS_STOP_TRADE
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
        LOG.info(Utils.toJson(symbol2Counter));
//        Utils.sendSms2Telegram(reportRunning.toString());
    }

    private void startThreadTestTradingSimulatorBySymbol(String symbol, KlineObjectNumber ticker) {
        // check running
//        try {
//            if (StringUtils.equals(symbol, "CELOUSDT") && ticker.startTime.longValue() == Utils.sdfFileHour.parse("20230401 23:30").getTime()) {
//                System.out.println("debug");
//            }
//            if (StringUtils.equals(symbol, "CELOUSDT") && ticker.startTime.longValue() == Utils.sdfFileHour.parse("20230402 06:15").getTime()) {
//                System.out.println("debug");
//            }
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
        String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol);
        if (StringUtils.isNotEmpty(json)) {
            OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
            if (orderInfo.timeStart < ticker.startTime.longValue()) {
                orderInfo.updatePriceByKline(ticker);
                Double rateLoss = Math.abs(Utils.rateOf2Double(orderInfo.lastPrice, orderInfo.priceEntry));
                if (rateLoss * 100 > DCAManagerTest.getMinRateDCA()) {
                    orderInfo.timeUpdate = ticker.startTime.longValue();
                    if (BudgetManagerTest.getInstance().isAvailableDca()) {
                        DCAManagerTest.checkAndDcaOrder(orderInfo, RATE_TARGET);
                    }
                }

                orderInfo.updateStatus();
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    allOrderDone.put(ticker.startTime.longValue() + "-" + symbol, orderInfo);
                    RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol);
                    checkAndCreateOrderNew(ticker, symbol);
                } else {
                    if (orderInfo.timeStart < ticker.startTime - Utils.TIME_HOUR * NUMBER_HOURS_STOP_TRADE) {
                        stopLossOrder(symbol, ticker);
                    } else {
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol, Utils.toJson(orderInfo));
                    }
                }
            }
        } else {
            checkAndCreateOrderNew(ticker, symbol);
        }

    }

    private void checkAndCreateOrderNew(KlineObjectNumber ticker, String symbol) {
        BreadDetectObject breadData = BreadFunctions.calBreadDataAlt(ticker, RATE_BREAD_MIN_2TRADE);
        MAStatus maStatus = SimpleMovingAverageManager.getInstance().getMaStatus(Utils.getDate(ticker.startTime.longValue()), symbol);
        Double maValue = SimpleMovingAverageManager.getInstance().getMaValue(symbol, Utils.getDate(ticker.startTime.longValue()));
        Double rateMa = Utils.rateOf2Double(ticker.priceClose, maValue);

        Double rateChange = BreadFunctions.getRateChangeWithVolume(ticker.totalUsdt / 1000000);
        if (rateChange == null) {
//            LOG.info("Error rateChange with ticker: {} {}", symbol, Utils.toJson(ticker));
            return;
        }
//        try {
//            if (StringUtils.equals(symbol, "CELOUSDT") && ticker.startTime.equals(Utils.sdfFileHour.parse("20230401 23:30").getTime())) {
//                System.out.println("debug");
//            }
//        } catch (Exception e) {
//            e.printStackTrace();
//        }

//        if (breadData.orderSide != null
//                && breadData.orderSide.equals(OrderSide.BUY)
//                && maStatus != null && maStatus.equals(MAStatus.TOP)
//                && rateMa <= RATE_MA_MAX
//                && ticker.priceClose < ticker.ma20
//                && breadData.totalRate >= rateChange) {
        if (BreadFunctions.isAvailableTrade(breadData, ticker, maStatus, rateChange, rateMa, RATE_MA_MAX)) {
            LOG.info("Big:{} {} {} rate:{} volume: {}", symbol, new Date(ticker.startTime.longValue()), breadData.orderSide, breadData.totalRate, ticker.totalUsdt);
            if (BudgetManagerTest.getInstance().isAvailableTrade()) {
                createOrderNew(symbol, ticker, breadData);
            } else {
                LOG.info("Stop trade because capital over: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            }
        }
    }

    private void stopLossOrder(String symbol, KlineObjectNumber ticker) {
        String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol);
        if (StringUtils.isNotEmpty(json)) {
            OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
            LOG.info("Cancel order over 30d: {} {} {}!", Utils.toJson(symbol),
                    Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart), Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            orderInfo.priceTP = ticker.priceClose;
            orderInfo.status = OrderTargetStatus.STOP_LOSS_DONE;
            orderInfo.timeUpdate = ticker.startTime.longValue();
            orderInfo.tickerClose = ticker;
            allOrderDone.put(ticker.startTime.longValue() + "-" + orderInfo.symbol, orderInfo);
            RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, orderInfo.symbol);
        }
    }

    private void createOrderNew(String symbol, KlineObjectNumber ticker, BreadDetectObject breadData) {
        Double entry = ticker.priceClose * 1.002;
        Double priceTp = Utils.calPriceTarget(symbol, entry, OrderSide.BUY, RATE_TARGET);

        String log = OrderSide.BUY + " " + symbol + " entry: " + entry + " target: " + priceTp + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(BudgetManagerTest.getInstance().getBudget(), BudgetManagerTest.getInstance().getLeverage(), entry, symbol);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, quantity,
                LEVERAGE_ORDER, symbol, ticker.startTime.longValue(), ticker.endTime.longValue(), OrderSide.BUY);
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.rsi14 = ticker.rsi;
        order.ma20 = ticker.ma20;
        order.rateChange = breadData.totalRate;
        order.volume = breadData.volume;
        order.tickerOpen = ticker;
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER, symbol, Utils.toJson(order));
        BudgetManagerTest.getInstance().updateInvesting();
        LOG.info(log);
    }


}
