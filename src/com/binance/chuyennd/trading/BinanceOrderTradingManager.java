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
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
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
    public ExecutorService executorServiceOrderManager = Executors.newFixedThreadPool(Configs.NUMBER_THREAD_ORDER_MANAGER);
    private final ConcurrentHashMap<String, OrderTargetInfo> symbol2Processing = new ConcurrentHashMap<>();


    public static void main(String[] args) throws InterruptedException, ParseException {
        LOG.info("Start trader with target: {}%", Utils.formatPercent(Configs.RATE_TARGET));
        new DetectEntrySignal2Trader().start();
        new BinanceOrderTradingManager().start();
        Reporter.startThreadReportPosition();
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
//                        if (FuturesRules.getInstance().getSymsLocked().contains(order.symbol)) {
//                            LOG.info("Sym {} is locking by trading rule!", order.symbol);
//                            continue;
//                        }
//                        if (BudgetManager.getInstance().getInvesting2Check()
//                                >= BudgetManager.getInstance().MAX_CAPITAL_RATE
//                        ) {
//                            LOG.info("Stop trading {} {} because investing over: {}", order.symbol,
//                                    Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
//                                    BudgetManager.getInstance().getInvesting());
//                            continue;
//
//                        }

                        if (!symbol2Processing.containsKey(order.symbol)) {
                            if (order.status.equals(OrderTargetStatus.REQUEST)) {
                                symbol2Processing.put(order.symbol, order);
                                executorServiceOrderNew.execute(() -> processOrderNewMarketNew(order));
                            }
//                            if (order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
//                                symbol2Processing.put(order.symbol, order);
//                                executorServiceOrderNew.execute(() -> createTPSL(order));
//                            }
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
            // check running
//            PositionRisk pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo(order.symbol);
            if (RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING, order.symbol) != null) {
                LOG.info("Reject because symbol {} have position running!", order.symbol);
            } else {
                LOG.info("Create order market {} {}", order.side, order.symbol);
                Order orderInfo = OrderHelper.newOrderMarket(order.symbol, order.side, order.quantity, BudgetManager.getInstance().getLeverage());
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, order.symbol, Utils.toJson(order));
                String log = order.side + " " + order.symbol + " entry: " + order.priceEntry
                        + " quantity: " + order.quantity
                        + " time:" + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart)
                        + " market level: " + order.marketLevel;
                LOG.info(log);
//                executorServiceOrderManager.execute(() -> Utils.sendSms2Telegram(log));
                if (orderInfo != null) {
                    // create take profit and stop loss
//                    order.status = OrderTargetStatus.POSITION_RUNNING;
//                    RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE, Utils.toJson(order));
                } else {
                    LOG.info("Create order symbol {} false! {}", order.symbol, Utils.toJson(order));
                }
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

