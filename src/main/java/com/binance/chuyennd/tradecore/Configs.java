/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.binance.chuyennd.tradecore;

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
    // ⛔ DANH SÁCH GENE KHÔNG-HPO (NO-HPO) — chốt TASK-111 sensitivity 2026-06-27
    // =========================================================
    // 9 gene dưới đây ĐÃ ĐO sensitivity (OAT 4 mức, FAST 2.5 năm) → PHẲNG (range fitness < 0.06).
    // Ablation off ĐỒNG THỜI cả cụm: fitness 1.5197 → 1.4868 (delta -2.16%) → có tương tác nhẹ nên
    // KHÔNG xóa cơ chế (ngắt MỀM), nhưng KHÔNG đưa vào HPO/WFO (đóng băng ở giá trị hiện tại):
    //   1. PREDICT_SYMBOL_RATE_DOWN_15M   (range 0.0000)
    //   2. PREDICT_SYMBOL_RATE_UP_AVG     (range 0.0000)
    //   3. PREDICT_SYMBOL_RATE_DOWN_AVG   (range 0.0000)
    //   4. MS_UP_SMALL_THRES              (range 0.0038)
    //   5. MS_DOWN_SMALL_AVG_OR_15M       (range 0.0044)
    //   6. DCA_LOSS_BIG_UP                (range 0.0092)
    //   7. BUDGET_DIVIDER_1               (range 0.0096)
    //   8. MS_UP_BIG_THRES                (range 0.0318)
    //   9. AI_DYNAMIC_MAX                 (range 0.0531)
    // → Genome HPO/WFO = 18 gene CÒN LẠI (xem WFORunner.GENOME). Chi tiết: docs/insights/SENSITIVITY_TASK111.md
    // =========================================================
    // [OFF-CỨNG TEST] true = VÔ HIỆU HÓA cơ chế 9 gene cụm phẳng tại điểm dùng engine (bỏ nhánh BIG_UP/
    // SMALL_UP/SMALL_DOWN_15M, bỏ trần clamp AI_DYNAMIC_MAX, bỏ tầng BUDGET_DIVIDER_1, bỏ 4 dòng set
    // PREDICT_RATE_* đã chết). false = nguyên trạng. CHỈ để TEST, KHÔNG commit true. Revert = đổi false.
    public static boolean OFF_FLAT_HARD = true;

    // =========================================================
    // 1. HỆ THỐNG & KHỞI TẠO (SYSTEM & INIT)
    // =========================================================
    public static String configFile = "config.properties";
    public static volatile Map<String, String> properties = new HashMap<>();

    static {
        // 🕐 Lớp 0: ép timezone mặc định JVM = GMT+7 TRƯỚC mọi xử lý ngày-giờ.
        // Mọi SimpleDateFormat trần (key Aerospike yyyyMMdd-HHmm) nhờ đó hành xử y hệt trên mọi OS,
        // chống lệch 7h giữa VPS (Oracle UTC vs cá nhân/live GMT+7) gây hỏng data.
        TimeZoneGuard.enforceGmt7();
        try {
            File file = new File(Configs.configFile);
            List<String> lines = FileUtils.readLines(file, "UTF-8");
            for (String line : lines) {
                if (StringUtils.contains(line, "=")) {
                    // split giới hạn 2 phần: dòng "KEY=" (value rỗng) -> value "" thay vì AIOOBE làm chết clinit;
                    // dòng value chứa '=' (vd URL ...?a=b) giữ trọn phần sau dấu '=' đầu tiên. KHÔNG đổi parse của value hiện có.
                    String[] kv = line.split("=", 2);
                    properties.put(kv[0].trim(), kv[1].trim());
                }
            }
        } catch (Exception e) {
            System.err.println("Do not read config file: " + configFile);
            e.printStackTrace();
            System.exit(0);
        }
        // 🕐 Lớp 2: fail-fast nếu tz vẫn sai (vd JVM bị override) — chặn chạy tiếp với data lệch giờ.
        TimeZoneGuard.assertGmt7();
    }

    // =========================================================
    // 2. CHẾ ĐỘ CHẠY (RUNNING MODES)
    // =========================================================
    public static boolean IS_HPO_MODE = false; // Bật khi chạy tối ưu hóa Jenetics
    public static boolean IS_KAGGLE_MODE = properties.get("IS_KAGGLE_MODE") != null ? getBoolean("IS_KAGGLE_MODE") : false;
    public static String TIME_RUN = Configs.getString("TIME_RUN");

    /**
     * Fail-fast cho PROCESS LIVE (gọi NGAY đầu {@code main()} của {@code BinanceOrderTradingManager} +
     * {@code BinanceDataIngestor}). Nếu lỡ bật {@link #IS_KAGGLE_MODE}/{@link #IS_HPO_MODE} trên box live,
     * {@code DataManagerAerospikeFloatSim.getReadClient()} sẽ trỏ Aerospike 226 (kho BACKTEST, dữ liệu cũ)
     * thay 242 → bot ĐỌC/QUYẾT ĐỊNH trên data sai mà KHÔNG báo. Audit #12 (TASK-030). DỪNG ngay nếu sai mode.
     * KHÔNG gọi trong tool backtest/kaggle/HPO (chúng cố ý bật IS_KAGGLE_MODE).
     */
    public static void assertLiveRuntime() {
        if (IS_KAGGLE_MODE || IS_HPO_MODE) {
            System.err.println("⛔ FATAL (audit #12): process LIVE khởi động với IS_KAGGLE_MODE=" + IS_KAGGLE_MODE
                    + " / IS_HPO_MODE=" + IS_HPO_MODE + " → getReadClient() sẽ đọc Aerospike 226 (kho backtest) thay 242. "
                    + "Tắt IS_KAGGLE_MODE trong config.properties trên box live rồi chạy lại. DỪNG.");
            System.exit(1);
        }
    }

    // =========================================================
    // 3. CẤU HÌNH GIAO DỊCH CƠ BẢN (BASIC TRADING)
    // =========================================================
    public static Integer LEVERAGE_ORDER = 1; // Đòn bẩy
    public static final Float RATE_FEE = 0.002f; // Phí giao dịch sàn đã sửa thành 2 chân
    public static Integer NUMBER_ENTRY_EACH_SIGNAL = 2; // Số lệnh vào mỗi khi có tín hiệu
    public static Integer NUMBER_TICKER_CAL_RATE_CHANGE = 15; // Số nến để tính biến động
    public static final Integer NUMBER_THREAD_ORDER_MANAGER = Configs.getInt("NUMBER_THREAD_ORDER_MANAGER");
    // TASK-027 #7: tuổi TỐI ĐA chấp nhận của giá price_realtime (242) khi tính SIZE lệnh live.
    // price_realtime ghi ~3s/lần (Rest-Price-Loop); 30s = ~10× nhịp, dư cho jitter. Quá tuổi này →
    // fallback giá nến đóng + cảnh báo. CHỈ dùng ở path entry LIVE (createOrderBuyRequest) — KHÔNG
    // ảnh hưởng backtest/sim nên KHÔNG cần bump CONFIG_VERSION.
    public static long PRICE_REALTIME_MAX_AGE_MS = 30 * 1000L;
    // === BƯỚC 0: SLIPPAGE & LOOK-AHEAD GUARD ===
    // Trượt giá mô phỏng cho mỗi chân khớp (entry + exit). 0.0005–0.001 là vùng hợp lý
    // cho coin thanh khoản tốt; coin nhỏ nên cao hơn. Áp cho cả entry và exit.
    public static float SLIPPAGE_RATE = 0.003f;

    // Công tắc bịt look-ahead nội-nến. MẶC ĐỊNH true (luôn bật khi backtest thật).
    // Đặt false CHỈ để đo "trước/sau khi bịt" — nếu PnL false >> true thì phần chênh
    // chính là ảo giác look-ahead, không phải lãi thật.
    public static boolean BLOCK_INTRABAR_LOOKAHEAD = true;

    // Bật/tắt mô phỏng slippage (để đo tác động riêng của nó).
    public static boolean APPLY_SLIPPAGE = true;


    public static float TS_MAX_GAP = 0.08f; // gap trailing tối đa (cũ: 16/200)
    public static float TS_MAX_GAP_WEAK = 0.03f; // gap khi momentum yếu (cũ: 6/200)
    public static float TS_WEAK_MOMENTUM_THRES = 0.004f; // ngưỡng coi là momentum yếu

    // =========================================================
    // 4. QUẢN TRỊ VỐN TỰ ĐỘNG (BUDGET MANAGEMENT)
    // =========================================================
    public static Integer number_order_budget = 50; // Tổng số phần chia vốn

    // Ngưỡng bóp vốn 1 & 2
    public static float BUDGET_MARGIN_RATIO_1 = 0.4820f;
    public static float BUDGET_DIVIDER_1 = 1.5578f;
    public static float BUDGET_MARGIN_RATIO_2 = 0.7475f;
    public static float BUDGET_DIVIDER_2 = 1.5984f;

    // =========================================================
    // 5. CẦU DAO & MẬT ĐỘ LỆNH (CIRCUIT BREAKER)
    // =========================================================
    public static int MAX_CONCURRENT_ORDERS = 40; // Số lệnh tối đa cùng chạy
    public static float DENSITY_SUSTAIN = 10.0f;  // Sức chịu đựng mật độ mở lệnh
    public static float DENSITY_ALPHA = 0.6f;     // Độ cong của hàm kiểm soát mật độ
    public static final int CIRCUIT_LOOKBACK_MINUTES = 4;
    public static float CIRCUIT_DANGER_RATIO = 0.7f; // 70% lệnh rủi ro

    // =========================================================
    // 6. TRAILING STOP ĐỘNG (DYNAMIC TRAILING)
    // =========================================================
    public static float RATE_PROFIT_STOP_MARKET = 0.01032f; // Khoảng dời SL tối thiểu (Base rate)
    public static float TS_DYNAMIC_K = 0.29774f;            // Hệ số nhân Volatility để dời SL
    public static float TS_PROFIT_MULTIPLIER = 5.21847f;    // Hệ số kích hoạt Trailing

    // =========================================================
    // 7. AI & BỘ LỌC TÍN HIỆU ĐỘNG (AI DYNAMIC FILTER - HPO UPDATE)
    // =========================================================
    public static float AI_DYNAMIC_MULTIPLIER = 1.28760f; // Cũ: 1.40234f
    public static float AI_DYNAMIC_MIN = 0.26787f;        // Cũ: 0.14568f
    public static float AI_DYNAMIC_MAX = 2.14135f;        // Cũ: 2.24405f

    public static float PREDICT_SYMBOL_RATE_DOWN_15M = -0.03234f;
    public static float PREDICT_SYMBOL_RATE_UP_AVG = 0.00454f;
    public static float PREDICT_SYMBOL_RATE_DOWN_AVG = -0.00503f;



    // === ABLATION FILTER (chỉ phục vụ ĐO, KHÔNG ảnh hưởng CONFIG_VERSION) ===
    // A=full (giữ RISK+MOM15)  B/D=bỏ nhánh RISK(DD4H) để đo. MOM24/predReturn24H đã BỎ HẲN khỏi hệ.
    // Nhánh EARLY trong checkSignalDynamic GIỮ NGUYÊN ở mọi mode.
    public static String FILTER_MODE = "A";

    // === ABLATION (Bước 2 roadmap: edge từ AI hay DCA? — chỉ ĐO, mặc định A, KHÔNG ảnh hưởng CONFIG_VERSION) ===
    // A=control (AI filter bật như thường) | B=no-AI (bỏ qua filter, mọi tín hiệu PASS) | C=placebo
    // (entry ngẫu nhiên cùng XÁC SUẤT pass như A). So leg-đầu (MAE/rescue/firstLegPnl) giữa A và B/C.
    // CHỈ tác động tại điểm AI filter trong createOrderBUY, KHÔNG đụng logic DCA/exit/budget.
    public static String ABLATION_MODE = "A";
    public static long ABLATION_SEED = 42L;

    // === CIRCUIT BREAKER (chống sập tầng DCA/margin — chỉ ĐO, mặc định OFF, KHÔNG ảnh hưởng CONFIG_VERSION) ===
    // OFF=không phanh | MARGIN=chặn mở mới khi margin/vốn cao | DCA=ngừng nhồi cụm lỗ sâu | BOTH=cả hai.
    // KHÔNG force-close (long-only): chỉ DỪNG MỞ / DỪNG NHỒI.
    public static String BREAKER_MODE = "OFF";
    public static float BREAKER_MARGIN_HALT = 0.70f;     // chặn MỞ MỚI khi marginRunning/balanceBasic >= ngưỡng
    public static float BREAKER_CLUSTER_DD_MAX = -0.30f; // ngừng NHỒI cụm khi (giá hiện tại - avg entry)/avg entry <= ngưỡng

    // =========================================================
    // 8. NGƯỠNG BÁO ĐỘNG & DCA NHỒI LỆNH (MARKET STATUS - HPO UPDATE)
    // =========================================================
    public static float PREDICT_SYMBOL_RATE_MAX_THRESHOLD = 0.15f;    // HPO (đã revert về cũ): 0.19727f (Log map: PREDICT_MAX_THRES)
    public static float HARD_RISK_LIMIT_4H = -0.2f;                   // HPO (đã revert về cũ): -0.09200f
    public static float MIN_MOMENTUM_15M = 0.02284f;                  // HPO (đã revert về cũ): 0.01720f
    public static float MS_UP_BIG_THRES = 0.02046f;                  // HPO (đã revert về cũ): 0.01757f
    public static float MS_DOWN_BIG_AVG = -0.03157f;                  // HPO (đã revert về cũ): -0.05514f

    public static float MS_UP_SMALL_THRES = 0.00442f;
    public static float MS_DOWN_SMALL_AVG_OR_15M = -0.02069f;         // HPO (đã revert về cũ): -0.02007f

    public static int DCA_TIME_BIG_DOWN = 8;                          // HPO (đã revert về cũ): 13
    public static float DCA_LOSS_BIG_DOWN = -0.15f;                   // HPO (đã revert về cũ): -0.26618f
    public static int DCA_TIME_BIG_Up = 15;                           // HPO (đã revert về cũ): 22
    public static float DCA_LOSS_BIG_UP = -0.25f;                     // HPO (đã revert về cũ): -0.10063f

    // =========================================================
    // 9. KẾT NỐI DỮ LIỆU (STORAGE & AEROSPIKE)
    // =========================================================
    public static final String FILE_AI_ENTRY_PREDICTIONS = Configs.getString("FILE_AI_PREDICTIONS");

    public static final String AEROSPIKE_HOST_242 = Configs.getString("AEROSPIKE_HOST");
    public static final int AEROSPIKE_PORT_242 = Configs.getInt("AEROSPIKE_PORT");

    public static final String AEROSPIKE_HOST_226 = Configs.getString("AEROSPIKE_HOST_226");
    public static final int AEROSPIKE_PORT_226 = Configs.getInt("AEROSPIKE_PORT_226");

    public static final String AEROSPIKE_NAMESPACE = Configs.getString("AEROSPIKE_NAMESPACE");

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