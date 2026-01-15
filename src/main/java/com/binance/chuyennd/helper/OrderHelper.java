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
import com.binance.client.exception.BinanceApiException;
import com.binance.client.model.enums.*;
import com.binance.client.model.trade.Order;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @author pc
 */
public class OrderHelper {

    public static final Logger LOG = LoggerFactory.getLogger(OrderHelper.class);

     public static Order newOrderMarket(String symbol, OrderSide side, Double quantity) {
        LOG.info("Create Order market {} {} {}", symbol, side, quantity);
        try {
            if (SymbolOrderLockingManager.getInstance().isLock(symbol, 5)) {
                LOG.info("Symbol {} is locking for loop!", symbol);
                return null;
            }
            SymbolOrderLockingManager.getInstance().addLock(symbol);
            return ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, side, null, OrderType.MARKET, null,
                    Utils.formatMoney(quantity), null, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);
        } catch (BinanceApiException e) { // Bắt cụ thể lỗi API của Binance
            // Kiểm tra xem có phải chính xác là lỗi -4400 không
            if (e.getMessage().contains("-4400") ) {
                LOG.warn("CANNOT OPEN NEW ORDER for {}: Exchange is in reduce-only mode. Pausing new trades for this symbol.", symbol);
                SymbolOrderLockingManager.getInstance().addLockReduceOnly(symbol);
                // 3. Bot sẽ bỏ qua việc mở lệnh mới cho mã này trong một khoảng thời gian (ví dụ: 1 giờ).
            } else {
                // Đối với các lỗi khác, vẫn in ra như bình thường
                e.printStackTrace();
            }
        } catch (Exception e) {
            // Bắt các lỗi chung khác (ví dụ: mất kết nối mạng)
            e.printStackTrace();
        }
        return null;
    }


    public static Order stopLoss(String symbol, Double quantity, Double stopPrice) {
        LOG.info("Create Stop Loss Algo {} qty: {} price: {}", symbol, quantity, stopPrice);
        try {
            if (SymbolOrderLockingManager.getInstance().isLock(symbol, 3)) {
                return null;
            }
            SymbolOrderLockingManager.getInstance().addLock(symbol);

            // Chuyển sang String
            String strQty = Utils.formatMoney(quantity);
            String strStopPrice = Utils.formatMoney(stopPrice);
            String strReduceOnly = "true";

            // SỬ DỤNG ALGO ORDER
            return ClientSingleton.getInstance().syncRequestClient.postAlgoOrder(
                    symbol,
                    OrderSide.SELL,         // Mặc định SL cho lệnh Long là Sell
                    OrderType.STOP_MARKET,  // Tham số này trong hàm postAlgoOrder mới sẽ bị bỏ qua hoặc dùng để log
                    strQty,
                    strStopPrice,
                    strReduceOnly
            );

        } catch (Exception e) {
            LOG.error("Error stopLoss", e);
            e.printStackTrace();
        }
        return null;

    }


    public static void main(String[] args) {
        Order order = OrderHelper.newOrderMarket("LUNA2USDT", OrderSide.BUY, 62.0);
        System.out.println(Utils.toJson(order));
//        System.out.println(Utils.normalQuantity2Api(955.0));

//        OrderHelper.stopLoss("LUNA2USDT",74.0, 0.141);
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
