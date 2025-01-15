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
public class SimulatorMarketLevelTicker1MStopLoss {

    public static final Logger LOG = LoggerFactory.getLogger(SimulatorMarketLevelTicker1MStopLoss.class);
    public static final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";
    public static final String FILE_STORAGE_ORDER_ENTRIES = "storage/OrderEntries.data";

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;

    public String TIME_RUN = Configs.getString("TIME_RUN");
    public Map<Long, List<OrderTargetInfoTest>> time2Entries = new HashMap<>();

    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry = new ConcurrentHashMap();
    public ConcurrentHashMap<String, OrderTargetInfoTest> symbol2OrderRunning = new ConcurrentHashMap();

    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
        test.initData();
        if (new File(FILE_STORAGE_ORDER_ENTRIES).exists()) {
            LOG.info("Run with mode not init entry!");
            test.simulatorNotInitEntry(FILE_STORAGE_ORDER_ENTRIES);
        } else {
            LOG.info("Run with mode init entry!");
            test.simulatorWithInitEntry();
        }
    }

    public void runAOrder(String symbol, String time, OrderSide side) {
        MarketLevelChange levelChange = MarketLevelChange.TINY_DOWN;
        try {
            long startTime = Utils.sdfFileHour.parse(time).getTime();
            List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
            if (side.equals(OrderSide.BUY)) {
                createOrderBUY(symbol, tickers.get(0), levelChange, null, null);
            } else {
//                createOrderSELL(symbol, tickers.get(0), levelChange, null);
            }
            levelChange = MarketLevelChange.SMALL_DOWN_15M;
            createOrderBUY(symbol, tickers.get(1), levelChange, null, null);
            levelChange = MarketLevelChange.TINY_UP;
            createOrderBUY(symbol, tickers.get(6), levelChange, null, null);
            while (true) {
                for (KlineObjectSimple ticker : tickers) {
                    if (symbol2OrderRunning.isEmpty()) {
                        break;
                    }
                    startUpdateOldOrderTrading(symbol, ticker, null);
                    BudgetManagerSimple.getInstance().updateBalance(ticker.startTime.longValue(), allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                }
                for (OrderTargetInfoTest order : allOrderDone.values()) {
                    LOG.info("{} {} {} {} {} -> {} fundingfee: {} {}%", Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate),
                            order.side, order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart),
                            order.priceEntry, order.priceTP, order.calFundingFee(),
                            Utils.formatDouble(Utils.rateOf2Double(order.priceTP, order.priceEntry) * 100, 3));
                }
                if (symbol2OrderRunning.isEmpty()) {
                    break;
                }
                startTime = tickers.get(tickers.size() - 1).startTime.longValue();
                tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void runMultiOrder(List<String> symbols, String timeInput) {
        MarketLevelChange levelChange = MarketLevelChange.TINY_DOWN;
        try {
            long startTime = Utils.getDate(Utils.sdfFileHour.parse(timeInput).getTime());
            for (String symbol : symbols) {
                List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol,
                        Constants.INTERVAL_1M, Utils.sdfFileHour.parse(timeInput).getTime());
                createOrderBUY(symbol, tickers.get(0), levelChange, null, null);
            }
            //get data
            while (true) {
                TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
                try {
                    time2Tickers = DataManager.readDataFromFile1M(startTime);
                    if (time2Tickers != null) {
                        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                            Long time = entry.getKey();
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                                String symbol = entry1.getKey();
                                if (Constants.diedSymbol.contains(symbol)) {
                                    continue;
                                }
                                KlineObjectSimple ticker = entry1.getValue();
                                // update order Old
                                startUpdateOldOrderTrading(symbol, ticker, null);
                            }

                            if (time % Utils.TIME_DAY == 0) {
                                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, true);
                            } else {
                                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                            }
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
                Long finalStartTime1 = startTime;
                startTime += Utils.TIME_DAY;
                if (startTime > System.currentTimeMillis() || symbol2OrderRunning.isEmpty()) {
                    BudgetManagerSimple.getInstance().updateBalance(finalStartTime1, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                    break;
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void simulatorWithInitEntry(String... inputs) throws ParseException {
        Long timeWriteData = null;
        if (inputs.length > 1) {
            TIME_RUN = inputs[0];
            timeWriteData = Utils.sdfFileHour.parse(inputs[1]).getTime();
        }
        LOG.info("TimeWriteData: {}", timeWriteData);
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
        TreeMap<Long, Double> timeBtcReverse = new TreeMap<>();
        List<Double> lastRateDown15Ms = new ArrayList<>();
        List<Double> lastRateUp15Ms = new ArrayList<>();
        Double rateTrend = 0.01;
        Integer duration = 400;
        String fileNameBtcReverse = "storage/btc/btcReverse-" + rateTrend + "-" + duration;
        Boolean isRenewBtcTrend = true;
        if (new File(fileNameBtcReverse).exists()) {
            isRenewBtcTrend = false;
            timeBtcReverse = (TreeMap<Long, Double>) Storage.readObjectFromFile(fileNameBtcReverse);
        }
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
//                LOG.info("Read file ticker: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                time2Tickers = DataManager.readDataFromFile1M(startTime);

                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
//                        if (time == Utils.sdfFileHour.parse("20241106 14:42").getTime()) {
//                            System.out.println("Debug");
//                        }
                        Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                        Map<String, Double> symbol2MaxPrice = new HashMap<>();
                        Map<String, Double> symbol2MinPrice = new HashMap<>();
                        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                            String symbol = entry1.getKey();
                            if (Constants.diedSymbol.contains(symbol)) {
                                continue;
                            }
                            KlineObjectSimple ticker = entry1.getValue();
                            if (!Utils.isTickerAvailable(ticker)) {
                                continue;
                            }
                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                            if (tickers == null) {
                                tickers = new ArrayList<>();
                                symbol2LastTickers.put(symbol, tickers);
                            }
                            tickers.add(ticker);

                            int sizeRemove = 120;
                            if (Constants.SYMBOL_PAIR_BTC.equals(symbol) || Constants.altReverseSymbol.contains(symbol)) {
                                sizeRemove = duration + 20;
                            }
                            if (tickers.size() > sizeRemove) {
                                for (int i = 0; i < 20; i++) {
                                    tickers.remove(0);
                                }
                            }
                            Double priceMax = null;
                            Double minPrice = null;
                            for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                                int index = tickers.size() - i - 1;
                                if (index >= 0) {
                                    KlineObjectSimple kline = tickers.get(index);
                                    if (priceMax == null || priceMax < kline.maxPrice) {
                                        priceMax = kline.maxPrice;
                                    }
                                    if (minPrice == null || minPrice > kline.minPrice) {
                                        minPrice = kline.minPrice;
                                    }

                                }
                            }
                            symbol2MaxPrice.put(symbol, priceMax);
                            symbol2MinPrice.put(symbol, minPrice);
                            // update order Old
                            startUpdateOldOrderTrading(symbol, ticker, minPrice);
                        }
                        MarketDataObject marketData;
                        marketData = MarketBigChangeDetectorTest.calMarketData(symbol2Ticker, symbol2MaxPrice, symbol2MinPrice);
                        if (timeWriteData != null && timeWriteData.equals(time)) {
                            String fileName = "storage/data/rateMax15M/" + Utils.normalizeDateYYYYMMDD(time)
                                    + "/" + time + "_test";
                            Storage.writeObject2File(fileName, marketData.rate2Max);
                            fileName = "storage/data/rateDown1M/" + Utils.normalizeDateYYYYMMDD(time)
                                    + "/" + time + "_test";
                            Storage.writeObject2File(fileName, marketData.rateDown2Symbols);
                            LOG.info("Finish 2 write data! {}", fileName);
                            System.exit(1);
                        }
//                        Set<String> symbolLocked = getSymbolLocked();
//                        LOG.info("Check level market: {} DownAvg: {}% UpAvg:{}% DownAvg15M:{}%  UpAvg15M:{}% btcRate: {}% btcRate15M: {}%",
//                                Utils.normalizeDateYYYYMMDDHHmm(time),
//                                Utils.formatDouble(marketData.rateDownAvg * 100, 3), Utils.formatDouble(marketData.rateUpAvg * 100, 3),
//                                Utils.formatDouble(marketData.rateDown15MAvg * 100, 3), Utils.formatDouble(marketData.rateUp15MAvg * 100, 3),
//                                Utils.formatDouble(marketData.rateBtc * 100, 3), Utils.formatDouble(marketData.rateBtcDown15M * 100, 3));

                        Set<String> symbolLocked = new HashSet<>();
                        symbolLocked.addAll(getSymbolMarginBig(10));
                        TreeMap<Double, String> rate2Max = new TreeMap<>();
                        rate2Max.putAll(marketData.rate2Max);
//                        Double rateBtcMaxMin = calRateMaxAndMin(symbol2LastTickers.get(Constants.SYMBOL_PAIR_BTC));
                        if (marketData != null) {
                            MarketLevelChange levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                                    marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg, marketData.rateUp15MAvg,
                                    marketData.rateBtcDown15M);
                            if (levelChange != null) {
                                Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                                symbolLocked.addAll(getSymbolRunning(levelChange));
                                List<String> symbol2BUY = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(marketData.rate2Max,
                                        numberOrder, symbol2Ticker, symbolLocked);

                                symbol2BUY = addSpecialSymbol(symbol2BUY, levelChange, symbol2Ticker);
                                List<String> symbolDca = getDCA(levelChange);
                                LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2BUY);
                                // check create order new
                                for (String symbol : symbol2BUY) {
                                    KlineObjectSimple ticker = entry.getValue().get(symbol);
                                    createOrderBUY(symbol, ticker, levelChange, marketData, null);
                                }
                                for (String symbol : symbolDca) {
                                    KlineObjectSimple ticker = entry.getValue().get(symbol);
                                    createOrderBUY(symbol, ticker, MarketLevelChange.DCA_ORDER, marketData, null);
                                }

                            } else {
                                levelChange = MarketBigChangeDetectorTest.getMarketStatus15M(marketData.rateDown15MAvg,
                                        marketData.rateUp15MAvg, lastRateDown15Ms, lastRateUp15Ms);
                                if (levelChange != null) {
                                    symbolLocked.addAll(getSymbolRunning(levelChange));
                                    List<String> symbol2BUY = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(marketData.rate2Max,
                                            Configs.NUMBER_ENTRY_EACH_SIGNAL, symbol2Ticker, symbolLocked);
                                    LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2BUY);
                                    // check create order new
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = entry.getValue().get(symbol);
                                        createOrderBUY(symbol, ticker, levelChange, marketData, null);
                                    }
                                }
//                                 btc reverse
                                if (calMarginRunning() < 15 * BudgetManagerSimple.getInstance().getBudget()) {
                                    List<KlineObjectSimple> btcTickers = symbol2LastTickers.get(Constants.SYMBOL_PAIR_BTC);
                                    if (MarketBigChangeDetectorTest.isBtcReverseVolume(btcTickers)
                                            && marketData.rateDown15MAvg <= -0.018
                                            && marketData.rateBtcDown15M <= -0.007
                                    ) {
                                        levelChange = MarketLevelChange.BTC_REVERSE;
                                        symbolLocked.addAll(getSymbolRunning(levelChange));
                                        List<String> symbol2BUY = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(marketData.rate2Max,
                                                Configs.NUMBER_ENTRY_EACH_SIGNAL, symbol2Ticker, symbolLocked);

                                        // check create order new
                                        for (String symbol : symbol2BUY) {
                                            KlineObjectSimple ticker = entry.getValue().get(symbol);
                                            createOrderBUY(symbol, ticker, levelChange, marketData, null);
                                        }
                                    } else {
                                        if (MarketBigChangeDetectorTest.isBtcReverseBig15M(btcTickers)
                                                && marketData.rateDown15MAvg <= -0.018) {
                                            levelChange = MarketLevelChange.BTC_REVERSE_15M;
                                            symbolLocked.addAll(getSymbolRunning(levelChange));
                                            List<String> symbol2BUY = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(marketData.rate2Max,
                                                    Configs.NUMBER_ENTRY_EACH_SIGNAL, symbol2Ticker, symbolLocked);
                                            // check create order new
                                            for (String symbol : symbol2BUY) {
                                                KlineObjectSimple ticker = entry.getValue().get(symbol);
                                                createOrderBUY(symbol, ticker, levelChange, marketData, null);
                                            }
                                        }
                                    }
                                }
                                // BTC trend reverse
                                Double rateBtcTrendReverse;
                                if (isRenewBtcTrend || timeBtcReverse.lastKey() < time) {
                                    rateBtcTrendReverse = MarketBigChangeDetectorTest.isBtcTrendReverse(
                                            symbol2LastTickers.get(Constants.SYMBOL_PAIR_BTC), rateTrend);
                                } else {
                                    rateBtcTrendReverse = timeBtcReverse.get(time);
                                }
                                if (rateBtcTrendReverse != null) {
                                    timeBtcReverse.put(time, rateBtcTrendReverse);
                                    levelChange = MarketLevelChange.BTC_TREND_REVERSE;
                                    List<String> symbol2BUY = new ArrayList<>();
                                    for (String symbol : Constants.specialSymbol) {
                                        if (calMarginRunning(symbol) < 15 * BudgetManagerSimple.getInstance().getBudget()) {
                                            symbol2BUY.add(symbol);
                                        }
                                    }
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = entry.getValue().get(symbol);
                                        createOrderBUY(symbol, ticker, levelChange, marketData, null);
                                    }
                                }

                            }
                        }
                        if (time % Utils.TIME_DAY == 0) {
                            BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, true);
                        } else {
                            BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                        }
                        if (lastRateDown15Ms.size() > 100) {
                            while (lastRateDown15Ms.size() > 40) {
                                lastRateDown15Ms.remove(0);
                            }
                        }
                        lastRateDown15Ms.add(marketData.rateDown15MAvg);
                        if (lastRateUp15Ms.size() > 100) {
                            while (lastRateUp15Ms.size() > 40) {
                                lastRateUp15Ms.remove(0);
                            }
                        }
                        lastRateUp15Ms.add(marketData.rateUp15MAvg);
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            Long finalStartTime1 = startTime;
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                BudgetManagerSimple.getInstance().updateBalance(finalStartTime1, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                break;
            }
        }
        // add all order running to done
        for (
                List<OrderTargetInfoTest> orderRunning : symbol2OrdersEntry.values()) {
            for (OrderTargetInfoTest orderInfo : orderRunning) {
                orderInfo.maxPrice = symbol2OrderRunning.get(orderInfo.symbol).maxPrice;
                orderInfo.lastPrice = symbol2OrderRunning.get(orderInfo.symbol).lastPrice;
                orderInfo.priceTP = orderInfo.lastPrice;
                orderInfo.minPrice = symbol2OrderRunning.get(orderInfo.symbol).minPrice;
                orderInfo.timeUpdate = symbol2OrderRunning.get(orderInfo.symbol).timeUpdate;
                allOrderDone.put(-orderInfo.timeUpdate + allOrderDone.size(), orderInfo);
            }
        }

        String reportMinProfit = statisticResult(allOrderDone);
        LOG.info("Update-{}-{} {}", Configs.TIME_AFTER_ORDER_2_SL, BudgetManagerSimple.getInstance().levelRun, reportMinProfit);
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-"
                + Configs.TIME_AFTER_ORDER_2_SL, allOrderDone);
        Storage.writeObject2File("storage/orderRunning.data", symbol2OrderRunning);
        Storage.writeObject2File("storage/BalanceIndex.data", BudgetManagerSimple.getInstance().balanceIndex);
        Storage.writeObject2File(fileNameBtcReverse, timeBtcReverse);
