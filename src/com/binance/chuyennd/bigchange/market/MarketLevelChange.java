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
package com.binance.chuyennd.bigchange.market;

/**
 * @author pc
 */
public enum MarketLevelChange {

    // UP
    BIG_UP("BIG_UP"),
    MEDIUM_UP("MEDIUM_UP"),
    SMALL_UP("SMALL_UP"),
    TINY_UP("TINY_UP"),
    MINI_UP("MINI_UP"),

    DCA_ORDER("DCA_ORDER"),
    DCA_BIG_LOSS("DCA_BIG_LOSS"),
    BTC_TREND_REVERSE("BTC_TREND_REVERSE"),

    BIG_DOWN("BIG_DOWN"),
    MEDIUM_DOWN("MEDIUM_DOWN"),
    SMALL_DOWN("SMALL_DOWN"),
    TINY_DOWN("TINY_DOWN"),

    FUNDING_FEE_BUY("FUNDING_FEE_BUY"),
    FUNDING_FEE_SELL("FUNDING_FEE_SELL"),
    MEDIUM_DOWN_15M("MEDIUM_DOWN_15M"),
    SMALL_DOWN_15M("SMALL_DOWN_15M"),
    GRID_TRADE("GRID_TRADE"),
    ORDER_PROFIT("ORDER_PROFIT"),
    ORDER_SELL("ORDER_SELL"),
    ORDER_SELL_DCA("ORDER_SELL_DCA"),
    ORDER_SELL_QUICK("ORDER_SELL_QUICK");

    private final String code;

    MarketLevelChange(String level) {
        this.code = level;
    }

    @Override
    public String toString() {
        return code;
    }

}
