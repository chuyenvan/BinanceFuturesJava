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
 * Class quản lý toàn bộ cấu hình siêu tham số của hệ thống Bot Trading.
 */
public class Configs {

    // =========================================================
    // 1. HỆ THỐNG & KHỞI TẠO (SYSTEM & INIT)
    // =========================================================
    public static String configFile = "config.properties";
    public static volatile Map<String, String> properties = new HashMap<>();

    static {
        try {
            File file = new File(Configs.configFile);
            List<String> lines = FileUtils.readLines(file, "UTF-8");
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

    // =========================================================
    // 2. CHẾ ĐỘ CHẠY (RUNNING MODES)
    // =========================================================
    public static boolean IS_HPO_MODE = false; // Bật khi chạy tối ưu hóa Jenetics
    public static boolean IS_KAGGLE_MODE = properties.get("IS_KAGGLE_MODE") != null
            ? getBoolean("IS_KAGGLE_MODE")
            : false;
    public static String TIME_RUN = Configs.getString("TIME_RUN");

    // =========================================================
    // 3. CẤU HÌNH GIAO DỊCH CƠ BẢN (BASIC TRADING)
    // =========================================================
    public static Integer LEVERAGE_ORDER = 1; // Đòn bẩy
    public static final Float RATE_FEE = 0.001f; // Phí giao dịch sàn
    public static Integer NUMBER_ENTRY_EACH_SIGNAL = 2; // Số lệnh vào mỗi khi có tín hiệu
    public static Integer NUMBER_TICKER_CAL_RATE_CHANGE = 15; // Số nến để tính biến động
    public static final Integer NUMBER_THREAD_ORDER_MANAGER = Configs.getInt("NUMBER_THREAD_ORDER_MANAGER");

    // =========================================================
    // 4. QUẢN TRỊ VỐN TỰ ĐỘNG (BUDGET MANAGEMENT - HPO)
    // =========================================================
    public static Integer number_order_budget = 50; // Tổng số phần chia vốn

    // Ngưỡng bóp vốn 1: Khi dùng hết x% vốn, chia nhỏ budget đi y lần
    public static float BUDGET_MARGIN_RATIO_1 = 0.4820f;
    public static float BUDGET_DIVIDER_1 = 1.5578f;

    // Ngưỡng bóp vốn 2: Khi dùng hết x% vốn, tiếp tục chia nhỏ budget đi y lần
    public static float BUDGET_MARGIN_RATIO_2 = 0.7475f;
    public static float BUDGET_DIVIDER_2 = 1.5984f;

    // =========================================================
    // 5. CẦU DAO & MẬT ĐỘ LỆNH (CIRCUIT BREAKER - HPO)
    // =========================================================
    public static int MAX_CONCURRENT_ORDERS = 40; // Số lệnh tối đa cùng chạy
    public static float DENSITY_SUSTAIN = 10.0f;  // Sức chịu đựng mật độ mở lệnh
    public static float DENSITY_ALPHA = 0.6f;     // Độ cong của hàm kiểm soát mật độ

    // =========================================================
    // 6. TRAILING STOP ĐỘNG (DYNAMIC TRAILING - HPO)
    // =========================================================
    public static float RATE_PROFIT_STOP_MARKET = 0.01032f; // Khoảng dời SL tối thiểu (Base rate)
    public static float TS_DYNAMIC_K = 0.29774f;            // Hệ số nhân Volatility để dời SL
    public static float TS_PROFIT_MULTIPLIER = 5.21847f;    // Hệ số kích hoạt Trailing (Bao nhiêu % lãi thì bắt đầu kéo)

    // =========================================================
    // 7. AI & BỘ LỌC TÍN HIỆU ĐỘNG (AI DYNAMIC FILTER - HPO)
    // =========================================================
    // Ngưỡng giới hạn cốt lõi của AI

    // Bộ bù trừ chéo (Trade-off) giữa AI Funding và AI Entry
    public static float AI_DYNAMIC_MULTIPLIER = 1.40234f; // Hệ số nhân tỷ lệ (Base scale)
    public static float AI_DYNAMIC_MIN = 0.14568f;        // Mức nới lỏng tiêu chuẩn tối đa (Hạ chuẩn)
    public static float AI_DYNAMIC_MAX = 2.24405f;        // Mức siết chặt tiêu chuẩn tối đa (Siết chuẩn)

    // Các tham số lọc tín hiệu dự đoán chung
    public static float PREDICT_SYMBOL_RATE_DOWN_15M = -0.03234f;
    public static float PREDICT_SYMBOL_RATE_UP_AVG = 0.00454f;
    public static float PREDICT_SYMBOL_RATE_DOWN_AVG = -0.00503f;



    public static float PREDICT_SYMBOL_RATE_MAX_THRESHOLD = 0.15f; // Tỉ lệ tạch tối đa cho phép
    public static float HARD_RISK_LIMIT_4H = -0.2f;            // Ngưỡng Drawdown 4H cấm vào lệnh
    public static float MIN_MOMENTUM_15M = 0.02284f;        // Đà nảy tối thiểu nến 15M
    public static float MIN_MOMENTUM_24H = 0.01682f;                  // Đà nảy tối thiểu nến 24H

    // =========================================================
    // 8. NGƯỠNG BÁO ĐỘNG THỊ TRƯỜNG (MARKET STATUS THRESHOLDS - HPO)
    // =========================================================
    // Ngưỡng Bão Lớn (BIG)
    public static float MS_UP_BIG_THRES = 0.02046f;
    public static float MS_DOWN_BIG_AVG = -0.03157f;

    // Ngưỡng Bão Vừa (MEDIUM)
    public static float MS_DOWN_MED_AVG = -0.02069f;

    // Ngưỡng Bão Nhỏ (SMALL)
    public static float MS_UP_SMALL_THRES = 0.00442f;
    public static float MS_DOWN_15M_SMALL_ONLY = -0.02145f;

    // =========================================================
    // THÊM MỚI: THAM SỐ CHUẨN BỊ CHO HPO PHASE 2 (SURVIVAL)
    // =========================================================
    // 1. Bắt đáy Altcoin (isDcaAlt)
    public static float DCA_ALT_DOWN_15M_THRES = -0.035f;
    public static float DCA_ALT_UP_AVG_THRES = 0.012f;
    public static float DCA_ALT_DOWN_AVG_THRES = -0.012f;

    // 2. Cầu dao chống bão (Circuit Breaker)
    public static float CIRCUIT_DANGER_RATIO = 0.7f;    // 70% lệnh rủi ro

    // 3. Cấu hình DCA Nhồi lệnh (DcaUtils)
    public static int DCA_TIME_BIG_DOWN = 8;
    public static float DCA_LOSS_BIG_DOWN = -0.15f;
    public static int DCA_TIME_MED_DOWN = 15;
    public static float DCA_LOSS_MED_DOWN = -0.25f;


    // =========================================================
    // 9. KẾT NỐI DỮ LIỆU (STORAGE & AEROSPIKE)
    // =========================================================
    public static final String FILE_AI_ENTRY_PREDICTIONS = Configs.getString("FILE_AI_PREDICTIONS");

    public static final String AEROSPIKE_HOST_242 = Configs.getString("AEROSPIKE_HOST");
    public static final int AEROSPIKE_PORT_242 = Configs.getInt("AEROSPIKE_PORT");

    public static final String AEROSPIKE_HOST_226 = Configs.getString("AEROSPIKE_HOST_226");
    public static final int AEROSPIKE_PORT_226 = Configs.getInt("AEROSPIKE_PORT_226");

    public static final String AEROSPIKE_NAMESPACE = Configs.getString("AEROSPIKE_NAMESPACE");
    public static final String AEROSPIKE_SET_NAME_FUNDING_PRED = Configs.getString("AEROSPIKE_SET_NAME_FUNDING_PRED");
    public static final String AEROSPIKE_SET_NAME_PRED_40 = Configs.getString("AEROSPIKE_SET_NAME_PRED_40");

    // =========================================================
    // 10. TIỆN ÍCH GETTER
    // =========================================================
    public static String getString(String configName) {
        return properties.get(configName);
    }

    public static int getInt(String configName) {
        return Integer.parseInt(properties.get(configName));
    }

    public static Boolean getBoolean(String configName) {
        return Boolean.parseBoolean(properties.get(configName));
    }

    public static float getDouble(String configName) {
        return Float.parseFloat(properties.get(configName));
    }

    public static void main(String[] args) {
        // Test configurations here
    }
}