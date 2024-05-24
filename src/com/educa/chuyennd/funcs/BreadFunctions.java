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
import com.binance.chuyennd.mongo.TickerMongoHelper;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.event.CandlestickEvent;
import com.mongodb.client.MongoCursor;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * @author pc
 */
public class BreadFunctions {
    public static final Logger LOG = LoggerFactory.getLogger(BreadFunctions.class);
    public static TreeMap<Double, Double> volume2RateChange = new TreeMap<>();

    static {
//         with stoploss a
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
        // rateTarget:0.01  64%
//        volume2RateChange.put(0.6, 0.015);
//        volume2RateChange.put(0.8, 0.016);
//        volume2RateChange.put(0.9, 0.017);
//        volume2RateChange.put(1.0, 0.018);
//        volume2RateChange.put(1.1, 0.019);
//        volume2RateChange.put(1.3, 0.02);
//        volume2RateChange.put(1.4, 0.021);
//        volume2RateChange.put(1.6, 0.022);
    }

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
        if (klineSide.equals(OrderSide.SELL) && rateChangeBelow > rateBread) { // web 3
//        if (klineSide.equals(OrderSide.SELL) && rateChangeBelow > rateChangeAbove) { // web 2
            side = OrderSide.BUY;
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
            if (rateChangeBelow > rateChangeAbove) {
                side = OrderSide.BUY;
            }
        } else {
            if (klineSide.equals(OrderSide.BUY) && rateChangeAbove > rateBread) {
                side = OrderSide.SELL;
            }
        }
        return new BreadDetectObject(rateChange, rateChangeAbove, rateChangeBelow, totalRate, side, kline.totalUsdt);

    }

//    public static BreadDetectObject calBreadDataAltWeek(List<KlineObjectNumber> klines, int index, Double rateBread) {
//        Double beardAbove;
//        Double beardBelow;
//        OrderSide klineSide;
//        KlineObjectNumber kline = klines.get(index);
//        if (kline.priceClose > kline.priceOpen) {
//            klineSide = OrderSide.BUY;
//            beardAbove = kline.maxPrice - kline.priceClose;
//            beardBelow = kline.priceOpen - kline.minPrice;
//        } else {
//            klineSide = OrderSide.SELL;
//            beardAbove = kline.maxPrice - kline.priceOpen;
//            beardBelow = kline.priceClose - kline.minPrice;
//        }
//        Double rateChange = Math.abs(Utils.rateOf2Double(kline.priceOpen, kline.priceClose));
//        double totalRate = Math.abs(Utils.rateOf2Double(kline.maxPrice, kline.minPrice));
//        double rateChangeAbove = beardAbove / kline.priceClose;
//        double rateChangeBelow = beardBelow / kline.priceClose;
//        OrderSide side = null;
//        if (rateChangeBelow > rateChangeAbove) {
//            if (rateChangeBelow > rateBread) {
//                side = OrderSide.BUY;
//            }
//        } else {
//            if (rateChangeAbove > rateBread) {
//                side = OrderSide.SELL;
//            }
//        }
//        return new BreadDetectObject(rateChange, rateChangeAbove, rateChangeBelow, totalRate, side, kline.totalUsdt);
//
//    }

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

    public static Double getRateChangeWithVolume(Double volume) {
        for (Double vol : BreadFunctions.volume2RateChange.keySet()) {
            if (volume <= vol) {
                return volume2RateChange.get(vol);
            }
        }
        return null;
    }

    public static void main(String[] args) {
        Integer numberHours = 14;
        BreadFunctions.updateVolumeRateChange(numberHours, 93.0);
    }

    public static void updateVolumeRateChange(Integer numberHours, Double rateSuccessTarget) {
        MongoCursor<Document> docs = TickerMongoHelper.getInstance().getAllTickerStatisticByHourNumber(numberHours);
        volume2RateChange.clear();
        TreeMap<Double, TreeMap<Double, Double>> volume2RateChangeAndRateSucess = new TreeMap<>();
        Map<String, Double> volumeAndRateChange2RateSuccess = new HashMap<>();
        /*
                    doc.append("hour", numberHours);
            doc.append("volume", volume);
            doc.append("rate_change", rateChange);
            doc.append("success_order", counterSuccess);
            doc.append("total_order", counterTotal);
            doc.append("rate_success", rateSuccess.doubleValue() / 10);
         */
        while (docs.hasNext()) {
            Document doc = docs.next();
            Double rateChange = doc.getDouble("rate_change");
            Double rateSuccess = doc.getDouble("rate_success");
            Double volume = doc.getDouble("volume");
            TreeMap<Double, Double> rateChange2RateSuccess = volume2RateChangeAndRateSucess.get(volume);
            if (rateChange2RateSuccess == null) {
                rateChange2RateSuccess = new TreeMap<>();
                volume2RateChangeAndRateSucess.put(volume, rateChange2RateSuccess);
            }
            rateChange2RateSuccess.put(rateChange, rateSuccess);
            volumeAndRateChange2RateSuccess.put(volume.toString() + "-" + rateChange.toString(), rateSuccess);
        }
        for (Map.Entry<Double, TreeMap<Double, Double>> entry : volume2RateChangeAndRateSucess.entrySet()) {
            Double volume = entry.getKey();
            TreeMap<Double, Double> volume2RateSuccess = entry.getValue();
            for (Map.Entry<Double, Double> entry1 : volume2RateSuccess.entrySet()) {
                Double rateChange = entry1.getKey();
                Double rateSuccess = entry1.getValue();
                if (rateSuccess >= rateSuccessTarget) {
                    volume2RateChange.put(volume, rateChange);
                    break;
                }
            }
        }
        // add with volume max 1000
        volume2RateChange.put(1000.0, volume2RateChange.lastEntry().getValue() * 2);
        TreeMap<Double, Double> hashMap = new TreeMap<>();
        for (Map.Entry<Double, Double> entry : volume2RateChange.entrySet()) {
            Double key = entry.getKey();
            Double values = entry.getValue();
            hashMap.put(values, key);
//            LOG.info(" {} {} {}", -key, values, volumeAndRateChange2RateSuccess.get(key + "-" + values));
        }
        for (Map.Entry<Double, Double> entry : hashMap.entrySet()) {
            Double key = entry.getKey();
            Double values = entry.getValue();
            LOG.info("New {} {} {}", values, -key, volumeAndRateChange2RateSuccess.get(values + "-" + key));
        }
        LOG.info("Finish update volume and rate change with rate success: {}", rateSuccessTarget);
    }

    public static boolean isAvailableTrade(BreadDetectObject breadData, KlineObjectNumber kline,
                                           MAStatus maStatus, Double rateChange, Double rateMa, Double RATE_MA_MAX) {
        if (breadData.orderSide != null
                && breadData.orderSide.equals(OrderSide.BUY)
                && maStatus != null && maStatus.equals(MAStatus.TOP)
                && rateMa < RATE_MA_MAX
                && kline.priceClose < kline.ma20
                && breadData.totalRate >= rateChange) {
            return true;
        }
        return false;
    }
}
