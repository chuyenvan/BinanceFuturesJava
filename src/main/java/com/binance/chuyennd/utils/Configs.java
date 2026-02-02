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


    public static final String FILE_TICKER_1M_STORAGE = "storage/tickers/symbol2ticker1Ms";
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

    public static Double FUNDING_RATE_MIN_TRADE = -0.01720;      // Param 1
    public static Double FUNDING_RATE_MIN_TRADE_FULL = -0.03234;  // Param 2
    public static Double FUNDING_RATE_UP_AVG = 0.00454;          // Param 3
    public static Double FUNDING_RATE_DOWN_AVG = -0.00503;       // Param 4

    // 1. Ngưỡng margin-ratio đầu tiên để giảm budget
    public static double BUDGET_MARGIN_RATIO_1 = 0.4820;
    // 2. Mức chia budget ở ngưỡng 1
    public static double BUDGET_DIVIDER_1 = 1.5578;

    // 3. Ngưỡng margin-ratio thứ hai
    public static double BUDGET_MARGIN_RATIO_2 = 0.7475;
    // 4. Mức chia budget ở ngưỡng 2
    public static double BUDGET_DIVIDER_2 = 1.5984;


    // --- CẤU HÌNH TRAILING STOP ĐỘNG (DYNAMIC) ---
    // Ngưỡng biến động (Volatility Thresholds) - Mặc định cũ: 0.01, 0.006, 0.004
//    public static Double RATE_PROFIT_STOP_MARKET = Configs.getDouble("RATE_PROFIT_STOP_MARKET");
//    public static double TS_VOL_HIGH_THRES = 0.01;
//    public static double TS_VOL_MED_THRES = 0.006;
//    public static double TS_VOL_LOW_THRES = 0.004;
//
//    // Mức chốt lời tương ứng (Target Rates) - Mặc định cũ: 0.03, 0.02, 0.016
//    public static double TS_RATE_HIGH = 0.03;
//    public static double TS_RATE_MED = 0.02;
//    public static double TS_RATE_LOW = 0.016;

    // Base Rate (Mức lãi tối thiểu để kích hoạt Trailing Stop)


    /*
    [root@web003 ~]#
        Base Rate:             0.01151
        --- HIGH VOLATILITY ---
        Threshold:             0.01760
        Target Rate:           0.05549
        --- MEDIUM VOLATILITY ---
        Threshold:             0.01020
        Target Rate:           0.04172
        --- LOW VOLATILITY ---
        Threshold:             0.00239
        Target Rate:           0.01189


        === KẾT QUẢ TỐI ƯU TRAILING STOP ===
        Time: 218 mins
        Profit Max: 74413.5656257369
        ------------------------------------
        Base Rate:             0.01651
        --- HIGH VOLATILITY ---
        Threshold:             0.02433
        Target Rate:           0.05105
        --- MEDIUM VOLATILITY ---
        Threshold:             0.01106
        Target Rate:           0.04157
        --- LOW VOLATILITY ---
        Threshold:             0.00289
        Target Rate:           0.01850

     */
    public static double RATE_PROFIT_STOP_MARKET = 0.01151;

    // --- HIGH VOLATILITY (Biến động mạnh) ---
    public static double TS_VOL_HIGH_THRES = 0.01760; // Ngưỡng nhận diện High Vol
    public static double TS_RATE_HIGH = 0.05549; // Target dời SL khi High Vol

    // --- MEDIUM VOLATILITY (Biến động vừa) ---
    public static double TS_VOL_MED_THRES = 0.01020; // Ngưỡng nhận diện Med Vol
    public static double TS_RATE_MED = 0.04172; // Target dời SL khi Med Vol

    // --- LOW VOLATILITY (Biến động thấp) ---
    public static double TS_VOL_LOW_THRES = 0.00239; // Ngưỡng nhận diện Low Vol
    public static double TS_RATE_LOW = 0.01189; // Ta
