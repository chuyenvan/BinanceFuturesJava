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

import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.FuturesRules;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.google.gson.internal.LinkedTreeMap;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class SignalTradingViewManager {

    public static final Logger LOG = LoggerFactory.getLogger(SignalTradingViewManager.class);
    public Set<? extends String> allSymbol;
    public Double RATE_TARGET_SIGNAL = Configs.getDouble("RATE_TARGET_SIGNAL");
    public static final Integer MAX_POS_TRADING = Configs.getInt("MAX_POS_TRADING");
    public static final Integer MAX_VOLUME_TRADING = Configs.getInt("MAX_VOLUME_TRADING");
    public static final String URL_SIGNAL_TRADINGVIEW = "http://103.157.218.242:8002/";
    public static final String URL_SIGNAL_TRADINGVIEW_BAK = "https://tool.edupia.vn/tool/offline/signal?s=";

    public ConcurrentHashMap<String, OrderTargetInfo> symbol2Orders = new ConcurrentHashMap<>();

    public static void main(String[] args) throws InterruptedException {
//        new RedisSTWManager().start();
        new SignalTradingViewManager().getStrongSignal2TradingBackup();
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
        initData();
        checkSignalStrong2Trading();
        checkSignalStrong2TradingBackup();
    }

    private void initData() throws InterruptedException {
        allSymbol = TickerFuturesHelper.getAllSymbol();
        allSymbol.removeAll(Constants.specialSymbol);
        LOG.info("Have {} s avalible!", allSymbol.size());
        ClientSingleton.getInstance();

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
                    int numberPosRunning = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER).size();
                    if (numberPosRunning > MAX_POS_TRADING) {
                        LOG.info("Not trading because max pos: {} {}", numberPosRunning, MAX_POS_TRADING);
                        continue;
                    }
                    getStrongSignal2Trading();
                } catch (Exception e) {
                    LOG.error("ERROR during SignalStrong2Trading: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(Utils.TIME_MINUTE);
                } catch (InterruptedException ex) {
                    ex.printStackTrace();
                }
            }
        }).start();
    }

    private Set<String> getAllSymbolVolumeOverVolumeNotTrade() {
        Set<String> syms = new HashSet<>();
        Map<String, Double> sym2Volume = TickerFuturesHelper.getAllVolume24hr();
        for (Map.Entry<String, Double> entry : sym2Volume.entrySet()) {
            String sym = entry.getKey();
            Double volume = entry.getValue();
            if ((volume / 1000000) >= MAX_VOLUME_TRADING) {
                syms.add(sym);
            }
        }
        return syms;
    }

    private void getStrongSignal2Trading() {
        long startTime = System.currentTimeMillis();
        LOG.info("Start detect symbol strong signal: {}", new Date());
        Set<String> symbolsVolumeOverVolumeNotTrade = getAllSymbolVolumeOverVolumeNotTrade();
        for (String symbol : allSymbol) {
            try {
                // check symbol had position running
                Set<String> symbolsTrading = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER);
                if (symbolsTrading.contains(symbol)
                        || symbolsTrading.size() > MAX_POS_TRADING
                        || symbolsVolumeOverVolumeNotTrade.contains(symbol)
                        || FuturesRules.getInstance().getSymsLocked().contains(symbol)) {
                    continue;
                }
                strongSignal2TradeBySymbol(symbol);

            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        long timeDetect = (System.currentTimeMillis() - startTime) / Utils.TIME_SECOND;
        if (timeDetect > 30) {
            restartDocker();
            Utils.sendSms2Skype("Check Signal API: time detect too large -> " + timeDetect + " second");
        }
        LOG.info("Finish detect symbol strong signal! {}s", timeDetect);
    }

    private void getStrongSignal2TradingBackup() {

        LOG.info("Start detect symbol strong signal backup: {}", new Date());
        Set<String> symbolsVolumeOverVolumeNotTrade = getAllSymbolVolumeOverVolumeNotTrade();
        Set<String> symbolsTrading = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER);
        Set<String> symbol2Trade = new HashSet<>();
//        symbol2Trade.addAll(allSymbol);
        symbol2Trade.addAll(TickerFuturesHelper.getAllSymbol());

        symbol2Trade.removeAll(Constants.specialSymbol);
        symbol2Trade.removeAll(symbolsVolumeOverVolumeNotTrade);
        symbol2Trade.removeAll(symbolsTrading);
        Set<Set<String>> symbol2Trades = Utils.subSet(symbol2Trade, 1);
        for (Set<String> symbols2T : symbol2Trades) {
            try {
                Map<String, String> symbol2Side = getReconmendationBackup(symbols2T);
                if (symbol2Side == null) {
                    continue;
                }
                for (Map.Entry<String, String> entry : symbol2Side.entrySet()) {
                    String symbol = entry.getKey();
                    String side = entry.getValue();
                    OrderSide sideSignal = OrderSide.BUY;
                    if (StringUtils.equalsIgnoreCase(side, "sell")) {
                        sideSignal = OrderSide.SELL;
                    }
                    if (sideSignal.equals(OrderSide.BUY)) {
                        addOrderTrading(symbol, sideSignal);
                    }
                }
            } catch (Exception e) {
                LOG.info("Error during get signal for {}", symbols2T.toString());
                e.printStackTrace();
            }
        }
    }

    private void strongSignal2TradeBySymbol(String symbol) {
        OrderSide sideSignal = getStrongSignalASymbol(symbol);
        if (sideSignal != null && sideSignal.equals(OrderSide.BUY)) {
            addOrderTrading(symbol, sideSignal);
        }
    }

    private void addOrderTrading(String symbol, OrderSide sideSignal) {
        Double priceEntry = ClientSingleton.getInstance().getCurrentPrice(symbol);
        Double priceTarget = Utils.calPriceTarget(symbol, priceEntry, sideSignal, RATE_TARGET_SIGNAL);
//        String log = sideSignal + " " + symbol + " by signal tradingview entry: " + priceEntry + " target: " + priceTarget
//                + " time:" + Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis());
//        Utils.sendSms2Telegram(log);
        Double quantity = Utils.calQuantity(BudgetManager.getInstance().getBudget(), BudgetManager.getInstance().getLeverage(), priceEntry, symbol);
        if (quantity != null && quantity != 0) {
            OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, priceEntry,
                    priceTarget, quantity, BudgetManager.getInstance().getLeverage(), symbol,
                    System.currentTimeMillis(), System.currentTimeMillis(),
                    sideSignal, Constants.TRADING_TYPE_SIGNAL);
            RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
            LOG.info("{} {} entry:{} target:{} quantity:{}", sideSignal.toString().charAt(0),
                    symbol.toLowerCase().replace("usdt", ""), priceEntry, priceTarget, quantity);
        } else {
            LOG.info("{} {} q false", symbol, quantity);
        }

    }

    private OrderSide getStrongSignalASymbol(String symbol) {
        try {
//            String signalRecommendation = getReconmendation(symbol);
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

    private String getReconmendation(String symbol) {
        String result = "";
        try {
            String urlSignal = URL_SIGNAL_TRADINGVIEW + symbol;
            int timeout = 3000;
            String respon = HttpRequest.getContentFromUrl(urlSignal, timeout);
            List<LinkedTreeMap> responObjects = Utils.gson.fromJson(respon, List.class);
            if (responObjects != null && !responObjects.isEmpty()) {
                String sideSignal = responObjects.get(0).get("recommendation").toString();
                if (StringUtils.contains(sideSignal, "STRONG")) {
                    result = sideSignal.split("_")[1];
                }
            } else {
                return null;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return result;
    }

    private Map<String, String> getReconmendationBackup(Set<String> symbols) {
        Map<String, String> sym2Side = new HashMap<>();
        try {
            StringBuilder builder = new StringBuilder();
            for (String symbol : symbols) {
                builder.append(symbol).append(",");
            }
            builder.setLength(builder.length() - 1);
            String urlSignal = URL_SIGNAL_TRADINGVIEW_BAK + builder.toString();

            String respon = HttpRequest.getContentFromUrl(urlSignal);
            Map<String, String> responMap = Utils.gson.fromJson(respon, Map.class);
            List<LinkedTreeMap> responObjects = Utils.gson.fromJson(responMap.get("data"), List.class);
            if (responObjects != null && !responObjects.isEmpty()) {
                for (LinkedTreeMap responObject : responObjects) {
                    String sideSignal = responObject.get("recommendation").toString();
                    if (StringUtils.contains(sideSignal, "STRONG")) {
                        sym2Side.put(responObject.get("pair").toString(), sideSignal.split("_")[1]);
                    }
                }
            } else {
                return null;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return sym2Side;
    }

    private void checkSignalStrong2TradingBackup() {
        new Thread(() -> {
            Thread.currentThread().setName("SignalStrong2TradingBackup");
            LOG.info("Start SignalStrong2TradingBackup !");
            while (true) {
                try {
                    Thread.sleep(5 * Utils.TIME_SECOND);
                    int numberPosRunning = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER).size();
                    if (numberPosRunning > MAX_POS_TRADING) {
                        LOG.info("Not trading because max pos: {} {}", numberPosRunning, MAX_POS_TRADING);
                        continue;
                    }
                    getStrongSignal2TradingBackup();
                } catch (Exception e) {
                    LOG.error("ERROR during SignalStrong2TradingBackup: {}", e);
                    e.printStackTrace();
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
