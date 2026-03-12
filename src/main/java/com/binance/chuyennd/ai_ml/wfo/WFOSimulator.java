package com.binance.chuyennd.ai_ml.wfo;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculator;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.DataManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.BotTradingConfig;
import com.binance.chuyennd.tradecore.DcaProcessor;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.apache.commons.lang.StringUtils;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class WFOSimulator {
    private final BotTradingConfig config;
    public final TreeMap<Long, OrderTargetInfoTest> allOrderDone = new TreeMap<>();
    private final ConcurrentHashMap<String, List<OrderTargetInfoTest>> symbol2OrdersEntry = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, OrderTargetInfoTest> symbol2OrderRunning = new ConcurrentHashMap<>();
    private final AIRejectFilter aiRejectFilter = new AIRejectFilter();

    public WFOSimulator(BotTradingConfig config) {
        this.config = config;
    }

    public void run(long startTime, long endTime) {
        Map<String, List<KlineObjectSimple>> symbol2History = new HashMap<>();
        long currentCursor = startTime;

        while (currentCursor < endTime) {
            TreeMap<Long, Map<String, KlineObjectSimple>> tickers = DataManager.getTickers1M(currentCursor);
            if (tickers != null) {
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : tickers.entrySet()) {
                    long time = entry.getKey();
                    if (time >= endTime) break;

                    Map<String, KlineObjectSimple> snapshot = entry.getValue();
                    updateMarketData(time, snapshot, symbol2History);
                    checkEntrySignals(time, snapshot);

                    if (time % (15 * Utils.TIME_MINUTE) == 0) {
                        BudgetManagerSimple.getInstance().updateBalance(time, allOrderDone, symbol2OrderRunning, symbol2OrdersEntry, false);
                    }
                }
            }
            currentCursor += Utils.TIME_DAY;
        }
        finalizeSession(endTime);
    }

    private void updateMarketData(long time, Map<String, KlineObjectSimple> snapshot, Map<String, List<KlineObjectSimple>> history) {
        for (String sym : snapshot.keySet()) {
            KlineObjectSimple k = snapshot.get(sym);
            if (!Utils.isTickerAvailable(k)) continue;

            List<KlineObjectSimple> list = history.computeIfAbsent(sym, s -> new ArrayList<>());
            list.add(k);
            if (list.size() > 201) list.remove(0);

            if (symbol2OrderRunning.containsKey(sym)) {
                OrderTargetInfoTest order = symbol2OrderRunning.get(sym);
                order.updatePriceByKlineSimple(k);

                AiPredictionData predict = DataManager.getAiPredictionData().get(time);
                float maxChange = (predict != null) ? predict.predReturn15M : 0f;

                order.updateStatusNew(maxChange, k);
                if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE) || order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                    closeOrder(sym, order);
                } else {
                    order.updateTPSL(maxChange, k);
                }
            }
        }
    }

    private void checkEntrySignals(long time, Map<String, KlineObjectSimple> snapshot) {
        MarketDataObject market = DataManager.getMarketData().get(time);
        if (market == null) return;

        MarketLevelChange level = MarketBigChangeDetector.getMarketStatus1M(
                market.rateDownAvg, market.rateUpAvg, market.rateBtc, market.rateDown15MAvg);

        if (level != null) {
            processSignals(time, level, snapshot, market);
        }

        if (MarketBigChangeDetector.isAiPredictTrade(market.rateDown15MAvg, market.rateDownAvg, market.rateUpAvg)) {
            processAiFunding(time, snapshot, market);
        }
    }

    private void processSignals(long time, MarketLevelChange level, Map<String, KlineObjectSimple> snapshot, MarketDataObject market) {
        int numberOrder = config.numberEntryEachSignal;
        if (level.equals(MarketLevelChange.SMALL_DOWN) || level.equals(MarketLevelChange.SMALL_UP)) {
            numberOrder /= 2;
        }

        Set<String> symbolLocked = new HashSet<>(symbol2OrderRunning.keySet());
        long[] symbol2Pred = DataManager.getFundingPredictionData(time - time % Utils.TIME_DAY, 1440).get(time);
        TreeMap<Float, String> predict2Symbol = extractPredict2Symbol(symbol2Pred);

        Set<String> symbol2BUY = MarketBigChangeDetector.getTopSymbol(numberOrder, snapshot, symbolLocked, predict2Symbol);
        List<String> symbolDca = DcaProcessor.getDCA(level, time, BudgetManagerSimple.getInstance().getBudget(), symbol2OrderRunning);

        for (String sym : symbol2BUY) {
            createOrderBUY(sym, snapshot.get(sym), level, market);
        }
        for (String sym : symbolDca) {
            createOrderBUY(sym, snapshot.get(sym), MarketLevelChange.DCA_LEVEL1, market);
        }
    }

    private void processAiFunding(long time, Map<String, KlineObjectSimple> snapshot, MarketDataObject market) {
        Set<String> candidates = new HashSet<>(snapshot.keySet());
        candidates.removeAll(symbol2OrderRunning.keySet());

        TreeMap<Float, String> sortedCandidates = new TreeMap<>();
        long[] predArray = DataManager.getFundingPredictionData(time - time % Utils.TIME_DAY, 1440).get(time);

        if (predArray != null) {
            for (String sym : candidates) {
                Float pred = getPredictionFromPrimitiveArray(predArray, SimpleSymbolMapper.getInstance().getId(sym));
                if (pred != null && pred <= config.aiPredictRateMaxThreshold) {
                    sortedCandidates.put(pred, sym);
                }
            }
        }

        int count = 0;
        for (String sym : sortedCandidates.values()) {
            if (++count > 30) break;
            createOrderBUY(sym, snapshot.get(sym), MarketLevelChange.PREDICT_SYMBOL_TRADE, market);
        }
    }

    private void createOrderBUY(String symbol, KlineObjectSimple ticker, MarketLevelChange level, MarketDataObject market) {
        AiPredictionData predict = DataManager.getAiPredictionData().get(ticker.startTime.longValue());
        if (predict != null && !level.equals(MarketLevelChange.BIG_DOWN)) {
            if (aiRejectFilter.checkSignal(predict).decision.equals(AIRejectFilter.FilterDecision.REJECT)) return;
        }

        Double marginRun = calMarginRunning();
        Double balance = BudgetManagerSimple.getInstance().balanceBasic;
        Double budget = TradeUtils.managerBudget(BudgetManagerSimple.getInstance().getBudget(), marginRun, balance, level);

        if (budget == null || budget < 5) return;

        Double quantity = Utils.calQuantityTest(budget, config.leverageOrder, ticker.priceClose, symbol);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, ticker.priceClose, null, quantity,
                config.leverageOrder, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BUY);

        order.minPrice = ticker.priceClose;
        order.lastPrice = ticker.priceClose;
        order.tickerOpen = ticker;
        order.marketLevelChange = level;
        order.marketData = market;

        List<OrderTargetInfoTest> orders = symbol2OrdersEntry.computeIfAbsent(symbol, k -> new ArrayList<>());
        orders.add(order);
        symbol2OrderRunning.put(symbol, mergeOrder(orders, ticker));
        BudgetManagerSimple.getInstance().updatePositionMargin(symbol2OrderRunning.values());
    }

    private void closeOrder(String symbol, OrderTargetInfoTest orderMulti) {
        List<OrderTargetInfoTest> entries = symbol2OrdersEntry.get(symbol);
        if (entries != null) {
            for (OrderTargetInfoTest order : entries) {
                order.timeUpdate = orderMulti.timeUpdate;
                order.status = orderMulti.status;
                order.priceTP = orderMulti.priceTP;
                order.minPrice = orderMulti.minPrice;
                order.lastPrice = orderMulti.lastPrice;
                allOrderDone.put(-order.timeUpdate + allOrderDone.size(), order);
                BudgetManagerSimple.getInstance().updatePnl(order);
            }
        }
        symbol2OrdersEntry.remove(symbol);
        symbol2OrderRunning.remove(symbol);
    }

    private void finalizeSession(long endTime) {
        symbol2OrderRunning.forEach((sym, order) -> {
            order.priceTP = order.lastPrice;
            order.timeUpdate = endTime;
            closeOrder(sym, order);
        });
    }

    private Double calMarginRunning() {
        return symbol2OrderRunning.values().stream().filter(o -> o.priceSL == null).mapToDouble(OrderTargetInfoTest::calMargin).sum();
    }

    private OrderTargetInfoTest mergeOrder(List<OrderTargetInfoTest> orders, KlineObjectSimple ticker) {
        double totalMargin = 0;
        double totalQty = 0;
        for (OrderTargetInfoTest o : orders) {
            totalMargin += o.priceEntry * o.quantity;
            totalQty += o.quantity;
        }
        double avgEntry = totalMargin / totalQty;
        OrderTargetInfoTest res = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, avgEntry, null, totalQty,
                config.leverageOrder, orders.get(0).symbol, orders.get(0).timeStart, ticker.startTime.longValue(), OrderSide.BUY);
        res.minPrice = ticker.priceClose;
        res.lastPrice = ticker.priceClose;
        res.tickerOpen = orders.get(0).tickerOpen;
        res.marketLevelChange = orders.get(0).marketLevelChange;
        return res;
    }

    private TreeMap<Float, String> extractPredict2Symbol(long[] encoded) {
        TreeMap<Float, String> res = new TreeMap<>();
        if (encoded != null) {
            for (long e : encoded) {
                res.put(Float.intBitsToFloat((int) e), SimpleSymbolMapper.getInstance().getSymbol((short) (e >> 32)));
            }
        }
        return res;
    }

    private Float getPredictionFromPrimitiveArray(long[] arr, short id) {
        for (long e : arr) if ((short) (e >> 32) == id) return Float.intBitsToFloat((int) e);
        return null;
    }
}