//
//    // Mức chốt lời tương ứng (Target Rates)
//    public static double TS_RATE_HIGH = 0.04799;      // Gồng lãi cực mạnh ~4.8% (Cũ: 3%)
//    public static double TS_RATE_MED = 0.02463;       // Gồng lãi ~2.5% (Cũ: 2%)
//    public static double TS_RATE_LOW = 0.01415;       // Chốt sớm ~1.4% (


    public static String TIME_RUN = Configs.getString("TIME_RUN");
    //budget config
    public static Integer number_order_budget = 70;

    public static final Integer NUMBER_RATE_DOWN_HISTORY_TRADE = 20;
    // funding fee config
    public static final Integer NUMBER_HOUR_FUNDING_CAL = 30;
    public static final Double FUNDING_MAX_TRADE = -0.00001;
    public static final Double FUNDING_MIN_TRADE = 0.00065;
    public static final int NUMBER_TICKER_RATE_CHANGE_MAX_TRADE = 60;


    public static final Integer NUMBER_THREAD_ORDER_MANAGER = Configs.getInt("NUMBER_THREAD_ORDER_MANAGER");
    public static Integer NUMBER_ENTRY_EACH_SIGNAL = Configs.getInt("NUMBER_ENTRY_EACH_SIGNAL");
    public static Integer NUMBER_TICKER_CAL_RATE_CHANGE = Configs.getInt("NUMBER_TICKER_CAL_RATE_CHANGE");

    public static final Double RATE_FEE = Configs.getDouble("RATE_FEE");
    public static Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");

    public static Integer BTC_TREND_REVERSE_DURATION = Configs.getInt("BTC_TREND_REVERSE_DURATION");
    public static Double BTC_TREND_REVERSE_RATE_MAX = Configs.getDouble("BTC_TREND_REVERSE_RATE_MAX");
    public static Double BTC_TREND_REVERSE_RATE_MIN_TRADE = Configs.getDouble("BTC_TREND_REVERSE_RATE_MIN_TRADE");

    public static String FILE_ENTRY_MARKET_LEVEL = "../storage/market_data_one_file/time2market.data";


    // aerospike
    public static final String AEROSPIKE_HOST_242 = Configs.getString("AEROSPIKE_HOST"); //"127.0.0.1";
    public static final int AEROSPIKE_PORT_242 = Configs.getInt("AEROSPIKE_PORT");
    public static final String AEROSPIKE_HOST_226 = Configs.getString("AEROSPIKE_HOST_226"); //"127.0.0.1";
    public static final int AEROSPIKE_PORT_226 = Configs.getInt("AEROSPIKE_PORT_226");


    public static final String AEROSPIKE_NAMESPACE = Configs.getString("AEROSPIKE_NAMESPACE"); //"ticker" ;
    public static final String FILE_AI_ENTRY_PREDICTIONS = Configs.getString("FILE_AI_PREDICTIONS"); //"ticker" ;
    public static final String FILE_AI_DCA_MODEL = Configs.getString("FILE_AI_DCA_PREDICTIONS"); //"ticker" ;

    public static String getString(String configName) {
        return (String) properties.get(configName);
    }

    public static int getInt(String configName) {
        return Integer.parseInt((String) properties.get(configName));
    }

    public static Boolean getBoolean(String configName) {
        return Boolean.parseBoolean((String) properties.get(configName));
    }

    public static double getDouble(String configName) {
        return Double.parseDouble((String) properties.get(configName));
    }

    // Trong file com.binance.chuyennd.utils.Configs

    // === MARKET STATUS THRESHOLDS (Mặc định ban đầu) ===
    public static double MS_UP_BIG_THRES       = 0.025;  // Default: 0.025

    public static double MS_DOWN_BIG_AVG       = -0.032; // Default: -0.032
    public static double MS_DOWN_BIG_BTC       = -0.01;  // Default: -0.01

    public static double MS_UP_MED_THRES       = 0.015;  // Default: 0.015

    public static double MS_DOWN_MED_AVG       = -0.030; // Default: -0.030
    public static double MS_DOWN_MED_AVG_CMB   = -0.014; // Default: -0.014 (Combined logic)
    public static double MS_DOWN_MED_15M_CMB   = -0.07;  // Default: -0.07  (Combined logic)

    public static double MS_UP_SMALL_THRES     = 0.008;  // Default: 0.008

    public static double MS_DOWN_SMALL_AVG     = -0.006; // Default: -0.006
    public static double MS_DOWN_SMALL_15M     = -0.025; // Default: -0.025 (Combined logic)

    public static double MS_DOWN_15M_MED_ONLY  = -0.045; // Default: -0.045
    public static double MS_DOWN_15M_SMALL_ONLY= -0.028; // Default: -0.028

    public static void main(String[] args) {

    }
}
