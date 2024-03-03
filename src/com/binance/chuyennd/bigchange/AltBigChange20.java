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

    public static void main(String[] args) {
        analyticAltBigChange20();
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
                        LOG.info("{} ->  {} {} priceOpen:{} priceClose:{} {}({}) {}({}) {}({})", symbol, Utils.normalizeDateYYYYMMDD(kline.startTime.longValue()), rate, kline.priceOpen, kline.priceClose,
                                price1, rate1, price2, rate2, price3, rate3);
                    }
                }
            }
        }
    }
}
