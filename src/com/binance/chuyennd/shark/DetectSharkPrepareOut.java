/*
 * The MIT License
 *
 * Copyright 2023 pc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */
package com.binance.chuyennd.shark;

import com.binance.chuyennd.client.GetTicker24h;
import com.binance.chuyennd.object.OrderInfo;
import com.binance.chuyennd.client.OrderManager;
import com.binance.chuyennd.object.PremiumIndex;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class DetectSharkPrepareOut {

    public static final Logger LOG = LoggerFactory.getLogger(DetectSharkPrepareOut.class);
    private final Map<String, PremiumIndex> allSymbolChecking;
    private final Map<String, PremiumIndex> symbolHadOrder;
    private final String FILE_PATH_CHECKING_DATA = "storage/symboldata/checking.data";
    private final String FILE_PATH_HAD_LONGED_DATA = "storage/symboldata/shorted.data";
    public static final String URL_PREMIUM_INDEX = "https://fapi.binance.com/fapi/v1/premiumIndex";
    public static long lastTimeReport = 0;
    public static double RATE_DECRE_TO_LONG;
    public static long TIME_CHECK_SECOND;
    public static double RATE_TO_SHORT;
    public static double BUDGET_PER_ORDER;

    public DetectSharkPrepareOut() {
        RATE_DECRE_TO_LONG = Configs.getDouble("RateDecre2Long");
        TIME_CHECK_SECOND = Configs.getLong("TimeCheck");
        RATE_TO_SHORT = Configs.getDouble("Rate2Short");
        BUDGET_PER_ORDER = Configs.getDouble("budgetPerLong");
        if (new File(FILE_PATH_CHECKING_DATA).exists()) {
            this.allSymbolChecking = (Map<String, PremiumIndex>) Storage.readObjectFromFile(FILE_PATH_CHECKING_DATA);
        } else {
            this.allSymbolChecking = new HashMap<>();
        }
        if (new File(FILE_PATH_HAD_LONGED_DATA).exists()) {
            this.symbolHadOrder = (Map<String, PremiumIndex>) Storage.readObjectFromFile(FILE_PATH_HAD_LONGED_DATA);
        } else {
            this.symbolHadOrder = new HashMap<>();
        }
    }

    public static void main(String[] args) {
        // init ticker 24h statistics
        GetTicker24h.getInstance();
        new DetectSharkPrepareOut().startThreadDetechSharkPrepareOut();
    }

    private void startThreadDetechSharkPrepareOut() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadDetechSharkPrepareOut");
            LOG.info("Start thread detect shark prepare out!");
            while (true) {
                try {
                    // get list suspect by priceChange
                    List<PremiumIndex> suspects = getAllSuspect();
                    Map<String, PremiumIndex> currentTickers = new HashMap<>();
                    for (PremiumIndex suspect : suspects) {
                        currentTickers.put(suspect.symbol, suspect);
                    }
                    OrderManager.getInstance().startThreadManagerOrder(currentTickers);
                    List<String> symbol2Remove = new ArrayList();
                    // send report all shorted method 
                    for (Map.Entry<String, PremiumIndex> entry : symbolHadOrder.entrySet()) {
                        String symbol = entry.getKey();
                        PremiumIndex ticker = entry.getValue();
                        if (System.currentTimeMillis() - ticker.time > Utils.TIME_DAY) {
                            symbol2Remove.add(symbol);
                        }
                    }
                    for (String symbol : symbol2Remove) {
                        symbolHadOrder.remove(symbol);
                        LOG.info("Remove symbol had over time: {}", symbol);
                    }
                    if (!symbolHadOrder.isEmpty() && (System.currentTimeMillis() - lastTimeReport > 30 * Utils.TIME_MINUTE || lastTimeReport == 0)) {
                        lastTimeReport = System.currentTimeMillis();
                        StringBuilder builder = new StringBuilder();
                        Double totalRateChange = 0d;
                        Integer counterTotal = 0;
                        Integer counterIncre = 0;
                        Integer counterDecre = 0;
                        for (Map.Entry<String, PremiumIndex> entry : symbolHadOrder.entrySet()) {
                            String key = entry.getKey();
                            PremiumIndex tickerHadShorted = entry.getValue();
                            PremiumIndex currentTikcer = currentTickers.get(key);
                            builder.append(key).append(" ").append(tickerHadShorted.side).append(" entry: ").append(tickerHadShorted.markPrice);
                            if (currentTikcer != null) {
                                Double rate;
                                if (tickerHadShorted.side.equals(OrderSide.BUY)) {
                                    rate = (Double.valueOf(String.valueOf(currentTikcer.markPrice)) - Double.valueOf(tickerHadShorted.markPrice)) * 100
                                            / Double.parseDouble(tickerHadShorted.markPrice);
                                } else {
                                    rate = (Double.valueOf(tickerHadShorted.markPrice) - Double.valueOf(String.valueOf(currentTikcer.markPrice))) * 100
                                            / Double.parseDouble(tickerHadShorted.markPrice);
                                }
                                totalRateChange += rate;
                                counterTotal++;
                                if (rate > 0) {
                                    counterIncre++;
                                } else {
                                    counterDecre++;
                                }
                                builder.append(" current: ").append(currentTikcer.markPrice);
                                builder.append(" rate: ").append(Utils.formatPercent(rate));
                            }
                            builder.append("\n");
                        }
                        Utils.sendSms2Telegram("All symbol had order: " + counterTotal + " = " + counterIncre + " + " + counterDecre + " -> " + totalRateChange + "\n" + builder.toString());
                    }
                    LOG.info("Get all symbol are suspect: {}", suspects.size());
                    for (PremiumIndex ticker : suspects) {
                        // check had long to continue
                        if (symbolHadOrder.containsKey(ticker.symbol)) {
                            continue;
                        }
                        PremiumIndex maxTicker = allSymbolChecking.get(ticker.symbol);
                        if (maxTicker == null) {
                            allSymbolChecking.put(ticker.symbol, ticker);
                            continue;
                        }
                        if (Double.valueOf(ticker.markPrice) > Double.valueOf(maxTicker.markPrice)) {
                            allSymbolChecking.put(ticker.symbol, ticker);
                        } else {
                            if ((Double.valueOf(maxTicker.markPrice) - Double.valueOf(ticker.markPrice)) * 100 / Double.parseDouble(maxTicker.markPrice) > RATE_DECRE_TO_LONG) {

                                StringBuilder builder = new StringBuilder();
                                OrderSide orderSide = detectOrderSide(ticker.symbol);
                                OrderInfo orderInfo = OrderManager.getInstance().addNewOrder(ticker.symbol, orderSide, BUDGET_PER_ORDER, Double.valueOf(ticker.markPrice));
                                if (orderInfo != null) {
                                    ticker.markPrice = orderInfo.priceEntry.toString();
                                    builder.append("Had order: ").append(orderSide).append(" ").append(ticker.symbol).append(" ").append(Utils.gson.toJson(ticker));
                                    builder.append(" price change from: ").append(maxTicker.markPrice).append(" -> ").append(ticker.markPrice);
                                    ticker.side = orderSide;
                                    symbolHadOrder.put(ticker.symbol, ticker);
                                }
                                Utils.sendSms2Telegram(builder.toString());
                                Storage.writeObject2File(FILE_PATH_CHECKING_DATA, allSymbolChecking);
                                Storage.writeObject2File(FILE_PATH_HAD_LONGED_DATA, symbolHadOrder);
                            }
                        }
                    }
                    Thread.sleep(TIME_CHECK_SECOND * Utils.TIME_SECOND);
                } catch (Exception e) {
                    LOG.error("ERROR during detect shark behavior: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private List<PremiumIndex> getAllSuspect() {
        List<PremiumIndex> indexs = new ArrayList<>();
        try {
            String respon = HttpRequest.getContentFromUrl(URL_PREMIUM_INDEX);
            List<Object> objects = Utils.gson.fromJson(respon, List.class);
            for (Object object : objects) {
                PremiumIndex data = Utils.gson.fromJson(object.toString(), PremiumIndex.class);
                if (StringUtils.endsWithIgnoreCase(data.symbol, "usdt")) {
                    indexs.add(data);
                }
            }
        } catch (Exception e) {
            LOG.info("Error during get all premium index!");
            e.printStackTrace();
        }
        return indexs;
    }

    private static OrderSide detectOrderSide(String symbol) {
        TickerStatistics tickerData = GetTicker24h.getInstance().tickerStatistics.get(symbol);
        if (tickerData != null) {
            LOG.info("Ticker statistics: open {} -> last {}", tickerData.getOpenPrice(), tickerData.getLastPrice());
            if (Double.valueOf(tickerData.getOpenPrice()) < Double.valueOf(tickerData.getLastPrice())) {
                return OrderSide.BUY;
            }
        }
        return OrderSide.SELL;

    }
}
