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
import com.binance.chuyennd.client.OrderHelper;
import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderType;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * @author pc
 */
public class BinanceOrderTradingManager {

    public static final Logger LOG = LoggerFactory.getLogger(BinanceOrderTradingManager.class);
    public ExecutorService executorServiceOrderNew = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    private final ConcurrentHashMap<String, OrderTargetInfo> symbol2Processing = new ConcurrentHashMap<>();


    public static void main(String[] args) throws InterruptedException, ParseException {
        LOG.info("Start trader with target: {}%", Utils.formatPercent(Configs.RATE_TARGET));
        new DetectEntrySignal2Trader().start();
        new BinanceOrderTradingManager().start();
    }

    private void start() throws InterruptedException {
        initData();
        startThreadListenQueueOrder2ManagerNew();
//        startThreadManagerOrderNew();
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

                        if (!symbol2Processing.containsKey(order.symbol)) {
                            if (order.status.equals(OrderTargetStatus.REQUEST)) {
                                symbol2Processing.put(order.symbol, order);
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
            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, order.symbol, Utils.toJson(order));
            String log = order.side + " " + order.symbol + " entry: " + order.priceEntry
                    + " quantity: " + order.quantity
                    + " time:" + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)
                    + " market level: " + order.marketLevel;
            BudgetManager.getInstance().updatePositionInitialMargin();
            LOG.info(log);
            if (orderInfo == null) {
                LOG.info("Create order symbol {} false! {}", order.symbol, Utils.toJson(order));
            }
        } catch (Exception e) {
            LOG.info("Error during process order: {}", Utils.toJson(order));
            e.printStackTrace();
        }
        symbol2Processing.remove(order.symbol);

    }

    private void initData() {
        ClientSingleton.getInstance();
    }

    public void processManagerPosition() {
        long startTime = System.currentTimeMillis();
        BudgetManager.getInstance().updatePositionInitialMargin();
        LOG.info("Start check all position: {}", new Date());
        try {
            // get all open order
            LOG.info("Get all Open order.");
            List<Order> ordersOpen = BinanceFuturesClientSingleton.getInstance().getAllOpenOrderInfos();
            // get all position
            LOG.info("Get all position.");
            List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
            Map<String, PositionRisk> symbol2Pos = new HashMap<>();
            BudgetManager.getInstance().symbol2Margin.clear();
            BudgetManager.getInstance().marginBig.clear();
            BudgetManager.getInstance().symbol2Pos.clear();
            for (PositionRisk position : positions) {
                if (position.getPositionAmt().doubleValue() > 0) {
                    BudgetManager.getInstance().symbol2Margin.put(position.getSymbol(), PositionHelper.callMargin(position));
                    if (PositionHelper.callMargin(position) > 10 * BudgetManager.getInstance().getBudget()) {
                        BudgetManager.getInstance().marginBig.add(position.getSymbol());
                    }
                    symbol2Pos.put(position.getSymbol(), position);
                }
            }
            BudgetManager.getInstance().symbol2Pos.putAll(symbol2Pos);
            BudgetManager.getInstance().removeSymbolNotPos(symbol2Pos.keySet());
            updateSymbolRunning(symbol2Pos.keySet());
            Map<String, Order> symbol2OrderSL = new HashMap<>();
            for (Order order : ordersOpen) {
                if (StringUtils.equals(order.getType(), OrderType.STOP_MARKET.toString())
                        && StringUtils.equals(order.getSide(), OrderSide.SELL.toString())) {
                    PositionRisk pos = symbol2Pos.get(order.getSymbol());
                    if (pos != null
                            && Math.abs(pos.getPositionAmt().doubleValue()) == order.getOrigQty().doubleValue()) {
                        symbol2OrderSL.put(order.getSymbol(), order);
                    } else {
                        try {
                            LOG.info("Cancel order sl not position: {}", order.getSymbol());
                            BinanceFuturesClientSingleton.getInstance().cancelOrder(
                                    order.getSymbol(), order.getClientOrderId());

                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                }
            }
            // tp/sl dynamic
            processDynamicTP_SL(positions, symbol2OrderSL);
            // process position not tp or sl fail
//            BudgetManager.getInstance().symbol2Level.clear();
            for (Map.Entry<String, PositionRisk> entry : symbol2Pos.entrySet()) {
                String symbol = entry.getKey();
                PositionRisk pos = entry.getValue();
                OrderTargetInfo orderInfo = getOrderInfo(pos.getSymbol());
                Double rateLoss = Utils.rateOf2Double(pos.getMarkPrice().doubleValue(), pos.getEntryPrice().doubleValue());
                if (orderInfo != null) {
                    BudgetManager.getInstance().symbol2Level.put(symbol, orderInfo.marketLevel);
                    Double rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;
                    if (Constants.specialSymbol.contains(symbol) || Constants.stableSymbol.contains(symbol)) {
                        rateMin2MoveSl = 0.01;
                    }
                    if ((System.currentTimeMillis() - pos.getUpdateTime()) >= Configs.TIME_AFTER_ORDER_2_SL * Utils.TIME_MINUTE
                            || rateLoss > rateMin2MoveSl
                    ) {
                        if (orderInfo.priceSL == null) {
                            Double rateStop = BudgetManager.getInstance().callRateLossDynamicBuy(rateLoss, symbol,rateMin2MoveSl);
                            Double priceSLNew = Utils.calPriceTarget(symbol, pos.getEntryPrice().doubleValue(), OrderSide.SELL, -rateStop);
                            if (priceSLNew <= pos.getEntryPrice().doubleValue() && rateLoss > 0) {
                                Double rateStopLoss = Configs.RATE_STOP_LOSS_ALT;
                                if (Constants.specialSymbol.contains(symbol) || Constants.stableSymbol.contains(symbol)) {
                                    rateStopLoss = Configs.RATE_STOP_LOSS_SPECIAL;
                                }
                                priceSLNew = Utils.calPriceTarget(symbol, pos.getEntryPrice().doubleValue(), OrderSide.SELL, rateStopLoss);
                            }
                            LOG.info("Renew price SL:{} {} {} {} {} {}%", symbol, orderInfo.marketLevel,
                                    Utils.normalizeDateYYYYMMDDHHmm(pos.getUpdateTime()),
                                    Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                                    priceSLNew, Utils.formatPercent(-rateStop));
                            orderInfo.priceSL = priceSLNew;
                            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderInfo));
                            createSL(pos, orderInfo.priceSL);
                        }
                    }
                } else {
                    OrderSide side = OrderSide.BUY;
                    if (pos.getPositionAmt().doubleValue() < 0) {
                        side = OrderSide.SELL;
                    }
                    OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, pos.getEntryPrice().doubleValue(),
                            null, pos.getPositionAmt().doubleValue(), BudgetManager.getInstance().getLeverage(symbol), symbol, pos.getUpdateTime(),
                            pos.getUpdateTime(), side, Constants.TRADING_TYPE_VOLUME_MINI);
                    orderTrade.marketLevel = MarketLevelChange.ORDER_PROFIT;
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderTrade));
                    LOG.info("New order 2 redis because order null: {}", Utils.toJson(orderTrade));
                }
            }
            // reporter
            if (Utils.getCurrentMinute() % 15 == 0 && Utils.getCurrentSecond() < 10) {
                executorServiceOrderNew.execute(() -> new Reporter().buildReport(positions));
            }
        } catch (Exception e) {
            LOG.error("ERROR during ThreadManagerOrderNew: {}", e);
            e.printStackTrace();
        }
        Long timeProcess = (System.currentTimeMillis() - startTime) * 10 / Utils.TIME_SECOND;
        LOG.info("Final check all position: {}s locked:{}", timeProcess.doubleValue() / 10, BudgetManager.getInstance().marginBig);
    }

    private void processDynamicTP_SL(List<PositionRisk> positions, Map<String, Order> symbol2OrderSL) {
        long startTime = System.currentTimeMillis();
        int counterOrderRunning = 0;
        for (PositionRisk position : positions) {
            try {
                if (position.getPositionAmt().doubleValue() <= 0) {
                    continue;
                }
                counterOrderRunning++;
                Double rateLoss = Utils.rateOf2Double(position.getMarkPrice().doubleValue(), position.getEntryPrice().doubleValue());
                Double priceEntry = position.getEntryPrice().doubleValue();

                OrderSide side2Sl = OrderSide.SELL;
                String symbol = position.getSymbol();
                OrderTargetInfo orderInfo = getOrderInfo(symbol);
                if (orderInfo == null) {
                    continue;
                }
                if (orderInfo.priceEntry != priceEntry) {
                    orderInfo.priceEntry = priceEntry;
                }

                if (orderInfo.priceSL != null) {
                    // move SL
                    Double rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;
                    if (Constants.specialSymbol.contains(symbol) || Constants.stableSymbol.contains(symbol)) {
                        rateMin2MoveSl = 0.01;
                    }
                    Double rateSL = BudgetManager.getInstance().callRateLossDynamicBuy(rateLoss, position.getSymbol(), rateMin2MoveSl);
                    Double priceSL = orderInfo.priceSL;
                    if (position.getPositionAmt().doubleValue() < 0) {
                        side2Sl = OrderSide.BUY;
                    }

                    Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, side2Sl, -rateSL);
                    double priceSLChange = priceSLNew - priceSL;
                    if (position.getPositionAmt().doubleValue() < 0) {
                        priceSLChange = -priceSLChange;
                    }
                    // sl init -> not order sl running
                    if (symbol2OrderSL.get(symbol) == null) {
                        createSL(position, priceSLNew);
                        orderInfo.priceSL = priceSLNew;
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderInfo));
                    } else {
                        // move sl
                        if ((rateLoss >= rateMin2MoveSl
                                && priceSLChange > 0)
                                && priceSLNew > priceEntry
                                && symbol2OrderSL.get(symbol) != null) {
                            LOG.info("Update SL {} {} {} {}->{} {}%", Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart),
                                    Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), symbol, priceSL,
                                    priceSLNew, Utils.formatPercent(rateSL));
                            orderInfo.priceSL = priceSLNew;
                            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderInfo));
                            Order orderSLOld = symbol2OrderSL.get(symbol);
                            if (orderSLOld != null) {
                                LOG.info("Cancel order sl to renew: {}", symbol);
                                BinanceFuturesClientSingleton.getInstance().cancelOrder(
                                        orderSLOld.getSymbol(), orderSLOld.getClientOrderId());
                            }
                            createSL(position, orderInfo.priceSL);
                        }
                    }

                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        long timeProcess = System.currentTimeMillis() - startTime;

        LOG.info("Process dynamic tp/sl for {} positions: {}s", counterOrderRunning, timeProcess / Utils.TIME_SECOND);
    }

