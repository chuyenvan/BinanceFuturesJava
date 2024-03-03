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
package com.binance.chuyennd.sideway;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.SideWayObject;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class SideWayDetector {

    public static final Logger LOG = LoggerFactory.getLogger(SideWayDetector.class);

    public static void main(String[] args) {

        Double rangeSizeTarget = 0.07;
        Integer minimumKline = 10;

        Long startTime = 1695574800000L;
        TreeMap<Long, SideWayObject> time2Object = new TreeMap();
        long today = Utils.getStartTimeDayAgo(0);
        Map<String, List<KlineObjectNumber>> allSymbolTickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);        
        for (String symbol : allSymbolTickers.keySet()) {
            if (Constants.specialSymbol.contains(symbol)) {
                continue;
            }
//        String symbol = "WLDUSDT";
            List<SideWayObject> objects = TickerFuturesHelper.extractSideWayObject(allSymbolTickers.get(symbol), rangeSizeTarget, minimumKline);
            for (SideWayObject object : objects) {
                LOG.info("{} {} hours  start: {} end: {} max: {} min: {} rate: {}", symbol, (object.end.endTime.longValue() - object.start.startTime.longValue()) / Utils.TIME_HOUR,
                        Utils.normalizeDateYYYYMMDDHHmm(object.start.startTime.longValue()),
                        Utils.normalizeDateYYYYMMDDHHmm(object.end.startTime.longValue()), object.maxPrice, object.minPrice, object.rate);
                if (object.end.startTime.longValue() > today) {
                    object.symbol = symbol;
                    time2Object.put(object.end.startTime.longValue() - object.start.startTime.longValue(), object);
                }
            }
        }
        for (Map.Entry<Long, SideWayObject> entry : time2Object.entrySet()) {
            SideWayObject object = entry.getValue();
            LOG.info("{} {} hours  start: {} end: {} max: {} min: {} rate: {}", object.symbol, (object.end.endTime.longValue() - object.start.startTime.longValue()) / Utils.TIME_HOUR,
                    Utils.normalizeDateYYYYMMDDHHmm(object.start.startTime.longValue()),
                    Utils.normalizeDateYYYYMMDDHHmm(object.end.startTime.longValue()), object.maxPrice, object.minPrice, object.rate);

        }

    }

}
