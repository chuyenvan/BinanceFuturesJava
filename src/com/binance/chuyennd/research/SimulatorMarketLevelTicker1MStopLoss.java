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
import com.binance.chuyennd.grid.SimpleMovingAverage4hManager;
import com.binance.chuyennd.grid.SimpleMovingAverageDayManager;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.StorageSnappy;
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

    public TreeMap<Long, MarketDataObject> time2MarketData;
    public TreeMap<Long, MarketRateChange> time2MarketRateChange;
    //    public TreeMap<Long, MarketDataObject> time2SignalSell;
    public TreeMap<Long, Set<String>> time2SymbolsSell;
    public TreeMap<Long, Double> time2BtcReverse;

    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry = new ConcurrentHashMap();
    public ConcurrentHashMap<String, OrderTargetInfoTest> symbol2OrderRunning = new ConcurrentHashMap();


    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
        test.initData();
        test.simulatorWithInitEntry();
    }

    public void simulatorWithInitEntry(String... inputs) throws ParseException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
            Set<String> symbolBigChanges = new HashSet<>();
            try {
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                if (time2Tickers == null) {
                    LOG.info("File data error: {} {}", Utils.normalizeDateYYYYMMDDHHmm(startTime),
                            Configs.FOLDER_TICKER_1M_SNAPPY_FILE + startTime);
                }
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        try {
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            for (String symbol : symbol2Ticker.keySet()) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (!Utils.isTickerAvailable(ticker)) {
                                    updateSymbolDeListed(symbol, time);
                                    continue;
                                }
                                if (Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.15) {
                                    symbolBigChanges.add(symbol);
                                }
                                List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                if (tickers == null) {
                                    tickers = new ArrayList<>();
                                    symbol2LastTickers.put(symbol, tickers);
                                }
                                tickers.add(ticker);
                                int sizeRemove = 360;
                                if (tickers.size() > sizeRemove) {
                                    for (int i = 0; i < 5; i++) {
                                        tickers.remove(0);
                                    }
                                }
                                // update order Old
                                startUpdateOldOrderTrading(symbol, ticker);
                            }

                            MarketRateChange marketRateChange = time2MarketRateChange.get(time);
                            // sell big change
                            if (time == Utils.getTimeInterval15m(time)) {
                                Set<String> symbol2Sell = time2SymbolsSell.get(time);
                                if (symbol2Sell != null && !symbol2Sell.isEmpty()) {
                                    Set<String> symbolFundingBuy = FundingFeeManager.getInstance().getFundingBuyNew(time);
                                    Set<String> symbolFundingSell = FundingFeeManager.getInstance().getFundingSell(time);
                                    symbol2Sell.removeAll(symbolFundingBuy);
                                    symbol2Sell.removeAll(symbol2OrderRunning.keySet());
                                    Double maDif1d = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                                    Double maDif4h = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                                    if ((maDif4h != null && maDif4h < 0)
                                            || (maDif1d != null && maDif1d < 0)
                                    ) {
                                        for (String symbol : symbol2Sell) {
                                            if (symbolFundingSell.contains(symbol)) {
                                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                                if (Utils.isTickerAvailable(ticker) && !symbol2OrderRunning.containsKey(symbol)) {
                                                    List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                                    Double priceMin15M = getMin15M(tickers);
                                                    createOrderSELL(symbol, ticker, MarketLevelChange.ORDER_SELL,
                                                            time2MarketRateChange.get(time), priceMin15M);

                                                }
                                            }
                                        }
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
                                                if (order.calMargin() > 3 * BudgetManagerSimple.getInstance().getBudget()) {
                                                    rateDca = -20.0;
                                                } else {
                                                    rateDca = -5.0;
                                                }
                                            } else {
                                                rateDca = -3.0;
                                            }
                                        }
                                        if (order.calRateLoss() < rateDca) {
                                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                            Double priceMin15M = getMin15M(tickers);
                                            createOrderSELL(symbol, ticker, MarketLevelChange.ORDER_SELL_DCA, time2MarketRateChange.get(time), priceMin15M);
                                        }
                                    }
                                }
                            }

                            // dca buy
                            List<String> symbolDcaLossBig = getDCA(null, time, marketRateChange);
                            for (String symbol : symbolDcaLossBig) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (Utils.isTickerAvailable(ticker)) {
                                    LOG.info("Dca big loss: {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), ticker.priceClose);
                                    List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                    Double priceMax15M = getMax15M(tickers);
                                    createOrderBUY(symbol, ticker, MarketLevelChange.DCA_LEVEL1,
                                            time2MarketRateChange.get(time), priceMax15M);
                                }
                            }

                            MarketDataObject marketData;
                            marketData = time2MarketData.get(time);
                            Set<String> symbolLocked = new HashSet<>();
                            MarketLevelChange levelChange = null;
                            Map<String, Double> symbol2PriceMax15M = new HashMap<>();
                            if (marketData != null) {
                                TreeMap<Double, String> rate2Max = new TreeMap<>();
                                rate2Max.putAll(marketData.rate2Max);

                                levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                                        marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg);
                                symbol2PriceMax15M.putAll(marketData.symbol2PriceMax15M);

                                // buy signal new
                                if (levelChange != null) {
                                    Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                                    symbolLocked.addAll(symbol2OrderRunning.keySet());
                                    if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                                            || levelChange.equals(MarketLevelChange.SMALL_UP)
                                            || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                                            || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                                    ) {
                                        numberOrder = numberOrder / 2;
                                    }
                                    List<String> symbol2BUY = MarketBigChangeDetectorTest.getTopSymbolSimpleNew(rate2Max, levelChange,
                                            numberOrder, symbol2Ticker, symbolLocked);
                                    if (symbol2BUY.size() < numberOrder) {
                                        LOG.info("Not symbol 2 buy: {} {} ", levelChange, Utils.normalizeDateYYYYMMDDHHmm(time));
                                    }
                                    symbol2BUY = addSpecialSymbol(symbol2BUY, symbol2Ticker);
                                    List<String> symbolDcaLevel = getDCA(levelChange, time, marketRateChange);
                                    LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2BUY);
                                    // check create order new
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        createOrderBUY(symbol, ticker, levelChange, time2MarketRateChange.get(time), symbol2PriceMax15M.get(symbol));
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
                                            if (calMarginRunning(symbol) < BudgetManagerSimple.getInstance().getBudget()
                                                    && calMarginRunning() < 100 * BudgetManagerSimple.getInstance().getBudget()) {
                                                createOrderBUY(symbol, ticker, MarketLevelChange.DCA_LEVEL1, time2MarketRateChange.get(time)
                                                        , symbol2PriceMax15M.get(symbol));
                                            } else {
                                                createOrderBUY(symbol, ticker, MarketLevelChange.DCA_LEVEL2, time2MarketRateChange.get(time)
                                                        , symbol2PriceMax15M.get(symbol));
                                            }
                                        }
                                    }
                                }
                            }

                            if (marketRateChange != null) {
                                if (marketRateChange.rateDown15MAvg < -0.018
                                        || marketRateChange.rateUpAvg > 0.006
                                        || marketRateChange.rateDownAvg < -0.006
                                ) {
                                    // funding level 1
                                    Set<String> symbolFundingBuy = FundingFeeManager.getInstance().getFundingBuyNew(time);
                                    Set<String> symbolBuyFundingFee = new HashSet<>();
                                    symbolBuyFundingFee.addAll(symbolFundingBuy);
                                    symbolBuyFundingFee.removeAll(symbol2OrderRunning.keySet());
                                    for (String symbol : symbolBuyFundingFee) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                        Double priceMax15M = getMax15M(tickers);
                                        Double priceMax4h = getMax4H(tickers);
                                        Double priceMin4h = getMin4H(tickers);
                                        Double rateTicker = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);

                                        Double rateMax15M = 0.0;
                                        if (priceMax15M != null) {
                                            rateMax15M = Utils.rateOf2Double(ticker.priceClose, priceMax15M);
                                        }
                                        Double priceMin15M = getMin15M(tickers);
                                        Double rateMin15M = 0.0;
                                        if (priceMin15M != null) {
                                            rateMin15M = Utils.rateOf2Double(priceMin15M, ticker.priceClose);
                                        }
                                        Double rateMax4h = 0.0;
                                        if (priceMax4h != null) {
                                            rateMax4h = Utils.rateOf2Double(ticker.priceClose, priceMax4h);
                                        }
                                        Double rateMin4h = 0.0;
                                        if (priceMin4h != null) {
                                            rateMin4h = Utils.rateOf2Double(priceMin4h, ticker.priceClose);
                                        }
                                        if (rateTicker < -0.013
                                                || rateMax15M < -0.045
                                                || (rateTicker < -0.006 && rateMax15M < -0.04)
                                                || (rateTicker < -0.01 && rateMax15M < -0.035)
                                                || (rateTicker < -0.01 && rateMin15M < -0.03)
                                                || (rateTicker < -0.006 && rateMax4h < -0.1)
                                                || (rateTicker < -0.01 && rateMin4h < -0.08)
                                        ) {
                                            LOG.info("Funding buy {} {} close: {} rate:{} max15M: {} min15M:{} max4h:{}" +
                                                            " min4h:{} tickers:{}", symbol,
                                                    Utils.normalizeDateYYYYMMDDHHmm(time), ticker.priceClose, rateTicker,
                                                    rateMax15M, rateMin15M, rateMax4h, rateMin4h, tickers.size());
                                            createOrderBUY(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY,
                                                    time2MarketRateChange.get(time), priceMax15M);

                                        }
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
                                            if (Utils.rateOf2Double(ticker.priceClose, order.lastEntry) < -0.03) {
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
                                        createOrderBUY(symbol, ticker, levelChange, time2MarketRateChange.get(time), symbol2PriceMax15M.get(symbol));
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
                orderInfo.updateFundingFee();
                allOrderDone.put(-orderInfo.timeUpdate + allOrderDone.size(), orderInfo);
            }
        }

        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
        Storage.writeObject2File("storage/orderRunning.data", symbol2OrderRunning);
        Storage.writeObject2File("storage/BalanceIndex.data", BudgetManagerSimple.getInstance().balanceIndex);
        BudgetManagerSimple.getInstance().printBalanceIndex();
        try {
            TraceOrderDone.printOrderTestDone("storage/printDone.csv", allOrderDone);
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    private Double getMax15M(List<KlineObjectSimple> tickers) {
        Double priceMax15M = null;
        for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
            int index = tickers.size() - i - 1;
            if (index >= 0) {
                KlineObjectSimple kline = tickers.get(index);
                if (priceMax15M == null) {
                    priceMax15M = kline.maxPrice;
                }
                priceMax15M = Math.max(priceMax15M, kline.maxPrice);
            }
        }
        return priceMax15M;
    }

    private Double getMax4H(List<KlineObjectSimple> tickers) {
        Double priceMax15M = null;
        for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE * 16; i++) {
            int index = tickers.size() - i - 1;
            if (index >= 0) {
                KlineObjectSimple kline = tickers.get(index);
                if (priceMax15M == null) {
                    priceMax15M = kline.maxPrice;
                }
                priceMax15M = Math.max(priceMax15M, kline.maxPrice);
            }
        }
        return priceMax15M;
    }

    private Double getMin4H(List<KlineObjectSimple> tickers) {
        Double priceMin15M = null;
        for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE * 16; i++) {
            int index = tickers.size() - i - 1;
            if (index >= 0) {
                KlineObjectSimple kline = tickers.get(index);
                if (priceMin15M == null) {
                    priceMin15M = kline.minPrice;
                }
                priceMin15M = Math.min(priceMin15M, kline.minPrice);
            }
        }
        return priceMin15M;
    }

    private Double getMin15M(List<KlineObjectSimple> tickers) {
        Double priceMin15M = null;
        for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
            int index = tickers.size() - i - 1;
            if (index >= 0) {
                KlineObjectSimple kline = tickers.get(index);
                if (priceMin15M == null) {
                    priceMin15M = kline.minPrice;
                }
                priceMin15M = Math.min(priceMin15M, kline.minPrice);
            }
        }
        return priceMin15M;
    }

    public void updateSymbolDeListed(String symbol, Long time) {
        OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
        if (order != null) {
            if (order.timeUpdate < time - 2 * Utils.TIME_DAY) {
                LOG.info("Close order by delist: {} {} {} {}", order.symbol,
                        Utils.normalizeDateYYYYMMDDHHmm(time),
                        Utils.normalizeDateYYYYMMDDHHmm(order.timeUpdate),
                        Utils.normalizeDateYYYYMMDDHHmm(time - 2 * Utils.TIME_DAY));
                order.status = OrderTargetStatus.STOP_LOSS_DONE;
                order.priceTP = order.lastPrice;
                closeOrder(order.symbol, order);
            }
        }
    }


    private List<String> getDCA(MarketLevelChange levelChange, Long time, MarketRateChange marketRateChange) {
        List<String> symbols = new ArrayList<>();
        Integer durationDca = null;
        Double rateLoss2Dca = null;
        Boolean isAll = false;
        if (levelChange == null) {
            durationDca = 1;
            rateLoss2Dca = -0.25;
        } else {
            if (levelChange.equals(MarketLevelChange.BIG_DOWN)) {
                isAll = true;
                durationDca = 8;
                rateLoss2Dca = -0.05;
            }
            if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                    || levelChange.equals(MarketLevelChange.BIG_UP)
            ) {
                durationDca = 15;
                rateLoss2Dca = -0.08;
            }
            if (levelChange.equals(MarketLevelChange.MEDIUM_UP)
                    || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
            ) {
                durationDca = 15;
                rateLoss2Dca = -0.15;
            }
            if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
            ) {
                durationDca = 15;
                rateLoss2Dca = -0.2;
            }
        }

        if (rateLoss2Dca != null) {
            for (String symbol : symbol2OrderRunning.keySet()) {
                Double rateLoss2DcaOfSym = rateLoss2Dca;
                OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
                if (!isAll) {
                    Double margin = order.calMargin();
                    if (margin >= BudgetManagerSimple.getInstance().getBudget()) {
                        if (margin >= 1.5 * BudgetManagerSimple.getInstance().getBudget()) {
                            if (margin >= 2 * BudgetManagerSimple.getInstance().getBudget()) {
                                if (margin >= 2.5 * BudgetManagerSimple.getInstance().getBudget()) {
                                    if (margin >= 3 * BudgetManagerSimple.getInstance().getBudget()) {
                                        rateLoss2DcaOfSym = -0.99;
                                    } else {
                                        rateLoss2DcaOfSym = -0.9;
                                    }
                                } else {
                                    rateLoss2DcaOfSym = -0.8;
                                }
                            } else {
                                rateLoss2DcaOfSym = -0.7;
                            }
                        } else {
                            rateLoss2DcaOfSym = -0.5;
                        }
                    }
                }

                if (order != null
                        && order.side.equals(OrderSide.BUY)
                        && order.calRateLoss() < rateLoss2DcaOfSym
                ) {
                    if (order.marketLevelChange.equals(MarketLevelChange.DCA_LEVEL2)
                            || order.marketLevelChange.equals(MarketLevelChange.DCA_LEVEL1)) {
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

    private List<String> addSpecialSymbol
            (List<String> symbol2BUY, Map<String, KlineObjectSimple> symbol2Ticker) {
        Set<String> symbol2Checks = new HashSet<>();
        if (calMarginRunning() < 50 * BudgetManagerSimple.getInstance().getBudget()) {
            symbol2Checks.addAll(Constants.specialSymbol);
            symbol2Checks.addAll(Constants.stableSymbol);
            symbol2Checks.removeAll(symbol2OrderRunning.keySet());
            symbol2Checks.removeAll(symbol2BUY);
        }
        for (String symbol : symbol2Checks) {
            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
            if (ticker != null && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.013) {
                symbol2BUY.add(symbol);
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
        if (!new File(Configs.FILE_MARKET_RATE_CHANGE).exists()) {
            new ExportMarketData2File().exportMarketEntries();
        }
        if (!new File(Configs.FILE_ENTRY_BTC_REVERSE).exists()) {
            new ExportMarketData2File().exportBtcTrendReverse();
        }
        time2MarketRateChange = (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
        time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
        time2SymbolsSell = (TreeMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_SYMBOL_SELL);
        time2BtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);

    }

    private void startUpdateOldOrderTrading(String symbol, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
        if (orderMulti != null) {
            if (orderMulti.timeStart < ticker.startTime.longValue()) {
                orderMulti.updatePriceByKlineSimple(ticker);
                orderMulti.updateStatusNew();
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
        for (OrderTargetInfoTest order : orders) {
            order.timeUpdate = orderMulti.timeUpdate;
            order.status = orderMulti.status;
            order.priceTP = orderMulti.priceTP;
            order.maxPrice = orderMulti.maxPrice;
            order.minPrice = orderMulti.minPrice;
            order.lastPrice = orderMulti.lastPrice;
            order.updateFundingFee();
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
                               MarketRateChange marketData, Double maxPrice15m) {
        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudget();
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();

        if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP)
                || levelChange.equals(MarketLevelChange.DCA_LEVEL1)
        ) {
            budget = budget / 2;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                || levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
                || levelChange.equals(MarketLevelChange.FUNDING_FEE_BUY)
                || levelChange.equals(MarketLevelChange.FUNDING_FEE_BUY_SPECIAL)
                || levelChange.equals(MarketLevelChange.DCA_LEVEL2)
        ) {
            budget = budget / 3;
        }

        if (levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                || levelChange.equals(MarketLevelChange.SMALL_UP)
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
        if (marketData != null) {
            order.marketData = marketData;
        }
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);
        LOG.info(log);
        BudgetManagerSimple.getInstance().counterOrderCreated.incrementAndGet();
        symbol2OrdersEntry.put(symbol, orders);
        symbol2OrderRunning.put(symbol, mergeOrder(orders, ticker));
        BudgetManagerSimple.getInstance().updateMaxOrderRunning(counterOrderRunning());
    }


    public void createOrderSELL(String symbol, KlineObjectSimple ticker, MarketLevelChange
            marketLevel, MarketRateChange marketData, Double priceMin15M) {

        Double entry = ticker.priceClose;
        Double budget = BudgetManagerSimple.getInstance().getBudgetSell();

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
        order.marketLevelChange = marketLevel;
        order.rateChange = priceMin15M;
        if (marketData != null) {
            order.marketData = marketData;
        }
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);
        LOG.info(log);
        BudgetManagerSimple.getInstance().counterOrderCreated.incrementAndGet();
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
