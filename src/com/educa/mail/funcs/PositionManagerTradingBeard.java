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
package com.educa.mail.funcs;

import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.OrderHelper;
import com.binance.chuyennd.client.OrderStatusProcess;
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
public class PositionManagerTradingBeard {

    public static final Logger LOG = LoggerFactory.getLogger(PositionManagerTradingBeard.class);
    public ConcurrentHashMap<String, OrderInfo> symbolHadOrderRunning = new ConcurrentHashMap<>();
    public ConcurrentHashMap<String, List<PositionRisk>> allOrderFnished = new ConcurrentHashMap<>();
    private static volatile PositionManagerTradingBeard INSTANCE = null;
    public final String FILE_POSITION_RUNNING = "storage/position_beard_manager/orderRunning.data";
    public final String FILE_POSITION_FINISHED = "storage/position_beard_manager/positionFinished.data";
    public Double BUDGET_PER_ORDER;
    public Integer LEVERAGE_ORDER_BEARD;
    public static double RATE_CHANGE_TAKE_PROFIT;
    public int counter = 0;

    public static PositionManagerTradingBeard getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new PositionManagerTradingBeard();
            INSTANCE.initClient();
        }
        return INSTANCE;
    }

    private void initClient() {
        BUDGET_PER_ORDER = Configs.getDouble("BudgetPerOrder");
        LEVERAGE_ORDER_BEARD = Configs.getInt("LeverageOrderBeard");
        RATE_CHANGE_TAKE_PROFIT = Configs.getDouble("TakeProfitRate");

        if (new File(FILE_POSITION_RUNNING).exists()) {
            symbolHadOrderRunning = (ConcurrentHashMap<String, OrderInfo>) Storage.readObjectFromFile(FILE_POSITION_RUNNING);
        } else {
            symbolHadOrderRunning = new ConcurrentHashMap<>();
        }
        if (new File(FILE_POSITION_FINISHED).exists()) {
            allOrderFnished = (ConcurrentHashMap<String, List<PositionRisk>>) Storage.readObjectFromFile(FILE_POSITION_FINISHED);
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
        new PositionManagerTradingBeard().testFuntion();
//        PositionManagerTradingBeard.getInstance();
    }

    public void addOrderByTarget(String symbol, OrderSide side, Double priceEntryTarget) {
        if (symbolHadOrderRunning.containsKey(symbol)) {
            LOG.info("Add order fail because symbol had order active: {} {}", symbol, new Date());
            return;
        }
        OrderInfo orderInfo = new OrderInfo();
        orderInfo.status = OrderStatusProcess.NEW;
        orderInfo.symbol = symbol;
        orderInfo.orderSide = side;
        orderInfo.quantity = ClientSingleton.getInstance().normalizeQuantity(symbol, BUDGET_PER_ORDER * LEVERAGE_ORDER_BEARD / priceEntryTarget);
        orderInfo.leverage = LEVERAGE_ORDER_BEARD;
        orderInfo.timeCreated = System.currentTimeMillis();
        // check position exits
        PositionRisk position = BinanceFuturesClientSingleton.getInstance().getPositionInfo(symbol);
        if (position != null && position.getPositionAmt().doubleValue() != 0) {
            LOG.info("Add order fail because had other position of symbol {} with volume {} {} ", symbol, position.getPositionAmt(), new Date());
            if (!symbolHadOrderRunning.containsKey(symbol)) {
                LOG.info("Add order had position running :{} {} entry: {} quantity:{} {}", side, symbol, orderInfo.priceEntry, orderInfo.quantity, new Date());
                symbolHadOrderRunning.put(symbol, orderInfo);
                startThreadMonitorPositionBySymbol(orderInfo);
            }
            return;
        }
        // check entryTarget if current price > target not sell or current price < target not buy => xu the nguoc
        if (!isPriceOverForTrading(symbol, side, priceEntryTarget)) {
            Order result = OrderHelper.newOrderMarket(orderInfo);
            if (result != null) {
                symbolHadOrderRunning.put(symbol, orderInfo);
                orderInfo.priceEntry = result.getPrice().doubleValue();
                LOG.info("Add order success:{} {} entry: {} stoploss: {} takeprofit:{} quantity:{} {}", side, symbol, orderInfo.priceEntry, orderInfo.priceSL, orderInfo.priceTP, orderInfo.quantity, new Date());
                startThreadMonitorPositionBySymbol(orderInfo);
                counter++;
            } else {
                LOG.info("Add order fail because create order fail: {} {}", symbol, new Date());
            }
        } else {
            LOG.info("Add order fail because price over to trading:{} priceTarget: {} side:{} currentPrice:{} {}", symbol,
                    priceEntryTarget, side, ClientSingleton.getInstance().getCurrentPrice(symbol), new Date());
        }

    }

    private void startThreadMonitorPositionBySymbol(OrderInfo orderInfo) {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadMonitorPositionBySymbol-" + orderInfo.symbol);
            LOG.info("Start thread ThreadMonitorPositionBySymbol: {} !", orderInfo.symbol);
            PositionRisk lastPosition = null;
            while (true) {
                try {
                    PositionRisk position = BinanceFuturesClientSingleton.getInstance().getPositionInfo(orderInfo.symbol);
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
                                lastPosition = position;
                                LOG.info("Change quantity: {} -> {}", orderInfo.quantity, position.getPositionAmt());
                                orderInfo.quantity = Math.abs(position.getPositionAmt().doubleValue());
                                double priceEntry = position.getEntryPrice().doubleValue();
                                orderInfo.priceEntry = priceEntry;
                                Double priceTP;
                                double ratePorfit = 0.005;
                                if (position.getPositionAmt().doubleValue() < 0) {
                                    priceTP = priceEntry - ratePorfit * priceEntry;
                                } else {
                                    priceTP = priceEntry + ratePorfit * priceEntry;
                                }
                                orderInfo.priceTP = priceTP;
                                OrderHelper.takeProfit(orderInfo);
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
//                                    orderInfo.status = OrderStatusProcess.TAKE_PROFIT_DONE;
                                    // sleep 30 to next trading for symbol
                                    symbolHadOrderRunning.remove(orderInfo.symbol);
                                    LOG.info("Remove symbol: {} out list running!", orderInfo.symbol);
                                    String today = Utils.getToDayFileName();
                                    List<PositionRisk> orderSucessByDate = allOrderFnished.get(today);
                                    if (orderSucessByDate == null) {
                                        orderSucessByDate = new ArrayList<>();
                                        allOrderFnished.put(today, orderSucessByDate);
                                    }
                                    orderSucessByDate.add(lastPosition);
                                    Storage.writeObject2File(FILE_POSITION_FINISHED, allOrderFnished);
                                    Storage.writeObject2File(FILE_POSITION_RUNNING, symbolHadOrderRunning);
                                    return;
                                }
                            } else {
                                checkProfitToCloseOrDCA(orderInfo.symbol);
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
                    java.util.logging.Logger.getLogger(PositionManagerTradingBeard.class.getName()).log(Level.SEVERE, null, ex);
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
                    for (Map.Entry<String, List<PositionRisk>> entry : allOrderFnished.entrySet()) {
                        String date = entry.getKey();
                        List<PositionRisk> orders = entry.getValue();
                        StringBuilder builder = new StringBuilder();
                        builder.append("Report auto trade:").append("\n");
                        Double totalMoneySuccess = 0d;
                        for (PositionRisk order : orders) {
                            if (order != null) {
                                totalMoneySuccess += order.getUnrealizedProfit().doubleValue();
                            }
                        }
                        Utils.sendSms2Telegram("Total profit: " + date + " -> " + totalMoneySuccess);
                        LOG.info("Total profit: {} -> {}", date, totalMoneySuccess);
                    }

                    Thread.sleep(30 * Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadReportByTelegram: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }


    private void testFuntion() {
//        checkProfitToClose("OGNUSDT");
        System.out.println(BinanceFuturesClientSingleton.getInstance().getPositionInfo("LINKUSDT"));
//        symbolHadOrderRunning = (ConcurrentHashMap<String, OrderInfo>) Storage.readObjectFromFile(FILE_POSITION_RUNNING);
//        OrderInfo orderInfo = symbolHadOrderRunning.get("LOOMUSDT");
//        OrderHelper.stopLoss(orderInfo);
//checkProfitToCloseOrDCA("BNTUSDT");
//        orderInfo.priceTP = 0.1209;
//        OrderInfo orderInfo = new OrderInfo();
//        orderInfo.status = OrderStatusProcess.NEW;
//        orderInfo.symbol = "ARKUSDT";
//        startThreadMonitorPositionBySymbol(orderInfo);
//        OrderHelper.takeProfit(orderInfo);
//        OrderHelper.stopLoss(orderInfo);
//        for (OrderInfo orderInfo : symbolHadOrderRunning.values()) {
//            System.out.println(Utils.gson.toJson(orderInfo));
//        }
    }

    private boolean waitForPositionDone(String symbol) {
        try {
            int counter = 0;
            for (int i = 0; i < 3; i++) {
                PositionRisk position = BinanceFuturesClientSingleton.getInstance().getPositionInfo(symbol);
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

    private void checkProfitToCloseOrDCA(String symbol) {
        try {
            PositionRisk pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo(symbol);
            if (rateLoss(pos) > 50 && pos.getUnrealizedProfit().doubleValue() < 0) {
                dcaForPosition(pos);
            }
            if (pos.getUnrealizedProfit().doubleValue() >= 3) {
                // check position by hand
                if (Math.abs(pos.getPositionAmt().doubleValue() * pos.getEntryPrice().doubleValue()) > 1000) {
                    LOG.info("Not close because position by hand: {}", pos.getSymbol());
                    Utils.sendSms2Telegram("Not close because position by hand: " + pos.getSymbol());
                    return;
                }
                LOG.info("Close by market: {}", pos);
                Utils.sendSms2Telegram("Close position of: " + symbol + " amt: " + pos.getPositionAmt() + " profit: " + pos.getUnrealizedProfit());
                OrderHelper.takeProfitPosition(pos);
                symbolHadOrderRunning.remove(symbol);
                LOG.info("Remove symbol: {} out list running!", symbol);
                String today = Utils.getToDayFileName();
                List<PositionRisk> orderSucessByDate = allOrderFnished.get(today);
                if (orderSucessByDate == null) {
                    orderSucessByDate = new ArrayList<>();
                    allOrderFnished.put(today, orderSucessByDate);
                }
                orderSucessByDate.add(pos);
                Storage.writeObject2File(FILE_POSITION_FINISHED, allOrderFnished);
                Storage.writeObject2File(FILE_POSITION_RUNNING, symbolHadOrderRunning);
            }
        } catch (Exception e) {
        }
    }

    private int rateLoss(PositionRisk pos) {
        try {
            Double rate = 100 * pos.getUnrealizedProfit().doubleValue() / (pos.getPositionAmt().doubleValue() * pos.getEntryPrice().doubleValue() / pos.getLeverage().doubleValue());
            LOG.info("Check rate loss for:{} {}", pos.getSymbol(), rate);
            return Math.abs(rate.intValue());
        } catch (Exception e) {
        }
        return 0;

    }

    private void dcaForPosition(PositionRisk pos) {
        try {
            LOG.info("DCA for {} {}", pos.getSymbol(), pos.getPositionAmt());
            OrderSide side = OrderSide.BUY;
            if (pos.getPositionAmt().doubleValue() < 0) {
                side = OrderSide.SELL;
            }
//            OrderHelper.dcaForPosition(pos.getSymbol(), side, Math.abs(pos.getPositionAmt().doubleValue()));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private boolean isPriceOverForTrading(String symbol, OrderSide side, Double priceEntryTarget) {
        try {
            Double currentPrice = ClientSingleton.getInstance().getCurrentPrice(symbol);
            if (side.equals(OrderSide.BUY)) {
                if (currentPrice > priceEntryTarget) {
                    return false;
                }
            } else {
                if (currentPrice < priceEntryTarget) {
                    return false;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return true;
    }
}
