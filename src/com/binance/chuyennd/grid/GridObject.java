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
package com.binance.chuyennd.grid;

/**
 *
 * @author pc
 */
public class GridObject {

    public String symbol;
    public Double currentPrice;
    public Double range2Month;
    public Double maxPrice;
    public Double minPrice;
    public Integer ageSymbolByDay;
    public Integer totalKlineBigChange;
    public Integer totalCurrentPriceInKlineBigChange;
    public Integer totalCurrentPriceInKlineDay;

    public GridObject(String symbol, Double currentPrice, Double range2Month, Double maxPrice,
            Double minPrice, Integer ageSymbolByDay, Integer totalKlineBigChange,
            Integer totalCurrentPriceInKlineBigChange, Integer totalCurrentPriceInKlineDay) {
        this.symbol = symbol;
        this.currentPrice = currentPrice;
        this.range2Month = range2Month;
        this.maxPrice = maxPrice;
        this.minPrice = minPrice;
        this.ageSymbolByDay = ageSymbolByDay;
        this.totalKlineBigChange = totalKlineBigChange;
        this.totalCurrentPriceInKlineBigChange = totalCurrentPriceInKlineBigChange;
        this.totalCurrentPriceInKlineDay = totalCurrentPriceInKlineDay;
    }

}
