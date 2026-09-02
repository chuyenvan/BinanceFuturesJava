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

/**
 * @author pc
 */
public enum MarketLevelChange {

    // UP
    BIG_UP("BIG_UP"),
//    SMALL_UP("MEDIUM_UP"),
    SMALL_UP("SMALL_UP"),

    DCA_LEVEL1("DCA_LEVEL1"),

    BIG_DOWN("BIG_DOWN"),
    MEDIUM_DOWN("MEDIUM_DOWN"),

    PREDICT_SYMBOL_TRADE("PREDICT_SYMBOL_TRADE"),
    SMALL_DOWN_15M("SMALL_DOWN_15M"),
    ORDER_PROFIT("ORDER_PROFIT"),

    // 2026-08-31: entry forced-seller reversion (SimulatorForcedSeller). Them CUOI enum de
    // khong doi ordinal cac hang cu -> khong vo du lieu da serialize.
    FORCED_SELLER("FORCED_SELLER");

    private final String code;

    MarketLevelChange(String level) {
        this.code = level;
    }

    @Override
    public String toString() {
        return code;
    }

}
