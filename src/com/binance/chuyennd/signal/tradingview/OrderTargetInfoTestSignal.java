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
package com.binance.chuyennd.signal.tradingview;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

/**
 * @author pc
 */
public class OrderTargetInfoTestSignal implements Serializable {

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

    public Double maxPrice;
    public Double minPrice;
    public Double lastPrice;

    public Double rateChange;
    public Double volume;

    public List<String> signals;

    public KlineObjectNumber tickerOpen;
    public KlineObjectNumber tickerClose;


    public OrderTargetInfoTestSignal(OrderTargetStatus status, Double priceEntry,
                                     Double priceTP, Double quantity, Integer leverage, String symbol,
                                     long timeStart, long timeUpdate, OrderSide side) {
        this.status = status;
        this.priceEntry = priceEntry;
        this.priceTP = priceTP;
        this.quantity = quantity;
        this.leverage = leverage;
        this.symbol = symbol;
        this.timeStart = timeStart;
        this.timeUpdate = timeUpdate;
        this.side = side;
        this.signals = new ArrayList<>();

    }

    public void updatePriceByKline(KlineObjectNumber ticker) {
        this.lastPrice = ticker.priceClose;
        if (this.maxPrice < ticker.maxPrice) {
            this.maxPrice = ticker.maxPrice;
            this.timeUpdate = ticker.endTime.longValue();
        }
        if (this.minPrice > ticker.minPrice) {
            this.minPrice = ticker.minPrice;
        }
//        this.maxPrice = ticker.maxPrice;
//        this.minPrice = ticker.minPrice;
//        this.timeUpdate = ticker.endTime.longValue();
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
        }
        if (System.currentTimeMillis() - timeStart >= 4 * Utils.TIME_HOUR){
            priceTP = lastPrice;
            status = OrderTargetStatus.STOP_LOSS_DONE;
        }
    }

    public Double calRateLoss() {
        double rate = Utils.rateOf2Double(lastPrice, priceEntry);
        if (side.equals(OrderSide.SELL)) {
            rate = -rate;
        }
        return rate;
    }

    public Double calProfit() {
        return quantity * (lastPrice - priceEntry);
    }

    public Double calMargin() {
        return quantity * priceEntry / leverage;
    }

    public Double calProfitMin() {
        return quantity * (minPrice - priceEntry);
    }

}
