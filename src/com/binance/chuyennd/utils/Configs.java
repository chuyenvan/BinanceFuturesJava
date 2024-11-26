/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.binance.chuyennd.utils;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.io.FileUtils;

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
    ;
    public static final Integer NUMBER_THREAD_ORDER_MANAGER = Configs.getInt("NUMBER_THREAD_ORDER_MANAGER");
    public static boolean MOD_RUN_CAPITAL_CONSTANT = Configs.getBoolean("MOD_RUN_CAPITAL_CONSTANT");
    public static Integer NUMBER_ENTRY_EACH_SIGNAL = Configs.getInt("NUMBER_ENTRY_EACH_SIGNAL");
    public static Integer NUMBER_TICKER_CAL_RATE_CHANGE = Configs.getInt("NUMBER_TICKER_CAL_RATE_CHANGE");
    public static final Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public static final Double RATE_STOP_LOSS = Configs.getDouble("RATE_STOP_LOSS");
    public static final Double RATE_PROFIT_STOP_MARKET = Configs.getDouble("RATE_PROFIT_STOP_MARKET");
    public static final Double MAX_CAPITAL_RATE = Configs.getDouble("MAX_CAPITAL_RATE");
    public static final Double RATE_FEE = Configs.getDouble("RATE_FEE");
    public static Double RATE_TICKER_MAX_SCAN_ORDER = Configs.getDouble("RATE_TICKER_MAX_SCAN_ORDER");
    public static final Double RATE_BUDGET_LIMIT_A_SIGNAL = Configs.getDouble("RATE_BUDGET_LIMIT_A_SIGNAL");
    public static final Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");

    public static String FOLDER_TICKER_15M = Configs.getString("FOLDER_TICKER_15M");//"../ticker/storage/ticker/symbols-15m/";
    public static String FOLDER_TICKER_1M = Configs.getString("FOLDER_TICKER_1M");//"../ticker/storage/ticker/symbols-15m/";
    public static String FOLDER_TICKER_1M_PRODUCTION = Configs.getString("FOLDER_TICKER_1M_PRODUCTION");//"../ticker/storage/ticker/symbols-15m/";
    public static String FOLDER_TICKER_15M_FILE = Configs.getString("FOLDER_TICKER_15M_FILE");
    public static String FOLDER_TICKER_1M_FILE = Configs.getString("FOLDER_TICKER_1M_FILE");
    public static String FOLDER_TICKER_HOUR = Configs.getString("FOLDER_TICKER_1H");//"../ticker/storage/ticker/symbols-1h/";
    public static String FOLDER_TICKER_4HOUR = Configs.getString("FOLDER_TICKER_4H");//"../ticker/storage/ticker/symbols-4h/";
    public static String FOLDER_TICKER_1D = Configs.getString("FOLDER_TICKER_1D");//"../ticker/storage/ticker/symbols-1D/";
    public static String FILE_DATA_LOADED = Configs.getString("FILE_DATA_LOADED");//"storage/macd_data_time";
    public static Integer TIME_AFTER_ORDER_2_SL = Configs.getInt("TIME_AFTER_ORDER_2_SL");

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
