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
package com.binance.chuyennd.object;

/**
 *
 * @author pc
 */
public class TrendDataTrackingObject {

    public TrendDataTrackingObject(String symbol) {
        this.symbol = symbol;
    }
    public String symbol;
    public long startTime;
    public Double priceStart;
    public Double priceEnd;
    public Double priceMax;
    public Double priceMin;
    public Double rateMax;
    public Double rateMin;
    public long timeMax;
    public long timeMin;

    public void updateRate() {
        rateMax = (priceMax - priceStart) / priceStart;
        rateMin = (priceStart - priceMin) / priceStart;        
    }

}
