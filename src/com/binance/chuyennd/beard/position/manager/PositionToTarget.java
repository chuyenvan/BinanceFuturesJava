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
package com.binance.chuyennd.beard.position.manager;

import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.chuyennd.funcs.OrderHelper;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import java.io.File;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class PositionToTarget {

    public static final Logger LOG = LoggerFactory.getLogger(PositionToTarget.class);
    public ConcurrentHashMap<String, PositionRisk> symbolHadPositionRunning = new ConcurrentHashMap<>();
    public ConcurrentHashMap<String, Double> symbol2BestProfit = new ConcurrentHashMap<>();
    public ConcurrentHashMap<String, List<PositionRisk>> allOrderFnished = new ConcurrentHashMap<>();
    private static volatile PositionToTarget INSTANCE = null;

    public final String FILE_POSITION_RUNNING = "storage/position_target_manager/positionRunning.data";
    public final String FILE_POSITION_FINISHED = "storage/position_target_manager/positionFinished.data";
    public static double RATE_MIN_TAKE_PROFIT;
    public static double RATE_LOSS_TO_DCA;
    public static double RATE_PROFIT_DEC_2CLOSE;
    public static Integer LEVERAGE_TRADING;
    public static Integer BUDGET_PER_ORDER = 10;
    public int counter = 0;

    public static PositionToTarget getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new PositionToTarget();
            INSTANCE.initClient();
        }
        return INSTANCE;
    }

    private void initClient() {
//        ClientSingleton.getInstance();
//        try {
//            Thread.sleep(30000);
//        } catch (InterruptedException ex) {
//            java.util.logging.Logger.getLogger(PositionToTarget.class.getName()).log(Level.SEVERE, null, ex);
//        }
        RATE_MIN_TAKE_PROFIT = Configs.getDouble("TakeProfitRateMinPositionTarget");
        RATE_LOSS_TO_DCA = Configs.getDouble("RateLoss2DCA");//  had * 100
        RATE_PROFIT_DEC_2CLOSE = Configs.getDouble("ProfitDec2Close");//  had * 100
        RATE_PROFIT_DEC_2CLOSE = Configs.getDouble("LeverageTrading");//  default 10

        if (new File(FILE_POSITION_RUNNING).exists()) {
            symbolHadPositionRunning = (ConcurrentHashMap<String, PositionRisk>) Storage.readObjectFromFile(FILE_POSITION_RUNNING);
        } else {
            symbolHadPositionRunning = new ConcurrentHashMap<>();
        }
        if (new File(FILE_POSITION_FINISHED).exists()) {
            allOrderFnished = (ConcurrentHashMap<String, List<PositionRisk>>) Storage.readObjectFromFile(FILE_POSITION_FINISHED);
        } else {
            allOrderFnished = new ConcurrentHashMap<>();
        }
        // start thread monitor symbol running
        for (PositionRisk pos : symbolHadPositionRunning.values()) {
            startThreadMonitorPositionBySymbol(pos.getSymbol());
        }
        startThreadGetPosition2Manager();
        startThreadReport();
    }

    public static void main(String[] args) {
//        new PositionToTarget().testFuntion();
        new PositionToTarget().initClient();
    }

    private void startThreadMonitorPositionBySymbol(String symbol) {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadMonitorPositionBySymbol-" + symbol);
            LOG.info("Start thread ThreadMonitorPositionBySymbol: {} !", symbol);
            PositionRisk lastPosition = null;
            while (true) {
                try {
                    PositionRisk position = getPositionBySymbol(symbol);
                    // if order new -> waiting for position active
                    // if order running -> create SL and TP if have position
                    // else check no position -> check price update order info and remove list active
//                    LOG.info("Checking position for {} {}", symbol, position.getPositionAmt());
                    if (position.getPositionAmt().doubleValue() != 0) {
                        checkProfitToCloseOrDCA(symbol);
                    } else {
                        if (waitForPositionDone(symbol)) {
                            Double lastPrice = ClientSingleton.getInstance().getCurrentPrice(symbol);
                            if (lastPrice != null) {
//                                    orderInfo.status = OrderStatusProcess.TAKE_PROFIT_DONE;
                                // sleep 30 to next trading for symbol
                                symbolHadPositionRunning.remove(symbol);
                                LOG.info("Remove symbol: {} out list running!", symbol);
                                String today = Utils.getToDayFileName();
                                List<PositionRisk> orderSucessByDate = allOrderFnished.get(today);
                                if (orderSucessByDate == null) {
                                    orderSucessByDate = new ArrayList<>();
                                    allOrderFnished.put(today, orderSucessByDate);
                                }
                                orderSucessByDate.add(lastPosition);
                                Storage.writeObject2File(FILE_POSITION_FINISHED, allOrderFnished);
                                Storage.writeObject2File(FILE_POSITION_RUNNING, symbolHadPositionRunning);
                                return;
                            }
                        }
                    }

                } catch (Exception e) {
                    LOG.error("ERROR during ThreadMonitorPositionBySymbol: {} {}", symbol, e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(30 * Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(PositionToTarget.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }
        ).start();
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
                        Double totalMoneySuccess = 0d;
                        for (PositionRisk order : orders) {
                            if (order != null) {
                                totalMoneySuccess += order.getUnrealizedProfit().doubleValue();
                            }
                        }
                        Utils.sendSms2Telegram("Total profit position target: " + date + " -> " + Utils.normalPrice2Api(totalMoneySuccess));
                        LOG.info("Total profit position target: {} -> {}", date, totalMoneySuccess);
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
//        checkProfitToClose("OGNUSDT");
//        System.out.println(getAllSymbol());
//        System.out.println(getPositionBySymbol("TRUUSDT"));
        System.out.println(rateLoss(getPositionBySymbol("INJUSDT")));
//        dcaForPosition(getPositionBySymbol("BNTUSDT"));
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
            int counterPos = 0;
            for (int i = 0; i < 3; i++) {
                PositionRisk position = getPositionBySymbol(symbol);
                if (position.getPositionAmt().doubleValue() == 0) {
                    counterPos++;
                }
                Thread.sleep(Utils.TIME_MINUTE);
            }
            if (counterPos == 3) {
                return true;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    private boolean waitForPositionOpen(String symbol) {
        try {
            for (int i = 0; i < 3; i++) {
                PositionRisk position = getPositionBySymbol(symbol);
                if (position.getPositionAmt().doubleValue() != 0) {
                    return true;
                }
                Thread.sleep(Utils.TIME_MINUTE);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    private void checkProfitToCloseOrDCA(String symbol) {
        try {
            Double bestProfit = symbol2BestProfit.get(symbol);
            if (bestProfit == null) {
                bestProfit = 0d;
            }
            PositionRisk pos = getPositionBySymbol(symbol);
            if (rateLoss(pos) > RATE_LOSS_TO_DCA) {
                dcaForPosition(pos);
            }
            Double currentRateProfit = rateProfit(pos);
            LOG.info("Checking position of: {} current profit: {} bestProfit: {} ", symbol, currentRateProfit, bestProfit);
            if (currentRateProfit >= RATE_MIN_TAKE_PROFIT) {
                if (currentRateProfit > bestProfit) {
                    String log = "Update best profit: " + symbol + " " + bestProfit + " -> " + currentRateProfit;
                    LOG.info(log);
                    Utils.sendSms2Telegram(log);
                    bestProfit = currentRateProfit;
                    symbol2BestProfit.put(symbol, bestProfit);
                } else {
                    if (100 * (bestProfit - currentRateProfit) / bestProfit >= RATE_PROFIT_DEC_2CLOSE) {
                        LOG.info("Close by market: {}", pos);
                        Utils.sendSms2Telegram("Close position of: " + symbol + " amt: " + pos.getPositionAmt()
                                + " profit: " + pos.getUnrealizedProfit() + " Rate: " + bestProfit + "->" + currentRateProfit);
                        OrderHelper.takeProfitPosition(pos);
                        symbolHadPositionRunning.remove(symbol);
                        LOG.info("Remove symbol: {} out list running profit change from {} {}!", symbol, bestProfit, currentRateProfit);
                        String today = Utils.getToDayFileName();
                        List<PositionRisk> orderSucessByDate = allOrderFnished.get(today);
                        if (orderSucessByDate == null) {
                            orderSucessByDate = new ArrayList<>();
                            allOrderFnished.put(today, orderSucessByDate);
                        }
                        orderSucessByDate.add(pos);
                        Storage.writeObject2File(FILE_POSITION_FINISHED, allOrderFnished);
                        Storage.writeObject2File(FILE_POSITION_RUNNING, symbolHadPositionRunning);
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private int rateLoss(PositionRisk pos) {
        try {
            if (pos.getUnrealizedProfit().doubleValue() > 0) {
                return 0;
            }
            Double rate = pos.getUnrealizedProfit().doubleValue() / marginOfPosition(pos);
            rate = Double.valueOf(Utils.formatPercent(rate));
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
            OrderHelper.dcaForPosition(pos.getSymbol(), side, Math.abs(pos.getPositionAmt().doubleValue()), LEVERAGE_TRADING);
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

    private Double rateProfit(PositionRisk pos) {
        double rate = 0;
        if (pos.getUnrealizedProfit().doubleValue() > 0) {
            rate = pos.getUnrealizedProfit().doubleValue() / marginOfPosition(pos);
            rate = Double.parseDouble(Utils.formatPercent(rate));
        }
        return rate;
    }

    private double marginOfPosition(PositionRisk pos) {
        return Math.abs((pos.getPositionAmt().doubleValue() * pos.getEntryPrice().doubleValue() / pos.getLeverage().doubleValue()));
    }

    private void startThreadGetPosition2Manager() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadGetPosition2Manager");
            LOG.info("Start thread ThreadGetPosition2Manager!");
            Set<String> allSymbol = new HashSet<String>();
            while (true) {
                try {
                    if (allSymbol.isEmpty()) {
                        allSymbol.addAll(getAllSymbol());
                    }
                    for (String symbol : allSymbol) {
                        try {
                            if (symbolHadPositionRunning.containsKey(symbol)) {
                                continue;
                            }
                            PositionRisk pos = getPositionBySymbol(symbol);
                            if (pos.getPositionAmt().doubleValue() != 0) {
                                symbolHadPositionRunning.put(symbol, pos);
                                Double bestProfit = 0d;
                                symbol2BestProfit.put(symbol, bestProfit);
                                startThreadMonitorPositionBySymbol(symbol);
                            }
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                    Storage.writeObject2File(FILE_POSITION_RUNNING, symbolHadPositionRunning);
                    Thread.sleep(10 * Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during : {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private Collection<? extends String> getAllSymbol() {
        Set<String> results = new HashSet<>();
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                results.add(ticker.getSymbol());
            }
        }
        return results;
    }

    public void addOrderByTarget(String symbol, OrderSide orderSide, Double priceEntryTarget) {
        if (symbolHadPositionRunning.containsKey(symbol)) {
            LOG.info("Add order fail because symbol had order active: {} {}", symbol, new Date());
            return;
        }
        PositionRisk position = getPositionBySymbol(symbol);
        if (position != null && position.getPositionAmt().doubleValue() != 0) {
            LOG.info("Add order fail because had other position of symbol {} with volume {} {} ", symbol, position.getPositionAmt(), new Date());
            return;
        }
        if (!isPriceOverForTrading(symbol, orderSide, priceEntryTarget)) {
            Double quantity = Double.valueOf(Utils.normalQuantity2Api(BUDGET_PER_ORDER * LEVERAGE_TRADING / priceEntryTarget));
            Order result = OrderHelper.newOrderMarket(symbol, orderSide, quantity, LEVERAGE_TRADING);
            if (result != null) {
                PositionRisk pos = getPositionBySymbol(symbol);
                symbolHadPositionRunning.put(symbol, pos);
                Double bestProfit = 0d;
                symbol2BestProfit.put(symbol, bestProfit);
                startThreadMonitorPositionBySymbol(symbol);
                LOG.info("Add order success:{} {} entry: {} quantity:{} {}", orderSide, symbol, pos.getEntryPrice().doubleValue(), pos.getPositionAmt().doubleValue(), new Date());

            }

        }
    }

}