//        Storage.writeObject2File(FILE_STORAGE_ORDER_ENTRIES, time2Entries);
        BudgetManagerSimple.getInstance().printBalanceIndex();

    }

    private Double calRateMaxAndMin(List<KlineObjectSimple> tickers) {
        if (tickers == null || tickers.isEmpty()) {
            return null;
        }
        Double priceMax = null;
        Double priceMin = null;
        for (KlineObjectSimple ticker : tickers) {
            if (priceMax == null || priceMax < ticker.maxPrice) {
                priceMax = ticker.maxPrice;
            }
            if (priceMin == null || priceMin > ticker.minPrice) {
                priceMin = ticker.minPrice;
            }
        }
        Double priceClose = tickers.get(tickers.size() - 1).priceClose;
        return Utils.rateOf2Double(priceMax, priceClose) / Utils.rateOf2Double(priceClose, priceMin);
    }

    private List<String> getDCA(MarketLevelChange levelChange) {

        List<String> symbols = new ArrayList<>();
        if (calMarginRunning() > 40 * BudgetManagerSimple.getInstance().getBudget()) {
            return symbols;
        }
        if (levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            for (String symbol : symbol2OrderRunning.keySet()) {
                OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
                if (order != null
                        && order.calRateLoss() < -0.05
                ) {
                    symbols.add(symbol);
                }
            }
        }
        if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)) {
            for (String symbol : symbol2OrderRunning.keySet()) {
                OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
                if (order != null
                        && order.calRateLoss() < -0.08
                ) {
                    symbols.add(symbol);
                }
            }
        }

        return symbols;
    }

    private void simulatorNotInitEntry(String fileName) throws ParseException {

        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<Long, List<OrderTargetInfoTest>> time2Entries = (Map<Long, List<OrderTargetInfoTest>>) Storage.readObjectFromFile(fileName);
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
                        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                            String symbol = entry1.getKey();
                            if (Constants.diedSymbol.contains(symbol)) {
                                continue;
                            }
                            KlineObjectSimple ticker = entry1.getValue();
                            // update order Old
                            startUpdateOldOrderTrading(symbol, ticker, null);
                        }
                        List<OrderTargetInfoTest> orders = time2Entries.get(time);
                        if (orders != null) {
                            for (OrderTargetInfoTest order : orders) {
                                KlineObjectSimple ticker = entry.getValue().get(order.symbol);
                                createOrderBUY(order.symbol, ticker, order.marketLevelChange, order.marketData, null);
                            }
                        }

                        if (time % Utils.TIME_DAY == 0) {
                            BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, true);
                        } else {
                            BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            Long finalStartTime1 = startTime;
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                BudgetManagerSimple.getInstance().updateBalance(finalStartTime1, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                break;
            }
        }
        // add all order running to done
        for (List<OrderTargetInfoTest> orderRunning : symbol2OrdersEntry.values()) {
            for (OrderTargetInfoTest orderInfo : orderRunning) {
                orderInfo.maxPrice = symbol2OrderRunning.get(orderInfo.symbol).maxPrice;
                orderInfo.lastPrice = symbol2OrderRunning.get(orderInfo.symbol).lastPrice;
                orderInfo.priceTP = orderInfo.lastPrice;
                orderInfo.minPrice = symbol2OrderRunning.get(orderInfo.symbol).minPrice;
                orderInfo.timeUpdate = symbol2OrderRunning.get(orderInfo.symbol).timeUpdate;
                allOrderDone.put(-orderInfo.timeUpdate + allOrderDone.size(), orderInfo);
            }
        }

        String reportMinProfit = statisticResult(allOrderDone);
        LOG.info("Update-{}-{} {}", Configs.TIME_AFTER_ORDER_2_SL, BudgetManagerSimple.getInstance().levelRun, reportMinProfit);
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-"
                + Configs.TIME_AFTER_ORDER_2_SL, allOrderDone);
        Storage.writeObject2File("storage/orderRunning.data", symbol2OrderRunning);
        BudgetManagerSimple.getInstance().printBalanceIndex();
    }

    private Set<String> getSymbolLocked() {
        Set<String> hashSet = new HashSet<>();
//        for (String symbol : symbol2OrdersEntry.keySet()) {
//            OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
//            if (orderMulti != null) {
////                if (orderMulti.calMargin() >= 5 * BudgetManagerSimple.getInstance().getBudget()
////                        && orderMulti.calRateLoss() < -0) {
////                    hashSet.add(symbol);
////                }
//                if (orderMulti.calRateLoss() < -0.1) {
//                    hashSet.add(symbol);
//                }
//            }
//        }
        return hashSet;
    }


    private List<String> addSpecialSymbol(List<String> symbol2BUY, MarketLevelChange levelChange,
                                          Map<String, KlineObjectSimple> symbol2Ticker) {
        if (levelChange != null && (levelChange.equals(MarketLevelChange.BIG_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN))
        ) {
            Set<String> symbol2Checks = new HashSet<>();
            if (calMarginRunning() < 30 * BudgetManagerSimple.getInstance().getBudget()) {
                symbol2Checks.addAll(Constants.specialSymbol);
                symbol2Checks.addAll(Constants.stableSymbol);
            }
            for (String symbol : symbol2Checks) {
                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                if (ticker != null && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.015) {
                    symbol2BUY.add(symbol);
                }
            }
        }
        if (levelChange != null && (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                || levelChange.equals(MarketLevelChange.TINY_DOWN))
        ) {
            Set<String> symbol2Checks = new HashSet<>();
            if (calMarginRunning() < 10 * BudgetManagerSimple.getInstance().getBudget()) {
                symbol2Checks.addAll(Constants.specialSymbol);
                symbol2Checks.addAll(Constants.stableSymbol);
            }
            for (String symbol : symbol2Checks) {
                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                if (ticker != null && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.018) {
                    symbol2BUY.add(symbol);
                }
            }
        }
        if (levelChange != null
                && (levelChange.equals(MarketLevelChange.BIG_UP)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP)
                || levelChange.equals(MarketLevelChange.SMALL_UP)
        )) {
            symbol2BUY.addAll(Constants.specialSymbol);
        }
        return symbol2BUY;
    }

    private List<String> addStableSymbol(List<String> symbol2BUY, MarketLevelChange levelChange,
                                         Map<String, KlineObjectSimple> symbol2Ticker) {
        if (levelChange != null && (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                || levelChange.equals(MarketLevelChange.TINY_DOWN))
        ) {
            for (String symbol : Constants.stableSymbol) {
                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                if (ticker != null && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.01) {
                    symbol2BUY.add(symbol);
                }
            }
        }
        return symbol2BUY;
    }

    public String statisticResult(TreeMap<Long, OrderTargetInfoTest> time2Order) {
        Map<MarketLevelChange, List<OrderTargetInfoTest>> level2Orders = new HashMap<>();
        List<Double> pnls = new ArrayList<>();
        List<Double> pnlNotMays = new ArrayList<>();
        List<Double> pnlNot2021 = new ArrayList<>();
        List<Double> pnl2024 = new ArrayList<>();
        Map<Double, String> pnl2Info = new HashMap<>();
        for (OrderTargetInfoTest orderInfo : time2Order.values()) {
            List<OrderTargetInfoTest> orders = level2Orders.get(orderInfo.marketLevelChange);
            if (orders == null) {
                orders = new ArrayList<>();
            }
            orders.add(orderInfo);
            level2Orders.put(orderInfo.marketLevelChange, orders);
            Double tp = orderInfo.calTp();
            pnl2Info.put(tp, orderInfo.symbol + "-" + Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart));
            pnls.add(tp);
            if (!StringUtils.equals(Utils.sdfFile.format(new Date(orderInfo.timeStart)), "20210519")) {
                pnlNotMays.add(tp);
            }
            if (!StringUtils.startsWith(Utils.sdfFile.format(new Date(orderInfo.timeStart)), "2021")) {
                pnlNot2021.add(tp);
            }
            if (StringUtils.startsWith(Utils.sdfFile.format(new Date(orderInfo.timeStart)), "2024")) {
                pnl2024.add(tp);
            }
        }
        TreeMap<Double, MarketLevelChange> rateProfit2Level = new TreeMap<>();
        for (MarketLevelChange level : level2Orders.keySet()) {
            List<OrderTargetInfoTest> orders = level2Orders.get(level);
            rateProfit2Level.put(-calRateProfit(orders), level);
        }
        StringBuilder builder = new StringBuilder();
        for (Double rate : rateProfit2Level.keySet()) {
            MarketLevelChange level = rateProfit2Level.get(rate);
            builder.append(level)
                    .append(" -> ")
                    .append(level2Orders.get(level).size())
                    .append(" ")
                    .append(Utils.formatDouble(-rate * 100, 3)).append("\t");
        }
        return "\tProfitMinAll: " + Utils.findMinSubarraySum(pnls.toArray(new Double[0]))
                + " " + pnl2Info.get(Utils.findMinSubarraySumIndex(pnls.toArray(new Double[0])))
                + "\tMinNotMay: " + Utils.findMinSubarraySum(pnlNotMays.toArray(new Double[0]))
                + " " + pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNotMays.toArray(new Double[0])))
                + "\tMinNot2021: " + Utils.findMinSubarraySum(pnlNot2021.toArray(new Double[0]))
                + " " + pnl2Info.get(Utils.findMinSubarraySumIndex(pnlNot2021.toArray(new Double[0])))
                + "\tMin2024: " + Utils.findMinSubarraySum(pnl2024.toArray(new Double[0]))
                + " " + pnl2Info.get(Utils.findMinSubarraySumIndex(pnl2024.toArray(new Double[0]))) + "\t" + builder;

    }

    private Double calRateProfit(List<OrderTargetInfoTest> orders) {
        Double rate = 0d;
        Double total = 0d;
        for (OrderTargetInfoTest order : orders) {
            total += order.calRateTp();
        }
        if (!orders.isEmpty()) {
            return total / orders.size();
        }
        return rate;
    }

    private Double calRateLoss(OrderTargetInfoTest order) {
        Double rate = 0d;
        if (order != null) {
            return order.calRateLoss();
        }
        return rate;
    }


    public void initData() throws IOException, ParseException {
        // clear Data Old
        allOrderDone = new TreeMap<>();
        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
            FileUtils.delete(new File(FILE_STORAGE_ORDER_DONE));
        }

    }

    private void startUpdateOldOrderTrading(String symbol, KlineObjectSimple ticker, Double minPrice) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
        if (orderMulti != null) {
            if (orderMulti.timeStart < ticker.startTime.longValue()) {
                orderMulti.updatePriceByKlineSimple(ticker);
                Double rateMin = 0d;
                if (minPrice != null) {
                    rateMin = Utils.rateOf2Double(ticker.priceClose, minPrice);
                }
                orderMulti.updateStatusNew(rateMin);
                orderMulti.updateFundingFee(ticker.startTime.longValue() + Utils.TIME_MINUTE);
                if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                        || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                        || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                    List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
                    orders.get(0).time2FundingFee.putAll(orderMulti.time2FundingFee);
                    for (OrderTargetInfoTest order : orders) {
                        order.timeUpdate = orderMulti.timeUpdate;
                        order.status = orderMulti.status;
                        order.priceTP = orderMulti.priceTP;
                        order.maxPrice = orderMulti.maxPrice;
                        order.minPrice = orderMulti.minPrice;
                        allOrderDone.put(-order.timeUpdate + allOrderDone.size(), order);
                        LOG.info("Order done: {}\t{}\t{}\t{} -> {}\t{}%\t{}", order.side, order.symbol, Utils.normalizeDateYYYYMMDDHHmm(order.timeStart),
                                order.priceEntry, order.priceTP, Utils.formatPercent(Utils.rateOf2Double(order.priceTP, order.priceEntry)), order.status);
                        BudgetManagerSimple.getInstance().updatePnl(order);
                    }
                    symbol2OrdersEntry.remove(symbol);
                    symbol2OrderRunning.remove(symbol);
                } else {
                    orderMulti.updateTPSL(rateMin);
//                    if (orderMulti.priceSL != null
//                            && !Constants.specialSymbol.contains(symbol)
//                            && calMarginRunning() < 30 * BudgetManagerSimple.getInstance().getBudget()
//                            && orderMulti.priceSL < orderMulti.priceEntry
//                            && Utils.rateOf2Double(orderMulti.lastPrice, orderMulti.priceSL) < 0.03
//                            && !orderMulti.marketLevelChange.equals(MarketLevelChange.DCA_ORDER)) {
//                        createOrderBUY(symbol, ticker, MarketLevelChange.DCA_ORDER, null, null);
//                    }
                }
            }
        }
    }

    private OrderTargetInfoTest mergeOrder(List<OrderTargetInfoTest> orders, KlineObjectSimple ticker) {
        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        String symbol = orders.get(0).symbol;
        Double quantity = 0d;
        String priceEntry = "";
        Double margin = 0d;
        for (OrderTargetInfoTest orderInfo : orders) {
            time2Order.put(orderInfo.timeStart, orderInfo);
            margin += orderInfo.priceEntry * orderInfo.quantity;
            quantity += orderInfo.quantity;
            priceEntry += orderInfo.priceEntry + "-";
        }
        double entry = margin / quantity;
        OrderTargetInfoTest orderResult = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry,
                null, quantity, BudgetManagerSimple.getInstance().getLeverage(symbol),
                time2Order.lastEntry().getValue().symbol,
                time2Order.lastEntry().getKey(),
                time2Order.lastEntry().getKey(), orders.get(0).side);
        orderResult.minPrice = ticker.priceClose;
        orderResult.lastPrice = ticker.priceClose;
        orderResult.maxPrice = ticker.priceClose;
        orderResult.tickerOpen = time2Order.lastEntry().getValue().tickerOpen;
        orderResult.marketLevelChange = time2Order.lastEntry().getValue().marketLevelChange;

        if (orders.size() > 2) {
            LOG.info("Merger orders of {}: {} -> {}", orders.get(0).symbol, priceEntry, orderResult.priceEntry);
        }
        return orderResult;
    }


    public void createOrderBUY(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange,
                               MarketDataObject marketData, Double maxRate) {

        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage(symbol);
        Double marginRunning = calMarginRunning();
        if (levelChange.equals(MarketLevelChange.BIG_UP)
                || levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            if (!Constants.specialSymbol.contains(symbol)
            ) {
                budget = budget * 2;
            }
        }
        if (marginRunning <= 40 * BudgetManagerSimple.getInstance().getBudget()
                && (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP))
        ) {
            if (!Constants.specialSymbol.contains(symbol)
            ) {
                budget = budget * 2;
            }
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                || levelChange.equals(MarketLevelChange.SMALL_UP)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                || levelChange.equals(MarketLevelChange.TINY_DOWN)
        ) {
            if (Constants.specialSymbol.contains(symbol)
                    || StringUtils.equals(symbol, Constants.SYMBOL_PAIR_ETH)
            ) {
                budget = budget / 2;
            }
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                || levelChange.equals(MarketLevelChange.TINY_UP)
                || levelChange.equals(MarketLevelChange.BTC_REVERSE)
                || levelChange.equals(MarketLevelChange.BTC_REVERSE_15M)

        ) {
            budget = budget / 2;
        }

        if (levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
                || levelChange.equals(MarketLevelChange.ALT_TREND_REVERSE)
                || levelChange.equals(MarketLevelChange.DCA_ORDER)
                || levelChange.equals(MarketLevelChange.TINY_DOWN_15M)
                || levelChange.equals(MarketLevelChange.BTC_BIG_DOWN)
        ) {
            if (calMarginRunning(symbol) < BudgetManagerSimple.getInstance().getBudget() / 2) {
                budget = budget / 3;
            } else {
                budget = budget / 6;
            }
        }

        if (calMarginRunning() < 20 * BudgetManagerSimple.getInstance().getBudget()) {
            if (levelChange.equals(MarketLevelChange.TINY_DOWN)
                    || levelChange.equals(MarketLevelChange.TINY_UP)
                    || levelChange.equals(MarketLevelChange.SMALL_DOWN)
                    || levelChange.equals(MarketLevelChange.SMALL_UP)
            ) {
                budget = budget * 2;
            }
        }

        if (calMarginRunning() > 20 * BudgetManagerSimple.getInstance().getBudget()) {
            if (levelChange.equals(MarketLevelChange.MINI_DOWN)
            ) {
                budget = budget / 2;
            }
        }
        if (marginRunning > 40 * BudgetManagerSimple.getInstance().getBudget()) {
            if (levelChange.equals(MarketLevelChange.BIG_UP)
                    || levelChange.equals(MarketLevelChange.BIG_DOWN)
                    || levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                    || levelChange.equals(MarketLevelChange.MEDIUM_UP)
            ) {
                budget = budget / 2;
            }
        }
