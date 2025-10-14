/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.binance.chuyennd.utils;

import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.StringUtils;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * @author chuyennd
 */
public class Configs {


    public static String configFile = "config.properties";
    public static volatile Map properties = new HashMap();

    static {
        try {
            File configFile = new File(Configs.configFile);
            List<String> lines = FileUtils.readLines(configFile);
            for (String line : lines) {
                if (StringUtils.contains(line, "=")) {
                    properties.put(line.split("=")[0].trim(), line.split("=")[1].trim());
                }
            }
        } catch (Exception e) {
            System.err.println("Do not read config file: " + configFile);
            e.printStackTrace();
            System.exit(0);
        }
    }

    public static String TIME_RUN = Configs.getString("TIME_RUN");
    //budget config
    public static Integer number_order_budget = 120;

    // funding fee config
    public static final Integer NUMBER_LAST_FUNDING_CAL = 8;
    public static final Integer NUMBER_LAST_FUNDING_EXTREME = 4;
    public static final Integer NUMBER_HOUR_FUNDING_CAL = 30;
    public static final Double FUNDING_MAX_TRADE = 0.00001;
    public static final Double FUNDING_MIN_TRADE = 0.0006;
    public static final int NUMBER_TICKER_RATE_CHANGE_MAX_TRADE = 60;
    public static final Long FUNDING_TIME_EXTREME = 12 * Utils.TIME_HOUR;
    public static final Double FUNDING_MAX_TRADE_EXTREME = -0.0003;


    public static final Integer NUMBER_THREAD_ORDER_MANAGER = Configs.getInt("NUMBER_THREAD_ORDER_MANAGER");
    public static boolean MOD_RUN_CAPITAL_CONSTANT = Configs.getBoolean("MOD_RUN_CAPITAL_CONSTANT");
    public static Integer NUMBER_ENTRY_EACH_SIGNAL = Configs.getInt("NUMBER_ENTRY_EACH_SIGNAL");
    public static Integer NUMBER_TICKER_CAL_RATE_CHANGE = Configs.getInt("NUMBER_TICKER_CAL_RATE_CHANGE");
    public static final Double RATE_PROFIT_STOP_MARKET = Configs.getDouble("RATE_PROFIT_STOP_MARKET");
    public static Integer SMA_LONG = Configs.getInt("SMA_LONG");
    public static Integer SMA_SHORT = Configs.getInt("SMA_SHORT");
    public static final Double RATE_FEE = Configs.getDouble("RATE_FEE");
    public static Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");

    public static String FOLDER_TICKER_15M = Configs.getString("FOLDER_TICKER_15M");//"../ticker/storage/ticker/symbols-15m/";
    public static String FOLDER_TICKER_1M = Configs.getString("FOLDER_TICKER_1M");//"../ticker/storage/ticker/symbols-15m/";
    public static String FOLDER_FUNDING_FEE = Configs.getString("FOLDER_FUNDING_FEE");//"../ticker/storage/ticker/symbols-15m/";
    public static String FOLDER_TICKER_1M_PRODUCTION = Configs.getString("FOLDER_TICKER_1M_PRODUCTION");//"../ticker/storage/ticker/symbols-15m/";
    public static String FOLDER_TICKER_15M_FILE = Configs.getString("FOLDER_TICKER_15M_FILE");
    public static String FOLDER_TICKER_1M_FILE = Configs.getString("FOLDER_TICKER_1M_FILE");
    public static String FOLDER_TICKER_1M_SNAPPY_FILE = "../storage/ticker/ticker1m-snappy/";
    public static final String FOLDER_TICKER_1M_PROTOBUF_SNAPPY_FILE = "../storage/ticker/ticker1m-protobuf/";
    public static final String FOLDER_TICKER_1M_PROTOBUF_SNAPPY_FILE_FULL = "../storage/ticker/ticker1m-protobuf-full/";
    public static String FOLDER_TICKER_HOUR = Configs.getString("FOLDER_TICKER_1H");//"../ticker/storage/ticker/symbols-1h/";
    public static String FOLDER_TICKER_4HOUR = Configs.getString("FOLDER_TICKER_4H");//"../ticker/storage/ticker/symbols-4h/";
    public static String FOLDER_TICKER_1D = Configs.getString("FOLDER_TICKER_1D");//"../ticker/storage/ticker/symbols-1D/";
    public static String FILE_DATA_LOADED = Configs.getString("FILE_DATA_LOADED");//"storage/macd_data_time";
    public static Integer BTC_TREND_REVERSE_DURATION = Configs.getInt("BTC_TREND_REVERSE_DURATION");
    public static Double BTC_TREND_REVERSE_RATE_MAX = Configs.getDouble("BTC_TREND_REVERSE_RATE_MAX");
    public static Double BTC_TREND_REVERSE_RATE_MIN = Configs.getDouble("BTC_TREND_REVERSE_RATE_MIN");
    public static Double BTC_TREND_REVERSE_RATE_MIN_TRADE = Configs.getDouble("BTC_TREND_REVERSE_RATE_MIN_TRADE");

    public static String FILE_ENTRY_MARKET_LEVEL = "../storage/market_data/time2market.data";
    public static String FILE_TIME_SYMBOL_EXHAUSTED = "../storage/market_data/time2SymbolSellingExhausted.data";
    public static String FILE_MARKET_RATE_CHANGE = "../storage/market_data/marketRateChange.data";

    public static String FILE_ENTRY_BTC_REVERSE = "../storage/btc/btcReverse-" + BTC_TREND_REVERSE_RATE_MIN + "-" + BTC_TREND_REVERSE_RATE_MAX + "-"
            + BTC_TREND_REVERSE_DURATION;

    public static final String URL_PREMIUM_INDEX = "https://fapi.binance.com/fapi/v1/premiumIndex";

    public static String getString(String configName) {
        return (String) properties.get(configName);
    }

    public static int getInt(String configName) {
        return Integer.parseInt((String) properties.get(configName));
    }

    public static Boolean getBoolean(String configName) {
        return Boolean.parseBoolean((String) properties.get(configName));
    }

    public static long getLong(String configName) {
        return Long.parseLong((String) properties.get(configName));
    }

    public static double getDouble(String configName) {
        return Double.parseDouble((String) properties.get(configName));
    }

    public static void main(String[] args) {

    }
}
