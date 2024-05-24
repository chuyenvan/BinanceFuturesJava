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

import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.FuturesRules;
import com.binance.chuyennd.client.OrderHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.statistic24hr.Volume24hrManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderType;
import com.binance.client.model.trade.Asset;
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
import java.util.logging.Level;

/**
 * @author pc
 */
public class BinanceOrderTradingManager {

    public static final Logger LOG = LoggerFactory.getLogger(BinanceOrderTradingManager.class);
    public ExecutorService executorServiceOrderNew = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    public ExecutorService executorServiceOrderManager = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    public Double RATE_TARGET = Configs.getDouble("RATE_TARGET");

    public final Double NUMBER_HOURS_STOP_TRADE = Configs.getDouble("NUMBER_HOURS_STOP_TRADE");
    private final ConcurrentHashMap<String, OrderTargetInfo> symbol2Processing = new ConcurrentHashMap<>();

    public static Double balanceStart = Configs.getDouble("CAPITAL_START");//9200.0;
    public static Double rateProfit = Configs.getDouble("PROFIT_RATE");//0.013;
    public static long timeStartRun = Configs.getLong("TIME_START");//1710892800000L;

    public static void main(String[] args) throws InterruptedException, ParseException {
        new VolumeMiniManager().start();
        new BinanceOrderTradingManager().start();
    }

    private void start() throws InterruptedException {
        initData();
        startThreadListenQueueOrder2ManagerNew();
        startThreadManagerOrderNew();
        reportPosition();
    }

