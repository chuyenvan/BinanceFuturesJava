/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.bigchange.test.TraceOrderDone;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
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
public class BtcBigChangeAndBread {

    public static final Logger LOG = LoggerFactory.getLogger(BtcBigChangeAndBread.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/OrderSpecialDone.data";

    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
    public ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning = new ConcurrentHashMap();

    public static void main(String[] args) throws ParseException, IOException {
        BtcBigChangeAndBread test = new BtcBigChangeAndBread();
        test.initData();
        List<KlineObjectSimple> tickers = getTickerFullBtc1M();

//        long startTime = Utils.sdfFileHour.parse("20241015 20:00").getTime();
//        List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime("BTCUSDT",
//                Constants.INTERVAL_1M, startTime);
//        LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(0).startTime.longValue()),
//                Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()));

        Set<Long> timeTrendReverse = new HashSet<>();
        for (int i = 0; i < tickers.size(); i++) {
            KlineObjectSimple ticker = tickers.get(i);
            if (isBtcTrendReverse(tickers, i)) {
                timeTrendReverse.add(ticker.startTime.longValue());
            }
        }
        LOG.info("Last btcTicker: {}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()));
        Storage.writeObject2File("target/time_btc_trend_reverse.data", timeTrendReverse);
        LOG.info("Total have {} times reverse", timeTrendReverse.size());
//        test.statisticAll();
    }

    public static boolean isTimeSell(List<KlineObjectSimple> btcTickers, int index) {
        int period = 15;
        if (index < period + 3) {
            return false;
        }
        KlineObjectSimple lastTicker = btcTickers.get(index);
        // check sideway in 2h and not volume big
        Double volumeTotal = 0d;
        Double volumeMax = null;
        Double maxPrice = null;
        for (int i = 3; i < period + 3; i++) {
            KlineObjectSimple ticker = btcTickers.get(index - i);
            if (volumeMax == null || volumeMax < ticker.totalUsdt) {
                volumeMax = ticker.totalUsdt;
            }
            if (maxPrice == null || maxPrice < ticker.maxPrice) {
                maxPrice = ticker.maxPrice;
            }
            volumeTotal += ticker.totalUsdt;
        }
        double volumeAvg = volumeTotal / period;
        if (lastTicker.totalUsdt > 10 * volumeAvg
                && Utils.rateOf2Double(lastTicker.priceClose, lastTicker.priceOpen) < -0.001
                && lastTicker.maxPrice >= maxPrice
        ) {
            LOG.info("IsBtcSingalSell: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()),
                    lastTicker.priceClose, lastTicker.totalUsdt / volumeAvg);
            return true;
        }
        return false;
    }

    private static List<KlineObjectSimple> getTickerFullBtc1M() {

        String fileName = Configs.FOLDER_TICKER_1M + Constants.SYMBOL_PAIR_BTC;
        List<KlineObjectSimple> tickers = null;
        if (new File(fileName).exists()) {
            try {
                tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(fileName);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        if (tickers == null) {
            tickers = new ArrayList<>();
            try {
                Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
                while (true) {
                    LOG.info("Get data: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                    tickers.addAll(TickerFuturesHelper.getTickerSimpleWithStartTime(Constants.SYMBOL_PAIR_BTC,
                            Constants.INTERVAL_1M, startTime));
                    startTime = startTime + 500 * Utils.TIME_MINUTE;
                    if (startTime > System.currentTimeMillis()) {
                        break;
                    }
                }
                Storage.writeObject2File(fileName, tickers);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return tickers;
    }


    private void statisticAll() throws ParseException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                LOG.info("Read file ticker: {} orderRunning:{} orders done:{} orders {}", Utils.normalizeDateYYYYMMDDHHmm(startTime),
                        orderRunning.size(), allOrderDone.size(), statisticRateSuccess());
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                Set<Long> timeBtcReverse = (Set<Long>) Storage.readObjectFromFile("target/time_btc_reverse.data");
                Set<String> timesTradeMarket = (Set<String>) Storage.readObjectFromFile("target/time_trade_market.data");
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
//                        if (time == Utils.sdfFileHour.parse("20240904 21:00").getTime()) {
//                            System.out.println("Debug");
//                        }
                        Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                        TreeMap<Double, String> symbol2MaxPrice = new TreeMap<>();

                        // update order Old
                        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                            String symbol = entry1.getKey();
                            if (Constants.diedSymbol.contains(symbol)) {
                                continue;
                            }
                            if (Constants.specialSymbol.contains(symbol)) {
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
                            if (tickers.size() > 50) {
                                for (int i = 0; i < 30; i++) {
                                    tickers.remove(0);
                                }
                            }
                            Double priceMax = null;
                            for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                                int index = tickers.size() - i - 1;
                                if (index >= 0) {
                                    KlineObjectSimple kline = tickers.get(index);
                                    if (priceMax == null || priceMax < kline.maxPrice) {
                                        priceMax = kline.maxPrice;
                                    }
                                }
                            }
                            symbol2MaxPrice.put(Utils.rateOf2Double(ticker.priceClose, priceMax), symbol);

                        }
                        if (!timesTradeMarket.contains(time)) {
                            if (timeBtcReverse.contains(time)) {
                                MarketLevelChange levelChange = MarketLevelChange.BTC_REVERSE;
                                List<String> symbol2Trade = MarketBigChangeDetectorTest.getTopSymbolSimple(symbol2MaxPrice,
                                        Configs.NUMBER_ENTRY_EACH_SIGNAL / 2, orderRunning.keySet());
                                LOG.info("{} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2Trade, symbol2MaxPrice.size());
                                for (String symbol : symbol2Trade) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    createOrderBUYTarget(symbol, ticker, levelChange);
                                }
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
        // add all order running to done

        for (OrderTargetInfoTest orderInfo : orderRunning.values()) {
            orderInfo.priceTP = orderInfo.lastPrice;
            allOrderDone.put(orderInfo.timeStart + "-" + orderInfo.symbol, orderInfo);
        }
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);

        try {
            TraceOrderDone.printOrderTestDone(FILE_STORAGE_ORDER_DONE, "storage/bct_reverse.csv");
        } catch (Exception e) {
            e.printStackTrace();
        }
        exitWhenDone();

    }

    public static boolean isBtcReverse(List<KlineObjectSimple> btcTickers, int index) {
        int period = 27;
        if (index < period + 3) {
            return false;
        }
        int size = btcTickers.size();
        KlineObjectSimple lastTicker = btcTickers.get(index);
        // check sideway in 2h and not volume big
        Double volumeTotal = 0d;
        Double volumeMax = null;
        Double minPrice = null;
        Double maxPrice = null;
        for (int i = 0; i < period + 3; i++) {
            KlineObjectSimple ticker = btcTickers.get(index - i);
            if (volumeMax == null || volumeMax < ticker.totalUsdt) {
                volumeMax = ticker.totalUsdt;
            }
            if (minPrice == null || minPrice > ticker.minPrice) {
                minPrice = ticker.minPrice;
            }
            if (maxPrice == null || maxPrice < ticker.maxPrice) {
                maxPrice = ticker.maxPrice;
            }
            volumeTotal += ticker.totalUsdt;
        }
        double volumeAvg = volumeTotal / period;
        try {
            if (lastTicker.startTime.longValue() == Utils.sdfFileHour.parse("20241011 01:09").getTime()) {
                LOG.info("TimeCheck: {} {} {}", maxPrice, lastTicker.priceClose, Utils.rateOf2Double(lastTicker.priceClose, maxPrice));
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        if (
                Utils.rateOf2Double(lastTicker.priceClose, maxPrice) < -0.012
//                lastTicker.totalUsdt > 10 * volumeAvg
//                        && lastTicker.priceClose < minPrice
                        && Utils.rateOf2Double(lastTicker.priceClose, lastTicker.priceOpen) < -0.002
        ) {
            LOG.info("IsBtcReverse: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()),
                    lastTicker.priceClose, lastTicker.totalUsdt / volumeAvg);
            return true;
        }
        return false;
    }

    public static boolean isBtcTrendReverse(List<KlineObjectSimple> btcTickers, int index) {
        int period = 300;
        KlineObjectSimple lastTicker = btcTickers.get(index);
        Double priceReverse = null;
        Integer indexMin = null;
        for (int i = 0; i < period; i++) {
            if (index >= i + 29) {
                KlineObjectSimple ticker = btcTickers.get(index - i);
                try {
                    if (ticker.startTime.longValue() == Utils.sdfFileHour.parse("20241015 21:44").getTime()) {
                        System.out.println("Debug");
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
                long minute = Utils.getCurrentMinute(ticker.startTime.longValue()) % 15;
                if (minute != 14) {
                    continue;
                }
                KlineObjectSimple ticker15m = btcTickers.get(index - i - 14);
                KlineObjectSimple ticker30m = btcTickers.get(index - i - 29);
                double rate = Math.min(Utils.rateOf2Double(ticker.priceClose, ticker30m.priceOpen),
                        Utils.rateOf2Double(ticker.priceClose, ticker15m.priceOpen));
                if (rate < -0.01) {
                    priceReverse = Math.max(ticker15m.priceOpen, ticker30m.priceOpen);
                    indexMin = i;
                    break;
                }
            }
        }
        try {
            if (lastTicker.startTime.longValue() == Utils.sdfFileHour.parse("20241011 01:09").getTime()) {
                System.out.println("Debug");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        if (priceReverse != null
                && lastTicker.priceClose > priceReverse
        ) {
            // by pass if last ticker not ticker first up over bottom 1%
            for (int i = 1; i < indexMin; i++) {
                KlineObjectSimple ticker = btcTickers.get(index - i);
                if (ticker.priceClose >= priceReverse) {
                    return false;
                }
            }
            LOG.info("IsBtcTrendReverse: {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()),
                    lastTicker.priceClose, priceReverse, Utils.rateOf2Double(lastTicker.priceClose, priceReverse),
                    Utils.sdfGoogle.format(new Date(lastTicker.startTime.longValue())));
            return true;
        }
        return false;
    }


    private String statisticRateSuccess() {
        Double pnl = 0d;
        try {
            for (OrderTargetInfoTest order : allOrderDone.values()) {
                pnl += order.calRateTp();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        if (allOrderDone.size() > 0) {
            Double rate = pnl / allOrderDone.size();
            return allOrderDone.size() + " -> " + Utils.formatPercent(rate) + "%";
        }
        return "";
    }

    private MarketDataObject calMarketData(Map<String, KlineObjectSimple> symbol2Ticker, Map<String, KlineObjectSimple> symbol2LastTicker) {
        TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateLast2Symbol = new TreeMap<>();
        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            if (Constants.specialSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = entry1.getValue();
            if (Utils.isTickerAvailable(ticker)) {
                Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                rateDown2Symbols.put(rateChange, symbol);
                rateUp2Symbols.put(-rateChange, symbol);
                KlineObjectSimple lastTicker = symbol2LastTicker.get(symbol);
                if (lastTicker != null) {
                    rateLast2Symbol.put(Utils.rateOf2Double(ticker.priceClose, lastTicker.priceOpen), symbol);
                }
            }
        }

        KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
        Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
        Double rateChangeDownAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateDown2Symbols, 50);
        Double rateChangeUpAvg = -MarketBigChangeDetectorTest.calRateLossAvg(rateUp2Symbols, 50);
        List<String> symbolsTopDown = MarketBigChangeDetectorTest.getTopSymbolSimple(rateDown2Symbols,
                Configs.NUMBER_ENTRY_EACH_SIGNAL, orderRunning.keySet());

//        if (symbolsTopDown.size() != Configs.NUMBER_ENTRY_EACH_SIGNAL) {
//            LOG.info("Error get symbol 2 trade: {} {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
//                    symbol2Ticker.size(), rateDown2Symbols.size(), symbolsTopDown.size(),
//                    Utils.toJson(symbolsTopDown), Utils.toJson(orderRunning.keySet()));
//        }
        return new MarketDataObject(rateChangeDownAvg, rateChangeUpAvg, btcRateChange, btcTicker.totalUsdt,
                null, symbolsTopDown);
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


    private void startUpdateOldOrderTrading(String symbol, KlineObjectSimple ticker) {

        OrderTargetInfoTest orderInfo = orderRunning.get(symbol);
        if (orderInfo != null) {
            if (orderInfo.timeStart < ticker.startTime.longValue()) {
                orderInfo.updatePriceByKlineSimple(ticker);
//                orderInfo.updateStatusFixTPSL();
                orderInfo.updateStatusNew(ticker);
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                        || orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                        || orderInfo.status.equals(OrderTargetStatus.STOP_MARKET_DONE)
                ) {
                    allOrderDone.put(orderInfo.timeStart + "-" + symbol, orderInfo);
                    orderRunning.remove(symbol);
                } else {
                    orderInfo.updateTPSL();
                }
            }
        }


    }


    private void createOrderBUYTarget(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange) {
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
        order.marketLevelChange = levelChange;
        orderRunning.put(symbol, order);
        LOG.info(log);
    }

}
