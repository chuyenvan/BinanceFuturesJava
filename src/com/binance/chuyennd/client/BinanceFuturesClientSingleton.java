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
package com.binance.chuyennd.client;

import com.binance.chuyennd.utils.Utils;
import com.binance.client.examples.constants.PrivateConfig;
import com.binance.client.model.trade.*;
import com.binance.connector.futures.client.impl.UMFuturesClientImpl;
import com.google.gson.internal.LinkedTreeMap;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

/**
 *
 * @author pc
 */
public class BinanceFuturesClientSingleton {

    public static final Logger LOG = LoggerFactory.getLogger(BinanceFuturesClientSingleton.class);

    public UMFuturesClientImpl umFuturesClient;
    private static volatile BinanceFuturesClientSingleton INSTANCE = null;

    public static BinanceFuturesClientSingleton getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new BinanceFuturesClientSingleton();
            INSTANCE.initClient();
        }
        return INSTANCE;
    }

    private void initClient() {
        umFuturesClient = new UMFuturesClientImpl(PrivateConfig.API_KEY, PrivateConfig.SECRET_KEY, PrivateConfig.UM_BASE_URL);
    }

    private void positionMode() {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();

        try {
            String respon = umFuturesClient.account().getCurrentPositionMode(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                System.out.println(respon);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    private void getCommissionRate() {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("symbol", "BTCUSDT");
        try {
            String respon = umFuturesClient.account().getCommissionRate(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                System.out.println(respon);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    private static void tracePnlAll() throws ParseException {

        Map<String, Double> symbol2Pnl = new HashMap<>();
        int page = 0;
        while (true) {
            page++;
            List<Income> incomes = BinanceFuturesClientSingleton.getInstance().getAllPositionHistory(
                    Utils.sdfFileHour.parse("20240306 04:00").getTime(), System.currentTimeMillis(), page);
            if (!incomes.isEmpty()) {
                LOG.info("{} {} {}", page, incomes.get(0).getSymbol(), Utils.normalizeDateYYYYMMDDHHmm(incomes.get(0).getTime()));
                for (Income income : incomes) {
                    Double total = symbol2Pnl.get(income.getSymbol());
                    if (total == null) {
                        total = 0d;
                    }
                    total += income.getIncome().doubleValue();
                    symbol2Pnl.put(income.getSymbol(), total);
                }
            } else {
                break;
            }
        }
        for (Map.Entry<String, Double> entry : symbol2Pnl.entrySet()) {
            Double pnl = entry.getValue();
            String symbol = entry.getKey();
            LOG.info("{} {}", symbol, pnl);
        }
    }

    private static void tracePnlAsymbol() throws ParseException {
        String symbol = "SANDUSDT";
        List<Income> incomes = BinanceFuturesClientSingleton.getInstance().getPositionHistoryBySymbol(symbol,
                Utils.sdfFileHour.parse("20241126 07:00").getTime(), System.currentTimeMillis());
        Double total = 0d;
        Double REALIZED_PNL = 0d;
        Double FUNDING_FEE = 0d;
        Double COMMISSION = 0d;
        for (Income income : incomes) {
            total += income.getIncome().doubleValue();
            if (StringUtils.equals(income.getIncomeType(), "REALIZED_PNL")) {
                REALIZED_PNL += income.getIncome().doubleValue();
            }
            if (StringUtils.equals(income.getIncomeType(), "COMMISSION")) {
                COMMISSION += income.getIncome().doubleValue();
            }
            if (StringUtils.equals(income.getIncomeType(), "FUNDING_FEE")) {
                FUNDING_FEE += income.getIncome().doubleValue();
            }
            LOG.info("{} {} {} {} {} ", income.getSymbol(), income.getAsset(), Utils.normalizeDateYYYYMMDDHHmm(income.getTime()),
                    income.getIncomeType(), income.getIncome().doubleValue());
        }
        Double rateF = FUNDING_FEE * 100 / REALIZED_PNL;
        Double rateC = COMMISSION * 100 / REALIZED_PNL;
        LOG.info("{} -> Pnl:{} total:{} Fundding:{} {}% Commission:{} {}%", symbol,
                Utils.formatMoneyNew(total), Utils.formatMoneyNew(REALIZED_PNL), Utils.formatMoneyNew(FUNDING_FEE),
                Utils.formatMoneyNew(rateF), Utils.formatMoneyNew(COMMISSION), Utils.formatMoneyNew(rateC));
    }

    public PositionRisk getPositionInfo(String symbol) {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("symbol", symbol);
        try {
            String result = umFuturesClient.account().positionInformation(parameters);
            if (StringUtils.isNotEmpty(result)) {
                List<LinkedTreeMap> pos = Utils.gson.fromJson(result, List.class);
                if (pos != null && !pos.isEmpty()) {
                    PositionRisk po = Utils.gson.fromJson(pos.get(0).toString(), PositionRisk.class);
                    return po;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public List<PositionRisk> getAllPositionInfos() {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        List<PositionRisk> positions = new ArrayList<>();
        try {
            String respon = umFuturesClient.account().positionInformation(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                List<LinkedTreeMap> list = Utils.gson.fromJson(respon, List.class);
                for (LinkedTreeMap linkedTreeMap : list) {
                    try {
                        positions.add(Utils.gson.fromJson(Utils.toJson(linkedTreeMap), PositionRisk.class));
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return positions;
    }

    public List<Order> getAllOpenOrderInfos() {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        List<Order> openOrders = new ArrayList<>();
        try {
            String respon = umFuturesClient.account().currentAllOpenOrders(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                List<LinkedTreeMap> list = Utils.gson.fromJson(respon, List.class);
                for (LinkedTreeMap linkedTreeMap : list) {
                    try {
                        openOrders.add(Utils.gson.fromJson(Utils.toJson(linkedTreeMap), Order.class));
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return openOrders;
    }

    public static void main(String[] args) throws ParseException {
//        String symbol = "AMBUSDT";
//        System.out.println(Utils.toJson(BinanceFuturesClientSingleton.getInstance().getOpenOrders(symbol)));
//        System.out.println(Utils.toJson(BinanceFuturesClientSingleton.getInstance().getOpenOrders(symbol)));
//        System.out.println(BinanceFuturesClientSingleton.getInstance().getAllPositionInfos().size());
//        System.out.println(Utils.toJson(BinanceFuturesClientSingleton.getInstance().getAllOpenOrderInfos().size()));
//        Set<String> allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS);
//        System.out.println(allSymbol.size());
//        for (String symbol : allSymbol) {
//        Set<String> symbolLocks = BinanceFuturesClientSingleton.getInstance().getAllSymbolLock();
//        System.out.println(symbolLocks);
        tracePnlAsymbol();
//        System.out.println(Utils.toJson(BinanceFuturesClientSingleton.getInstance().getPositionInfo("ORBSUSDT")));
//        BinanceFuturesClientSingleton.getInstance().positionMode();
//        tracePnlAll();
//        BinanceFuturesClientSingleton.getInstance().getCommissionRate();
//        }
//        System.out.println(Utils.toJson(umInfo));
    }

    public List<Order> getOpenOrders(String symbol) {
        List<Order> results = new ArrayList<>();
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("symbol", symbol);
        try {
            String respon = umFuturesClient.account().currentAllOpenOrders(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                List<LinkedTreeMap> list = Utils.gson.fromJson(respon, List.class);
                if (list != null && !list.isEmpty()) {
                    for (LinkedTreeMap linkedTreeMap : list) {
                        results.add(Utils.gson.fromJson(linkedTreeMap.toString(), Order.class));
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return results;
    }

    public List<Order> getOrders(String symbol) {
        List<Order> results = new ArrayList<>();
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("startTime", String.valueOf(Utils.getStartTimeDayAgo(30)));
        parameters.put("endTime", String.valueOf(System.currentTimeMillis()));
        parameters.put("symbol", symbol);

        try {
            String respon = umFuturesClient.account().allOrders(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                List<LinkedTreeMap> list = Utils.gson.fromJson(respon, List.class);
                if (list != null && !list.isEmpty()) {
                    for (LinkedTreeMap linkedTreeMap : list) {
                        results.add(Utils.gson.fromJson(linkedTreeMap.toString(), Order.class));
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return results;
    }

    public AccountInformation getAccountInfo() {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("symbol", "USDT");
        try {
            String respon = BinanceFuturesClientSingleton.getInstance().umFuturesClient.account().accountInformation(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                AccountInformation accInfo = Utils.gson.fromJson(respon, AccountInformation.class);
                return accInfo;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public Asset getAccountUMInfo() {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("symbol", "USDT");
        try {
            String respon = BinanceFuturesClientSingleton.getInstance().umFuturesClient.account().accountInformation(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                AccountInformation accInfo = Utils.gson.fromJson(respon, AccountInformation.class);
                for (Asset asset : accInfo.getAssets()) {
                    if (StringUtils.equalsIgnoreCase(asset.getAsset(), "usdt")) {
                        return asset;
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public String cancelOrder(String symbol, String origClientOrderId) {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("symbol", symbol);
        parameters.put("origClientOrderId", origClientOrderId);
        try {
            String respon = BinanceFuturesClientSingleton.getInstance().umFuturesClient.account().cancelOrder(parameters);
            return respon;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return "";
    }

    public Order readOrder(String symbol, String origClientOrderId) {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("symbol", symbol);
        parameters.put("origClientOrderId", origClientOrderId);
        try {
            String respon = BinanceFuturesClientSingleton.getInstance().umFuturesClient.account().queryOrder(parameters);
            return Utils.gson.fromJson(respon, Order.class);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private List<Income> getPositionHistoryBySymbol(String symbol, Long startTime, Long endTime) {
        List<Income> results = new ArrayList<>();
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("symbol", symbol);
        parameters.put("startTime", startTime);
        parameters.put("endTime", endTime);
//        parameters.put("incomeType", "REALIZED_PNL");
        try {
            String respon = BinanceFuturesClientSingleton.getInstance().umFuturesClient.account().getIncomeHistory(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                List<LinkedTreeMap> list = Utils.gson.fromJson(respon, List.class);
                if (list != null && !list.isEmpty()) {
                    for (LinkedTreeMap linkedTreeMap : list) {
                        String jsonInconme = linkedTreeMap.toString();
                        jsonInconme = StringUtils.replace(jsonInconme, "tradeId=}", "tradeId=1}");
                        Income inconme = Utils.gson.fromJson(jsonInconme, Income.class);
                        results.add(inconme);
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return results;
    }

    private List<Income> getAllPositionHistory(long startTime, long endTime, int page) {
        List<Income> results = new ArrayList<>();
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("startTime", startTime);
        parameters.put("page", page);
        parameters.put("endTime", endTime);
        parameters.put("incomeType", "REALIZED_PNL");
        try {
            String respon = BinanceFuturesClientSingleton.getInstance().umFuturesClient.account().getIncomeHistory(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                List<LinkedTreeMap> list = Utils.gson.fromJson(respon, List.class);
                if (list != null && !list.isEmpty()) {
                    for (LinkedTreeMap linkedTreeMap : list) {
                        String jsonInconme = linkedTreeMap.toString();
                        jsonInconme = StringUtils.replace(jsonInconme, "tradeId=}", "tradeId=1}");
                        Income inconme = Utils.gson.fromJson(jsonInconme, Income.class);
                        results.add(inconme);
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return results;
    }

    public Set<String> getAllSymbolLock() {
        Set<String> results = new HashSet<>();
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        try {
            String respon = umFuturesClient.account().getTradingRulesIndicators(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                System.out.println(respon);
                Map<String, LinkedTreeMap> infos = Utils.gson.fromJson(respon, Map.class);
                LinkedTreeMap indicators = infos.get("indicators");
                Map<String, LinkedTreeMap> symbol2Info = Utils.gson.fromJson(Utils.toJson(indicators), Map.class);
                if (symbol2Info != null && !symbol2Info.isEmpty()) {
                    LOG.info("List locked : {}", Utils.toJson(symbol2Info.keySet()));
                    return symbol2Info.keySet();
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return results;
    }

    public String getFundingRate() {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        return umFuturesClient.market().fundingRate(parameters);
    }
    public String getFundingRate(String symbol) {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("symbol", symbol);
        return umFuturesClient.market().fundingRate(parameters);
    }
}
