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
package com.binance.chuyennd.object.sw;

import java.io.Serializable;
import java.util.List;

/**
 *
 * @author pc
 */
public class KlineObjectSimple implements Serializable {

    public Long startTime;
    public float priceOpen;
    public float maxPrice;
    public float minPrice;
    public float priceClose;
    public float totalUsdt;

    public static KlineObjectSimple convertString2Kline(List<Object> kline) {
        KlineObjectSimple result = new KlineObjectSimple();
        Double time = (Double) kline.get(0);
        result.startTime = time.longValue();
        result.priceOpen = Float.valueOf(kline.get(1).toString());
        result.maxPrice = Float.valueOf(kline.get(2).toString());
        result.minPrice = Float.valueOf(kline.get(3).toString());
        result.priceClose = Float.valueOf(kline.get(4).toString());
        result.totalUsdt = Float.valueOf(kline.get(7).toString());
        return result;
    }

    public float getDefaultPrice() {
        return priceClose;
    }


}
