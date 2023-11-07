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
package com.binance.chuyennd.sideway;

import com.binance.client.model.enums.OrderSide;

/**
 *
 * @author pc
 */
public class SymbolSideWayObject {
    public String symbol;
    public Double priceMax;
    public Double priceMin;
    public Double priceSignalLong;
    public Double priceSignalShort;
    public OrderSide preferSide;
    public Double rangeSize;
    public Long timeStart;

    public SymbolSideWayObject() {
    }

    public SymbolSideWayObject(String symbol, Double priceMax, Double priceMin, Double priceSignalLong, Double priceSignalShort, OrderSide preferSide, Double rangeSize) {
        this.symbol = symbol;
        this.priceMax = priceMax;
        this.priceMin = priceMin;
        this.priceSignalLong = priceSignalLong;
        this.priceSignalShort = priceSignalShort;
        this.preferSide = preferSide;
        this.rangeSize = rangeSize;
    }
    
}
