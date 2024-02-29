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
package com.educa.mail.funcs;

import com.binance.chuyennd.bigchange.btctd.BreadDetectObject;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.event.CandlestickEvent;
import java.util.List;

/**
 *
 * @author pc
 */
public class BreadFunctions {

    public static BreadDetectObject calBreadDataBtc(KlineObjectNumber kline, Double rateBread) {
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

    public static BreadDetectObject calBreadDataAltWithBtcTrend(List<KlineObjectNumber> klines, int index, Double rateBread) {
        Double beardAbove;
        Double beardBelow;
        OrderSide klineSide;
        KlineObjectNumber kline = klines.get(index);
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
    public static BreadDetectObject calBreadDataAltWeek(List<KlineObjectNumber> klines, int index, Double rateBread) {
        Double beardAbove;
        Double beardBelow;
        OrderSide klineSide;
        KlineObjectNumber kline = klines.get(index);
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
        if (rateChangeBelow > rateChangeAbove) {            
            if (rateChangeBelow > rateBread) {
                side = OrderSide.BUY;
            }            
        }else{
            if (rateChangeAbove > rateBread) {
                side = OrderSide.SELL;
            }
        }
        return new BreadDetectObject(rateChange, rateChangeAbove, rateChangeBelow, totalRate, side, kline.totalUsdt);

    }

    public static BreadDetectObject calBreadData(CandlestickEvent event, Double rateBread) {
        Double beardAbove;
        Double beardBelow;
        Double rateChange;

        if (event.getClose().doubleValue() > event.getOpen().doubleValue()) {
            beardAbove = event.getHigh().doubleValue() - event.getClose().doubleValue();
            beardBelow = event.getOpen().doubleValue() - event.getLow().doubleValue();
            rateChange = Utils.rateOf2Double(event.getClose().doubleValue(), event.getOpen().doubleValue());
        } else {
            beardAbove = event.getHigh().doubleValue() - event.getOpen().doubleValue();
            beardBelow = event.getClose().doubleValue() - event.getLow().doubleValue();
            rateChange = Utils.rateOf2Double(event.getOpen().doubleValue(), event.getClose().doubleValue());
        }
        double rateChangeAbove = beardAbove / event.getClose().doubleValue();
        double rateChangeBelow = beardBelow / event.getClose().doubleValue();
        double totalRate = Math.abs(Utils.rateOf2Double(event.getHigh().doubleValue(), event.getLow().doubleValue()));
        OrderSide side = null;
        if (rateChangeAbove > rateBread) {
            side = OrderSide.SELL;
        } else {
            if (rateChangeBelow > rateBread) {
                side = OrderSide.BUY;
            }
        }
        return new BreadDetectObject(rateChange, rateChangeAbove, rateChangeBelow, totalRate, side, event.getVolume().doubleValue());
    }
}
