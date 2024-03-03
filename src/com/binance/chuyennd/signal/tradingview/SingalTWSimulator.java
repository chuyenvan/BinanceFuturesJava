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

import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TickerStatistics;
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
import com.binance.chuyennd.trading.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.google.gson.internal.LinkedTreeMap;
import java.io.File;
import java.io.IOException;
import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentSkipListSet;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class SingalTWSimulator {

    public static final Logger LOG = LoggerFactory.getLogger(SingalTWSimulator.class);

    private final ConcurrentSkipListSet<String> allSymbol = new ConcurrentSkipListSet<>();
    public static final String URL_SIGNAL_TRADINGVIEW = "http://103.157.218.242:8002/";
    public static final String FILE_STORAGE_ORDER_DONE = "storage/OrderTestDone.data";
    public static final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public ConcurrentHashMap<Long, OrderTargetInfoTest> allOrderDone;

    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));

    public static void main(String[] args) throws IOException {

        new SingalTWSimulator().start();
//        new SingalTWSimulator().getStrongSignal2TradingBigVolumeBuy();
//        new SingalTWSimulator().getStrongSignal2TradingBigVolumeSell();
//        new TradingBySignalTradingView().buildReport();
//        System.out.println(new TradingBySignalTradingView().getReconmendation("BTCUSDT"));
    }

    public void startThreadManagerPosition() {

        new Thread(() -> {
            Thread.currentThread().setName("ThreadAltDetectBread");
            LOG.info("Start thread ThreadAltDetectBread target: {}", 0.01);
            while (true) {

                if (isTimeDetectBigChange()) {
                    try {
                        LOG.info("Start detect symbol is beard big! {}", new Date());
                        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER)) {
                            executorService.execute(() -> updatePositionBySymbol(symbol));
                        }
                    } catch (Exception e) {
                        LOG.error("ERROR during ThreadBigBeardTrading: {}", e);
                        e.printStackTrace();
                    }
                }

                try {
                    Thread.sleep(Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(SingalTWSimulator.class.getName()).log(Level.SEVERE, null, ex);
                }

            }
        }).start();
    }

    private void updatePositionBySymbol(String symbol) {
        try {
            OrderTargetInfoTest orderInfo = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol),
                    OrderTargetInfoTest.class);
            KlineObjectNumber ticker = TickerFuturesHelper.getLastTicker(symbol, Constants.INTERVAL_15M);
            if (orderInfo.timeStart < ticker.startTime.longValue()) {
                orderInfo.updatePriceByKline(ticker);
                LOG.info("Update price for {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()), Utils.toJson(ticker));
                orderInfo.updateStatus();
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    allOrderDone.put(System.currentTimeMillis(), orderInfo);
                    RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol);
                    Storage.writeObject2File(FILE_STORAGE_ORDER_DONE, allOrderDone);
                } else {
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol, Utils.toJson(orderInfo));
                }
            }
        } catch (Exception e) {
            LOG.info("Error detect big bread of symbol:{}", symbol);
            e.printStackTrace();
        }
    }

    public boolean isTimeDetectBigChange() {
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
                    getStrongSignal2TradingMiniVolume();
//                    getStrongSignal2TradingBigVolumeBuy();
//                    getStrongSignal2TradingBigVolumeSell();
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadBigBeardTrading: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(Utils.TIME_MINUTE);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(SingalTWSimulator.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private OrderSide getStrongSignalASymbol(String symbol) {
        try {
            String signalRecommendation = getReconmendation(symbol);
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
            String json = RedisHelper.getInstance().readJsonData(
                    RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, event.getSymbol());
            if (StringUtils.isNotEmpty(json)) {
                OrderTargetInfoTest orderInfo = Utils.gson.fromJson(json, OrderTargetInfoTest.class);
                orderInfo.updatePriceByLastPrice(event.getLastPrice().doubleValue());
                orderInfo.updateStatus();
                if (orderInfo.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)) {
                    allOrderDone.put(System.currentTimeMillis(), orderInfo);
                    RedisHelper.getInstance().get().hdel(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, event.getSymbol());
                } else {
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, event.getSymbol(), Utils.toJson(orderInfo));
                }
            }
        }
    }

    private void getStrongSignal2TradingMiniVolume() {
        LOG.info("Start detect symbol is Strong signal! {}", new Date());
        Set<String> symbolsVolumeOver50M = getAllSymbolVolumeOver50M();
        for (String symbol : allSymbol) {
            try {
                // check symbol had position running
                Set<String> symbolsTrading = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER);
                if (symbolsTrading.contains(symbol)
                        || symbolsVolumeOver50M.contains(symbol)) {
                    continue;
                }
                strongSignal2TradeBySymbol(symbol);

            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private void getStrongSignal2TradingBigVolumeBuy() {
        LOG.info("Start detect symbol is Strong signal! {}", new Date());
        Set<String> symbolsVolumeBigChangeAndTrendBuy = getAllSymbolVolumeOver100MIncre2Buy();
        symbolsVolumeBigChangeAndTrendBuy.removeAll(Constants.specialSymbol);
        for (String symbol : symbolsVolumeBigChangeAndTrendBuy) {
            try {
                // check symbol had position running
                Set<String> symbolsTrading = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER);
                if (symbolsTrading.contains(symbol)) {
                    continue;
                }
                strongSignalBuy2TradeBySymbol(symbol);

            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private void getStrongSignal2TradingBigVolumeSell() {
        LOG.info("Start detect symbol is Strong signal! {}", new Date());
        Set<String> symbolsVolumeBigChangeAndTrendBuy = getAllSymbolVolumeOver100MDecre2Sell();
        symbolsVolumeBigChangeAndTrendBuy.removeAll(Constants.specialSymbol);
        for (String symbol : symbolsVolumeBigChangeAndTrendBuy) {
            try {
                // check symbol had position running
                Set<String> symbolsTrading = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER);
                if (symbolsTrading.contains(symbol)) {
                    continue;
                }
                strongSignalSell2TradeBySymbol(symbol);

            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private String getReconmendation(String symbol) {
        String result = "";
        try {
            String urlSignal = URL_SIGNAL_TRADINGVIEW + symbol;
            String respon = HttpRequest.getContentFromUrl(urlSignal);
            List<LinkedTreeMap> responObjects = Utils.gson.fromJson(respon, List.class);
            if (responObjects != null && !responObjects.isEmpty()) {
                String sideSignal = responObjects.get(0).get("recommendation").toString();
                if (StringUtils.contains(sideSignal, "STRONG")) {
                    result = sideSignal.split("_")[1];
                    LOG.info("StrongSignal: {}", respon);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return result;
    }

    private void addOrderTrading(String symbol, OrderSide sideSignal) {
        Double entry = ClientSingleton.getInstance().getCurrentPrice(symbol);
        Double priceTp = Utils.calPriceTarget(symbol, entry, sideSignal, RATE_TARGET);

        String log = sideSignal + " " + symbol + " by signal tradingview entry: " + entry + " target: "
                + priceTp + " stoploss: " + 0.0 + " time:" + Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis());
//        Utils.sendSms2Telegram(log);
        OrderTargetInfoTest order = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, priceTp, 0.0, 10, symbol,
                System.currentTimeMillis(), System.currentTimeMillis(), sideSignal, "SINGAL_TRADINGVIEW", false);
        order.minPrice = entry;
        order.maxPrice = entry;
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol, Utils.toJson(order));
        LOG.info(log);

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
        TreeMap<Double, OrderTargetInfoTest> rate2Order = new TreeMap<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER)) {
            OrderTargetInfoTest orderInfo = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol),
                    OrderTargetInfoTest.class);
            Double rateLoss = orderInfo.calRateLoss() * 10000;
            rate2Order.put(rateLoss, orderInfo);
        }
        int counterLog = 0;
        for (Map.Entry<Double, OrderTargetInfoTest> entry : rate2Order.entrySet()) {
            Double rateLoss = entry.getKey();
            OrderTargetInfoTest orderInfo = entry.getValue();
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
        if (allSymbol.isEmpty()) {
            allSymbol.addAll(ClientSingleton.getInstance().getAllSymbol());
            allSymbol.removeAll(Constants.specialSymbol);
        }
        if (new File(FILE_STORAGE_ORDER_DONE).exists()) {
            allOrderDone = (ConcurrentHashMap<Long, OrderTargetInfoTest>) Storage.readObjectFromFile(FILE_STORAGE_ORDER_DONE);
        } else {
            allOrderDone = new ConcurrentHashMap<>();
        }
    }

    private void strongSignal2TradeBySymbol(String symbol) {
        OrderSide sideSignal = getStrongSignalASymbol(symbol);
        if (sideSignal != null) {
            addOrderTrading(symbol, sideSignal);
        }
    }

    private void strongSignalBuy2TradeBySymbol(String symbol) {
        OrderSide sideSignal = getStrongSignalASymbol(symbol);
        if (sideSignal != null && sideSignal.equals(OrderSide.BUY)) {
            addOrderTrading(symbol, sideSignal);
        }
    }

    private void strongSignalSell2TradeBySymbol(String symbol) {
        OrderSide sideSignal = getStrongSignalASymbol(symbol);
        if (sideSignal != null && sideSignal.equals(OrderSide.SELL)) {
            addOrderTrading(symbol, sideSignal);
        }
    }

    private void buildReport() {
        StringBuilder reportRunning = calReportRunning();
        reportRunning.append(" Success: ").append(allOrderDone.size() * RATE_TARGET * 100).append("%");
        int totalBuy = 0;
        int totalSell = 0;
        for (OrderTargetInfoTest order : allOrderDone.values()) {
            if (order.side.equals(OrderSide.BUY)) {
                totalBuy++;
            } else {
                totalSell++;
            }
        }
        reportRunning.append(" Buy: ").append(totalBuy * RATE_TARGET * 100).append("%");
        reportRunning.append(" Sell: ").append(totalSell * RATE_TARGET * 100).append("%");
        reportRunning.append(" Running: ").append(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER).size()).append(" orders");
        Utils.sendSms2Telegram(reportRunning.toString());
    }

    public static Double calRateTp(OrderTargetInfoTest orderInfo) {

        double rate = Utils.rateOf2Double(orderInfo.maxPrice, orderInfo.priceEntry);
        if (orderInfo.side.equals(OrderSide.SELL)) {
            rate = -Utils.rateOf2Double(orderInfo.minPrice, orderInfo.priceEntry);
        }
        return rate * 10000;

    }

    public static void printAllOrderRunning() {
        Map<String, Double> sym2Volume = TickerFuturesHelper.getAllVolume24hr();
        TreeMap<Double, OrderTargetInfoTest> rate2Order = new TreeMap<>();
        Integer counter50M = 0;
        Set<String> symbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER);
        for (String symbol : symbols) {
            OrderTargetInfoTest orderInfo = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol),
                    OrderTargetInfoTest.class);
            Double rateLoss = orderInfo.calRateLoss() * 10000;
            rate2Order.put(rateLoss, orderInfo);
        }

        for (Map.Entry<Double, OrderTargetInfoTest> entry : rate2Order.entrySet()) {
            Double rateLoss = entry.getKey();
            OrderTargetInfoTest orderInfo = entry.getValue();
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

        }
        Double rate50M = counter50M.doubleValue() / symbols.size();
        LOG.info("{} {} {}", counter50M, symbols.size(), rate50M);

    }

    private Set<String> getAllSymbolVolumeOver50M() {
        Set<String> syms = new HashSet<>();
        Map<String, Double> sym2Volume = TickerFuturesHelper.getAllVolume24hr();
        for (Map.Entry<String, Double> entry : sym2Volume.entrySet()) {
            String sym = entry.getKey();
            Double volume = entry.getValue();
            if ((volume / 1000000) >= 40) {
                syms.add(sym);
            }
        }
        return syms;
    }

    private Set<String> getAllSymbolVolumeOver100MIncre2Buy() {
        Set<String> syms = new HashSet<>();
        Map<String, TickerStatistics> sym2Ticker = TickerFuturesHelper.getAllTicker24hr();
        for (Map.Entry<String, TickerStatistics> entry : sym2Ticker.entrySet()) {
            String sym = entry.getKey();
            TickerStatistics ticker = entry.getValue();
            if ((Double.parseDouble(ticker.getQuoteVolume()) / 1000000) >= 50
                    && (Double.parseDouble(ticker.getQuoteVolume()) / 1000000) <= 100
                    && Utils.rateOf2Double(Double.valueOf(ticker.getLastPrice()), Double.valueOf(ticker.getOpenPrice())) >= 0.03) {
                syms.add(sym);
            }
        }
        return syms;
    }

    private Set<String> getAllSymbolVolumeOver100MDecre2Sell() {
        Set<String> syms = new HashSet<>();
        Map<String, TickerStatistics> sym2Ticker = TickerFuturesHelper.getAllTicker24hr();
        for (Map.Entry<String, TickerStatistics> entry : sym2Ticker.entrySet()) {
            String sym = entry.getKey();
            TickerStatistics ticker = entry.getValue();

            if ((Double.parseDouble(ticker.getQuoteVolume()) / 1000000) >= 50
                    && Utils.rateOf2Double(Double.valueOf(ticker.getLastPrice()), Double.valueOf(ticker.getOpenPrice())) <= -0.03) {
                syms.add(sym);
            }
        }
        return syms;
    }
}
