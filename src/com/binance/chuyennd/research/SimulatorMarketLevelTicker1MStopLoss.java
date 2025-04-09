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
import com.binance.chuyennd.grid.SimpleMovingAverage4hManager;
import com.binance.chuyennd.grid.SimpleMovingAverageDayManager;
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

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;

    public String TIME_RUN = Configs.getString("TIME_RUN");

    public TreeMap<Long, MarketDataObject> time2MarketData;
    public TreeMap<Long, MarketDataObject> time2SignalSell;
    public TreeMap<Long, TreeMap<Double, String>> time2RateMax2d;
    public TreeMap<Long, TreeMap<Double, String>> time2RateMin2d;
    public TreeMap<Long, Double> time2BtcReverse;

    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry = new ConcurrentHashMap();
    public ConcurrentHashMap<String, OrderTargetInfoTest> symbol2OrderRunning = new ConcurrentHashMap();


    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
        test.initData();
        test.simulatorWithInitEntry();


//        long time = Utils.sdfFileHour.parse("20250223 23:30").getTime();
//        System.out.println(test.getSymbolSell(time));
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
//            levelChange = MarketLevelChange.SMALL_DOWN_15M;
//            createOrderBUY(symbol, tickers.get(1), levelChange, null, null);
//            levelChange = MarketLevelChange.TINY_UP;
//            createOrderBUY(symbol, tickers.get(6), levelChange, null, null);
            while (true) {
                for (KlineObjectSimple ticker : tickers) {
                    if (symbol2OrderRunning.isEmpty()) {
                        break;
                    }
                    startUpdateOldOrderTrading(symbol, ticker);
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
                                startUpdateOldOrderTrading(symbol, ticker);
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
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
//            List<Double> lastRateDown15M = new ArrayList<>();
            try {
//                LOG.info("Read file ticker: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        Set<String> symbolFundingBuy = FundingFeeManager.getInstance().getFundingBuy(time);
                        Set<String> symbolFundingSell = FundingFeeManager.getInstance().getFundingSell(time);
                        try {
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            for (String symbol : symbol2OrderRunning.keySet()) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (!Utils.isTickerAvailable(ticker)) {
                                    continue;
                                }
                                // update order Old
                                startUpdateOldOrderTrading(symbol, ticker);
                            }
                            // sell big change
                            Set<String> symbol2Sell = getSymbolSell(time);
                            if (!symbol2Sell.isEmpty()) {
                                symbol2Sell.removeAll(symbolFundingBuy);
                                Double maDif1d = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                                Double maDif4h = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                                if ((maDif4h != null && maDif4h < 0)
                                        || (maDif1d != null && maDif1d < 0)
                                ) {
                                    for (String symbol : symbol2Sell) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (Utils.isTickerAvailable(ticker) && !symbol2OrderRunning.containsKey(symbol)) {
                                            createOrderSELL(symbol, ticker, MarketLevelChange.ORDER_SELL, null);
                                        }
                                    }
                                }
                            }
                            // sell market
                            Double maDif1d = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                            Double maDif4h = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                            if ((maDif4h != null && maDif4h < 0)
                                    || (maDif1d != null && maDif1d < 0)
                            ) {
                                MarketDataObject sellSignal = time2SignalSell.get(time);
                                if (sellSignal != null && getSymbolLockBySide(OrderSide.SELL).size() < 50)
                                    if (sellSignal.rateUpAvg > 0.008) {
                                        Set<String> symbolLocked = new HashSet<>();
                                        symbolLocked.addAll(symbol2OrderRunning.keySet());
                                        symbolLocked.addAll(symbolFundingBuy);
                                        List<String> symbol2SELL = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(sellSignal.rate2Min, null,
                                                1, symbol2Ticker, symbolLocked);
                                        if (symbol2SELL.size() < 1) {
                                            LOG.info("Not symbol 2 sell: {} {} ", sellSignal.rateUp15MAvg, Utils.normalizeDateYYYYMMDDHHmm(time));
                                        }
                                        for (String symbol : symbol2SELL) {
                                            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                            if (!Utils.isTickerAvailable(ticker)) {
                                                continue;
                                            }
                                            createOrderSELL(symbol, ticker, MarketLevelChange.ORDER_SELL_QUICK, sellSignal);
                                        }
                                    }
                            }
                            // dca sell
                            for (String symbol : getSymbolLockBySide(OrderSide.SELL)) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (Utils.isTickerAvailable(ticker)) {
                                    OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
                                    if (order != null) {
                                        Double rateDca = -1.0;
                                        if (order.calMargin() > BudgetManagerSimple.getInstance().getBudget()) {
                                            if (order.calMargin() > 2 * BudgetManagerSimple.getInstance().getBudget()) {
                                                rateDca = -5.0;
                                            } else {
                                                rateDca = -3.0;
                                            }
                                        }
                                        if (order.calRateLoss() < rateDca) {
                                            createOrderSELL(symbol, ticker, MarketLevelChange.ORDER_SELL_DCA, null);
                                        }
                                    }
                                }
                            }
                            // dca buy
                            List<String> symbolDcaLossBig = getDCA(null, time);
                            for (String symbol : symbolDcaLossBig) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (Utils.isTickerAvailable(ticker)) {
                                    LOG.info("Dca big loss: {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), ticker.priceClose);
                                    createOrderBUY(symbol, ticker, MarketLevelChange.DCA_BIG_LOSS, null, null);
                                }
                            }
                            MarketDataObject marketData;
                            marketData = time2MarketData.get(time);

                            Set<String> symbolLocked = new HashSet<>();
                            symbolLocked.addAll(getSymbolLockByMargin(time));
                            symbolLocked.addAll(getSymbolLockBySide(OrderSide.SELL));
                            MarketLevelChange levelChange;
                            Map<String, Double> symbol2PriceMax15M = new HashMap<>();
                            if (marketData != null) {
                                TreeMap<Double, String> rate2Max = new TreeMap<>();
                                TreeMap<Double, String> rate2Min = new TreeMap<>();
//                                lastRateDown15M.add(marketData.rateDownAvg);
//                                while (lastRateDown15M.size() > 20) {
//                                    lastRateDown15M.remove(0);
//                                }
                                rate2Max.putAll(marketData.rate2Max);
                                rate2Min.putAll(marketData.rate2Min);

                                levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                                        marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg, marketData.rateUp15MAvg,
                                        marketData.rateBtcDown15M);
                                symbol2PriceMax15M.putAll(marketData.symbol2PriceMax15M);
                                if (levelChange != null) {
                                    Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                                    symbolLocked.addAll(symbol2OrderRunning.keySet());
                                    if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                                            || levelChange.equals(MarketLevelChange.SMALL_UP)
                                            || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                                            || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                                            || levelChange.equals(MarketLevelChange.TINY_DOWN)
                                            || levelChange.equals(MarketLevelChange.TINY_UP)
                                    ) {
                                        numberOrder = numberOrder / 2;
                                    }
                                    List<String> symbol2BUY = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(rate2Max, levelChange,
                                            numberOrder, symbol2Ticker, symbolLocked);
                                    if (symbol2BUY.size() < numberOrder) {
                                        LOG.info("Not symbol 2 buy: {} {} ", levelChange, Utils.normalizeDateYYYYMMDDHHmm(time));
                                    }
                                    symbol2BUY = addSpecialSymbol(symbol2BUY, levelChange, symbol2Ticker);
                                    List<String> symbolDcaLevel = getDCA(levelChange, time);
                                    LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2BUY);
                                    // check create order new
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        createOrderBUY(symbol, ticker, levelChange, marketData, symbol2PriceMax15M.get(symbol));
                                    }
                                    for (String symbol : symbolDcaLevel) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (Utils.isTickerAvailable(ticker)) {
                                            OrderTargetInfoTest orderRunning = symbol2OrderRunning.get(symbol);
                                            if (orderRunning != null) {
                                                if (orderRunning.calMargin() > 2 * BudgetManagerSimple.getInstance().getBudget()
                                                        && Utils.rateOf2Double(ticker.priceClose, orderRunning.lastEntry) > 0) {
                                                    LOG.info("Not dca {} {} {}", symbol, orderRunning.lastEntry, ticker.priceClose);
                                                    continue;
                                                }
                                            }
                                            createOrderBUY(symbol, ticker, MarketLevelChange.DCA_ORDER, marketData, symbol2PriceMax15M.get(symbol));
                                        }
                                    }
                                }
                                Set<String> symbolBuyFundingFee = new HashSet<>();
                                symbolBuyFundingFee.addAll(symbolFundingBuy);
                                symbolBuyFundingFee.removeAll(symbol2OrderRunning.keySet());
                                for (String symbol : symbolBuyFundingFee) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    if (!Utils.isTickerAvailable(ticker)) {
                                        continue;
                                    }
                                    if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.013) {
                                        createOrderBUY(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY, marketData, symbol2PriceMax15M.get(symbol));
                                    } else {
                                        Double priceMax15M = symbol2PriceMax15M.get(symbol);
                                        if (priceMax15M != 0
                                                && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.005
                                                && Utils.rateOf2Double(ticker.priceClose, priceMax15M) < -0.05) {
                                            createOrderBUY(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY, marketData, symbol2PriceMax15M.get(symbol));
                                        }
                                    }
                                }
                                Set<String> symbolSellFundingFee = new HashSet<>();
                                symbolSellFundingFee.addAll(symbolFundingSell);
                                symbolSellFundingFee.removeAll(symbol2OrderRunning.keySet());
                                for (String symbol : symbolSellFundingFee) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    if (!Utils.isTickerAvailable(ticker)) {
                                        continue;
                                    }
                                    if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) > 0.015) {
                                        createOrderSELL(symbol, ticker, MarketLevelChange.FUNDING_FEE_SELL, marketData);
                                    }
                                }

                            }
                            // BTC trend reverse
                            Double rateBtcTrendReverse = time2BtcReverse.get(time);
                            if (rateBtcTrendReverse != null && rateBtcTrendReverse >= Configs.BTC_TREND_REVERSE_RATE_MIN_TRADE) {
                                levelChange = MarketLevelChange.BTC_TREND_REVERSE;
                                List<String> symbol2BUY = new ArrayList<>();
                                Set<String> symbolSelling = getSymbolLockBySide(OrderSide.SELL);
                                for (String symbol : Constants.specialSymbol) {
                                    if (symbolSelling.contains(symbol)) {
                                        continue;
                                    }
                                    if (calMarginRunning(symbol) > 2 * BudgetManagerSimple.getInstance().getBudget()) {
                                        if (calMarginRunning(symbol) > 4 * BudgetManagerSimple.getInstance().getBudget()) {
                                            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                            OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
                                            if (ticker.priceClose < order.lastEntry) {
                                                symbol2BUY.add(symbol);
                                            }

                                        } else {
                                            if (calRateLoss(symbol) < -0.03 || calRateLoss(symbol) > 0.02) {
                                                symbol2BUY.add(symbol);
                                            }
                                        }
                                    } else {
                                        if (calRateLoss(symbol) < -0.02 || calRateLoss(symbol) > 0.02) {
                                            symbol2BUY.add(symbol);
                                        }
                                    }
                                }
                                for (String symbol : symbol2BUY) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    if (Utils.isTickerAvailable(ticker)) {
                                        createOrderBUY(symbol, ticker, levelChange, marketData, symbol2PriceMax15M.get(symbol));
                                    }
                                }
                            }
                            if (time % Utils.TIME_DAY == 0) {
                                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, true);
                            } else {
                                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                            }
                        } catch (Exception e) {
                            e.printStackTrace();
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

        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE + "-"
                + Configs.TIME_AFTER_ORDER_2_SL, allOrderDone);

        Storage.writeObject2File("storage/orderRunning.data", symbol2OrderRunning);
        Storage.writeObject2File("storage/BalanceIndex.data", BudgetManagerSimple.getInstance().balanceIndex);
        BudgetManagerSimple.getInstance().printBalanceIndex();
        try {
            TraceOrderDone.printOrderTestDone("storage/printDone.csv", allOrderDone);
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    private Set<String> getSymbolSell(Long time) {
        Set<String> hashSet = new HashSet<>();
        if (time == Utils.getTimeInterval15m(time)) {
            Double rateMax = 0.1;
            Double rateMin = 0.6;
            TreeMap<Double, String> rateMax2Symbol = time2RateMax2d.get(time);
            TreeMap<Double, String> rateMin2Symbol = time2RateMin2d.get(time);
            Set<String> symbolRateMax = new HashSet<>();
            Set<String> symbolRateMin = new HashSet<>();
            if (rateMax2Symbol != null && rateMin2Symbol != null) {
                for (Double rate : rateMax2Symbol.keySet()) {
                    if (rate < -rateMax) {
                        symbolRateMax.add(rateMax2Symbol.get(rate));
                    } else {
                        break;
                    }
                }
                for (Double rate : rateMin2Symbol.keySet()) {
                    if (-rate > rateMin) {
                        symbolRateMin.add(rateMin2Symbol.get(rate));
                    } else {
                        break;
                    }

                }
            }
            for (String symbol : symbolRateMax) {
                if (symbolRateMin.contains(symbol)) {
                    hashSet.add(symbol);
                }
            }
        }
        return hashSet;
    }

    private List<String> getDCA(MarketLevelChange levelChange, Long time) {
        List<String> symbols = new ArrayList<>();
        Integer durationDca = null;
        Double rateLoss2Dca = null;
        Boolean isAll = false;
        if (levelChange == null) {
            durationDca = 1;
            rateLoss2Dca = -0.3;
        } else {
            if (levelChange.equals(MarketLevelChange.BIG_DOWN)) {
                isAll = true;
                rateLoss2Dca = -0.05;
                durationDca = 8;
            }
            if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                    || levelChange.equals(MarketLevelChange.BIG_UP)) {
                rateLoss2Dca = -0.08;
                durationDca = 15;
            }
        }

        if (rateLoss2Dca != null) {
            for (String symbol : symbol2OrderRunning.keySet()) {
                if (!isAll && Constants.specialSymbol.contains(symbol)) {
                    continue;
                }
                Double rateLoss2DcaOfSym = rateLoss2Dca;
                OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
                if (!isAll && order.calMargin() >= BudgetManagerSimple.getInstance().getBudget()) {
                    rateLoss2DcaOfSym = -0.5;
                }
                if (order != null
                        && order.side.equals(OrderSide.BUY)
                        && order.calRateLoss() < rateLoss2DcaOfSym
                ) {
                    if (order.marketLevelChange.equals(MarketLevelChange.DCA_ORDER)) {
                        if (time > order.timeStart + durationDca * Utils.TIME_MINUTE) {
                            symbols.add(symbol);
                        }
                    } else {
                        symbols.add(symbol);
                    }
                }
            }
        }
        return symbols;
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
                if (!getSymbolLockBySide(OrderSide.SELL).contains(symbol)
                        && calMarginRunning(symbol) < 3 * BudgetManagerSimple.getInstance().getBudget()) {
                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                    if (ticker != null && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.015) {
                        symbol2BUY.add(symbol);
                    }
                }
            }
        }
        return symbol2BUY;
    }

    public void initData() throws IOException, ParseException {
        // clear Data Old
        allOrderDone = new TreeMap<>();
        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
            FileUtils.delete(new File(FILE_STORAGE_ORDER_DONE));
        }
        // check and rebuild entry
        ExportMarketData2File exporter = new ExportMarketData2File();
        File fileEntryMarket = new File(Configs.FILE_ENTRY_MARKET_LEVEL);
        if (fileEntryMarket == null) {
            exporter.exportMarketEntries();
        } else {
            time2MarketData = (TreeMap<Long, MarketDataObject>) Storage.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
            if (time2MarketData.lastKey() < System.currentTimeMillis() - 12 * Utils.TIME_HOUR) {
                exporter.exportMarketEntries();
                time2MarketData = (TreeMap<Long, MarketDataObject>) Storage.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
            }
        }
        time2SignalSell = (TreeMap<Long, MarketDataObject>) Storage.readObjectFromFile(Configs.FILE_ENTRY_SELL_SIGNAL_1);
        time2SignalSell.putAll((TreeMap<Long, MarketDataObject>) Storage.readObjectFromFile(Configs.FILE_ENTRY_SELL_SIGNAL_2));
        time2RateMax2d = (TreeMap<Long, TreeMap<Double, String>>) Storage.readObjectFromFile(Configs.FILE_ENTRY_RATE_MAX_2D);
        time2RateMin2d = (TreeMap<Long, TreeMap<Double, String>>) Storage.readObjectFromFile(Configs.FILE_ENTRY_RATE_MIN_2D);
        File fileEntryBtcTrendReverse = new File(Configs.FILE_ENTRY_BTC_REVERSE);
        if (fileEntryBtcTrendReverse == null || fileEntryBtcTrendReverse.lastModified() < System.currentTimeMillis() - 12 * Utils.TIME_HOUR) {
            exporter.exportBtcTrendReverse();
        }
        time2BtcReverse = (TreeMap<Long, Double>) Storage.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);

    }

    private void startUpdateOldOrderTrading(String symbol, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
        if (orderMulti != null) {
            if (orderMulti.timeStart < ticker.startTime.longValue()) {
                orderMulti.updatePriceByKlineSimple(ticker);
                orderMulti.updateStatusNew();
                orderMulti.updateFundingFee(ticker.startTime.longValue() + Utils.TIME_MINUTE);
                if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                        || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                        || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                    closeOrder(symbol, orderMulti);

                } else {
                    orderMulti.updateTPSL();
                }
            }
        }
    }

    private void closeOrder(String symbol, OrderTargetInfoTest orderMulti) {
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
    }

    private OrderTargetInfoTest mergeOrder(List<OrderTargetInfoTest> orders, KlineObjectSimple ticker) {
        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        Double quantity = 0d;
        String priceEntry = "";
        Double margin = 0d;
        OrderSide side = orders.get(0).side;
        for (OrderTargetInfoTest orderInfo : orders) {
            if (!side.equals(orderInfo.side)) {
                LOG.info("Error order: {} {} {} {}", orders.get(0).symbol,
                        Utils.normalizeDateYYYYMMDDHHmm(orders.get(0).timeStart), side, orderInfo.side);
            }
            time2Order.put(orderInfo.timeStart, orderInfo);
            margin += orderInfo.priceEntry * orderInfo.quantity;
            quantity += orderInfo.quantity;
            priceEntry += orderInfo.priceEntry + "-";
        }
        double entry = margin / quantity;
        OrderTargetInfoTest orderResult = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry,
                null, quantity, BudgetManagerSimple.getInstance().getLeverage(),
                time2Order.lastEntry().getValue().symbol,
                time2Order.lastEntry().getKey(),
                time2Order.lastEntry().getKey(), orders.get(0).side);
        orderResult.minPrice = ticker.priceClose;
        orderResult.lastPrice = ticker.priceClose;
        orderResult.maxPrice = ticker.priceClose;
        orderResult.lastEntry = orders.get(orders.size() - 1).lastEntry;
        orderResult.rateChange = orders.get(orders.size() - 1).rateChange;
        orderResult.tickerOpen = time2Order.lastEntry().getValue().tickerOpen;
        orderResult.marketLevelChange = time2Order.lastEntry().getValue().marketLevelChange;

        if (orders.size() > 2) {
            LOG.info("Merger orders of {}: {} -> {}", orders.get(0).symbol, priceEntry, orderResult.priceEntry);
        }
        return orderResult;
    }


    public void createOrderBUY(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange,
                               MarketDataObject marketData, Double maxPrice15m) {
        if (isOverMargin()) {
            LOG.info("Not trade because over margin: {}/{} {} {} {}", calMarginRunning().longValue(), BudgetManagerSimple.getInstance().balanceBasic
                    , symbol, levelChange, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            return;
        }
        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
        if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP)
                || levelChange.equals(MarketLevelChange.DCA_BIG_LOSS)
        ) {
            budget = budget / 2;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                || levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
                || levelChange.equals(MarketLevelChange.TINY_DOWN)
                || levelChange.equals(MarketLevelChange.DCA_ORDER)
                || levelChange.equals(MarketLevelChange.FUNDING_FEE_BUY)
        ) {
            budget = budget / 3;
        }

        if (levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                || levelChange.equals(MarketLevelChange.SMALL_UP)
                || levelChange.equals(MarketLevelChange.TINY_UP)
        ) {
            long time = ticker.startTime.longValue();
            Double maDif1d = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
            Double maDif4h = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
            if ((maDif1d != null && maDif1d > 0)
                    || (maDif4h != null && maDif4h > 0)
                    || Constants.specialSymbol.contains(symbol)) {
                budget = budget / 4;
            } else {
                return;
            }
        }

        String log = OrderSide.BUY + " " + symbol + " entry: " + entry +
                " budget: " + budget
                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue());
        Double quantity = Utils.calQuantityTest(budget, leverage, entry, symbol);

        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