//        if (marginRunningTotal > 70 * BudgetManagerSimple.getInstance().getBudget()) {
//            budget = budget / 2;
//        }
//        if (marginRunningTotal > 80 * BudgetManagerSimple.getInstance().getBudget()) {
//            budget = budget / 3;
//        }
        if (marginRunning > 50 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 2;
        }
        if (marginRunning > 60 * BudgetManagerSimple.getInstance().getBudget()) {
            budget = budget / 4;
        }


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
        order.marketLevelChange = levelChange;
        order.rateChange = maxRate;
        order.ordersRunning = counterOrderRunning();
        order.unProfitTotal = BudgetManagerSimple.getInstance().calUnrealizedProfitMin(symbol2OrderRunning.values());
        order.slTotal = BudgetManagerSimple.getInstance().calProfitLossMax(symbol2OrderRunning.values());
        order.marginRunning = BudgetManagerSimple.getInstance().calPositionMargin(symbol2OrderRunning.values());
        order.marginRealRunning = BudgetManagerSimple.getInstance().calPositionMarginReal(symbol2OrderRunning.values());
        if (marketData != null) {
            marketData.rateDown2Symbols.clear();
            marketData.rate2Max.clear();
            marketData.symbol2PriceMax15M.clear();
            order.marketData = marketData;
        }
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);
        LOG.info(log);
        symbol2OrdersEntry.put(symbol, orders);
        symbol2OrderRunning.put(symbol, mergeOrder(orders, ticker));
        // update list entry to write file
        List<OrderTargetInfoTest> entries = time2Entries.get(order.timeStart);
        if (entries == null) {
            entries = new ArrayList<>();
        }
        entries.add(order);
        time2Entries.put(order.timeStart, entries);

        BudgetManagerSimple.getInstance().updateMaxOrderRunning(counterOrderRunning());
    }

    private Integer counterOrderRunning() {
        Integer counter = 0;
        for (List<OrderTargetInfoTest> orders : symbol2OrdersEntry.values()) {
            if (orders != null) {
                counter += orders.size();
            }
        }
        return counter;
    }

    private Double calMarginRunning() {
        Double marginTotal = 0d;
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            marginTotal += order.calMargin();
        }
        return marginTotal;
    }

    private Double calMarginRunningTotal() {
        Double marginTotal = 0d;
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            marginTotal += order.calMargin() - order.calProfit();
        }
        return marginTotal;
    }


    private Double calMarginRunningNotLevel(MarketLevelChange level) {
        Double marginTotal = 0d;
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (!order.marketLevelChange.equals(level)) {
                marginTotal += order.calMargin();
            }
        }
        return marginTotal;
    }

    private Double calMarginRunning(String symbol) {
        Double marginTotal = 0d;
        OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
        if (order != null) {
            return order.calMargin();
        }
        return marginTotal;
    }

    private Set<String> getSymbolRunning(MarketLevelChange level) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.marketLevelChange.equals(level)) {
                hashSet.add(order.symbol);
            }
        }
        return hashSet;
    }

    private Set<String> getSymbolMarginBig(Integer numberBudget) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.calMargin() > BudgetManagerSimple.getInstance().getBudget() * numberBudget) {
                hashSet.add(order.symbol);
            }
        }
        return hashSet;
    }

    private Set<String> getSymbolRunningBUYLoss(Double rateLoss) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.side.equals(OrderSide.BUY)) {
                if (order.calRateLoss() < rateLoss) {
                    hashSet.add(order.symbol);
                }
            }
        }
        return hashSet;
    }

    //    private Set<String> getSymbolLockByMargin(Integer rate) {
//        Set<String> hashSet = new HashSet<>();
//        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
//            if (order.side.equals(OrderSide.BUY)) {
//                if (order.calMargin() > BudgetManagerSimple.getInstance().getBudget() * rate) {
//                    hashSet.add(order.symbol);
//                }
//            }
//        }
//        return hashSet;
//    }
    private Set<String> getSymbolRunningSELLLoss(Double rateLoss) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.side.equals(OrderSide.SELL)) {
                if (order.calRateLoss() < rateLoss) {
                    hashSet.add(order.symbol);
                }
            }
        }
        return hashSet;
    }
}
