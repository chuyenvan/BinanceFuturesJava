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
package com.binance.chuyennd.signal.tradingview;

import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.statistic24hr.Volume24hrManager;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.trading.SymbolTradingManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.google.gson.internal.LinkedTreeMap;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Date;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;

import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @author pc
 */
public class SignalTradingViewManager {

    public static final Logger LOG = LoggerFactory.getLogger(SignalTradingViewManager.class);
    //    public Set<? extends String> allSymbol;
    public Double RATE_TARGET = Configs.getDouble("RATE_TARGET");

    //    public static final String URL_SIGNAL_TRADINGVIEW = "http://103.157.218.242:8002/";
    public static final String URL_SIGNAL_TRADINGVIEW = "http://172.25.80.128:8002/";
    //    public static final String URL_SIGNAL_EDUCA = "http://172.25.80.128:8002/";
    public static final String URL_SIGNAL_TRADINGVIEW_BAK = "https://tool.edupia.vn/tool/offline/signal?s=";

    public ConcurrentHashMap<String, OrderTargetInfoTestSignal> symbol2Orders = new ConcurrentHashMap<>();

    public static void main(String[] args) throws InterruptedException {
//        new RedisSTWManager().start();
        System.out.println(new SignalTradingViewManager().getRecommendation("RVNUSDT"));

//        SignalTradingViewManager test = new SignalTradingViewManager();
//        Set<String> hashSet = new HashSet<String>();
//
//        for (String symbol : TickerFuturesHelper.getAllSymbol()) {
//            if (true) {
//
//            }
//            String signal = test.getReconmendation(symbol);
//            if (signal == null) {
//                hashSet.add(symbol);
//            } else {
//                LOG.info("{} -> {}", symbol, signal);
//            }
//
//        }
//        System.out.println(hashSet);
//        System.out.println(THelper.getAllSymbol());
    }

    public void start() throws InterruptedException {

        checkSignalStrong2Trading();
        checkSignalStrong2TradingBackup();
    }



    public boolean isTimeCheckBalance() {
        return Utils.getCurrentHour() == 0 && Utils.getCurrentMinute() == 0;
    }

