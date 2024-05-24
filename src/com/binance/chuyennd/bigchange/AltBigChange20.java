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
package com.binance.chuyennd.bigchange;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import java.text.ParseException;
import java.util.Date;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class AltBigChange20 {

    public static final Logger LOG = LoggerFactory.getLogger(AltBigChange20.class);

    public static void main(String[] args) throws ParseException {
//        analyticAltBigChange20();
        analyticDCAPoint();
    }

    private static void analyticAltBigChange20() {
        Map<String, List<KlineObjectNumber>> symbol2Kline1Ds = TickerFuturesHelper.getAllKlineWithUpdateTime(Constants.INTERVAL_1D, Utils.TIME_DAY);
        for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Kline1Ds.entrySet()) {
            String symbol = entry.getKey();
            List<KlineObjectNumber> klines = entry.getValue();
            for (int i = 0; i < klines.size(); i++) {
                KlineObjectNumber kline = klines.get(i);
                double rate = Utils.rateOf2Double(kline.priceClose, kline.priceOpen);
                if (i < klines.size() - 3) {
                    KlineObjectNumber nextKline = klines.get(i + 1);
                    KlineObjectNumber afterNextKline = klines.get(i + 2);
                    KlineObjectNumber after2NextKline = klines.get(i + 3);
                    Double price1;
                    Double price2;
                    Double price3;
                    Double rate1;
                    Double rate2;
                    Double rate3;
                    if (rate < 0) {
                        price1 = nextKline.minPrice;
                        price2 = afterNextKline.minPrice;
                        price3 = after2NextKline.minPrice;
                        rate1 = Utils.rateOf2Double(kline.priceClose, price1);
                        rate2 = Utils.rateOf2Double(kline.priceClose, price2);
                        rate3 = Utils.rateOf2Double(kline.priceClose, price3);
                    } else {
                        price1 = nextKline.maxPrice;
                        price2 = afterNextKline.maxPrice;
                        price3 = after2NextKline.maxPrice;
                        rate1 = Utils.rateOf2Double(kline.priceClose, price1);
                        rate2 = Utils.rateOf2Double(kline.priceClose, price2);
                        rate3 = Utils.rateOf2Double(kline.priceClose, price3);
                    }
                    if (Math.abs(rate) >= 0.2) {
                        LOG.info("{} ->  {} {} priceOpen:{} priceClose:{} {}({}) {}({}) {}({})",
                                symbol, Utils.normalizeDateYYYYMMDD(kline.startTime.longValue()), rate, kline.priceOpen, kline.priceClose,
                                price1, rate1, price2, rate2, price3, rate3);
                    }
                }
            }
        }
    }

    private static void analyticDCAPoint() throws ParseException {
        Map<String, List<KlineObjectNumber>> symbol2Kline1Ds = TickerFuturesHelper.getAllKlineWithUpdateTime(Constants.INTERVAL_1D, Utils.TIME_DAY);
        Date timeStart = Utils.sdfFile.parse("20240305");
        for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Kline1Ds.entrySet()) {
            String symbol = entry.getKey();
            List<KlineObjectNumber> klines = entry.getValue();
            Double maxPrice = null;
            Long dateMax = null;
            Long dateMin = null;
            Double minPrice = null;
            int counter = 0;
            for (int i = 0; i < klines.size(); i++) {
                KlineObjectNumber kline = klines.get(i);
                if (kline.startTime.doubleValue() < timeStart.getTime()) {
                    continue;
                }
                if (maxPrice == null || maxPrice < kline.maxPrice) {
                    maxPrice = kline.maxPrice;
                    dateMax = kline.startTime.longValue();
                    counter = 0;
                    minPrice = null;
                    continue;
                }
                counter++;
                if (minPrice == null || minPrice > kline.minPrice) {
                    minPrice = kline.minPrice;
                    dateMin = kline.startTime.longValue();
                }
                if (counter >= 10 && minPrice != null) {
                    double rate = Utils.rateOf2Double(minPrice, maxPrice);
                    LOG.info("{} max: {} {} min: {} {} rate: {} {} days",
                            symbol, maxPrice, Utils.normalizeDateYYYYMMDD(dateMax), minPrice, Utils.normalizeDateYYYYMMDD(dateMin),
                            rate, (dateMin - dateMax) / Utils.TIME_DAY);
                    maxPrice = null;
                    minPrice = null;
                    counter = 0;
                }
            }
            if (minPrice != null) {
                double rate = Utils.rateOf2Double(minPrice, maxPrice);
                LOG.info("{} max: {} {} min: {} {} rate: {} {} days",
                        symbol, maxPrice, Utils.normalizeDateYYYYMMDD(dateMax), minPrice, Utils.normalizeDateYYYYMMDD(dateMin),
                        rate, (dateMin - dateMax) / Utils.TIME_DAY);
                maxPrice = null;
                minPrice = null;
                counter = 0;
            }
        }
    }
}
