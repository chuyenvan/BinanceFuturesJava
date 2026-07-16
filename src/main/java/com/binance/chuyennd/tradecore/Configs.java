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
    // TASK-112: nguồn dữ liệu TƯỜNG MINH per-box, thay 2 flag runtime mode cũ (kaggle/HPO)
    // (2 flag trộn 3 quyết định độc lập + ~25 tool set tay ở main() → quên set = âm thầm đọc sai nguồn,
    // đã vô hiệu 2 lần chạy, gần nhất full WFO 17 window 2026-07-02).
    // KHÔNG default ngầm, KHÔNG validate ở static-init — validate LAZY tại điểm dùng:
    //   AEROSPIKE_READ_CLUSTER (226|242) → DataManagerAerospikeFloatSim.getReadClient() throw nếu thiếu/sai;
    //   TICKER_SOURCE (aerospike|file)  → SimulatorMarketLevelTicker1MStopLoss throw nếu thiếu/sai.
    // Lý do lazy: box Kaggle thuần file không cần AEROSPIKE_READ_CLUSTER; tool không chạy sim không cần TICKER_SOURCE.
    public static String AEROSPIKE_READ_CLUSTER = properties.get("AEROSPIKE_READ_CLUSTER");
    public static String TICKER_SOURCE = properties.get("TICKER_SOURCE");
    // TASK-112: sim ghi storage/*.data + printDone.csv sau khi chạy xong. Default FALSE — ⚠️ ĐỔI DEFAULT:
    // trước đây box local (không bật kaggle-mode) mặc định GHI; box nào muốn giữ hành vi cũ thêm WRITE_SIM_STORAGE=true.
    public static boolean WRITE_SIM_STORAGE = properties.get("WRITE_SIM_STORAGE") != null ? getBoolean("WRITE_SIM_STORAGE") : false;
    // WFO/HPO: bật cache nén kline trong RAM (HPOSmartCache). Default tắt → simulator giữ nguyên đường đọc cũ.
    // Bật riêng cho worker WFO (env USE_SMART_CACHE=true) để N sample cùng window dùng chung cache, đọc DB 1 lần/ngày.
    public static boolean USE_SMART_CACHE = properties.get("USE_SMART_CACHE") != null ? getBoolean("USE_SMART_CACHE") : false;
    // WFO/HPO: bật CoinRank TĨNH (tier nạp sẵn từ file thay vì tính live qua HistoryManager).
    // Default tắt → giữ nguyên hành vi cũ (live, cold-start ring mỗi window). Bật cho worker WFO để
    // backtest KHÔNG cần HistoryManager.updateHistoryArray (cắt overhead + cắt phụ thuộc totalUsdt).
    public static boolean WFO_STATIC_RANK = properties.get("WFO_STATIC_RANK") != null ? getBoolean("WFO_STATIC_RANK") : false;
    public static String TIME_RUN = Configs.getString("TIME_RUN");

    /**
     * Fail-fast cho PROCESS LIVE (gọi NGAY đầu {@code main()} của {@code BinanceOrderTradingManager} +
     * {@code BinanceDataIngestor}). Live BẮT BUỘC {@code AEROSPIKE_READ_CLUSTER=242} trong config.properties —
     * thiếu key hoặc giá trị khác 242 → {@code getReadClient()} sẽ throw/đọc 226 (kho BACKTEST, dữ liệu cũ)
     * → bot ĐỌC/QUYẾT ĐỊNH trên data sai mà KHÔNG báo. Audit #12 (TASK-030); TASK-112 chuyển sang check config
     * tường minh. DỪNG ngay ({@code System.exit(1)}) nếu sai. KHÔNG gọi trong tool backtest/kaggle/HPO.
     */
    public static void assertLiveRuntime() {
        if (!"242".equals(AEROSPIKE_READ_CLUSTER)) {
            System.err.println("⛔ FATAL (audit #12 / TASK-112): process LIVE yêu cầu AEROSPIKE_READ_CLUSTER=242 trong "
                    + "config.properties (hiện tại: " + AEROSPIKE_READ_CLUSTER + "). Thiếu/sai → getReadClient() đọc nhầm "
                    + "Aerospike 226 (kho backtest) thay 242. Thêm dòng AEROSPIKE_READ_CLUSTER=242 rồi chạy lại. DỪNG.");
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

    // === FUNDING FEE (Bước 3, code lại 2026-06-29 — tính 1 LƯỢT khi đóng lệnh) ===
    // Trừ phí funding cho lệnh long: Σ rate(settlement) × quantity × avgEntry, tính 1 lần ở closeOrder.
    // MẶC ĐỊNH OFF (Uni chốt 2026-06-29): tác động nhỏ (~0.9% PnL, maxDD không đổi) nhưng làm chậm ~vài %
    // mỗi lần chạy → KHÔNG đáng gánh trong HPO/WFO (hàng nghìn lần eval). CHỈ bật (=true) ở vòng HPO/Golden
    // backtest CUỐI trước go-live để đo PnL/DD thật. RunFundingImpact tự bật/tắt để đo đối chứng.
    public static boolean APPLY_FUNDING_FEE = false;


    public static float TS_MAX_GAP = 0.08f; // gap trailing tối đa (cũ: 16/200)
    public static float TS_MAX_GAP_WEAK = 0.03f; // gap khi momentum yếu (cũ: 6/200)
    public static float TS_WEAK_MOMENTUM_THRES = 0.004f; // ngưỡng coi là momentum yếu

    // =========================================================
    // 4. QUẢN TRỊ VỐN TỰ ĐỘNG (BUDGET MANAGEMENT)
    // =========================================================
    // TASK (2026-07-10): cho phep override qua config de SWEEP SIZING (khong rebuild moi lan). Mac dinh 50 = cu.
    // BASE_BUDGET = BALANCE_BASIC / number_order_budget. Giam so nay = size/lenh lon hon = trien khai nhieu von hon.
    public static Integer number_order_budget = properties.get("NUMBER_ORDER_BUDGET") != null
            ? Integer.parseInt(properties.get("NUMBER_ORDER_BUDGET")) : 50; // Tổng số phần chia vốn

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
    // TASK (2026-07-09, theo yêu cầu Uni): SL cứng cho lệnh CHƯA từng chạm ngưỡng lãi để arm trailing.
    // Vấn đề đo được: neu peak-profit khong bao gio vuot RATE_PROFIT_STOP_MARKET, priceSL mai la null
    // -> khong co exit nao, chi con DCA nap them ("nuoi lo"). Bien nay CHỈ chặn đúng lỗ hổng đó, KHÔNG
    // đụng cơ chế trailing-khi-lãi. 0f = tắt (mặc định, hành vi cũ y nguyên). ví dụ 0.10f = cắt khi lỗ 10%.
    public static float HARD_STOP_LOSS_RATE = properties.get("HARD_STOP_LOSS_RATE") != null
            ? Float.parseFloat(properties.get("HARD_STOP_LOSS_RATE")) : 0f;
    // TASK (2026-07-10): time-stop "thesis-expiry" cho lenh CHUA arm trailing (priceSL null).
    // Khac HARD_STOP_LOSS_RATE (cat theo DO SAU lo): cai nay cat lenh I THEO THOI GIAN — tin hieu
    // (pump 12h / hoi capitulation) het han ma khong no thi thoat, giai phong margin, tranh nuoi vo han.
    // Do tu leg DAU cua cum (clusterFirstLegTime, fallback timeStart) — neu do tu leg cuoi thi moi lan
    // DCA lai reset dong ho, lenh nuoi lo se KHONG BAO GIO bi time-stop. 0 = tat (mac dinh, hanh vi cu).
    public static int TIME_STOP_HOURS = properties.get("TIME_STOP_HOURS") != null
            ? Integer.parseInt(properties.get("TIME_STOP_HOURS")) : 0;
    // TASK (2026-07-10): ti le nha lai dinh cua trailing (cu hardcode 0.5). 0.3 = giu chat, 0.7 = long nuoi trend.
    public static float TS_GIVEBACK_RATIO = properties.get("TS_GIVEBACK_RATIO") != null
            ? Float.parseFloat(properties.get("TS_GIVEBACK_RATIO")) : 0.5f;
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
    // TASK (2026-07-11) §2 DCA-primary: TAT sleeve PREDICT_SYMBOL_TRADE (pump selector) de do rieng
    // sleeve mean-reversion. true = chi chay DCA_LEVEL1 + BIG_DOWN. Mac dinh false = hanh vi cu.
    public static boolean DISABLE_PREDICT_SYMBOL = "true".equalsIgnoreCase(properties.get("DISABLE_PREDICT_SYMBOL"));

    public static String FILTER_MODE = "A";

    // === ABLATION (Bước 2 roadmap: edge từ AI hay DCA? — chỉ ĐO, mặc định A, KHÔNG ảnh hưởng CONFIG_VERSION) ===
    // A=control (AI filter bật như thường) | B=no-AI (bỏ qua filter, mọi tín hiệu PASS) | C=placebo
    // (entry ngẫu nhiên cùng XÁC SUẤT pass như A). So leg-đầu (MAE/rescue/firstLegPnl) giữa A và B/C.
    // CHỈ tác động tại điểm AI filter trong createOrderBUY, KHÔNG đụng logic DCA/exit/budget.
    // TASK (2026-07-11) doc tu env de test gate-off (mode B) khong can sua WfoWorker; van mac dinh A.
    public static String ABLATION_MODE = System.getenv("ABLATION_MODE") != null
            ? System.getenv("ABLATION_MODE") : "A";
    public static long ABLATION_SEED = 42L;

    // === CIRCUIT BREAKER (chống sập tầng DCA/margin — BẬT MẶC ĐỊNH từ Bước 3, ĐỔI PnL/DD → bump CONFIG_VERSION v10) ===
    // OFF=không phanh | MARGIN=chặn mở mới khi margin/vốn cao | DCA=ngừng nhồi cụm lỗ sâu | BOTH=cả hai.
    // KHÔNG force-close (long-only): chỉ DỪNG MỞ / DỪNG NHỒI.
    // CHỐT 2026-06-28 (Bước 3 ruin): MARGIN + 0.50. Quét ngưỡng 2021→2026 cho return/maxDD tốt nhất tại 0.50
    // (4.88; maxDD -58.6%→-29.5%, maxMargR 0.99→0.51, đổi lấy PnL -27%). Lá chắn THẬT là trần margin TỔNG, không
    // phải cap %vốn/cụm (đã thử & gỡ: veto 0-8 lần trên danh mục vì budget phân tán qua hàng trăm cụm nhỏ).
    public static String BREAKER_MODE = "MARGIN";
    public static float BREAKER_MARGIN_HALT = 0.50f;     // chặn MỞ MỚI khi marginRunning/balanceBasic >= ngưỡng.
    public static float BREAKER_CLUSTER_DD_MAX = -0.30f; // [ADR-0008: VÔ HIỆU CẤU TRÚC - đo DD vs avgEntry trôi theo giá] ngừng NHỒI khi (giá-avgEntry)/avgEntry <= ngưỡng (chỉ dùng khi BREAKER_MODE=DCA/BOTH)

    // [ADR-0008 bước 3 — ĐÃ GỠ cap %vốn/cụm + số leg + DD-vs-first 2026-06-28] LunaDcaScenario (1 coin) cho thấy
    // cả 3 cứu ruin, NHƯNG backtest 5 năm: cap %vốn/cụm veto 0-8 lần (vô dụng trên danh mục — budget phân tán
    // qua hàng trăm cụm nhỏ). Lá chắn THẬT là BREAKER_MARGIN_HALT tổng ở trên. Không giữ tham số cap chết.

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

    // SIM ABLATION: override entry-knob qua env (chi cho backtest so cau hinh; env rong -> giu default).
    static {
        try {
            String v;
            if ((v = System.getenv("SIM_OFF_FLAT_HARD")) != null) OFF_FLAT_HARD = Boolean.parseBoolean(v);
            if ((v = System.getenv("SIM_MIN_MOMENTUM_15M")) != null) MIN_MOMENTUM_15M = Float.parseFloat(v);
            if ((v = System.getenv("SIM_AI_DYNAMIC_MIN")) != null) AI_DYNAMIC_MIN = Float.parseFloat(v);
            if ((v = System.getenv("SIM_PREDICT_SYMBOL_RATE_MAX")) != null) PREDICT_SYMBOL_RATE_MAX_THRESHOLD = Float.parseFloat(v);
            if ((v = System.getenv("SIM_RATE_PROFIT_STOP_MARKET")) != null) RATE_PROFIT_STOP_MARKET = Float.parseFloat(v);
            if ((v = System.getenv("SIM_BREAKER_MODE")) != null) BREAKER_MODE = v;
            if ((v = System.getenv("SIM_BREAKER_MARGIN_HALT")) != null) BREAKER_MARGIN_HALT = Float.parseFloat(v);
            if ((v = System.getenv("SIM_MS_DOWN_BIG_AVG")) != null) MS_DOWN_BIG_AVG = Float.parseFloat(v);
        } catch (Exception e) {
            System.err.println("SIM env override parse error: " + e);
        }
    }

    public static void main(String[] args) {
        // Test configurations here
    }
}