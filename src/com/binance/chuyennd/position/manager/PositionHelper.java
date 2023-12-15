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
package com.binance.chuyennd.position.manager;

import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.chuyennd.funcs.OrderHelper;
import com.binance.chuyennd.funcs.TickerHelper;
import com.binance.chuyennd.object.KlineObject;
import com.binance.chuyennd.object.TickerStatistics;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.NewOrderRespType;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderType;
import com.binance.client.model.enums.TimeInForce;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;

import java.util.Date;
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
public class PositionHelper {

    public static final Logger LOG = LoggerFactory.getLogger(OrderHelper.class);
    private static volatile PositionHelper INSTANCE = null;

    public Integer LEVERAGE_TRADING = Configs.getInt("LeverageTrading");
    public Integer BUDGET_PER_ORDER = Configs.getInt("BudgetPerOrder");
    public Double RATE_CHECK_SIGNAL_TARGET = Configs.getDouble("RateCheckSignalTarget");
    public Double LIMIT_ORDER_TRADING = Configs.getDouble("LitmitOrderTrading");

    public static final String URL_TICKER_1D = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&interval=1w";

    public int counter = 0;
    public static final Set<String> symbolAvalible2Trading = new HashSet<>();

    public static PositionHelper getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new PositionHelper();
            INSTANCE.initClient();
        }
        return INSTANCE;
    }

    private void initClient() {
        getAllSymbolAvailible();
    }

    public static void main(String[] args) {
//        PositionHelper.getInstance();
        System.out.println(Utils.toJson(new PositionHelper().dcaForPositionNew(getPositionBySymbol("BIGTIMEUSDT"))));
// 5753457816
//        ClientSingleton.getInstance().syncRequestClient.cancelOrder("BALUSDT", 5753457816L, "5753457816");
//        System.out.println(Utils.toJson(ClientSingleton.getInstance().syncRequestClient.getOrder("BALUSDT", 5753457816L, "5753457816")));
    }

    private double changeTargetWithRateAndSide(Double target, OrderSide orderSide, double rate) {
        if (orderSide.equals(OrderSide.BUY)) {
            return target + target * rate;
        } else {
            return target - target * rate;
        }
    }

    private void getAllSymbolAvailible() {
//
//        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
//        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
//        for (Object futurePrice : futurePrices) {
//            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
//            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
//                try {
//                    // only get symbol over 2 months
//                    long timeStart = getStartTimeAtExchange(ticker.getSymbol());
////                    LOG.info("{} -> {} -> {}", ticker.getSymbol(), new Date(timeStart), (System.currentTimeMillis() - timeStart) / Utils.TIME_DAY);
//                    if ((System.currentTimeMillis() - timeStart) / Utils.TIME_DAY > 30) {
//                        symbolAvalible2Trading.add(ticker.getSymbol());
//                    }
//                } catch (Exception e) {
//
//                }
//            }
//        }

    }

    private boolean isPriceOverForTrading(String symbol, OrderSide side, Double priceEntryTarget) {
        try {
            Double currentPrice = ClientSingleton.getInstance().getCurrentPrice(symbol);
            Double rateChangeWithEntryTarget = 0d;
            if (side.equals(OrderSide.BUY)) {
                if (currentPrice > priceEntryTarget) {
                    return false;
                } else {
                    rateChangeWithEntryTarget = (priceEntryTarget - currentPrice) / priceEntryTarget;
                }
            } else {
                if (currentPrice < priceEntryTarget) {
                    return false;
                } else {
                    rateChangeWithEntryTarget = (currentPrice - priceEntryTarget) / priceEntryTarget;
                }
            }
            if (rateChangeWithEntryTarget > 0.003) {
                return false;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return true;
    }

    public static PositionRisk getPositionBySymbol(String symbol) {
        List<PositionRisk> positionInfos = ClientSingleton.getInstance().syncRequestClient.getPositionRisk(symbol);
        PositionRisk position = null;
        if (positionInfos != null && !positionInfos.isEmpty()) {
            position = positionInfos.get(0);
        }
        return position;
    }

    public void addOrderByTarget(String symbol, OrderSide orderSide, Double priceEntryTarget) {
        // change target
        double priceEntryTargetNew = changeTargetWithRateAndSide(priceEntryTarget, orderSide, RATE_CHECK_SIGNAL_TARGET);
        LOG.info("Change price target: {} {} {} -> {}", symbol, orderSide, priceEntryTarget, priceEntryTargetNew);
        priceEntryTarget = priceEntryTargetNew;
        boolean passCheckBasic = basicCheckToTrade(symbol);
        if (!passCheckBasic) {
            return;
        }
        if (!isPriceOverForTrading(symbol, orderSide, priceEntryTarget)) {
            Double quantity = Double.valueOf(Utils.normalQuantity2Api(BUDGET_PER_ORDER * LEVERAGE_TRADING / priceEntryTarget));
            quantity = ClientSingleton.getInstance().normalizeQuantity(symbol, quantity);
            for (int i = 1; i < 10; i++) {
                if (quantity == 0) {
                    quantity = Double.valueOf(Utils.normalQuantity2Api((BUDGET_PER_ORDER + i) * LEVERAGE_TRADING / priceEntryTarget));
                    quantity = ClientSingleton.getInstance().normalizeQuantity(symbol, quantity);
                }
            }
            Order result = OrderHelper.newOrderMarket(symbol, orderSide, quantity, LEVERAGE_TRADING);
            if (result != null) {
                PositionRisk pos = getPositionBySymbol(symbol);
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol, Utils.gson.toJson(pos));
                RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER_QUEUE, symbol);
                String telegramAler = symbol + " -> " + orderSide + " entry: " + pos.getEntryPrice().doubleValue();
                Utils.sendSms2Telegram(telegramAler);
                LOG.info("Add order success:{} {} entry: {} quantity:{} {} {}", orderSide, symbol, pos.getEntryPrice().doubleValue(), pos.getPositionAmt().doubleValue(), new Date(), telegramAler);
            } else {
                String log = "Add order fail because can not create order symbol: " + symbol;
                LOG.info(log);
                Utils.sendSms2Telegram(log);
            }
        } else {
            String log = "Add order fail because price over to " + orderSide + " " + ClientSingleton.getInstance().getCurrentPrice(symbol) + "/" + priceEntryTarget + " symbol: " + symbol;
            LOG.info(log);
            Utils.sendSms2Telegram(log);
        }
    }

    public boolean addOrderByTarget(String symbol, OrderSide orderSide) {
        // change target       
        try {
            if (ClientSingleton.getInstance().getBalanceAvalible() <= BUDGET_PER_ORDER) {
                return false;
            }
            boolean passCheckBasic = basicCheckToTrade(symbol);
            if (!passCheckBasic) {
                return true;
            }
            Double priceEntryTarget = ClientSingleton.getInstance().getCurrentPrice(symbol);
            Double quantity = Double.valueOf(Utils.normalQuantity2Api(BUDGET_PER_ORDER * LEVERAGE_TRADING / priceEntryTarget));
            quantity = ClientSingleton.getInstance().normalizeQuantity(symbol, quantity);
            for (int i = 1; i < 10; i++) {
                if (quantity == 0) {
                    quantity = Double.valueOf(Utils.normalQuantity2Api((BUDGET_PER_ORDER + i) * LEVERAGE_TRADING / priceEntryTarget));
                    quantity = ClientSingleton.getInstance().normalizeQuantity(symbol, quantity);
                }
            }
            Order result = OrderHelper.newOrder(symbol, orderSide, quantity, priceEntryTarget, LEVERAGE_TRADING);
            if (result != null) {
                String telegramAler = symbol + " -> " + orderSide + " entry: " + priceEntryTarget;
                Utils.sendSms2Telegram(telegramAler);
                LOG.info("Add order success:{} {} entry: {} quantity:{} {} {}", orderSide, symbol, priceEntryTarget, quantity, new Date(), telegramAler);
            } else {
                String log = "Add order fail because can not create order symbol: " + symbol;
                LOG.info(log);
                Utils.sendSms2Telegram(log);
            }
        } catch (Exception e) {
            e.printStackTrace();
            return true;
        }
        return true;
    }

    public void addOrderBySignal(String symbol, OrderSide orderSide) {

        boolean passCheckBasic = basicCheckToTrade(symbol);
        if (!passCheckBasic) {
            return;
        }
        Double quantity = Double.valueOf(Utils.normalQuantity2Api(BUDGET_PER_ORDER * LEVERAGE_TRADING / ClientSingleton.getInstance().getCurrentPrice(symbol)));
        Order result = OrderHelper.newOrderMarket(symbol, orderSide, quantity, LEVERAGE_TRADING);
        if (result != null) {
            PositionRisk pos = getPositionBySymbol(symbol);
            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol, Utils.gson.toJson(pos));
            RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER_QUEUE, symbol);
            String telegramAler = symbol + " -> " + orderSide + " entry: " + pos.getEntryPrice().doubleValue();
            Utils.sendSms2Telegram(telegramAler);
            LOG.info("Add order success:{} {} entry: {} quantity:{} {} {}", orderSide, symbol, pos.getEntryPrice().doubleValue(), pos.getPositionAmt().doubleValue(), new Date(), telegramAler);
        } else {
            String log = "Add order fail because can not create order symbol: " + symbol;
            LOG.info(log);
            Utils.sendSms2Telegram(log);
        }
    }

    private long getStartTimeAtExchange(String symbol) {

        String urlM1 = URL_TICKER_1D.replace("xxxxxx", symbol);
        String respon = HttpRequest.getContentFromUrl(urlM1);
        try {
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            KlineObject klineFirst = KlineObject.convertString2Kline(allKlines.get(0));
            return klineFirst.startTime.longValue();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0;

    }

    private boolean basicCheckToTrade(String symbol) {
        // check number to trade
        if (RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER).size() > LIMIT_ORDER_TRADING) {
            String log = "Add order fail because over limit order trading: " + symbol
                    + " limit: " + LIMIT_ORDER_TRADING + " orderCurrent: " + RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER).size();
            LOG.info(log);
//            Utils.sendSms2Telegram(log);
            return false;
        }
