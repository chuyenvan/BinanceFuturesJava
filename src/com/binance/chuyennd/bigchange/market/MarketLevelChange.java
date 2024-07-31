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
    BIG_UP,
    MEDIUM_UP,
    SMALL_UP,


    // DOWN
    ALT_BIG_CHANGE_REVERSE,
    ALT_BIG_CHANGE_REVERSE_EXTEND,

    MINI_DOWN,
    TINY_DOWN,
    SMALL_DOWN,
    MEDIUM_DOWN,
    MAYBE_BIG_DOWN_AFTER,
    BIG_DOWN,


    ALT_SIGNAL_SELL,
    // market state have order market running
    MULTI_LEVEL_MARKET_RUNNING;
}
