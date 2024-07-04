/*
 * Copyright 2024 pc.
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
package com.binance.chuyennd.trading;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.Order;
import java.io.Serializable;

/**
 *
 * @author pc
 */
public class OrderTargetInfo implements Serializable {

    public OrderTargetStatus status;
    public OrderSide side;
    public Double priceEntry;
    public Double priceTP;
    public Double priceSL;
    public Double quantity;
    public Integer leverage;
    public String tradingType;
    public String symbol;
    public MarketLevelChange marketLevel;
    public long timeStart;
    public long timeUpdate;
    

    public OrderTargetInfo(OrderTargetStatus status, Double priceEntry,
            Double priceTP, Double quantity, Integer leverage, String symbol, long timeStart, long timeUpdate, OrderSide side, String tradingType) {
        this.status = status;
        this.priceEntry = priceEntry;
        this.priceTP = priceTP;
        this.quantity = quantity;
        this.leverage = leverage;
        this.symbol = symbol;
        this.timeStart = timeStart;
        this.timeUpdate = timeUpdate;
        this.side = side;
        this.tradingType = tradingType;
    }

}