//        if (!symbolAvalible2Trading.contains(symbol)) {
//            String log = "Add order fail because symbol had new at exchange: " + symbol;
//            LOG.info(log);
//            Utils.sendSms2Telegram(log);
//            return false;
//        }
        if (RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_POS_MANAGER, symbol) != null) {
            String log = "Add order fail because symbol had order active: " + symbol;
            LOG.info(log);
            Utils.sendSms2Telegram(log);
            return false;
        }
        PositionRisk position = getPositionBySymbol(symbol);
        if (position != null && position.getPositionAmt().doubleValue() != 0) {
            String log = "Add order fail because had other position of symbol : " + symbol;
            LOG.info(log);
            Utils.sendSms2Telegram(log);
            return false;
        }
        return true;
    }

    public void cancelOrder(String symbol, Long orderId) {
        try {
            ClientSingleton.getInstance().syncRequestClient.cancelOrder(symbol, orderId, orderId.toString());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public Order dcaForPositionNew(PositionRisk pos) {
        try {
            Double quantity = Math.abs(pos.getPositionAmt().doubleValue());
            OrderSide orderSide = OrderSide.BUY;
            Double price = ClientSingleton.getInstance().getCurrentPrice(pos.getSymbol());
            if (pos.getPositionAmt().doubleValue() < 0) {
                orderSide = OrderSide.SELL;
            }
            if (TickerHelper.getCurrentSide(pos.getSymbol(), Constants.INTERVAL_1D).equals(orderSide)) {
                LOG.info("DCA to {} side:{} price: {} quantity: {}", pos.getSymbol(), orderSide, price, quantity);
                Utils.sendSms2Telegram("DCA for " + pos.getSymbol() + " side: " + orderSide + " price" + Utils.normalPrice2Api(price) + " quantity: " + quantity);
                return ClientSingleton.getInstance().syncRequestClient.postOrder(pos.getSymbol(), orderSide, null, OrderType.LIMIT, TimeInForce.GTC,
                        quantity.toString(), Utils.normalPrice2Api(price), null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);
            }
        } catch (Exception e) {
            LOG.info("Error during DCA for: {}", Utils.toJson(pos));
            e.printStackTrace();
        }
        return null;
    }
//    public Order dcaForPosition(PositionRisk pos, Double rate2DCA) {
//        try {
//            Double quantity = Math.abs(pos.getPositionAmt().doubleValue());
//            OrderSide orderSide = OrderSide.BUY;
//            Double price = pos.getEntryPrice().doubleValue() - pos.getEntryPrice().doubleValue() * rate2DCA / pos.getLeverage().doubleValue();
//            if (pos.getPositionAmt().doubleValue() < 0) {
//                orderSide = OrderSide.SELL;
//                price = pos.getEntryPrice().doubleValue() + pos.getEntryPrice().doubleValue() * rate2DCA / pos.getLeverage().doubleValue();
//            }
//            LOG.info("DCA to {} side:{} price: {} quantity: {}", pos.getSymbol(), orderSide, price, quantity);
//            Utils.sendSms2Telegram("DCA for " + pos.getSymbol() + " side: " + orderSide + " price" + Utils.normalPrice2Api(price) + " quantity: " + quantity);
//            return ClientSingleton.getInstance().syncRequestClient.postOrder(pos.getSymbol(), orderSide, null, OrderType.LIMIT, TimeInForce.GTC,
//                    quantity.toString(), Utils.normalPrice2Api(price), null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);
//        } catch (Exception e) {
//            LOG.info("Error during DCA for: {}", Utils.toJson(pos));
//            e.printStackTrace();
//        }
//        return null;
//    }

    public Order readOrderInfo(String symbol, Long orderId) {
        try {
            return ClientSingleton.getInstance().syncRequestClient.getOrder(symbol, orderId, orderId.toString());
        } catch (Exception e) {
        }
        return null;
    }
}
