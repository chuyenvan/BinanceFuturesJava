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
package com.binance.chuyennd.bigchange.statistic;

import com.binance.client.model.enums.OrderSide;

/**
 *
 * @author pc
 */
public class BreadDetectObject {    
    public Double rateChange;
    public Double breadAbove;
    public Double breadBelow;
    public Double totalRate;    
    public Double volume;    
    public OrderSide orderSide;    
    public String symbol;    

    public BreadDetectObject(Double rateChange, Double breadAbove, Double breadBelow,
                             Double totalRate, OrderSide orderSides, Double volume) {
        this.rateChange = rateChange;
        this.breadAbove = breadAbove;
        this.breadBelow = breadBelow;
        this.totalRate = totalRate;
        this.orderSide = orderSides;
        this.volume = volume;
    }
    
}
