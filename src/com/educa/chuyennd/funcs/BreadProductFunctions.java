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
package com.educa.chuyennd.funcs;

import com.binance.chuyennd.bigchange.btctd.BreadDetectObject;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.event.CandlestickEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.TreeMap;

/**
 * @author pc
 */
public class BreadProductFunctions {
        public static final Logger LOG = LoggerFactory.getLogger(BreadProductFunctions.class);
    public static TreeMap<Double, Double> volume2RateChange = new TreeMap<>();

    static {
        // with stoploss and ma20 rate 96% 24h
//        volume2RateChange.put(0.6, 0.015);
//        volume2RateChange.put(0.8, 0.016);
//        volume2RateChange.put(0.9, 0.017);
//        volume2RateChange.put(1.0, 0.018);
//        volume2RateChange.put(1.1, 0.019);
//        volume2RateChange.put(1.3, 0.02);
//        volume2RateChange.put(1.4, 0.021);
//        volume2RateChange.put(1.6, 0.022);
//        volume2RateChange.put(1.8, 0.023);
//        volume2RateChange.put(2.0, 0.024);
//        volume2RateChange.put(2.2, 0.026);
//        volume2RateChange.put(2.5, 0.027);
//        volume2RateChange.put(3.0, 0.028);
//        volume2RateChange.put(3.3, 0.029);
//        volume2RateChange.put(4.0, 0.03);
//        volume2RateChange.put(7.0, 0.034);
//        volume2RateChange.put(10.0, 0.036);
//        volume2RateChange.put(13.0, 0.04);
//        volume2RateChange.put(16.0, 0.045);
//        volume2RateChange.put(19.0, 0.05);
//        volume2RateChange.put(31.0, 0.06);
//        volume2RateChange.put(100.0, 0.08);
//        volume2RateChange.put(1000.0, 0.12);

        // 91.5% target0.01 16h
        volume2RateChange.put(0.2, 0.014);
        volume2RateChange.put(0.4, 0.016);
        volume2RateChange.put(0.6, 0.018);
        volume2RateChange.put(1.0, 0.019);
        volume2RateChange.put(1.3, 0.02);
        volume2RateChange.put(1.9, 0.021);
        volume2RateChange.put(3.0, 0.022);
        volume2RateChange.put(13.1, 0.023);
        volume2RateChange.put(92.0, 0.024);
        volume2RateChange.put(1000.0, 0.48);
    }


    public static BreadDetectObject calBreadDataAlt(KlineObjectNumber kline, Double rateBread) {
        Double beardAbove;
        Double beardBelow;
        OrderSide klineSide;
        if (kline.priceClose > kline.priceOpen) {
            klineSide = OrderSide.BUY;
            beardAbove = kline.maxPrice - kline.priceClose;
            beardBelow = kline.priceOpen - kline.minPrice;
        } else {
            klineSide = OrderSide.SELL;
            beardAbove = kline.maxPrice - kline.priceOpen;
            beardBelow = kline.priceClose - kline.minPrice;
        }
        Double rateChange = Math.abs(Utils.rateOf2Double(kline.priceOpen, kline.priceClose));
        double totalRate = Math.abs(Utils.rateOf2Double(kline.maxPrice, kline.minPrice));
        double rateChangeAbove = beardAbove / kline.priceClose;
        double rateChangeBelow = beardBelow / kline.priceClose;
        OrderSide side = null;
        if (klineSide.equals(OrderSide.SELL) && rateChangeBelow > rateBread) {
            side = OrderSide.BUY;
        } else {
            if (klineSide.equals(OrderSide.BUY) && rateChangeAbove > rateBread) {
                side = OrderSide.SELL;
            }
        }
        return new BreadDetectObject(rateChange, rateChangeAbove, rateChangeBelow, totalRate, side, kline.totalUsdt);

    }

    public static Double getRateChangeWithVolume(Double volume) {
        for (Double vol : BreadProductFunctions.volume2RateChange.keySet()) {
            if (volume <= vol) {
                return volume2RateChange.get(vol);
            }
        }
        return null;
    }

    public static void main(String[] args) {
        for (int i = 0; i < 100; i++) {
            Double volume = i * 100000d;
            LOG.info("{} M - {}",volume/ 1000000, BreadProductFunctions.getRateChangeWithVolume(volume/ 1000000));
        }
    }
}
