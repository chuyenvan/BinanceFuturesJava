/*
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
package com.binance.chuyennd.research;

import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.chuyennd.websocket.ListenPriceBySymbol;
import com.binance.client.model.enums.OrderSide;
import java.io.File;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class ResearchManager {

    public static final Logger LOG = LoggerFactory.getLogger(ResearchManager.class);
    public ConcurrentHashMap<String, ObjectResearch> allOrder;
    private final String FILE_PATH_ORDER_DATA = "storage/research/order.data";
    private static volatile ResearchManager INSTANCE = null;
    private long TIME_REPORT;

    public static ResearchManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new ResearchManager();
            INSTANCE.initClient();

        }
        return INSTANCE;
    }

    private void initClient() {
        TIME_REPORT = Configs.getLong("TimeReportMinute");
        if (new File(FILE_PATH_ORDER_DATA).exists()) {
            this.allOrder = (ConcurrentHashMap<String, ObjectResearch>) Storage.readObjectFromFile(FILE_PATH_ORDER_DATA);
        } else {
            allOrder = new ConcurrentHashMap<>();
        }
        startThreadReport();
    }

    public void startThreadReport() {

        new Thread(() -> {
            Thread.currentThread().setName("ThreadReport");
            LOG.info("Start thread report by research name: {}", new Date());
            while (true) {
                try {
                    // udpate price
                    updatePriceAll();
                    // build report
                    Map<String, List<ObjectResearch>> nameResearch2Info = new HashMap<>();
                    for (Map.Entry<String, ObjectResearch> entry : allOrder.entrySet()) {
                        ObjectResearch orderInfo = entry.getValue();
                        List<ObjectResearch> infos = nameResearch2Info.get(orderInfo.researchName);
                        if (infos == null) {
                            infos = new ArrayList();
                            nameResearch2Info.put(orderInfo.researchName, infos);
                        }
                        infos.add(orderInfo);
                    }
                    for (Map.Entry<String, List<ObjectResearch>> entry : nameResearch2Info.entrySet()) {
                        String name = entry.getKey();
                        List<ObjectResearch> infos = entry.getValue();
                        String msgReport = buildMsgTeleReport(infos, name);
                        Utils.sendSms2Telegram(msgReport);
                    }

                    Storage.writeObject2File(FILE_PATH_ORDER_DATA, allOrder);
                } catch (Exception e) {
                    LOG.error("ERROR during process order active: {}", e);
                    e.printStackTrace();
                }
                try {
                    Thread.sleep(TIME_REPORT * Utils.TIME_MINUTE);
//                    Thread.sleep(10000);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(ResearchManager.class.getName()).log(Level.SEVERE, null, ex);
                }
            }

        }).start();

    }

    public void addNewOrder(String symbol, OrderSide side, String researchName, Double priceOrder) {
        if (allOrder.contains(symbol)) {
            LOG.info("Symbol {} had monitor!", symbol);
            return;
        }
        ObjectResearch info = new ObjectResearch();
        info.symbol = symbol;
        info.side = side;
        info.priceOrder = priceOrder;
        info.lastPrice = priceOrder;
        info.bestPriceByOrder = priceOrder;
        info.researchName = researchName;
        info.timeCreate = System.currentTimeMillis();
        allOrder.put(symbol, info);
        startWSUpdatePriceForOrder(info);
        LOG.info("Add new symbol 2 order: {}", Utils.gson.toJson(info));
    }

    private void startWSUpdatePriceForOrder(ObjectResearch symbol) {
        new ListenPriceBySymbol().startReceivePriceRealTimeBySymbol(symbol);
    }

    public static void main(String[] args) {
        ResearchManager.getInstance().addNewOrder("BTCUSDT", OrderSide.SELL, "TopIncrement", 27665.74);
        ResearchManager.getInstance().addNewOrder("ETHUSDT", OrderSide.SELL, "TopIncrement", 1612.74);
    }

    private String buildMsgTeleReport(List<ObjectResearch> infos, String name) {
        StringBuilder builder = new StringBuilder();
        Double totalRateChange = 0d;
        Integer counterTotal = 0;
        Integer counterIncre = 0;
        Integer counterDecre = 0;
        for (ObjectResearch ticker : infos) {
            builder.append(ticker.symbol).append(" ").append(ticker.side).append(" entry: ").append(ticker.priceOrder);
            Double rate;
            if (ticker.side.equals(OrderSide.BUY)) {
                rate = (ticker.lastPrice - ticker.priceOrder) * 100
                        / ticker.priceOrder;
            } else {
                rate = (ticker.priceOrder - ticker.lastPrice) * 100
                        / ticker.priceOrder;
            }
            totalRateChange += rate;
            counterTotal++;
            if (rate > 0) {
                counterIncre++;
            } else {
                counterDecre++;
            }
            builder.append(" current: ").append(ticker.lastPrice);
            builder.append(" bestPrice: ").append(ticker.bestPriceByOrder);
            builder.append(" rate: ").append(Utils.formatPercent(rate));
            builder.append("\n");
        }
        return name + " : " + counterTotal + " = " + counterIncre + " + " + counterDecre + " -> " + totalRateChange + "\n" + builder.toString();
    }

    private void updatePriceAll() {
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (ticker.getLastPrice().equals(ticker.getHighPrice())) {
                LOG.info("Symbol price api erorr: {}", ticker.getSymbol());
            } else {
                // only get pair with usdt
                if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                    ObjectResearch orderInfo = allOrder.get(ticker.getSymbol());
                    if (orderInfo != null) {
                        orderInfo.updateLastPrice(Double.parseDouble(ticker.getLastPrice()));
                    }
                }
            }
        }
    }
}
