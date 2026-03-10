/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.binance.chuyennd.utils;

import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.StringUtils;

import java.io.File;
import java.net.URI;
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

    public static boolean IS_HPO_MODE = false;
    // Mặc định là false, sẽ được ghi đè nếu trong config.properties có key này
    public static boolean IS_KAGGLE_MODE = properties.get("IS_KAGGLE_MODE") != null
            ? getBoolean("IS_KAGGLE_MODE")
            : false;
    // Thêm dòng này vào Configs.java
// Các tham số đã được cập nhật từ kết quả tối ưu hóa Funding Fee
    public static double PREDICT_SYMBOL_RATE_MAX_THRESHOLD = 0.2; // Cập nhật từ FUNDING_PRED_MAX_THRESHOLD

    // Nhóm tham số lọc tín hiệu thị trường (Market Filters)
    public static Double PREDICT_SYMBOL_RATE_DOWN_15M = -0.03234;  // Param 2
    public static Double PREDICT_SYMBOL_RATE_UP_AVG = 0.00454;          // Param 3
    public static Double PREDICT_SYMBOL_RATE_DOWN_AVG = -0.00503;

    // Tham số bổ sung từ kết quả HPO


    // 1. Ngưỡng margin-ratio đầu tiên để giảm budget
    public static double BUDGET_MARGIN_RATIO_1 = 0.4820;
    // 2. Mức chia budget ở ngưỡng 1
    public static double BUDGET_DIVIDER_1 = 1.5578;

    // 3. Ngưỡng margin-ratio thứ hai
    public static double BUDGET_MARGIN_RATIO_2 = 0.7475;
    // 4. Mức chia budget ở ngưỡng 2
    public static double BUDGET_DIVIDER_2 = 1.5984;


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

    public static Integer NUMBER_RATE_DOWN_HISTORY_TRADE = 60;


    public static final Integer NUMBER_THREAD_ORDER_MANAGER = Configs.getInt("NUMBER_THREAD_ORDER_MANAGER");
    public static Integer NUMBER_ENTRY_EACH_SIGNAL = Configs.getInt("NUMBER_ENTRY_EACH_SIGNAL");
    public static Integer NUMBER_TICKER_CAL_RATE_CHANGE = Configs.getInt("NUMBER_TICKER_CAL_RATE_CHANGE");

    public static final Double RATE_FEE = Configs.getDouble("RATE_FEE");
    public static Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");

    // kaggle
//    public static String FILE_ENTRY_MARKET_LEVEL = "storage/market_data_one_file/time2market.data";
//    public static String FILE_ENTRY_MARKET_LEVEL = Configs.getString("FILE_ENTRY_MARKET_LEVEL");


    // aerospike
    public static final String AEROSPIKE_HOST_242 = Configs.getString("AEROSPIKE_HOST"); //"127.0.0.1";
    public static final int AEROSPIKE_PORT_242 = Configs.getInt("AEROSPIKE_PORT");
    public static final String AEROSPIKE_HOST_226 = Configs.getString("AEROSPIKE_HOST_226"); //"127.0.0.1";
    public static final int AEROSPIKE_PORT_226 = Configs.getInt("AEROSPIKE_PORT_226");

    public static final String AEROSPIKE_SET_NAME_FUNDING_PRED = Configs.getString("AEROSPIKE_SET_NAME_FUNDING_PRED");
    public static final String AEROSPIKE_SET_NAME_PRED_40 = Configs.getString("AEROSPIKE_SET_NAME_PRED_40");


    public static final String AEROSPIKE_NAMESPACE = Configs.getString("AEROSPIKE_NAMESPACE"); //"ticker" ;
    public static final String FILE_AI_ENTRY_PREDICTIONS = Configs.getString("FILE_AI_PREDICTIONS"); //"ticker" ;

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

    // =========================================================
    // 1. NHÓM 8 THAM SỐ ĐÃ ĐƯỢC UPDATE TỪ KẾT QUẢ HPO
    // =========================================================
    public static double MS_UP_BIG_THRES = 0.02046;  // Default cũ: 0.025
    public static double MS_DOWN_BIG_AVG = -0.03157; // Default cũ: -0.032

    public static double MS_UP_MED_THRES = 0.01204;  // Default cũ: 0.015
    public static double MS_DOWN_MED_AVG = -0.02069; // Default cũ: -0.030

    public static double MS_UP_SMALL_THRES = 0.00442;  // Default cũ: 0.008
    public static double MS_DOWN_SMALL_AVG = -0.01713; // Default cũ: -0.006

    public static double MS_DOWN_15M_MED_ONLY = -0.06725; // Default cũ: -0.045
    public static double MS_DOWN_15M_SMALL_ONLY = -0.02145; // Default cũ: -0.028

    // =========================================================
    // 2. NHÓM 4 THAM SỐ THIẾU TRONG HPO (GIỮ NGUYÊN DEFAULT)
    // =========================================================
    public static double MS_DOWN_BIG_BTC = -0.01;  // Default: -0.01

    public static double MS_DOWN_MED_AVG_CMB = -0.014; // Default: -0.014 (Combined logic)
    public static double MS_DOWN_MED_15M_CMB = -0.07;  // Default: -0.07  (Combined logic)

    public static double MS_DOWN_SMALL_15M = -0.025; // Default: -0.025 (Combined logic)


    public static void main(String[] args) {

    }
}
