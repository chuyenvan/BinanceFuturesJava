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
package com.binance.chuyennd.websocket;

import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.model.enums.CandlestickInterval;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class ListenPriceBySymbol {

    public static final Logger LOG = LoggerFactory.getLogger(ListenPriceBySymbol.class);

    public static void main(String[] args) {
//        new ListenPriceBySymbol().startReceivePriceRealTimeBySymbol("BTCUSDT");
//indexKlineCandlestick
        SubscriptionClient client = SubscriptionClient.create();
        client.subscribeCandlestickEvent("BTCUSDT", CandlestickInterval.ONE_MINUTE, ((event) -> {
            LOG.info("Update ticker: {}", Utils.gson.toJson(event));
        }), null);
    }

    public void startReceivePriceRealTimeBySymbol(String symbol) {
        LOG.info("Start listen price: {}", symbol);
        SubscriptionClient client = SubscriptionClient.create();
        client.subscribeSymbolTickerEvent(symbol.toLowerCase(), ((event) -> {
            LOG.info("Update price: {}", Utils.gson.toJson(event));
        }), null);
    }

}