    private void checkSignalStrong2Trading() {
        new Thread(() -> {
            Thread.currentThread().setName("SignalStrong2Trading");
            LOG.info("Start thread SignalStrong2Trading!");
            while (true) {
                try {
                    int numberPosRunning = RedisHelper.getInstance().smembers(RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING).size();

                    getStrongSignal2Trading();
                } catch (Exception e) {
                    LOG.error("ERROR during SignalStrong2Trading: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    ex.printStackTrace();
                }
            }
        }).start();
    }

    private void getStrongSignal2Trading() {
        long startTime = System.currentTimeMillis();
        LOG.info("Start detect symbol strong signal: {}", new Date());
        Set<String> symbol2Trade = SymbolTradingManager.getInstance().getAllSymbol2TradingSignal();
        for (String symbol : symbol2Trade) {
            try {
                strongSignal2TradeBySymbol(symbol);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        long timeDetect = (System.currentTimeMillis() - startTime) / Utils.TIME_SECOND;
        if (timeDetect > 100) {
            restartDocker();
            Utils.sendSms2Skype("Check Signal API: time detect too large -> " + timeDetect + " second");
        }
        LOG.info("Finish detect symbol strong signal! {}s", timeDetect);
    }

    private void getStrongSignal2TradingBackup() {
        long startTime = System.currentTimeMillis();
        LOG.info("Start detect symbol strong signal backup: {}", new Date(startTime));
        Set<String> symbol2Trade = SymbolTradingManager.getInstance().getAllSymbol2TradingSignal();
        for (String symbol : symbol2Trade) {
            try {
                String side = getRecommendationBackup(symbol);
                if (StringUtils.isNotEmpty(side)) {
                    OrderSide sideSignal = OrderSide.BUY;
                    if (StringUtils.equalsIgnoreCase(side, "sell")) {
                        sideSignal = OrderSide.SELL;
                    }
                    if (sideSignal.equals(OrderSide.BUY)) {
                        addOrderTrading(symbol, sideSignal);
                    }
                }
            } catch (Exception e) {
                LOG.info("Error during get signal for {}", symbol);
                e.printStackTrace();
            }
        }
        LOG.info("Finish detect symbol strong signal backup: {}s", (System.currentTimeMillis() - startTime) / Utils.TIME_SECOND);
    }

    private void strongSignal2TradeBySymbol(String symbol) {
        OrderSide sideSignal = getStrongSignalASymbol(symbol);
        if (sideSignal != null && sideSignal.equals(OrderSide.BUY)) {
            addOrderTrading(symbol, sideSignal);
        }
    }

    private void addOrderTrading(String symbol, OrderSide sideSignal) {
        Double priceEntry = ClientSingleton.getInstance().getCurrentPrice(symbol);
        Double priceTarget = Utils.calPriceTarget(symbol, priceEntry, sideSignal, RATE_TARGET);
//        String log = sideSignal + " " + symbol + " by signal tradingview entry: " + priceEntry + " target: " + priceTarget
//                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis());
//        Utils.sendSms2Telegram(log);
        Double quantity = Utils.calQuantity(BudgetManager.getInstance().getBudget(),
                BudgetManager.getInstance().getLeverage(), priceEntry, symbol);
        if (quantity != null && quantity != 0) {
            OrderTargetInfoTestSignal orderTrade = new OrderTargetInfoTestSignal(OrderTargetStatus.REQUEST, priceEntry,
                    priceTarget, quantity, BudgetManager.getInstance().getLeverage(), symbol,
                    System.currentTimeMillis(), System.currentTimeMillis(),
                    sideSignal);
//            RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));

            LOG.info("{} {} entry:{} target:{} quantity:{} ", sideSignal,
                    symbol, priceEntry, priceTarget, quantity);
        } else {
            LOG.info("{} {} q false", symbol, quantity);
        }

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

    private String getRecommendation(String symbol) {
        String result = "";
        try {
            String respon = getRecommendationRaw(symbol);
            List<LinkedTreeMap> responObjects = Utils.gson.fromJson(respon, List.class);
            if (responObjects != null && !responObjects.isEmpty()) {
                String sideSignal = responObjects.get(0).get("recommendation").toString();
                if (StringUtils.contains(sideSignal, "STRONG")) {
                    result = sideSignal.split("_")[1];
                }
                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_TRADINGVIEW_FAIL, symbol);
            } else {
                Double rate24hr = Volume24hrManager.getInstance().symbol2RateChangeWithOpen.get(symbol);
                // not tradingview ta -> buy when rate change 24hr > 1%
                if (rate24hr > 0.01) {
                    RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_TRADINGVIEW_FAIL, symbol);
                    result = "BUY";
                    return result;
                } else {
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_TRADINGVIEW_FAIL, symbol, String.valueOf(System.currentTimeMillis()));
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return result;
    }

    private String getRecommendationRaw(String symbol) {
        String urlSignal = URL_SIGNAL_TRADINGVIEW + symbol;
        int timeout = 3000;
        return HttpRequest.getContentFromUrl(urlSignal, timeout);
    }

    private String getRecommendationBackup(String symbol) {
        try {
            String urlSignal = URL_SIGNAL_TRADINGVIEW_BAK + symbol;
            String respon = HttpRequest.getContentFromUrl(urlSignal);
            Map<String, String> responMap = Utils.gson.fromJson(respon, Map.class);
            List<LinkedTreeMap> responObjects = Utils.gson.fromJson(responMap.get("data"), List.class);
            if (responObjects != null && !responObjects.isEmpty()) {
                for (LinkedTreeMap responObject : responObjects) {
                    String sideSignal = responObject.get("recommendation").toString();
                    if (StringUtils.contains(sideSignal, "STRONG")) {
                        return sideSignal.split("_")[1];
                    }
                }
            } else {
                return null;
            }
        } catch (Exception e) {
            Utils.sendSms2Telegram("<b>Check docker tradingview backup!<\b>");
            LOG.info("<b>Check docker tradingview backup!<\b>");
            e.printStackTrace();
        }
        return "";
    }

    private void checkSignalStrong2TradingBackup() {
        new Thread(() -> {
            Thread.currentThread().setName("SignalStrong2TradingBackup");
            LOG.info("Start SignalStrong2TradingBackup !");
            while (true) {
                try {
                    int numberPosRunning = RedisHelper.getInstance().smembers(RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING).size();
                    getStrongSignal2TradingBackup();
                } catch (Exception e) {
                    LOG.error("ERROR during SignalStrong2TradingBackup: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(SignalTradingViewManager.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private void restartDocker() {
        try {
            String s;
            Process p = Runtime.getRuntime().exec("docker restart d76683cff6dd");
            BufferedReader br = new BufferedReader(
                    new InputStreamReader(p.getInputStream()));
            while ((s = br.readLine()) != null) {
                System.out.println("line: " + s);
            }
            Utils.sendSms2Skype(s + " had restart!");
            p.waitFor();
            p.destroy();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

}
