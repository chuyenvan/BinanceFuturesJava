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
package com.binance.chuyennd.position.manager;

import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.chuyennd.funcs.OrderHelper;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.SubscriptionErrorHandler;
import com.binance.client.exception.BinanceApiException;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderStatus;
import com.binance.client.model.event.SymbolTickerEvent;
import com.binance.client.model.trade.AccountBalance;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import java.math.BigDecimal;
import java.util.Collection;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentSkipListSet;
import java.util.logging.Level;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class PositionToTargetMonitor {

    public static final Logger LOG = LoggerFactory.getLogger(PositionToTargetMonitor.class);

    public final String FILE_POSITION_FINISHED = "storage/position_target_manager/positionFinished.data";
    public final Map<String, Double> day2Balance = new HashMap<>();
    public final ConcurrentHashMap<String, PositionRisk> positionDones = new ConcurrentHashMap<>();
    public ConcurrentSkipListSet<String> symbolNotUpdate = new ConcurrentSkipListSet<>();
    public static double RATE_MIN_TAKE_PROFIT = Configs.getDouble("TakeProfitRateMinPositionTarget");
    public static double RATE_MAX_TAKE_PROFIT = Configs.getDouble("TakeProfitRateMaxPositionTarget");
    public static double RATE_DCA_ORDER = Configs.getDouble("RateDcaOrder");//  had * 100
    public static double RATE_LOSS_TO_DCA = Configs.getDouble("RateLoss2DCA");
    public static double RATE_PROFIT_DEC_2CLOSE = Configs.getDouble("ProfitDec2Close");//  had * 100       
    public static double LIMIT_TIME_POSITION_2CLOSE = Configs.getDouble("LimitTimePosition2Close"); //minute

    private void initAndStart() {
        ClientSingleton.getInstance();
        try {
            Thread.sleep(5000);
        } catch (InterruptedException ex) {
            java.util.logging.Logger.getLogger(PositionToTargetMonitor.class.getName()).log(Level.SEVERE, null, ex);
        }

        // init trend with btc
        new BTCInfoManager().startThreadUpdateTrend();

        // start thread monitor symbol running
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER)) {
            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol, Utils.toJson(getPositionBySymbol(symbol)));
        }
        threadListenPrice();
        startThreadMonitorAllPosition();
        startThreadMonitorOrderDCA();
        startThreadGetPosition2Manager();
        startThreadCheckPositionDone();
        startThreadListenQueuePosition2Manager();
        startThreadReport();
        startThreadUpdatePosition();
    }

    public static void main(String[] args) {
        new PositionToTargetMonitor().initAndStart();

//        new PositionToTargetMonitor().checkProfitToCloseOrStopLoss(PositionHelper.getPositionBySymbol("BIGTIMEUSDT"));
//        System.out.println(new PositionToTargetMonitor().getAllSymbol());
    }

    private void startThreadMonitorAllPosition() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadMonitorAllPosition");
            LOG.info("Start thread {} !", Thread.currentThread().getName());
            while (true) {
                startThreadProcessAllPosition();
                try {
                    Thread.sleep(Utils.TIME_MINUTE / 2);
                } catch (Exception ex) {
                    ex.printStackTrace();
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
                    List<AccountBalance> balanceInfos = ClientSingleton.getInstance().syncRequestClient.getBalance();
                    for (AccountBalance balanceInfo : balanceInfos) {
                        if (StringUtils.equalsIgnoreCase(balanceInfo.getAsset(), "usdt")) {
                            String today = Utils.getToDayFileName();
                            double balance = balanceInfo.getBalance().doubleValue();
                            day2Balance.put(today, balance);
                            String yesterday = Utils.normalizeDateYYYYMMDD(new Date(System.currentTimeMillis() - Utils.TIME_DAY));
                            String log = "Balance: " + day2Balance.get(today);
                            if (day2Balance.get(yesterday) != null) {
                                log = "Balance: " + day2Balance.get(yesterday) + " -> " + day2Balance.get(today);
                            }
                            Utils.sendSms2Telegram(log);
                        }
                    }
                    Thread.sleep(120 * Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadReportByTelegram: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void startThreadUpdatePosition() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdatePosition");
            LOG.info("Start thread ThreadUpdatePosition!");
            while (true) {
                try {
                    startThreadUpdatePositionSingle();
                    Thread.sleep(1 * Utils.TIME_MINUTE);
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

    private boolean waitForPositionDone(String symbol) {
        try {
            int counterPos = 0;
            for (int i = 0; i < 3; i++) {
                PositionRisk position = getPositionBySymbol(symbol);
                if (position.getPositionAmt().doubleValue() == 0) {
                    counterPos++;
                }
                Thread.sleep(30 * Utils.TIME_SECOND);
            }
            if (counterPos == 3) {
                return true;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    private boolean checkProfitToCloseOrStopLoss(PositionRisk pos) {
        try {
            Double bestProfit;
            if (RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_PROFIT_MANAGER, pos.getSymbol()) == null) {
                bestProfit = 0d;
            } else {
                bestProfit = Double.valueOf(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_PROFIT_MANAGER, pos.getSymbol()));
            }
            // check and dca
            int rateLoss = rateLoss(pos);
            Order orderRedis = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER, pos.getSymbol()), Order.class);
            if (rateLoss >= RATE_DCA_ORDER
                    && orderRedis == null
                    && ClientSingleton.getInstance().getBalanceAvalible() > Utils.marginOfPosition(pos)) {
//                Order orderDCA = PositionHelper.getInstance().dcaForPosition(pos, RATE_DCA_ORDER / 100);
                Order orderDCA = PositionHelper.getInstance().dcaForPositionNew(pos);
                if (orderDCA != null) {
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER, pos.getSymbol(), Utils.toJson(orderDCA));
                }
            }

            Double currentRateProfit = rateProfit(pos);
            OrderSide side = OrderSide.BUY;
            if (pos.getPositionAmt().doubleValue() < 0) {
                side = OrderSide.SELL;
            }
            LOG.info("Checking position of:{} {} current profit: {} bestProfit: {} ", side.toString(), pos.getSymbol(), currentRateProfit, bestProfit);
            if (currentRateProfit / pos.getLeverage().doubleValue() >= RATE_MIN_TAKE_PROFIT) {
                if (currentRateProfit > bestProfit) {
                    String log = "Update best profit: " + pos.getSymbol() + " " + bestProfit + " -> " + currentRateProfit;
                    LOG.info(log);
                    Utils.sendSms2Telegram(log);
                    bestProfit = currentRateProfit;
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_TIME_MANAGER, pos.getSymbol(), String.valueOf(System.currentTimeMillis()));
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_PROFIT_MANAGER, pos.getSymbol(), bestProfit.toString());
                } else {
                    // close with max profit
                    boolean isCloseMax = false;
                    boolean isCloseWithLost = false;
                    if (currentRateProfit / pos.getLeverage().doubleValue() > RATE_MAX_TAKE_PROFIT) {
                        isCloseMax = true;
                    }
                    double currentLossProfit = (bestProfit - currentRateProfit) / pos.getLeverage().doubleValue();
                    boolean isTimeOverLimit = checkTimeProfitAndTime(currentRateProfit, pos.getSymbol());
                    if ((currentLossProfit >= RATE_PROFIT_DEC_2CLOSE && isTimeOverLimit)
                            || (currentRateProfit < 2 * RATE_MIN_TAKE_PROFIT && isTimeOverLimit)) {
                        isCloseWithLost = true;
                    }
                    if (isCloseMax || isCloseWithLost) {
                        LOG.info("Close by market: {}", pos);
                        String log = "Close position of: " + pos.getSymbol() + " amt: " + pos.getPositionAmt()
                                + " profit: " + " isMax: " + isCloseMax + " isCloseWithLoss: " + isCloseWithLost + " profit: "
                                + pos.getUnrealizedProfit() + " Rate: " + bestProfit + "->" + currentRateProfit
                                + " rateloss:" + currentLossProfit + " timeout: " + isTimeOverLimit + " leverage: " + pos.getLeverage().intValue();
                        LOG.info(log);
                        Utils.sendSms2Telegram(log);
                        pos = getPositionBySymbol(pos.getSymbol());
                        if (pos.getUnrealizedProfit().doubleValue() != 0) {
                            OrderHelper.takeProfitPosition(pos);
                        }
                        RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, pos.getSymbol());
                        LOG.info("Remove symbol: {} out list running profit change from {} {}!", pos.getSymbol(), bestProfit, currentRateProfit);
                        return true;
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return false;
    }

    private int rateLoss(PositionRisk pos) {
        try {
            if (pos.getUnrealizedProfit().doubleValue() > 0) {
                return 0;
            }
            Double rate = pos.getUnrealizedProfit().doubleValue() / Utils.marginOfPosition(pos);
            rate = Double.valueOf(Utils.formatPercent(rate));
            return Math.abs(rate.intValue());
        } catch (Exception e) {
        }
        return 0;

    }

    private Double rateProfit(PositionRisk pos) {
        double rate;
        rate = pos.getUnrealizedProfit().doubleValue() / Utils.marginOfPosition(pos);
        rate = Double.parseDouble(Utils.formatPercent(rate));
        return rate;
    }

    private void startThreadGetPosition2Manager() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadGetPosition2Manager");
            LOG.info("Start thread ThreadGetPosition2Manager!");
            Set<String> allSymbol = new HashSet<>();
            while (true) {
                try {
                    LOG.info("Number of threads active: {}", Thread.activeCount());
                    if (allSymbol.isEmpty()) {
                        allSymbol.addAll(getAllSymbol());
                    }
                    for (String symbol : allSymbol) {
                        try {
                            if (RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol) != null) {
                                continue;
                            }
                            PositionRisk pos = getPositionBySymbol(symbol);
                            if (pos.getPositionAmt().doubleValue() != 0) {
                                RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER_QUEUE, symbol);
                            }
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                    Thread.sleep(5 * Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during : {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void startThreadListenQueuePosition2Manager() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadListenQueuePosition2Manager");
            LOG.info("Start thread ThreadListenQueuePosition2Manager!");
            while (true) {
                List<String> data;
                try {
                    data = RedisHelper.getInstance().get().blpop(0, RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER_QUEUE);
                    LOG.info("Queue listen symbol to manager position received : {} ", data.toString());
                    String symbol = data.get(1);
                    try {
                        PositionRisk pos = getPositionBySymbol(symbol);
                        if (pos.getPositionAmt().doubleValue() != 0) {
                            Double bestProfit = 0d;
                            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_PROFIT_MANAGER, pos.getSymbol(), bestProfit.toString());
                            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol, Utils.toJson(pos));
                            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_TIME_MANAGER, symbol, String.valueOf(System.currentTimeMillis()));
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

//    private void startThreadListenPriceAndUpdatePosition(String symbol) {
//        LOG.info("Start listen price: {}", symbol);
//        SubscriptionClient client = SubscriptionClient.create();
//
//        SubscriptionErrorHandler errorHandler = (BinanceApiException exception) -> {
//
////            LOG.info("Error listen -> create new listener: {}", symbol);
////            startThreadListenPriceAndUpdatePosition(symbol);
////            exception.printStackTrace();
//        };
//        client.subscribeSymbolTickerEvent(symbol.toLowerCase(), ((event) -> {
////            LOG.info("Update price: {}", Utils.gson.toJson(event));
//            PositionRisk pos = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(
//                    RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol), PositionRisk.class);
//            pos.setMarkPrice(event.getLastPrice());
//            pos.setUnrealizedProfit(calUnrealizedProfit(pos));
//        }), errorHandler);
//
////        }), null);
//    }
    private BigDecimal calUnrealizedProfit(PositionRisk pos) {
        Double profit;
        profit = pos.getPositionAmt().doubleValue() * (pos.getMarkPrice().doubleValue() - pos.getEntryPrice().doubleValue());
        return new BigDecimal(profit);
    }

    private boolean checkTimeProfitAndTime(double currentRateProfit, String symbol) {
        if (currentRateProfit < 2 * RATE_MIN_TAKE_PROFIT) {
            if (RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_TIME_MANAGER, symbol) == null) {
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_TIME_MANAGER, symbol, String.valueOf(System.currentTimeMillis()));
            }
            Long timePos = Long.valueOf(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_TIME_MANAGER, symbol));
            if ((System.currentTimeMillis() - timePos) > LIMIT_TIME_POSITION_2CLOSE * Utils.TIME_MINUTE) {
                return true;
            }
        }
        return false;
    }

    private void startThreadMonitorOrderDCA() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadMOnitorOrderDCA");
            LOG.info("Start thread ThreadMOnitorOrderDCA!");
            while (true) {
                try {
                    // check position close => cancel order dca if order status new
                    Set<String> symbolsDca = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER);
                    LOG.info("Checking {} orders DCA process!", symbolsDca.size());
                    for (String symbol : symbolsDca) {
                        Order orderDCA = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER, symbol), Order.class);
                        if (RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol) == null) {
                            Order orderDcaInfo = PositionHelper.getInstance().readOrderInfo(symbol, orderDCA.getOrderId());
                            if (orderDcaInfo != null && orderDcaInfo.getStatus().equals(OrderStatus.NEW.toString())) {
                                String log = "Cancel order DCA: " + Utils.toJson(orderDcaInfo);
                                LOG.info(log);
                                Utils.sendSms2Telegram(log);
                                PositionHelper.getInstance().cancelOrder(symbol, orderDCA.getOrderId());
                            }
                            RedisHelper.getInstance().hdel(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER, symbol);
                            LOG.info("Remove order DCA of list monitor when position sucess: {}", symbol);
                        } else {
                            Order orderDcaInfo = PositionHelper.getInstance().readOrderInfo(symbol, orderDCA.getOrderId());
                            if (orderDcaInfo != null && orderDcaInfo.getStatus().equals(OrderStatus.FILLED.toString())) {
                                RedisHelper.getInstance().hdel(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER, symbol);
                                LOG.info("Remove order DCA of list monitor when status filled: {}", symbol);
                            }
                        }
                    }
                    Thread.sleep(5 * Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadMOnitorOrderDCA: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void startThreadCheckPositionDone() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadCheckPositionDone");
            LOG.info("Start thread ThreadCheckPositionDone!");
            while (true) {
                try {
                    Set<String> listDone = new HashSet<>();
                    LOG.info("Check positon done: {}", positionDones.keySet());
                    for (Map.Entry<String, PositionRisk> entry : positionDones.entrySet()) {
                        String symbol = entry.getKey();
                        if (waitForPositionDone(symbol)) {
                            RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol);
                            LOG.info("{} Remove symbol had Close by over margin: {} out list running!", Thread.currentThread().getName(), symbol);
                            listDone.add(symbol);
                        }
                    }
                    for (String symbol : listDone) {
                        positionDones.remove(symbol);
                    }
                    Thread.sleep(Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadCheckPositionDone: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void threadListenPrice() {
        startThreadMonitorUpdatePirce();
        SubscriptionClient client = SubscriptionClient.create();
        SubscriptionErrorHandler errorHandler = (BinanceApiException exception) -> {
        };
        client.subscribeAllTickerEvent(((event) -> {
            updatePriceFromEventAllTicker(event);
        }), errorHandler);
    }

    private void updatePriceFromEventAllTicker(List<SymbolTickerEvent> events) {
        StringBuilder builder = new StringBuilder();
        builder.setLength(0);
        for (SymbolTickerEvent event : events) {
            symbolNotUpdate.remove(event.getSymbol());
            String json = RedisHelper.getInstance().readJsonData(
                    RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, event.getSymbol());
            if (StringUtils.isNotEmpty(json)) {
                PositionRisk pos = Utils.gson.fromJson(json, PositionRisk.class);
                pos.setMarkPrice(event.getLastPrice());                
                pos.setUnrealizedProfit(calUnrealizedProfit(pos));
            }
        }
//        for (Map.Entry<String, Double> entry : sym2Price.entrySet()) {
//            Object sym = entry.getKey();
//            Object price = entry.getValue();
//            builder.append(sym).append(" -> ").append(price).append("\t");
//        }
//        LOG.info("Update price: {}/{} {}", symbols.size(), sym2Price.size(), Utils.toJson(symbols));

    }

    private void startThreadMonitorUpdatePirce() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadMonitorUpdatePirce");
            LOG.info("Start thread ThreadMonitorUpdatePirce!");
            while (true) {
                try {
                    symbolNotUpdate.addAll(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER));
                    Thread.sleep(5 * Utils.TIME_MINUTE);
                    LOG.info("Not update price in 5 minutes: {}/{} {}", symbolNotUpdate.size(), RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER).size(), Utils.toJson(symbolNotUpdate));
                    if (!symbolNotUpdate.isEmpty()) {
                        Utils.sendSms2Telegram("Symbols not update price in 5 minutes: " + Utils.toJson(symbolNotUpdate));
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadMonitorUpdatePirce: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void startThreadUpdatePositionSingle() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdatePositionSingle");
            Set<String> allSymbolHadPos = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER);
            LOG.info("Update pos schedule: {} symbols", allSymbolHadPos.size());
            for (String symbol : allSymbolHadPos) {
                try {
                    PositionRisk pos = getPositionBySymbol(symbol);
                    if (pos != null) {
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER,
                                symbol, Utils.toJson(pos));
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void startThreadProcessAllPosition() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadProcessAllPosition");
            try {
                Set<String> allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER);
                LOG.info("Start process positions: {}", allSymbol.size());
                for (String symbol : allSymbol) {
                    PositionRisk position = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(
                            RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol), PositionRisk.class);
                    if (position == null) {
                        continue;
                    }
                    if (position.getPositionAmt().doubleValue() != 0) {
                        checkProfitToCloseOrStopLoss(position);
                    } else {
                        positionDones.put(symbol, position);
                    }
                }
            } catch (Exception e) {
                LOG.error("ERROR during ThreadMonitorAllPosition: {}", e);
                e.printStackTrace();
            }
        }).start();
    }

}
