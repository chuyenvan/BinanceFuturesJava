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
import com.binance.chuyennd.client.PriceManager;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.statistic24hr.Volume24hrManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderStatus;
import com.binance.client.model.trade.Asset;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class BinanceOrderTradingManager {

    public static final Logger LOG = LoggerFactory.getLogger(BinanceOrderTradingManager.class);
    public ExecutorService executorServiceOrderNew = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    public ExecutorService executorServiceOrderManager = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    public Double RATE_TARGET_VOLUME_MINI = Configs.getDouble("RATE_TARGET_VOLUME_MINI");
    public Double RATE_TARGET_SIGNAL = Configs.getDouble("RATE_TARGET_SIGNAL");
    public Double MAX_CAPITAL_RATE = Configs.getDouble("MAX_CAPITAL_RATE");
    private final ConcurrentHashMap<String, OrderTargetInfo> symbol2Processing = new ConcurrentHashMap<>();
    private final String FILE_STORAGE_ORDER_DONE = "storage/trading/order-volume-success.data";

    public Double balanceStart = 4100.0;
    public Double rateProfit = 0.05;
    public long timeStartRun = 1709683200000L;

    public static void main(String[] args) throws InterruptedException {
        new SignalTradingViewManager().start();
        new VolumeMiniManager().start();
        new BinanceOrderTradingManager().start();
//        new DCAManager().startThreadDca();

//        new VolumeMiniManager().detectBySymbol("BTCUSDT");
//        LOG.info("Done check!");
//        new VolumeMiniManager().fixbug();
//        new VolumeMiniManager().testFunction();
//        new VolumeMiniManager().buildReport();
    }

    private void start() throws InterruptedException {
        initData();
        startThreadListenQueueOrder2Manager();
        startThreadManagerOrder();
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
        List<OrderTargetInfo> allOrderDone = getAllOrderDone();
        int totalBuy = 0;
        int totalSell = 0;
        int totalVolumeMini = 0;
        for (OrderTargetInfo order : allOrderDone) {
            if (order.tradingType.equals(Constants.TRADING_TYPE_VOLUME_MINI)) {
                totalVolumeMini++;
            } else {
                if (order.side.equals(OrderSide.BUY)) {
                    totalBuy++;
                } else {
                    totalSell++;
                }
            }
        }
        Double successTotal = totalBuy * RATE_TARGET_SIGNAL * 100
                + totalSell * RATE_TARGET_SIGNAL * 100
                + totalVolumeMini * RATE_TARGET_VOLUME_MINI * 100;
        reportRunning.append(" Success: ").append(successTotal.longValue()).append("%");
        Double totalBuyDouble = totalBuy * RATE_TARGET_SIGNAL * 100;
        reportRunning.append(" Buy: ").append(totalBuyDouble.longValue()).append("%");
        Double totalSellDouble = totalSell * RATE_TARGET_SIGNAL * 100;
        reportRunning.append(" Sell: ").append(totalSellDouble.longValue()).append("%");
        Double totalVolumeMiniDouble = totalVolumeMini * RATE_TARGET_VOLUME_MINI * 100;
        reportRunning.append("\nVolumeMini: ").append(totalVolumeMiniDouble.longValue()).append("%");
        reportRunning.append(" Running: ").append(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER).size()).append(" orders");
        Utils.sendSms2Telegram(reportRunning.toString());
    }

    public Double calRateLoss(OrderTargetInfo orderInfo, Double lastPrice) {
        double rate = Utils.rateOf2Double(lastPrice, orderInfo.priceEntry);
        if (orderInfo.side.equals(OrderSide.SELL)) {
            rate = -rate;
        }
        return rate;
    }

    public StringBuilder calReportRunning() {
        StringBuilder builder = new StringBuilder();
        Map<String, Double> sym2Volume = TickerFuturesHelper.getAllVolume24hr();
        Map<String, Double> sym2LastPrice = TickerFuturesHelper.getAllLastPrice();
        Set<String> volumeMinis = new HashSet<>();
        Set<String> symbolsSell = new HashSet<>();

        Long totalLoss = 0l;
        Long totalBuy = 0l;
        Long totalSell = 0l;
        Long totalVolumeMini = 0l;
        TreeMap<Double, OrderTargetInfo> rate2Order = new TreeMap<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER)) {
            OrderTargetInfo orderInfo = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol),
                    OrderTargetInfo.class);
            if (orderInfo.tradingType.equals(Constants.TRADING_TYPE_VOLUME_MINI)) {
                volumeMinis.add(symbol);
            }
            Double rateLoss = calRateLoss(orderInfo, sym2LastPrice.get(orderInfo.symbol)) * 10000;
            rate2Order.put(rateLoss, orderInfo);
        }
        int counterLog = 0;
        for (Map.Entry<Double, OrderTargetInfo> entry : rate2Order.entrySet()) {
            Double rateLoss = entry.getKey();
            OrderTargetInfo orderInfo = entry.getValue();
            Long ratePercent = rateLoss.longValue();
            totalLoss += ratePercent;
            if (orderInfo.side.equals(OrderSide.BUY)) {
                totalBuy += ratePercent;
            } else {
                symbolsSell.add(orderInfo.symbol);
                totalSell += ratePercent;
            }
            if (orderInfo.tradingType.equals(Constants.TRADING_TYPE_VOLUME_MINI)) {
                totalVolumeMini += ratePercent;
            }
            if (Math.abs(rateLoss) > 60 && counterLog < 15) {
                counterLog++;

                Double volume24hr = sym2Volume.get(orderInfo.symbol);
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart)).append(" ")
                        .append(orderInfo.side).append(" ")
                        .append(orderInfo.symbol).append(" ")
                        .append(volume24hr.longValue() / 1000000).append("M ")
                        .append(orderInfo.priceEntry).append("->").append(sym2LastPrice.get(orderInfo.symbol))
                        .append(" ").append(ratePercent.doubleValue() / 100).append("%")
                        .append(" - ").append(getUnPNL(orderInfo, sym2LastPrice.get(orderInfo.symbol)))
                        .append("\n");
            }
        }
        Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
        Double balanceTarget = getTargetBalance();
        Double profit = getTargetProfit();

        builder.append("Balance: ").append(umInfo.getMarginBalance().longValue()).append("$ -> ")
                .append(umInfo.getWalletBalance().longValue()).append("$")
                .append(" -> target: ").append(balanceTarget.longValue() * 80 / 100).append(" -> ")
                .append(balanceTarget).append("<b>").append("\nInvest: ")
                .append(BudgetManager.getInstance().getInvesting().longValue()).append("%")
                .append(" rateDump2die: ").append(callRateDump2Die()).append("%").append("</b>")
                .append(" profit: ").append(profit.longValue()).append("\n");
        builder.append("Total: ").append(totalLoss.doubleValue() / 100).append("% -> ")
                .append(umInfo.getCrossUnPnl().longValue()).append("$");
        builder.append(" Buy: ").append(totalBuy.doubleValue() / 100).append("%");
        builder.append(" Sell: ").append(totalSell.doubleValue() / 100).append("%");
        builder.append(" ").append(symbolsSell.toString());
        builder.append("VolumeMini: ").append(totalVolumeMini.doubleValue() / 100).append("%");
        builder.append(" ").append(volumeMinis.toString());
        return builder;
    }

    private void startThreadListenQueueOrder2Manager() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadListenQueueOrder2Manager");
            LOG.info("Start thread ThreadListenQueueOrder2Manager!");
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
                        if (BudgetManager.getInstance().getInvesting() > MAX_CAPITAL_RATE) {
                            LOG.info("Stop trading {} because investing over: {}", order.symbol,
                                    BudgetManager.getInstance().getInvesting());
                            continue;
                        }
                        if (!symbol2Processing.containsKey(order.symbol)) {
                            if (order.status.equals(OrderTargetStatus.REQUEST)) {
                                symbol2Processing.put(order.symbol, order);
                                executorServiceOrderNew.execute(() -> processOrderNewMarket(order));
                            }
                        } else {
                            LOG.info("{} is lock because processing! {}", order.symbol, symbol2Processing.size());
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadListenQueuePosition2Manager {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void processOrderNewMarket(OrderTargetInfo order) {
        if (BudgetManager.getInstance().getBudget() <= 0) {
            LOG.info("Reject symbol {} because budget not avalible!", order.symbol);
            symbol2Processing.remove(order.symbol);
            return;
        }
        try {
            String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol);
            if (!StringUtils.isEmpty(json)) {
                // check order open
                List<Order> openOrders = BinanceFuturesClientSingleton.getInstance().getOpenOrders(order.symbol);
                if (!openOrders.isEmpty()) {
                    LOG.info("Reject because symbol {} have running!", order.symbol);
                    symbol2Processing.remove(order.symbol);
                    return;
                } else {
                    // delete redis
                    RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol);
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_TRADING, order.symbol, String.valueOf(System.currentTimeMillis()));
                    //write file
                    List<String> lines = new ArrayList<>();
                    lines.add(Utils.toJson(order));
                    FileUtils.writeLines(new File(FILE_STORAGE_ORDER_DONE), lines, true);
                }
            }
            // check pos
//            PositionRisk pos = OrderHelper.getPositionBySymbol(order.symbol);
            PositionRisk pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo(order.symbol);
            if (pos != null && pos.getPositionAmt().doubleValue() != 0) {
                LOG.info("Reject because symbol {} have p running!", order.symbol);
                if (StringUtils.isEmpty(json)) {
                    if (pos.getPositionAmt().doubleValue() < 0) {
                        order.side = OrderSide.SELL;
                    } else {
                        order.side = OrderSide.BUY;
                    }
                    order.priceEntry = pos.getEntryPrice().doubleValue();
                    order.quantity = Math.abs(pos.getPositionAmt().doubleValue());
                    // todo -> get order tp = getopenorders => neu ko co tp moi tao tp
                    order.status = OrderTargetStatus.POSITION_RUNNING;
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol, Utils.toJson(order));
//                    createTp(order);
                }

            } else {
                Double volume = Volume24hrManager.getInstance().symbol2Volume.get(order.symbol) / 1000000;
                LOG.info("Create order market {} {} {}", order.side, order.symbol, volume.longValue() + "M");
                Order orderInfo = OrderHelper.newOrderMarket(order.symbol, order.side, order.quantity, BudgetManager.getInstance().getLeverage());
                Utils.sendSms2Telegram(order.side + " " + order.symbol + " entry: " + order.priceEntry + " -> " + order.priceTP
                        + " target: " + Utils.formatPercent(Utils.rateOf2Double(order.priceTP, order.priceEntry))
                        + " quantity: " + order.quantity
                        + " volume: " + volume.longValue() + "M"
                        + " time:" + Utils.normalizeDateYYYYMMDDHHmm(order.timeStart));
                if (orderInfo != null) {
                    order.orderEntry = orderInfo;
                    order.priceEntry = orderInfo.getAvgPrice().doubleValue();
                    order.status = OrderTargetStatus.NEW_HAD_SL3TP_WAIT;
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER,
                            order.symbol, Utils.toJson(order));
                    // create take profit and stoploss
                    createTp(order);
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

    private void processOrderRunning(OrderTargetInfo order) {
        try {
            if (order.status.equals(OrderTargetStatus.NEW_HAD_SL3TP)) {
                try {
//                    Order orderInfo = OrderHelper.readOrderInfo(order.symbol, order.orderTakeProfit.getOrderId());
                    Order orderInfo = BinanceFuturesClientSingleton.getInstance().readOrder(order.symbol, order.orderTakeProfit.getClientOrderId());
                    if (orderInfo != null && !StringUtils.equalsIgnoreCase(orderInfo.getStatus(), OrderStatus.NEW.toString())) {
                        order.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER,
                                order.symbol, Utils.toJson(order));
                    }
                } catch (Exception e) {
                    updateTPInCorrect(order);
                    e.printStackTrace();
                }
            }
            if (order.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                if (order.orderTakeProfit == null) {
                    PositionRisk pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo(order.symbol);
                    if (pos != null && pos.getPositionAmt().doubleValue() != 0) {
                        if (pos.getPositionAmt().doubleValue() < 0) {
                            order.side = OrderSide.SELL;
                        } else {
                            order.side = OrderSide.BUY;
                        }
                        order.priceEntry = pos.getEntryPrice().doubleValue();
                        order.quantity = Math.abs(pos.getPositionAmt().doubleValue());
                        // check sau 10s create moi tao tp tranh tao trung tp voi order new
                        if (System.currentTimeMillis() - order.timeStart > 10 * Utils.TIME_SECOND) {
                            createTp(order);
                        }
                    } else {
                        order.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER,
                                order.symbol, Utils.toJson(order));
                    }
                } else {
                    Order orderInfo = OrderHelper.readOrderInfo(order.symbol, order.orderTakeProfit.getOrderId());
                    if (orderInfo != null && StringUtils.equalsIgnoreCase(orderInfo.getStatus(), OrderStatus.FILLED.toString())) {
                        order.status = OrderTargetStatus.TAKE_PROFIT_DONE;
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol, Utils.toJson(order));
                    }
                }
            }
            if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                    || order.status.equals(OrderTargetStatus.FINISHED)
                    || order.status.equals(OrderTargetStatus.CANCELED)
                    || order.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                // cancel order tp running
                if (order.orderTakeProfit != null) {
                    Order orderInfo = OrderHelper.readOrderInfo(order.symbol, order.orderTakeProfit.getOrderId());
                    if (orderInfo != null && StringUtils.equalsIgnoreCase(orderInfo.getStatus(), OrderStatus.NEW.toString())) {
                        ClientSingleton.getInstance().syncRequestClient.cancelOrder(order.symbol,
                                orderInfo.getOrderId(), orderInfo.getOrderId().toString());
                    }
                }
                // delete redis
                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol);
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_TRADING, order.symbol, String.valueOf(System.currentTimeMillis()));
                //write file
                List<String> lines = new ArrayList<>();
                lines.add(Utils.toJson(order));
                FileUtils.writeLines(new File(FILE_STORAGE_ORDER_DONE), lines, true);
            }
        } catch (Exception e) {
            LOG.info("Error during process order: {}", Utils.toJson(order));
            e.printStackTrace();
        }
        symbol2Processing.remove(order.symbol);

    }

    private void initData() throws InterruptedException {
        ClientSingleton.getInstance();
        PriceManager.getInstance();
    }

    private Double getTargetBalance() {
        Double total = balanceStart;
        Long numberDay = (System.currentTimeMillis() - timeStartRun) / Utils.TIME_DAY;
        for (int i = 0; i < numberDay + 1; i++) {
            Double inc = balanceStart * rateProfit;
            total += inc;
        }
        return total;
    }

    private Double getTargetProfit() {
        Double total = balanceStart;
        Long numberDay = (System.currentTimeMillis() - timeStartRun) / Utils.TIME_DAY;
        for (int i = 0; i < numberDay + 1; i++) {
            Double inc = total * rateProfit;
            total += inc;
        }
        return total * rateProfit;
    }

    private void startThreadManagerOrder() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadManagerOrder");
            LOG.info("Start thread ThreadManagerOrder!");
            while (true) {
                try {
                    for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER)) {
                        OrderTargetInfo order = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(
                                RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol),
                                OrderTargetInfo.class);
                        if (!symbol2Processing.containsKey(order.symbol)) {
                            symbol2Processing.put(order.symbol, order);
                            executorServiceOrderManager.execute(() -> processOrderRunning(order));
                        } else {
                            LOG.info("{} is lock because processing order running! {}", order.symbol, symbol2Processing.size());
                        }
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadManagerOrder: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(60 * Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(BinanceOrderTradingManager.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private void fixbug() {
        String symbol = "RSRUSDT";
        OrderTargetInfo order = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol),
                OrderTargetInfo.class);
//        System.out.println(Utils.toJson(order));
//        order.priceTP = Double.parseDouble(ClientSingleton.formatDouble(order.priceTP));
//        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol, Utils.toJson(order));
//        System.out.println(order.priceTP);

        processOrderRunning(order);
    }

    public void createTp(OrderTargetInfo order) {
        try {
            // check all open order 
            List<Order> openOrders = BinanceFuturesClientSingleton.getInstance().getOpenOrders(order.symbol);
            if (!openOrders.isEmpty()) {
                LOG.info("{} have tp order -> not create tp");
                order.orderTakeProfit = openOrders.get(0);
                order.status = OrderTargetStatus.NEW_HAD_SL3TP;
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER,
                        order.symbol, Utils.toJson(order));
                return;
            }

            // chua co tp -> tao tp
            Double target = RATE_TARGET_SIGNAL;
            if (StringUtils.equals(order.tradingType, Constants.TRADING_TYPE_VOLUME_MINI)) {
                target = RATE_TARGET_VOLUME_MINI;
            }
            OrderSide sideTP = OrderSide.SELL;
            if (order.side.equals(OrderSide.SELL)) {
                sideTP = OrderSide.BUY;
            }
            Double priceTp = Utils.calPriceTarget(order.symbol, order.priceEntry, order.side, target);
            Double currentPrice = ClientSingleton.getInstance().getCurrentPrice(order.symbol);
            for (int i = 1; i < 50; i++) {
                priceTp = Utils.calPriceTarget(order.symbol, order.priceEntry, order.side, target * i);
                if (order.side.equals(OrderSide.BUY) && priceTp > currentPrice) {
                    break;
                }
                if (order.side.equals(OrderSide.SELL) && priceTp < currentPrice) {
                    break;
                }
            }
            String log = "Create tp -> " + sideTP.toString().charAt(0) + " "
                    + order.symbol + " "
                    + order.quantity + " " + order.priceEntry + " -> " + priceTp + " rate: "
                    + Utils.formatPercent(Math.abs(Utils.rateOf2Double(priceTp, order.priceEntry)));
            LOG.info(log);
            Utils.sendSms2Telegram(log);
            Order orderTP = OrderHelper.takeProfit(order.symbol, sideTP, order.quantity, priceTp);
            if (orderTP != null) {
                order.orderTakeProfit = orderTP;
                order.status = OrderTargetStatus.NEW_HAD_SL3TP;
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol, Utils.toJson(order));
            } else {
                order.status = OrderTargetStatus.POSITION_RUNNING;
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, order.symbol, Utils.toJson(order));
            }
            executorServiceOrderManager.execute(() -> recheckOrderTP(order.symbol));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void testFunction() {

        String symbol = "CYBERUSDT";
        OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, 8.283,
                8.325, 7.4, 7, symbol,
                System.currentTimeMillis(), System.currentTimeMillis(),
                OrderSide.BUY, Constants.TRADING_TYPE_SIGNAL);
        processOrderNewMarket(orderTrade);
