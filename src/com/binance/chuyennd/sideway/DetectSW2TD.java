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
package com.binance.chuyennd.sideway;

import com.binance.chuyennd.position.manager.BTCInfoManager;
import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.chuyennd.funcs.TickerHelper;
import com.binance.chuyennd.object.KlineObject;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Contanst;
import com.binance.client.model.enums.OrderSide;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class DetectSW2TD {

    public static final Logger LOG = LoggerFactory.getLogger(DetectSW2TD.class);
    public Integer LEVERAGE_TRADING = Configs.getInt("LeverageTrading");
    public Integer BUDGET_PER_ORDER = Configs.getInt("BudgetPerOrder");
    public Integer NUMBER_DAY_SIDEWAY = Configs.getInt("NumberDaySideWay");
    public Double RATE_RANGE_TRADING = Configs.getDouble("RateRangeTrading");
    public Double RATE_2TRADING = Configs.getDouble("Rate2Trading");
    public final ConcurrentHashMap<String, SymbolSideWayObject> symbolSideWay2Trading = new ConcurrentHashMap();

    private void detectSW2Trading() {
        try {
            String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
            List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
            for (Object futurePrice : futurePrices) {
                TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
                if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt") && !StringUtils.startsWithIgnoreCase(ticker.getSymbol(), "btc")) {
                    try {
                        // only get symbol over 2 months
                        SymbolSideWayObject objectSideway = getRangeSideWay(ticker.getSymbol());
                        if (objectSideway == null) {
                            continue;
                        }
                        if (objectSideway.rangeSize <= RATE_RANGE_TRADING && objectSideway.rangeSize > 2.1 * RATE_2TRADING) {
                            add2ListTrading(objectSideway);
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void startThreadTrading() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadTrading");
            LOG.info("Start ThreadTrading !");
            while (true) {
                try {
                    Set<String> symbol2Remove = new HashSet<>();
                    LOG.info("Start check price 2 trading for {} symbols", symbolSideWay2Trading.size());
                    for (Map.Entry<String, SymbolSideWayObject> entry : symbolSideWay2Trading.entrySet()) {
                        String symbol = entry.getKey();
                        SymbolSideWayObject sidewayObject = entry.getValue();
                        // check price break out sideway
                        KlineObjectNumber klineToday = TickerHelper.getLastTicker(symbol, Contanst.INTERVAL_1D);
                        if (klineToday.priceMax > sidewayObject.priceMax
                                || klineToday.priceMin < sidewayObject.priceMin) {
                            String log = symbol + " is break out sideway -> not trading";
//                            Utils.sendSms2Telegram(log);
                            LOG.info(log);
                            symbol2Remove.add(symbol);
                            continue;
                        }
                        // check symbol had position running                        
                        if (RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol) != null) {
                            String log = "Symbol " + symbol + " had order active: ";
                            LOG.info(log);
                            continue;
                        }
                        Double currentPrice = ClientSingleton.getInstance().getCurrentPrice(symbol);
                        if (System.currentTimeMillis() - sidewayObject.timeStart > Utils.TIME_DAY
                                || currentPrice > sidewayObject.priceMax
                                || currentPrice < sidewayObject.priceMin) {
                            symbol2Remove.add(symbol);
                            continue;
                        }
                        OrderSide orderSide = null;
                        Double priceEntry = null;
                        if (currentPrice > sidewayObject.priceSignalShort) {
//                            String log = "Short " + symbol + " entry: " + currentPrice + " detail: " + Utils.gson.toJson(sidewayObject);
//                            Utils.sendSms2Telegram(log);
//                            CreatePositionNew.getInstance().addOrderByTarget(symbol, OrderSide.SELL, sidewayObject.priceMax);
//                            LOG.info(log);
                            orderSide = OrderSide.SELL;
                            priceEntry = sidewayObject.priceMax;
                        }
                        if (currentPrice < sidewayObject.priceSignalLong) {
//                            if (TickerHelper.getCurrentTrendWithInterval(Contanst.SYMBOL_PAIR_BTC, Contanst.INTERVAL_15M).equals(OrderSide.BUY)) {
//                                String log = "Long " + symbol + " entry: " + currentPrice + " detail: " + Utils.gson.toJson(sidewayObject);
//                                Utils.sendSms2Telegram(log);
//                                CreatePositionNew.getInstance().addOrderByTarget(symbol, OrderSide.BUY, sidewayObject.priceMin);
//                                LOG.info(log);
//                            } else {
//                                LOG.info("Not trading because not match trend with BTC! {}", symbol);
//                            }
                            orderSide = OrderSide.BUY;
                            priceEntry = sidewayObject.priceMin;
                        }
                        if (orderSide != null) {
                            OrderSide currentTrendBtc = TickerHelper.getCurrentTrendWithInterval(Contanst.SYMBOL_PAIR_BTC, Contanst.INTERVAL_15M);
                            OrderSide longTrendBtc = BTCInfoManager.getLongTrendBtc();
                            if (currentTrendBtc.equals(orderSide)
                                    && orderSide.equals(longTrendBtc)) {
                                String log = orderSide + " " + symbol + " entry: " + currentPrice + " detail: " + Utils.gson.toJson(sidewayObject);
                                Utils.sendSms2Telegram(log);
                                PositionHelper.getInstance().addOrderByTarget(symbol, orderSide, priceEntry);
                                LOG.info(log);
                            } else {
                                LOG.info("Not trading because not match trend with BTC! {} {} {} {}", orderSide, symbol, currentTrendBtc, longTrendBtc);
                            }
                        }
                    }
                    for (String symbol : symbol2Remove) {
                        LOG.info("Remove symbol break out side way: currentPrice: {} detail: {}", Utils.gson.toJson(symbolSideWay2Trading.get(symbol)));
                        symbolSideWay2Trading.remove(symbol);
                    }
                    Thread.sleep(60 * Utils.TIME_SECOND);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadTrading: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void startThreadDetectSideWay() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadDetectSideWay");
            LOG.info("Start ThreadDetectSideWay !");
            while (true) {
                try {
                    detectSW2Trading();
                    Thread.sleep(12 * Utils.TIME_HOUR);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadDetectSideWay: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private SymbolSideWayObject getRangeSideWay(String symbol) {
        List<KlineObjectNumber> allKlines = TickerHelper.getTicker(symbol, Contanst.INTERVAL_1D);
        try {
            if (allKlines.size() > 31) {
                Double maxPrice = 0d;
                Double minPrice = 0d;
                KlineObjectNumber klineToday = allKlines.get(allKlines.size() - 1);
                KlineObjectNumber klineYesterday = allKlines.get(allKlines.size() - 2);
                for (int i = 0; i < NUMBER_DAY_SIDEWAY; i++) {
                    KlineObjectNumber kline = allKlines.get(allKlines.size() - i - 1);
                    if (maxPrice < kline.priceMax) {
                        maxPrice = kline.priceMax;
                    }
                    if (minPrice > kline.priceMin || minPrice == 0) {
                        minPrice = kline.priceMin;
                    }
                }
                Double result = (maxPrice - minPrice) / maxPrice;
                // check today is trend not trading
                if (klineToday.priceMax >= maxPrice
                        || klineToday.priceMin <= minPrice) {
//                        || Double.valueOf(klineYesterday.priceMax) <= maxPrice
//                        || Double.valueOf(klineYesterday.priceMin) <= minPrice) {
                    String log = symbol + " is trend -> not trading";
//                    Utils.sendSms2Telegram(log);
                    LOG.info(log);
                    return null;
                }
//                LOG.info("{} {}: {} -> {} ", symbol, result, minPrice, maxPrice);
                SymbolSideWayObject resultObject = new SymbolSideWayObject();
                resultObject.symbol = symbol;
                resultObject.priceMax = maxPrice;
                resultObject.priceMin = minPrice;
                resultObject.priceSignalLong = minPrice + RATE_2TRADING * minPrice;
                resultObject.priceSignalShort = maxPrice - RATE_2TRADING * maxPrice;
                resultObject.rangeSize = result;
                OrderSide sidePrefer = getPreferSide(klineToday, klineYesterday, maxPrice, minPrice);
                resultObject.preferSide = sidePrefer;
                resultObject.timeStart = System.currentTimeMillis();
                return resultObject;
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private void startThreadDetectSideWayAndTrading() {
        LOG.info("Start process trading with sideway: leverage: {} budget: {} rangeRate: {} rateTrading: {} numberDayCheckSideway: {}",
                LEVERAGE_TRADING, BUDGET_PER_ORDER, RATE_RANGE_TRADING, RATE_2TRADING, NUMBER_DAY_SIDEWAY);
        //detect sideway and put lish trading
        startThreadDetectSideWay();
        startThreadTrading();

    }

    private void add2ListTrading(SymbolSideWayObject objectSideway) {
        if (symbolSideWay2Trading.contains(objectSideway.symbol)) {
            LOG.info("Add list trading fail becase symbol had trading: {}", Utils.gson.toJson(objectSideway));
            return;
        }
        LOG.info("Add {} to list trading success! {}", objectSideway.symbol, Utils.gson.toJson(objectSideway));
        symbolSideWay2Trading.put(objectSideway.symbol, objectSideway);
    }

    private OrderSide getPreferSide(KlineObjectNumber klineToday, KlineObjectNumber klineYesterday, Double maxPrice, Double minPrice) {
        OrderSide result = OrderSide.BUY;
        Double maxNearPrice = klineToday.priceMax;
        if (klineYesterday.priceMax > maxNearPrice) {
            maxNearPrice = klineYesterday.priceMax;
        }
        Double minNearPrice = klineToday.priceMax;
        if (klineYesterday.priceMax < minNearPrice) {
            minNearPrice = klineYesterday.priceMax;
        }
        // prefer Long after check prefer Short
        if ((maxPrice - maxNearPrice) / maxPrice < 0.005) {
            result = OrderSide.BUY;
        } else {
            if ((minNearPrice - minPrice) / minPrice < 0.005) {
                result = OrderSide.SELL;
            }
        }
        return result;
    }

    public static void main(String[] args) {

        new DetectSW2TD().startThreadDetectSideWayAndTrading();
    }
}
