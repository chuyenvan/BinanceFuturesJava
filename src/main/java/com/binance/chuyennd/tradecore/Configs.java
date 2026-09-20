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
                // 2026-09-03 (B3): bo qua dong trong va dong COMMENT. Truoc day chi kiem tra co dau '='
                // nen comment kieu "# ... (Oracle = backtest)" bien thanh mot key rac.
                String trimmed = line == null ? "" : line.trim();
                if (trimmed.isEmpty() || trimmed.startsWith("#")) continue;
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
    public static Float RATE_FEE = 0.002f; // Phí giao dịch sàn đã sửa thành 2 chân (env SIM_RATE_FEE chi cho stress test)
    // [2026-09-02 STRESS] he so nhan funding accrual (mark mode). 1.0 = hanh vi cu. env SIM_FUNDING_SCALE.
    public static float FUNDING_SCALE = 1.0f;
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
    // [2026-09-02] FUNDING theo notional MARK: tich luy tai MOI ky settle voi qty dang mo x gia hien tai (thay cho
    //   qty_cuoi_cum x avgEntry co dinh trong computeFundingOnClose). Ly do: coin roi -90% giu 900 ngay (AXS DEV)
    //   bi thoi funding nhan ~10x (sim -130.7 vs mark -35.1). env SIM_FUNDING_MARK=true. Default false = byte-identical.
    //   Chi la KE TOAN o closeOrder — KHONG tham gia quyet dinh mo/dong lenh (khong doi so lenh).
    public static boolean FUNDING_MARK_NOTIONAL = false;


    public static float TS_MAX_GAP = 0.08f; // gap trailing tối đa (cũ: 16/200)
    public static float TS_MAX_GAP_WEAK = 0.03f; // gap khi momentum yếu (cũ: 6/200)

    // =========================================================
    // 4. QUẢN TRỊ VỐN TỰ ĐỘNG (BUDGET MANAGEMENT)
    // =========================================================
    // TASK (2026-07-10): cho phep override qua config de SWEEP SIZING (khong rebuild moi lan). Mac dinh 50 = cu.
    // BASE_BUDGET = BALANCE_BASIC / number_order_budget. Giam so nay = size/lenh lon hon = trien khai nhieu von hon.
    // 2026-09-03 (B3): env/profile > properties > 50. Truoc day CHI doc properties => profile khong kiem soat duoc.
    public static Integer number_order_budget = Cfg.get("NUMBER_ORDER_BUDGET") != null
            ? Integer.parseInt(Cfg.get("NUMBER_ORDER_BUDGET").trim())
            : (properties.get("NUMBER_ORDER_BUDGET") != null
                ? Integer.parseInt(properties.get("NUMBER_ORDER_BUDGET")) : 50); // Tổng số phần chia vốn

    // ===== BUDGET v1 (FROZEN 2026-08-24) — throttle liên tục thay logic vách rời rạc =====
    public static float F_BASE = 0.03f;   // % equity mỗi lệnh gốc (gene search [0.01, 0.05])
    public static float U_MAX  = 0.60f;   // trần tổng margin/equity, U≥U_MAX → chặn (gene search [0.40, 0.80])



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
    // TASK (2026-07-10): ti le nha lai dinh cua trailing (cu hardcode 0.5). 0.3 = giu chat, 0.7 = long nuoi trend.
    // 2026-08-02: them env-fallback (khop pattern TS_MIN_GAP) de sweep duoc TS_GIVEBACK_RATIO qua env.
    //   env > properties > 0.5f. env unset -> byte-identical hanh vi cu.
    public static float TS_GIVEBACK_RATIO = Cfg.get("TS_GIVEBACK_RATIO") != null
            ? Float.parseFloat(Cfg.get("TS_GIVEBACK_RATIO").trim())
            : (properties.get("TS_GIVEBACK_RATIO") != null ? Float.parseFloat(properties.get("TS_GIVEBACK_RATIO")) : 0.5f);
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
    public static boolean DCA_GRID_ENABLED = "true".equalsIgnoreCase(Cfg.get("DCA_GRID_ENABLED"));
    public static float[] DCA_GRID_LEVELS = parseFloats(
            Cfg.get("DCA_GRID_LEVELS") != null ? Cfg.get("DCA_GRID_LEVELS") : "-0.50,-0.75,-0.90");
    public static float[] DCA_GRID_WEIGHTS = parseFloats(
            Cfg.get("DCA_GRID_WEIGHTS") != null ? Cfg.get("DCA_GRID_WEIGHTS") : "1,1,3,8");

    // =========================================================
    // DCA ROUND CAP (2026-09-16) — tran TONG margin moi moi luot DCA. docs/PREREG_DCA_ROUND_CAP.md.
    //   Mac dinh OFF => DcaProcessor.getDCA chay logic cu NGUYEN VEN (byte-identical).
    //   - DCA_ROUND_CAP_ENABLED : bat/tat tran (goc cua user: "moi luot max 10% von").
    //   - DCA_ROUND_CAP_PCT      : tran = PCT x equity hien tai (equityNow).
    //   - DCA_RANK_MODE          : off (khong rank/khong cap) | drop (rank theo drop tang dan).
    // =========================================================
    public static boolean DCA_ROUND_CAP_ENABLED = "true".equalsIgnoreCase(Cfg.get("DCA_ROUND_CAP_ENABLED"));
    public static float DCA_ROUND_CAP_PCT = Cfg.get("DCA_ROUND_CAP_PCT") != null
            ? Float.parseFloat(Cfg.get("DCA_ROUND_CAP_PCT").trim()) : 0.10f;
    public static String DCA_RANK_MODE = Cfg.getOr("DCA_RANK_MODE", "off");

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
    public static boolean DCA_GRID_SCALAR = "true".equalsIgnoreCase(Cfg.get("DCA_GRID_SCALAR"));
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


    // DCA_GRID_SCALE (2026-08-01): he so nhan CA THANG. Ly do can no: chia budget theo ti trong
    //   1:1:3:8 lam leg dau chi con 1/13 budget, ma do do sau -50/-75/-90 nen chi 0.34% cum cham day
    //   => 99.66% thoi gian von NAM KHONG => WFO dcagrid1 ra PnL tut 11 lan (maxDD cung tut 20 lan).
    //   scale bu lai phan du tru khong dung. scale=6 => leg dau ~46% budget, tong khi cham day = 6x budget
    //   (chi xay ra 0.34%). Dinh von dong thoi phai kiem bang CapacityProbe truoc khi tang.
    public static float DCA_GRID_SCALE = Cfg.get("DCA_GRID_SCALE") != null
            ? Float.parseFloat(Cfg.get("DCA_GRID_SCALE").trim()) : 1.0f;

    private static float[] parseFloats(String csv) {
        String[] p = csv.split(",");
        float[] r = new float[p.length];
        for (int i = 0; i < p.length; i++) r[i] = Float.parseFloat(p[i].trim());
        return r;
    }

    /** env -> float, rong/sai dinh dang -> def (khong nem, khong giet clinit). */
    private static float envFloat(String name, float def) {
        String v = Cfg.get(name);
        try { return (v != null && !v.trim().isEmpty()) ? Float.parseFloat(v.trim()) : def; }
        catch (NumberFormatException e) { return def; }
    }

    /** env -> int, rong/sai dinh dang -> def. */
    private static int envInt(String name, int def) {
        String v = Cfg.get(name);
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
    // F9: mac dinh backtest NUOT exception trong vong lap phut/ngay (chi printStackTrace) va SKIP
    //     nguyen ngay neu <1440 phut => ngay do khong kiem SL, khong cap nhat maxDD (thien lech duong)
    //     ma van bao "chay thanh cong". true = nem loi ngay, khong cho ket qua ban ra ngoai.
    public static boolean SIM_FAIL_FAST_ON_DATA_ERROR = "true".equalsIgnoreCase(Cfg.get("SIM_FAIL_FAST_ON_DATA_ERROR"));





    // =========================================================

    // =========================================================
    // 7. AI & BỘ LỌC TÍN HIỆU ĐỘNG (AI DYNAMIC FILTER - HPO UPDATE)
    // =========================================================
    // [L7 2026-09-11] HAI FIELD DUOI DAY KHONG CON LA NGUONG GATE ENTRY.
    //   Cong entry tang 2 doc HANG SO trong com.binance.chuyennd.tradecore.EntryGate.
    //   Chung chi con phuc vu cac tool HPO/validation offline (WFORunner, StrategyWfoTask,
    //   SensitivityTool, RunWorkerKaggle, BackTestEngineDynamicFilter, ValidateBrakeDynamic...).
    //   => gene "AI_DYNAMIC_MIN"/"AI_DYNAMIC_MULTIPLIER" trong cac tool do KHONG con tac dong
    //      len gate. Go chung khoi gene vector la viec cua L8 (doi index gene, khong lam chung
    //      voi cong parity nay). Xem docs/L7_LEAN_GATE.md muc "con lai".
    public static float AI_DYNAMIC_MULTIPLIER = 1.28760f; // Cũ: 1.40234f
    public static float AI_DYNAMIC_MIN = 0.26787f;        // Cũ: 0.14568f
    public static float AI_DYNAMIC_MAX = 2.14135f;        // Cũ: 2.24405f





    // ABLATION DCA-OFF (2026-07-16): env WFO_DISABLE_DCA=1 -> DcaProcessor.getDCA tra rong (tat nhoi lenh
    // hoan toan) de do dong gop DCA. Mac dinh false = hanh vi cu NGUYEN VEN.
    public static final boolean WFO_DISABLE_DCA = "1".equals(Cfg.get("WFO_DISABLE_DCA"));

    // ENTRY-MATCH PROBE (2026-07-18): env WFO_LOG_ENTRIES=1 -> log 1 dong ENTRY_DUMP moi khi 1 leg vao lenh
    // that su (sau khi qua het cong). Mac dinh false = KHONG log = hanh vi cu byte-identical.
    public static final boolean WFO_LOG_ENTRIES = "1".equals(Cfg.get("WFO_LOG_ENTRIES"));

    // BINS SELECTOR (2026-09-03): thu muc predict_wf_*.bin cua selector dang dung.
    // Doc o day de MOI process (sim va export) deu KHAI BAO bins nao va de duong dan bins
    // vao CONFIG_HASH - truoc day doi selector ma CONFIG_HASH/PROFILE_HASH khong he doi
    // (docs/AUDIT_APPLIED.md 3.3a). Gia tri hash noi dung bins: xem BinsProvenance/DumpConfig.
    // KHONG dat default: thieu = fail cung o WfoDataset.export.
    public static final String WFO_FUNDING_PRED_DIR = Cfg.getOr("WFO_FUNDING_PRED_DIR", "");


    // =========================================================
    // 8. NGƯỠNG BÁO ĐỘNG & DCA NHỒI LỆNH (MARKET STATUS - HPO UPDATE)
    // =========================================================
    public static float PREDICT_SYMBOL_RATE_MAX_THRESHOLD = 0.15f;    // HPO (đã revert về cũ): 0.19727f (Log map: PREDICT_MAX_THRES)

    // RANK-BASED TOP-K (2026-07-28, Probe A go/no-go): thay leg selector tu ABSOLUTE threshold
    //  (nPass = so coin co score <= maxThres) sang RANK top-K per timestamp. Khi SELECTOR_RANK_TOPK=k (k>0)
    //  -> BO QUA maxThres/nPass, chon K coin score THAP nhat (symbol2Pred da sort tang -> lay k phan tu dau).
    //  Muc dich: tu-chuan-hoa theo regime (khong starve luc yeu, khong flood luc manh) thay vi absolute cutoff.
    //  Doc lap SELECTOR_TOPN (cai do van bi cap boi nPass). Default -1 = OFF = giu absolute = byte-identical.
    public static final int SELECTOR_RANK_TOPK = Cfg.get("SELECTOR_RANK_TOPK") != null
            ? Integer.parseInt(Cfg.get("SELECTOR_RANK_TOPK").trim()) : -1;
    // SELECTOR-ONLY ENTRY (2026-07-23): SELECTOR_ONLY_ENTRY=1 -> TAT leg entry theo market-signal
    // (levelChange getTopSymbolArray Best-N = luong FOMO), CHI giu luong selector PREDICT_SYMBOL_TRADE.
    // Dung de co lap 100% edge inverted-selector (khop proxy Kaggle). Default false = byte-identical.
    public static final boolean SELECTOR_ONLY_ENTRY = "1".equals(Cfg.get("SELECTOR_ONLY_ENTRY"));
    // COUNT-ONLY: đếm gate admission rồi short-circuit trước khi tạo order (đo tần suất qua gate).
    // Default false = byte-identical. Bật bằng env SIM_GATE_COUNT_ONLY=1.
    public static final boolean GATE_COUNT_ONLY = "1".equals(Cfg.get("SIM_GATE_COUNT_ONLY"));
    // ENTRY-UNIVERSE DUMP (E0, 2026-07-30): khi CHAY CUNG GATE_COUNT_ONLY, ghi lai TUNG admission
    //  (ts, symbolId, score, price, levelChange) vao list RAM thay vi chi tang counter. Muc dich: dung
    //  dung duong admission THAT (gate ∩ rank-K) de dem so VI THE DOC LAP sau dedup, phuc vu nghien cuu
    //  exit tren tap entry dong bang (docs/reports/EXIT_MACHINE_20260730_stop_schedule.md, buoc E0).
    //  Vi GATE_COUNT_ONLY khong bao gio tao order -> isSymbolRunning luon false -> tu dong BO filter von,
    //  dung y muon C1. Default false = OFF = khong ton RAM, byte-identical.
    public static final boolean ENTRY_UNIVERSE_DUMP = "1".equals(Cfg.get("SIM_ENTRY_UNIVERSE_DUMP"));
    // [TICKLOG 2026-09-03] LOG QUYET DINH TUNG TICK CHO TUNG RUN (docs/PREREG_TICKLOG.md).
    //  Ly do: khong ton tai log quyet dinh theo tick cho tung run => ghep cap theo tick chi lam
    //  duoc cho gene selector/gate (docs/PREREG_GS.md muc 12.2). Doc qua cong Cfg, khai trong
    //  profile. Mac dinh khong khai bao => OFF => moi diem chen la if(false) => byte-identical.
    public static final boolean TICKLOG = "1".equals(Cfg.get("SIM_TICKLOG"));
    public static final boolean TICKLOG_POOL = "1".equals(Cfg.getOr("SIM_TICKLOG_POOL", "0"));
    public static final String TICKLOG_DIR = Cfg.getOr("SIM_TICKLOG_DIR", "/home/ubuntu/tick");
    public static final String TICKLOG_TAG = Cfg.getOr("SIM_TICKLOG_TAG", "run");
    public static final int TICKLOG_POS_EVERY_MIN =
            Integer.parseInt(Cfg.getOr("SIM_TICKLOG_POS_EVERY_MIN", "1").trim());
    public static String SIM_REGIME_FILE = null;   // [REGIME] docs/PREREG_REGIME_GATE.md
    public static String SIM_REGIME_FORCE = null;  // [REGIME] UP|NOTUP: ep hang so cho cong 2-cuc
    public static String SIM_FILTER_D3D4 = null;   // [D3D4-FILTER] docs/PREREG_D3D4_FILTER_SIM.md — off|d3|d4|both, default off
    public static float MIN_MOMENTUM_15M = 0.02284f;                  // HPO (đã revert về cũ): 0.01720f
    public static float MS_UP_BIG_THRES = 0.02046f;                  // HPO (đã revert về cũ): 0.01757f
    public static float MS_DOWN_BIG_AVG = -0.03157f;                  // HPO (đã revert về cũ): -0.05514f
    // [BD-THRESHOLD-FRAGILITY 2026-09-17] tach nguong DCA khoi nguong BIG_DOWN (docs/PREREG_BD_THRESHOLD_FRAGILITY.md).
    //   MS_DOWN_BIG_AVG chi con dieu khien getMarketStatus1M (BIG_DOWN); duong isDcaAlt doc field nay.
    //   Default = gia tri cu => parity byte-identical. Override qua SIM_MS_DOWN_BIG_AVG_DCA.
    public static float MS_DOWN_BIG_AVG_DCA = -0.03157f;

    public static float MS_UP_SMALL_THRES = 0.00442f;
    public static float MS_DOWN_SMALL_AVG_OR_15M = -0.02069f;         // HPO (đã revert về cũ): -0.02007f

    public static int DCA_TIME_BIG_DOWN = 8;                          // HPO (đã revert về cũ): 13
    public static float DCA_LOSS_BIG_DOWN = -0.15f;                   // HPO (đã revert về cũ): -0.26618f
    // [2026-09-02] LOSER TIME-STOP (env SIM_LOSER_TIME_STOP_HOURS, 0=tat): cum CHUA arm trailing (priceSL==null) qua N gio
    //   ke tu leg DAU thi dong tai min(open, close). Khac TIME_STOP_HOURS (nam TRONG updateStatusNew, chi duoc goi khi
    //   maxPrice >= entry*(1+RATE_PROFIT_STOP_MARKET) => KHONG BAO GIO cham cum thua lo thuan — dead cho zombie).
    //   Dat TRUOC cong profit-arm nhu HARD_SL_PCT. Default 0 = byte-identical.
    public static int LOSER_TIME_STOP_HOURS = 0;
    // [2026-09-04 F2] CONDITIONAL EXIT (SIM_COND_EXIT_HOURS=0 -> tat; SIM_COND_EXIT_MIN_FAV): cum CHUA arm
    //   (priceSL==null) da giu qua N gio ke tu leg DAU MA dinh THAT dat duoc tinh tu entry < MIN_FAV thi dong
    //   tai min(open, close). Khac LOSER_TIME_STOP_HOURS (cat PHANG theo gio): day cat CO DIEU KIEN nen giu lai
    //   nhung lenh dang chay. Default 0 => nhanh khong chay => byte-identical. Xem docs/PREREG_F2.md.
    public static int COND_EXIT_HOURS = 0;
    public static float COND_EXIT_MIN_FAV = 0f;
    // [2026-09-05 X2] PRE-ARM HARD SL (SIM_PRE_ARM_SL, 0 = TAT = mac dinh): cum CHUA arm trailing
    //   (priceSL==null) ma gia cham nguong lo do tren firstEntryPrice (BAT BIEN qua DCA) thi dong NGAY
    //   tai min(stopLevel, min(open, close)). Gia tri AM (vd -0.20 = cat o -20%).
    //   Dat TRUOC cong profit-arm VA truoc LOSER_TIME_STOP/COND_EXIT. Key cu SIM_HARD_SL_PCT da chet
    //   o HEAD; day la ban viet lai. Default 0 => nhanh khong chay => byte-identical.
    //   Logic thuan o PreArmSlUtils (co unit test). Xem docs/PREREG_X2.md muc 2.2.
    public static float PRE_ARM_SL = 0f;
    /** [2026-09-03] ban MUTABLE de test do nhay; doc qua tsPnoPumpWeakThr(). */
    public static Float TS_PNOPUMP_WEAK_THR_OVR = null;
    public static float tsPnoPumpWeakThr() {
        return TS_PNOPUMP_WEAK_THR_OVR != null ? TS_PNOPUMP_WEAK_THR_OVR : TS_PNOPUMP_WEAK_THR;
    }
    public static final float TS_PNOPUMP_WEAK_THR = Cfg.get("TS_PNOPUMP_WEAK_THR") != null
            ? Float.parseFloat(Cfg.get("TS_PNOPUMP_WEAK_THR").trim()) : 0.29f;
    // [2026-09-06 X3] TRAILING CAP THEO RANK SELECTOR (TS_CAP_STRONG_RANK, 0 = TAT = mac dinh).
    //   HIEN TRANG truoc X3: trailRate() chon cap theo GIA TRI symbolPred so voi ban le TUYET DOI
    //   TS_PNOPUMP_WEAK_THR = 0.29. Ban le do nam NGOAI tick => tick "nong" ca K coin deu STRONG,
    //   tick "lanh" ca K coin deu WEAK (do thuc tren C3: 71.5% lenh di nhanh STRONG). Do KHONG phai
    //   "trailing theo selector" ma la "trailing theo thang do G015x26 da bi build_map gan lai".
    //   Khi TS_CAP_STRONG_RANK = N > 0: cap STRONG (TS_MAX_GAP) khi selRank <= N, cap WEAK
    //   (TS_MAX_GAP_WEAK) khi sau hon; ban le 0.29 BI BO QUA hoan toan.
    //   selRank == null (leg DCA_LEVEL1 / BIG_DOWN, khong di qua selector) -> WEAK, dung quy uoc
    //   bao thu giong nhanh pNoPump == null.
    //   Default 0 => trailRate di NGUYEN duong cu => byte-identical. Xem docs/PREREG_X3.md.
    //   KHONG final: unit test lat truc tiep.
    public static int TS_CAP_STRONG_RANK = Cfg.get("TS_CAP_STRONG_RANK") != null
            ? Integer.parseInt(Cfg.get("TS_CAP_STRONG_RANK").trim()) : 0;
    // [SL-ADAPTIVE 2026-09-12] 3 lever SL tuy bien theo selRank (STRONG = rank<=N, WEAK = rank>N hoac null).
    //   Default TAT (SIM_SL_ADAPT_* khong khai bao trong profile) => nhanh OFF chay nguyen code cu =>
    //   byte-identical. Chi doc selRank co san tren orderMulti (khong plumbing). Xem docs/PREREG_SL_ADAPTIVE_SWEEP.md.
    public static int SL_ADAPT_RANK_N = Cfg.get("SIM_SL_ADAPT_RANK_N") != null
            ? Integer.parseInt(Cfg.get("SIM_SL_ADAPT_RANK_N").trim()) : 4;
    // B — LOSER TIME-STOP theo rank (cum CHUA arm). STRONG giu 168h, WEAK cat 72h.
    public static boolean SL_ADAPT_TSTOP = "1".equals(Cfg.get("SIM_SL_ADAPT_TSTOP"))
            || "true".equalsIgnoreCase(Cfg.getOr("SIM_SL_ADAPT_TSTOP", ""));
    public static int SL_ADAPT_TSTOP_STRONG_H = Cfg.get("SIM_SL_ADAPT_TSTOP_STRONG_H") != null
            ? Integer.parseInt(Cfg.get("SIM_SL_ADAPT_TSTOP_STRONG_H").trim()) : 168;
    public static int SL_ADAPT_TSTOP_WEAK_H = Cfg.get("SIM_SL_ADAPT_TSTOP_WEAK_H") != null
            ? Integer.parseInt(Cfg.get("SIM_SL_ADAPT_TSTOP_WEAK_H").trim()) : 72;
    // A — PRE-ARM HARD SL theo rank. STRONG=0 (giu/off), WEAK=-0.08 (cap -8%).
    public static boolean SL_ADAPT_HARDSL = "1".equals(Cfg.get("SIM_SL_ADAPT_HARDSL"))
            || "true".equalsIgnoreCase(Cfg.getOr("SIM_SL_ADAPT_HARDSL", ""));
    public static float SL_ADAPT_HARDSL_STRONG = Cfg.get("SIM_SL_ADAPT_HARDSL_STRONG") != null
            ? Float.parseFloat(Cfg.get("SIM_SL_ADAPT_HARDSL_STRONG").trim()) : 0f;
    public static float SL_ADAPT_HARDSL_WEAK = Cfg.get("SIM_SL_ADAPT_HARDSL_WEAK") != null
            ? Float.parseFloat(Cfg.get("SIM_SL_ADAPT_HARDSL_WEAK").trim()) : -0.08f;
    // C — arm rate theo rank. STRONG=0.03, WEAK=0.05.
    public static boolean SL_ADAPT_ARM = "1".equals(Cfg.get("SIM_SL_ADAPT_ARM"))
            || "true".equalsIgnoreCase(Cfg.getOr("SIM_SL_ADAPT_ARM", ""));
    public static float SL_ADAPT_ARM_STRONG = Cfg.get("SIM_SL_ADAPT_ARM_STRONG") != null
            ? Float.parseFloat(Cfg.get("SIM_SL_ADAPT_ARM_STRONG").trim()) : 0.03f;
    public static float SL_ADAPT_ARM_WEAK = Cfg.get("SIM_SL_ADAPT_ARM_WEAK") != null
            ? Float.parseFloat(Cfg.get("SIM_SL_ADAPT_ARM_WEAK").trim()) : 0.05f;
    // [ABLATION 2026-09-02] env TIER_FLAT=1: bo he so budget theo tier (1.2/1.0/0.5 -> 1.0). Default off = byte-identical.
    public static final boolean TIER_FLAT = "1".equals(Cfg.get("TIER_FLAT"));

    // ========================================================================
    // [2026-09-05 C3] BA CO SUA BUG B1/B2/B3 — xem docs/PREREG_C3.md, docs/C3_BASELINE.md.
    //   MAC DINH true = DA SUA. Dat "false" trong profile => tai lap hanh vi CU byte-identical
    //   (cong hoi quy C2b: b:60390 aerospike / b:60395 file, md5 8f7afdfb... / 910f1aa6...).
    //   B1: mergeOrder() chep symbolPred sang object cum => trailRate() dung dung nhanh STRONG/WEAK.
    //   B2: tong trong so DCA chi chia MOT LAN (bo lan chia thu hai o DcaUtils.gridLegWeightRatio).
    //   B3: sizing lay EQUITY hien tai (balanceCurrent + unProfit) thay hang so capitalStart().
    //   KHONG final: unit test lat co truc tiep.
    // ========================================================================
    public static boolean FIX_B1 = !"false".equalsIgnoreCase(Cfg.getOr("SIM_FIX_B1", "true"));
    public static boolean FIX_B2 = !"false".equalsIgnoreCase(Cfg.getOr("SIM_FIX_B2", "true"));
    public static boolean FIX_B3 = !"false".equalsIgnoreCase(Cfg.getOr("SIM_FIX_B3", "true"));

    // ========================================================================
    // [DCA-SIGNAL 2026-09-14] docs/PREREG_DCA_SIGNAL_GATE.md — chia doi suat von/lenh (base 50%)
    //   + leg-2 chi ban khi symbol DOC LAP pass dung pipeline admit lenh moi (top-K + EntryGate)
    //   VA dang lo X% tren firstEntryPrice. DOC LAP voi grid DCA cu (-50/-75/-90%).
    //   DCA_SIGNAL_GATE=false (mac dinh) => KHONG nhanh nao doc 3 key con lai, khong doi sizing,
    //   khong doi phep dem bac grid => printDone.csv byte-identical.
    //   KHONG final: unit test lat co truc tiep.
    // ========================================================================
    public static boolean DCA_SIGNAL_GATE = "true".equalsIgnoreCase(Cfg.getOr("SIM_DCA_SIGNAL_GATE", "false"))
            || "1".equals(Cfg.getOr("SIM_DCA_SIGNAL_GATE", "false"));
    /** Nguong lo (AM) do tren firstEntryPrice de duoc phep ban leg-2 DCA-signal. */
    public static float DCA_SIGNAL_LOSS = Cfg.get("SIM_DCA_SIGNAL_LOSS") != null
            ? Float.parseFloat(Cfg.get("SIM_DCA_SIGNAL_LOSS").trim()) : -0.08f;
    /** Ti le suat von co so cho leg MO CUM va cho leg-2 DCA-signal (0.5 = chia doi). */
    public static float DCA_SIGNAL_BASE_RATIO = Cfg.get("SIM_DCA_SIGNAL_BASE_RATIO") != null
            ? Float.parseFloat(Cfg.get("SIM_DCA_SIGNAL_BASE_RATIO").trim()) : 0.5f;
    /** Cooldown (phut) ke tu leg DAU cua cum truoc khi leg-2 duoc phep ban. */
    public static int DCA_SIGNAL_COOLDOWN_MIN = Cfg.get("SIM_DCA_SIGNAL_COOLDOWN_MIN") != null
            ? Integer.parseInt(Cfg.get("SIM_DCA_SIGNAL_COOLDOWN_MIN").trim()) : 60;

    // ========================================================================
    // [CONC-CAP 2026-09-15] docs/PREREG_CONCENTRATION_SAFETYCAP.md — SAFETY-NET, KHONG phai lever.
    //   Guard 1: tran AGGREGATE margin nam trong cac leg DCA-grid bac>=1, cong dong TOAN BO coin.
    //   Guard 2: tran so leg BIG_DOWN mo trong 60 phut (rolling window, theo thoi gian SIM).
    //   Hai nguong dat CO CHU DICH CAO HON dinh lich su da do tren 4.5 nam
    //   (docs/DIAG_DCA_CONCURRENCY.md: aggregate max 0.4120 equity; BIG_DOWN max 54 leg/gio)
    //   => KHONG binding tren vung da quan sat; chi bat trong kich ban TE HON moi thu da thay.
    //   Mac dinh CA HAI TAT => khong nhanh nao doc nguong, khong cap phat cau truc nao
    //   => printDone.csv byte-identical voi baseline.
    //   KHONG duoc dua 2 nguong nay vao HPO/WFO/grid-search: day la BIEN AN TOAN, khong phai gene.
    //   KHONG final: unit test lat co truc tiep.
    // ========================================================================
    public static boolean CONC_CAP_AGG_DCA_ENABLED =
            "true".equalsIgnoreCase(Cfg.getOr("CONC_CAP_AGG_DCA_ENABLED", "false"))
            || "1".equals(Cfg.getOr("CONC_CAP_AGG_DCA_ENABLED", "false"));
    /** Tran (ti le tren equity) cua TONG margin dang nam trong cac leg DCA-grid bac>=1 toan so. */
    public static float CONC_CAP_AGG_DCA_PCT = Cfg.get("CONC_CAP_AGG_DCA_PCT") != null
            ? Float.parseFloat(Cfg.get("CONC_CAP_AGG_DCA_PCT").trim()) : 0.45f;
    public static boolean CONC_CAP_BD_RATE_ENABLED =
            "true".equalsIgnoreCase(Cfg.getOr("CONC_CAP_BD_RATE_ENABLED", "false"))
            || "1".equals(Cfg.getOr("CONC_CAP_BD_RATE_ENABLED", "false"));
    /** Tran so leg BIG_DOWN duoc mo trong 60 phut gan nhat. */
    public static int CONC_CAP_BD_PER_HOUR = Cfg.get("CONC_CAP_BD_PER_HOUR") != null
            ? Integer.parseInt(Cfg.get("CONC_CAP_BD_PER_HOUR").trim()) : 75;

    // ========================================================================
    // [CONC-PERCOIN 2026-09-17] docs/PREREG_DCA_AGG_PERCOIN.md — tran margin MOT coin
    //   (entry + moi leg DCA). Khac Guard 1 (aggregate): guard nay chan khi MOT coin don le tich
    //   luy margin qua nguong (STOCK concentration), khong phai tong toan so. Mac dinh FALSE
    //   => khong nhanh nao chay => printDone.csv byte-identical.
    //   KHONG final: unit test lat co truc tiep.
    // ========================================================================
    /** Bat/tat tran ti le margin cua MOT coin tren equity (entry + moi leg DCA). */
    public static boolean CONC_CAP_PERCOIN_ENABLED =
            "true".equalsIgnoreCase(Cfg.getOr("CONC_CAP_PERCOIN_ENABLED", "false"))
            || "1".equals(Cfg.getOr("CONC_CAP_PERCOIN_ENABLED", "false"));
    /** Tran (ti le tren equity) cua TONG margin dang nam cua MOT coin khi mo leg moi. */
    public static float CONC_CAP_PERCOIN_PCT = Cfg.get("CONC_CAP_PERCOIN_PCT") != null
            ? Float.parseFloat(Cfg.get("CONC_CAP_PERCOIN_PCT").trim()) : 0.15f;

    // ========================================================================
    // [BD-SIZE-ADAPT 2026-09-16] docs/PREREG_BD_SIZE_ADAPT.md — size leg BIG_DOWN
    //   theo severity causal (rolling N-ngay). KHONG doi trigger BIG_DOWN.
    //   Mac dinh "off" => khong cap phat cau truc, khong nhanh nao chay => byte-identical.
    //   Cac mode: down50 (giam khi sau), down25 (giam nhe), up50 (tang khi sau).
    //   KHONG final: unit test lat co truc tiep.
    // ========================================================================
    /** Che do size-adapt cho leg BIG_DOWN (off|down50|down25|up50). */
    public static String BD_SIZE_ADAPT = Cfg.getOr("BD_SIZE_ADAPT", "off");
    /** Cua so lich (ngay) tinh qmin(D) = min(dayMin[D-N .. D-1]), causal, KHONG gom D. */
    public static int BD_SIZE_ADAPT_N = Cfg.get("BD_SIZE_ADAPT_N") != null
            ? Integer.parseInt(Cfg.get("BD_SIZE_ADAPT_N").trim()) : 120;

    // ========================================================================
    // [VOL_TARGET 2026-09-20] docs/PREREG_VOL_TARGET.md - TASK 5: size lenh theo bien dong
    //   THUC TE (risk parity), KHONG doi lenh nao duoc chon vao/ra - chi doi KICH THUOC. Mac dinh
    //   "OFF" -> VolTargetSizing.ACTIVE=false -> khong nhanh nao chay -> byte-identical voi T170
    //   (cong repro md5 efb793e2). Xem VolTargetSizing.java cho COIN/PORTFOLIO.
    // ========================================================================
    /** Che do vol-target sizing (OFF|COIN|PORTFOLIO). */
    public static String SIZE_VOL_TARGET_MODE = Cfg.getOr("SIZE_VOL_TARGET_MODE", "OFF");

    // ========================================================================
    // [PACING 2026-09-21] docs/PREREG_PACING_BIGDOWN.md - TASK B: giam size khi bigdown
    //   (P3, regime-conditional, causal BD1a) hoac giam size DEU khong dieu kien (P0, doi
    //   chung) tren nen gate 1.0. KHONG doi lenh nao duoc chon vao/ra - chi doi KICH THUOC
    //   (giong VolTargetSizing). Mac dinh "OFF" -> PacingSizing.ACTIVE=false -> khong nhanh
    //   nao chay -> byte-identical voi T170 (cong repro md5 efb793e2). Xem PacingSizing.java.
    // ========================================================================
    /** Che do pacing sizing (OFF|P0|P3). */
    public static String SIZE_PACING_MODE = Cfg.getOr("SIZE_PACING_MODE", "OFF");

    // ========================================================================
    // [BD-SEL 2026-09-16] docs/PREREG_SEL_BIGDOWN.md — doi cach chon 2 coin cua leg
    //   BIG_DOWN theo drop 1-phut causal thay vi pNoPump. KHONG sua getTopSymbolArray.
    //   Mac dinh "off" => khong cap phat, khong nhanh nao chay => byte-identical.
    //   Cac mode: drop (am nhat), mix (tong hang rankP+rankD), drop_top8 (top-K pNoPump
    //   roi chon rot nhat). KHONG final: unit test lat co truc tiep.
    // ========================================================================
    /** Che do chon coin cho leg BIG_DOWN (off|drop|mix|drop_top8). */
    public static String BD_SEL_MODE = Cfg.getOr("BD_SEL_MODE", "off");
    /** Shortlist size pNoPump cho drop_top8 (default 8). */
    public static int BD_SEL_TOPK = Cfg.get("BD_SEL_TOPK") != null
            ? Integer.parseInt(Cfg.get("BD_SEL_TOPK").trim()) : 8;



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

    // 2026-09-03 (B3): goc tinh size lenh (BASE_BUDGET = CAPITAL_START / number_order_budget).
    // Truoc day 2 cho (BudgetManager, BudgetManagerSimple) doc truc tiep properties => khong ai thay o dau.
    // env/profile > properties. LAZY (khong phai field static) de tool nao khong dung von thi khong bat
    // buoc phai co key nay trong config.properties — giu nguyen pham vi anh huong nhu truoc.
    public static float capitalStart() {
        String v = Cfg.get("CAPITAL_START");
        if (v != null && !v.trim().isEmpty()) return Float.parseFloat(v.trim());
        return Float.parseFloat(properties.get("CAPITAL_START").trim());
    }

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
            if ((v = Cfg.get("SIM_MIN_MOMENTUM_15M")) != null) MIN_MOMENTUM_15M = Float.parseFloat(v);
            // [2026-09-12 GATESCALE] do doc gate dyn (docs/PREREG_GATESCALE.md): nhan 1 he so vao
            //   KET QUA dyn_thr da tinh trong EntryGate. Doc 1 lan o day (khong nong). Khong khai /
            //   <=0 => giu 1.0f => x*1.0f IEEE-exact => byte-identical.
            if ((v = Cfg.get("SIM_GATE_DYN_SCALE")) != null) {
                float gs = Float.parseFloat(v.trim());
                if (gs > 0f) EntryGate.GATE_DYN_SCALE = gs;
            }
            // [REGIME 2026-09-14] docs/PREREG_REGIME_GATE.md: gate scale doi theo regime BTC 30d.
            //   default OFF => byte-identical. SIM_REGIME_FORCE=UP|NOTUP chi cho cong 2-cuc.
            if ((v = Cfg.get("SIM_GATE_REGIME_ADAPTIVE")) != null) {
                String t = v.trim();
                EntryGate.GATE_REGIME_ADAPTIVE = t.equals("1") || t.equalsIgnoreCase("true");
            }
            if ((v = Cfg.get("SIM_REGIME_FILE")) != null) SIM_REGIME_FILE = v.trim();
            if ((v = Cfg.get("SIM_REGIME_FORCE")) != null) SIM_REGIME_FORCE = v.trim();
            // [D3D4-FILTER 2026-09-17] docs/PREREG_D3D4_FILTER_SIM.md: filter pump-dump cho lenh moi
            //   (selector + BIG_DOWN). default off => byte-identical. configure() throw neu gia tri sai.
            if ((v = Cfg.get("SIM_FILTER_D3D4")) != null) {
                SIM_FILTER_D3D4 = v.trim();
                PumpDumpFilter.configure(SIM_FILTER_D3D4);
            }
            // [L7 2026-09-11] SIM_AI_DYNAMIC_MIN / SIM_AI_DYNAMIC_MULTIPLIER da XOA: hai he so do
            //   nay la HANG SO trong com.binance.chuyennd.tradecore.EntryGate (gate chi con MOT knob
            //   la SIM_MIN_MOMENTUM_15M). Khong profile/env nao tung khai hai key do
            //   (docs/LEAN_GATE_AUDIT.md muc 2.3) nen xoa la byte-identical.
            //   MAX = TRAN UNG VIEN tang 1 (rate_max * MAX) — VAN SONG, giu override.
            if ((v = Cfg.get("SIM_AI_DYNAMIC_MAX")) != null) AI_DYNAMIC_MAX = Float.parseFloat(v.trim());
            if ((v = Cfg.get("SIM_TS_PNOPUMP_WEAK_THR")) != null) TS_PNOPUMP_WEAK_THR_OVR = Float.parseFloat(v.trim());
            // [2026-09-03 GS] gap trailing: TRUOC DAY hardcode-only (0.08 / 0.03) => profile khong dieu khien duoc.
            //   Mo override de tim kiem toan cuc. Default (khong khai bao) = gia tri cu => byte-identical.
            if ((v = Cfg.get("SIM_TS_MAX_GAP")) != null) TS_MAX_GAP = Float.parseFloat(v.trim());
            if ((v = Cfg.get("SIM_TS_MAX_GAP_WEAK")) != null) TS_MAX_GAP_WEAK = Float.parseFloat(v.trim());
            if ((v = Cfg.get("SIM_F_BASE")) != null) F_BASE = Float.parseFloat(v.trim());
            if ((v = Cfg.get("SIM_U_MAX")) != null) U_MAX = Float.parseFloat(v.trim());
            if ((v = Cfg.get("SIM_PREDICT_SYMBOL_RATE_MAX")) != null) PREDICT_SYMBOL_RATE_MAX_THRESHOLD = Float.parseFloat(v);
            if ((v = Cfg.get("SIM_RATE_PROFIT_STOP_MARKET")) != null) RATE_PROFIT_STOP_MARKET = Float.parseFloat(v);
            if ((v = Cfg.get("SIM_MS_DOWN_BIG_AVG")) != null) MS_DOWN_BIG_AVG = Float.parseFloat(v);
            // [BD-THRESHOLD-FRAGILITY] nguong rieng cho duong DCA (isDcaAlt); default = gia tri cu.
            if ((v = Cfg.get("SIM_MS_DOWN_BIG_AVG_DCA")) != null) MS_DOWN_BIG_AVG_DCA = Float.parseFloat(v);
            if ((v = Cfg.get("SIM_LOSER_TIME_STOP_HOURS")) != null) LOSER_TIME_STOP_HOURS = Integer.parseInt(v.trim());
            if ((v = Cfg.get("SIM_COND_EXIT_HOURS")) != null) COND_EXIT_HOURS = Integer.parseInt(v.trim());
            if ((v = Cfg.get("SIM_COND_EXIT_MIN_FAV")) != null) COND_EXIT_MIN_FAV = Float.parseFloat(v.trim());
            if ((v = Cfg.get("SIM_PRE_ARM_SL")) != null) PRE_ARM_SL = Float.parseFloat(v.trim());
            // TASK (frozen leakage-free genome, Buoc 0): funding.bin trong WFO_DATA_DIR/-ff CHI tu-ap cho
            //   funding-SELECTOR (ds.funding), KHONG tu-ap thanh FEE. Fee van gate boi APPLY_FUNDING_FEE
            //   (default false). SIM_APPLY_FUNDING=true -> bat funding fee cho vong WFO/HPO nay (funding-on).
            //   Default (env rong) -> giu false = byte-identical.
            if ((v = Cfg.get("SIM_APPLY_FUNDING")) != null) APPLY_FUNDING_FEE = Boolean.parseBoolean(v);
            if ((v = Cfg.get("SIM_FUNDING_MARK")) != null) FUNDING_MARK_NOTIONAL = Boolean.parseBoolean(v);
            // [2026-09-02 STRESS] chi phi: fee/slippage/funding scale cho bai robustness. Default = gia tri cu -> byte-identical.
            if ((v = Cfg.get("SIM_RATE_FEE")) != null) RATE_FEE = Float.parseFloat(v.trim());
            if ((v = Cfg.get("SIM_SLIPPAGE_RATE")) != null) SLIPPAGE_RATE = Float.parseFloat(v.trim());
            if ((v = Cfg.get("SIM_FUNDING_SCALE")) != null) FUNDING_SCALE = Float.parseFloat(v.trim());
        } catch (Exception e) {
            System.err.println("SIM env override parse error: " + e);
        }
    }

    /**
     * 2026-09-03 (B3): danh sach TAT CA key ma code THUC SU doc tu config.properties.
     * Key nao co trong file ma khong co trong day = dead/decoy: doc gia tri trong file la SAI SU THAT
     * (vd RATE_FEE=0.001 trong file nhung code dung 0.002; RATE_PROFIT_STOP_MARKET=0.1 vs code 0.03).
     */
    private static final java.util.List<String> KNOWN_PROPS = java.util.Arrays.asList(
            "AEROSPIKE_HOST", "AEROSPIKE_HOST_226", "AEROSPIKE_NAMESPACE", "AEROSPIKE_NAMESPACE_242",
            "AEROSPIKE_PORT", "AEROSPIKE_PORT_226", "AEROSPIKE_READ_CLUSTER", "CAPITAL_START",
            "DIED_SYMBOLS", "FILE_AI_PREDICTIONS",
            "NUMBER_ORDER_BUDGET", "NUMBER_THREAD_ORDER_MANAGER", "SPECIAL_SYMBOLS", "TICKER_SOURCE",
            "TIME_RUN", "TS_GIVEBACK_RATIO", "USE_SMART_CACHE",
            "WFO_STATIC_RANK", "WRITE_SIM_STORAGE");

    static {
        java.util.List<String> unknown = new java.util.ArrayList<>();
        for (String k : properties.keySet()) if (!KNOWN_PROPS.contains(k)) unknown.add(k);
        java.util.Collections.sort(unknown);
        if (!unknown.isEmpty()) {
            System.err.println("[CFG] CANH BAO: config.properties co " + unknown.size()
                    + " key KHONG AI DOC (gia tri trong file la SAI SU THAT): " + unknown);
            if ("1".equals(Cfg.get("CONFIG_STRICT"))) {
                System.err.println("[CFG] CONFIG_STRICT=1 -> DUNG. Xoa cac key tren khoi config.properties.");
                System.exit(2);
            }
        }
    }

    /**
     * 2026-09-03 (CLEAN): hai co duoi day DA BI GO khoi engine — chi con MOT duong duy nhat.
     * Key van PHAI khai bao trong profile (SIM_TS_GIVEBACK=1, SIM_BREAKER_MODE=OFF): (a) Cfg.auditProfile()
     * khong bao "key khong ai doc", (b) nguoi doc profile thay ro trailing chay che do nao va breaker tat.
     * Dat gia tri KHAC => DUNG NGAY, khong am tham chay duong da bi xoa.
     * env rong (tool WFO/HPO khong dat) => bo qua, giu tuong thich nguoc.
     */
    static {
        String gb = Cfg.get("SIM_TS_GIVEBACK");
        if (gb != null && !"1".equals(gb.trim())) {
            System.err.println("[CFG] DUNG: SIM_TS_GIVEBACK=" + gb + " nhung duong trailing cu"
                    + " (calRateLossDynamicBuy) DA BI XOA 2026-09-03. Chi ho tro SIM_TS_GIVEBACK=1.");
            System.exit(2);
        }
        String bm = Cfg.get("SIM_BREAKER_MODE");
        if (bm != null && !"OFF".equals(bm.trim())) {
            System.err.println("[CFG] DUNG: SIM_BREAKER_MODE=" + bm + " nhung co che circuit-breaker"
                    + " DA BI XOA 2026-09-03. Chi ho tro SIM_BREAKER_MODE=OFF.");
            System.exit(2);
        }
    }

    public static void main(String[] args) {
        // Test configurations here
    }
}
