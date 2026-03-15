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

import java.io.Serializable;
import java.util.List;

/**
 * @author pc
 */
public class KlineObjectNumber implements Serializable {

    public Long startTime;
    public float priceOpen;
    public float maxPrice;
    public float minPrice;
    public float priceClose;
    public float totalUsdt;
    public Long endTime;
    public float rsi;
    public float ma20;
    // macd
    public float signal;
    public float macd;
    public float histogram;
//    public Float al;

    public static KlineObjectNumber convertString2Kline(List<Object> kline) {
        KlineObjectNumber result = new KlineObjectNumber();
        result.startTime = (Long) kline.get(0);
        result.priceOpen = Float.valueOf(kline.get(1).toString());
        result.maxPrice = Float.valueOf(kline.get(2).toString());
        result.minPrice = Float.valueOf(kline.get(3).toString());
        result.priceClose = Float.valueOf(kline.get(4).toString());
//        result.volume = Float.valueOf(kline.get(5).toString());
        result.endTime = (Long) kline.get(6);
        result.totalUsdt = Float.valueOf(kline.get(7).toString());
//        result.al = (Float) kline.get(8);
        return result;
    }

    public float getDefaultPrice() {
        return priceClose;
    }
}
