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
public class KlineObject {

    public Double startTime;
    public String priceOpen;
    public String priceMax;
    public String priceMin;
    public String priceClose;
    public String totalUsdt;
    public Double endTime;
    public String volume;
    public Double al;
    public String orther1;
    public String orther2;
    public String orther3;

    public static KlineObject convertString2Kline(List<Object> kline) {
        KlineObject result = new KlineObject();
        result.startTime = (Double) kline.get(0);
        result.priceOpen = (String) kline.get(1);
        result.priceMax = (String) kline.get(2);
        result.priceMin = (String) kline.get(3);
        result.priceClose = (String) kline.get(4);
        result.totalUsdt = (String) kline.get(5);
        result.endTime = (Double) kline.get(6);
        result.volume = (String) kline.get(7);
        result.al = (Double) kline.get(8);
        result.orther1 = (String) kline.get(9);
        result.orther2 = (String) kline.get(10);
        result.orther3 = (String) kline.get(11);
        return result;
    }

}
