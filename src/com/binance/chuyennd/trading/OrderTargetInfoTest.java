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

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.Order;
import java.io.Serializable;

/**
 *
 * @author pc
 */
public class OrderTargetInfoTest implements Serializable {

    public Order orderEntry;
    public Order orderStoploss;
    public Order orderTakeProfit;
    public OrderTargetStatus status;
    public OrderSide side;
    public Double priceEntry;
    public Double priceTP;
    public Double priceSL;
    public Double quantity;
    public Integer leverage;
    public String symbol;
    public long timeStart;
    public long timeUpdate;
    public String tradingType;

    public Double maxPrice;
    public Double minPrice;
    public Double lastPrice;
    public Double rateBreadAbove;
    public Double rateBreadBelow;
    public Double rateChange;
    public Double volume;
    public Double avgVolume24h;
    public Boolean btcBigchange;

    public OrderTargetInfoTest(OrderTargetStatus status, Double priceEntry,
            Double priceTP, Double quantity, Integer leverage, String symbol, long timeStart, long timeUpdate, OrderSide side, String tradingType, Boolean btcBigchange) {
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
        this.btcBigchange = btcBigchange;
    }

    public void updatePriceByKline(KlineObjectNumber ticker) {
        lastPrice = ticker.priceClose;
        if (this.maxPrice < ticker.maxPrice) {
            this.maxPrice = ticker.maxPrice;
        }
        if (this.minPrice > ticker.minPrice) {
            this.minPrice = ticker.minPrice;
        }
    }

    public void updatePriceByLastPrice(Double lastPrice) {
        this.lastPrice = lastPrice;
        if (this.maxPrice < lastPrice) {
            this.maxPrice = lastPrice;
        }
        if (this.minPrice > lastPrice) {
            this.minPrice = lastPrice;
        }
    }

    public void updateStatus() {
        if (maxPrice > priceTP && minPrice < priceTP) {
            status = OrderTargetStatus.TAKE_PROFIT_DONE;
            timeUpdate = System.currentTimeMillis();
        }
    }

    public Double calRateLoss() {
        double rate = Utils.rateOf2Double(lastPrice, priceEntry);
        if (side.equals(OrderSide.SELL)) {
            rate = -rate;
        }
        return rate;
    }

}
