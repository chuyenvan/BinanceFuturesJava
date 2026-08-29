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
    // ===== BUDGET v1 (FROZEN 2026-08-24) — throttle liên tục thay logic vách rời rạc =====
    public static float F_BASE = 0.03f;   // % equity mỗi lệnh gốc (gene search [0.01, 0.05])
    public static float U_MAX  = 0.60f;   // trần tổng margin/equity, U≥U_MAX → chặn (gene search [0.40, 0.80])
    public static float BUDGET_DIVIDER_2 = 1.5984f;

    // === LEVER-B SIZE (TASK 2026-07-19, env-gated — MAC DINH 1.0 = byte-identical) ===
    // He dang deploy QUA IT von (log: margin ~0.7%, minEq_mtm 99-100% = von idle). Edge Calmar~1 nen noi
    // size = nang return. SIZE_MULT nhan TRUC TIEP budget-per-order tai createOrder SAU khi da qua HET guard
    // (managerBudget throttle theo marginRatio + tierMultiplier). >1 -> moi lenh deploy nhieu von hon
    // (quantity + margin scale TUYEN TINH). KHONG pha guard chong-am-von: managerBudget van return null khi
    // marginRatio>=0.99, BREAKER_MARGIN_HALT van chan mo moi (voi size lon marginRunning phinh nhanh hon ->
    // cham tran SOM hon). Chi scale SIZE trong khuon budget. Clamp >=0. env unset -> 1.0f -> budget khong doi
    // -> byte-identical. env SIZE_MULT (vd 10) de deploy nhieu hon khi chay WFO sizing.
    public static final float SIZE_MULT = System.getenv("SIZE_MULT") != null
            ? Math.max(0f, Float.parseFloat(System.getenv("SIZE_MULT").trim())) : 1.0f;

    // === SIZE-BY-CONFIDENCE / soft-gate (TASK 2026-07-19, env-gated, DEFAULT OFF = byte-identical) ===
    // LY DO (data long-conf-headroom): trong nhom admit (p6>=0.68), top-2 decile p6 an +3.40/+2.38/keo
    // (winrate 52-56%) NHUNG decile giua (p6~0.68) LO -1.3/-1.2. Gate nhi phan vut info nay. -> size TO cho
    // p6 cao, size NHO cho p6 marginal, GIU tan suat (khong doi admit gate). Nhan CUNG voi SIZE_MULT, SAU
    // guard chong-am-von (managerBudget + BREAKER_MARGIN_HALT + tier) -> guard GIU NGUYEN.
    //   CONF_SIZE_MODE: 0=off (default) -> confFactor khong duoc ap -> byte-identical. 1=on.
    //   confFactor(p6) = clamp( FMIN + (FMAX-FMIN)*(p6-LO)/(HI-LO), FMIN, FMAX ).
    //     p6<=LO -> FMIN ; p6>=HI -> FMAX ; tuyen tinh o giua. (p6 = 1 - symbolPred, tinh per-order.)
    public static final int CONF_SIZE_MODE = System.getenv("CONF_SIZE_MODE") != null
            ? Integer.parseInt(System.getenv("CONF_SIZE_MODE").trim()) : 0;   // 0=OFF (byte-identical)
    public static final float CONF_SIZE_LO = System.getenv("CONF_SIZE_LO") != null
            ? Float.parseFloat(System.getenv("CONF_SIZE_LO").trim()) : 0.68f; // = admit threshold p6
    public static final float CONF_SIZE_HI = System.getenv("CONF_SIZE_HI") != null
            ? Float.parseFloat(System.getenv("CONF_SIZE_HI").trim()) : 0.95f;
    public static final float CONF_SIZE_FMIN = System.getenv("CONF_SIZE_FMIN") != null
            ? Float.parseFloat(System.getenv("CONF_SIZE_FMIN").trim()) : 0.3f;
    public static final float CONF_SIZE_FMAX = System.getenv("CONF_SIZE_FMAX") != null
            ? Float.parseFloat(System.getenv("CONF_SIZE_FMAX").trim()) : 3.0f;

    /**
     * Soft-gate size multiplier theo do tin cay p6 (=1-symbolPred). Pure/static -> function-test khong can
     * Aerospike. Tuyen tinh giua [LO,HI] roi clamp ve [FMIN,FMAX]. HI<=LO (cau hinh xau) -> tra FMAX (>=LO)
     * / FMIN (<LO) de tranh chia 0.
     */
    public static float confFactor(float p6) {
        if (p6 <= CONF_SIZE_LO) return CONF_SIZE_FMIN;
        if (p6 >= CONF_SIZE_HI) return CONF_SIZE_FMAX;
        float f = CONF_SIZE_FMIN + (CONF_SIZE_FMAX - CONF_SIZE_FMIN) * (p6 - CONF_SIZE_LO) / (CONF_SIZE_HI - CONF_SIZE_LO);
        // clamp phong ve so hoc (FMIN co the > FMAX neu cau hinh nguoc)
        float lo = Math.min(CONF_SIZE_FMIN, CONF_SIZE_FMAX);
        float hi = Math.max(CONF_SIZE_FMIN, CONF_SIZE_FMAX);
        return Math.max(lo, Math.min(hi, f));
    }

    // =========================================================
    // 5. CẦU DAO & MẬT ĐỘ LỆNH (CIRCUIT BREAKER)
    // =========================================================
    // TASK LEVER-B (2026-07-19): env MAX_CONCURRENT override (default 40 = giu nguyen). Day la BASE cua
    // density-burst limiter (is50PercentOrderLoss -> evaluateCircuitBreakerCore) + tuyen phong lop-2 storm.
    // KHONG phai hard-cap so lenh dong thoi (mang activeRunningIds cap 1000, KHONG that co). Nang so nay ->
    // cho phep nhieu lenh mo trong cua so 4' hon truoc khi phanh mat-do. env unset -> 40 -> byte-identical.
    public static int MAX_CONCURRENT_ORDERS = System.getenv("MAX_CONCURRENT") != null
            ? Integer.parseInt(System.getenv("MAX_CONCURRENT").trim()) : 40; // Số lệnh tối đa cùng chạy
    public static float DENSITY_SUSTAIN = 10.0f;  // Sức chịu đựng mật độ mở lệnh
    public static float DENSITY_ALPHA = 0.6f;     // Độ cong của hàm kiểm soát mật độ
    public static final int CIRCUIT_LOOKBACK_MINUTES = 4;
    public static float CIRCUIT_DANGER_RATIO = 0.7f; // 70% lệnh rủi ro

    // =========================================================
    // 6. TRAILING STOP ĐỘNG (DYNAMIC TRAILING)
    // =========================================================
    // TASK (2026-07-30, theo yeu cau Uni): nang tu 0.01032 -> 0.03. Ly do: round-trip cost
    // (RATE_FEE 2 chan 0.002 + SLIPPAGE_RATE 2 chan 0.003 = 0.008) an het loi nhuan cua bat ky
    // lenh nao thoat duoi ~0.016 profit; arm cu (0.01032) + giveback 0.5 -> SL dong bang o +0.5%,
    // sau chi phi la LO CHAC CHAN. Khop voi TASK-139 (sweep 0.03-0.05 -> PnL 2.4x, calmar 2.3x,
    // maxDD khong doi). Truoc ban sua nay, gia tri nay CHI dung cho duong live/production
    // (khong qua HPO) nen bi lech so voi bestGenome cua WFO (~0.0385) - ban sua dong bo lai.
    public static float RATE_PROFIT_STOP_MARKET = 0.03f; // Khoảng dời SL tối thiểu (Base rate)
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
    // TASK (2026-07-17): env TIME_STOP_HOURS override (config-driven cho ladder WFO) > properties > 0.
    //   env unset -> fallback properties -> 0 = hanh vi cu NGUYEN VEN.
    public static int TIME_STOP_HOURS = System.getenv("TIME_STOP_HOURS") != null
            ? Integer.parseInt(System.getenv("TIME_STOP_HOURS").trim())
            : (properties.get("TIME_STOP_HOURS") != null
                ? Integer.parseInt(properties.get("TIME_STOP_HOURS")) : 0);
    // TASK (2026-07-17): che do chon DINH cho trailing-stop (arm + ratchet SL). env-driven, config-driven.
    //   high  = maxPrice (HIGH cua nen 1m) = MAC DINH = HANH VI CU (byte-identical, backward-compatible).
    //   close = priceClose (dong nen) de chong wick/giat. Chi doi diem ARM/RATCHET trailing, KHONG dung
    //           cho minPrice/maeLow (day, trigger cat + MAE), maePeak, disaster-SL, time-stop.
    public static final String TRAIL_PEAK_MODE = System.getenv("TRAIL_PEAK_MODE") != null
            ? System.getenv("TRAIL_PEAK_MODE").trim().toLowerCase() : "high";
    // TASK (2026-07-10): ti le nha lai dinh cua trailing (cu hardcode 0.5). 0.3 = giu chat, 0.7 = long nuoi trend.
    // 2026-08-02: them env-fallback (khop pattern TS_MIN_GAP) de sweep duoc TS_GIVEBACK_RATIO qua env.
    //   env > properties > 0.5f. env unset -> byte-identical hanh vi cu.
    public static float TS_GIVEBACK_RATIO = System.getenv("TS_GIVEBACK_RATIO") != null
            ? Float.parseFloat(System.getenv("TS_GIVEBACK_RATIO").trim())
            : (properties.get("TS_GIVEBACK_RATIO") != null ? Float.parseFloat(properties.get("TS_GIVEBACK_RATIO")) : 0.5f);
    public static float TS_DYNAMIC_K = 0.29774f;            // Hệ số nhân Volatility để dời SL
    public static float TS_PROFIT_MULTIPLIER = 5.21847f;    // Hệ số kích hoạt Trailing
    // TASK (2026-07-30, theo yeu cau Uni): "dead zone" giua ARM va RATCHET — sau khi arm (updateStatusNew,
    // dung predReturn15M), SL dong bang tai gia tri arm cho toi khi rateLoss vuot THEM 1 nguong cao hon
    // TS_PROFIT_MULTIPLIER lan (updateTPSL, dung rateChangeMax90M) - vd TS_PROFIT_MULTIPLIER=5.21847 =>
    // SL khong nhuc nhich cho toi khi lai gap ~5.2x diem arm, giu ca gia leo them ma khong siet SL theo.
    // false (MAC DINH) = HANH VI CU nguyen ven (updateTPSL nhan Configs.TS_PROFIT_MULTIPLIER, byte-identical).
    // true = bo he so nhan o updateTPSL — ratchet kich hoat NGAY khi rateLoss vuot threshold(rateChangeMax90M),
    // khong cho doi mot khoang trong. CHi doi diem RATCHET (updateTPSL); KHONG doi diem ARM (updateStatusNew)
    // va KHONG doi input rateChangeMax90M vs predReturn15M (van la 2 bien khac nhau, van la viec rieng).
    // ===== DCA GRID (2026-08-01) — thay DCA phan xa bang GRID CO KE HOACH =====
    // VAN DE cua DCA cu: nguong nhoi do bang calRateLoss() tren avgEntry, ma avgEntry tut sau moi lan
    // nhoi => muc lo "reset" => KHOANG CACH NHOI CO LAI DAN (15% -> 8% -> 5.5% -> 4.4%). Cang lo sau
    // cang nhoi day = chay het dan dung luc can tiet kiem nhat. Khong co tran so leg. BIG_DOWN con
    // tat ca thang chan margin (isAll=true).
    // GRID MOI: moc do tren firstEntryPrice (BAT BIEN qua DCA) => khoang cach GIAN dung nhu thiet ke.
    // So do tu du lieu that (171k entry, phan phoi MAE p50=-56%, xem EXIT_SWEEP + SurvivalProbe):
    //   -50/-75/-90 ti trong 1:1:3:8 -> chi 0.34% cum dung het dan, %hoi 78.3%, p95 lo -76.4%.
    //   Nhieu leg hon (5-6) do ra TE HON: %hoi tut con 43-62% vi moc -88/-90% hiem khi hoi.
    // Tong von moi coin GIU NGUYEN = getBudget(): leg_i = getBudget() * w[i]/sum(w).
    public static boolean DCA_GRID_ENABLED = "true".equalsIgnoreCase(System.getenv("DCA_GRID_ENABLED"));
    public static float[] DCA_GRID_LEVELS = parseFloats(
            System.getenv("DCA_GRID_LEVELS") != null ? System.getenv("DCA_GRID_LEVELS") : "-0.50,-0.75,-0.90");
    public static float[] DCA_GRID_WEIGHTS = parseFloats(
            System.getenv("DCA_GRID_WEIGHTS") != null ? System.getenv("DCA_GRID_WEIGHTS") : "1,1,3,8");

    // =========================================================
    // DCA GRID — DANG SCALAR (2026-08-01, de HPO tune duoc)
    // =========================================================
    // VAN DE: StrategyWfoTask ap gene bang reflection len FIELD SCALAR cua Configs
    // (setField -> Field.setFloat/setInt). Ba tham so grid o tren la MANG float[] => HPO
    // KHONG cham toi duoc => "chay HPO cho DCA" la bat kha thi voi dang mang.
    // GIAI PHAP: mo ta cung mot luoi bang 4 so vo huong, sinh mang khi can:
    //   levels[i] = clamp(DCA_GRID_L1 - DCA_GRID_STEP * i,  -0.99 .. -0.01),  i = 0..LEGS-1
    //   weights[0] = 1;  weights[i] = DCA_GRID_W_RATIO^i,                      i = 1..LEGS
    // Vi du DCA_GRID_L1=-0.50, STEP=0.20, LEGS=3, W_RATIO=2.0
    //   -> levels -0.50/-0.70/-0.90, weights 1/2/4/8 (xap xi 1:1:3:8 da do duoc).
    //
    // ⚠️ DCA_GRID_SCALAR MAC DINH FALSE = duong scalar TAT HAN, moi thu doc thang tu mang nhu cu
    //    => byte-identical voi ban chot tam (DCA_GRID_LEVELS=-0.50,-0.75,-0.90 / WEIGHTS=1,1,3,8).
    //    Chi bat =true khi chay HPO. Khi =true thi mang tren bi BO QUA hoan toan (khong con nguon
    //    su that kep — tranh dung tinh huong "set env mang nhung HPO tune scalar, khong biet cai nao thang").
    public static boolean DCA_GRID_SCALAR = "true".equalsIgnoreCase(System.getenv("DCA_GRID_SCALAR"));
    /** Muc lo kich hoat lan nhoi DAU TIEN, do tren firstEntryPrice (am). Gene HPO. */
    public static float DCA_GRID_L1 = envFloat("DCA_GRID_L1", -0.50f);
    /** Khoang GIAN giua hai bac lien tiep (duong). Gene HPO. */
    public static float DCA_GRID_STEP = envFloat("DCA_GRID_STEP", 0.20f);
    /** So bac nhoi (KHONG tinh leg dau). Gene HPO (int). */
    public static int DCA_GRID_LEGS = envInt("DCA_GRID_LEGS", 3);
    /** Ti le nhan ti trong giua hai leg lien tiep (>1 = nang dan ve day). Gene HPO. */
    public static float DCA_GRID_W_RATIO = envFloat("DCA_GRID_W_RATIO", 2.0f);

    /** So bac grid dang hieu luc (mang neu SCALAR=false, DCA_GRID_LEGS neu true). */
    public static int dcaGridLegs() {
        return DCA_GRID_SCALAR ? Math.max(1, DCA_GRID_LEGS) : DCA_GRID_LEVELS.length;
    }

    /**
     * Muc lo kich hoat bac thu (legIdx+1), legIdx 0-based. Tra ve so AM.
     * Tra 0f khi legIdx vuot so bac => caller hieu la "het bac, khong nhoi nua".
     */
    public static float dcaGridLevel(int legIdx) {
        if (legIdx < 0 || legIdx >= dcaGridLegs()) return 0f;
        if (!DCA_GRID_SCALAR) return DCA_GRID_LEVELS[legIdx];
        float lv = DCA_GRID_L1 - Math.abs(DCA_GRID_STEP) * legIdx;
        // clamp: khong vuot -99% (gia ve 0 la delist, khong con lenh de nhoi) va khong nong hon -1%
        if (lv < -0.99f) lv = -0.99f;
        if (lv > -0.01f) lv = -0.01f;
        return lv;
    }

    /** Ti trong THO cua leg thu legIdx (0 = leg dau). 0f khi vuot so leg. */
    public static float dcaGridWeight(int legIdx) {
        if (legIdx < 0 || legIdx > dcaGridLegs()) return 0f;
        if (!DCA_GRID_SCALAR) {
            return legIdx < DCA_GRID_WEIGHTS.length ? DCA_GRID_WEIGHTS[legIdx] : 0f;
        }
        if (legIdx == 0) return 1f;
        float r = Math.max(1f, DCA_GRID_W_RATIO);
        return (float) Math.pow(r, legIdx);
    }

    // === TRAN MARGIN THEO BAC DO SAU (2026-08-01) — giai bai toan "sap lien tiep con von de DCA" ===
    // VAN DE cua BREAKER_MARGIN_HALT: no la VACH DUNG o 50%. Duoi 50% nhoi vo han, cham 50% dung het.
    //   => Dot sap 1: hang tram coin cung nhoi leg2 -> margin vot len 50% -> KHOA.
    //      Dot sap 2 (gia re hon nhieu): KHONG nhoi duoc gi, ke ca leg -90%.
    //   Tuc no chan dung nhung leg CO GIA TRI CAO NHAT. SurvivalProbe: 76.4% cum xuong -80% van hoi va
    //   thoat co lai — nhom ti le thang cao nhat lai bi chan, con leg1 (chua lo gi) duoc tieu von truoc.
    // GIAI PHAP: moi BAC grid mot tran rieng, bac cang sau tran cang cao. Khi margin da 45% thi lenh MOI
    //   bi chan nhung leg 3-4 VAN nhoi duoc => von khong the bi lenh nong tieu het => luon con dan cho
    //   vung sau, va dan do CHI tieu duoc o vung sau.
    // Do dai mang = so bac (leg1..legN). Mac dinh OFF (dung tran phang cu) de byte-identical.
    public static boolean DCA_TIER_MARGIN_ENABLED = "true".equalsIgnoreCase(System.getenv("DCA_TIER_MARGIN_ENABLED"));
    public static float[] DCA_TIER_MARGIN_CAPS = parseFloats(
            System.getenv("DCA_TIER_MARGIN_CAPS") != null ? System.getenv("DCA_TIER_MARGIN_CAPS") : "0.25,0.40,0.60,0.80");

    // Dang SCALAR cua tran bac (cung ly do voi DCA_GRID_SCALAR: mang float[] thi HPO khong tune duoc):
    //   cap[i] = clamp(DCA_TIER_CAP_BASE + DCA_TIER_CAP_STEP * i, 0.05 .. 0.98)
    // BASE=0.50 giu dung vach production BREAKER_MARGIN_HALT cho leg dau; STEP noi dan cho leg sau.
    // Chi co hieu luc khi DCA_GRID_SCALAR=true (dung 1 cong tac cho ca cum, khong de rai rac nhieu co).
    /** Tran margin cho leg DAU (legIdx=0). Gene HPO. */
    public static float DCA_TIER_CAP_BASE = envFloat("DCA_TIER_CAP_BASE", 0.50f);
    /** Moi bac sau noi them bao nhieu. 0 = tran phang. Gene HPO. */
    public static float DCA_TIER_CAP_STEP = envFloat("DCA_TIER_CAP_STEP", 0.10f);

    /** Tran margin cho phep khi sap mo leg thu (legIdx+1). legIdx 0-based. */
    public static float tierMarginCap(int legIdx) {
        int i = Math.max(0, legIdx);
        if (DCA_GRID_SCALAR) {
            float cap = DCA_TIER_CAP_BASE + DCA_TIER_CAP_STEP * i;
            if (cap < 0.05f) cap = 0.05f;
            if (cap > 0.98f) cap = 0.98f;
            return cap;
        }
        float[] c = DCA_TIER_MARGIN_CAPS;
        if (c.length == 0) return BREAKER_MARGIN_HALT;
        return c[Math.min(i, c.length - 1)];
    }

    // DCA_GRID_SCALE (2026-08-01): he so nhan CA THANG. Ly do can no: chia budget theo ti trong
    //   1:1:3:8 lam leg dau chi con 1/13 budget, ma do do sau -50/-75/-90 nen chi 0.34% cum cham day
    //   => 99.66% thoi gian von NAM KHONG => WFO dcagrid1 ra PnL tut 11 lan (maxDD cung tut 20 lan).
    //   scale bu lai phan du tru khong dung. scale=6 => leg dau ~46% budget, tong khi cham day = 6x budget
    //   (chi xay ra 0.34%). Dinh von dong thoi phai kiem bang CapacityProbe truoc khi tang.
    public static float DCA_GRID_SCALE = System.getenv("DCA_GRID_SCALE") != null
            ? Float.parseFloat(System.getenv("DCA_GRID_SCALE").trim()) : 1.0f;

    private static float[] parseFloats(String csv) {
        String[] p = csv.split(",");
        float[] r = new float[p.length];
        for (int i = 0; i < p.length; i++) r[i] = Float.parseFloat(p[i].trim());
        return r;
    }

    /** env -> float, rong/sai dinh dang -> def (khong nem, khong giet clinit). */
    private static float envFloat(String name, float def) {
        String v = System.getenv(name);
        try { return (v != null && !v.trim().isEmpty()) ? Float.parseFloat(v.trim()) : def; }
        catch (NumberFormatException e) { return def; }
    }

    /** env -> int, rong/sai dinh dang -> def. */
    private static int envInt(String name, int def) {
        String v = System.getenv(name);
        try { return (v != null && !v.trim().isEmpty()) ? Integer.parseInt(v.trim()) : def; }
        catch (NumberFormatException e) { return def; }
    }

    /**
     * Tong ti trong — de quy doi leg_i = budget * w[i]/totalWeight (tong von/coin KHONG doi).
     * SCALAR=false: cong het mang (hanh vi cu, byte-identical).
     * SCALAR=true : cong w(0..LEGS) sinh tu DCA_GRID_W_RATIO — PHAI tinh lai moi lan goi vi HPO
     *               doi W_RATIO/LEGS giua cac sample trong cung mot JVM (khong duoc cache static).
     */
    public static float dcaGridTotalWeight() {
        if (!DCA_GRID_SCALAR) {
            float s = 0; for (float x : DCA_GRID_WEIGHTS) s += x; return s;
        }
        float s = 0;
        int n = dcaGridLegs();
        for (int i = 0; i <= n; i++) s += dcaGridWeight(i);
        return s > 0 ? s : 1f;
    }

    // ===== FIX AUDIT 2026-08-01 — 3 co, MAC DINH FALSE = HANH VI CU BYTE-IDENTICAL =====
    // F7: mergeOrder (DCA nhoi them leg) tao object cum MOI va KHONG carry priceSL => cum da arm SL
    //     o +2.5% ma bi nhoi 1 leg la MAT SACH bao ve, phai arm lai tu avgEntry moi. true = mang SL cu
    //     sang cum moi, NHUNG chi khi SL cu van > avgEntry moi (neu khong se thanh cat-lo-ngay).
    public static boolean TS_CARRY_SL_ON_DCA = "true".equalsIgnoreCase(System.getenv("TS_CARRY_SL_ON_DCA"));
    // F10: coin delist/dong bang co the phat nen phang volume=0 thay vi null => isTickerAvailable van
    //      true => timeUpdate lien tuc moi => updateSymbolDeListed KHONG BAO GIO kich hoat => cum song
    //      mai va cuoi ky duoc mark-to-market o GIA DONG BANG thay vi ghi giam ve ~0 (thien lech duong).
    //      true = coi nen volume 0 nhu ticker khong kha dung.
    public static boolean SIM_TREAT_ZERO_VOL_AS_DELIST = "true".equalsIgnoreCase(System.getenv("SIM_TREAT_ZERO_VOL_AS_DELIST"));
    // F9: mac dinh backtest NUOT exception trong vong lap phut/ngay (chi printStackTrace) va SKIP
    //     nguyen ngay neu <1440 phut => ngay do khong kiem SL, khong cap nhat maxDD (thien lech duong)
    //     ma van bao "chay thanh cong". true = nem loi ngay, khong cho ket qua ban ra ngoai.
    public static boolean SIM_FAIL_FAST_ON_DATA_ERROR = "true".equalsIgnoreCase(System.getenv("SIM_FAIL_FAST_ON_DATA_ERROR"));

    // KHONG final (2026-07-31): can gan lai runtime trong RatchetDecoupleSweepProbe (so sanh
    // true/false truc tiep, khong qua WFO/HPO). Gia tri khoi tao van tu env nhu cu, khong doi hanh vi
    // production/WfoWorker (chi doi khi co code khac chu dong gan lai, khong ai lam vay ngoai probe).
    public static boolean TS_RATCHET_DECOUPLED = "true".equalsIgnoreCase(System.getenv("TS_RATCHET_DECOUPLED"));

    // TASK (2026-07-31, EXIT_MACHINE PHAN 1/2, hang muc P6 "giveback fix"): gap = min(peak*g, maxGap)
    // khien ti le nha lai TEO DAN khi p lon (maxGap/p -> 0) - cat mat duoi x2/x3 (xem doc PHAN 1
    // "PHAT HIEN 2"). Y tuong sua: gap = max(peak*g, minGap) - nha theo ti le, co SAN tuyet doi de
    // nhieu khong giet luc p nho, KHONG co TRAN nen lai lon duoc nuoi dung ti le thay vi bi siet.
    // false (MAC DINH) = HANH VI CU nguyen ven (calRateLossDynamicBuy dung Math.min(...,maxGap),
    // byte-identical). true = doi sang Math.max(...,TS_MIN_GAP). Ca ARM (updateStatusNew) va RATCHET
    // (updateTPSL) deu goi chung TradeUtils.calRateLossDynamicBuy -> flag nay anh huong CA HAI diem,
    // dung nhu maxGap/g hien tai dang anh huong ca hai.
    // KHONG final: ExitParamSweepProbe can gan lai runtime de sweep. Mac dinh van doc tu env nhu cu.
    public static boolean TS_GIVEBACK_FLOOR = "true".equalsIgnoreCase(System.getenv("TS_GIVEBACK_FLOOR"));
    // San tuyet doi cho gap khi TS_GIVEBACK_FLOOR=true. CHUA CO CAN CU CHON GIA TRI - can Uni chot
    // (grid E3 trong EXIT_MACHINE PHAN 2) truoc khi tin so ra tu default nay. env > properties > 0.01f.
    public static float TS_MIN_GAP = System.getenv("TS_MIN_GAP") != null
            ? Float.parseFloat(System.getenv("TS_MIN_GAP").trim())
            : (properties.get("TS_MIN_GAP") != null ? Float.parseFloat(properties.get("TS_MIN_GAP")) : 0.01f);

    // =========================================================
    // 6b. SHORT-SIDE (DRAFT 2026-07-18, flag-gated — MAC DINH OFF = long-only byte-identical)
    // =========================================================
    // Them order-side SHORT (OrderSide.SELL) vao sim de sau chay WFO short (proxy Kaggle xac nhan alpha).
    // MAC DINH ENABLE_SHORT=false -> KHONG tao/quan ly lenh SELL nao -> engine byte-identical long-only.
    // Chi bat (=true) de chay backtest short SAU khi review. env-driven (khong can rebuild).
    public static final boolean ENABLE_SHORT = "true".equalsIgnoreCase(System.getenv("ENABLE_SHORT"));
    // Hard-SL CUNG BAT BUOC cho short: gia TANG (rise) >= SHORT_SL_PCT so voi entry -> cat lo tai -SHORT_SL_PCT.
    // Mac dinh 0.25 = 25% (chot tu proxy). env SHORT_SL_PCT override.
    public static float SHORT_SL_PCT = System.getenv("SHORT_SL_PCT") != null
            ? Float.parseFloat(System.getenv("SHORT_SL_PCT").trim()) : 0.25f;
    // Time-stop cho short (let-dump-run toi han): thoat sau SHORT_TIME_STOP_HOURS ke tu leg dau cum. 0 = tat.
    // Mac dinh 24h (chot tu proxy: chop duong 12-24h). env SHORT_TIME_STOP_HOURS override.
    public static int SHORT_TIME_STOP_HOURS = System.getenv("SHORT_TIME_STOP_HOURS") != null
            ? Integer.parseInt(System.getenv("SHORT_TIME_STOP_HOURS").trim()) : 24;

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
    // [2026-08-29 DEV pivot] AI lai TRAILING per-symbol: arm-SL gap dung symbolPred cua chinh coin
    // (khop updateTPSL). false = hanh vi cu (arm dung market predReturn15M). Env SIM_TRAIL_PER_SYMBOL.
    public static boolean TRAIL_PER_SYMBOL = false;
    // [2026-08-29 DEV pivot] Tat market gate MOM15 (bo entry-gate muc thi truong). Env SIM_GATE_MARKET_OFF.
    public static boolean GATE_MARKET_OFF = false;

    // === ABLATION (Bước 2 roadmap: edge từ AI hay DCA? — chỉ ĐO, mặc định A, KHÔNG ảnh hưởng CONFIG_VERSION) ===
    // A=control (AI filter bật như thường) | B=no-AI (bỏ qua filter, mọi tín hiệu PASS) | C=placebo
    // (entry ngẫu nhiên cùng XÁC SUẤT pass như A). So leg-đầu (MAE/rescue/firstLegPnl) giữa A và B/C.
    // CHỈ tác động tại điểm AI filter trong createOrderBUY, KHÔNG đụng logic DCA/exit/budget.
    // TASK (2026-07-11) doc tu env de test gate-off (mode B) khong can sua WfoWorker; van mac dinh A.
    public static String ABLATION_MODE = System.getenv("ABLATION_MODE") != null
            ? System.getenv("ABLATION_MODE") : "A";
    public static long ABLATION_SEED = 42L;
    // ABLATION DCA-OFF (2026-07-16): env WFO_DISABLE_DCA=1 -> DcaProcessor.getDCA tra rong (tat nhoi lenh
    // hoan toan) de do dong gop DCA. Mac dinh false = hanh vi cu NGUYEN VEN.
    public static final boolean WFO_DISABLE_DCA = "1".equals(System.getenv("WFO_DISABLE_DCA"));

    // ENTRY-MATCH PROBE (2026-07-18): env WFO_LOG_ENTRIES=1 -> log 1 dong ENTRY_DUMP moi khi 1 leg vao lenh
    // that su (sau khi qua het cong). Mac dinh false = KHONG log = hanh vi cu byte-identical.
    public static final boolean WFO_LOG_ENTRIES = "1".equals(System.getenv("WFO_LOG_ENTRIES"));

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

    // MAX-DEPLOYMENT (ablation tan-suat): override TRUC TIEP tran score cua selector-gate (final cutoff
    //   tren symbolPred = 1 - p6). Selector cu: maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MAX
    //   = 0.15*2.14135 = 0.3212 -> admit p6 >= 0.679. Set SELECTOR_SCORE_MAX=0.5 -> admit p6 >= 0.5
    //   (nhieu lenh hon) MA KHONG dinh AI_DYNAMIC_MAX (genome-coupled). Default -1f = OFF = byte-identical.
    public static final float SELECTOR_SCORE_MAX = System.getenv("SELECTOR_SCORE_MAX") != null
            ? Float.parseFloat(System.getenv("SELECTOR_SCORE_MAX").trim()) : -1f;
    // ALPHA-TEST (placebo selector): dao thu hang selector -> chon coin TE-nhat-truoc thay vi TOT-nhat.
    // Cung gate/nguong/so-lenh, chi doi uu tien budget. So PnL INVERT=0 vs =1 => selector co alpha that khong.
    // Default false = byte-identical (khong dao).
    public static final boolean SELECTOR_INVERT = "1".equals(System.getenv("SELECTOR_INVERT"));
    // WORST-N BREADTH CAP (2026-07-22): cap so candidate selector-path mo dong thoi tai MOI moc tin hieu.
    // Selector cu chon TAT CA nPass candidate qua gate; SELECTOR_TOPN>0 -> chi lay N candidate dau tien theo
    // uu tien hien hanh (INVERT=1 -> N coin TE-nhat/oversold; INVERT=0 -> N coin TOT-nhat). Dung cho sweep
    // Worst-3/5/8: tap trung von, giam capital-lock. Default -1 = OFF = uncapped = byte-identical.
    public static final int SELECTOR_TOPN = System.getenv("SELECTOR_TOPN") != null
            ? Integer.parseInt(System.getenv("SELECTOR_TOPN").trim()) : -1;
    // SELECTOR OFFSET (2026-07-24, offset-sweep): bo qua [SELECTOR_OFFSET] candidate o cuc bien TRUOC khi lay N.
    //  INVERT=1 (Worst-N): bo qua N coin TE-nhat (tail cuoi mang = dead-coin/rac cua truoc) roi lay TOPN coin
    //    tiep theo (oversold that, con luc nay). INVERT=0 (Best-N): bo qua N coin TOT-nhat dau mang.
    //  Clamp theo do dai mang (WORST) / nPass (BEST) de tranh IndexOutOfBounds. Default 0 = OFF = byte-identical.
    public static final int SELECTOR_OFFSET = System.getenv("SELECTOR_OFFSET") != null
            ? Integer.parseInt(System.getenv("SELECTOR_OFFSET").trim()) : 0;
    // RANK-BASED TOP-K (2026-07-28, Probe A go/no-go): thay leg selector tu ABSOLUTE threshold
    //  (nPass = so coin co score <= maxThres) sang RANK top-K per timestamp. Khi SELECTOR_RANK_TOPK=k (k>0)
    //  -> BO QUA maxThres/nPass, chon K coin score THAP nhat (symbol2Pred da sort tang -> lay k phan tu dau).
    //  Muc dich: tu-chuan-hoa theo regime (khong starve luc yeu, khong flood luc manh) thay vi absolute cutoff.
    //  Doc lap SELECTOR_TOPN (cai do van bi cap boi nPass). Default -1 = OFF = giu absolute = byte-identical.
    public static final int SELECTOR_RANK_TOPK = System.getenv("SELECTOR_RANK_TOPK") != null
            ? Integer.parseInt(System.getenv("SELECTOR_RANK_TOPK").trim()) : -1;
    // RANK OFFSET (2026-07-28, offset-sweep tren rank top-K): bo qua [SELECTOR_RANK_OFFSET] coin score
    //  THAP nhat (top dau) TRUOC khi lay K -> lay symbol2Pred[off .. off+K). Gia thuyet: top dau lan
    //  fake-pump sap dump; bo vai coin dau lay K tiep theo giam nhiem. RIENG voi SELECTOR_OFFSET (dung cho
    //  branch INVERT/best-N). Clamp theo poolSize. Default 0 = OFF = lay [0..K) = hanh vi cu byte-identical.
    public static final int SELECTOR_RANK_OFFSET = System.getenv("SELECTOR_RANK_OFFSET") != null
            ? Integer.parseInt(System.getenv("SELECTOR_RANK_OFFSET").trim()) : 0;
    // SELECTOR-ONLY ENTRY (2026-07-23): SELECTOR_ONLY_ENTRY=1 -> TAT leg entry theo market-signal
    // (levelChange getTopSymbolArray Best-N = luong FOMO), CHI giu luong selector PREDICT_SYMBOL_TRADE.
    // Dung de co lap 100% edge inverted-selector (khop proxy Kaggle). Default false = byte-identical.
    public static final boolean SELECTOR_ONLY_ENTRY = "1".equals(System.getenv("SELECTOR_ONLY_ENTRY"));
    // COUNT-ONLY: đếm gate admission rồi short-circuit trước khi tạo order (đo tần suất qua gate).
    // Default false = byte-identical. Bật bằng env SIM_GATE_COUNT_ONLY=1.
    public static final boolean GATE_COUNT_ONLY = "1".equals(System.getenv("SIM_GATE_COUNT_ONLY"));
    // ENTRY-UNIVERSE DUMP (E0, 2026-07-30): khi CHAY CUNG GATE_COUNT_ONLY, ghi lai TUNG admission
    //  (ts, symbolId, score, price, levelChange) vao list RAM thay vi chi tang counter. Muc dich: dung
    //  dung duong admission THAT (gate ∩ rank-K) de dem so VI THE DOC LAP sau dedup, phuc vu nghien cuu
    //  exit tren tap entry dong bang (docs/reports/EXIT_MACHINE_20260730_stop_schedule.md, buoc E0).
    //  Vi GATE_COUNT_ONLY khong bao gio tao order -> isSymbolRunning luon false -> tu dong BO filter von,
    //  dung y muon C1. Default false = OFF = khong ton RAM, byte-identical.
    public static final boolean ENTRY_UNIVERSE_DUMP = "1".equals(System.getenv("SIM_ENTRY_UNIVERSE_DUMP"));
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
    // HARD-SL BLANKET (env SIM_HARD_SL_PCT) — hard stop-loss tinh tren GIA ENTRY DAU TIEN
    //   (firstEntryPrice, bat bien qua DCA — KHONG dung averaged priceEntry). Default 0f = OFF =
    //   byte-identical. Doc env o static SIM block ben duoi (Float.parseFloat).
    public static float HARD_SL_PCT = 0f;

    // 2026-08-03 GRID-ALIGN ENTRY: model selector du doan TAI moc 15m (ts%900000==0), label maxFav do tu
    //   gia moc 15m. Forward-fill 15m->1m cho vao giua cua so -> vao o gia DA CHAY != reference model hoc.
    //   Co nay chi cho selector entry (PREDICT_SYMBOL_TRADE) fire khi offset-trong-snapshot <= N phut.
    //   N=0 -> chi mat moc 15m (align chuan). N=-1 (default) -> OFF, khong gioi han = byte-identical.
    public static final int SIM_SELECTOR_MAX_STALE_MIN =
            System.getenv("SIM_SELECTOR_MAX_STALE_MIN") != null
            ? Integer.parseInt(System.getenv("SIM_SELECTOR_MAX_STALE_MIN").trim()) : -1;

    // =========================================================
    // 9. KẾT NỐI DỮ LIỆU (STORAGE & AEROSPIKE)
    // =========================================================
    public static final String FILE_AI_ENTRY_PREDICTIONS = Configs.getString("FILE_AI_PREDICTIONS");

    public static final String AEROSPIKE_HOST_242 = Configs.getString("AEROSPIKE_HOST");
    public static final int AEROSPIKE_PORT_242 = Configs.getInt("AEROSPIKE_PORT");

    // Tên hằng đổi 226→ORACLE (2026-08-04, retire 226). GIỮ config-key "AEROSPIKE_HOST_226" để
    // tương thích config.properties đã deploy (Oracle/Kaggle/dev) — đổi key là bước migration riêng.
    public static final String AEROSPIKE_HOST_ORACLE = Configs.getString("AEROSPIKE_HOST_226");
    public static final int AEROSPIKE_PORT_ORACLE = Configs.getInt("AEROSPIKE_PORT_226");

    public static final String AEROSPIKE_NAMESPACE = Configs.getString("AEROSPIKE_NAMESPACE");

    // [TASK-251, 2026-08-05] Namespace THẬT trên cụm 242 là "ticker" (đo trực tiếp bằng
    // client.info_all('namespaces'), KHÔNG phải "test" như AEROSPIKE_NAMESPACE ở trên — hằng số
    // đó chỉ đúng cho Oracle-local). Trước đây CopyTicker242To226/CopyAuxSets242To226 dùng CHUNG
    // AEROSPIKE_NAMESPACE cho cả đọc-242 và đọc/ghi-Oracle => đọc 242 luôn fail
    // (AerospikeException$InvalidNamespace). Hằng số riêng này CHỈ dùng cho 2 tool copy đó khi
    // đọc từ 242 — KHÔNG đổi AEROSPIKE_NAMESPACE ở trên (đang đúng cho Oracle, nhiều nơi khác
    // đang dùng đúng). Nếu properties thiếu key này (config.properties cũ chưa cập nhật), giá trị
    // sẽ là null — 2 tool copy sẽ fail rõ ràng ngay ở bước đọc (Key namespace null), KHÔNG âm thầm
    // dùng nhầm "test". Deploy config.properties mới lên Oracle TRƯỚC khi chạy lại 2 tool này.
    public static final String AEROSPIKE_NAMESPACE_242 = Configs.getString("AEROSPIKE_NAMESPACE_242");

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
            if ((v = System.getenv("SIM_TRAIL_PER_SYMBOL")) != null) TRAIL_PER_SYMBOL = Boolean.parseBoolean(v);
            if ((v = System.getenv("SIM_GATE_MARKET_OFF")) != null) GATE_MARKET_OFF = Boolean.parseBoolean(v);
            if ((v = System.getenv("SIM_AI_DYNAMIC_MIN")) != null) AI_DYNAMIC_MIN = Float.parseFloat(v);
            if ((v = System.getenv("SIM_PREDICT_SYMBOL_RATE_MAX")) != null) PREDICT_SYMBOL_RATE_MAX_THRESHOLD = Float.parseFloat(v);
            if ((v = System.getenv("SIM_RATE_PROFIT_STOP_MARKET")) != null) RATE_PROFIT_STOP_MARKET = Float.parseFloat(v);
            if ((v = System.getenv("SIM_TS_PROFIT_MULTIPLIER")) != null) TS_PROFIT_MULTIPLIER = Float.parseFloat(v);
            if ((v = System.getenv("SIM_BREAKER_MODE")) != null) BREAKER_MODE = v;
            if ((v = System.getenv("SIM_BREAKER_MARGIN_HALT")) != null) BREAKER_MARGIN_HALT = Float.parseFloat(v);
            if ((v = System.getenv("SIM_MS_DOWN_BIG_AVG")) != null) MS_DOWN_BIG_AVG = Float.parseFloat(v);
            if ((v = System.getenv("SIM_HARD_SL_PCT")) != null) HARD_SL_PCT = Float.parseFloat(v);
            // TASK (frozen leakage-free genome, Buoc 0): funding.bin trong WFO_DATA_DIR/-ff CHI tu-ap cho
            //   funding-SELECTOR (ds.funding), KHONG tu-ap thanh FEE. Fee van gate boi APPLY_FUNDING_FEE
            //   (default false). SIM_APPLY_FUNDING=true -> bat funding fee cho vong WFO/HPO nay (funding-on).
            //   Default (env rong) -> giu false = byte-identical.
            if ((v = System.getenv("SIM_APPLY_FUNDING")) != null) APPLY_FUNDING_FEE = Boolean.parseBoolean(v);
        } catch (Exception e) {
            System.err.println("SIM env override parse error: " + e);
        }
    }

    public static void main(String[] args) {
        // Test configurations here
    }
}
