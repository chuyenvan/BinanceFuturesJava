/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
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
public class SellDetector {

    public static final Logger LOG = LoggerFactory.getLogger(SellDetector.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/OrderSELLDone.data";
    public static final String FILE_SIGNAL_SELL = "target/time_btc_sell.data";

    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
    public ConcurrentHashMap<String, OrderTargetInfoTest> orderRunning = new ConcurrentHashMap();

    public static void main(String[] args) throws ParseException, IOException {
//        long startTime = Utils.sdfFile.parse("20210201").getTime();
//        while (true) {
//            startTime = startTime + Utils.TIME_DAY;
//            if (startTime > System.currentTimeMillis()) {
//                break;
//            }
//            LOG.info("Check data of: {}", Utils.normalizeDateYYYYMMDD(startTime));
//            Map<String, Double> symbol2Volume = Volume24hrManager.getInstance().getVolume24h(startTime);
//            if (symbol2Volume != null) {
//                LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(startTime),
//                        symbol2Volume.size());
//            }
//        }
        SellDetector test = new SellDetector();
        test.initData();
        List<KlineObjectSimple> tickers = getTickerFullBtc1M();
        Map<Long, Double> timeReverse = new HashMap<>();
        for (int i = 0; i < tickers.size(); i++) {
            KlineObjectSimple ticker = tickers.get(i);
            if (isTimeSell(tickers, i)) {
                timeReverse.put(ticker.startTime.longValue(), Utils.rateOf2Double(ticker.maxPrice, ticker.minPrice));
            }
        }
        LOG.info("Last btcTicker: {}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()));
        Storage.writeObject2File(FILE_SIGNAL_SELL, timeReverse);
        System.out.println(Utils.normalizeDateYYYYMMDDHHmm(tickers.get(tickers.size() - 1).startTime.longValue()));
        test.statisticAll();
    }

    private static List<KlineObjectSimple> getTickerFullBtc1M() {

        String fileName = Configs.FOLDER_TICKER_1M + Constants.SYMBOL_PAIR_BTC;
        List<KlineObjectSimple> tickers = null;
        if (new File(fileName).exists()) {
            try {
                tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(fileName);
                Long startTime = tickers.get(tickers.size() - 1).startTime.longValue();
                tickers.remove(tickers.size() - 1);
                while (true) {
                    LOG.info("Get data: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                    tickers.addAll(TickerFuturesHelper.getTickerSimpleWithStartTime(Constants.SYMBOL_PAIR_BTC,
                            Constants.INTERVAL_1M, startTime));
                    startTime = startTime + 500 * Utils.TIME_MINUTE;
                    if (startTime > System.currentTimeMillis()) {
                        break;
                    }
                }
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
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        Storage.writeObject2File(fileName, tickers);
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
                Map<Long, Double> timeSignalSell = (Map<Long, Double>) Storage.readObjectFromFile(FILE_SIGNAL_SELL);
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        Map<String, Double> symbol2Volume24h = Volume24hrManager.getInstance().getVolume24h(time);
                        if (symbol2Volume24h == null){
                            continue;
                        }
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
                            if (!Utils.isTickerAvailable(ticker)) {
                                continue;
                            }

                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                            if (tickers == null) {
                                tickers = new ArrayList<>();
                                symbol2LastTickers.put(symbol, tickers);
                            }
                            tickers.add(ticker);
                            if (tickers.size() > 2000) {
                                for (int i = 0; i < 500; i++) {
                                    tickers.remove(0);
                                }
                            }
                            Double priceMin = null;
                            Double priceMax = null;

                            for (int i = 0; i < 20; i++) {
                                int index = tickers.size() - i - 1;
                                if (index >= 0) {
                                    KlineObjectSimple kline = tickers.get(index);
                                    if (priceMin == null || priceMin > kline.minPrice) {
                                        priceMin = kline.minPrice;
                                    }
                                    if (priceMax == null || priceMax < kline.maxPrice) {
                                        priceMax = kline.maxPrice;
                                    }

                                }
                            }

                            if (symbol2Volume24h != null &&
                                    symbol2Volume24h.get(symbol) != null
                                    && symbol2Volume24h.get(symbol) < 100 * 1E6) {
                                symbol2MaxPrice.put(Utils.rateOf2Double(ticker.priceClose, priceMin), symbol);
                            }
                        }
                        if (timeSignalSell.containsKey(time)) {
                            MarketLevelChange levelChange = MarketLevelChange.BTC_REVERSE;
                            List<String> symbol2Trade = MarketBigChangeDetectorTest.getTopSymbolSimple(symbol2MaxPrice,
                                    Configs.NUMBER_ENTRY_EACH_SIGNAL / 2, orderRunning.keySet());
                            LOG.info("{} {} -> {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2Trade, symbol2MaxPrice.size());
                            for (String symbol : symbol2Trade) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
                                createOrderSELL(symbol, ticker, levelChange, btcTicker, timeSignalSell.get(time));
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
            TraceOrderDone.printOrderTestDone(FILE_STORAGE_ORDER_DONE, "storage/signal_sell.csv");
        } catch (Exception e) {
            e.printStackTrace();
        }
        exitWhenDone();

    }

    public static Boolean isTimeSell(List<KlineObjectSimple> btcTickers, int index) {
        int period = 15;
        if (index < period + 3) {
            return false;
        }
        KlineObjectSimple lastTicker = btcTickers.get(index);
        Double volumeTotal = 0d;
        for (int i = 3; i < period + 3; i++) {
            KlineObjectSimple ticker = btcTickers.get(index - i);
            volumeTotal += ticker.totalUsdt;
        }
        double volumeAvg = volumeTotal / period;
        if (lastTicker.totalUsdt > 10 * volumeAvg
                && Utils.rateOf2Double(lastTicker.priceClose, lastTicker.priceOpen) > 0.001
        ) {
            LOG.info("IsBtcReverse: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()),
                    lastTicker.priceClose, lastTicker.totalUsdt / volumeAvg);
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
                orderInfo.updateStatusFixTPSL();
//                orderInfo.updateStatusNew(ticker);
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                        || orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                        || orderInfo.status.equals(OrderTargetStatus.STOP_MARKET_DONE)
                ) {
                    allOrderDone.put(orderInfo.timeStart + "-" + symbol, orderInfo);
                    orderRunning.remove(symbol);
                } else {
//                    orderInfo.updateTPSL();
                }
            }
        }


    }


    private void createOrderSELL(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange,
                                 KlineObjectSimple btcTicker, Double rateBtc15M) {
        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();

        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
        Double priceTp = Utils.calPriceTarget(symbol, entry, OrderSide.SELL, 1 * Configs.RATE_TARGET);
        Double priceSL = Utils.calPriceTarget(symbol, entry, OrderSide.BUY, 1 * Configs.RATE_TARGET);
//        Double priceTp = null;
        String log = OrderSide.SELL + " " + symbol + " entry: " + entry + " target: " + priceTp + " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.SELL);
        order.priceSL = priceSL;
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.marketLevelChange = levelChange;
        order.rateChange = rateBtc15M;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        order.tickerClose = Utils.convertKlineSimple(btcTicker);
        orderRunning.put(symbol, order);
        BudgetManagerSimple.getInstance().updateInvesting(orderRunning.values());
        LOG.info(log);
    }

}
