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

import com.binance.chuyennd.utils.Configs;
import org.apache.commons.lang.StringUtils;

import java.util.ArrayList;

/**
 * @author pc
 */
public class Constants {

    public static final String SYMBOL_PAIR_BTC = "BTCUSDT";
    public static final String INTERVAL_1M = "1m";
    public static final String INTERVAL_15M = "15m";
    public static final String INTERVAL_1D = "1d";
    public static final String INTERVAL_1H = "1h";
    public static final String INTERVAL_4H = "4h";
    public static final String INTERVAL_6H = "6h";
    public static final String INTERVAL_8H = "8h";
    public static final String INTERVAL_12H = "12h";
    public static final String INTERVAL_1W = "1w";
    public static final String INTERVAL_1MONTH = "1M";
    public static final String TRADING_TYPE_BREAD = "TRADING_TYPE_BREAD";
    public static final String TRADING_TYPE_VOLUME_MINI = "TRADING_TYPE_VOLUME_MINI";
    public static final String TRADING_TYPE_SIGNAL = "TRADING_TYPE_SIGNALTW";
    public static final ArrayList<String> diedSymbol = new ArrayList<>();
    public static final ArrayList<String> specialSymbol = new ArrayList<>();
//    public static final ArrayList<String> specialSymbol = new ArrayList<>(Arrays.asList(
//            "STPTUSDT",
//            "SNTUSDT",
//            "MBLUSDT",
//            "RADUSDT",
//            "CVXUSDT",
//            "IDEXUSDT",
//            "SLPUSDT",
//            "GLMRUSDT",
//            "MDTUSDT",
//            "AUDIOUSDT",
//            "BLUEBIRDUSDT",
//            "FOOTBALLUSDT",
//            "ANTUSDT",
//            "CTKUSDT",
//            "DGBUSDT",
//            "STRAXUSDT",
//            "COCOSUSDT",
//            "RAYUSDT",
//            "FTTUSDT",
//            "SCUSDT",
//            "HNTUSDT",
//            "BTCSTUSDT",
//            "BTSUSDT",
//            "TOMOUSDT",
//            "SRMUSDT",
//            "CVCUSDT",
//            "USDCUSDT"));
    public static final String URL_TICKER_FUTURES = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&interval=";
    public static final String URL_TICKER_FUTURES_STARTTIME = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&startTime=tttttt&interval=";
    public static final String URL_TICKER_SPOT = "https://api.binance.com/api/v1/klines?symbol=xxxxxx&interval=";
    public static final String URL_TICKER_SPOT_STARTTIME = "https://api.binance.com/api/v1/klines?symbol=xxxxxx&startTime=tttttt&interval=";

    static {
        String symbols = Configs.getString("DIED_SYMBOLS");
        for (String symbol : StringUtils.split(symbols, ",")) {
            diedSymbol.add(symbol);
        }
        symbols = Configs.getString("SPECIAL_SYMBOLS");
        for (String symbol : StringUtils.split(symbols, ",")) {
            specialSymbol.add(symbol);
        }
    }

    public static void main(String[] args) {
        System.out.println(Constants.diedSymbol);
    }
}
