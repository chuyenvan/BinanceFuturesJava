/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
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
public class Ticker1MStatisticMarketLevel {

    public static final Logger LOG = LoggerFactory.getLogger(Ticker1MStatisticMarketLevel.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/OrderStatisticDone.data";
    public ConcurrentHashMap<String, OrderTargetInfoTest> allOrderDone;
    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> orderRunning = new ConcurrentHashMap();

    public static void main(String[] args) throws ParseException, IOException {
        Ticker1MStatisticMarketLevel test = new Ticker1MStatisticMarketLevel();
        test.initData();
        test.statisticAll();
    }


    private void statisticAll() throws ParseException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<String, KlineObjectSimple> symbol2LastTicker = new HashMap<>();
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
                        }
                        MarketDataObject marketData = calMarketData(symbol2Ticker);
                        MarketLevelChange levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                                marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg, marketData.rateUp15MAvg, marketData.rateBtcDown15M);
                        List<String> symbol2Trade;
                        symbol2Trade = marketData.symbolsTopDown;
                        if (levelChange != null) {
                            LOG.info("Market: {} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2Trade);
                            Double target;
                            if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                                    || levelChange.equals(MarketLevelChange.SMALL_UP)) {
                                while (symbol2Trade.size() > Configs.NUMBER_ENTRY_EACH_SIGNAL / 2) {
                                    symbol2Trade.remove(symbol2Trade.size() - 1);
                                }
                            }
                            // check create order new
                            for (String symbol : symbol2Trade) {
                                KlineObjectSimple lastTicker = symbol2LastTicker.get(symbol);
                                KlineObjectSimple ticker = entry.getValue().get(symbol);
                                target = Utils.rateOf2Double(ticker.priceOpen, ticker.priceClose);
                                if (lastTicker != null
                                        && Utils.rateOf2Double(lastTicker.priceClose, lastTicker.priceOpen) < 0) {
                                    target = Utils.rateOf2Double(lastTicker.priceOpen, ticker.priceClose);
                                }
                                createOrderBUYTarget(symbol, ticker, target, levelChange);
                            }
                        }
                        symbol2LastTicker.putAll(entry.getValue());
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
        for (List<OrderTargetInfoTest> orders : orderRunning.values()) {
            for (OrderTargetInfoTest orderInfo : orders) {
                allOrderDone.put(orderInfo.timeStart + "-" + orderInfo.symbol, orderInfo);
            }
        }
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
        exitWhenDone();

    }

    private MarketDataObject calMarketData(Map<String, KlineObjectSimple> symbol2Ticker) {
        TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();
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
            }
        }
        // stop trade when capital over
//                        if (BudgetManagerSimple.getInstance().isAvailableTrade()) {
        KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
        Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
        Double rateChangeDownAvg = MarketBigChangeDetectorTest.calRateLossAvg(rateDown2Symbols, 50);
        Double rateChangeUpAvg = -MarketBigChangeDetectorTest.calRateLossAvg(rateUp2Symbols, 50);
        List<String> symbol2Trade = MarketBigChangeDetectorTest.getTopSymbolSimple(rateDown2Symbols,
                Configs.NUMBER_ENTRY_EACH_SIGNAL, null);
        if (symbol2Trade.size() != Configs.NUMBER_ENTRY_EACH_SIGNAL) {
            LOG.info("Error get symbol 2 trade: {} {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(btcTicker.startTime.longValue()),
                    symbol2Ticker.size(), rateDown2Symbols.size(), symbol2Trade.size(),
                    Utils.toJson(symbol2Trade));
        }
        return new MarketDataObject(rateChangeDownAvg, rateChangeUpAvg, btcRateChange, btcTicker.totalUsdt, null, symbol2Trade);
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
        List<OrderTargetInfoTest> orderInfos = orderRunning.get(symbol);
        List<OrderTargetInfoTest> orderSuccess = new ArrayList<>();
        if (orderInfos != null) {
            for (OrderTargetInfoTest orderInfo : orderInfos) {
                if (orderInfo != null) {
                    if (orderInfo.timeStart < ticker.startTime.longValue()) {
                        orderInfo.updatePriceByKlineSimple(ticker);
                        orderInfo.updateStatus();
                        if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                                || orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                                || orderInfo.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                            allOrderDone.put(orderInfo.timeStart + "-" + symbol, orderInfo);
                            orderSuccess.add(orderInfo);
                        } else {
                            orderInfo.updateTPSL();
                        }
                    }
                }
            }
            orderInfos.removeAll(orderSuccess);
        }
    }


    private void createOrderBUYTarget(String symbol, KlineObjectSimple ticker, Double rateTarget, MarketLevelChange levelChange) {
        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage(symbol);
        Double targetTp = rateTarget;

        if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)) {
            targetTp = targetTp / 2;
        }
        if (levelChange.equals(MarketLevelChange.BIG_DOWN)
                || levelChange.equals(MarketLevelChange.BIG_UP)) {
            budget = budget * 2;
        }
        if (targetTp < 0.04) {
            targetTp = 0.04;
        }


        Double priceTp = Utils.calPriceTarget(symbol, entry, OrderSide.BUY, targetTp);
        Double priceSL = Utils.calPriceTarget(symbol, entry, OrderSide.SELL, Configs.RATE_STOP_LOSS);
//        String log = OrderSide.BUY + " " + symbol + " entry: " + entry + " target: " + priceTp
//                + " SL: " + priceSL + " budget: " + budget
//                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantity(budget, leverage, entry, symbol);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BUY);
        order.priceSL = priceSL;
        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        order.marketLevelChange = levelChange;
        List<OrderTargetInfoTest> orders = orderRunning.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
            orderRunning.put(symbol, orders);
        }
        orders.add(order);
//        LOG.info(log);
    }

}
