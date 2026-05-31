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

import com.binance.chuyennd.tradecore.Configs;
import org.apache.commons.lang.StringUtils;

import java.util.HashSet;
import java.util.Set;

/**
 * @author pc
 */
public class Constants {

    public static final String SYMBOL_PAIR_BTC = "BTCUSDT";
    public static final String SYMBOL_PAIR_ETH = "ETHUSDT";
    public static final String SYMBOL_PAIR_BNB = "BNBUSDT";
    public static final String SYMBOL_PAIR_SOL = "SOLUSDT";
    public static final String SYMBOL_PAIR_XRP = "XRPUSDT";
    public static final String SYMBOL_PAIR_ADA = "ADAUSDT";
    public static final String SYMBOL_PAIR_AVAX = "AVAXUSDT";
    public static final String SYMBOL_PAIR_LINK = "LINKUSDT";
    public static final String SYMBOL_PAIR_DOGE = "DOGEUSDT";
    public static final String SYMBOL_PAIR_AAVE = "AAVEUSDT";
    public static final String INTERVAL_1M = "1m";
    public static final String INTERVAL_15M = "15m";
    public static final String INTERVAL_1D = "1d";
    public static final String INTERVAL_3D = "3d";
    public static final String INTERVAL_1H = "1h";
    public static final String INTERVAL_4H = "4h";
    public static final String INTERVAL_12H = "12h";
    public static final String INTERVAL_1W = "1w";
    public static final String INTERVAL_1MONTH = "1M";
    public static final String TRADING_TYPE_BREAD = "TRADING_TYPE_BREAD";
    public static final String TRADING_TYPE_VOLUME_MINI = "TRADING_TYPE_VOLUME_MINI";


    public static final Set<String> diedSymbol = new HashSet<>();
    public static final Set<String> allSymbolStable = new HashSet<>();
    public static final Set<String> specialSymbol = new HashSet<>();
    public static final Set<String> stableSymbol = new HashSet<>();
    public static final Set<String> btcReverseSymbol = new HashSet<>();
    public static final String URL_TICKER_FUTURES = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&interval=";
    public static final String URL_TICKER_FUTURES_STARTTIME = "https://fapi.binance.com/fapi/v1/klines?symbol=xxxxxx&startTime=tttttt&interval=";
    public static final String URL_FUNDING_FEE_FUTURES_START_TIME = "https://fapi.binance.com/fapi/v1/fundingRate?startTime=tttttt&symbol=xxxxxx";

    static {
        String symbols = Configs.getString("DIED_SYMBOLS");
        for (String symbol : StringUtils.split(symbols, ",")) {
            if (!StringUtils.contains(symbol, "USDT")) {
                symbol = symbol + "USDT";
            }
            diedSymbol.add(symbol);
        }
        symbols = Configs.getString("SPECIAL_SYMBOLS");
        for (String symbol : StringUtils.split(symbols, ",")) {
            if (!StringUtils.contains(symbol, "USDT")) {
                symbol = symbol + "USDT";
            }
            specialSymbol.add(symbol);
        }
        symbols = Configs.getString("STABLE_SYMBOLS");
        for (String symbol : StringUtils.split(symbols, ",")) {
            if (!StringUtils.contains(symbol, "USDT")) {
                symbol = symbol + "USDT";
            }
            stableSymbol.add(symbol);
        }
        symbols = Configs.getString("BTC_REVERSE_SYMBOLS");
        for (String symbol : StringUtils.split(symbols, ",")) {
            if (!StringUtils.contains(symbol, "USDT")) {
                symbol = symbol + "USDT";
            }
            btcReverseSymbol.add(symbol);
        }
        allSymbolStable.addAll(specialSymbol);
        allSymbolStable.addAll(stableSymbol);
        allSymbolStable.addAll(btcReverseSymbol);
    }

    public static void main(String[] args) {

        System.out.println(Constants.diedSymbol);
    }
}
