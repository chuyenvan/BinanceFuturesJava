/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * @author pc
 */
public class Market24hChangeTotal {

    public static final Logger LOG = LoggerFactory.getLogger(Market24hChangeTotal.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/" + Market24hChangeTotal.class.getSimpleName() + ".data";
    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
    public ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning = new ConcurrentHashMap();

    public static void main(String[] args) throws ParseException, IOException {
        Market24hChangeTotal test = new Market24hChangeTotal();
        test.initData();
        test.statisticAll();
    }


    private void statisticAll() throws ParseException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        TreeMap<Long, List<String>> time2Entry = new TreeMap<>();
        //get data
        TreeMap<Long, Map<String, KlineObjectSimple>> lastDate2Tickers = null;
        Double rateMin = 0d;
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                LOG.info("Read file: {} {}", Utils.normalizeDateYYYYMMDD(startTime), time2Entry.size());
                if (time2Tickers != null && lastDate2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                        double totalRate = 0d;
                        // update order Old
                        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                            String symbol = entry1.getKey();
                            KlineObjectSimple ticker = entry1.getValue();
                            if (Constants.diedSymbol.contains(symbol)) {
                                continue;
                            }
                            Map<String, KlineObjectSimple> symbol2Ticker24hAgo = lastDate2Tickers.get(time - Utils.TIME_DAY);
                            if (symbol2Ticker24hAgo != null) {
                                KlineObjectSimple ticker24hAgo = symbol2Ticker24hAgo.get(symbol);
                                if (ticker24hAgo != null) {
                                    totalRate += Utils.rateOf2Double(ticker.priceClose, ticker24hAgo.priceOpen);
                                }
                            }
                        }
                        if (rateMin > totalRate) {
                            rateMin = totalRate;
//                            LOG.info("{} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time)
//                                    , Utils.sdfGoogle.format(new Date(time)), lastTotalRate, totalRate);
                        }
                        if (totalRate - rateMin > 10) {
                            LOG.info("----------{} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time)
                                    , Utils.sdfGoogle.format(new Date(time)), rateMin, totalRate);
                            rateMin = totalRate;
                        }
                    }
                }
                lastDate2Tickers = time2Tickers;
            } catch (Exception e) {
                e.printStackTrace();
            }
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
        exitWhenDone();
    }


    private void exitWhenDone() {
        try {
            Thread.sleep(10 * Utils.TIME_SECOND);
            System.exit(1);
        } catch (Exception e) {
            e.printStackTrace();
        }
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


    private void createOrderBUYTarget(String symbol, KlineObjectSimple ticker, Double volumeChange) {
        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage(symbol);
        String log = OrderSide.BUY + " " + symbol + " entry: " + entry + " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);
//        Double priceTp = Utils.calPriceTarget(symbol, entry, OrderSide.BUY, 3 * Configs.RATE_TARGET);
//        Double priceSL = Utils.calPriceTarget(symbol, entry, OrderSide.SELL, 3 * Configs.RATE_TARGET);
        Double priceTp = null;
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BUY);
//        order.priceSL = priceSL;
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        order.rateChange = volumeChange;
        orderRunning.put(symbol, order);

        LOG.info(log);
    }

    private void initData() throws IOException, ParseException {
        // clear Data Old
        allOrderDone = new ConcurrentHashMap<>();
    }
}
