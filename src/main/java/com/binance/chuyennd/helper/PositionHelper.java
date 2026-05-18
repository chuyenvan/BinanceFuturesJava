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
package com.binance.chuyennd.helper;

import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.trade.PositionRisk;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;

/**
 * @author pc
 */
public class PositionHelper {

    public static final Logger LOG = LoggerFactory.getLogger(OrderHelper.class);

    public static Float callMargin(PositionRisk pos) {
        if (pos == null){
            return null;
        }
        try {
            return Math.abs(pos.getEntryPrice().floatValue() * pos.getPositionAmt().floatValue() / pos.getLeverage().floatValue());
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static Float calRateLoss(PositionRisk pos) {
        try {
            Float rate = Utils.rateOf2Double(pos.getMarkPrice().floatValue(), pos.getEntryPrice().floatValue());
            if (pos.getPositionAmt().compareTo(new BigDecimal("0")) < 0) {
                rate = -rate;
            }
            return rate;
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }



    public static PositionRisk createPosNew(String symbol, BigDecimal price, BigDecimal quantity) {
        PositionRisk pos = new PositionRisk();
        pos.setSymbol(symbol);
        pos.setEntryPrice(price);
        pos.setUpdateTime(System.currentTimeMillis());
        pos.setMarkPrice(price);
        pos.setPositionAmt(quantity);
        return pos;
    }
}