//    private void sendDcaOrder(PositionRisk position) {
//        try {
//            String symbol = position.getSymbol();
//            List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1M);
//
//            new DetectEntrySignal2Trader().createOrderBuyRequest(symbol, tickers.get(tickers.size() - 1),
//                    MarketLevelChange.DCA_ORDER);
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//    }

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

    public void createTp(PositionRisk pos, Double priceTp) {
        try {
            if (priceTp == null) {
                return;
            }
            List<Order> openOrders = BinanceFuturesClientSingleton.getInstance().getOpenOrders(pos.getSymbol());
            if (!openOrders.isEmpty()) {
                for (Order openOrder : openOrders) {
                    if (openOrder.getType().equals(OrderType.TAKE_PROFIT.toString())
                            || openOrder.getType().equals(OrderType.TAKE_PROFIT_MARKET.toString())) {
                        LOG.info("{} have tp order -> not create tp", pos.getSymbol());
                        return;
                    }
                    if (openOrder.getType().equals(OrderType.LIMIT.toString()) && openOrder.getPrice().doubleValue() == priceTp) {
                        LOG.info("Cancel order tp type limit: " + openOrder.getOrderId() + " of " + openOrder.getSymbol());
                        BinanceFuturesClientSingleton.getInstance().cancelOrder(openOrder.getSymbol(), openOrder.getClientOrderId());
                    }
                }
            }
            // chua co tp -> tao tp
            Double currentPrice = ClientSingleton.getInstance().getCurrentPrice(pos.getSymbol());

            String log;
            if (pos.getPositionAmt().doubleValue() > 0) {
                for (int i = 1; i < 50; i++) {
                    if (priceTp > currentPrice) {
                        break;
                    }
                    priceTp = Utils.calPriceTarget(pos.getSymbol(), pos.getEntryPrice().doubleValue(), OrderSide.BUY, Configs.RATE_TARGET * i);
                }
                log = "Create tp -> SELL "
                        + pos.getSymbol() + " " + pos.getPositionAmt().doubleValue() + " " + pos.getEntryPrice().doubleValue()
                        + " -> " + priceTp + " rate: " + Utils.formatPercent(Math.abs(Utils.rateOf2Double(priceTp, pos.getEntryPrice().doubleValue())));
                OrderHelper.takeProfit(pos.getSymbol(), OrderSide.SELL, pos.getPositionAmt().doubleValue(), priceTp);
            } else {
                for (int i = 1; i < 50; i++) {
                    if (priceTp < currentPrice) {
                        break;
                    }
                    priceTp = Utils.calPriceTarget(pos.getSymbol(), pos.getEntryPrice().doubleValue(), OrderSide.SELL, Configs.RATE_TARGET * i);
                }
                log = "Create tp -> BUY "
                        + pos.getSymbol() + " " + pos.getPositionAmt().doubleValue() + " " + pos.getEntryPrice().doubleValue()
                        + " -> " + priceTp + " rate: " + Utils.formatPercent(Math.abs(Utils.rateOf2Double(priceTp, pos.getEntryPrice().doubleValue())));
                OrderHelper.takeProfit(pos.getSymbol(), OrderSide.BUY, -pos.getPositionAmt().doubleValue(), priceTp);
            }
            LOG.info(log);
//            executorServiceOrderManager.execute(() -> Utils.sendSms2Telegram(log));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void createSL(PositionRisk pos, Double priceSL) {
        try {
            if (priceSL == null) {
                return;
            }
            List<Order> openOrders = BinanceFuturesClientSingleton.getInstance().getOpenOrders(pos.getSymbol());
            if (!openOrders.isEmpty()) {
                for (Order openOrder : openOrders) {
                    if (openOrder.getType().equals(OrderType.STOP_MARKET.toString())) {
                        LOG.info("{} have sl order -> not create sl", pos.getSymbol());
                        return;
                    }
                    if (openOrder.getType().equals(OrderType.LIMIT.toString()) && openOrder.getPrice().doubleValue() == priceSL) {
                        LOG.info("Cancel order sl type limit: " + openOrder.getOrderId() + " of " + openOrder.getSymbol());
                        BinanceFuturesClientSingleton.getInstance().cancelOrder(openOrder.getSymbol(), openOrder.getClientOrderId());
                    }
                }
            }
            // chua co sl -> tao sl
            String log;
            if (pos.getPositionAmt().doubleValue() > 0) {
                log = "Create sl -> SELL "
                        + pos.getSymbol() + " " + pos.getPositionAmt().doubleValue() + " " + pos.getEntryPrice().doubleValue()
                        + " -> " + priceSL + " rate: " + Utils.formatPercent(Math.abs(Utils.rateOf2Double(priceSL,
                        pos.getEntryPrice().doubleValue())));
                LOG.info(log);
                OrderHelper.stopLoss(pos.getSymbol(), OrderSide.SELL, pos.getPositionAmt().doubleValue(), priceSL);
            } else {
                log = "Create sl -> BUY "
                        + pos.getSymbol() + " " + pos.getPositionAmt().doubleValue() + " " + pos.getEntryPrice().doubleValue()
                        + " -> " + priceSL + " rate: " + Utils.formatPercent(Math.abs(Utils.rateOf2Double(priceSL,
                        pos.getEntryPrice().doubleValue())));
                LOG.info(log);
                OrderHelper.stopLoss(pos.getSymbol(), OrderSide.BUY, -pos.getPositionAmt().doubleValue(), priceSL);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private OrderTargetInfo getOrderInfo(String symbol) {
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
