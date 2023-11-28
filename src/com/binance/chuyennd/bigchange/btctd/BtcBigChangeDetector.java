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
package com.binance.chuyennd.bigchange.btctd;

import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.chuyennd.funcs.OrderHelper;
import com.binance.chuyennd.funcs.TickerHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class BtcBigChangeDetector {

    public static final Logger LOG = LoggerFactory.getLogger(BtcBigChangeDetector.class);
    public static Integer LEVERAGE_TRADING = Configs.getInt("BtcBigLeverageTrading");
    public static Integer BUDGET_PER_ORDER = Configs.getInt("BtcBigBudgetPerOrder");
    public static Double RATE_PROFIT = Configs.getDouble("BtcBigRateProfit");
    public static Double RATE_STOPLOSS = Configs.getDouble("BtcBigRateStopLoss");
    public static final Double RATE_BIG_CHANGE_TD = Configs.getDouble("BtcBigRateBigChangeTD");
    public static final Integer NUMBER_TOP_SYMBOL2TRADE = Configs.getInt("BtcBigNumberSymbol4Trade");

    public static void main(String[] args) {
        new BtcBigChangeDetector().startThreadDetectBigChangeBTCIntervalOneMinute();
//        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE, "CYBERUSDT", "123");
//        System.out.println(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE));
//        new BtcBigChangeDetector().processTradingForList(OrderSide.SELL);
//        Order orderInfo = OrderHelper.readOrderInfo("CYBERUSDT", 1147007976L);
//        OrderHelper.stopLoss(orderInfo, RATE_STOPLOSS);
//        OrderHelper.takeProfit(orderInfo, RATE_PROFIT);
//1147007976
//        System.out.println(RATE_STOPLOSS);
//        Double priceSL = 5 * (1 - RATE_STOPLOSS);
//        System.out.println(priceSL);
    }

    public void processTradingForList(OrderSide orderSide) {
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE)) {
            try {
                Double priceEntryTarget = ClientSingleton.getInstance().getCurrentPrice(symbol);
                Double quantity = Double.valueOf(Utils.normalQuantity2Api(BUDGET_PER_ORDER * LEVERAGE_TRADING / priceEntryTarget));
                Order orderResult = OrderHelper.newOrderMarket(symbol, orderSide, quantity, LEVERAGE_TRADING);
                if (orderResult != null) {
                    PositionRisk pos = PositionHelper.getPositionBySymbol(symbol);
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_POS_MANAGER, symbol, Utils.gson.toJson(pos));
                    String telegramAler = symbol + " bigchangebtc -> " + orderSide + " entry: " + orderResult.getAvgPrice().doubleValue();
                    // create tp sl                    
                    Order slOrder = OrderHelper.stopLoss(orderResult, RATE_STOPLOSS);
                    if (slOrder != null) {
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_ORDER_SL_MANAGER, symbol, Utils.gson.toJson(slOrder));
                    }
                    Order tpOrder = OrderHelper.takeProfit(orderResult, RATE_PROFIT);
                    if (tpOrder != null) {
                        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_ORDER_TP_MANAGER, symbol, Utils.gson.toJson(tpOrder));
                    }
                    Utils.sendSms2Telegram(telegramAler);
                    LOG.info("Add order success:{} {} entry: {} quantity:{} {} {}", orderSide, symbol, orderResult.getAvgPrice().doubleValue(), quantity, new Date(), telegramAler);
                } else {
                    String log = "Add order fail because can not create order symbol: " + symbol;
                    LOG.info(log);
                    Utils.sendSms2Telegram(log);
                }
            } catch (Exception e) {
                LOG.info("Error during create order for {} btcbigchangetrading", symbol);
                e.printStackTrace();
            }
        }
    }

    private void startThreadDetectBigChangeBTCIntervalOneMinute() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadDetectBigChangeBTCIntervalOneMinute");
            LOG.info("Start ThreadDetectBigChangeBTCIntervalOneMinute !");
            Set<String> symbols = new HashSet<>();
            symbols.addAll(TickerHelper.getAllSymbol());
            while (true) {
                try {
                    if (System.currentTimeMillis() % Utils.TIME_MINUTE <= Utils.TIME_SECOND) {
                        LOG.info("Detect bigchane in month kline!");
                        KlineObjectNumber ticker = TickerHelper.getLastTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1M);
                        Double rate = (ticker.priceMax - ticker.priceMin) / ticker.priceMin;
                        if (rate > RATE_BIG_CHANGE_TD) {
                            LOG.info("{} {} {}", "BTCUSDT", rate, Utils.toJson(ticker));
                            OrderSide side = OrderSide.BUY;
                            if (ticker.priceClose < ticker.priceOpen) {
                                side = OrderSide.SELL;
                            }
                            startThreadTradingWithListTradingBefore(side);
                            startThreadExtractAllTopAltChange(ticker, symbols);
                        }
                    }
                    Thread.sleep(Utils.TIME_SECOND);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadDetectBigChangeBTCIntervalOneMinute: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void startThreadExtractAllTopAltChange(KlineObjectNumber ticker, Set<String> symbols) {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadExtractAllTopAltChange");
            LOG.info("Start ThreadExtractAllTopAltChange !");
            try {
                int numberMinuteCheckRateChange = 10;
                Thread.sleep(numberMinuteCheckRateChange * Utils.TIME_MINUTE);
                TreeMap<Double, String> rate2Symbol = new TreeMap<>();
                Map<String, Double> symbol2Rate = new HashMap<>();
                OrderSide side = OrderSide.BUY;
                if (ticker.priceClose < ticker.priceOpen) {
                    side = OrderSide.SELL;
                }
                List<String> symbols4Trade = new ArrayList<>();
                Map<String, KlineObjectNumber> symbol2KlineTarget = new HashMap<>();
                for (String symbol : symbols) {
                    try {
                        List<KlineObjectNumber> tickers = TickerHelper.getTicker(symbol, Constants.INTERVAL_1M);
                        Double maxPrice = null;
                        Double minPrice = null;
                        KlineObjectNumber klineCheckPoint = tickers.get(tickers.size() - 1 - numberMinuteCheckRateChange);
                        symbol2KlineTarget.put(symbol, klineCheckPoint);
                        for (int i = 0; i < numberMinuteCheckRateChange + 1; i++) {
                            KlineObjectNumber kline = tickers.get(tickers.size() - 1 - i);
                            if (maxPrice == null || kline.priceMax > maxPrice) {
                                maxPrice = kline.priceMax;
                            }
                            if (minPrice == null || kline.priceMin < minPrice) {
                                minPrice = kline.priceMin;
                            }
                        }
                        Double rateDown = (klineCheckPoint.priceOpen - minPrice) / klineCheckPoint.priceOpen;
                        Double rateUp = (maxPrice - klineCheckPoint.priceOpen) / klineCheckPoint.priceOpen;
                        Double rateChange = 0d;
                        if (side.equals(OrderSide.BUY)) {
                            rateChange = rateUp;
                            symbol2Rate.put(symbol, rateDown);
                        } else {
                            rateChange = rateDown;
                            symbol2Rate.put(symbol, rateUp);
                        }
                        rate2Symbol.put(rateChange, symbol);
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
                for (Map.Entry<Double, String> entry : rate2Symbol.entrySet()) {
                    Double rate = entry.getKey();
                    String symbol = entry.getValue();
                    if (rate > RATE_PROFIT) {
                        symbols4Trade.add(symbol);
                        LOG.info("{} {} {}", symbol, rate, symbol2Rate.get(symbol));
                    }
                }
                // clear list trade old
                RedisHelper.getInstance().get().del(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE);
                // update list trade new
                for (int i = 0; i < NUMBER_TOP_SYMBOL2TRADE; i++) {
                    String symbol = symbols4Trade.get(symbols4Trade.size() - 1 - i);
                    KlineObjectNumber klineTarget = symbol2KlineTarget.get(symbol);
                    LOG.info("Add symbol new: {} to list trade next btc bigchange", symbol);
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE, symbol, Utils.toJson(klineTarget));
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }

    public void startThreadTradingWithListTradingBefore(OrderSide side) {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadTradingWithListTradingBefore");
            LOG.info("Start thread ThreadTradingWithListTradingBefore!");
            processTradingForList(side);
        }).start();

    }

}
