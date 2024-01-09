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
package com.binance.client.constant;

import java.util.ArrayList;
import java.util.Arrays;

/**
 *
 * @author pc
 */
public class Constants {

    public static final String SYMBOL_PAIR_BTC = "BTCUSDT";
    public static final String INTERVAL_1M = "1m";
    public static final String INTERVAL_15M = "15m";
    public static final String INTERVAL_1D = "1d";
    public static final String INTERVAL_1H = "1h";
    public static final ArrayList<String> specialSymbol = new ArrayList<String>(    Arrays.asList("BTCUSDT", "ETHUSDT", "BNBUSDT"));
    public static final String URL_TICKER = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&interval=";    
    public static final String URL_TICKER_STARTTIME = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&startTime=tttttt&interval=";    
}
