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
package com.binance.chuyennd.funcs;

import com.binance.client.RequestOptions;
import com.binance.client.SyncRequestClient;
import com.binance.client.examples.constants.PrivateConfig;
import com.binance.client.model.market.ExchangeInfoEntry;
import com.binance.client.model.market.ExchangeInformation;
import com.binance.client.model.market.SymbolPrice;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class ClientSingleton {

    public static final Logger LOG = LoggerFactory.getLogger(ClientSingleton.class);
    public SyncRequestClient syncRequestClient;
    private static volatile ClientSingleton INSTANCE = null;

    public static ClientSingleton getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new ClientSingleton();
            INSTANCE.initClient();
        }
        return INSTANCE;
    }

    private void initClient() {
        RequestOptions options = new RequestOptions();
        syncRequestClient = SyncRequestClient.create(PrivateConfig.API_KEY, PrivateConfig.SECRET_KEY,
                options);
    }

    public Double getCurrentPrice(String symbol) {
        List<SymbolPrice> datas = syncRequestClient.getSymbolPriceTicker(symbol);
        if (datas != null && !datas.isEmpty()) {
            return datas.get(0).getPrice().doubleValue();
        }
        return null;
    }

    public Set<String> getAllSymbol() {
        Set<String> symbols = new HashSet<String>();
        ExchangeInformation exchangeInfo = syncRequestClient.getExchangeInformation();
        for (ExchangeInfoEntry symbol : exchangeInfo.getSymbols()) {
            if (StringUtils.endsWithIgnoreCase(symbol.getSymbol(), "usdt")) {
                symbols.add(symbol.getSymbol());
            }
        }
        return symbols;
    }
}
