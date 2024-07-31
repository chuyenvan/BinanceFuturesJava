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
 * @author pc
 */
public class TrendObject {

    public TrendState status;
    public KlineObjectNumber kline;


    public TrendObject(TrendState status, KlineObjectNumber kline) {
        this.status = status;
        this.kline = kline;
    }

    public TrendState getStatus() {
        return status;
    }

    public void setStatus(TrendState status) {
        this.status = status;
    }

    public KlineObjectNumber getKline() {
        return kline;
    }

    public void setKline(KlineObjectNumber kline) {
        this.kline = kline;
    }

    public double getMaxPrice() {
        return kline.maxPrice;
    }

    public double getMinPrice() {
        return kline.minPrice;
    }

    public double getDefaultPrice() {
        return kline.priceOpen;
    }
}
