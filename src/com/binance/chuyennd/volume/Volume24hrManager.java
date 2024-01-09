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
package com.binance.chuyennd.volume;

import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.SubscriptionErrorHandler;
import com.binance.client.exception.BinanceApiException;
import com.binance.client.model.event.SymbolTickerEvent;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class Volume24hrManager {

    public static final Logger LOG = LoggerFactory.getLogger(Volume24hrManager.class);
    public final ConcurrentHashMap<String, Double> symbol2Volume = new ConcurrentHashMap<>();
    public final ConcurrentHashMap<String, Double> symbol2OpenPrice = new ConcurrentHashMap<>();
    private static volatile Volume24hrManager INSTANCE = null;

    public static Volume24hrManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new Volume24hrManager();
            INSTANCE.initData();
            INSTANCE.threadListenVolume();
        }
        return INSTANCE;
    }

    private void threadListenVolume() {
        SubscriptionClient client = SubscriptionClient.create();
        SubscriptionErrorHandler errorHandler = (BinanceApiException exception) -> {
        };
        client.subscribeAllTickerEvent(((event) -> {
            for (SymbolTickerEvent e : event) {
                symbol2Volume.put(e.getSymbol(), e.getTotalTradedQuoteAssetVolume().doubleValue());
                symbol2OpenPrice.put(e.getSymbol(), e.getOpen().doubleValue());
//                LOG.info("{}", Utils.toJson(e));
            }
        }), errorHandler);
    }

    public static void main(String[] args) throws InterruptedException {
        Volume24hrManager.getInstance();
//        TreeMap<Double, String> volume2Symbol = new TreeMap<>();
//
//        for (Map.Entry<String, Double> entry : Volume24hrManager.getInstance().symbol2Volume.entrySet()) {
//            String key = entry.getKey();
//            Double val = entry.getValue();
//            volume2Symbol.put(val, key);
//        }
//        for (Map.Entry<Double, String> entry : volume2Symbol.entrySet()) {
//            Double rate = entry.getKey();
//            String sym = entry.getValue();
//            LOG.info("{} -> {}", sym, rate);
//        }

//        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
//        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
//        for (Object futurePrice : futurePrices) {
//            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
//            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
//                LOG.info(" {} -> {}", ticker.getSymbol(), Double.parseDouble(ticker.getQuoteVolume()));
//            }
//        }
    }

    private void initData() {
        try {
            String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
            List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
            for (Object futurePrice : futurePrices) {
                TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
                if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                    symbol2Volume.put(ticker.getSymbol(), Double.valueOf(ticker.getQuoteVolume()));
                    symbol2OpenPrice.put(ticker.getSymbol(), Double.valueOf(ticker.getOpenPrice()));
                }
            }
        } catch (Exception e) {
        }
    }
}
