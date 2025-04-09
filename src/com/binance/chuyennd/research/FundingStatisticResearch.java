/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
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
public class FundingStatisticResearch {

    public static final Logger LOG = LoggerFactory.getLogger(FundingStatisticResearch.class);
    public static final String FILE_STORAGE_ORDER_DONE = "storage/FundingStatisticResearch.data";

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;

    public String TIME_RUN = Configs.getString("TIME_RUN");
    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrderRunning = new ConcurrentHashMap();

    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        FundingStatisticResearch test = new FundingStatisticResearch();
        test.initData();
        test.simulatorWithInitEntry();

//        TreeMap<Long, Set<String>> symbolsTest = test.extractSymbolFundingChange();
//        for (Long time : symbolsTest.keySet()) {
////            if (Utils.getDate(time) == Utils.getDate(Utils.sdfFileHour.parse("20250127 00:00").getTime())) {
//                LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(time), symbolsTest.get(time));
////            }
//        }
        startWriteRate24h();
    }

    public static boolean isTimeGetData() {
        long time = System.currentTimeMillis();
        long second = (time / Utils.TIME_SECOND) % 60;
        long miniSecond = (time % Utils.TIME_SECOND);
        return second == 0 && miniSecond < 10;
    }

    private static void startWriteRate24h() {
        Map<Long, Double> time2Rate24h = new HashMap<>();
        int counter = 0;
        while (true) {
            try {
                if (isTimeGetData()) {
                    time2Rate24h.put(Utils.getMinute(System.currentTimeMillis()), TickerFuturesHelper.getRate24hAvg());
                    counter++;
                    if (counter > 60) {
                        Storage.writeObject2File("storage/time2rate24hAvgLive.data", time2Rate24h);
                    }
                }
                Thread.sleep(10);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    public void simulatorWithInitEntry(String... inputs) throws ParseException {
        Map<Long, Set<String>> time2Symbol = MarketBigChangeDetectorTest.extractSymbolFundingChange();

        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();

        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                LOG.info("Read file ticker: {} orderRunning:{} orders done:{} orders {}", Utils.normalizeDateYYYYMMDDHHmm(startTime),
                        symbol2OrderRunning.size(), allOrderDone.size(), Utils.statisticRateSuccessTree(allOrderDone));
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        Set<String> symbolTrade = time2Symbol.get(time + Utils.TIME_MINUTE);

                        Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                        KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
                        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                            String symbol = entry1.getKey();
                            KlineObjectSimple ticker = entry1.getValue();
                            if (!Utils.isTickerAvailable(ticker)) {
                                continue;
                            }
                            // update order Old
                            startUpdateOldOrderTrading(symbol, ticker);
                        }
                        if (symbolTrade != null) {
                            for (String symbol : symbolTrade) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (Utils.isTickerAvailable(ticker)) {
                                    createOrderBUY(symbol, ticker);
                                }
                            }
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            Long finalStartTime1 = startTime;
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
        // add all order running to done
        for (List<OrderTargetInfoTest> orderRunning : symbol2OrderRunning.values()) {
            for (OrderTargetInfoTest orderInfo : orderRunning) {
                orderInfo.priceTP = orderInfo.lastPrice;
                allOrderDone.put(-orderInfo.timeStart + allOrderDone.size(), orderInfo);
            }
        }
//        Storage.writeObject2File("storage/time2rate24hAvg.data", time2Rate24h);
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-" + Configs.TIME_AFTER_ORDER_2_SL, allOrderDone);
    }




    public void initData() throws IOException, ParseException {
        // clear Data Old
        allOrderDone = new TreeMap<>();
        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
            FileUtils.delete(new File(FILE_STORAGE_ORDER_DONE));
        }

    }

    private void startUpdateOldOrderTrading(String symbol, KlineObjectSimple ticker) {
        List<OrderTargetInfoTest> orders = symbol2OrderRunning.get(symbol);
        List<OrderTargetInfoTest> ordersDone = new ArrayList<>();
        if (orders != null) {
            for (OrderTargetInfoTest order : orders) {
                if (order.timeStart < ticker.startTime.longValue()) {
                    order.updatePriceByKlineSimple(ticker);
                    if (order.timeUpdate - order.timeStart > 2 * Utils.TIME_DAY) {
                        allOrderDone.put(-order.timeStart + allOrderDone.size(), order);
                        ordersDone.add(order);
                    }
                }
            }
            if (!ordersDone.isEmpty()) {
                orders.removeAll(ordersDone);
            }
        }
    }

    public void createOrderBUY(String symbol, KlineObjectSimple ticker) {

        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
        String log = OrderSide.BUY + " " + symbol + " entry: " + entry +
                " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantityTest(budget, leverage, entry, symbol);

        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
            Double minBtcTrade = BudgetManagerSimple.getInstance().balanceBasic.longValue() / 1E6;
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
        List<OrderTargetInfoTest> orders = symbol2OrderRunning.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);
        LOG.info(log);
        symbol2OrderRunning.put(symbol, orders);
    }

//    public void runAOrder(String symbol, String time, OrderSide buy) {
//
//        try {
//            long startTime = Utils.sdfFileHour.parse(time).getTime();
//            List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
//            createOrderBUY(symbol, tickers.get(0), null);
//            while (true) {
//                for (KlineObjectSimple ticker : tickers) {
//                    if (symbol2OrderRunning.isEmpty()) {
//                        break;
//                    }
//                    startUpdateOldOrderTrading(symbol, ticker, null);
//                }
//                for (OrderTargetInfoTest order : allOrderDone.values()) {
//                    LOG.info("{} {} {} {} {} -> {} fundingfee: {} {}%", Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate),
//                            order.side, order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart),
//                            order.priceEntry, order.priceTP, order.calFundingFee(),
//                            Utils.formatDouble(Utils.rateOf2Double(order.priceTP, order.priceEntry) * 100, 3));
//                }
//                if (symbol2OrderRunning.isEmpty()) {
//                    break;
//                }
//                startTime = tickers.get(tickers.size() - 1).startTime.longValue();
//                tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
//            }
//
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//    }
}
