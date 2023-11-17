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
    public ConcurrentHashMap<String, Double> symbol2BestProfit = new ConcurrentHashMap<>();
    public ConcurrentHashMap<String, Long> symbol2TimePosition = new ConcurrentHashMap<>();

    public final String FILE_POSITION_FINISHED = "storage/position_target_manager/positionFinished.data";
    public final Map<String, Double> day2Balance = new HashMap<>();
    public final ConcurrentHashMap<String, PositionRisk> allPosition2Monitor = new ConcurrentHashMap<>();
    public final ConcurrentHashMap<String, Order> symbol2OrderDCA = new ConcurrentHashMap<>();
    public static double RATE_MIN_TAKE_PROFIT = Configs.getDouble("TakeProfitRateMinPositionTarget");
    public static double RATE_LOSS_TO_STOP_LOSS = Configs.getDouble("RateStopLoss");//  had * 100
    public static double RATE_LOSS_TO_DCA = Configs.getDouble("RateLoss2DCA");//  had * 100
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
            startThreadListenPriceAndUpdatePosition(symbol);
        }
        startThreadMonitorAllPosition();
        startThreadMOnitorOrderDCA();
        startThreadGetPosition2Manager();
        startThreadListenQueuePosition2Manager();
        startThreadReport();
        startThreadUpdatePosition();
    }

    public static void main(String[] args) {
        new PositionToTargetMonitor().initAndStart();
//        System.out.println(new PositionToTargetMonitor().getAllSymbol());
    }

    private void startThreadMonitorAllPosition() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadMonitorAllPosition");
            LOG.info("Start thread {} !", Thread.currentThread().getName());
            while (true) {
                try {
                    for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER)) {
                        PositionRisk position = allPosition2Monitor.get(symbol);
                        if (position == null) {
                            continue;
                        }
                        if (position.getPositionAmt().doubleValue() != 0) {
                            checkProfitToCloseOrStopLoss(position);
                        } else {
                            if (waitForPositionDone(symbol)) {
                                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol);
                                LOG.info("{} Remove symbol had Close by over margin: {} out list running!", Thread.currentThread().getName(), symbol);
                                allPosition2Monitor.remove(symbol);
                            }
                        }
                    }

                } catch (Exception e) {
                    LOG.error("ERROR during ThreadMonitorAllPosition: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(20 * Utils.TIME_SECOND);
//                    Thread.sleep(10 * Utils.TIME_MINUTE);
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
                    LOG.info("Update pos schedule: {} symbols", allPosition2Monitor.size());
                    for (Map.Entry<String, PositionRisk> entry : allPosition2Monitor.entrySet()) {
                        String symbol = entry.getKey();
                        try {
                            PositionRisk pos = getPositionBySymbol(symbol);
                            allPosition2Monitor.put(symbol, pos);
                            symbol2TimePosition.put(symbol, System.currentTimeMillis());
                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
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
            Double bestProfit = symbol2BestProfit.get(pos.getSymbol());
            if (bestProfit == null) {
                bestProfit = 0d;
            }
            // check and dca
            int rateLoss = rateLoss(pos);
            if (rateLoss >= RATE_LOSS_TO_DCA && symbol2OrderDCA.get(pos.getSymbol()) == null) {
                Order orderDCA = PositionHelper.getInstance().dcaForPosition(pos, RATE_LOSS_TO_STOP_LOSS);
                if (orderDCA != null) {
                    symbol2OrderDCA.put(pos.getSymbol(), orderDCA);
                }
            }
            // stop-loss
            if (rateLoss >= RATE_LOSS_TO_STOP_LOSS && symbol2OrderDCA.get(pos.getSymbol()) != null) {
                LOG.info("Close by market to stoploss: {}", pos);
                Utils.sendSms2Telegram("Close position of: " + pos.getSymbol() + " amt: " + pos.getPositionAmt()
                        + " stoploss: " + pos.getUnrealizedProfit());
                pos = getPositionBySymbol(pos.getSymbol());
                if (pos.getUnrealizedProfit().doubleValue() != 0) {
                    OrderHelper.stopLossPosition(pos);
                }
                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, pos.getSymbol());
                LOG.info("Remove symbol: {} out list stoploss {}!", pos.getSymbol(), rateLoss(pos));
                return true;
            }
            Double currentRateProfit = rateProfit(pos);
            LOG.info("{}: Checking position of: {} current profit: {} bestProfit: {} ", Thread.currentThread().getName(), pos.getSymbol(), currentRateProfit, bestProfit);
            if (currentRateProfit >= RATE_MIN_TAKE_PROFIT) {
                if (currentRateProfit > bestProfit) {
                    String log = "Update best profit: " + pos.getSymbol() + " " + bestProfit + " -> " + currentRateProfit;
                    LOG.info(log);
                    Utils.sendSms2Telegram(log);
                    bestProfit = currentRateProfit;
                    symbol2BestProfit.put(pos.getSymbol(), bestProfit);
                } else {
                    double rateProfit2Close = RATE_PROFIT_DEC_2CLOSE;
                    if (bestProfit < 50) {
                        rateProfit2Close = 40;
                    } else {
                        if (bestProfit < 30) {
                            rateProfit2Close = 50;
                        }
                    }
                    double currentLossProfit = 100 * (bestProfit - currentRateProfit) / bestProfit;
                    boolean isTimeOverLimit = checkTimeProfitAndTime(currentRateProfit, pos.getSymbol());
                    if (currentLossProfit >= rateProfit2Close || isTimeOverLimit) {
                        LOG.info("Close by market: {}", pos);
                        Utils.sendSms2Telegram("Close position of: " + pos.getSymbol() + " amt: " + pos.getPositionAmt()
                                + " profit: " + pos.getUnrealizedProfit() + " Rate: " + bestProfit + "->" + currentRateProfit + " rateloss:" + currentLossProfit + " timeout: {}" + isTimeOverLimit);
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
            Double rate = pos.getUnrealizedProfit().doubleValue() / marginOfPosition(pos);
            rate = Double.valueOf(Utils.formatPercent(rate));
            return Math.abs(rate.intValue());
        } catch (Exception e) {
        }
        return 0;

    }

    private Double rateProfit(PositionRisk pos) {
        double rate;
        rate = pos.getUnrealizedProfit().doubleValue() / marginOfPosition(pos);
        rate = Double.parseDouble(Utils.formatPercent(rate));
        return rate;
    }

    private double marginOfPosition(PositionRisk pos) {
        return Math.abs((pos.getPositionAmt().doubleValue() * pos.getEntryPrice().doubleValue() / pos.getLeverage().doubleValue()));
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
                List<String> data = null;
                try {
                    data = RedisHelper.getInstance().get().blpop(0, RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER_QUEUE);
                    LOG.info("Queue listen symbol to manager position received : {} ", data.toString());
                    String symbol = data.get(1);
                    try {
                        PositionRisk pos = getPositionBySymbol(symbol);
                        if (pos.getPositionAmt().doubleValue() != 0) {
                            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol, Utils.gson.toJson(pos));
                            Double bestProfit = 0d;
                            symbol2BestProfit.put(symbol, bestProfit);
                            allPosition2Monitor.put(symbol, pos);
                            symbol2TimePosition.put(symbol, System.currentTimeMillis());
                            startThreadListenPriceAndUpdatePosition(symbol);
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

    private void startThreadListenPriceAndUpdatePosition(String symbol) {
        LOG.info("Start listen price: {}", symbol);
        SubscriptionClient client = SubscriptionClient.create();
        SubscriptionErrorHandler errorHandler = (BinanceApiException exception) -> {
            LOG.info("Error listen -> create new listener: {}", symbol);
            startThreadListenPriceAndUpdatePosition(symbol);
            exception.printStackTrace();
        };
        client.subscribeSymbolTickerEvent(symbol.toLowerCase(), ((event) -> {
//            LOG.info("Update price: {}", Utils.gson.toJson(event));
            PositionRisk pos = allPosition2Monitor.get(symbol);
            if (pos == null) {
                LOG.info("Re add pos to monitor for {} because not in list monitor pos", symbol);
                pos = getPositionBySymbol(symbol);
                allPosition2Monitor.put(symbol, pos);
                symbol2TimePosition.put(symbol, System.currentTimeMillis());
            }
            pos.setMarkPrice(event.getLastPrice());
            pos.setUnrealizedProfit(calUnrealizedProfit(pos));
        }), errorHandler);
    }

    private BigDecimal calUnrealizedProfit(PositionRisk pos) {
        Double profit;
        profit = pos.getPositionAmt().doubleValue() * (pos.getMarkPrice().doubleValue() - pos.getEntryPrice().doubleValue());
        return new BigDecimal(profit);
    }

    private boolean checkTimeProfitAndTime(double currentRateProfit, String symbol) {
        if (currentRateProfit < 2 * RATE_MIN_TAKE_PROFIT) {
            Long timePos = symbol2TimePosition.get(symbol);
            if (timePos == null) {
                symbol2TimePosition.put(symbol, System.currentTimeMillis());
            }
            if ((System.currentTimeMillis() - timePos) > LIMIT_TIME_POSITION_2CLOSE * Utils.TIME_MINUTE) {
                return true;
            }
        }
        return false;
    }

    private void startThreadMOnitorOrderDCA() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadMOnitorOrderDCA");
            LOG.info("Start thread ThreadMOnitorOrderDCA!");
            while (true) {
                try {
                    // check position close => cancel order dca if order status new
                    Set<String> symbol2Remove = new HashSet<>();
                    for (Map.Entry<String, Order> entry : symbol2OrderDCA.entrySet()) {
                        String symbol = entry.getKey();
                        Order orderDCA = entry.getValue();
                        if (allPosition2Monitor.get(symbol) == null) {
                            Order orderDcaInfo = PositionHelper.getInstance().readOrderInfo(symbol, orderDCA.getOrderId());
                            if (orderDcaInfo != null && StringUtils.equals(orderDcaInfo.getStatus(), "NEW")) {
                                String log = "Cancel order DCA: " + Utils.toJson(orderDcaInfo);
                                LOG.info(log);
                                Utils.sendSms2Telegram(log);
                                PositionHelper.getInstance().cancelOrder(symbol, orderDCA.getOrderId());
                            }
                            symbol2Remove.add(symbol);
                        }
                    }
                    for (String symbol : symbol2Remove) {
                        symbol2OrderDCA.remove(symbol);
                        LOG.info("Remove order DCA of list monitor: {}", symbol);
                    }
                    Thread.sleep(5 * Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadMOnitorOrderDCA: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

}
