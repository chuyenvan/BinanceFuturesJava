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
import com.binance.chuyennd.tradecore.DcaProcessor;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.tradecore.TradeUtils;
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
    public static final String FILE_STORAGE_ORDER_RUNNING = "storage/orderRunning/orderRunning-RUNNINGDATA.data";
    public static final String FILE_STORAGE_ORDER_RUNNING_ENTRY = "storage/orderRunning/orderRunning-entry-RUNNINGDATA.data";

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;

    public TreeMap<Long, MarketDataObject> time2MarketData;
    public TreeMap<Long, MarketRateChange> time2MarketRateChange;


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
        Map<String, Long> symbolSellingExhausted = new HashMap<>();
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
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

                                if (MarketBigChangeDetectorTest.isSellingExhausted(tickers, symbol)) {
                                    symbolSellingExhausted.put(symbol, time);
                                }
                                // update order Old
                                startUpdateOldOrderTrading(symbol, tickers);
                            }

                            MarketRateChange marketRateChange = time2MarketRateChange.get(time);

                            // dca buy
                            List<String> symbolDcaLossBig = DcaProcessor.getDCA(null, time, BudgetManagerSimple.getInstance().getBudget(), symbol2OrderRunning);
                            for (String symbol : symbolDcaLossBig) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (Utils.isTickerAvailable(ticker)) {
                                    LOG.info("Dca big loss: {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), ticker.priceClose);
                                    List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                    Double priceMax15M = getMax15M(tickers);
                                    MarketLevelChange leveChange2Dca = MarketLevelChange.DCA_LEVEL1;
                                    createOrderBUY(symbol, ticker, leveChange2Dca,
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
                                    Set<String> symbol2BUY = new HashSet<>();
                                    symbol2BUY.addAll(MarketBigChangeDetectorTest.getTopSymbolSimpleNew(rate2Max, levelChange,
                                            numberOrder, symbol2Ticker, symbolLocked));
                                    if (symbol2BUY.size() < numberOrder) {
                                        LOG.info("Not symbol 2 buy: {} {} ", levelChange, Utils.normalizeDateYYYYMMDDHHmm(time));
                                    }
                                    symbol2BUY.addAll(addSpecialSymbol(symbol2Ticker));
                                    List<String> symbolDcaLevel =
//                                            getDCA(levelChange, time, BudgetManagerSimple.getInstance().getBudget());
                                            DcaProcessor.getDCA(levelChange, time, BudgetManagerSimple.getInstance().getBudget(), symbol2OrderRunning);
                                    LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2BUY);
                                    // check create order new
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                        // ================== GỌI HÀM LỌC DUY NHẤT ==================
                                        if (TradeUtils.shouldAvoidEntry(symbol, tickers)) {
                                            continue; // Bỏ qua nếu có rủi ro
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
                                            MarketLevelChange leveChange2Dca;
                                            if (calMarginRunning(symbol) < BudgetManagerSimple.getInstance().getBudget()
                                                    && calMarginRunning() < 100 * BudgetManagerSimple.getInstance().getBudget()) {
                                                leveChange2Dca = MarketLevelChange.DCA_LEVEL1;
                                            } else {
                                                leveChange2Dca = MarketLevelChange.DCA_LEVEL2;
                                            }
                                            createOrderBUY(symbol, ticker, leveChange2Dca, time2MarketRateChange.get(time)
                                                    , symbol2PriceMax15M.get(symbol));
                                        }
                                    }
                                }
                            }

                            if (marketRateChange != null) {
                                if (marketRateChange.rateDown15MAvg < -0.018
                                        || marketRateChange.rateUpAvg > 0.005
                                        || marketRateChange.rateDownAvg < -0.0055
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
                                                || (rateTicker < -0.005 && rateMax15M < -0.04)
                                                || (rateTicker < -0.01 && rateMax15M < -0.035)
                                                || (rateTicker < -0.01 && rateMin15M < -0.03)
                                                || (rateTicker < -0.006 && rateMax4h < -0.1)
                                                || (rateTicker < -0.01 && rateMin4h < -0.08)
                                        ) {
                                            // ================== GỌI HÀM LỌC DUY NHẤT ==================
                                            if (TradeUtils.shouldAvoidEntry(symbol, tickers)) {
                                                continue; // Bỏ qua nếu có rủi ro
                                            }
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
                            if (marketRateChange.rateDown15MAvg < -0.015) {
                                // ========== LOGIC CHO TÍN HIỆU FUNDING ÂM CỰC ĐOAN ==========
                                Double fundingFeeMin = -0.0005;
                                Set<String> extremeFundingSymbols = FundingFeeManager.getInstance().getExtremeNegativeFundingSymbols(time, fundingFeeMin);
//                                if (symbol2OrderRunning.size() < 30 && !extremeFundingSymbols.isEmpty()) {
                                // Ghi log để theo dõi
                                LOG.info("{} - TÍN HIỆU FUNDING CỰC ĐOAN: {}", Utils.normalizeDateYYYYMMDDHHmm(time), extremeFundingSymbols);

                                // Duyệt qua danh sách các symbol đủ điều kiện
                                // TreeMap tự động sắp xếp nên symbol có funding âm nhất sẽ được xử lý trước
                                for (String symbol : extremeFundingSymbols) {
                                    // Chỉ vào lệnh nếu chưa có vị thế đang chạy cho symbol này
                                    if (!symbol2OrderRunning.containsKey(symbol) && symbolSellingExhausted.containsKey(symbol)) {
                                        if (symbolSellingExhausted.get(symbol) < time - Utils.TIME_DAY) {
                                            LOG.info("SellingExhausted of {} over time: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time),
                                                    Utils.normalizeDateYYYYMMDDHHmm(symbolSellingExhausted.get(symbol)));
                                            symbolSellingExhausted.remove(symbol);
                                            continue;
                                        }
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                        // ================== GỌI HÀM LỌC DUY NHẤT ==================
                                        if (TradeUtils.shouldAvoidEntry(symbol, tickers)) {
                                            continue; // Bỏ qua nếu có rủi ro
                                        }
                                        createOrderBUY(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY_SPECIAL,
                                                time2MarketRateChange.get(time), symbol2PriceMax15M.get(symbol));
                                    }
                                }
//                                }
                            }

                            // BTC trend reverse
                            Double rateBtcTrendReverse = time2BtcReverse.get(time);
                            if (rateBtcTrendReverse != null && rateBtcTrendReverse >= Configs.BTC_TREND_REVERSE_RATE_MIN_TRADE) {
                                levelChange = MarketLevelChange.BTC_TREND_REVERSE;
                                List<String> symbol2BUY = new ArrayList<>();
                                for (String symbol : Constants.specialSymbol) {
                                    if (calMarginRunning(symbol) > 2 * BudgetManagerSimple.getInstance().getBudget()) {
                                        if (calMarginRunning(symbol) > 4 * BudgetManagerSimple.getInstance().getBudget()) {
                                            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                            OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
                                            if (Utils.rateOf2Double(ticker.priceClose, order.lastEntry) < -0.1) {
                                                symbol2BUY.add(symbol);
                                            }
                                        } else {
                                            if (calRateLoss(symbol) < -0.05 || calRateLoss(symbol) > 0.02) {
                                                symbol2BUY.add(symbol);
                                            }
                                        }
                                    } else {
                                        if (calRateLoss(symbol) < -0.03 || calRateLoss(symbol) > 0.02) {
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
            String month = Utils.getMonth(finalStartTime1);
            if (Utils.getMonth(startTime).equals(month)) {
                StorageSnappy.writeObject2File(FILE_STORAGE_ORDER_RUNNING.replace("RUNNINGDATA", month), symbol2OrderRunning);
                StorageSnappy.writeObject2File(FILE_STORAGE_ORDER_RUNNING_ENTRY.replace("RUNNINGDATA", month), symbol2OrdersEntry);
            }
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
// Bên trong file SimulatorMarketLevelTicker1MStopLoss.java

    private int calculateEntryScore(String symbol, long time, List<KlineObjectSimple> tickers) {
        int totalScore = 0;

        // Tín hiệu cũ
//        if (MarketBigChangeDetectorTest.isSellingExhausted(tickers, symbol)) totalScore += 2;
//        if (!FundingFeeManager.getInstance().getExtremeNegativeFundingSymbols(time, -0.0005).isEmpty()) totalScore += 3;

        // Tín hiệu mới
//        if (MarketBigChangeDetectorTest.isVolatilitySqueezeBreakout(tickers)) totalScore += 2;
//        if (MarketBigChangeDetectorTest.isBullishDivergence(tickers)) totalScore += 4;
//        if (MarketBigChangeDetectorTest.isSellSideAbsorption(tickers)) totalScore += 3;

        return totalScore;
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

    private List<String> addSpecialSymbol(Map<String, KlineObjectSimple> symbol2Ticker) {
        List<String> symbol2BUY = new ArrayList<>();
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
        time2BtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);
//        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
//        String month = Utils.getMonth(startTime);
//        if (new File(FILE_STORAGE_ORDER_RUNNING.replace("RUNNINGDATA", month)).exists()) {
//            symbol2OrderRunning = (ConcurrentHashMap<String, OrderTargetInfoTest>) StorageSnappy.readObjectFromFile(FILE_STORAGE_ORDER_RUNNING.replace("RUNNINGDATA", month));
//            symbol2OrdersEntry = (ConcurrentHashMap<String, List<OrderTargetInfoTest>>) StorageSnappy.readObjectFromFile(FILE_STORAGE_ORDER_RUNNING_ENTRY.replace("RUNNINGDATA", month));
//        }

    }

    private void startUpdateOldOrderTrading(String symbol, List<KlineObjectSimple> tickers) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
        if (orderMulti != null) {
            int index = tickers.size() - 1;
            KlineObjectSimple ticker = tickers.get(index);
            if (orderMulti.timeStart <= ticker.startTime.longValue()) {
                Double maxChangeIn60M = null;
                for (int i = 0; i < 60; i++) {
                    if (index - i < 0) {
                        break;
                    }
                    KlineObjectSimple tickerCheck = tickers.get(index - i);
                    if (maxChangeIn60M == null || Utils.rateOf2Double(tickerCheck.maxPrice, tickerCheck.minPrice) > maxChangeIn60M) {
                        maxChangeIn60M = Utils.rateOf2Double(tickerCheck.maxPrice, tickerCheck.minPrice);
                    }
                }
                orderMulti.updatePriceByKlineSimple(ticker);
                orderMulti.updateStatusNew(maxChangeIn60M);
                if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                        || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                        || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                    closeOrder(symbol, orderMulti);
                } else {
                    orderMulti.updateTPSL(maxChangeIn60M);
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
                || levelChange.equals(MarketLevelChange.FUNDING_FEE_BUY)
                || levelChange.equals(MarketLevelChange.FUNDING_FEE_BUY_SPECIAL)
                || levelChange.equals(MarketLevelChange.DCA_LEVEL2)
                || levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
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


    private Integer counterOrderRunning() {
        Integer counter = 0;
        for (List<OrderTargetInfoTest> orders : symbol2OrdersEntry.values()) {
            if (orders != null) {
                counter += orders.size();
            }
        }
        return counter;
    }

    private Integer counterOrderRunning(MarketLevelChange level) {
        Integer counter = 0;
        for (List<OrderTargetInfoTest> orders : symbol2OrdersEntry.values()) {
            if (orders != null && orders.size() != 0) {
                for (OrderTargetInfoTest order : orders) {
                    if (order.marketLevelChange.equals(level)) {
                        counter++;
                    }
                }
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

}