//        PositionRisk pos = OrderHelper.getPositionBySymbol(symbol);
//        if (pos != null && pos.getPositionAmt().doubleValue() != 0) {
//            createOrderWithPosition(orderTrade, pos);
//        }
    }

    public List<OrderTargetInfo> getAllOrderDone() {
        List<OrderTargetInfo> hashMap = new ArrayList<>();
        try {
            List<String> lines = FileUtils.readLines(new File(FILE_STORAGE_ORDER_DONE));
            for (String line : lines) {
                try {
                    OrderTargetInfo order = Utils.gson.fromJson(line, OrderTargetInfo.class);
                    if (order != null) {
                        hashMap.add(order);
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return hashMap;

    }

    private Double getUnPNL(OrderTargetInfo orderInfo, Double lastPrice) {
        Double pnl = (orderInfo.priceEntry - lastPrice) * orderInfo.quantity * 100;
        Long result = pnl.longValue();
        return result.doubleValue() / 100;
    }

    public void recheckOrderTP(String symbol) {
        try {
            Thread.sleep(10 * Utils.TIME_SECOND);
            String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol);
            if (StringUtils.isNotEmpty(json)) {
                OrderTargetInfo orderInfo = Utils.gson.fromJson(json, OrderTargetInfo.class);
                List<Order> orderOpen = BinanceFuturesClientSingleton.getInstance().getOpenOrders(symbol);
                for (Order order : orderOpen) {
                    if (!Objects.equals(order.getOrderId(), orderInfo.orderTakeProfit.getOrderId())) {
                        Utils.sendSms2Telegram("Cancel order tp duplicate: " + order.getOrderId() + " of " + symbol);
                        LOG.info("Cancel order: " + order.getOrderId() + " of " + symbol);
                        BinanceFuturesClientSingleton.getInstance().cancelOrder(symbol, order.getClientOrderId());
                    }
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public Long callRateDump2Die() {
        Double rate = 100 / BudgetManager.getInstance().getInvesting();
        rate = rate * 100 / BudgetManager.getInstance().getLeverage();
        return rate.longValue();
    }

    private void updateTPInCorrect(OrderTargetInfo order) {
        try {
            List<Order> openOrders = BinanceFuturesClientSingleton.getInstance().getOpenOrders(order.symbol);
            if (!openOrders.isEmpty()) {
                LOG.info("Update order tp for {} {} -> {}", order.symbol,
                        order.orderTakeProfit.getClientOrderId(), openOrders.get(0).getClientOrderId());
                order.orderTakeProfit = openOrders.get(0);
                order.status = OrderTargetStatus.NEW_HAD_SL3TP;
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER,
                        order.symbol, Utils.toJson(order));
                return;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        LOG.info("Update tp order for {} {}", order.symbol, order.orderTakeProfit.getClientOrderId());
    }

}
