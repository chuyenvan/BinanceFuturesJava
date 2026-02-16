/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import ai.onnxruntime.OrtException;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.HPOSmartCache;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingFeatureExtractor;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.onnx.entry.RunGeneratePredictions;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.bigchange.test.TraceOrderDone;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.DcaProcessor;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
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
    public TreeMap<Long, AiPredictionData> predictionMap;
    public AIRejectFilter aiRejectFilter;
    FundingFeatureExtractor extractor = new FundingFeatureExtractor();
    public Map<String, KlineObjectSimple> symbol2LastTicker = new HashMap<>();

//    public DcaFeatureExtractor extractor = new DcaFeatureExtractor();
//    public DcaOnnxInferenceManager dcaBrain;

    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry = new ConcurrentHashMap();
    public ConcurrentHashMap<String, OrderTargetInfoTest> symbol2OrderRunning = new ConcurrentHashMap();

    private long lastBasketTimestamp = -1;
    private List<String> cachedBasket = new ArrayList<>();


    public static void main(String[] args) throws ParseException, IOException, InterruptedException {


        SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
        // 🔥 BẬT CHẾ ĐỘ PRODUCTION
        FundingFeeManager.getInstance().setProductionMode(false);
        test.initData();
        test.simulatorWithInitEntry();
        Thread.sleep(5000);
        System.exit(1);
    }

    public void simulatorWithInitEntry(String... inputs) throws ParseException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        TreeMap<Long, Float> time2RateDown15MAvg = new TreeMap<>();
        Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();

        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            TreeMap<Long, Map<Short, float[]>> time2FundingPre;
