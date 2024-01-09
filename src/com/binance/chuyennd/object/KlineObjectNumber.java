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
 *
 * @author pc
 */
public class KlineObjectNumber implements Serializable {

    public Double startTime;
    public Double priceOpen;
    public Double maxPrice;
    public Double minPrice;
    public Double priceClose;
    public Double totalUsdt;
    public Double endTime;
//    public Double al;

    public static KlineObjectNumber convertString2Kline(List<Object> kline) {
        KlineObjectNumber result = new KlineObjectNumber();
        result.startTime = (Double) kline.get(0);
        result.priceOpen = Double.valueOf(kline.get(1).toString());
        result.maxPrice = Double.valueOf(kline.get(2).toString());
        result.minPrice = Double.valueOf(kline.get(3).toString());
        result.priceClose = Double.valueOf(kline.get(4).toString());
//        result.volume = Double.valueOf(kline.get(5).toString());
        result.endTime = (Double) kline.get(6);
        result.totalUsdt = Double.valueOf(kline.get(7).toString());
//        result.al = (Double) kline.get(8);
        return result;
    }

}
