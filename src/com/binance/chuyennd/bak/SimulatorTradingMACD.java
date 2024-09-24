/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.bak;

import com.binance.chuyennd.indicators.MACDTradingController;
import com.binance.chuyennd.indicators.SimpleMovingAverage1DManager;
import com.binance.chuyennd.mongo.TickerMongoHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.research.OrderTargetInfoTest;
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

/**
 * @author pc
 */
public class SimulatorTradingMACD {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorTradingMACD.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";
    public final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public final Double RATE_MA_MAX = Configs.getDouble("RATE_MA_MAX");
    public final Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");
    public final Integer NUMBER_HOURS_STOP_MIN = Configs.getInt("NUMBER_HOURS_STOP_MIN");
    public final Double RATE_SUCCESS_STATISTIC = Configs.getDouble("RATE_SUCCESS_STATISTIC");
    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
    public final String TIME_RUN = Configs.getString("TIME_RUN");


    public static void main(String[] args) throws ParseException, IOException {
        SimulatorTradingMACD test = new SimulatorTradingMACD();
        test.initData();
        test.simulatorAllSymbol();
    }


    private void simulatorAllSymbol() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;

        Map<String, List<KlineObjectNumber>> symbol2LastTickers = new HashMap<>();
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers;
            time2Tickers = TickerMongoHelper.getInstance().getDataFromDb(startTime);
            for (Map.Entry<Long, Map<String, KlineObjectNumber>> entry : time2Tickers.entrySet()) {
                Long time = entry.getKey();
                Map<String, KlineObjectNumber> symbol2Ticker = entry.getValue();
                for (Map.Entry<String, KlineObjectNumber> entry1 : symbol2Ticker.entrySet()) {
                    String symbol = entry1.getKey();
                    KlineObjectNumber ticker = entry1.getValue();
                    List<KlineObjectNumber> tickers = symbol2LastTickers.get(symbol);
                    if (tickers == null) {
                        tickers = new ArrayList<>();
                        symbol2LastTickers.put(symbol, tickers);
                    }
                    tickers.add(ticker);
                    if (tickers.size() < 20) {
                        continue;
                    }
                    if (tickers.size() > 500) {
                        for (int i = 0; i < 50; i++) {
                            tickers.remove(0);
                        }
                    }
                    List<KlineObjectNumber> finalTickers = tickers;
                    startTradingSimulatorASymbol(symbol, finalTickers);
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
        RedisHelper.getInstance().get().del(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER);
        allOrderDone = new ConcurrentHashMap<>();
        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
            FileUtils.delete(new File(FILE_STORAGE_ORDER_DONE));
        }
        SimpleMovingAverage1DManager.getInstance();
        if (RATE_SUCCESS_STATISTIC != 0) {
            BreadFunctions.updateVolumeRateChange(NUMBER_HOURS_STOP_MIN, RATE_SUCCESS_STATISTIC);
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
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart)).append(" ").append(Utils.normalizeDateYYYYMMDDHHmm(currentTime)).append(" margin:").append(orderInfo.calMargin().longValue()).append(" ").append(orderInfo.side).append(" ").append(orderInfo.symbol).append(" ").append(" dcaLevel:").append(orderInfo.dynamicTP_SL).append(" ").append(orderInfo.priceEntry).append("->").append(orderInfo.lastPrice).append(" ").append(ratePercent.longValue()).append("%").append(" ").append(pnl.longValue()).append("$").append("\n");
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
        LOG.info(Utils.toJson(symbol2Counter));
//        Utils.sendSms2Telegram(reportRunning.toString());
    }

    private void startTradingSimulatorASymbol(String symbol, List<KlineObjectNumber> tickers) {
        // check running
        KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
        String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol);
        if (StringUtils.isNotEmpty(json)) {
            OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
            if (orderInfo.timeStart < ticker.startTime.longValue()) {
                orderInfo.updatePriceByKline(ticker);
                orderInfo.updateStatus();
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    allOrderDone.put(ticker.startTime.longValue() + "-" + symbol, orderInfo);
                    RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol);
                    checkAndCreateOrderNew(tickers, symbol);
                } else {
                    if (ticker.startTime > orderInfo.timeStart + NUMBER_HOURS_STOP_MIN * Utils.TIME_HOUR
                            || ticker.histogram < orderInfo.tickerOpen.histogram) {
//                    if (MACDTradingController.isMacdStopTrendBuy(tickers, tickers.size() - 1, orderInfo.timeStart)) {
                        stopLossOrder(symbol, ticker);
                    } else {
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol, Utils.toJson(orderInfo));
                    }
                }
            }
        } else {
            checkAndCreateOrderNew(tickers, symbol);
        }

    }

    private void checkAndCreateOrderNew(List<KlineObjectNumber> tickers, String symbol) {
        KlineObjectNumber ticker = tickers.get(tickers.size() - 1);
//        SimpleMovingAverage1DManager.getInstance().updateWithTicker(symbol, ticker);
//        MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(ticker.startTime.longValue(), symbol);
//        Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(ticker.startTime.longValue()));
//        Double rateMa = Utils.rateOf2Double(ticker.priceClose, maValue);
//        Double rateMaWithCurrentInterval = Utils.rateOf2Double(ticker.priceClose, ticker.ma20);
//        if (maValue == null) {
//            return;
//        }
        if (
                MACDTradingController.isMacdTrendUpAndTickerDown(tickers, tickers.size() - 1, 2.0)
//                && rateMaWithCurrentInterval < 0
//                && rateMa < 0.2
//                && maStatus != null && maStatus.equals(MAStatus.TOP)
        ) {
            LOG.info("Macd cut signal:{} {} {} volume: {}", symbol, new Date(ticker.startTime.longValue()), ticker.rsi, ticker.totalUsdt);
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
            LOG.info("Cancel order over macd: {} {} {}!", Utils.toJson(symbol), Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart), Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            orderInfo.priceTP = ticker.priceClose;
            orderInfo.status = OrderTargetStatus.STOP_LOSS_DONE;
            orderInfo.timeUpdate = ticker.startTime.longValue();
            orderInfo.tickerClose = ticker;
            allOrderDone.put(ticker.startTime.longValue() + "-" + orderInfo.symbol, orderInfo);
            RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, orderInfo.symbol);
        }
    }

    private void createOrderNew(String symbol, KlineObjectNumber ticker) {
        Double entry = ticker.priceClose * 1.002;
        Double priceTp = Utils.calPriceTarget(symbol, entry, OrderSide.BUY, RATE_TARGET);

        String log = OrderSide.BUY + " " + symbol + " entry: " + entry + " target: " + priceTp + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(BudgetManagerTest.getInstance().getBudget(), BudgetManagerTest.getInstance().getLeverage(), entry, symbol);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, quantity, LEVERAGE_ORDER, symbol, ticker.startTime.longValue(), ticker.endTime.longValue(), OrderSide.BUY);
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = ticker;
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol, Utils.toJson(order));
        BudgetManagerTest.getInstance().updateInvesting();
        LOG.info(log);
    }


}