//            Double minBtcTrade = BudgetManagerSimple.getInstance().balanceBasic.longValue() / 1E6;
            Double minBtcTrade = 0.002;
            if (quantity < minBtcTrade) {
                quantity = minBtcTrade;
            }
        }
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity,
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BUY);

        order.minPrice = entry;
        order.lastEntry = entry;
        order.maxPrice = entry;
        order.lastPrice = entry;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        order.marketLevelChange = levelChange;
        order.rateChange = maxPrice15m;
        order.ordersRunning = counterOrderRunning();
        order.unProfitTotal = BudgetManagerSimple.getInstance().calUnrealizedProfitMin(symbol2OrderRunning.values());
        order.slTotal = BudgetManagerSimple.getInstance().calProfitLossMax(symbol2OrderRunning.values());
        order.marginRunning = BudgetManagerSimple.getInstance().calPositionMargin(symbol2OrderRunning.values());
        order.marginRealRunning = BudgetManagerSimple.getInstance().calPositionMarginReal(symbol2OrderRunning.values());
        if (marketData != null) {
            order.marketData = cloneData(marketData);
        }
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);
        LOG.info(log);
        symbol2OrdersEntry.put(symbol, orders);
        symbol2OrderRunning.put(symbol, mergeOrder(orders, ticker));
        BudgetManagerSimple.getInstance().updateMaxOrderRunning(counterOrderRunning());
    }

    public MarketDataObject cloneData(MarketDataObject marketData) {
        MarketDataObject result = new MarketDataObject(marketData.rateDownAvg, marketData.rateUpAvg, marketData.rateBtc,
                marketData.volumeBtc, marketData.level, marketData.symbolsTopDown);
        result.rateDown15MAvg = marketData.rateDown15MAvg;
        result.rateUp15MAvg = marketData.rateUp15MAvg;
        result.rateBtcUp15M = marketData.rateBtcUp15M;
        result.rateBtcDown15M = marketData.rateBtcDown15M;
        return result;
    }

    public void createOrderSELL(String symbol, KlineObjectSimple ticker, MarketLevelChange marketLevel, MarketDataObject marketData) {

        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudgetSell();
        if (marketLevel.equals(MarketLevelChange.ORDER_SELL_QUICK)
                || marketLevel.equals(MarketLevelChange.FUNDING_FEE_SELL)) {
            budget = budget * 2 / 3;
        }
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
        String log = OrderSide.SELL + " " + symbol + " entry: " + entry +
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
                leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.SELL);

        order.minPrice = entry;
        order.lastPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = Utils.convertKlineSimple(ticker);
        order.ordersRunning = counterOrderRunning();
        order.marketLevelChange = marketLevel;
        order.unProfitTotal = BudgetManagerSimple.getInstance().calUnrealizedProfitMin(symbol2OrderRunning.values());
        order.slTotal = BudgetManagerSimple.getInstance().calProfitLossMax(symbol2OrderRunning.values());
        order.marginRunning = BudgetManagerSimple.getInstance().calPositionMargin(symbol2OrderRunning.values());
        order.marginRealRunning = BudgetManagerSimple.getInstance().calPositionMarginReal(symbol2OrderRunning.values());
        if (marketData != null) {
            order.marketData = cloneData(marketData);
        }
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);
        LOG.info(log);
        symbol2OrdersEntry.put(symbol, orders);
        symbol2OrderRunning.put(symbol, mergeOrder(orders, ticker));

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
            if (order.side.equals(OrderSide.BUY)) {
                if (order.priceSL == null || order.priceSL < order.priceEntry) {
                    marginTotal += order.calMargin();
                }
            } else {
                if (order.priceSL == null || order.priceSL > order.priceEntry) {
                    marginTotal += order.calMargin();
                }
            }
        }
        BudgetManagerSimple.getInstance().marginRunning = marginTotal;
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

    private Double calRateLoss(String symbol) {
        Double rateLoss = 1d;
        OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
        if (order != null) {
            return order.calRateLoss();
        }
        return rateLoss;
    }

    private Boolean isOverMargin() {
        Double marginTotal = 0d;
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
//
//            if (order.timeUpdate - order.timeStart > Utils.TIME_DAY) {
//                continue;
//            }
            if (order.priceSL == null || order.priceSL < order.priceEntry) {
                marginTotal += order.calMargin();
            }
        }
        return marginTotal > BudgetManagerSimple.getInstance().balanceBasic * 0.8;
    }

    private Set<String> getSymbolRunning(MarketLevelChange level) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.marketLevelChange.equals(level) &&
                    order.timeUpdate - order.timeStart < 30 * Utils.TIME_MINUTE
            ) {
                hashSet.add(order.symbol);
            }
        }
        return hashSet;
    }

    private Set<String> getSymbolLockByMargin(Long time) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.calMargin() >= BudgetManagerSimple.getInstance().getBudget()) {
                hashSet.add(order.symbol);
            }
        }
        return hashSet;
    }

    private Set<String> getSymbolLockBySide(OrderSide side) {
        Set<String> hashSet = new HashSet<>();
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.side.equals(side)) {
                hashSet.add(order.symbol);
            }
        }
        return hashSet;
    }
}
