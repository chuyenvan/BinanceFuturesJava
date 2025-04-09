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
public class GridConfigs {
    public static String configFile = "grid.properties";
    public static volatile Map properties = new HashMap();

    static {
        try {
            File configFile = new File(GridConfigs.configFile);
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


    public static  Double GRID_RATE_TRADE = GridConfigs.getDouble("GRID_RATE_TRADE");
    public static  Double GRID_RATE_BUY_OVER = GridConfigs.getDouble("GRID_RATE_BUY_OVER");
    public static  Double GRID_RATE_SELL_OVER = GridConfigs.getDouble("GRID_RATE_SELL_OVER");
    public static Integer GRID_NUMBER_ORDER_ACTIVE = GridConfigs.getInt("GRID_NUMBER_ORDER_ACTIVE");
    public static Integer SMA_LONG = GridConfigs.getInt("SMA_LONG");
    public static Integer SMA_SHORT = GridConfigs.getInt("SMA_SHORT");
    public static Double RATE_DOWN_4H_REVERSE = GridConfigs.getDouble("RATE_DOWN_4H_REVERSE");
    public static Integer NUMBER_MIN_CLOSE_PRICE_REVERSE = GridConfigs.getInt("NUMBER_MIN_CLOSE_PRICE_REVERSE");




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
