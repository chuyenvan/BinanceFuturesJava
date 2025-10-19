/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.data.DataManager;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.bigchange.test.TraceOrderDone;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.DcaProcessor;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.tradecore.TrendDetector;
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
    public static final String FILE_TREND_BY_TIME = "storage/data_file_quick_run/trend_by_time.data";

    public String currentMonth = null;
    public Map<String, TreeMap<Long, Double>> symbol2TimeAndMaxRate90M = null;

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;
    public ConcurrentHashMap<String, Map<Long, Boolean>> symbol2TrendData;

    public TreeMap<Long, MarketDataObject> time2MarketData;
    public TreeMap<Long, MarketRateChange> time2MarketRateChange;

    public Map<Long, Set<String>> time2SymbolSellingExhausted;


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
        TreeMap<Long, Double> time2RateDown15MAvg = new TreeMap<>();
        Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                // THAY ĐỔI: GỌI HÀM ĐỌC DỮ LIỆU TỪ PROTOBUF
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                if (time2Tickers == null) {
                    LOG.info("File data error or not found for time: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                }
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
                        Long startTimeRun = System.currentTimeMillis();
                        Boolean isTrendBuyWithBtc = getTrendBySymbol(Constants.SYMBOL_PAIR_BTC, time);
                        Boolean isTrendBuyWithETH = getTrendBySymbol(Constants.SYMBOL_PAIR_ETH, time);
                        try {
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            for (String symbol : symbol2Ticker.keySet()) {
//                            symbol2Ticker.keySet().parallelStream().forEach(symbol -> {
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
                                int sizeRemove = 100;
                                if (!symbol2OrderRunning.containsKey(symbol)) {
                                    sizeRemove = 21;
                                }
                                if (tickers.size() > sizeRemove) {
                                    for (int i = 0; i < 5; i++) {
                                        tickers.remove(0);
                                    }
                                }
                                // update order Old
                                startUpdateOldOrderTrading(time, symbol, tickers, isTrendBuyWithETH);
                            }
                            logByProcessTime(startTimeRun, "Done update order", time);

                            startTimeRun = System.currentTimeMillis();

                            Set<String> symbolsExhausted = time2SymbolSellingExhausted.get(time);
                            if (symbolsExhausted != null) {
                                for (String symbol : symbolsExhausted) {
                                    symbolSellingExhausted.put(symbol, time);
                                }
                            }

                            MarketRateChange marketRateChange = time2MarketRateChange.get(time);

                            MarketDataObject marketData;
                            marketData = time2MarketData.get(time);
                            Set<String> symbolLocked = new HashSet<>();
                            MarketLevelChange levelChange = null;
                            Map<String, Double> symbol2PriceMax15M = new HashMap<>();

                            if (marketData != null) {
                                TreeMap<Double, String> rate2Max = new TreeMap<>();
                                rate2Max.putAll(marketData.rate2Max);

                                levelChange = MarketBigChangeDetector.getMarketStatus1M(marketData.rateDownAvg,
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
                                    symbol2BUY.addAll(MarketBigChangeDetector.getTopSymbol(rate2Max, numberOrder, symbol2Ticker, symbolLocked));
                                    if (symbol2BUY.size() < numberOrder) {
                                        LOG.info("Not symbol 2 buy: {} {} ", levelChange, Utils.normalizeDateYYYYMMDDHHmm(time));
                                    }
                                    symbol2BUY.addAll(addSpecialSymbol(symbol2Ticker, symbol2BUY));
                                    List<String> symbolDcaLevel =
                                            DcaProcessor.getDCA(levelChange, time, BudgetManagerSimple.getInstance().getBudget(),
                                                    symbol2OrderRunning, isTrendBuyWithBtc, isTrendBuyWithETH);
                                    LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2BUY);
                                    // check create order new
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                        // ================== GỌI HÀM LỌC DUY NHẤT ==================
                                        if (TradeUtils.shouldAvoidEntry(symbol, tickers, isTrendBuyWithETH)) {
                                            continue; // Bỏ qua nếu có rủi ro
                                        }
                                        createOrderBUY(symbol, ticker, levelChange, time2MarketRateChange.get(time), symbol2PriceMax15M.get(symbol)
                                                , isTrendBuyWithBtc, isTrendBuyWithETH);
                                    }
                                    for (String symbol : symbolDcaLevel) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (Utils.isTickerAvailable(ticker)) {
                                            MarketLevelChange leveChange2Dca;
                                            if (calMarginRunning(symbol) < BudgetManagerSimple.getInstance().getBudget()) {
                                                leveChange2Dca = MarketLevelChange.DCA_LEVEL1;
                                            } else {
                                                leveChange2Dca = MarketLevelChange.DCA_LEVEL2;
                                            }
                                            createOrderBUY(symbol, ticker, leveChange2Dca, time2MarketRateChange.get(time)
                                                    , symbol2PriceMax15M.get(symbol), isTrendBuyWithBtc, isTrendBuyWithETH);
                                        }
                                    }
                                }
                            }
                            logByProcessTime(startTimeRun, "Done market data", time);
                            startTimeRun = System.currentTimeMillis();

                            if (marketRateChange != null) {
                                time2RateDown15MAvg.put(time, marketRateChange.rateDown15MAvg);
                                while (time2RateDown15MAvg.size() > 60) {
                                    time2RateDown15MAvg.remove(time2RateDown15MAvg.firstKey());
                                }
                                Double minRate15Min60M = Collections.min(time2RateDown15MAvg.values());

                                if (MarketBigChangeDetector.isDcaAlt(marketRateChange.rateDown15MAvg,
                                        marketRateChange.rateDownAvg, marketRateChange.rateUpAvg)) {
                                    // dca buy
                                    List<String> symbolDcaLossBig = DcaProcessor.getDCA(null, time,
                                            BudgetManagerSimple.getInstance().getBudget(), symbol2OrderRunning, isTrendBuyWithBtc, isTrendBuyWithETH);
                                    for (String symbol : symbolDcaLossBig) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (Utils.isTickerAvailable(ticker)) {
                                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                            LOG.info("Dca big loss: {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), ticker.priceClose);
                                            Double priceMax15M = getMax15M(tickers);
                                            MarketLevelChange leveChange2Dca;
                                            if (calMarginRunning(symbol) < BudgetManagerSimple.getInstance().getBudget()) {
                                                leveChange2Dca = MarketLevelChange.DCA_LEVEL1;
                                            } else {
                                                leveChange2Dca = MarketLevelChange.DCA_LEVEL2;
                                            }
                                            createOrderBUY(symbol, ticker, leveChange2Dca,
                                                    time2MarketRateChange.get(time), priceMax15M, isTrendBuyWithBtc, isTrendBuyWithETH);
                                        }
                                    }

                                    logByProcessTime(startTimeRun, "Done dca big", time);
                                    startTimeRun = System.currentTimeMillis();
                                }


                                if (MarketBigChangeDetector.isFundingFeeTrade(marketRateChange.rateDown15MAvg,
                                        marketRateChange.rateDownAvg, marketRateChange.rateUpAvg, minRate15Min60M, isTrendBuyWithETH)
                                ) {
                                    // funding level 1
                                    Set<String> symbolFundingBuy = FundingFeeManager.getInstance().getFundingBuyNew(time);
                                    Set<String> symbolBuyFundingFee = new HashSet<>();
                                    symbolBuyFundingFee.addAll(symbolFundingBuy);
                                    symbolBuyFundingFee.removeAll(symbol2OrderRunning.keySet());
                                    Set<String> symbolCanTrade = new HashSet<>();
                                    for (String symbol : symbolBuyFundingFee) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);

                                        Double priceMax15M = getMax15M(tickers);
                                        Double rateTicker = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);

                                        Double rateMax15M = 0.0;
                                        if (priceMax15M != null) {
                                            rateMax15M = Utils.rateOf2Double(ticker.priceClose, priceMax15M);
                                        }
                                        if (MarketBigChangeDetector.isRateChangeAvailable2Trade(rateTicker, rateMax15M)) {
                                            // ================== GỌI HÀM LỌC DUY NHẤT ==================
                                            if (TradeUtils.shouldAvoidEntry(symbol, tickers, isTrendBuyWithETH)) {
                                                continue; // Bỏ qua nếu có rủi ro
                                            }
                                            LOG.info("Funding buy {} {} close: {} rate:{} max15M: {} tickers:{}", symbol,
                                                    Utils.normalizeDateYYYYMMDDHHmm(time), ticker.priceClose, rateTicker,
                                                    rateMax15M, tickers.size());
                                            symbolCanTrade.add(symbol);
                                            createOrderBUY(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY,
                                                    time2MarketRateChange.get(time), priceMax15M, isTrendBuyWithBtc, isTrendBuyWithETH);
                                        } else {
                                            if (rateTicker < -0.008 || rateMax15M < -0.04) {
                                                symbolCanTrade.add(symbol);
                                            }
                                        }
                                    }
                                    if (symbolCanTrade.size() > 5) {
                                        symbolCanTrade.removeAll(symbol2OrderRunning.keySet());
                                        for (String symbol : symbolCanTrade) {
                                            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                            if (!Utils.isTickerAvailable(ticker)) {
                                                continue;
                                            }
                                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                            if (TradeUtils.shouldAvoidEntry(symbol, tickers, isTrendBuyWithETH)) {
                                                continue; // Bỏ qua nếu có rủi ro
                                            }
                                            Double priceMax15M = getMax15M(tickers);
                                            createOrderBUY(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY,
                                                    time2MarketRateChange.get(time), priceMax15M, isTrendBuyWithBtc, isTrendBuyWithETH);
                                        }
                                    }
                                    symbolCanTrade.clear();
                                    // ========== LOGIC CHO TÍN HIỆU FUNDING ÂM CỰC ĐOAN ==========
                                    Set<String> extremeFundingSymbols = FundingFeeManager.getInstance().getExtremeNegativeFundingSymbols(time);
                                    // TreeMap tự động sắp xếp nên symbol có funding âm nhất sẽ được xử lý trước
                                    for (String symbol : extremeFundingSymbols) {
                                        // Chỉ vào lệnh nếu chưa có vị thế đang chạy cho symbol này
                                        if (!symbol2OrderRunning.containsKey(symbol) && symbolSellingExhausted.containsKey(symbol)) {
                                            if (symbolSellingExhausted.get(symbol) < time - Configs.FUNDING_TIME_EXTREME) {
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
                                            Double priceMax15M = getMax15M(tickers);
                                            Double rateTicker = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);

                                            Double rateMax15M = 0.0;
                                            if (priceMax15M != null) {
                                                rateMax15M = Utils.rateOf2Double(ticker.priceClose, priceMax15M);
                                            }
                                            if (rateTicker > -0.01 && rateMax15M > -0.04) {
                                                if (rateTicker < -0.008 || rateMax15M < -0.035) {
                                                    symbolCanTrade.add(symbol);
                                                }
                                                continue;
                                            }
                                            // ================== GỌI HÀM LỌC DUY NHẤT ==================
                                            if (TradeUtils.shouldAvoidEntry(symbol, tickers, isTrendBuyWithETH)) {
                                                continue; // Bỏ qua nếu có rủi ro
                                            }
                                            createOrderBUY(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY_SPECIAL,
                                                    time2MarketRateChange.get(time), symbol2PriceMax15M.get(symbol), isTrendBuyWithBtc, isTrendBuyWithETH);

                                        }
                                    }
                                    if (symbolCanTrade.size() > 5) {
                                        symbolCanTrade.removeAll(symbol2OrderRunning.keySet());
                                        for (String symbol : symbolCanTrade) {
                                            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                            if (!Utils.isTickerAvailable(ticker)) {
                                                continue;
                                            }
                                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                            if (TradeUtils.shouldAvoidEntry(symbol, tickers, isTrendBuyWithETH)) {
                                                continue; // Bỏ qua nếu có rủi ro
                                            }
                                            Double priceMax15M = getMax15M(tickers);
                                            createOrderBUY(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY_SPECIAL,
                                                    time2MarketRateChange.get(time), priceMax15M, isTrendBuyWithBtc, isTrendBuyWithETH);
                                        }
                                    }
                                }
                            }
                            logByProcessTime(startTimeRun, "Done funding fee", time);
                            startTimeRun = System.currentTimeMillis();
                            // BTC trend reverse
                            Double rateBtcTrendReverse = time2BtcReverse.get(time);
                            if (rateBtcTrendReverse != null && rateBtcTrendReverse >= Configs.BTC_TREND_REVERSE_RATE_MIN_TRADE) {
                                levelChange = MarketLevelChange.BTC_TREND_REVERSE;
                                List<String> symbol2BUY = new ArrayList<>();
                                for (String symbol : Constants.specialSymbol) {
                                    Double rateLoss = calRateLoss(symbol);
                                    Double budget = BudgetManagerSimple.getInstance().getBudget();
                                    Double marginOfSym = calMarginRunning(symbol);
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
                                    boolean isDcaSpecialSymbol = true;
                                    if (order != null) {
                                        isDcaSpecialSymbol = MarketBigChangeDetector.isDcaWithBtcReverse(rateLoss,
                                                budget, marginOfSym, ticker.priceClose, order.lastEntry);
                                    }
                                    if (isDcaSpecialSymbol) {
                                        symbol2BUY.add(symbol);
                                    }

                                }
                                for (String symbol : symbol2BUY) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    if (Utils.isTickerAvailable(ticker)) {
                                        createOrderBUY(symbol, ticker, levelChange, time2MarketRateChange.get(time), symbol2PriceMax15M.get(symbol), isTrendBuyWithBtc, isTrendBuyWithETH);
                                    }
                                }
                            }
                            logByProcessTime(startTimeRun, "Done btc reverse done", time);
                            startTimeRun = System.currentTimeMillis();

                            if (time % Utils.TIME_DAY == 0) {
                                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, true);
                                BudgetManagerSimple.getInstance().updateBudget();
                            } else {
                                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                            }
                            logByProcessTime(startTimeRun, "Done budget data", time);


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
                BudgetManagerSimple.getInstance().updateBalance(finalStartTime1, allOrderDone, symbol2OrderRunning,
                        symbol2OrdersEntry, false);
                break;
            }
        }
        // add all order running to done
        for (List<OrderTargetInfoTest> orderRunning : symbol2OrdersEntry.values()) {
            for (OrderTargetInfoTest orderInfo : orderRunning) {
                orderInfo.lastPrice = symbol2OrderRunning.get(orderInfo.symbol).lastPrice;
                orderInfo.priceTP = orderInfo.lastPrice;
                orderInfo.minPrice = symbol2OrderRunning.get(orderInfo.symbol).minPrice;
                orderInfo.timeUpdate = symbol2OrderRunning.get(orderInfo.symbol).timeUpdate;
                orderInfo.updateFundingFee();
                allOrderDone.put(-orderInfo.timeUpdate + allOrderDone.size(), orderInfo);
            }
        }
        FundingFeeManager.getInstance().writeData2File();
        StorageSnappy.writeObject2File(FILE_TREND_BY_TIME, symbol2TrendData);
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

    private Boolean getTrendBySymbol(String symbol, Long time) {
        Map<Long, Boolean> trendData = symbol2TrendData.get(symbol);
        if (trendData == null) {
            trendData = new HashMap<>();
            symbol2TrendData.put(symbol, trendData);
        }
        if (trendData.containsKey(time)) {
            return trendData.get(time);
        } else {
            Boolean trend = false;
            switch (symbol) {
                case Constants.SYMBOL_PAIR_BTC:
                    trend = TrendDetector.isTrendBTC(time);
                    break;
                case Constants.SYMBOL_PAIR_ETH:
                    trend = TrendDetector.isTrendETH(time);
                    break;
            }
            trendData.put(time, trend);
            return trend;
        }
    }

    private void logByProcessTime(Long startTimeRun, String msg, Long time) {
        long duration = (System.currentTimeMillis() - startTimeRun);
        if (duration > 100) {
            LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), msg, duration);
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

    private List<String> addSpecialSymbol(Map<String, KlineObjectSimple> symbol2Ticker, Set<String> symbol2BUY) {
        List<String> hashSet = new ArrayList<>();
        Set<String> symbol2Checks = new HashSet<>();
        symbol2Checks.addAll(Constants.specialSymbol);
        symbol2Checks.addAll(Constants.stableSymbol);
        symbol2Checks.removeAll(symbol2OrderRunning.keySet());
        symbol2Checks.removeAll(symbol2BUY);
        for (String symbol : symbol2Checks) {
            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
            if (ticker != null && Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen) < -0.013) {
                hashSet.add(symbol);
            }
        }
        return hashSet;
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
        time2SymbolSellingExhausted = (Map<Long, Set<String>>) StorageSnappy.readObjectFromFile(Configs.FILE_TIME_SYMBOL_EXHAUSTED);
        time2BtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);

        if (new File(FILE_TREND_BY_TIME).exists()) {
            symbol2TrendData = (ConcurrentHashMap<String, Map<Long, Boolean>>) StorageSnappy.readObjectFromFile(FILE_TREND_BY_TIME);
        } else {
            symbol2TrendData = new ConcurrentHashMap<>();
        }

    }

    private void startUpdateOldOrderTrading(Long time, String symbol, List<KlineObjectSimple> tickers, Boolean isTrendBuyWithETH) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
        if (orderMulti != null) {
            KlineObjectSimple ticker = tickers.get(tickers.size() - 1);
            if (orderMulti.timeStart <= ticker.startTime.longValue()) {
                orderMulti.updatePriceByKlineSimple(ticker);
                if (ticker.maxPrice >= orderMulti.priceEntry * 1.009 || orderMulti.priceSL != null) {
                    Double maxChangeIn90M = getMaxRateIn90MForTradingStop(time, symbol, tickers);
                    orderMulti.updateStatusNew(maxChangeIn90M, ticker, isTrendBuyWithETH);
                    if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                        closeOrder(symbol, orderMulti);
                    } else {
                        orderMulti.updateTPSL(maxChangeIn90M, ticker, isTrendBuyWithETH);
                    }
                }
            }
        }
    }

    private Double getMaxRateIn90MForTradingStop(Long time, String symbol, List<KlineObjectSimple> tickers) {
        Double maxChangeIn60M = null;
        String month = Utils.getMonth(time);
        if (currentMonth == null || !StringUtils.equals(currentMonth, month)) {
            if (currentMonth != null) {
                String fileName = "storage/rate_change_" + Configs.NUMBER_TICKER_RATE_CHANGE_MAX_TRADE + "m/" + currentMonth;
                if (!Utils.getMonth(System.currentTimeMillis() - Utils.TIME_HOUR).equals(currentMonth)
                        && !new File(fileName).exists()) {
                    LOG.info("Write data max rate change 90M month: {}", fileName);
                    StorageSnappy.writeObject2File(fileName, symbol2TimeAndMaxRate90M);
                }
            }
            String fileName = "storage/rate_change_" + Configs.NUMBER_TICKER_RATE_CHANGE_MAX_TRADE + "m/" + month;
            if (new File(fileName).exists()) {
                LOG.info("Read data max rate change 90M month: {}", fileName);
                symbol2TimeAndMaxRate90M = (Map<String, TreeMap<Long, Double>>) StorageSnappy.readObjectFromFile(fileName);
            } else {
                symbol2TimeAndMaxRate90M = new HashMap<>();
            }
            currentMonth = month;
        }

        TreeMap<Long, Double> time2Rate = symbol2TimeAndMaxRate90M.get(symbol);
        if (time2Rate != null) {
            maxChangeIn60M = time2Rate.get(time);
        }
        if (maxChangeIn60M == null) {
//            LOG.info("Calculate max rate change 60M for trading stop: {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), tickers.size());
            maxChangeIn60M = MarketBigChangeDetector.getMaxRateIn90MForTradingStop(tickers);
            if (time2Rate == null) {
                time2Rate = new TreeMap<>();
                symbol2TimeAndMaxRate90M.put(symbol, time2Rate);
            }
            time2Rate.put(time, maxChangeIn60M);
        }

        return maxChangeIn60M;
    }


    private void closeOrder(String symbol, OrderTargetInfoTest orderMulti) {
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        for (OrderTargetInfoTest order : orders) {
            order.timeUpdate = orderMulti.timeUpdate;
            order.status = orderMulti.status;
            order.priceTP = orderMulti.priceTP;
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
        BudgetManagerSimple.getInstance().updatePositionMargin(symbol2OrderRunning.values());
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
                               MarketRateChange marketData, Double maxPrice15m, Boolean isTrendBuyWithBtc, Boolean isTrendBuyWithETH) {
        Double entry = ticker.priceClose;
        Integer leverage = BudgetManagerSimple.getInstance().getLeverage();

        Double marginRunning = calMarginRunning();
        Double balanceBasic = BudgetManagerSimple.getInstance().balanceBasic;
        Double budget = BudgetManagerSimple.getInstance().getBudget();

        budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange, isTrendBuyWithBtc, isTrendBuyWithETH);

        if (budget == null) {
            LOG.info("Not trade because over capital: {} {} {}", symbol, levelChange,
                    Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
            return;
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
        order.lastPrice = entry;

        order.tickerOpen = ticker;
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
        BudgetManagerSimple.getInstance().updatePositionMargin(symbol2OrderRunning.values());
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
            if (order.priceSL == null) {
                marginTotal += order.calMargin();
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