//            TreeMap<Long, Map<Short, float[]>> time2FundingPreDca;
            try {
//                time2Tickers = HPOSmartCache.getData(startTime);
                time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M(startTime);
                time2FundingPre = DataManagerAerospikeFloatSim.readFundingBatchCustom(startTime, 1440);
//                time2FundingPreDca = DataManagerAerospikeFloatSim.readFundingLabel40BatchCustom(startTime, 1440);

                if (time2Tickers == null) {
                    LOG.info("File data error or not found for time: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                }
                if (time2Tickers != null && time2Tickers.size() >= 1440) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();
//                        extractor.updateMarketHistory(entry.getValue());
//                        if (time != lastBasketTimestamp) {
//                            cachedBasket = extractor.identifyTargetBasket(time);
//                            lastBasketTimestamp = time;
//                        }
                        Long startTimeRun = System.currentTimeMillis();
                        try {
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            extractor.updateMarketHistory(symbol2Ticker);
                            for (String symbol : symbol2Ticker.keySet()) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (!Utils.isTickerAvailable(ticker)) {
                                    updateSymbolDeListed(symbol, time);
                                    continue;
                                }
                                symbol2LastTicker.put(symbol, ticker);
                                List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                if (tickers == null) {
                                    tickers = new ArrayList<>();
                                    symbol2LastTickers.put(symbol, tickers);
                                }
                                tickers.add(ticker);
                                int sizeRemove = 200;
                                if (!symbol2OrderRunning.containsKey(symbol)) {
                                    sizeRemove = 201;
                                }
                                // Chỉ dọn dẹp khi dư ra một khoảng để đỡ tốn CPU dọn liên tục
                                if (tickers.size() > sizeRemove + 1000) {
                                    tickers.subList(0, tickers.size() - sizeRemove).clear();
                                }

                            }
                            // --- BƯỚC 2: UPDATE ACTIVE ORDERS (SIÊU TỐI ƯU) ---
                            // Thay vì duyệt 2000 symbol, chỉ duyệt danh sách đang chạy (vài chục lệnh)
                            if (!symbol2OrderRunning.isEmpty()) {
                                // Dùng keySet copy hoặc iterator để tránh ConcurrentModificationException nếu có lệnh đóng
                                for (String runningSymbol : new ArrayList<>(symbol2OrderRunning.keySet())) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(runningSymbol);
                                    if (ticker != null) { // Chỉ update nếu có data mới của symbol đó
                                        startUpdateOldOrderTrading(time, runningSymbol,
                                                symbol2LastTickers.get(runningSymbol));
                                    }
                                }
                            }

                            logByProcessTime(startTimeRun, "Done update order", time);

                            startTimeRun = System.currentTimeMillis();

                            MarketDataObject marketData;
                            marketData = time2MarketData.get(time);
                            Set<String> symbolLocked = new HashSet<>();
                            MarketLevelChange levelChange = null;
//                            Map<String, Double> symbol2PriceMax15M = new HashMap<>();

                            if (marketData != null && marketData.rate2Max != null && !marketData.rate2Max.isEmpty()) {
                                TreeMap<Float, String> rate2Max = new TreeMap<>();
                                rate2Max.putAll(SimpleSymbolMapper.getInstance().extractSymbol(marketData.rate2Max));
                                levelChange = MarketBigChangeDetector.getMarketStatus1M(marketData.rateDownAvg,
                                        marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg);
//                                symbol2PriceMax15M.putAll(marketData.symbol2PriceMax15M);
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
//                                    if (symbol2BUY.size() < numberOrder) {
//                                        LOG.info("Not symbol 2 buy: {} {} ", levelChange, Utils.normalizeDateYYYYMMDDHHmm(time));
//                                    }
                                    symbol2BUY.addAll(MarketBigChangeDetector.addSpecialSymbol(symbol2Ticker, symbol2BUY,
                                            symbol2OrderRunning.keySet()));
                                    List<String> symbolDcaLevel =
                                            DcaProcessor.getDCA(levelChange, time, BudgetManagerSimple.getInstance().getBudget(),
                                                    symbol2OrderRunning);
//                                    LOG.info("{} {} -> {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange, symbol2BUY);
                                    // check create order new
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        createOrderBUY(symbol, ticker, levelChange, time2MarketData.get(time),
                                                null, symbol2Ticker);
                                    }
                                    for (String symbol : symbolDcaLevel) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (Utils.isTickerAvailable(ticker)) {
//                                            Map<Short, float[]> symbol2PredDca = time2FundingPreDca.get(time);
//                                            if (symbol2PredDca != null) {
//                                                float[] fundingPred = symbol2PredDca.get(SimpleSymbolMapper.getInstance().getId(symbol));
//                                                if (fundingPred != null) {
//                                                    if (fundingPred[0] > 0.4) {
//                                                        LOG.info("❌ [FILTER AI] {}: Dca Prediction too high ({})", symbol, fundingPred[0]);
//                                                        continue;
//                                                    }
//                                                }
//                                            } else {
//                                                LOG.info("No Dca prediction data for time: {}", Utils.normalizeDateYYYYMMDDHHmm(time));
//                                            }

                                            MarketLevelChange leveChange2Dca;
                                            if (calMarginRunning(symbol) < BudgetManagerSimple.getInstance().getBudget()) {
                                                leveChange2Dca = MarketLevelChange.DCA_LEVEL1;
                                            } else {
                                                leveChange2Dca = MarketLevelChange.DCA_LEVEL2;
                                            }
                                            createOrderBUY(symbol, ticker, leveChange2Dca, time2MarketData.get(time)
                                                    , null, symbol2Ticker);
                                        }
                                    }
                                }
                            }
                            logByProcessTime(startTimeRun, "Done market data", time);
                            startTimeRun = System.currentTimeMillis();

                            if (marketData != null) {
                                time2RateDown15MAvg.put(time, marketData.rateDown15MAvg);
                                while (time2RateDown15MAvg.size() > Configs.NUMBER_RATE_DOWN_HISTORY_TRADE) {
                                    time2RateDown15MAvg.remove(time2RateDown15MAvg.firstKey());
                                }
                                Float minRate15Min60M = Collections.min(time2RateDown15MAvg.values());

                                if (MarketBigChangeDetector.isDcaAlt(marketData.rateDown15MAvg,
                                        marketData.rateDownAvg, marketData.rateUpAvg)) {
                                    // dca buy
                                    List<String> symbolDcaLossBig = DcaProcessor.getDCA(null, time,
                                            BudgetManagerSimple.getInstance().getBudget(), symbol2OrderRunning);
                                    for (String symbol : symbolDcaLossBig) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (Utils.isTickerAvailable(ticker)) {
//                                            Map<Short, float[]> symbol2PredDca = time2FundingPreDca.get(time);
//                                            if (symbol2PredDca != null) {
//                                                float[] fundingPred = symbol2PredDca.get(SimpleSymbolMapper.getInstance().getId(symbol));
//                                                if (fundingPred != null) {
//                                                    if (fundingPred[0] > 0.4) {
//                                                        LOG.info("❌ [FILTER AI] {}: Dca Prediction too high ({})", symbol, fundingPred[0]);
//                                                        continue;
//                                                    }
//                                                }
//                                            } else {
//                                                LOG.info("No Dca prediction data for time: {}", Utils.normalizeDateYYYYMMDDHHmm(time));
//                                            }
                                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
//                                            LOG.info("Dca big loss: {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), ticker.priceClose);
                                            Double priceMax15M = getMax15M(tickers);
                                            MarketLevelChange leveChange2Dca;
                                            if (calMarginRunning(symbol) < BudgetManagerSimple.getInstance().getBudget()) {
                                                leveChange2Dca = MarketLevelChange.DCA_LEVEL1;
                                            } else {
                                                leveChange2Dca = MarketLevelChange.DCA_LEVEL2;
                                            }
                                            createOrderBUY(symbol, ticker, leveChange2Dca,
                                                    time2MarketData.get(time), priceMax15M, symbol2Ticker);
                                        }
                                    }

                                    logByProcessTime(startTimeRun, "Done dca big", time);
                                    startTimeRun = System.currentTimeMillis();
                                }

                                // funding level 1
                                if (MarketBigChangeDetector.isFundingFeeTrade(marketData.rateDown15MAvg,
                                        marketData.rateDownAvg, marketData.rateUpAvg, minRate15Min60M)
                                ) {
                                    Set<String> symbolFundingBuy = FundingFeeManager.getInstance().getFundingListSymbol2Trade(time);
                                    Set<String> symbolBuyFundingFee = new HashSet<>();
                                    symbolBuyFundingFee.addAll(symbolFundingBuy);
                                    symbolBuyFundingFee.removeAll(symbol2OrderRunning.keySet());
                                    TreeMap<Float, String> fundingPredict2Symbol = new TreeMap<>();
                                    for (String symbol : symbolBuyFundingFee) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        double rate1m = (ticker.priceClose - ticker.priceOpen) / ticker.priceOpen;
                                                        // Logic: Chỉ giữ lại nếu (rate1m < -0.65%)
                                        // Tức là đang sập mạnh.
                                        if (rate1m >= -0.0065) {
                                            continue;
                                        }

                                        Map<Short, float[]> symbol2Pred = time2FundingPre.get(time);
                                        if (symbol2Pred != null) {
                                            float[] fundingPred = symbol2Pred.get(SimpleSymbolMapper.getInstance().getId(symbol));
                                            if (fundingPred != null) {
                                                if (fundingPred[0] > 0.2) {
                                                    LOG.info("❌ [FILTER AI] {}: Funding Prediction too high ({})", symbol, fundingPred[0]);
                                                    continue;
                                                }
                                                fundingPredict2Symbol.put(fundingPred[0], symbol);
                                            }
                                        } else {
                                            LOG.info("No funding prediction data for time: {}", Utils.normalizeDateYYYYMMDDHHmm(time));
                                        }
                                    }
                                    int counter = 0;
                                    for (String symbol : fundingPredict2Symbol.values()) {
                                        counter++;
                                        if (counter > 30) {
                                            break;
                                        }
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                        Double priceMax15M = getMax15M(tickers);
                                        createOrderBUY(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY,
                                                time2MarketData.get(time), priceMax15M, symbol2Ticker);
                                    }
                                }
                            }
                            logByProcessTime(startTimeRun, "Done funding fee", time);
                            startTimeRun = System.currentTimeMillis();
                            // BTC trend reverse
