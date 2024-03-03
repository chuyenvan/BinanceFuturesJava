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

    public static void main(String[] args) {
        String symbol = "AMBUSDT";
        System.out.println(Utils.toJson(BinanceFuturesClientSingleton.getInstance().getOpenOrders(symbol)));
        symbol = "OMUSDT";
        System.out.println(Utils.toJson(BinanceFuturesClientSingleton.getInstance().getOpenOrders(symbol)));

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
}
