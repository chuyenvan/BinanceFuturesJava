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

import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class GetTicker24h {

    public static final Logger LOG = LoggerFactory.getLogger(GetTicker24h.class);

    public ConcurrentHashMap<String, TickerStatistics> tickerStatistics = new ConcurrentHashMap();
    private static volatile GetTicker24h INSTANCE = null;

    public static GetTicker24h getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new GetTicker24h();
            INSTANCE.startThreadUpdateTickerStatistics();
        }
        return INSTANCE;
    }

    private void startThreadUpdateTickerStatistics() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateTickerStatistics");
            LOG.info("Start thread UpdateTickerStatistics!");
            while (true) {
                try {
                    String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
                    List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
                    for (Object futurePrice : futurePrices) {
                        TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
                        if (ticker.getLastPrice().equals(ticker.getHighPrice())) {
                            LOG.info("Symbol price api erorr: {}", ticker.getSymbol());
                        } else {
                            tickerStatistics.put(ticker.getSymbol(), ticker);
                        }
                    }
                    Thread.sleep(10 * Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during UpdateTickerStatistics{}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    public static void main(String[] args) {
        System.out.println(GetTicker24h.getInstance().tickerStatistics.get("BTCUSDT"));
    }
}
