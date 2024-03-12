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
import com.binance.client.model.trade.AccountInformation;
import com.binance.client.model.trade.Asset;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import com.binance.connector.futures.client.impl.UMFuturesClientImpl;
import com.google.gson.internal.LinkedTreeMap;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

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

    public List<Order> getAllOrderInfos() {
        LinkedHashMap<String, Object> parameters = new LinkedHashMap<>();
        List<Order> positions = new ArrayList<>();
        try {
            String respon = umFuturesClient.account().currentAllOpenOrders(parameters);
            if (StringUtils.isNotEmpty(respon)) {
                List<LinkedTreeMap> list = Utils.gson.fromJson(respon, List.class);
                for (LinkedTreeMap linkedTreeMap : list) {
                    try {
                        positions.add(Utils.gson.fromJson(Utils.toJson(linkedTreeMap), Order.class));
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

    public static void main(String[] args) {
//        String symbol = "AMBUSDT";
//        System.out.println(Utils.toJson(BinanceFuturesClientSingleton.getInstance().getOpenOrders(symbol)));
//        symbol = "OMUSDT";
//        System.out.println(Utils.toJson(BinanceFuturesClientSingleton.getInstance().getOpenOrders(symbol)));
//        System.out.println(BinanceFuturesClientSingleton.getInstance().getAllPositionInfos().size());
        System.out.println(Utils.toJson(BinanceFuturesClientSingleton.getInstance().getAllOrderInfos().size()));
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
}
