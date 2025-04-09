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
package com.binance.chuyennd.trading.grid;

import com.binance.chuyennd.client.ClientSingleton;
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
public class GridOrderHelper {

    public static final Logger LOG = LoggerFactory.getLogger(GridOrderHelper.class);

    public static Order newOrder(String symbol, OrderSide orderSide, Double quantity, Double price) {

        String priceNormal = Utils.formatMoney(ClientSingleton.getInstance().normalizePrice(symbol, price));
        try {
            return GridClientSingleton.getInstance().syncRequestClient.postOrder(symbol, orderSide, null, OrderType.LIMIT, TimeInForce.GTC,
                    quantity.toString(), priceNormal, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);
        } catch (Exception e) {
            LOG.info("new order error: {} {} {} {}", symbol, orderSide, quantity, priceNormal);
            e.printStackTrace();
        }
        return null;
    }

    public static Order stopLoss(String symbol, OrderSide side, Double quantity, Double stopPrice) {
        return GridClientSingleton.getInstance().syncRequestClient.postOrder(symbol, side, null, OrderType.STOP_MARKET, TimeInForce.GTC,
                Utils.formatMoney(quantity), null, null, null, Utils.formatMoney(stopPrice),
                null, null, null, null, null, NewOrderRespType.RESULT);
    }


    public static Order newOrderMarket(String symbol, OrderSide side, Double quantity) {
        LOG.info("Order market {} {} {}", symbol, side, quantity);
        try {
            return GridClientSingleton.getInstance().syncRequestClient.postOrder(symbol, side, null, OrderType.MARKET, null,
                    Utils.formatMoney(quantity), null, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static void main(String[] args) {
        GridOrderHelper.newOrder("BTCUSDT", OrderSide.BUY, 0.002, 90000.0);
    }

}
