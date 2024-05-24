///*
// * Copyright 2024 pc.
// *
// * Licensed under the Apache License, Version 2.0 (the "License");
// * you may not use this file except in compliance with the License.
// * You may obtain a copy of the License at
// *
// *      http://www.apache.org/licenses/LICENSE-2.0
// *
// * Unless required by applicable law or agreed to in writing, software
// * distributed under the License is distributed on an "AS IS" BASIS,
// * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// * See the License for the specific language governing permissions and
// * limitations under the License.
// */
//package com.binance.chuyennd.trading;
//
//import com.educa.mail.funcs.BreadFunctions;
//import com.binance.chuyennd.bigchange.btctd.BreadDetectObject;
//import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
//import com.binance.chuyennd.client.ClientSingleton;
//import com.binance.chuyennd.client.OrderHelper;
//import com.binance.chuyennd.client.TickerFuturesHelper;
//import com.binance.chuyennd.object.KlineObjectNumber;
//import com.binance.chuyennd.position.manager.PositionHelper;
//import com.binance.chuyennd.redis.RedisConst;
//import com.binance.chuyennd.redis.RedisHelper;
//import com.binance.chuyennd.utils.Configs;
//import com.binance.chuyennd.utils.Utils;
//import com.binance.client.constant.Constants;
//import com.binance.client.model.enums.OrderSide;
//import com.binance.client.model.enums.OrderStatus;
//import com.binance.client.model.trade.Order;
//import com.binance.client.model.trade.PositionRisk;
//import java.io.File;
//import java.util.ArrayList;
//import java.util.Date;
//import java.util.List;
//import java.util.Map;
//import java.util.Set;
//import java.util.concurrent.ConcurrentHashMap;
//import java.util.concurrent.ExecutorService;
//import java.util.concurrent.Executors;
//import java.util.logging.Level;
//import org.apache.commons.io.FileUtils;
//import org.apache.commons.lang.StringUtils;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
///**
// *
// * @author pc
// */
//public class BreadTradingManager {
//
//    public static final Logger LOG = LoggerFactory.getLogger(BreadTradingManager.class);
//    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
//    public Set<? extends String> allSymbol;
//    public Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");
//    public Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
//    public Double RATE_CHANGE_MIN_2TRADING = Configs.getDouble("RATE_CHANGE_MIN_2TRADING");
//
//    public Integer LEVERAGE_ORDER_BEARD = Configs.getInt("LEVERAGE_ORDER_BEARD");
//    public Integer RATE_BUDGET_PER_ORDER = Configs.getInt("RATE_BUDGET_PER_ORDER");
//    public Double BUDGET_PER_ORDER;
//
//    public ConcurrentHashMap<String, OrderTargetInfo> symbol2Orders = new ConcurrentHashMap<>();
//
//    public static void main(String[] args) throws InterruptedException {
//        new BreadTradingManager().start();
//
//    }
//
//    private void start() throws InterruptedException {
//        initData();
//
//        startThreadAltDetectBread();
//        startThreadListenQueueOrder2Manager();
//        startThreadManagerOrder();
//    }
//
//    public void startThreadAltDetectBread() {
//        new Thread(() -> {
//            Thread.currentThread().setName("ThreadAltDetectBread");
//            LOG.info("Start thread ThreadAltDetectBread rateMin:{} breadMin:{} target: {}", RATE_CHANGE_MIN_2TRADING, RATE_BREAD_MIN_2TRADE, RATE_TARGET);
//            while (true) {
//                if (isTimeCheckBalance()) {
//                    checkUpdateBalanceAvalible();
//                }
//                if (isTimeDetectBigChange() && BUDGET_PER_ORDER > 0) {
//                    try {
//                        LOG.info("Start detect symbol is beard big! {}", new Date());
//                        for (String symbol : allSymbol) {
//                            executorService.execute(() -> detectBySymbol(symbol));
//                        }
//                    } catch (Exception e) {
//                        LOG.error("ERROR during ThreadBigBeardTrading: {}", e);
//                        e.printStackTrace();
//                    }
//                }
//                if (isTimeTrade()) {
//                    executorService.execute(() -> calAndTrade());
//                }
//                try {
//                    Thread.sleep(Utils.TIME_SECOND);
//                } catch (InterruptedException ex) {
//                    java.util.logging.Logger.getLogger(BreadTradingManager.class.getName()).log(Level.SEVERE, null, ex);
//                }
//
//            }
//        }).start();
//    }
//
//    public boolean isTimeDetectBigChange() {
//        return Utils.getCurrentMinute() % 15 == 14 && Utils.getCurrentSecond() == 55;
//    }
//
//    public boolean isTimeTrade() {
//        return Utils.getCurrentMinute() % 15 == 14 && Utils.getCurrentSecond() == 59;
//    }
//
//    public boolean isTimeCheckBalance() {
//        return Utils.getCurrentHour() == 0 && Utils.getCurrentMinute() == 0 && Utils.getCurrentSecond() == 0;
//    }
//
//    private void startThreadListenQueueOrder2Manager() {
//        new Thread(() -> {
//            Thread.currentThread().setName("ThreadListenQueueOrder2Manager");
//            LOG.info("Start thread ThreadListenQueueOrder2Manager!");
//            while (true) {
//                List<String> data;
//                try {
//                    data = RedisHelper.getInstance().get().blpop(0, RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE);
//                    LOG.info("Queue listen order to manager order received : {} ", data.toString());
//                    String orderJson = data.get(1);
//                    try {
//                        OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
//                        executorService.execute(() -> processOrderNew(order));
//                    } catch (Exception e) {
//                        e.printStackTrace();
//                    }
//                } catch (Exception e) {
//                    LOG.error("ERROR during ThreadListenQueuePosition2Manager {}", e);
//                    e.printStackTrace();
//                }
//            }
//        }).start();
//    }
//
//    private void processOrderNew(OrderTargetInfo order) {
//        try {
//            String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol);
//            if (order.status.equals(OrderTargetStatus.REQUEST) && !StringUtils.isEmpty(json)) {
//                LOG.info("Reject because symbol {} have order running! {}", order.symbol, Utils.toJson(order));
//                return;
//            }
//            if (order.status.equals(OrderTargetStatus.REQUEST)) {
//                Double priceEntry = ClientSingleton.getInstance().getCurrentPrice(order.symbol);
//                Double priceTarget = Utils.calPriceTarget(order.symbol, priceEntry, order.side, RATE_TARGET);
//                order.priceEntry = priceEntry;
//                order.priceTP = priceTarget;
//                Utils.sendSms2Telegram(order.side + " " + order.symbol + " entry: " + order.priceEntry + " -> " + order.priceTP
//                        + " target: " + Utils.formatPercent(Utils.rateOf2Double(order.priceEntry, order.priceTP))
//                        + " time:" + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart));
//
//                Order orderInfo = OrderHelper.newOrder(order.symbol, order.side, order.quantity, order.priceEntry, order.leverage);
//                if (orderInfo != null) {
//                    order.orderEntry = orderInfo;
//                    order.status = OrderTargetStatus.NEW;
//                    // create take profit and stoploss
//                    OrderSide sideTP = OrderSide.BUY;
//                    if (order.side.equals(OrderSide.BUY)) {
//                        sideTP = OrderSide.SELL;
//                    }
//                    Order orderTP = OrderHelper.takeProfit(order.symbol, sideTP, order.quantity, order.priceTP);
//                    if (orderTP != null) {
//                        order.orderTakeProfit = orderTP;
//                        order.status = OrderTargetStatus.NEW_HAD_SL3TP;
//                    }
//                    // write redis
//                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol, Utils.toJson(order));
//                } else {
//                    LOG.info("Create oder symbol {} false! {}", order.symbol, Utils.toJson(order));
//                    return;
//                }
//            }
//
//        } catch (Exception e) {
//            LOG.info("Error during process order: {}", Utils.toJson(order));
//            e.printStackTrace();
//        }
//
//    }
//
//    private void processOrderRunning(OrderTargetInfo order) {
//        try {
//            if (order.status.equals(OrderTargetStatus.NEW)) {
//                if (order.orderTakeProfit == null) {
//                    // create take profit and stoploss
//                    OrderSide sideTP = OrderSide.BUY;
//                    if (order.side.equals(OrderSide.BUY)) {
//                        sideTP = OrderSide.SELL;
//                    }
//                    Order orderTP = OrderHelper.takeProfit(order.symbol, sideTP, order.quantity, order.priceTP);
//                    if (orderTP != null) {
//                        order.orderTakeProfit = orderTP;
//                        order.status = OrderTargetStatus.NEW_HAD_SL3TP;
//                    }
//                } else {
//                    order.status = OrderTargetStatus.NEW_HAD_SL3TP;
//                }
//                // write redis
//                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol, Utils.toJson(order));
//            }
//            if (order.status.equals(OrderTargetStatus.NEW_HAD_SL3TP)) {
//                Order orderInfo = OrderHelper.readOrderInfo(order.symbol, order.orderEntry.getOrderId());
//                if (orderInfo != null && StringUtils.equalsIgnoreCase(orderInfo.getStatus(), OrderStatus.FILLED.toString())) {
//                    order.status = OrderTargetStatus.POSITION_RUNNING;
//                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol, Utils.toJson(order));
//                }
//                if (orderInfo != null && StringUtils.equalsIgnoreCase(orderInfo.getStatus(), OrderStatus.CANCELED.toString())) {
//                    order.status = OrderTargetStatus.CANCELED;
//                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol, Utils.toJson(order));
//                }
//            }
//            if (order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
//                Order orderInfo = OrderHelper.readOrderInfo(order.symbol, order.orderTakeProfit.getOrderId());
//                if (orderInfo != null && !StringUtils.equalsIgnoreCase(orderInfo.getStatus(), OrderStatus.NEW.toString())) {
//                    order.status = OrderTargetStatus.TAKE_PROFIT_DONE;
//                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol, Utils.toJson(order));
//                }
//            }
//            if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
//                    || order.status.equals(OrderTargetStatus.FINISHED)
//                    || order.status.equals(OrderTargetStatus.CANCELED)
//                    || order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
//                // delete redis
//                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol);
//                //write file
//                List<String> lines = new ArrayList<>();
//                lines.add(Utils.toJson(order));
//                FileUtils.writeLines(new File("storage/trading/order-bread-success.data"), lines, true);
//            }
//        } catch (Exception e) {
//            LOG.info("Error during process order: {}", Utils.toJson(order));
//            e.printStackTrace();
//        }
//
//    }
//
//    private void initData() throws InterruptedException {
//        allSymbol = TickerFuturesHelper.getAllSymbol();
//        allSymbol.removeAll(Constants.specialSymbol);
//        LOG.info("Have {} symbols avalible 2 trade!", allSymbol.size());
//        ClientSingleton.getInstance();
//        Thread.sleep(10000);
//        checkUpdateBalanceAvalible();
//    }
//
//    private void detectBySymbol(String symbol) {
//        try {
//            KlineObjectNumber ticker = TickerFuturesHelper.getLastTicker(symbol, Constants.INTERVAL_15M);
//            BreadDetectObject breadData = BreadFunctions.calBreadDataAlt(ticker, RATE_BREAD_MIN_2TRADE);
//            if (breadData.orderSide != null && breadData.rateChange >= RATE_CHANGE_MIN_2TRADING) {
//                LOG.info("Bigchange:{} {} {} bread above:{} bread below:{} rateChange:{}", symbol, new Date(ticker.startTime.longValue()),
//                        breadData.orderSide, breadData.breadAbove, breadData.breadBelow, breadData.totalRate);
//                Double priceEntry = ticker.priceClose;
//                Double priceTarget = Utils.calPriceTarget(symbol, priceEntry, breadData.orderSide, RATE_TARGET);
//                Double quantity = Utils.calQuantity(BUDGET_PER_ORDER, LEVERAGE_ORDER_BEARD, priceEntry, symbol);
//                if (quantity != null && quantity != 0) {
//                    OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
//                            priceTarget, quantity, LEVERAGE_ORDER_BEARD, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), breadData.orderSide, Constants.TRADING_TYPE_BREAD);
//                    Double breadMax = breadData.breadAbove;
//                    if (breadMax < breadData.breadBelow) {
//                        breadMax = breadData.breadBelow;
//                    }
//                    orderTrade.priceSL = breadMax;
//                    symbol2Orders.put(symbol, orderTrade);
////                    RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
//                } else {
//                    LOG.info("{} {} quantity false", symbol, quantity);
//                }
//            }
//        } catch (Exception e) {
//            LOG.info("Error detect big bread of symbol:{}", symbol);
//            e.printStackTrace();
//        }
//    }
//
//    private void startThreadManagerOrder() {
//        new Thread(() -> {
//            Thread.currentThread().setName("ThreadManagerOrder");
//            LOG.info("Start thread ThreadManagerOrder!");
//            while (true) {
//                try {
//                    for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER)) {
//                        OrderTargetInfo order = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol),
//                                OrderTargetInfo.class);
//                        executorService.execute(() -> processOrderRunning(order));
//                    }
//                } catch (Exception e) {
//                    LOG.error("ERROR during ThreadManagerOrder: {}", e);
//                    e.printStackTrace();
//                }
//                try {
//                    Thread.sleep(2 * Utils.TIME_MINUTE);
//                } catch (InterruptedException ex) {
//                    java.util.logging.Logger.getLogger(BreadTradingManager.class.getName()).log(Level.SEVERE, null, ex);
//                }
//            }
//        }).start();
//    }
//
//    private void calAndTrade() {
//        if (!symbol2Orders.isEmpty()) {
//            OrderTargetInfo orderMax = null;
//            Set<String> allSymbolTrading = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER);
//            for (Map.Entry<String, OrderTargetInfo> entry : symbol2Orders.entrySet()) {
//                String sym = entry.getKey();
//                OrderTargetInfo order = entry.getValue();
//                if (!allSymbolTrading.contains(sym)) {
//                    PositionRisk pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo(sym);
//                    if (pos != null && pos.getPositionAmt().doubleValue() != 0) {
//                        continue;
//                    }
//                    if (orderMax == null || orderMax.priceSL > order.priceSL) {
//                        orderMax = order;
//                    }
//                }
//            }
//            if (orderMax != null) {
//                RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderMax));
//            }
//            symbol2Orders.clear();
//        }
//    }
//
//    private void checkUpdateBalanceAvalible() {
//        Double balanceAvalible = ClientSingleton.getInstance().getBalanceAvalible();
//        if (balanceAvalible < 200) {
//            LOG.info("Not trade because balance avalible not enough! avalible: {}", ClientSingleton.getInstance().getBalanceAvalible());
//            BUDGET_PER_ORDER = 0.0;
//        } else {
//            BUDGET_PER_ORDER = RATE_BUDGET_PER_ORDER * balanceAvalible / 100;
//        }
//    }
//}
