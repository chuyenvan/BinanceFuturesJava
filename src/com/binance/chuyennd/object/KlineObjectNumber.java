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
 *
 * @author pc
 */
public class KlineObjectNumber {

    public Double startTime;
    public Double priceOpen;
    public Double priceMax;
    public Double priceMin;
    public Double priceClose;
    public String totalUsdt;
    public Double endTime;
    public Double volume;
    public Double al;
    public String orther1;
    public String orther2;
    public String orther3;

    public static KlineObjectNumber convertString2Kline(List<Object> kline) {
        KlineObjectNumber result = new KlineObjectNumber();
        result.startTime = (Double) kline.get(0);
        result.priceOpen = Double.valueOf(kline.get(1).toString());
        result.priceMax = Double.valueOf(kline.get(2).toString());
        result.priceMin = Double.valueOf(kline.get(3).toString());
        result.priceClose = Double.valueOf(kline.get(4).toString());
        result.volume = Double.valueOf(kline.get(5).toString());
        result.endTime = (Double) kline.get(6);
        result.totalUsdt = (String) kline.get(7);
        result.al = (Double) kline.get(8);
        result.orther1 = (String) kline.get(9);
        result.orther2 = (String) kline.get(10);
        result.orther3 = (String) kline.get(11);
        return result;
    }

}
