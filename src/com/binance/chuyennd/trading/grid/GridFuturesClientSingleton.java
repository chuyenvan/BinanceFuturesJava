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
package com.binance.chuyennd.trading.grid;

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
public class GridFuturesClientSingleton {

    public static final Logger LOG = LoggerFactory.getLogger(GridFuturesClientSingleton.class);

    public UMFuturesClientImpl umFuturesClient;
    private static volatile GridFuturesClientSingleton INSTANCE = null;

    public static GridFuturesClientSingleton getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new GridFuturesClientSingleton();
            INSTANCE.initClient();
        }
        return INSTANCE;
    }

    private void initClient() {
        umFuturesClient = new UMFuturesClientImpl(PrivateConfig.GRID_API_KEY, PrivateConfig.GRID_SECRET_KEY, PrivateConfig.UM_BASE_URL);
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
//        parameters.put("startTime", String.valueOf(Utils.getStartTimeDayAgo(7)));
//        parameters.put("endTime", String.valueOf(System.currentTimeMillis()));
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
            String respon = GridFuturesClientSingleton.getInstance().umFuturesClient.account().accountInformation(parameters);
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
            String respon = GridFuturesClientSingleton.getInstance().umFuturesClient.account().accountInformation(parameters);
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
            String respon = GridFuturesClientSingleton.getInstance().umFuturesClient.account().cancelOrder(parameters);
            return respon;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return "";
    }
    public static void tracePnlAsymbol() throws ParseException {
        String symbol = "BNBUSDT";
        List<Income> incomes = GridFuturesClientSingleton.getInstance().getPositionHistoryBySymbol(symbol,
                Utils.sdfFileHour.parse("20250214 09:00").getTime(), System.currentTimeMillis());
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
    public Order readOrder(String symbol, String origClientOrderId) {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        parameters.put("symbol", symbol);
        parameters.put("origClientOrderId", origClientOrderId);
        try {
            String respon = GridFuturesClientSingleton.getInstance().umFuturesClient.account().queryOrder(parameters);
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
            String respon = GridFuturesClientSingleton.getInstance().umFuturesClient.account().getIncomeHistory(parameters);
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
            String respon = GridFuturesClientSingleton.getInstance().umFuturesClient.account().getIncomeHistory(parameters);
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

    public static void main(String[] args) throws ParseException {
      tracePnlAsymbol();
    }
}