    private void reportPosition() {
        new Thread(() -> {
            Thread.currentThread().setName("Reporter");
            LOG.info("Start thread report !");
            while (true) {
                try {
                    Thread.sleep(30 * Utils.TIME_SECOND);
                    if (isTimeReport()) {
                        buildReport();
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during : {}", e);
                    e.printStackTrace();
                }
            }
        }).start();

    }

    public boolean isTimeReport() {
        return Utils.getCurrentMinute() % 15 == 1 && Utils.getCurrentSecond() < 30;
    }

    public void buildReport() {
        StringBuilder reportRunning = calReportRunning();
        Utils.sendSms2Telegram(reportRunning.toString());
    }

    public StringBuilder calReportRunning() {
        StringBuilder builder = new StringBuilder();
        Set<String> symbolsSell = new HashSet<>();

        Long totalLoss = 0l;
        Long totalBuy = 0l;
        Long totalSell = 0l;
        Long totalUnder3 = 0l;
        Long totalOver10 = 0l;

        TreeMap<Double, PositionRisk> rate2Order = new TreeMap<>();
        List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
        for (PositionRisk position : positions) {
            if (position.getPositionAmt() != null && position.getPositionAmt().doubleValue() != 0) {
                Double rateLoss = Utils.rateOf2Double(position.getMarkPrice().doubleValue(), position.getEntryPrice().doubleValue()) * 100;
                rate2Order.put(rateLoss, position);
                if (rateLoss < -10) {
                    totalOver10++;
                }
                if (rateLoss >= -3) {
                    totalUnder3++;
                }
            }
        }
        int counterLog = 0;
        for (Map.Entry<Double, PositionRisk> entry : rate2Order.entrySet()) {
            Double rateLoss = entry.getKey();
            PositionRisk pos = entry.getValue();
            Long ratePercent = rateLoss.longValue();
            totalLoss += ratePercent;
            if (pos.getPositionAmt().doubleValue() > 0) {
                totalBuy += ratePercent;
            } else {
                symbolsSell.add(pos.getSymbol());
                totalSell += ratePercent;
            }
            if (counterLog < 15) {
                counterLog++;
                Double volume24hr = Volume24hrManager.getInstance().symbol2Volume.get(pos.getSymbol());
                OrderSide side = OrderSide.BUY;
                if (pos.getPositionAmt().doubleValue() < 0) {
                    side = OrderSide.SELL;
                }
                Double pnl = Utils.callPnl(pos) * 100;
                Long pnlLong = pnl.longValue();
                Double entryPrice = ClientSingleton.getInstance().normalizePrice(pos.getSymbol(), pos.getEntryPrice().doubleValue());
                Double lastPrice = ClientSingleton.getInstance().normalizePrice(pos.getSymbol(), pos.getMarkPrice().doubleValue());
                builder.append(side).append(" ")
                        .append(pos.getSymbol()).append(" ")
                        .append(volume24hr.longValue() / 1000000).append("M ")
                        .append(entryPrice).append("->").append(lastPrice)
                        .append(" ").append(ratePercent).append("%")
                        .append(" ").append(pnlLong.doubleValue() / 100).append("$")
                        .append("\n");
            }
        }
        Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
        Double balanceTarget = getTargetBalance(System.currentTimeMillis() + Utils.TIME_DAY);
        Double profit = balanceTarget - umInfo.getWalletBalance().doubleValue();

        builder.append("Balance: ").append(umInfo.getMarginBalance().longValue()).append("$ -> ")
                .append(umInfo.getWalletBalance().longValue())
                .append("/").append(balanceTarget.longValue()).append("$")
                .append(" profit: ").append(profit.longValue()).append("");
        builder.append("\nTotal: ").append(totalLoss.doubleValue()).append("% -> ")
                .append(umInfo.getCrossUnPnl().longValue()).append("$");
        builder.append(" Buy: ").append(totalBuy.doubleValue()).append("%");
        builder.append(" Sell: ").append(totalSell.doubleValue()).append("%");
        builder.append(" ").append(symbolsSell.toString());
        builder.append(" \nRunning: ").append(RedisHelper.getInstance().smembers(
                RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING).size()).append(" orders");
        builder.append(" Under3: ").append(totalUnder3);
        builder.append(" Over10: ").append(totalOver10);
        return builder;
    }

    private void startThreadListenQueueOrder2ManagerNew() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadListenQueueOrder2ManagerNew");
            LOG.info("Start thread ThreadListenQueueOrder2ManagerNew!");
            while (true) {
                List<String> data;
                try {
                    data = RedisHelper.getInstance().get().blpop(0, RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE);
                    String orderJson = data.get(1);
                    try {
                        OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
                        LOG.info("Queue listen order to manager order received : {} ", order.symbol);
                        if (FuturesRules.getInstance().getSymsLocked().contains(order.symbol)) {
                            LOG.info("Sym {} is locking by trading rule!", order.symbol);
                            continue;
                        }
//                        if (BudgetManager.getInstance().getNumberOrderBudgetAvailable() <= 0) {
                        if (BudgetManager.getInstance().getInvesting2Check() >= BudgetManager.getInstance().MAX_CAPITAL_RATE) {
                            LOG.info("Stop trading {} {} because investing over: {}", order.symbol,
                                    Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                                    BudgetManager.getInstance().getInvesting());
                            continue;
                        }
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
        if (FuturesRules.getInstance().getSymsLocked().contains(order.symbol)) {
            LOG.info("Sym {} is locking by trading rule!", order.symbol);
            return;
        }
        if (BudgetManager.getInstance().getBudget() <= 0) {
            LOG.info("Reject symbol {} because budget not avalible!", order.symbol);
            symbol2Processing.remove(order.symbol);
            return;
        }
        try {
            // check pos
            PositionRisk pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo(order.symbol);
            if (pos != null && pos.getPositionAmt().doubleValue() != 0) {
                LOG.info("Reject because symbol {} have position running!", order.symbol);
                RedisHelper.getInstance().addList(RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING, order.symbol);
                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_CHECKING, order.symbol);
            } else {
                Double volume = 0d;
                if (Volume24hrManager.getInstance().symbol2Volume.get(order.symbol) != null) {
                    volume = Volume24hrManager.getInstance().symbol2Volume.get(order.symbol) / 1000000;
                }
                LOG.info("Create order market {} {} {}", order.side, order.symbol, volume.longValue() + "M");
                Order orderInfo = OrderHelper.newOrderMarket(order.symbol, order.side, order.quantity, BudgetManager.getInstance().getLeverage());
                Utils.sendSms2Telegram(order.side + " " + order.symbol + " entry: " + order.priceEntry + " -> " + order.priceTP
                        + " target: " + Utils.formatPercent(Utils.rateOf2Double(order.priceTP, order.priceEntry))
                        + " quantity: " + order.quantity
                        + " volume: " + volume.longValue() + "M"
                        + " time:" + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart));
                if (orderInfo != null) {
                    // create take profit and stoploss
                    RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_CHECKING, order.symbol);
                    pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo(order.symbol);
                    if (pos != null && pos.getPositionAmt().doubleValue() != 0) {
                        createTp(pos);
                    }
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

    public static Double getTargetBalance(Long currentTime) {
        Double total = balanceStart;
        Long numberDay = (currentTime - timeStartRun) / Utils.TIME_DAY;
        for (int i = 0; i < numberDay; i++) {
            Double inc = total * rateProfit;
            total += inc;
        }
        return total;
    }

    private void startThreadManagerOrderNew() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadManagerOrderNew");
            LOG.info("Start thread ThreadManagerOrderNew");
            while (true) {
                executorServiceOrderManager.execute(() -> processManagerPosition());
                try {
                    Thread.sleep(3 * Utils.TIME_MINUTE);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(BinanceOrderTradingManager.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    public void processManagerPosition() {
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
            // udpate list running
            Set<String> symbolsRunning = RedisHelper.getInstance().smembers(RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING);
            for (PositionRisk position : positions) {
                if (position.getPositionAmt().doubleValue() > 0) {
                    symbol2Pos.put(position.getSymbol(), position);
                    if (!symbolsRunning.contains(position.getSymbol())) {
                        RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_CHECKING, position.getSymbol());
                        RedisHelper.getInstance().addList(RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING, position.getSymbol());
                    }
                    // check and Close position
                    if (position.getUpdateTime() < System.currentTimeMillis() - Utils.TIME_HOUR * NUMBER_HOURS_STOP_TRADE) {
                        stopLossOrder(position);
                    }
                }
            }

            Map<String, Order> symbol2OrderTp = new HashMap<>();
            for (Order order : ordersOpen) {
                // pass order not tp
                if (!StringUtils.equals(order.getType(), OrderType.TAKE_PROFIT.toString())
                        && !StringUtils.equals(order.getType(), OrderType.TAKE_PROFIT_MARKET.toString())) {
                    continue;
                }
                PositionRisk pos = symbol2Pos.get(order.getSymbol());
                if (pos != null
                        && pos.getPositionAmt().doubleValue() == order.getOrigQty().doubleValue()) {
                    if (symbol2OrderTp.containsKey(order.getSymbol())) {
                        recheckOrderTPNew(order.getSymbol());
                    }
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
            for (String symbol : symbolsRunning) {
                if (!symbol2Pos.containsKey(symbol)) {
                    RedisHelper.getInstance().removeList(RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING, symbol);
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_CHECKING, symbol,
                            String.valueOf(System.currentTimeMillis()));
                }
            }
            // process position not tp or tp fail
            for (Map.Entry<String, PositionRisk> entry : symbol2Pos.entrySet()) {
                String symbol = entry.getKey();
                PositionRisk pos = entry.getValue();
                Order orderTp = symbol2OrderTp.get(symbol);
                if (orderTp == null && (System.currentTimeMillis() - pos.getUpdateTime()) > 5 * Utils.TIME_SECOND) {
                    createTp(pos);
                }
            }
        } catch (Exception e) {
            LOG.error("ERROR during ThreadManagerOrderNew: {}", e);
            e.printStackTrace();
        }
        Long timeProcess = (System.currentTimeMillis() - startTime) * 10 / Utils.TIME_SECOND;
        LOG.info("Final check all position: {}s", timeProcess.doubleValue() / 10);
    }

    private void stopLossOrder(PositionRisk position) {
        OrderHelper.takeProfitPosition(position);
    }

    public void createTp(PositionRisk pos) {
        try {
            // check all open order 
//            Double target = BudgetManager.getInstance().callRateTargetWithPosition(pos,RATE_TARGET_SIGNAL);
            Double target = RATE_TARGET;
            Double priceTp = Utils.calPriceTarget(pos.getSymbol(), pos.getEntryPrice().doubleValue(), OrderSide.BUY, target);
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
            for (int i = 1; i < 50; i++) {
                priceTp = Utils.calPriceTarget(pos.getSymbol(), pos.getEntryPrice().doubleValue(), OrderSide.BUY, target * i);
                if (priceTp > currentPrice) {
                    break;
                }

            }
            String log = "Create tp -> SELL "
                    + pos.getSymbol() + " " + pos.getPositionAmt().doubleValue() + " " + pos.getEntryPrice().doubleValue() + " -> " + priceTp + " rate: "
                    + Utils.formatPercent(Math.abs(Utils.rateOf2Double(priceTp, pos.getEntryPrice().doubleValue())));
            LOG.info(log);
            Utils.sendSms2Telegram(log);
            OrderHelper.takeProfit(pos.getSymbol(), OrderSide.SELL, pos.getPositionAmt().doubleValue(), priceTp);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void recheckOrderTPNew(String symbol) {
        try {
            LOG.info("Recheck tp for {}", symbol);
            List<Order> orderOpen = BinanceFuturesClientSingleton.getInstance().getOpenOrders(symbol);
            if (orderOpen.size() > 1) {
                Order orderOpenMaxTime = null;
                for (int i = 0; i < orderOpen.size(); i++) {
                    Order order = orderOpen.get(i);
                    if (orderOpenMaxTime == null) {
                        orderOpenMaxTime = order;
                        continue;
                    } else {
                        if (order.getUpdateTime() > orderOpenMaxTime.getUpdateTime()) {
                            Utils.sendSms2Telegram("Cancel order tp duplicate: " + orderOpenMaxTime.getOrderId()
                                    + " of " + symbol + " price:" + orderOpenMaxTime.getPrice().doubleValue()
                                    + Utils.normalizeDateYYYYMMDDHHmm(orderOpenMaxTime.getUpdateTime()));
                            LOG.info("Cancel order: " + orderOpenMaxTime.getOrderId() + " of " + symbol);
                            BinanceFuturesClientSingleton.getInstance().cancelOrder(symbol, orderOpenMaxTime.getClientOrderId());
                            orderOpenMaxTime = order;
                        } else {
                            Utils.sendSms2Telegram("Cancel order tp duplicate: " + order.getOrderId()
                                    + " of " + symbol + " price:" + order.getPrice().doubleValue()
                                    + Utils.normalizeDateYYYYMMDDHHmm(order.getUpdateTime()));
                            LOG.info("Cancel order: " + order.getOrderId() + " of " + symbol);
                            BinanceFuturesClientSingleton.getInstance().cancelOrder(symbol, order.getClientOrderId());
                        }
                    }

                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

}
