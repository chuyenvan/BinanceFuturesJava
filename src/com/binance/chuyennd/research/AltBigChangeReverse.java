/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.bigchange.test.TraceOrderDone;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
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
public class AltBigChangeReverse {

    public static final Logger LOG = LoggerFactory.getLogger(AltBigChangeReverse.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/" + AltBigChangeReverse.class.getSimpleName() + ".data";
    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersRunning = new ConcurrentHashMap();
//    public ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning = new ConcurrentHashMap();

    public static void main(String[] args) throws ParseException, IOException {
        AltBigChangeReverse test = new AltBigChangeReverse();
        test.initData();
        test.statisticAll();
    }


    private void statisticAll() throws ParseException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        TreeMap<Long, List<String>> time2Entry = new TreeMap<>();

        String fileMarketChangeLevelData = "target/entry/time2Market_" + Configs.NUMBER_TICKER_CAL_RATE_CHANGE + ".data";

        Map<Long, MarketDataObject> timeTradeMarket = new HashMap<>();
        if (new File(fileMarketChangeLevelData).exists()) {
            timeTradeMarket = (Map<Long, MarketDataObject>) Storage.readObjectFromFile(fileMarketChangeLevelData);
        }
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
            try {
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                LOG.info("Read file: {} {}", Utils.normalizeDateYYYYMMDD(startTime), time2Entry.size());
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        if (timeTradeMarket.containsKey(time)) {
                            continue;
                        }

                        Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                        // update order Old
                        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                            String symbol = entry1.getKey();
                            if (Constants.diedSymbol.contains(symbol)) {
                                continue;
                            }

                            KlineObjectSimple ticker = entry1.getValue();
                            startUpdateOldOrderTrading(symbol, ticker);
                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                            if (tickers == null) {
                                tickers = new ArrayList<>();
                                symbol2LastTickers.put(symbol, tickers);
                            }
                            tickers.add(ticker);
                            if (tickers.size() > 100) {
                                for (int i = 0; i < 50; i++) {
                                    tickers.remove(0);
                                }
                            }
                            Double volumeTotal = 0d;
                            Double volumeMax = 0d;
                            for (int i = 0; i < tickers.size() - 1; i++) {
                                KlineObjectSimple tickerCheck = tickers.get(i);
                                volumeTotal += tickerCheck.totalUsdt;
                                if (volumeMax < tickerCheck.totalUsdt) {
                                    volumeMax = tickerCheck.totalUsdt;
                                }
                            }

                            if (MarketBigChangeDetectorTest.isAltReverse15M(tickers)) {
                                List<String> symbolsEntry = time2Entry.get(ticker.startTime.longValue());
                                if (symbolsEntry == null) {
                                    symbolsEntry = new ArrayList<>();
                                    time2Entry.put(ticker.startTime.longValue(), symbolsEntry);
                                }
                                symbolsEntry.add(symbol);
                                createOrderBUYTarget(symbol, ticker);
                            }

                        }
                    }
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
        Storage.writeObject2File("target/entry/volumeBigSignal1MBuy.data", time2Entry);
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
        try {
            TraceOrderDone.printOrderTestDone(FILE_STORAGE_ORDER_DONE, "storage/" + AltBigChangeReverse.class.getSimpleName() + ".csv");
        } catch (Exception e) {
            e.printStackTrace();
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
        List<OrderTargetInfoTest> orderDone = new ArrayList<>();
        List<OrderTargetInfoTest> orders = symbol2OrdersRunning.get(symbol);
        if (orders == null) {
            return;
        }
        for (OrderTargetInfoTest orderInfo : orders) {
            if (orderInfo.timeStart < ticker.startTime.longValue()) {
                orderInfo.updatePriceByKlineSimple(ticker);
                orderInfo.updateStatusNew();
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                        || orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                        || orderInfo.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                    allOrderDone.put(orderInfo.timeStart + "-" + symbol, orderInfo);
                    BudgetManagerSimple.getInstance().updatePnl(orderInfo);
                    orderDone.add(orderInfo);
                } else {
                    orderInfo.updateTPSL();
                }
            }
        }
        if (!orderDone.isEmpty()) {
            symbol2OrdersRunning.get(symbol).removeAll(orderDone);
        }
    }


    private void createOrderBUYTarget(String symbol, KlineObjectSimple ticker) {
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
        List<OrderTargetInfoTest> orders = symbol2OrdersRunning.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);
        symbol2OrdersRunning.put(symbol, orders);

        LOG.info(log);
    }

    private void initData() throws IOException, ParseException {
        // clear Data Old
        allOrderDone = new ConcurrentHashMap<>();
    }
}
