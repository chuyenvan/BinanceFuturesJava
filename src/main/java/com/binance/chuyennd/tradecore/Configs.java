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
    public static float MIN_MOMENTUM_15M = 0.02284f;                  // HPO (đã revert về cũ): 0.01720f
    public static float MS_UP_BIG_THRES = 0.02046f;                  // HPO (đã revert về cũ): 0.01757f
    public static float MS_DOWN_BIG_AVG = -0.03157f;                  // HPO (đã revert về cũ): -0.05514f

    public static float MS_UP_SMALL_THRES = 0.00442f;
    public static float MS_DOWN_SMALL_AVG_OR_15M = -0.02069f;         // HPO (đã revert về cũ): -0.02007f

    public static int DCA_TIME_BIG_DOWN = 8;                          // HPO (đã revert về cũ): 13
    public static float DCA_LOSS_BIG_DOWN = -0.15f;                   // HPO (đã revert về cũ): -0.26618f
    // [2026-09-02] LOSER TIME-STOP (env SIM_LOSER_TIME_STOP_HOURS, 0=tat): cum CHUA arm trailing (priceSL==null) qua N gio
    //   ke tu leg DAU thi dong tai min(open, close). Khac TIME_STOP_HOURS (nam TRONG updateStatusNew, chi duoc goi khi
    //   maxPrice >= entry*(1+RATE_PROFIT_STOP_MARKET) => KHONG BAO GIO cham cum thua lo thuan — dead cho zombie).
    //   Dat TRUOC cong profit-arm nhu HARD_SL_PCT. Default 0 = byte-identical.
    public static int LOSER_TIME_STOP_HOURS = 0;
    /** [2026-09-03] ban MUTABLE de test do nhay; doc qua tsPnoPumpWeakThr(). */
    public static Float TS_PNOPUMP_WEAK_THR_OVR = null;
    public static float tsPnoPumpWeakThr() {
        return TS_PNOPUMP_WEAK_THR_OVR != null ? TS_PNOPUMP_WEAK_THR_OVR : TS_PNOPUMP_WEAK_THR;
    }
    public static final float TS_PNOPUMP_WEAK_THR = Cfg.get("TS_PNOPUMP_WEAK_THR") != null
            ? Float.parseFloat(Cfg.get("TS_PNOPUMP_WEAK_THR").trim()) : 0.29f;
    // [ABLATION 2026-09-02] env TIER_FLAT=1: bo he so budget theo tier (1.2/1.0/0.5 -> 1.0). Default off = byte-identical.
    public static final boolean TIER_FLAT = "1".equals(Cfg.get("TIER_FLAT"));


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
            if ((v = Cfg.get("SIM_AI_DYNAMIC_MIN")) != null) AI_DYNAMIC_MIN = Float.parseFloat(v);
            // [2026-09-03] mo override cho cac hang so HPO CON SONG, de test do nhay (lam tron).
            //   MULTIPLIER = do doc duong nguong gate; MAX = TRAN UNG VIEN (rate_max * MAX);
            //   PNOPUMP_WEAK_THR = ranh gioi strong/weak cua gap trailing; F_BASE/U_MAX = throttle von.
            // Default (env rong) = gia tri cu => byte-identical.
            if ((v = Cfg.get("SIM_AI_DYNAMIC_MULTIPLIER")) != null) AI_DYNAMIC_MULTIPLIER = Float.parseFloat(v.trim());
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
            if ((v = Cfg.get("SIM_LOSER_TIME_STOP_HOURS")) != null) LOSER_TIME_STOP_HOURS = Integer.parseInt(v.trim());
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
