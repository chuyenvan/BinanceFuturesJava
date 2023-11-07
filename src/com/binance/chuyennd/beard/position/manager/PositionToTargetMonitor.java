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
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.PositionRisk;
import java.io.File;
import java.util.ArrayList;
import java.util.Collection;
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
    public ConcurrentHashMap<String, List<PositionRisk>> allOrderFnished = new ConcurrentHashMap<>();
    private static volatile PositionToTargetMonitor INSTANCE = null;
    
    public final String FILE_POSITION_FINISHED = "storage/position_target_manager/positionFinished.data";
    public static double RATE_MIN_TAKE_PROFIT;
    public static double RATE_LOSS_TO_STOP_LOSS;
    public static double RATE_PROFIT_DEC_2CLOSE;
    
    public int counter = 0;
    
    public static PositionToTargetMonitor getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new PositionToTargetMonitor();
            INSTANCE.initClient();
        }
        return INSTANCE;
    }
    
    private void initClient() {
        ClientSingleton.getInstance();
        try {
            Thread.sleep(5000);
        } catch (InterruptedException ex) {
            java.util.logging.Logger.getLogger(PositionToTargetMonitor.class.getName()).log(Level.SEVERE, null, ex);
        }
        RATE_MIN_TAKE_PROFIT = Configs.getDouble("TakeProfitRateMinPositionTarget");
        RATE_LOSS_TO_STOP_LOSS = Configs.getDouble("RateStopLoss");//  had * 100
        RATE_PROFIT_DEC_2CLOSE = Configs.getDouble("ProfitDec2Close");//  had * 100

        if (new File(FILE_POSITION_FINISHED).exists()) {
            allOrderFnished = (ConcurrentHashMap<String, List<PositionRisk>>) Storage.readObjectFromFile(FILE_POSITION_FINISHED);
        } else {
            allOrderFnished = new ConcurrentHashMap<>();
        }
        // start thread monitor symbol running
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER)) {
            startThreadMonitorPositionBySymbol(symbol);
        }
        startThreadGetPosition2Manager();
        startThreadListenQueuePosition2Manager();
        startThreadReport();
    }
    
    public static void main(String[] args) {
        new PositionToTargetMonitor().initClient();
//        System.out.println(new PositionToTargetMonitor().getAllSymbol());
    }
    
    private void startThreadMonitorPositionBySymbol(String symbol) {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadMonitorPositionBySymbol-" + symbol);
            LOG.info("Start thread ThreadMonitorPositionBySymbol: {} !", symbol);
            PositionRisk lastPosition = null;
            while (true) {
                try {
                    PositionRisk position = getPositionBySymbol(symbol);
                    if (position.getPositionAmt().doubleValue() != 0) {
                        lastPosition = position;
                        boolean closePos = checkProfitToCloseOrStopLoss(symbol);
                        if (closePos) {
                            return;
                        }
                    } else {
                        if (waitForPositionDone(symbol)) {
                            RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol);
                            LOG.info("{} Remove symbol had Close by over margin: {} out list running!", Thread.currentThread().getName(), symbol);
                            String today = Utils.getToDayFileName();
                            List<PositionRisk> orderSucessByDate = allOrderFnished.get(today);
                            if (orderSucessByDate == null) {
                                orderSucessByDate = new ArrayList<>();
                                allOrderFnished.put(today, orderSucessByDate);
                            }
                            orderSucessByDate.add(lastPosition);
                            Storage.writeObject2File(FILE_POSITION_FINISHED, allOrderFnished);
                            return;
                        }
                    }
                    
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadMonitorPositionBySymbol: {} {}", symbol, e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(30 * Utils.TIME_SECOND);
                } catch (Exception ex) {
                    ex.printStackTrace();
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
                    Thread.sleep(120 * Utils.TIME_MINUTE);
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
    
    private boolean checkProfitToCloseOrStopLoss(String symbol) {
        try {
            Double bestProfit = symbol2BestProfit.get(symbol);
            if (bestProfit == null) {
                bestProfit = 0d;
            }
            PositionRisk pos = getPositionBySymbol(symbol);
            if (rateLoss(pos) >= RATE_LOSS_TO_STOP_LOSS) {
                LOG.info("Close by market to stoploss: {}", pos);
                Utils.sendSms2Telegram("Close position of: " + symbol + " amt: " + pos.getPositionAmt()
                        + " stoploss: " + pos.getUnrealizedProfit());
                OrderHelper.stopLossPosition(pos);
                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol);
                LOG.info("Remove symbol: {} out list stoploss {}!", symbol, rateLoss(pos));
                String today = Utils.getToDayFileName();
                List<PositionRisk> orderSucessByDate = allOrderFnished.get(today);
                if (orderSucessByDate == null) {
                    orderSucessByDate = new ArrayList<>();
                    allOrderFnished.put(today, orderSucessByDate);
                }
                orderSucessByDate.add(pos);
                Storage.writeObject2File(FILE_POSITION_FINISHED, allOrderFnished);
                return true;
            }
            Double currentRateProfit = rateProfit(pos);
            LOG.info("{}: Checking position of: {} current profit: {} bestProfit: {} ", Thread.currentThread().getName(), symbol, currentRateProfit, bestProfit);
            if (currentRateProfit >= RATE_MIN_TAKE_PROFIT) {
                if (currentRateProfit > bestProfit) {
                    String log = "Update best profit: " + symbol + " " + bestProfit + " -> " + currentRateProfit;
                    LOG.info(log);
                    Utils.sendSms2Telegram(log);
                    bestProfit = currentRateProfit;
                    symbol2BestProfit.put(symbol, bestProfit);
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
                    if (currentLossProfit >= rateProfit2Close) {
                        LOG.info("Close by market: {}", pos);
                        Utils.sendSms2Telegram("Close position of: " + symbol + " amt: " + pos.getPositionAmt()
                                + " profit: " + pos.getUnrealizedProfit() + " Rate: " + bestProfit + "->" + currentRateProfit + " rateloss:" + currentLossProfit);
                        OrderHelper.takeProfitPosition(pos);
                        RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol);
                        LOG.info("Remove symbol: {} out list running profit change from {} {}!", symbol, bestProfit, currentRateProfit);
                        String today = Utils.getToDayFileName();
                        List<PositionRisk> orderSucessByDate = allOrderFnished.get(today);
                        if (orderSucessByDate == null) {
                            orderSucessByDate = new ArrayList<>();
                            allOrderFnished.put(today, orderSucessByDate);
                        }
                        orderSucessByDate.add(pos);
                        Storage.writeObject2File(FILE_POSITION_FINISHED, allOrderFnished);
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
    
    private void dcaForPosition(PositionRisk pos) {
        try {
            LOG.info("DCA for {} {}", pos.getSymbol(), pos.getPositionAmt());
            OrderSide side = OrderSide.BUY;
            if (pos.getPositionAmt().doubleValue() < 0) {
                side = OrderSide.SELL;
            }
            OrderHelper.dcaForPosition(pos.getSymbol(), side, Math.abs(pos.getPositionAmt().doubleValue()));
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
//        if (pos.getUnrealizedProfit().doubleValue() > 0) {
        rate = pos.getUnrealizedProfit().doubleValue() / marginOfPosition(pos);
        rate = Double.parseDouble(Utils.formatPercent(rate));
//        }
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
                            startThreadMonitorPositionBySymbol(symbol);
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
    
}