//                            Double rateBtcTrendReverse = null;
//                            if (time2MarketData.get(time) != null) {
//                                rateBtcTrendReverse = time2MarketData.get(time).btcReversion;
//                            }
//                            if (rateBtcTrendReverse != null && rateBtcTrendReverse >= Configs.BTC_TREND_REVERSE_RATE_MIN_TRADE) {
//                                levelChange = MarketLevelChange.BTC_TREND_REVERSE;
//                                List<String> symbol2BUY = new ArrayList<>();
//                                for (String symbol : Constants.specialSymbol) {
//                                    Double rateLoss = calRateLoss(symbol);
//                                    Double budget = BudgetManagerSimple.getInstance().getBudget();
//                                    Double marginOfSym = calMarginRunning(symbol);
//                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
//                                    OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
//                                    boolean isDcaSpecialSymbol = true;
//                                    if (order != null) {
//                                        isDcaSpecialSymbol = MarketBigChangeDetector.isDcaWithBtcReverse(rateLoss,
//                                                budget, marginOfSym, ticker.priceClose, order.lastEntry);
//                                    }
//                                    if (isDcaSpecialSymbol) {
//                                        symbol2BUY.add(symbol);
//                                    }
//
//                                }
//                                for (String symbol : symbol2BUY) {
//                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
//                                    if (Utils.isTickerAvailable(ticker)) {
//                                        createOrderBUY(symbol, ticker, levelChange, time2MarketData.get(time), null, symbol2Ticker);
//                                    }
//                                }
//                            }
//                            logByProcessTime(startTimeRun, "Done btc reverse done", time);
//                            startTimeRun = System.currentTimeMillis();

                            if (time % Utils.TIME_DAY == 0) {
                                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, true);
                                BudgetManagerSimple.getInstance().updateBudget();
                            } else {
                                if (time % (15 * Utils.TIME_MINUTE) == 0) {
                                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                                }
                            }
                            logByProcessTime(startTimeRun, "Done budget data", time);


                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                }
                time2Tickers = null;
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
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime); // Hoặc dùng biến startTime của vòng lặp
        int finalYear = cal.get(Calendar.YEAR);
        BudgetManagerSimple.getInstance().balanceIndex.year2UnrealizedPnl.put(finalYear, 0d);
        FundingFeeManager.getInstance().writeData2File();
        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
        Storage.writeObject2File("storage/orderRunning.data", symbol2OrderRunning);
        Storage.writeObject2File("storage/BalanceIndex.data", BudgetManagerSimple.getInstance().balanceIndex);
        BudgetManagerSimple.getInstance().printBalanceIndex();
        try {
            TraceOrderDone.printOrderTestDone("storage/printDone.csv", allOrderDone);
        } catch (Exception e) {
            e.printStackTrace();
        }
        Utils.printMemoryUse();
    }

    private void logByProcessTime(Long startTimeRun, String msg, Long time) {
        long duration = (System.currentTimeMillis() - startTimeRun);
        if (duration > 50) {
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


    public void initData() throws IOException, ParseException {
        // clear Data Old
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();
        File fileMarketData = new File(Configs.FILE_ENTRY_MARKET_LEVEL);
        if (!fileMarketData.exists() || fileMarketData.lastModified() < System.currentTimeMillis() - Utils.TIME_DAY) {
            new ExportMarketData2File().exportMarketEntries(null);
        }

        if (!new File(Configs.FILE_AI_ENTRY_PREDICTIONS).exists()) {
            try {
                new RunGeneratePredictions().generateAndSave();
            } catch (Exception e) {
                throw new RuntimeException(e);
            }
        }
        time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
        predictionMap = (TreeMap<Long, AiPredictionData>) StorageSnappy.readObjectFromFile(Configs.FILE_AI_ENTRY_PREDICTIONS);
//        try {
//            dcaBrain = new DcaOnnxInferenceManager(Configs.FILE_AI_DCA_PREDICTIONS);
//        } catch (OrtException e) {
//            e.printStackTrace();
//        }
        aiRejectFilter = new AIRejectFilter();
    }

    private void startUpdateOldOrderTrading(Long time, String symbol, List<KlineObjectSimple> tickers) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
        if (orderMulti != null) {
            KlineObjectSimple ticker = tickers.get(tickers.size() - 1);
            if (orderMulti.timeStart <= ticker.startTime.longValue()) {
                orderMulti.updatePriceByKlineSimple(ticker);
                if (ticker.maxPrice >= orderMulti.priceEntry * 1.007 || orderMulti.priceSL != null) {
                    Float maxChangeIn90M = getMaxRateIn90MForTradingStop(time);
                    orderMulti.updateStatusNew(maxChangeIn90M, ticker);
                    if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                            || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                        closeOrder(symbol, orderMulti);
                    } else {
                        orderMulti.updateTPSL(maxChangeIn90M, ticker);
                    }
                }
            }
        }
    }

    private Float getMaxRateIn90MForTradingStop(Long time) {
        AiPredictionData predict = predictionMap.get(time);
        if (predict == null) {
            return 0f;
        } else {
            return predict.predReturn15M;
        }
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
                null, quantity, Configs.LEVERAGE_ORDER,
                time2Order.lastEntry().getValue().symbol,
                time2Order.lastEntry().getKey(),
                time2Order.lastEntry().getKey(), orders.get(0).side);
        orderResult.minPrice = ticker.priceClose;
        orderResult.lastPrice = ticker.priceClose;
        orderResult.lastEntry = orders.get(orders.size() - 1).lastEntry;
        orderResult.rateChange = orders.get(orders.size() - 1).rateChange;
        orderResult.tickerOpen = time2Order.lastEntry().getValue().tickerOpen;
        orderResult.marketLevelChange = time2Order.lastEntry().getValue().marketLevelChange;

        return orderResult;
    }

    public void createOrderBUY(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange,
                               MarketDataObject marketData, Double maxPrice15m, Map<String, KlineObjectSimple> symbol2Ticker) {
        AiPredictionData predict = predictionMap.get(ticker.startTime.longValue());


        if (predict != null && !levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            if (aiRejectFilter.checkSignal(predict).decision.equals(AIRejectFilter.FilterDecision.REJECT)) {
//                LOG.info("⛔ REJECTED BY RISK FILTER: {} {}", predict.predReturn1H, predict.predRisk4H);
                return; // Dừng ngay
            }
        }
        Double entry = ticker.priceClose;
        Integer leverage = Configs.LEVERAGE_ORDER;

        Double marginRunning = calMarginRunning();
        Double balanceBasic = BudgetManagerSimple.getInstance().balanceBasic;
        Double budget = BudgetManagerSimple.getInstance().getBudget();

        budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange);

        if (budget == null) {
            return;
        }

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
//        order.rateChange = maxPrice15m;
        if (marketData != null) {
            order.marketData = marketData;
        }
//        order.predict = predictDca;
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);

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


    public void initDataReady(TreeMap<Long, MarketDataObject> time2MarketData,
                              TreeMap<Long, AiPredictionData> predictionMap, AIRejectFilter aiRejectFilter) throws OrtException { // <--- THÊM THAM SỐ NÀY

        // Reset Data Old
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();

        // Gán dữ liệu cache vào biến của instance
        this.time2MarketData = time2MarketData;
        this.predictionMap = predictionMap; // <--- GÁN DỮ LIỆU AI
        this.aiRejectFilter = aiRejectFilter;
//        this.aiRejectFilter = new AIRejectFilter();
//        this.dcaBrain = new DcaOnnxInferenceManager(Configs.FILE_AI_DCA_PREDICTIONS);

    }


}