//    private void startThreadManagerOrderNew() {
//        new Thread(() -> {
//            Thread.currentThread().setName("ThreadManagerOrderNew");
//            LOG.info("Start thread ThreadManagerOrderNew");
//            while (true) {
//                executorServiceOrderManager.execute(() -> processManagerPosition(symbol2FinalTicker));
//                try {
//                    Thread.sleep(2 * Utils.TIME_MINUTE);
//                } catch (InterruptedException ex) {
//                    java.util.logging.Logger.getLogger(BinanceOrderTradingManager.class.getName()).log(Level.SEVERE, null, ex);
//                }
//            }
//        }).start();
//    }

    public void processManagerPosition(Map<String, KlineObjectNumber> symbol2Ticker) {
        long startTime = System.currentTimeMillis();
        LOG.info("Start check all position: {}", new Date());
        try {
            // get all open order
            LOG.info("Get all Open order.");
            List<Order> ordersOpen = BinanceFuturesClientSingleton.getInstance().getAllOpenOrderInfos();
            // get all position
            LOG.info("Get all position.");
            List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
            Map<String, PositionRisk> symbol2Pos = new HashMap<>();
            for (PositionRisk position : positions) {
                if (position.getPositionAmt().doubleValue() != 0) {
                    symbol2Pos.put(position.getSymbol(), position);
                }
                updateSymbolRunning(symbol2Pos.keySet());
            }
            Map<String, Order> symbol2OrderTp = new HashMap<>();
            Map<String, Order> symbol2OrderSL = new HashMap<>();
            for (Order order : ordersOpen) {
                if (StringUtils.equals(order.getType(), OrderType.TAKE_PROFIT.toString())
                        || StringUtils.equals(order.getType(), OrderType.TAKE_PROFIT_MARKET.toString())) {
                    PositionRisk pos = symbol2Pos.get(order.getSymbol());
                    if (pos != null
                            && Math.abs(pos.getPositionAmt().doubleValue()) == order.getOrigQty().doubleValue()) {
                        symbol2OrderTp.put(order.getSymbol(), order);
                    } else {
                        try {
                            LOG.info("Cancel order take profit not position: {}", order.getSymbol());
                            BinanceFuturesClientSingleton.getInstance().cancelOrder(
                                    order.getSymbol(), order.getClientOrderId());

                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                }
                if (StringUtils.equals(order.getType(), OrderType.STOP_MARKET.toString())) {
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
            processDynamicTP_SL(positions, symbol2OrderTp, symbol2OrderSL);
            // process position not tp or sl fail
            for (Map.Entry<String, PositionRisk> entry : symbol2Pos.entrySet()) {
                String symbol = entry.getKey();
                PositionRisk pos = entry.getValue();
                Order orderTp = symbol2OrderTp.get(symbol);
                Order orderSL = symbol2OrderSL.get(symbol);
                OrderTargetInfo orderInfo = getOrderInfo(pos.getSymbol());
                KlineObjectNumber ticker = symbol2Ticker.get(symbol);
                if (ticker == null) {
                    continue;
                }
                Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                Double rateLoss = Utils.rateOf2Double(pos.getMarkPrice().doubleValue(), pos.getEntryPrice().doubleValue());
                if (orderSL == null
                        && orderInfo != null) {
                    if ((System.currentTimeMillis() - pos.getUpdateTime()) >= Configs.TIME_AFTER_ORDER_2_SL * Utils.TIME_MINUTE
                            || (rateChange < -0.005 && orderInfo.priceTP != null)
                            || rateLoss > 0.05) {
                        Double rateStopLoss = Configs.RATE_STOP_LOSS;
                        if (orderInfo.marketLevel != null
                                && (orderInfo.marketLevel.equals(MarketLevelChange.BTC_REVERSE)
                                || orderInfo.marketLevel.equals(MarketLevelChange.SMALL_UP_15M)
                                || orderInfo.marketLevel.equals(MarketLevelChange.BIG_UP_15M)
                        )) {
                            rateStopLoss = 3 * Configs.RATE_STOP_LOSS;
                        }
                        if (orderInfo.priceSL == null) {
                            Double rateStop;
                            if (rateLoss > rateStopLoss * 1 / 3) {
                                if (rateLoss > rateStopLoss * 2 / 3) {
                                    rateStop = rateLoss - rateStopLoss * 2 / 3;
                                } else {
                                    rateStop = rateLoss - rateStopLoss * 1 / 3;
                                }
                            } else {
                                if (rateLoss < -rateStopLoss * 5 / 6) {
                                    rateStop = -rateLoss + rateStopLoss;
                                } else {
                                    rateStop = rateStopLoss;
                                }
                            }
                            Double priceSLNew = Utils.calPriceTarget(symbol, pos.getEntryPrice().doubleValue(), OrderSide.SELL, rateStop);
                            LOG.info("Renew price SL:{} {} {} {} {} {}%", symbol, orderInfo.marketLevel,
                                    Utils.normalizeDateYYYYMMDDHHmm(pos.getUpdateTime()),
                                    Utils.normalizeDateYYYYMMDDHHmm(ticker.endTime.longValue()),
                                    priceSLNew, Utils.formatPercent(rateLoss - Configs.RATE_STOP_LOSS));
                            orderInfo.priceSL = priceSLNew;
                            createSL(pos, orderInfo.priceSL);
                        }
                    }
                }
                if (orderTp == null
                        && orderInfo != null) {
                    if ((System.currentTimeMillis() - pos.getUpdateTime()) > Configs.TIME_AFTER_ORDER_2_TP * Utils.TIME_MINUTE
                            || rateChange > 0.001
                            || rateLoss > 0.03) {
                        if (orderInfo.priceTP == null) {
                            double priceEntry = pos.getEntryPrice().doubleValue();
                            Double rateProfit;
                            if (rateLoss < 0.0) {
                                rateProfit = 3 * Configs.RATE_TARGET;
                            } else {
                                rateProfit = rateLoss + 3 * Configs.RATE_TARGET;
                            }
                            Double priceTPNew = Utils.calPriceTarget(symbol, priceEntry, OrderSide.BUY, rateProfit);
                            LOG.info("Create price TP:{} {} {} {} {} {}%", symbol, orderInfo.marketLevel,
                                    Utils.normalizeDateYYYYMMDDHHmm(pos.getUpdateTime()),
                                    Utils.normalizeDateYYYYMMDDHHmm(ticker.endTime.longValue())
                                    , priceTPNew, Utils.formatPercent(Utils.rateOf2Double(priceTPNew, priceEntry)));
                            orderInfo.priceTP = priceTPNew;
                            createTp(pos, orderInfo.priceTP);
                        }
                    }
                }
            }
        } catch (Exception e) {
            LOG.error("ERROR during ThreadManagerOrderNew: {}", e);
            e.printStackTrace();
        }
        Long timeProcess = (System.currentTimeMillis() - startTime) * 10 / Utils.TIME_SECOND;
        LOG.info("Final check all position: {}s", timeProcess.doubleValue() / 10);
    }

    private void processDynamicTP_SL(List<PositionRisk> positions, Map<String, Order> symbol2OrderTp, Map<String, Order> symbol2OrderSL) {
        long startTime = System.currentTimeMillis();
        int counterOrderRunning = 0;
        int counterOrder15M = 0;
        Double rateLossTotal = 0d;
        for (PositionRisk position : positions) {
            try {
                if (position.getPositionAmt().doubleValue() == 0) {
                    continue;
                }
                counterOrderRunning++;
                Double rateLoss = Utils.rateOf2Double(position.getMarkPrice().doubleValue(), position.getEntryPrice().doubleValue());
                rateLossTotal += rateLoss;
                Double priceEntry = position.getEntryPrice().doubleValue();

                OrderSide side2Sl = OrderSide.SELL;
                String symbol = position.getSymbol();
                OrderTargetInfo orderInfo = getOrderInfo(symbol);
                if (orderInfo == null) {
                    continue;
                }
                if (StringUtils.containsIgnoreCase(orderInfo.marketLevel.toString(), "15M")){
                    counterOrder15M ++;
                }
                if (orderInfo.priceSL != null) {
                    Double rateSL = BudgetManager.getInstance().callRateLossDynamicBuy(rateLoss);
                    if (rateLoss >= 0.006 && rateLoss < 0.029) {
                        if (rateLoss < 0.01) {
                            rateSL = 0.5;
                        }else{
                            rateSL = rateLoss * 100/2;
                        }
                    }
                    Double priceSL = orderInfo.priceSL;
                    if (position.getPositionAmt().doubleValue() < 0) {
                        side2Sl = OrderSide.BUY;
                    }

                    Double priceSLNew = Utils.calPriceTarget(symbol, priceEntry, side2Sl, -rateSL / 100);
                    double priceSLChange = priceSLNew - priceSL;
                    if (position.getPositionAmt().doubleValue() < 0) {
                        priceSLChange = -priceSLChange;
                    }
                    // move sl
                    if (rateLoss >= 0.005 && priceSLChange > 0) {
                        LOG.info("Update SL {} {} {} {}->{} {}%", Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart),
                                Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), symbol, priceSL,
                                priceSLNew, Utils.formatPercent(rateSL / 100));
                        orderInfo.priceSL = priceSLNew;
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderInfo));
                        Order orderSLOld = symbol2OrderSL.get(symbol);
                        if (orderSLOld != null) {
                            LOG.info("Cancel order sl to renew: {}", symbol);
                            BinanceFuturesClientSingleton.getInstance().cancelOrder(
                                    orderSLOld.getSymbol(), orderSLOld.getClientOrderId());
                            createSL(position, orderInfo.priceSL);
                        }
                    }
                }
                // move tp
                if (orderInfo.priceTP != null) {
                    Double priceTP = orderInfo.priceTP;
                    if (rateLoss > 0.0) {
                        Double rateTP = BudgetManager.getInstance().callTPDynamicBuy(rateLoss);
                        OrderSide side2TP = OrderSide.BUY;
                        if (position.getPositionAmt().doubleValue() < 0) {
                            side2TP = OrderSide.SELL;
                        }
                        Double priceTPNew = Utils.calPriceTarget(symbol, priceEntry, side2TP, rateTP / 100);
                        double priceTpChange = priceTPNew - priceTP;
                        if (position.getPositionAmt().doubleValue() < 0) {
                            priceTpChange = -priceTpChange;
                        }
                        if (priceTpChange > 0) {
                            LOG.info("Update TP {} {} {} {}->{} {}%", Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart),
                                    Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()), symbol, priceTP,
                                    priceTPNew, Utils.formatPercent(rateTP / 100));
                            orderInfo.priceTP = priceTPNew;
                            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol, Utils.toJson(orderInfo));
                            Order orderTpOld = symbol2OrderTp.get(symbol);
                            if (orderTpOld != null) {
                                LOG.info("Cancel order tp to renew: {}", symbol);
                                BinanceFuturesClientSingleton.getInstance().cancelOrder(
                                        orderTpOld.getSymbol(), orderTpOld.getClientOrderId());
                                createTp(position, orderInfo.priceTP);
                            }
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        long timeProcess = System.currentTimeMillis() - startTime;
        if (counterOrderRunning != 0){
            BudgetManager.getInstance().rateLossAvg = rateLossTotal/counterOrderRunning;
        }else{
            BudgetManager.getInstance().rateLossAvg = 0d;
        }
        BudgetManager.getInstance().totalOrder15MRunning = counterOrder15M;
        BudgetManager.getInstance().totalOrderRunning = counterOrderRunning;
        LOG.info("Process dynamic tp/sl for {} positions: {}s", counterOrderRunning, timeProcess / Utils.TIME_SECOND);
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
            Double currentPrice = ClientSingleton.getInstance().getCurrentPrice(pos.getSymbol());
            String log;
            if (pos.getPositionAmt().doubleValue() > 0) {
                for (int i = 1; i < 50; i++) {
                    if (priceSL < currentPrice) {
                        break;
                    }
                    priceSL = Utils.calPriceTarget(pos.getSymbol(), pos.getEntryPrice().doubleValue(), OrderSide.SELL, Configs.RATE_TARGET * i);
                }
                log = "Create sl -> SELL "
                        + pos.getSymbol() + " " + pos.getPositionAmt().doubleValue() + " " + pos.getEntryPrice().doubleValue()
                        + " -> " + priceSL + " rate: " + Utils.formatPercent(Math.abs(Utils.rateOf2Double(priceSL,
                        pos.getEntryPrice().doubleValue())));
                OrderHelper.stopLoss(pos.getSymbol(), OrderSide.SELL, pos.getPositionAmt().doubleValue(), priceSL);
            } else {
                for (int i = 1; i < 50; i++) {
                    if (priceSL > currentPrice) {
                        break;
                    }
                    priceSL = Utils.calPriceTarget(pos.getSymbol(), pos.getEntryPrice().doubleValue(), OrderSide.BUY, Configs.RATE_TARGET * i);
                }
                log = "Create sl -> BUY "
                        + pos.getSymbol() + " " + pos.getPositionAmt().doubleValue() + " " + pos.getEntryPrice().doubleValue()
                        + " -> " + priceSL + " rate: " + Utils.formatPercent(Math.abs(Utils.rateOf2Double(priceSL,
                        pos.getEntryPrice().doubleValue())));
                OrderHelper.stopLoss(pos.getSymbol(), OrderSide.BUY, -pos.getPositionAmt().doubleValue(), priceSL);
            }
            LOG.info(log);
//            executorServiceOrderManager.execute(() -> Utils.sendSms2Telegram(log));
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
