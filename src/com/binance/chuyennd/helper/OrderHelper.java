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
package com.binance.chuyennd.helper;

import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.trading.SymbolOrderLockingManager;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.NewOrderRespType;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderType;
import com.binance.client.model.enums.TimeInForce;
import com.binance.client.model.trade.Order;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @author pc
 */
public class OrderHelper {

    public static final Logger LOG = LoggerFactory.getLogger(OrderHelper.class);

     public static Order newOrderMarket(String symbol, OrderSide side, Double quantity) {
        LOG.info("cat Order market {} {} {}", symbol, side, quantity);
        try {
            if (SymbolOrderLockingManager.getInstance().isLock(symbol, 5)) {
                LOG.info("Symbol {} is locking for loop!", symbol);
                return null;
            }
            SymbolOrderLockingManager.getInstance().addLock(symbol);
            return ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, side, null, OrderType.MARKET, null,
                    Utils.formatMoney(quantity), null, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }


    public static Order stopLoss(String symbol, Double quantity, Double stopPrice) {
        try {
            if (SymbolOrderLockingManager.getInstance().isLock(symbol, 3)) {
                LOG.info("Symbol {} is locking for loop!", symbol);
                return null;
            }
            SymbolOrderLockingManager.getInstance().addLock(symbol);
            return ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, OrderSide.SELL, null, OrderType.STOP_MARKET,
                    TimeInForce.GTC,
                    Utils.formatMoney(quantity), null, null, null, Utils.formatMoney(stopPrice),
                    null, null, null, null, null, NewOrderRespType.RESULT);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }


    public static void main(String[] args) {
//        OrderHelper.newOrderMarket("XEMUSDT", OrderSide.BUY, 50.0);
//        System.out.println(Utils.normalQuantity2Api(955.0));

//        OrderHelper.newOrder("RVNUSDT", OrderSide.SELL, 955.0, 0.020, 7);
//        Double quantity = 10044065d;
//        System.out.println(Utils.formatMoney(quantity));
//        OrderHelper.newOrder("MKRUSDT", OrderSide.BUY, 0.027, 2008.4, 7);
//        OrderHelper.takeProfit("BNBUSDT", OrderSide.SELL, 0.25, 700.0);
//        System.out.println(OrderHelper.stopLoss("BNBUSDT", OrderSide.SELL, 0.25, 630.0));
//        System.out.println(ClientSingleton.getInstance().stopLimit("BNBUSDT", OrderSide.SELL, 0.25, 630.0));
//        OrderHelper.takeProfit("Bigchange", OrderSide.BUY, 1.0, 6.0);
//        System.out.println(OrderHelper.calQuantity(5, 5, 133.5, "TRBUSDT"));
    }


}
