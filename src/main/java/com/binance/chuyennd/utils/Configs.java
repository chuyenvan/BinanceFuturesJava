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
    public static int MAX_CONCURRENT_ORDERS = 40;
    // Tham số kiểm soát mật độ vào lệnh (Đưa vào HPO)
    public static float RECOVERY_RATE_PER_MIN = 1.0f;   // Số lệnh xả tối đa ngay phút đầu

    public static float DENSITY_SUSTAIN = 10.0f; // HPO: Dò từ 5 -> 20
    public static float DENSITY_ALPHA = 0.6f;    // HPO: Dò từ 0.2 -> 0.8 (Độ cong)


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
    public static float PREDICT_SYMBOL_RATE_MAX_THRESHOLD = 0.15f; // Cập nhật từ FUNDING_PRED_MAX_THRESHOLD

    // Nhóm tham số lọc tín hiệu thị trường (Market Filters)
    public static float PREDICT_SYMBOL_RATE_DOWN_15M = -0.03234f;  // Param 2
    public static float PREDICT_SYMBOL_RATE_UP_AVG = 0.00454f;          // Param 3
    public static float PREDICT_SYMBOL_RATE_DOWN_AVG = -0.00503f;




    // 1. Ngưỡng margin-ratio đầu tiên để giảm budget
    public static float BUDGET_MARGIN_RATIO_1 = 0.4820f;
    // 2. Mức chia budget ở ngưỡng 1
    public static float BUDGET_DIVIDER_1 = 1.5578f;

    // 3. Ngưỡng margin-ratio thứ hai
    public static float BUDGET_MARGIN_RATIO_2 = 0.7475f;
    // 4. Mức chia budget ở ngưỡng 2
    public static float BUDGET_DIVIDER_2 = 1.5984f;


    public static float RATE_PROFIT_STOP_MARKET = 0.01032f;
    public static float TS_DYNAMIC_K = 0.29774f;
    public static float TS_PROFIT_MULTIPLIER = 5.21847f;

    // --- HIGH VOLATILITY (Biến động mạnh) ---
    public static float TS_VOL_HIGH_THRES = 0.01760f; // Ngưỡng nhận diện High Vol
    public static float TS_RATE_HIGH = 0.05549f; // Target dời SL khi High Vol

    // --- MEDIUM VOLATILITY (Biến động vừa) ---
    public static float TS_VOL_MED_THRES = 0.01020f; // Ngưỡng nhận diện Med Vol
    public static float TS_RATE_MED = 0.04172f; // Target dời SL khi Med Vol

    // --- LOW VOLATILITY (Biến động thấp) ---
    public static float TS_VOL_LOW_THRES = 0.00239f; // Ngưỡng nhận diện Low Vol
    public static float TS_RATE_LOW = 0.01189f; // Ta


    public static String TIME_RUN = Configs.getString("TIME_RUN");
    //budget config
    public static Integer number_order_budget = 50;

    // Nhóm tham số lọc tín hiệu thị trường (Geometric Filters)
    public static float BASE_DOWN = 0.006f;
    public static float RATIO_DOWN = 2.0f;
    public static float BASE_UP = 0.005f;
    public static float RATIO_UP = 2.0f;

    public static final Integer NUMBER_THREAD_ORDER_MANAGER = Configs.getInt("NUMBER_THREAD_ORDER_MANAGER");
    public static Integer NUMBER_ENTRY_EACH_SIGNAL = Configs.getInt("NUMBER_ENTRY_EACH_SIGNAL");
    public static Integer NUMBER_TICKER_CAL_RATE_CHANGE = Configs.getInt("NUMBER_TICKER_CAL_RATE_CHANGE");

    // Funding Fee related configurations
    public static Integer NUMBER_HOUR_FUNDING_CAL = Configs.getInt("NUMBER_HOUR_FUNDING_CAL");
    public static float FUNDING_MAX_TRADE = Configs.getDouble("FUNDING_MAX_TRADE");
    public static float FUNDING_MIN_TRADE = Configs.getDouble("FUNDING_MIN_TRADE");

    public static final Float RATE_FEE = Configs.getDouble("RATE_FEE");
    public static Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");


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

    public static float getDouble(String configName) {
        return Float.parseFloat((String) properties.get(configName));
    }

    // =========================================================
    // 1. NHÓM 8 THAM SỐ ĐÃ ĐƯỢC UPDATE TỪ KẾT QUẢ HPO
    // =========================================================
    public static float MS_UP_BIG_THRES = 0.02046f;  // Default cũ: 0.025
    public static float MS_DOWN_BIG_AVG = -0.03157f; // Default cũ: -0.032

    public static float MS_UP_MED_THRES = 0.01204f;  // Default cũ: 0.015
    public static float MS_DOWN_MED_AVG = -0.02069f; // Default cũ: -0.030

    public static float MS_UP_SMALL_THRES = 0.00442f;  // Default cũ: 0.008
    public static float MS_DOWN_SMALL_AVG = -0.01713f; // Default cũ: -0.006

    public static float MS_DOWN_15M_MED_ONLY = -0.06725f; // Default cũ: -0.045
    public static float MS_DOWN_15M_SMALL_ONLY = -0.02145f; // Default cũ: -0.028

    // =========================================================
    // 2. NHÓM 4 THAM SỐ THIẾU TRONG HPO (GIỮ NGUYÊN DEFAULT)
    // =========================================================
    public static float MS_DOWN_BIG_BTC = -0.01f;  // Default: -0.01

    public static float MS_DOWN_MED_AVG_CMB = -0.014f; // Default: -0.014 (Combined logic)
    public static float MS_DOWN_MED_15M_CMB = -0.07f;  // Default: -0.07  (Combined logic)

    public static float MS_DOWN_SMALL_15M = -0.025f; // Default: -0.025 (Combined logic)


    public static void main(String[] args) {

    }
}
