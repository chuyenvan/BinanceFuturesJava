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

    public static Order newOrderMarket(String symbol, OrderSide side, Float quantity) {
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
            String errorMsg = e.getMessage();

            // 1. Lỗi -4400: Reduce-only mode
            if (errorMsg != null && errorMsg.contains("-4400")) {
                LOG.warn("CANNOT OPEN NEW ORDER for {}: Exchange is in reduce-only mode. Pausing new trades for this symbol.", symbol);
                SymbolOrderLockingManager.getInstance().addLockReduceOnly(symbol);
            }
            // 2. Lỗi -1008: Request throttled by system-level protection (Quá tải API)
            else if (errorMsg != null && errorMsg.contains("-1008")) {
                LOG.warn("API THROTTLED (-1008) for {}: Binance system is overloaded. Pausing new trades to prevent ban.", symbol);

                // Khóa symbol này tương tự như lỗi 4400 để bot tạm ngưng mở lệnh
                SymbolOrderLockingManager.getInstance().addLockReduceOnly(symbol);

                // CỰC KỲ QUAN TRỌNG: Cho Thread ngủ 1-2 giây để xả Rate Limit, tránh spam liên tục dẫn đến Band IP
                try {
                    Thread.sleep(1500);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                }
            }
            // Các lỗi API khác
            else {
                LOG.error("Binance API Exception when creating order for {}: {}", symbol, errorMsg);
                e.printStackTrace();
            }
        } catch (Exception e) {
            // Bắt các lỗi chung khác (ví dụ: mất kết nối mạng, timeout)
            LOG.error("General Exception when creating order for {}: {}", symbol, e.getMessage());
            e.printStackTrace();
        }
        return null;
    }


    public static Order stopLoss(String symbol, Float quantity, Float stopPrice) {
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
        Order order = OrderHelper.newOrderMarket("LUNA2USDT", OrderSide.BUY, 62.0f);
        System.out.println(Utils.toJson(order));
//        System.out.println(Utils.normalQuantity2Api(955.0));

//        OrderHelper.stopLoss("LUNA2USDT",74.0, 0.141);
//        OrderHelper.newOrder("RVNUSDT", OrderSide.SELL, 955.0, 0.020, 7);
//        Float quantity = 10044065d;
//        System.out.println(Utils.formatMoney(quantity));
//        OrderHelper.newOrder("MKRUSDT", OrderSide.BUY, 0.027, 2008.4, 7);
//        OrderHelper.takeProfit("BNBUSDT", OrderSide.SELL, 0.25, 700.0);
//        System.out.println(OrderHelper.stopLoss("BNBUSDT", OrderSide.SELL, 0.25, 630.0));
//        System.out.println(ClientSingleton.getInstance().stopLimit("BNBUSDT", OrderSide.SELL, 0.25, 630.0));
//        OrderHelper.takeProfit("Bigchange", OrderSide.BUY, 1.0, 6.0);
//        System.out.println(OrderHelper.calQuantity(5, 5, 133.5, "TRBUSDT"));
    }


}
