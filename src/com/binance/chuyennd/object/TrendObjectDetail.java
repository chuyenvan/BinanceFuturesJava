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

import java.util.List;

/**
 * @author pc
 */
public class TrendObjectDetail {

    public TrendState status;
//    public List<TrendObject> topBottonObjects;
    public List<TrendObject> topBottonObjects;
    public Double maxPrice;
    public Double minPrice;
    public long startTimeTrend = 0;
    public long endTimeTrend = 0;
    public long timeNextTrend = 0;

    public TrendObjectDetail(TrendState status, List<TrendObject> klines) {
        this.status = status;
        this.topBottonObjects = klines;
    }

    public void updatePriceRange(TrendObject trend) {
        if (maxPrice == null || maxPrice < trend.kline.maxPrice) {
            maxPrice = trend.kline.maxPrice;
        }
        if (minPrice == null || minPrice > trend.kline.minPrice) {
            minPrice = trend.kline.minPrice;
        }

    }
}
