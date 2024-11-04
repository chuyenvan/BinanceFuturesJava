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
package com.binance.chuyennd.signal.tradingview;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.indicators.SimpleMovingAverage1DManager;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.SubscriptionErrorHandler;
import com.binance.client.constant.Constants;
import com.binance.client.exception.BinanceApiException;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.event.SymbolTickerEvent;
import com.binance.chuyennd.trading.OrderTargetStatus;

import java.io.File;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;

import com.google.gson.internal.LinkedTreeMap;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @author pc
 */
public class SignalTWSimulator {

    public static final Logger LOG = LoggerFactory.getLogger(SignalTWSimulator.class);
    public static final String URL_SIGNAL_TRADINGVIEW_15M = "http://172.25.80.128:8002/";
    public static final String URL_SIGNAL_TRADINGVIEW_1H = "http://172.25.80.128:8003/";
    public static final String URL_SIGNAL_TRADINGVIEW_4H = "http://172.25.80.128:8004/";
    public static final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestTADone.data";
    public static final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public final Double RATE_MA_MAX = Configs.getDouble("RATE_MA_MAX");
    public ConcurrentHashMap<Long, OrderTargetInfoTestSignal> allOrderDone;

    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));

    public static void main(String[] args) throws IOException {
        new SignalTWSimulator().start();
    }

    public void startThreadManagerPosition() {

        new Thread(() -> {
            Thread.currentThread().setName("ThreadAltDetectBread");
            LOG.info("Start thread ThreadAltDetectBread target: {}", 0.01);
            while (true) {
                if (isTimeScheduleUpdateOrder()) {
                    try {
                        LOG.info("Start update order by schedule! {}", new Date());
                        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER)) {
                            executorService.execute(() -> updatePositionBySchedule(symbol));
                        }
                    } catch (Exception e) {
                        LOG.error("ERROR during ThreadBigBeardTrading: {}", e);
                        e.printStackTrace();
                    }
                }

                try {
                    Thread.sleep(Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(SignalTWSimulator.class.getName()).log(Level.SEVERE, null, ex);
                }

            }
        }).start();
    }

    private void updatePositionBySchedule(String symbol) {
        try {
            OrderTargetInfoTestSignal orderInfo = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol),
                    OrderTargetInfoTestSignal.class);
            KlineObjectNumber ticker = TickerFuturesHelper.getLastTicker(symbol, Constants.INTERVAL_15M);
            if (orderInfo.timeStart < ticker.startTime.longValue()) {
                orderInfo.updatePriceByKline(ticker);
//                LOG.warn("Update price for {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), Utils.toJson(ticker));
                orderInfo.updateStatus();
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE) ||
                        orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                    RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol);
                    orderInfo.tickerClose = ticker;
                    orderInfo.timeUpdate = System.currentTimeMillis();
                    allOrderDone.put(System.currentTimeMillis(), orderInfo);
                    Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
                } else {
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol, Utils.toJson(orderInfo));
                }
            }
        } catch (Exception e) {
            LOG.info("Error detect big bread of symbol:{}", symbol);
            e.printStackTrace();
        }
    }

    public boolean isTimeScheduleUpdateOrder() {
        return Utils.getCurrentMinute() % 15 == 14 && Utils.getCurrentSecond() == 55;
    }

    public boolean isTimeReport() {
        return Utils.getCurrentMinute() % 15 == 1 && Utils.getCurrentSecond() == 0;
    }

    private void checkStrongSignal2Trading() {
        new Thread(() -> {
            Thread.currentThread().setName("StrongSignal2Trading");
            LOG.info("Start thread StrongSignal2Trading!");
            while (true) {
                try {
                    getStrongSignal2Trading();
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadBigBeardTrading: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(15 * Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(SignalTWSimulator.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }


    private void threadListenPrice() {
        SubscriptionClient client = SubscriptionClient.create();
        SubscriptionErrorHandler errorHandler = (BinanceApiException exception) -> {
        };
        client.subscribeAllTickerEvent(((event) -> {
            executorService.execute(() -> updatePriceFromEventAllTicker(event));
        }), errorHandler);
    }

    private void updatePriceFromEventAllTicker(List<SymbolTickerEvent> events) {
        StringBuilder builder = new StringBuilder();
        builder.setLength(0);
        for (SymbolTickerEvent event : events) {
            String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, event.getSymbol());
            if (StringUtils.isNotEmpty(json)) {
                OrderTargetInfoTestSignal orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTestSignal.class);
                orderInfo.updatePriceByLastPrice(event.getLastPrice().doubleValue());
                orderInfo.updateStatus();
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    allOrderDone.put(System.currentTimeMillis(), orderInfo);
                    RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, event.getSymbol());
                } else {
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, event.getSymbol(), Utils.toJson(orderInfo));
                }
            }
        }
    }

    private void getStrongSignal2Trading() {
        LOG.info("Start detect symbol is Strong signal! {}", new Date());

        // check symbol had position running
        Set<String> symbolsTrading = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER);
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS)) {
            try {
                if (symbolsTrading.contains(symbol)) {
                    continue;
                }
                if (Constants.diedSymbol.contains(symbol)) {
                    continue;
                }
                strongSignal2TradeBySymbol(symbol);

            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private void addOrderTrading(String symbol, OrderSide sideSignal, KlineObjectNumber ticker) {
        Double entry = ticker.priceClose;
        Double priceTp = Utils.calPriceTarget(symbol, entry, sideSignal, RATE_TARGET);
        String log = sideSignal + " " + symbol + " by signal tradingview entry: " + entry + " target: "
                + priceTp + " stoploss: " + 0.0 + " time:" + Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis());
//        Utils.sendSms2Telegram(log);
        OrderTargetInfoTestSignal order = new OrderTargetInfoTestSignal(OrderTargetStatus.REQUEST, entry, priceTp, 0.0, 10, symbol,
                System.currentTimeMillis(), System.currentTimeMillis(), sideSignal);
        order.minPrice = entry;
        order.maxPrice = entry;
        order.tickerOpen = ticker;
        order.signals.addAll(getAllSignal(symbol));
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol, Utils.toJson(order));
        LOG.info(log);

    }

    private Collection<String> getAllSignal(String symbol) {
        List<String> signals = new ArrayList<>();
        try {
            signals.add(getRecommendationRaw(symbol, Constants.INTERVAL_15M));
            signals.add(getRecommendationRaw(symbol, Constants.INTERVAL_1H));
            signals.add(getRecommendationRaw(symbol, Constants.INTERVAL_4H));
            signals.add(getRecommendationRaw(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_15M));
            signals.add(getRecommendationRaw(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1H));
            signals.add(getRecommendationRaw(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_4H));
        } catch (Exception e) {
            e.printStackTrace();
        }
        return signals;
    }

    private void reportPosition() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadReportPositionTradingview ");
            LOG.info("Start thread report trading by signal tradingview!");
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_SECOND);
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

    private StringBuilder calReportRunning() {
        StringBuilder builder = new StringBuilder();
        Map<String, Double> sym2Volume = TickerFuturesHelper.getAllVolume24hr();
        Long totalLoss = 0l;
        Long totalBuy = 0l;
        Long totalSell = 0l;
        TreeMap<Double, OrderTargetInfoTestSignal> rate2Order = new TreeMap<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER)) {
            OrderTargetInfoTestSignal orderInfo = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol),
                    OrderTargetInfoTestSignal.class);
            Double rateLoss = orderInfo.calRateLoss() * 10000;
            rate2Order.put(rateLoss, orderInfo);
        }
        int counterLog = 0;
        for (Map.Entry<Double, OrderTargetInfoTestSignal> entry : rate2Order.entrySet()) {
            Double rateLoss = entry.getKey();
            OrderTargetInfoTestSignal orderInfo = entry.getValue();
            Long ratePercent = rateLoss.longValue();
            totalLoss += ratePercent;
            if (orderInfo.side.equals(OrderSide.BUY)) {
                totalBuy += ratePercent;
            } else {
                totalSell += ratePercent;
            }

            if (Math.abs(rateLoss) > 60 && counterLog < 15) {
                counterLog++;
                Long rateTp = calRateTp(orderInfo).longValue();
                Double volume24hr = sym2Volume.get(orderInfo.symbol);
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart)).append(" ")
                        .append(orderInfo.side).append(" ")
                        .append(orderInfo.symbol).append(" ")
                        .append(volume24hr.longValue() / 1000000).append("M ")
                        .append(orderInfo.priceEntry).append("->").append(orderInfo.lastPrice)
                        .append(" ").append(rateTp.doubleValue() / 100).append("%")
                        .append(" ").append(ratePercent.doubleValue() / 100).append("%")
                        .append("\n");
            }
        }

        builder.append("Total: ").append(totalLoss.doubleValue() / 100).append("%");
        builder.append(" Buy: ").append(totalBuy.doubleValue() / 100).append("%");
        builder.append(" Sell: ").append(totalSell.doubleValue() / 100).append("%");
        return builder;
    }

    private void start() {
        LOG.info("Start SingalTWSimulator!");
        initData();
        threadListenPrice();
        checkStrongSignal2Trading();
        startThreadManagerPosition();
        reportPosition();

    }

    private void initData() {
        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
            allOrderDone = (ConcurrentHashMap<Long, OrderTargetInfoTestSignal>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_DONE);
        } else {
            allOrderDone = new ConcurrentHashMap<>();
        }
    }

    private void strongSignal2TradeBySymbol(String symbol) {
        KlineObjectNumber ticker = TickerFuturesHelper.getLastTicker(symbol, Constants.INTERVAL_15M);
        OrderSide sideSignal = getStrongSignalASymbol(symbol);
        if (isTradingAvailable(sideSignal, symbol,ticker)) {
            addOrderTrading(symbol, sideSignal, ticker);
        }
    }

    private boolean isTradingAvailable(OrderSide sideSignal, String symbol, KlineObjectNumber ticker) {
        MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(ticker.startTime.longValue(), symbol);
        Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(ticker.startTime.longValue()));
        if (maValue == null) {
            return false;
        }
        Double rateMa = Utils.rateOf2Double(ticker.priceClose, maValue);
        if (sideSignal != null
                && sideSignal.equals(OrderSide.BUY)
                && getSignalBySymbol(symbol,Constants.INTERVAL_1H).equals(OrderSide.BUY)
                && getSignalBySymbol(symbol,Constants.INTERVAL_4H).equals(OrderSide.BUY)
                && getSignalBySymbol(Constants.SYMBOL_PAIR_BTC,Constants.INTERVAL_15M).equals(OrderSide.BUY)
                && getSignalBySymbol(Constants.SYMBOL_PAIR_BTC,Constants.INTERVAL_1H).equals(OrderSide.BUY)
                && getSignalBySymbol(Constants.SYMBOL_PAIR_BTC,Constants.INTERVAL_4H).equals(OrderSide.BUY)
                && maStatus != null && maStatus.equals(MAStatus.TOP)
                && rateMa < RATE_MA_MAX
        ){
            return true;
        }
        return false;
    }


    private OrderSide getStrongSignalASymbol(String symbol) {
        try {
            String signalRecommendation = getRecommendation(symbol);
            if (StringUtils.isNotEmpty(signalRecommendation)) {
                OrderSide sideSignal = OrderSide.BUY;
                if (StringUtils.equalsIgnoreCase(signalRecommendation, "sell")) {
                    sideSignal = OrderSide.SELL;
                }
                return sideSignal;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public OrderSide getSignalBySymbol(String symbol, String interval) {

        try {
            String respon = getRecommendationRaw(symbol, interval);
            List<LinkedTreeMap> responObjects = Utils.gson.fromJson(respon, List.class);
            if (responObjects != null && !responObjects.isEmpty()) {
                String sideSignal = responObjects.get(0).get("recommendation").toString();
                if (StringUtils.contains(sideSignal, "BUY")) {
                    return OrderSide.BUY;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return OrderSide.SELL;
    }

    public String getRecommendationRaw(String symbol, String interval) {
        String urlSignal = URL_SIGNAL_TRADINGVIEW_15M + symbol;
        switch (interval) {
            case Constants.INTERVAL_1H:
                urlSignal = URL_SIGNAL_TRADINGVIEW_1H + symbol;
                break;
            case Constants.INTERVAL_4H:
                urlSignal = URL_SIGNAL_TRADINGVIEW_4H + symbol;
                break;
        }
        int timeout = 3000;
        return HttpRequest.getContentFromUrl(urlSignal, timeout);
    }

    private String getRecommendation(String symbol) {
        String result = "";
        try {
            String respon = getRecommendationRaw(symbol, Constants.INTERVAL_15M);
            List<LinkedTreeMap> responObjects = Utils.gson.fromJson(respon, List.class);
            if (responObjects != null && !responObjects.isEmpty()) {
                String sideSignal = responObjects.get(0).get("recommendation").toString();
                if (StringUtils.contains(sideSignal, "STRONG")) {
                    result = sideSignal.split("_")[1];
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return result;
    }

    public void buildReport() {
        StringBuilder reportRunning = calReportRunning();
        int totalTP = 0;
        Double total = 0d;
        int totalSL = 0;

        for (OrderTargetInfoTestSignal order : allOrderDone.values()) {
            Double pnlRate = order.calProfit();
            total += pnlRate;
            if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                totalTP++;
            } else {
                totalSL++;
            }
        }
        total *= 100;
        reportRunning.append(" Success: ").append(total.longValue()).append("%");
        reportRunning.append(" loss/tp: ").append(totalSL).append("/").append(totalTP);
        reportRunning.append(" Running: ").append(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER).size()).append(" orders");
        Utils.sendSms2Telegram(reportRunning.toString());
//        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
    }

    public void buildReportTest() {

        StringBuilder reportRunning = new StringBuilder();
        ConcurrentHashMap<Long, OrderTargetInfoTestSignal> orderDones =
                (ConcurrentHashMap<Long, OrderTargetInfoTestSignal>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_DONE);
        int totalTP = 0;
        Double total = 0d;
        int totalSL = 0;

        for (OrderTargetInfoTestSignal order : orderDones.values()) {
            Double pnlRate = order.calProfit();
            total += pnlRate;
            if (order.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                totalTP++;
            } else {
                totalSL++;
            }
        }
        total *= 100;
        reportRunning.append(" Success: ").append(total.longValue()).append("%");
        reportRunning.append(" loss/tp: ").append(totalSL).append("/").append(totalTP);
        reportRunning.append(" Running: ").append(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER).size()).append(" orders");
        Utils.sendSms2Telegram(reportRunning.toString());
//        Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
    }

    public static Double calRateTp(OrderTargetInfoTestSignal orderInfo) {

        double rate = Utils.rateOf2Double(orderInfo.maxPrice, orderInfo.priceEntry);
        if (orderInfo.side.equals(OrderSide.SELL)) {
            rate = -Utils.rateOf2Double(orderInfo.minPrice, orderInfo.priceEntry);
        }
        return rate * 10000;

    }


    public static void printAllOrderRunning() {
        Map<String, Double> sym2Volume = TickerFuturesHelper.getAllVolume24hr();
        TreeMap<Double, OrderTargetInfoTestSignal> rate2Order = new TreeMap<>();
        Integer counter50M = 0;
        Set<String> symbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER);
        for (String symbol : symbols) {
            OrderTargetInfoTestSignal orderInfo = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_TEST_TD_POS_MANAGER, symbol),
                    OrderTargetInfoTestSignal.class);
            Double rateLoss = orderInfo.calRateLoss() * 10000;
            rate2Order.put(rateLoss, orderInfo);
        }

        for (Map.Entry<Double, OrderTargetInfoTestSignal> entry : rate2Order.entrySet()) {
            Double rateLoss = entry.getKey();
            OrderTargetInfoTestSignal orderInfo = entry.getValue();
            Long ratePercent = rateLoss.longValue();
            Long rateTp = calRateTp(orderInfo).longValue();
            Double volume24hr = sym2Volume.get(orderInfo.symbol) / 1000000;
            if (volume24hr < 50) {
                counter50M++;
            }
            StringBuilder builder = new StringBuilder();
//            KlineObjectNumber ticker24hr = TickerHelper.getTickerByTime(orderInfo.symbol, Constants.INTERVAL_4H, orderInfo.timeStart);
//            Double tickerChange = Utils.rateOf2Double(ticker24hr.priceClose, ticker24hr.priceOpen) * 10000;
//            double rate = tickerChange.longValue();

            builder.append(Utils.normalizeDateYYYYMMDDHHmm(orderInfo.timeStart)).append(" ")
                    .append(orderInfo.side).append(" ")
                    .append(orderInfo.symbol).append(" ")
                    .append(volume24hr.longValue()).append("M ")
                    .append(orderInfo.priceEntry).append("->").append(orderInfo.priceTP)
                    //                    .append(" tickerchange: ").append(rate / 100).append("% ")
                    .append(" ").append(rateTp.doubleValue() / 100).append("%")
                    .append(" ").append(ratePercent.doubleValue() / 100).append("%");
            LOG.info(builder.toString());
//                    + " " + orderInfo.singals);

        }
        Double rate50M = counter50M.doubleValue() / symbols.size();
        LOG.info("{} {} {}", counter50M, symbols.size(), rate50M);

    }
}
