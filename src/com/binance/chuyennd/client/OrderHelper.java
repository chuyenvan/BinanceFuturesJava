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

import com.binance.chuyennd.object.OrderInfo;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.MarginType;
import com.binance.client.model.enums.NewOrderRespType;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderType;
import com.binance.client.model.enums.TimeInForce;
import com.binance.client.model.trade.Order;
import com.binance.client.model.trade.PositionRisk;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class OrderHelper {

    public static final Logger LOG = LoggerFactory.getLogger(OrderHelper.class);

    public static Order newOrder(String symbol, OrderSide orderSide, Double quantity, Double price, Integer leverage) {
        if (FuturesRules.getInstance().getSymsLocked().contains(symbol)) {
            LOG.info("Sym {} is locking by trading rule!", symbol);
            return null;
        }
        try {
            ClientSingleton.getInstance().syncRequestClient.changeMarginType(symbol, MarginType.CROSSED);
        } catch (Exception e) {
        }
        try {
            ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(symbol, leverage);
        } catch (Exception e) {
        }
        String priceNormal = Utils.formatMoney(ClientSingleton.getInstance().normalizePrice(symbol, price));
        try {
            return ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, orderSide, null, OrderType.LIMIT, TimeInForce.GTC,
                    quantity.toString(), priceNormal, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);
        } catch (Exception e) {
            LOG.info("new order error: {} {} {} {}", symbol, orderSide, quantity, priceNormal);
            e.printStackTrace();
        }
        return null;
    }

    public static Order newOrder(OrderInfo orderInfo) {
        try {
            ClientSingleton.getInstance().syncRequestClient.changeMarginType(orderInfo.symbol, MarginType.ISOLATED);
        } catch (Exception e) {
        }
        try {
            ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(orderInfo.symbol, orderInfo.leverage);
        } catch (Exception e) {
            LOG.info("Leverage {} of: {} not support", orderInfo.leverage, orderInfo.symbol);
            orderInfo.leverage = orderInfo.leverage / 2;
        }
        return ClientSingleton.getInstance().syncRequestClient.postOrder(orderInfo.symbol, orderInfo.orderSide, null, OrderType.LIMIT, TimeInForce.GTC,
                orderInfo.quantity.toString(), orderInfo.priceEntry.toString(), null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);

    }

    public static Order newOrderMarket(OrderInfo orderInfo) {

        try {
            ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(orderInfo.symbol, orderInfo.leverage);
        } catch (Exception e) {
            LOG.info("Leverage {} of: {} not support", orderInfo.leverage, orderInfo.symbol);
            orderInfo.leverage = orderInfo.leverage / 2;
        }
        return ClientSingleton.getInstance().syncRequestClient.postOrder(orderInfo.symbol, orderInfo.orderSide, null, OrderType.MARKET, null,
                orderInfo.quantity.toString(), null, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);

    }

