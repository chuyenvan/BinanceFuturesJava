/*
 * Copyright 2023 pc.
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
package com.binance.chuyennd.testing;

import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.chuyennd.funcs.OrderHelper;
import com.binance.chuyennd.funcs.OrderStatusProcess;
import com.binance.chuyennd.object.OrderInfo;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import java.io.File;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class PositionManagerChangeInTime {

    public static final Logger LOG = LoggerFactory.getLogger(PositionManagerChangeInTime.class);
    public ConcurrentHashMap<String, OrderInfo> symbolHadOrderRunning = new ConcurrentHashMap<>();
    public ConcurrentHashMap<String, List<OrderInfo>> allOrderFnished = new ConcurrentHashMap<>();
    private static volatile PositionManagerChangeInTime INSTANCE = null;
    public final String FILE_POSITION_RUNNING = "storage/position_manager/orderRunning.data";
    public final String FILE_POSITION_FINISHED = "storage/position_manager/orderFinished.data";
    public Double BUDGET_PER_ORDER;
    public Integer LEVERAGE_ORDER;
    public Double PERCENT_TARGET_CONFIG;
    public Double PERCENT_STOPLOSS_CONFIG;
    public int counter = 0;

    public static PositionManagerChangeInTime getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new PositionManagerChangeInTime();
            INSTANCE.initClient();
        }
        return INSTANCE;
    }

    private void initClient() {
        BUDGET_PER_ORDER = Configs.getDouble("BudgetPerOrder");
        LEVERAGE_ORDER = Configs.getInt("LeverageOrder");
        PERCENT_TARGET_CONFIG = Configs.getDouble("PercentTargetConfig");
        PERCENT_STOPLOSS_CONFIG = Configs.getDouble("PercentStopLossConfig");
        if (new File(FILE_POSITION_RUNNING).exists()) {
            symbolHadOrderRunning = (ConcurrentHashMap<String, OrderInfo>) Storage.readObjectFromFile(FILE_POSITION_RUNNING);
        } else {
            symbolHadOrderRunning = new ConcurrentHashMap<>();
        }
        if (new File(FILE_POSITION_FINISHED).exists()) {
            allOrderFnished = (ConcurrentHashMap<String, List<OrderInfo>>) Storage.readObjectFromFile(FILE_POSITION_FINISHED);
        } else {
            allOrderFnished = new ConcurrentHashMap<>();
        }
        // start thread monitor symbol running
        for (OrderInfo oderInfo : symbolHadOrderRunning.values()) {
            startThreadMonitorPositionBySymbol(oderInfo);
        }
        startThreadReport();
    }

    public static void main(String[] args) {
//        System.out.println(ClientSingleton.getInstance().syncRequestClient.get24hrTickerPriceChange("BTCUSDT"));
//        System.out.println(ClientSingleton.getInstance().syncRequestClient.get("STORJUSDT"));
        new PositionManagerChangeInTime().testFuntion();
//        PositionManager.getInstance().startThreadReport();
//        PositionManager.getInstance().addOrderByTarget("CYBERUSDT", 4.0, 4.8, 5.2, OrderSide.BUY);
//        String symbol = "STORJUSDT";
//        String symbol = "BTCUSDT";
//        System.out.println(PositionManager.getInstance().getPositionBySymbol("BTCUSDT"));
//        PositionManager.getInstance().startThreadMonitorPositionBySymbol(PositionManager.getInstance().symbolHadOrderRunning.get("ZRXUSDT"));
    }

//    public void addOrderByTarget(String symbol, Double priceSL, Double priceEntry, Double priceTP, OrderSide side, Double pricePercentChange) {
//        int maxOrderTrading = 10;
//        if (symbolHadOrderRunning.size() > maxOrderTrading) {
//            LOG.info("Add order fail because had {} order running: {} entry:{} {}", maxOrderTrading, symbol, priceEntry, new Date());
//            return;
//        }
//        if (symbolHadOrderRunning.containsKey(symbol)) {
//            LOG.info("Add order fail because symbol had order active: {} entry:{} {}", symbol, priceEntry, new Date());
//            return;
//        }
//        PositionRisk position = getPositionBySymbol(symbol);
//        if (position != null && position.getPositionAmt().doubleValue() != 0) {
//            LOG.info("Add order fail because had other position of symbol {} with volume {} {} ", symbol, position.getPositionAmt(), new Date());
//            return;
//        }
//        OrderInfo orderInfo = new OrderInfo();
//        orderInfo.status = OrderStatusProcess.NEW;
//        orderInfo.percentChangeDay = pricePercentChange;
//        orderInfo.symbol = symbol;
//        orderInfo.priceEntry = Double.valueOf(Utils.normalPrice2Api(priceEntry));
//        orderInfo.priceTP = Double.valueOf(Utils.normalPrice2Api(priceTP));
//        orderInfo.priceSL = Double.valueOf(Utils.normalPrice2Api(priceSL));
//        orderInfo.orderSide = side;
//        orderInfo.quantity = Double.valueOf(Utils.normalQuantity2Api(BUDGET_PER_ORDER * LEVERAGE_ORDER / priceEntry));
//        orderInfo.leverage = LEVERAGE_ORDER;
//        orderInfo.timeCreated = System.currentTimeMillis();
//        if (isTrendWithSide(orderInfo)) {
//            Order result = OrderHelper.newOrder(orderInfo);
//            if (result != null) {
//                LOG.info("Add order success:{} {} entry: {} stoploss: {} takeprofit:{} quantity:{} {}", side, symbol, orderInfo.priceEntry, orderInfo.priceSL, orderInfo.priceTP, orderInfo.quantity, new Date());
//                symbolHadOrderRunning.put(symbol, orderInfo);
//                startThreadMonitorPositionBySymbol(orderInfo);
//                counter++;
//            } else {
//                LOG.info("Add order fail because create order fail: {} {} {}", symbol, priceEntry, new Date());
//            }
//        }
//    }

//    public void addOrderByConfig(String symbol, Double priceSL, Double priceEntry, Double priceTP, OrderSide side) {
//
//        if (symbolHadOrderRunning.contains(symbol)) {
//            LOG.info("Add order fail because symbol had order active: {} entry:{} {}", symbol, priceEntry, new Date());
//            return;
//        }
//        PositionRisk position = getPositionBySymbol(symbol);
//        if (position != null && Double.parseDouble(position.getIsolatedMargin()) != 0) {
//            LOG.info("Add order fail because had other position of symbol {} with margine {} {} ", symbol, position.getIsolatedMargin(), new Date());
//            return;
//        }
//        OrderInfo orderInfo = new OrderInfo();
//        orderInfo.status = OrderStatusProcess.NEW;
//        orderInfo.symbol = symbol;
//        orderInfo.priceEntry = Double.valueOf(Utils.normalPrice2Api(priceEntry));
//        orderInfo.priceTP = Double.valueOf(Utils.normalPrice2Api(priceTP));
//        orderInfo.priceSL = Double.valueOf(Utils.normalPrice2Api(priceSL));
//        orderInfo.orderSide = side;
//        orderInfo.quantity = Double.valueOf(Utils.normalQuantity2Api(BUDGET_PER_ORDER * LEVERAGE_ORDER / priceEntry));
//        orderInfo.leverage = LEVERAGE_ORDER;
//        Order result = OrderHelper.newOrder(orderInfo);
//        if (result != null) {
//            LOG.info("Add order success: {} entry: {} stoploss: {} takeprofit:{} quantity:{} {}", symbol, priceEntry, priceTP, priceSL, orderInfo.quantity, new Date());
//            symbolHadOrderRunning.put(symbol, orderInfo);
//            startThreadMonitorPositionBySymbol(orderInfo);
//            counter++;
//        } else {
//            LOG.info("Add order fail because create order fail: {} {} {}", symbol, priceEntry, new Date());
//        }
//    }
//
    private void startThreadMonitorPositionBySymbol(OrderInfo orderInfo) {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadMonitorPositionBySymbol-" + orderInfo.symbol);
            LOG.info("Start thread ThreadMonitorPositionBySymbol: {} !", orderInfo.symbol);

            while (true) {
                try {
                    PositionRisk position = getPositionBySymbol(orderInfo.symbol);
                    // if order new -> waiting for position active
                    // if order running -> create SL and TP if have position
                    // else check no position -> check price update order info and remove list active
                    LOG.info("Checking position for {} {}", orderInfo.symbol, position.getPositionAmt());
                    if (orderInfo.status.equals(OrderStatusProcess.NEW)) {
                        if (position.getPositionAmt().doubleValue() != 0) {
                            orderInfo.status = OrderStatusProcess.POSITION_RUNNING;
                        }
                    } else {
                        if (orderInfo.status.equals(OrderStatusProcess.POSITION_RUNNING)) {
                            if (position.getPositionAmt().doubleValue() != 0) {
                                LOG.info("Change quantity: {} -> {}", orderInfo.quantity, position.getPositionAmt());
                                orderInfo.quantity = Math.abs(position.getPositionAmt().doubleValue());
                                OrderHelper.takeProfit(orderInfo);
                                OrderHelper.stopLoss(orderInfo);
                                orderInfo.status = OrderStatusProcess.NEW_HAD_SL3TP;
                                symbolHadOrderRunning.put(orderInfo.symbol, orderInfo);
                                StringBuilder builder = new StringBuilder();
                                builder.append(orderInfo.symbol).append(" -> create SL:").append(orderInfo.priceSL).append(" TP: ").append(orderInfo.priceTP);
                                Utils.sendSms2Telegram(builder.toString());
                                LOG.info(builder.toString());
                                Storage.writeObject2File(FILE_POSITION_RUNNING, symbolHadOrderRunning);
                            }
                        } else {
                            if (waitForPositionDone(orderInfo.symbol)) {
                                Double lastPrice = ClientSingleton.getInstance().getCurrentPrice(orderInfo.symbol);
                                if (lastPrice != null) {
                                    if (lastPrice - orderInfo.priceSL < lastPrice - orderInfo.priceTP) {
                                        orderInfo.status = OrderStatusProcess.STOP_LOSS_DONE;
                                    } else {
                                        orderInfo.status = OrderStatusProcess.TAKE_PROFIT_DONE;
                                    }
                                    // sleep 30 to next trading for symbol
                                    symbolHadOrderRunning.remove(orderInfo.symbol);
                                    LOG.info("Remove symbol: {} out list running!", orderInfo.symbol);
                                    String today = Utils.getToDayFileName();
                                    List<OrderInfo> orderSucessByDate = allOrderFnished.get(today);
                                    if (orderSucessByDate == null) {
                                        orderSucessByDate = new ArrayList<>();
                                        allOrderFnished.put(today, orderSucessByDate);
                                    }
                                    orderSucessByDate.add(orderInfo);
                                    Storage.writeObject2File(FILE_POSITION_FINISHED, allOrderFnished);
                                    Storage.writeObject2File(FILE_POSITION_RUNNING, symbolHadOrderRunning);
                                    return;
                                }
                            }
                        }
                    }

                } catch (Exception e) {
                    LOG.error("ERROR during ThreadMonitorPositionBySymbol: {} {}", orderInfo.symbol, e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(30 * Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(PositionManagerChangeInTime.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private void startThreadReport() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadReportByTelegram");
            LOG.info("Start thread ThreadReportByTelegram!");
            while (true) {
                try {
                    for (Map.Entry<String, List<OrderInfo>> entry : allOrderFnished.entrySet()) {
                        String date = entry.getKey();
                        List<OrderInfo> orders = entry.getValue();
                        StringBuilder builder = new StringBuilder();
                        builder.append("Report auto trade:").append("\n");
                        Integer totalSuccess = 0;
                        Double totalMoneySuccess = 0d;
                        Integer totalFail = 0;
                        Double totalMoneyFalse = 0d;
                        for (OrderInfo order : orders) {
                            if (order.status.equals(OrderStatusProcess.TAKE_PROFIT_DONE)) {
                                System.out.println(Utils.gson.toJson(order));
                            }
                        }
                    }

                    Thread.sleep(30 * Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadReportByTelegram: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private PositionRisk getPositionBySymbol(String symbol) {
        List<PositionRisk> positionInfos = ClientSingleton.getInstance().syncRequestClient.getPositionRisk(symbol);
        PositionRisk position = null;
        if (positionInfos != null && !positionInfos.isEmpty()) {
            position = positionInfos.get(0);
        }
        return position;
    }

    private void testFuntion() {
        System.out.println(getPositionBySymbol("BIGTIMEUSDT"));
//        symbolHadOrderRunning = (ConcurrentHashMap<String, OrderInfo>) Storage.readObjectFromFile(FILE_POSITION_RUNNING);
//        OrderInfo orderInfo = symbolHadOrderRunning.get("1000PEPEUSDT");
//        OrderHelper.stopLoss(orderInfo);
//        orderInfo.priceTP = 0.1209;

//        OrderHelper.takeProfit(orderInfo);
//        OrderHelper.stopLoss(orderInfo);
//        for (OrderInfo orderInfo : symbolHadOrderRunning.values()) {
//            System.out.println(Utils.gson.toJson(orderInfo));
//        }
    }

    private boolean isTrendWithSide(OrderInfo orderInfo) {
        // check current ticket hour
        boolean isTrendSide = false;
        try {
            if (orderInfo.orderSide.equals(OrderSide.BUY) && orderInfo.percentChangeDay > 0) {
                isTrendSide = true;
            } else {
                if (orderInfo.percentChangeDay < 0 && orderInfo.orderSide.equals(OrderSide.SELL)) {
                    isTrendSide = true;
                }
            }
            LOG.info("Check trend orderside:{} {} percentChange: {} checkTrend: {}", orderInfo.symbol, orderInfo.orderSide, orderInfo.percentChangeDay, isTrendSide);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return isTrendSide;
    }

    private boolean waitForPositionDone(String symbol) {
        try {
            int counter = 0;
            for (int i = 0; i < 3; i++) {
                PositionRisk position = getPositionBySymbol(symbol);
                if (position.getPositionAmt().doubleValue() == 0) {
                    counter++;
                }
                Thread.sleep(Utils.TIME_MINUTE);
            }
            if (counter == 3) {
                return true;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }
}
