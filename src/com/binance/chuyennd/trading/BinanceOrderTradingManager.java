/*
 * Copyright 2024 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.trading;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.helper.OrderHelper;
import com.binance.chuyennd.helper.PositionHelper;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.chuyennd.websocket.ListenAllTicker;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderType;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;

/**
 * @author pc
 */
public class BinanceOrderTradingManager {

    public static final Logger LOG = LoggerFactory.getLogger(BinanceOrderTradingManager.class);
    public ExecutorService executorServiceOrderNew = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    private final ConcurrentHashMap<String, Long> symbol2Processing = new ConcurrentHashMap<>();


    public static void main(String[] args) throws InterruptedException, ParseException {
        new DetectEntrySignal2TradeNormal().start();
        new BinanceOrderTradingManager().start();
    }

    private void start() throws InterruptedException {
        initData();
        startThreadListenQueueOrder2ManagerNew();
        startThreadManagerOrder();
        startThreadAutoRestartProgram();
    }


    private void startThreadManagerOrder() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadManagerOrder");
            LOG.info("Start thread ThreadManagerOrder {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
            try {
                // update first
                updatePositionInfo();
            } catch (Exception e) {
                e.printStackTrace();
            }
            while (true) {
                try {
                    processManagerPosition();
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadManagerOrder: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectEntrySignal2TradeNormal.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private void startThreadAutoRestartProgram() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadAutoRestartProgram");
            LOG.info("Start thread ThreadAutoRestartProgram");
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_HOUR * 4);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(DetectEntrySignal2TradeNormal.class.getName()).log(Level.SEVERE, null, ex);
                }
                try {
                    Utils.reset("Reset by Schedule");
                } catch (Exception e) {
                    LOG.error("ERROR during Restart: {}", e);
                    e.printStackTrace();
                }
            }

        }).start();
    }

    private void startThreadListenQueueOrder2ManagerNew() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadListenQueueOrder2ManagerNew");
            LOG.info("Start thread ThreadListenQueueOrder2ManagerNew!");
            while (true) {
                List<String> data;
                try {
                    data = RedisHelper.getInstance().get().blpop(0, RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE);
                    String orderJson = data.get(1);
                    try {
                        OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
                        LOG.info("Queue listen order to manager order received : {} {} ", order.side, order.symbol);
                        if (!symbol2Processing.containsKey(order.symbol)
                                || symbol2Processing.get(order.symbol) < System.currentTimeMillis() - 2 * Utils.TIME_MINUTE) {
                            if (order.status.equals(OrderTargetStatus.REQUEST)) {
                                symbol2Processing.put(order.symbol, System.currentTimeMillis());
                                executorServiceOrderNew.execute(() -> processOrderNewMarketNew(order));
                            }
                        } else {
                            LOG.info("{} is lock because processing! {}", order.symbol, symbol2Processing.size());
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadListenQueuePosition2ManagerNew {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }


    private void processOrderNewMarketNew(OrderTargetInfo order) {
        try {
            LOG.info("Create order market {} {}", order.side, order.symbol);
            Order orderInfo = OrderHelper.newOrderMarket(order.symbol, order.side, order.quantity);
            BudgetManager.getInstance().symbol2Level.put(order.symbol, order.marketLevel);
            BudgetManager.getInstance().symbol2Pos.put(order.symbol, PositionHelper.createPosNew(order.symbol, orderInfo.getPrice()
                    , orderInfo.getExecutedQty()));
            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, order.symbol, Utils.toJson(order));
            String log = order.side + " " + order.symbol + " entry: " + order.priceEntry
                    + " quantity: " + order.quantity
                    + " time:" + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)
                    + " market level: " + order.marketLevel;
            LOG.info(log);
            updatePositionInfo();
        } catch (Exception e) {
            LOG.info("Error during process order: {}", Utils.toJson(order));
            try {
                Thread.sleep(200);
                if (order.timeStart > System.currentTimeMillis() - 5 * Utils.TIME_MINUTE) {
                    RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE, Utils.toJson(order));
                }
                LOG.info("ReCreate order symbol false! {} {}", order.symbol, Utils.toJson(order));
            } catch (Exception ex) {
                ex.printStackTrace();
            }
            e.printStackTrace();
        }
        symbol2Processing.remove(order.symbol);

    }

    private void initData() {
        FundingFeeManagerProduction.getInstance();
        ClientSingleton.getInstance();
    }

    public void processManagerPosition() {
        try {
            int currentSecond = Utils.getCurrentSecond();
            if (currentSecond == 10) {
                executorServiceOrderNew.execute(() -> updatePositionInfo());
            }
            // sl dynamic
            if (currentSecond % 2 == 0) {
                executorServiceOrderNew.execute(() -> updatePositionMarkPrice());
                executorServiceOrderNew.execute(() -> processDynamicTP_SL());
                executorServiceOrderNew.execute(() -> initSLFirst());

            }
            // reporter
            if (Utils.getCurrentMinute() % 15 == 0 && Utils.getCurrentSecond() == 30) {
                executorServiceOrderNew.execute(() -> checkSLErrorAtRedis());
                executorServiceOrderNew.execute(() -> new Reporter().buildReport());
            }
        } catch (Exception e) {
            LOG.error("ERROR during ThreadManagerOrderNew: {}", e);
            e.printStackTrace();
        }
    }

    private void updatePositionMarkPrice() {
        try {
            Set<PositionRisk> positions = new HashSet<>();
            positions.addAll(BudgetManager.getInstance().symbol2Pos.values());
            for (PositionRisk pos : positions) {
                Double lastPrice = ListenAllTicker.getInstance().symbol2Price.get(pos.getSymbol());
                if (lastPrice != null) {
                    pos.setMarkPrice(new BigDecimal(lastPrice));
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void initSLFirst() {
        long startTime = System.currentTimeMillis();
        Set<PositionRisk> positions = new HashSet<>();
        positions.addAll(BudgetManager.getInstance().symbol2Pos.values());
        for (PositionRisk position : positions) {
            if (position == null) {
                continue;
            }
            String symbol = position.getSymbol();
//            if (StringUtils.equals(position.getSymbol(), "MOODENGUSDT")) {
//                System.out.println("debug");
//            }
            OrderTargetInfo orderInfo = getOrderInfo(position.getSymbol());
            Double rateLoss = PositionHelper.calRateLoss(position);
            OrderSide positionSide = OrderSide.BUY;
            if (position.getPositionAmt().compareTo(new BigDecimal("0")) < 0) {
                positionSide = OrderSide.SELL;
            }
            if (orderInfo != null && orderInfo.side.equals(positionSide)) {
                if (position.getUpdateTime() < startTime + 30 * Utils.TIME_MINUTE) {
                    BudgetManager.getInstance().symbol2Level.put(symbol, orderInfo.marketLevel);
                } else {
                    BudgetManager.getInstance().symbol2Level.remove(symbol);
                }
                List<KlineObjectSimple> tickers = ListenAllTicker.getInstance().getTickerBySymbol(symbol);
                Double maxChange60M = MarketBigChangeDetector.getMaxRateIn60M(tickers);
                Double rateMin2MoveSl = TradeUtils.calRateMinWithMaxChange60M(maxChange60M);
                if (rateLoss > rateMin2MoveSl) {
                    if (orderInfo.priceSL == null) {
                        OrderSide sideSL = OrderSide.SELL;
                        Double rateStop = TradeUtils.calRateLossDynamicBuy(rateLoss);
                        if (orderInfo.side.equals(OrderSide.SELL)) {
                            sideSL = OrderSide.BUY;
                        }
                        Double priceSLNew = Utils.calPriceTarget(symbol, position.getEntryPrice().doubleValue(), sideSL, -rateStop);
                        if (priceSLNew != 0) {
                            LOG.info("Renew price SL:{} {} {} {} {} {}%", symbol, orderInfo.marketLevel,
                                    Utils.normalizeDateYYYYMMDDHHmm(position.getUpdateTime()),
                                    Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                                    priceSLNew, Utils.formatPercent(-rateStop));
                            if (createSL(position, priceSLNew)) {
                                orderInfo.priceSL = priceSLNew;
                                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderInfo));
                            }
                        }
                    }
                }
            } else {
                OrderSide side = OrderSide.BUY;
                if (position.getPositionAmt().compareTo(new BigDecimal("0")) < 0) {
                    side = OrderSide.SELL;
                }
                OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, position.getEntryPrice().doubleValue(),
                        null, position.getPositionAmt().doubleValue(), BudgetManager.getInstance().getLeverage(), symbol, position.getUpdateTime(),
                        position.getUpdateTime(), side, Constants.TRADING_TYPE_VOLUME_MINI);
                orderTrade.marketLevel = MarketLevelChange.ORDER_PROFIT;
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderTrade));
                LOG.info("New order 2 redis because order null: {}", Utils.toJson(orderTrade));
            }
        }
    }


    public void updatePositionInfo() {
        String lockName = "UpdateAllPos";
        if (SymbolOrderLockingManager.getInstance().isLock(lockName, 5)) {
            LOG.info("Symbol {} is locking for loop!", lockName);
            return;
        }
        SymbolOrderLockingManager.getInstance().addLock(lockName);
        long startTime = System.currentTimeMillis();
        List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
        if (positions == null || positions.isEmpty()) {
            LOG.info("Error get position from binance! {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
            return;
        }
        Map<String, PositionRisk> symbol2Pos = new HashMap<>();
        BudgetManager.getInstance().symbol2Margin.clear();
        BudgetManager.getInstance().marginBig.clear();
        BudgetManager.getInstance().symbol2Pos.clear();
        BudgetManager.getInstance().symbolSell.clear();
        BudgetManager.getInstance().symbolBuy.clear();
        Double marginTotal = 0d;
        for (PositionRisk position : positions) {

            if (position.getPositionAmt().compareTo(new BigDecimal("0")) == 0) {
                continue;
            }
            symbol2Pos.put(position.getSymbol(), position);
            if (PositionHelper.calRateLoss(position) < 6 * Configs.RATE_PROFIT_STOP_MARKET) {
                marginTotal += PositionHelper.callMargin(position);
            }
            BudgetManager.getInstance().symbol2Margin.put(position.getSymbol(), PositionHelper.callMargin(position));
            if (PositionHelper.callMargin(position) >= 1.5 * BudgetManager.getInstance().getBudget()) {
                BudgetManager.getInstance().marginBig.add(position.getSymbol());
            }
            if (position.getPositionAmt().compareTo(new BigDecimal("0")) > 0) {
                BudgetManager.getInstance().symbolBuy.add(position.getSymbol());
            } else {
                BudgetManager.getInstance().symbolSell.add(position.getSymbol());
            }
        }
        BudgetManager.getInstance().marginRunning = marginTotal;
        BudgetManager.getInstance().symbol2Pos.putAll(symbol2Pos);
        BudgetManager.getInstance().removeSymbolNotPos(symbol2Pos.keySet());
        updateSymbolRunning(symbol2Pos.keySet());
        Long timeProcess = (System.currentTimeMillis() - startTime);
        LOG.info("Update all position:{} {} ms", BudgetManager.getInstance().symbol2Pos.size(), timeProcess.doubleValue());
    }

    public void processDynamicTP_SL() {
        Set<PositionRisk> positions = new HashSet<>();
        positions.addAll(BudgetManager.getInstance().symbol2Pos.values());
        for (PositionRisk position : positions) {
            try {
                if (position == null || position.getPositionAmt().compareTo(new BigDecimal("0")) == 0) {
                    continue;
                }
                Double rateLoss = PositionHelper.calRateLoss(position);
                Double priceEntry = position.getEntryPrice().doubleValue();
                String symbol = position.getSymbol();
                OrderTargetInfo orderInfo = getOrderInfo(symbol);
                if (orderInfo == null) {
                    continue;
                }
                if (orderInfo.priceEntry != priceEntry) {
                    orderInfo.priceEntry = priceEntry;
                }
                OrderSide side2Sl;
                List<KlineObjectSimple> tickers = ListenAllTicker.getInstance().getTickerBySymbol(symbol);
                Double maxChange60M = MarketBigChangeDetector.getMaxRateIn60M(tickers);
                Double rateMin2MoveSl = TradeUtils.calRateMinWithMaxChange60M(maxChange60M * 1.5);
                // BUY
                if (position.getPositionAmt().compareTo(new BigDecimal("0")) > 0) {
                    side2Sl = OrderSide.SELL;
                } else { // SELL
                    side2Sl = OrderSide.BUY;
                }
                if (orderInfo.priceSL != null && rateLoss > rateMin2MoveSl) {
                    // move SL
                    Double priceSL = orderInfo.priceSL;
                    Double rateSL = TradeUtils.calRateLossDynamicBuy(rateLoss);
                    Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, side2Sl, -rateSL);
                    double priceSLChange = priceSLNew - priceSL;
                    if (position.getPositionAmt().compareTo(new BigDecimal("0")) < 0) {
                        priceSLNew = Utils.calPriceTarget(symbol, priceEntry, side2Sl, -rateSL);
                        priceSLChange = priceSL - priceSLNew;
                    }

                    // move sl

                    if (rateLoss >= rateMin2MoveSl
                            && priceSLChange > 0) {
                        if (symbol2Processing.containsKey(symbol)) {
                            if (symbol2Processing.get(symbol) > System.currentTimeMillis() - 5 * Utils.TIME_MINUTE) {
                                LOG.info("{} is locking in list: {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(symbol2Processing.get(symbol)));
                                return;
                            }
                        }
                        LOG.info("Update SL {} {} {} {}->{} {}%", Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart),
                                Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), symbol, priceSL,
                                priceSLNew, Utils.formatPercent(rateSL));
                        if (createSL(position, priceSLNew)) {
                            orderInfo.priceSL = priceSLNew;
                            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderInfo));
                        }
                    }
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private void updateSymbolRunning(Set<String> symbols) {
        try {
            Set<String> symbolsAtRedis = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING);
            for (String symbol : symbols) {
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING, symbol, symbol);
            }
            for (String symbol : symbolsAtRedis) {
                if (!symbols.contains(symbol)) {
                    RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING, symbol);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void checkSLErrorAtRedis() {
        try {
            List<Order> orders = BinanceFuturesClientSingleton.getInstance().getAllOpenOrderInfos();
            Set<String> symbolHasSLOrder = new HashSet<>();
            for (Order order : orders) {
                symbolHasSLOrder.add(order.getSymbol());
            }
            for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO)) {
                OrderTargetInfo orderInfo = getOrderInfo(symbol);
                if (orderInfo == null) {
                    continue;
                }
                if (!BudgetManager.getInstance().symbol2Pos.containsKey(symbol)) {
                    continue;
                }
                if (orderInfo.priceSL != null && !symbolHasSLOrder.contains(symbol)) {
                    LOG.info("Remove SL at redis of {} {} {}", symbol,
                            orderInfo.priceSL, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
                    orderInfo.priceTP = null;
                    orderInfo.priceSL = null;
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderInfo));
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    public boolean createSL(PositionRisk pos, Double priceSL) {
        try {
            if (priceSL == null) {
                return false;
            }
            String symbol = pos.getSymbol();
            if (symbol2Processing.containsKey(symbol)) {
                if (symbol2Processing.get(symbol) > System.currentTimeMillis() - 2 * Utils.TIME_MINUTE) {
                    LOG.info("{} is locking in list: {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(symbol2Processing.get(symbol)));
                    return false;
                }
            }
            symbol2Processing.put(symbol, System.currentTimeMillis());
            Order orderSLResult = null;
            try {
                List<Order> openOrders = BinanceFuturesClientSingleton.getInstance().getOpenOrders(pos.getSymbol());
                if (!openOrders.isEmpty()) {
                    for (Order openOrder : openOrders) {
                        if (openOrder.getType().equals(OrderType.STOP_MARKET.toString())) {
                            if (openOrder.getPrice().doubleValue() != priceSL) {
                                LOG.info("Cancel order sl to renew: {}", openOrder.getSymbol());
                                BinanceFuturesClientSingleton.getInstance().cancelOrder(
                                        openOrder.getSymbol(), openOrder.getClientOrderId());
                            } else {
                                LOG.info("{} have sl order -> not create sl", pos.getSymbol());
                                return false;
                            }
                        }
                        if (openOrder.getType().equals(OrderType.LIMIT.toString()) && openOrder.getPrice().doubleValue() == priceSL) {
                            LOG.info("Cancel order sl type limit: " + openOrder.getOrderId() + " of " + openOrder.getSymbol());
                            BinanceFuturesClientSingleton.getInstance().cancelOrder(openOrder.getSymbol(), openOrder.getClientOrderId());
                        }
                    }
                }
                // chua co sl -> tao sl
                String log;
                if (pos.getPositionAmt().compareTo(new BigDecimal("0")) > 0) {
                    if (pos.getEntryPrice().equals(new BigDecimal("0.0"))) {
                        LOG.info("Error process SL for: {} {}", pos.getSymbol(), pos.getEntryPrice());
                    } else {
                        pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo(pos.getSymbol());
                        if (pos.getEntryPrice().equals(new BigDecimal("0.0"))) {
                            LOG.info("Position has finished: {} {} {}", pos.getSymbol(), pos.getEntryPrice(),
                                    Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
                        } else {
                            if (pos != null) {
                                log = "Create sl -> SELL "
                                        + pos.getSymbol() + " " + pos.getPositionAmt().doubleValue() + " " + pos.getEntryPrice().doubleValue()
                                        + " -> " + priceSL + " rate: " + Utils.formatPercent(Math.abs(Utils.rateOf2Double(priceSL,
                                        pos.getEntryPrice().doubleValue())));
                                LOG.info(log);
                                orderSLResult = OrderHelper.stopLoss(pos.getSymbol(), pos.getPositionAmt().doubleValue(), priceSL);
                            }
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            symbol2Processing.remove(symbol);
            if (orderSLResult != null) {
                return true;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    public OrderTargetInfo getOrderInfo(String symbol) {
        try {
            String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
            OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
            return order;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }
}