//    public static Order newOrderMarket(String symbol, OrderSide side, Double quantity, Integer leverage) {
//        LOG.info("Order {} {} {} {}", symbol, side, quantity, leverage);
//        try {
//            ClientSingleton.getInstance().syncRequestClient.changeMarginType(symbol, MarginType.CROSSED);
//        } catch (Exception e) {
//        }
//        try {
//            ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(symbol, leverage);
//        } catch (Exception e) {
//            LOG.info("Leverage {} of: {} not support", leverage, symbol);
//        }
//        try {
//            return ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, side, null, OrderType.MARKET, null,
//                    quantity.toString(), null, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//        return null;
//    }
    public static Order newOrderMarket(String symbol, OrderSide side, Double quantity, Integer leverage) {
        if (FuturesRules.getInstance().getSymsLocked().contains(symbol)) {
            LOG.info("Sym {} is locking by trading rule!", symbol);
            return null;
        }
        LOG.info("Order market {} {} {}", symbol, side, quantity);
        try {
            ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(symbol, leverage);
        } catch (Exception e) {
            LOG.info("Leverage {} of: {} not support", leverage, symbol);
        }
        try {
            return ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, side, null, OrderType.MARKET, null,
                    quantity.toString(), null, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static Order takeProfit(OrderInfo orderInfo) {
        OrderSide side = OrderSide.BUY;
        if (orderInfo.orderSide.equals(OrderSide.BUY)) {
            side = OrderSide.SELL;
        }
        try {
            return takeProfit(orderInfo.symbol, side, orderInfo.quantity, orderInfo.priceTP);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static Order takeProfit(Order orderInfo, Double rateProfit) {
        OrderSide side = OrderSide.BUY;
        Double priceTP = orderInfo.getAvgPrice().doubleValue() * (1 - rateProfit);
        if (StringUtils.equals(orderInfo.getSide(), OrderSide.BUY.toString())) {
            side = OrderSide.SELL;
            priceTP = orderInfo.getAvgPrice().doubleValue() * (1 + rateProfit);
        }
        try {
            return takeProfit(orderInfo.getSymbol(), side, orderInfo.getOrigQty().doubleValue(), priceTP);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static Order takeProfitPosition(PositionRisk orderInfo) {
        OrderSide side = OrderSide.BUY;
        if (orderInfo.getPositionAmt().doubleValue() > 0) {
            side = OrderSide.SELL;
        }
        try {
            return takeProfit(orderInfo.getSymbol(), side, orderInfo.getPositionAmt().doubleValue());
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static Order stopLossPosition(PositionRisk orderInfo) {
        OrderSide side = OrderSide.BUY;
        if (orderInfo.getPositionAmt().doubleValue() > 0) {
            side = OrderSide.SELL;
        }
        try {
            return takeProfit(orderInfo.getSymbol(), side, orderInfo.getPositionAmt().doubleValue());
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static Order takeProfit(String symbol, OrderSide side, Double quantity, Double stopPrice) {
        if (FuturesRules.getInstance().getSymsLocked().contains(symbol)) {
            LOG.info("Sym {} is locking by trading rule!", symbol);
            return null;
        }
        String priceNormal = Utils.formatMoney(stopPrice);
        try {
//            FuturesRules.getInstance().addLock(symbol, System.currentTimeMillis());
            return ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, side, null,
                    OrderType.TAKE_PROFIT, TimeInForce.GTC, quantity.toString(), priceNormal, null, null,
                    priceNormal, null, null, null, null, null, NewOrderRespType.RESULT);

        } catch (Exception e) {
            LOG.info("tp error: {} {} {} {}", symbol, side.toString(), quantity, priceNormal);
            e.printStackTrace();
        }
        return null;
    }

    public static Order takeProfit(String symbol, OrderSide side, Double quantity) {
        try {
            return ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, side, null, OrderType.MARKET, null,
                    String.valueOf(Math.abs(quantity)), null, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);

        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static Order stopLoss(OrderInfo orderInfo) {
        OrderSide side = OrderSide.BUY;
        if (orderInfo.orderSide.equals(OrderSide.BUY)) {
            side = OrderSide.SELL;
        }
        return stopLoss(orderInfo.symbol, side, orderInfo.quantity, orderInfo.priceSL);
    }

    public static Order stopLoss(Order orderInfo, Double rateSL) {
        OrderSide side = OrderSide.BUY;
        Double priceSL = orderInfo.getAvgPrice().doubleValue() * (1 + rateSL);
        if (StringUtils.equals(orderInfo.getSide(), OrderSide.BUY.toString())) {
            side = OrderSide.SELL;
            priceSL = orderInfo.getAvgPrice().doubleValue() * (1 - rateSL);
        }
        return stopLoss(orderInfo.getSymbol(), side, orderInfo.getOrigQty().doubleValue(), priceSL);
    }

    public static Order stopLoss(String symbol, OrderSide side, Double quantity, Double stopPrice) {
        return ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, side, null, OrderType.STOP_MARKET, TimeInForce.GTC,
                quantity.toString(), null, null, null, stopPrice.toString(),
                null, null, null, null, null, NewOrderRespType.RESULT);
    }

    public static void main(String[] args) {
//        OrderHelper.newOrderMarket("UNIUSDT", OrderSide.SELL, 5.0, 4);
//        System.out.println(Utils.normalQuantity2Api(955.0));

//        OrderHelper.newOrder("RVNUSDT", OrderSide.SELL, 955.0, 0.020, 7);
        OrderHelper.newOrder("MKRUSDT", OrderSide.BUY, 0.027, 2008.4, 7);
//        OrderHelper.takeProfit("MKRUSDT", OrderSide.BUY, 2008.4, 0.027);
//        System.out.println(OrderHelper.stopLoss("CYBERUSDT", OrderSide.BUY, 1.0, 14.0));
//        OrderHelper.takeProfit("Bigchange", OrderSide.BUY, 1.0, 6.0);
//        System.out.println(OrderHelper.calQuantity(5, 5, 133.5, "TRBUSDT"));
    }

    public static void dcaForPosition(String symbol, OrderSide side, double quantity, int leverage) {
        LOG.info("DCA to {} side:{} quantity: {}", symbol, side, quantity);
        Utils.sendSms2Telegram("DCA for " + symbol + " side: " + side + " quantity: " + quantity);
        newOrderMarket(symbol, side, quantity, leverage);
    }

}
