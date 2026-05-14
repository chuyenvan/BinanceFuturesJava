package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.DcaProcessor;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class SimulatorOfflineKaggle {
    public static final Logger LOG = LoggerFactory.getLogger(SimulatorOfflineKaggle.class);

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;
    public TreeMap<Long, MarketDataObject> time2MarketData;
    public TreeMap<Long, AiPredictionData> predictionMap;
    public TreeMap<Long, long[]> time2SymbolPred;
    public AIRejectFilter aiRejectFilter;
    public Map<String, KlineObjectSimple> symbol2LastTicker = new HashMap<>();

    public ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry = new ConcurrentHashMap<>();
    public ConcurrentHashMap<String, OrderTargetInfoTest> symbol2OrderRunning = new ConcurrentHashMap<>();

    public void initDataReady(TreeMap<Long, MarketDataObject> time2MarketData,
                              TreeMap<Long, AiPredictionData> predictionMap,
                              TreeMap<Long, long[]> time2FundingPre,
                              AIRejectFilter aiRejectFilter) {

        // Reset Data Old
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();

        // Gán dữ liệu cache vào biến của instance
        this.time2MarketData = time2MarketData;
        this.predictionMap = predictionMap;
        this.time2SymbolPred = time2FundingPre;
        this.aiRejectFilter = aiRejectFilter;

        symbol2OrdersEntry.clear();
        symbol2OrderRunning.clear();
        symbol2LastTicker.clear();
    }

    public void simulate(long startTs, long endTs) {
        long currentDay = startTs;

        while (currentDay <= endTs) {
            // Load offline chunk cho 1 ngày
            TreeMap<Long, Map<String, KlineObjectSimple>> dailyData = KaggleDataLoader.loadDailyTickers(currentDay);

            if (dailyData != null) {
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : dailyData.entrySet()) {
                    long time = entry.getKey();
                    Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();

                    try {
                        // update for update ranking coin
                        HistoryManager.getInstance().updateHistory(symbol2Ticker);
                        for (Map.Entry<String, KlineObjectSimple> tickerEntry : symbol2Ticker.entrySet()) {
                            String symbol = tickerEntry.getKey();
                            KlineObjectSimple ticker = tickerEntry.getValue();
                            if (!Utils.isTickerAvailable(ticker)) {
                                updateSymbolDeListed(symbol, time);
                                continue;
                            }
                            symbol2LastTicker.put(symbol, ticker);
                        }

                        // --- BƯỚC 2: UPDATE ACTIVE ORDERS ---
                        if (!symbol2OrderRunning.isEmpty()) {
                            for (String runningSymbol : new ArrayList<>(symbol2OrderRunning.keySet())) {
                                KlineObjectSimple ticker = symbol2Ticker.get(runningSymbol);
                                if (ticker != null) {
                                    startUpdateOldOrderTrading(time, runningSymbol, ticker);
                                }
                            }
                        }

                        MarketDataObject marketData = time2MarketData.get(time);
                        Set<String> symbolLocked = new HashSet<>();
                        MarketLevelChange levelChange = null;
                        AiPredictionData predict = predictionMap.get(time);

                        if (predict != null && marketData != null) {
                            levelChange = MarketBigChangeDetector.getMarketStatus1M(marketData.rateDownAvg, marketData.rateUpAvg,
                                    marketData.rateDown15MAvg);

                            // buy signal new
                            if (levelChange != null) {
                                Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                                symbolLocked.addAll(symbol2OrderRunning.keySet());
                                if (levelChange.equals(MarketLevelChange.SMALL_DOWN) || levelChange.equals(MarketLevelChange.SMALL_UP) || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M) || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)) {
                                    numberOrder = numberOrder / 2;
                                }
                                Set<String> symbol2BUY = new HashSet<>();
                                TreeMap<Float, String> predict2Symbol = extractPredict2Symbol(time2SymbolPred.get(time));
                                symbol2BUY.addAll(MarketBigChangeDetector.getTopSymbol(numberOrder, symbol2Ticker, symbolLocked, predict2Symbol));

                                List<String> symbolDcaLevel = DcaProcessor.getDCA(levelChange, time, BudgetManagerSimple.getInstance().getBudget(), symbol2OrderRunning);

                                // check create order new
                                for (String symbol : symbol2BUY) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    if (!Utils.isTickerAvailable(ticker)) {
                                        continue;
                                    }
                                    createOrderBUY(symbol, ticker, levelChange, time2MarketData.get(time));
                                }
                                for (String symbol : symbolDcaLevel) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    if (Utils.isTickerAvailable(ticker)) {
                                        createOrderBUY(symbol, ticker, MarketLevelChange.DCA_LEVEL1, time2MarketData.get(time));
                                    }
                                }
                            }
                        }

                        if (marketData != null) {
                            if (MarketBigChangeDetector.isDcaAlt(marketData.rateDown15MAvg, marketData.rateDownAvg, marketData.rateUpAvg)) {
                                // dca buy
                                List<String> symbolDcaLossBig = DcaProcessor.getDCA(null, time, BudgetManagerSimple.getInstance().getBudget(), symbol2OrderRunning);
                                for (String symbol : symbolDcaLossBig) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    if (Utils.isTickerAvailable(ticker)) {
                                        createOrderBUY(symbol, ticker, MarketLevelChange.DCA_LEVEL1, time2MarketData.get(time));
                                    }
                                }
                            }

                            // 🔥 BƯỚC 3: FUNDING FEE O(N) 🔥
                            long[] symbol2Pred = time2SymbolPred.get(time);
                            if (symbol2Pred != null) {
                                TreeMap<Float, String> predict2Symbol = new TreeMap<>();
                                float maxThres = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * Configs.AI_DYNAMIC_MAX;

                                for (long encodedData : symbol2Pred) {
                                    float symbolPred = Float.intBitsToFloat((int) encodedData);

                                    if (symbolPred > maxThres) continue;

                                    short targetId = (short) (encodedData >> 32);
                                    String symbol = SimpleSymbolMapper.getInstance().getSymbol(targetId);

                                    if (symbol != null && !symbol2OrderRunning.containsKey(symbol)) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (Utils.isTickerAvailable(ticker)) {
                                            predict2Symbol.put(symbolPred, symbol);
                                        }
                                    }
                                }

                                for (String symbol : predict2Symbol.values()) {
                                    KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                    createOrderBUY(symbol, ticker, MarketLevelChange.PREDICT_SYMBOL_TRADE, marketData);
                                }
                            }
                        }

                        if (time % Utils.TIME_DAY == 0) {
                            if (Configs.IS_HPO_MODE) {
                                if (Utils.isMidnightFirstDay(time)) {
                                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, true);
                                    BudgetManagerSimple.getInstance().updateBudget();
                                } else {
                                    BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                                    BudgetManagerSimple.getInstance().updateBudget();
                                }
                            }
                        } else {
                            if (time % (15 * Utils.TIME_MINUTE) == 0) {
                                BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                            }
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            }
            currentDay += Utils.TIME_DAY;
        }

        // add all order running to done (END OF SIMULATION)
        for (List<OrderTargetInfoTest> orderRunning : symbol2OrdersEntry.values()) {
            for (OrderTargetInfoTest orderInfo : orderRunning) {
                OrderTargetInfoTest masterOrder = symbol2OrderRunning.get(orderInfo.symbol);
                if (masterOrder != null) {
                    orderInfo.lastPrice = masterOrder.lastPrice;
                    orderInfo.priceTP = orderInfo.lastPrice;
                    orderInfo.minPrice = masterOrder.minPrice;
                    orderInfo.timeUpdate = masterOrder.timeUpdate;
                }
                orderInfo.updateFundingFee();
                allOrderDone.put(-orderInfo.timeUpdate + allOrderDone.size(), orderInfo);
            }
        }
    }

    private TreeMap<Float, String> extractPredict2Symbol(long[] encodedDataArray) {
        TreeMap<Float, String> predict2Symbol = new TreeMap<>();
        if (encodedDataArray != null && encodedDataArray.length > 0) {
            for (long encodedData : encodedDataArray) {
                short symbolId = (short) (encodedData >> 32);
                float pred = Float.intBitsToFloat((int) encodedData);
                String symbol = SimpleSymbolMapper.getInstance().getSymbol(symbolId);
                if (StringUtils.isNotEmpty(symbol)) {
                    predict2Symbol.put(pred, symbol);
                }
            }
        }
        return predict2Symbol;
    }

    public void updateSymbolDeListed(String symbol, Long time) {
        OrderTargetInfoTest order = symbol2OrderRunning.get(symbol);
        if (order != null) {
            if (order.timeUpdate < time - 2 * Utils.TIME_DAY) {
                order.status = OrderTargetStatus.STOP_LOSS_DONE;
                order.priceTP = order.lastPrice;
                closeOrder(order.symbol, order);
            }
        }
    }

    private void startUpdateOldOrderTrading(Long time, String symbol, KlineObjectSimple ticker) {
        OrderTargetInfoTest orderMulti = symbol2OrderRunning.get(symbol);
        if (orderMulti != null) {
            if (orderMulti.timeStart <= ticker.startTime.longValue()) {
                orderMulti.updatePriceByKlineSimple(ticker);
                if (ticker.maxPrice >= orderMulti.priceEntry * 1.007 || orderMulti.priceSL != null) {
                    Float maxChangeIn90M = getMaxRateIn90MForTradingStop(time);
                    orderMulti.updateStatusNew(maxChangeIn90M, ticker);
                    if (orderMulti.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE) || orderMulti.status.equals(OrderTargetStatus.STOP_LOSS_DONE) || orderMulti.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
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

            allOrderDone.put(-order.timeUpdate + allOrderDone.size(), order);
            BudgetManagerSimple.getInstance().updatePnl(order);
        }
        symbol2OrdersEntry.remove(symbol);
        symbol2OrderRunning.remove(symbol);
        BudgetManagerSimple.getInstance().updatePositionMargin(symbol2OrderRunning.values());
    }

    private OrderTargetInfoTest mergeOrder(List<OrderTargetInfoTest> orders, KlineObjectSimple ticker) {
        TreeMap<Long, OrderTargetInfoTest> time2Order = new TreeMap<>();
        float quantity = 0f;
        float margin = 0f;
        OrderSide side = orders.get(0).side;
        for (OrderTargetInfoTest orderInfo : orders) {
            time2Order.put(orderInfo.timeStart, orderInfo);
            margin += orderInfo.priceEntry * orderInfo.quantity;
            quantity += orderInfo.quantity;
        }
        float entry = margin / quantity;
        OrderTargetInfoTest orderResult = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity, Configs.LEVERAGE_ORDER, time2Order.lastEntry().getValue().symbol, time2Order.lastEntry().getKey(), time2Order.lastEntry().getKey(), orders.get(0).side);
        orderResult.minPrice = ticker.priceClose;
        orderResult.lastPrice = ticker.priceClose;
        orderResult.lastEntry = orders.get(orders.size() - 1).lastEntry;
        orderResult.rateChange = orders.get(orders.size() - 1).rateChange;
        orderResult.tickerOpen = time2Order.lastEntry().getValue().tickerOpen;
        orderResult.marketLevelChange = time2Order.lastEntry().getValue().marketLevelChange;

        return orderResult;
    }

    public void createOrderBUY(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange,
                               MarketDataObject marketData) {

        Float symbolPred = null;

        AiPredictionData predict = predictionMap.get(ticker.startTime);
        if (predict != null && !levelChange.equals(MarketLevelChange.BIG_DOWN)) {
            AIRejectFilter.FilterResult filterResult = null;
            if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) {
                long[] symbol2Pred = time2SymbolPred.get(ticker.startTime);
                if (symbol2Pred != null) {
                    symbolPred = getPredictionFromPrimitiveArray(symbol2Pred, SimpleSymbolMapper.getInstance().getId(symbol));
                    filterResult = aiRejectFilter.checkSignalDynamic(predict, symbolPred);
                }
            }
            if (filterResult == null)
                filterResult = aiRejectFilter.checkSignal(predict);

            if (filterResult.decision == AIRejectFilter.FilterDecision.REJECT) {
                return;
            }
        }

        if (levelChange != MarketLevelChange.DCA_LEVEL1) {
            if (MarketBigChangeDetector.is50PercentOrderLoss(symbol2OrderRunning.values(), ticker.startTime)) {
                return;
            }
        }
        Float entry = ticker.priceClose;
        Integer leverage = Configs.LEVERAGE_ORDER;

        Float marginRunning = calMarginRunning();
        Float balanceBasic = BudgetManagerSimple.getInstance().balanceBasic;
        Float budget = BudgetManagerSimple.getInstance().getBudget();

        budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange);

        if (budget == null) {
            return;
        }

        long currentTs = ticker.startTime;
        float tierMultiplier = CoinRankManager.getInstance().getBudgetMultiplier(symbol);
        CoinRankManager.CoinTier myTier = CoinRankManager.getInstance().getCoinTier(symbol, currentTs);
        if (myTier == CoinRankManager.CoinTier.TIER_3_SHITCOIN) {
            if (levelChange == MarketLevelChange.DCA_LEVEL1) {
                return;
            }
        }

        budget *= tierMultiplier;
        Float quantity = Utils.calQuantityTest(budget, leverage, entry, symbol);

        if (StringUtils.equals(symbol, Constants.SYMBOL_PAIR_BTC)) {
            Float minBtcTrade = 0.002f;
            if (quantity < minBtcTrade) {
                quantity = minBtcTrade;
            }
        }

        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity, leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BUY);
        order.minPrice = entry;
        order.lastEntry = entry;
        order.lastPrice = entry;

        order.tickerOpen = ticker;
        order.marketLevelChange = levelChange;
        if (marketData != null) {
            order.marketData = marketData;
        }
        order.predict = predict;
        order.symbolPred = symbolPred;
        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.get(symbol);
        if (orders == null) {
            orders = new ArrayList<>();
        }
        orders.add(order);

        BudgetManagerSimple.getInstance().counterOrderCreated.incrementAndGet();
        symbol2OrdersEntry.put(symbol, orders);

        // PHỤC HỒI HÀM mergeOrder: Rất quan trọng để thiết lập lại minPrice, lastPrice đúng chuẩn
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

    private Float calMarginRunning() {
        Float marginTotal = 0f;
        for (OrderTargetInfoTest order : symbol2OrderRunning.values()) {
            if (order.priceSL == null) {
                marginTotal += order.calMargin();
            }
        }
        BudgetManagerSimple.getInstance().marginRunning = marginTotal;
        return marginTotal;
    }

    private Float getPredictionFromPrimitiveArray(long[] encodedArray, short targetId) {
        for (long encodedData : encodedArray) {
            if ((short) (encodedData >> 32) == targetId) {
                return Float.intBitsToFloat((int) encodedData);
            }
        }
        return null;
    }
}