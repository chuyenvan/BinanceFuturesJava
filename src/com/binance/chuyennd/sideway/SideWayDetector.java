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

import com.binance.chuyennd.funcs.TickerHelper;
import com.binance.chuyennd.object.sw.SideWayObject;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class SideWayDetector {

    public static final Logger LOG = LoggerFactory.getLogger(SideWayDetector.class);

    public static void main(String[] args) {
        for (String symbol : TickerHelper.getAllSymbol()) {
            String interval = Constants.INTERVAL_15M;
            Double rangeSizeTarget = 0.03;
            Integer minimumKline = 20;
            List<SideWayObject> objects = TickerHelper.extractSideWayObject(symbol, interval, rangeSizeTarget, minimumKline);
            for (SideWayObject object : objects) {
                LOG.info("{} {} hours  start: {} end: {} max: {} min: {} rate: {}", symbol, (object.end.endTime.longValue() - object.start.startTime.longValue()) / Utils.TIME_HOUR,
                        Utils.normalizeDateYYYYMMDDHHmm(object.start.startTime.longValue()),
                        Utils.normalizeDateYYYYMMDDHHmm(object.end.startTime.longValue()), object.maxPrice, object.minPrice, object.rate);
            }
        }

    }

}
