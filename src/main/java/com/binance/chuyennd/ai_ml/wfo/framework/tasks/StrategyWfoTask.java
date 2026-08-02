package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV4;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoContext;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoJob;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoTask;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.util.*;

/**
 * WFO TASK loại 1 — STRATEGY WFO (tối ưu 17 gene chiến lược, off-cứng 9 gene phẳng đã loại + bỏ DCA_TIME_BIG_Up chết).
 *
 * <p>Mỗi JOB = 1 cửa sổ: train 12 tháng + OOS 3 tháng (trượt = OOS, không chồng lấn). runJob:
 * random-search N mẫu genome trên TRAIN → best theo fitness V4.1 → đo OOS → WFE. result JSON gồm
 * {winIdx, label, isFit, oosFit, wfe, oosPnl, oosMaxDD, oosCalmar, oosNote, isNote, bestGenome}.
 * V4.1 (TASK-113): oosPnl/oosDdPct/oosCalmar là số THẬT kể cả nhánh sentinel (TOO_FEW/BURN/...);
 * %OOS-dương đếm tường minh theo oosNote=SUCCESS (semantics đếm giữ nguyên V4).
 *
 * <p>Dữ liệu lấy từ {@link WfoContext#dataset} (offline, load 1 lần/JVM) — KHÔNG scanAll Aerospike.
 *
 * <p>aggregate: gom mọi cửa sổ → %cửa-sổ-OOS-dương, WFE trung vị, maxDD OOS xấu nhất, ổn định gene →
 * VERDICT theo ngưỡng pre-registered (chốt TRƯỚC khi nhìn): WFE_median ≥ {@value #PASS_WFE},
 * %dương ≥ {@value #PASS_POS_RATIO}, maxDD OOS xấu nhất ≤ {@value #PASS_MAXDD_OOS}.
 */
public class StrategyWfoTask implements WfoTask {

    private static final Logger LOG = LoggerFactory.getLogger(StrategyWfoTask.class);
    public static final String TYPE = "strategy_window";

    // count-only frequency probe: counters cua sim OOS gan nhat (chi dung khi Configs.GATE_COUNT_ONLY)
    private long lastGateSeen = 0, lastGatePass = 0;

    // ===== cấu hình cửa sổ (khớp WFORunner) =====
    private static final String DATA_START = "20210101";
    private static final String DATA_END = "20260601";
    private static final int TRAIN_MONTHS = envInt("WFO_TRAIN_MONTHS", 12);
    private static final int OOS_MONTHS = envInt("WFO_OOS_MONTHS", 3);
    private static final int DEFAULT_N_SAMPLES = 30;
    private static final long SEED_BASE = envLong("WFO_SEED_BASE", 42L);  // TASK-133: env-configurable de do selection noise (multi-seed)

    // ===== ngưỡng VERDICT pre-registered (chốt TRƯỚC khi chạy — WFO_OBJECTIVE_RESEARCH.md) =====
    public static final float PASS_WFE = 0.5f;        // WFE = PnL_OOS/PnL_IS; ≥0.5 tốt, <0.3 overfit
    public static final float PASS_POS_RATIO = 0.70f; // ≥70% cửa sổ OOS dương
    public static final float PASS_MAXDD_OOS = 0.50f; // maxDD-OOS xấu nhất theo TỶ LỆ vốn (≤50%, pre-registered). Dùng ddPct, KHÔNG abs USD.

    // ===== GENOME 17 gene (cụm A REJECT + B nhạy vừa). Range vùng AN TOÀN tránh REJECT. =====
    // 2026-07-13 Uni: BỎ DCA_TIME_BIG_Up (18→17) — gene CHẾT dưới OFF_FLAT_HARD: chỉ dùng ở nhánh BIG_UP
    // (DcaUtils:51) mà BIG_UP off-cứng → không tác động sleeve nào đang bật → phí 1 chiều search HPO.
    static final LinkedHashMap<String, double[]> GENOME = new LinkedHashMap<>();
    static final LinkedHashMap<String, Boolean> IS_INT = new LinkedHashMap<>();
    static {
        // 2026-07-27 (gate-DOF regularize confirm): bounds cua MIN_MOMENTUM_15M gio ENV-CONFIGURABLE
        // (WFO_MOM15_LO / WFO_MOM15_HI, default giu nguyen [0.010,0.045] -> backward-compatible).
        // Giả thuyết: HPO thưởng IS-fit -> tu day gate len 0.045 -> giet OOS frequency/robustness (WFE artifact 0.24).
        // Cap ceiling (WFO_MOM15_HI<0.045) va/hoac ha san (WFO_MOM15_LO<0.010) de test apples-to-apples voi baseline.
        double mom15Lo = envDouble("WFO_MOM15_LO", 0.010);
        double mom15Hi = envDouble("WFO_MOM15_HI", 0.045);
        put("MIN_MOMENTUM_15M", mom15Lo, mom15Hi, false);  // 2026-07-12 Uni: NOI xuong 0.010 (cu 0.020) de HPO tu do chon vung tan-suat-cao (team ghi vung tot 0.010-0.020 bi loai) - test tan suat. TASK-137: [0.020,0.045] - range B [0.015,0.045] cho WFE 0.104 (te hon), 0.020 tranh mep vach chay: mo range xuong (cu [0.030,0.050]) - sweep cho thay 0.050 la diem te nhat toan ky (calmar 0.92), vung tot 0.015-0.0228 bi loai ngoai; can duoi 0.020 (khong 0.015) de tranh mep vach chay 0.010-0.015
        put("PREDICT_SYMBOL_RATE_MAX_THRESHOLD", 0.05, 0.20, false);
        put("AI_DYNAMIC_MULTIPLIER", 1.5, 2.0, false);
        put("AI_DYNAMIC_MIN", 0.10, 0.50, false);
        put("HARD_RISK_LIMIT_4H", -0.30, -0.05, false);
        put("MS_DOWN_BIG_AVG", -0.055, -0.020, false);

        // ---- cum DCA: HOAN DOI theo co, KHONG cong don (2026-08-01) ----------------------------
        // DCA_LOSS_BIG_DOWN + DCA_TIME_BIG_DOWN CHI duoc doc trong DcaUtils.getDcaConfig(BIG_DOWN).
        // Khi DCA_GRID_ENABLED=true, DcaProcessor.getDCA re sang shouldDcaGrid() va KHONG BAO GIO goi
        // shouldDca() nua => 2 gene nay thanh GENE CHET (HPO van quay chung, ton chieu search, va te
        // hon: geneStability report ra range 'on dinh' gia). => bo hai gene, thay bang 4 gene mo ta
        // luoi + 1 gene scale. Net +3 chieu (17 -> 20 khi bat grid).
        if (Configs.DCA_GRID_ENABLED && Configs.DCA_GRID_SCALAR) {
            put("DCA_GRID_L1", -0.60, -0.30, false);      // moc nhoi dau, do tren firstEntryPrice
            put("DCA_GRID_STEP", 0.10, 0.30, false);      // do GIAN giua 2 bac
            put("DCA_GRID_LEGS", 2, 5, true);             // so bac nhoi (SurvivalProbe: >5 bac do ra te hon)
            put("DCA_GRID_W_RATIO", 1.0, 3.0, false);     // 1.0 = ti trong phang; >1 = don von ve day
            put("DCA_GRID_SCALE", 4.0, 16.0, false);      // bu phan du tru hiem dung; >16 phai kiem CapacityProbe truoc
        } else {
            put("DCA_LOSS_BIG_DOWN", -0.22, -0.08, false);
            put("DCA_TIME_BIG_DOWN", 3, 7, true);
        }
        // Tran margin theo bac: chi co nghia khi co bat. Do dang mang -> scalar (BASE/STEP) o Configs.
        if (Configs.DCA_TIER_MARGIN_ENABLED && Configs.DCA_GRID_SCALAR) {
            put("DCA_TIER_CAP_BASE", 0.40, 0.60, false);  // 0.50 = dung vach BREAKER_MARGIN_HALT production
            put("DCA_TIER_CAP_STEP", 0.00, 0.15, false);  // 0.00 = tran phang (bao gom ca truong hop cu)
        }

        put("RATE_PROFIT_STOP_MARKET", 0.03, 0.05, false);  // TASK-139: PHAT HIEN LON - cu [0.012,0.025] ep WFO tune trong vung CAT NON. Sweep: 0.03-0.05 cho PnL 2.4x + calmar 2.3x, maxDD khong doi. Day la nut that that (khong phai MIN_MOM15). 2026-07-30: nang san 0.020->0.03 (khop chinh xac vung sweep da xac nhan, khong con test duoi san chi phi 0.016)
        // 2026-08-01 (Uni chot): TS_PROFIT_MULTIPLIER=1.0 CHINH LA TS_RATCHET_DECOUPLED=true
        //   (updateTPSL: rateMin2MoveSl = DECOUPLED ? base : MULT*base). Thay vi 1 co boolean 2 trang
        //   thai ma HPO khong cham duoc, mo SAN range xuong 1.0 => HPO tu do tim diem giua thay vi
        //   phai sweep tay 2 nhanh. San MO chi khi nhanh exit moi bat (TS_GIVEBACK_FLOOR) hoac khi
        //   ep bang env; mac dinh van [4.0,8.0] de baseline cu byte-identical.
        double tsMultLo = envDouble("WFO_TSMULT_LO", Configs.TS_GIVEBACK_FLOOR ? 1.0 : 4.0);
        double tsMultHi = envDouble("WFO_TSMULT_HI", 8.0);
        put("TS_PROFIT_MULTIPLIER", tsMultLo, tsMultHi, false);
        put("TS_DYNAMIC_K", 0.10, 0.25, false);

        // ---- cum EXIT giveback: HOAN DOI, net -1 chieu ----------------------------------------
        // TradeUtils.calRateLossDynamicBuy:
        //   FLOOR=false -> gap = min(peak*RATIO, maxGap)   <- maxGap = TS_MAX_GAP / TS_MAX_GAP_WEAK,
        //                                                     chon boi TS_WEAK_MOMENTUM_THRES
        //   FLOOR=true  -> gap = max(peak*RATIO, TS_MIN_GAP) <- maxGap KHONG duoc dung o dau ca
        // => bat FLOOR thi 3 gene TS_MAX_GAP/TS_MAX_GAP_WEAK/TS_WEAK_MOMENTUM_THRES la NHIEU THUAN.
        // Thay bang 2 gene that su dieu khien hinh dang: san TS_MIN_GAP + ti le nha TS_GIVEBACK_RATIO.
        if (Configs.TS_GIVEBACK_FLOOR) {
            put("TS_MIN_GAP", 0.005, 0.030, false);       // san tuyet doi; <0.008 la duoi chi phi round-trip
            put("TS_GIVEBACK_RATIO", 0.30, 0.70, false);  // 0.3 giu chat / 0.7 nuoi trend
        } else {
            put("TS_MAX_GAP", 0.04, 0.06, false);
            put("TS_MAX_GAP_WEAK", 0.045, 0.060, false);
            put("TS_WEAK_MOMENTUM_THRES", 0.004, 0.008, false);
        }

        put("BUDGET_MARGIN_RATIO_1", 0.30, 0.50, false);
        put("BUDGET_MARGIN_RATIO_2", 0.60, 0.78, false);
        put("BUDGET_DIVIDER_2", 1.60, 2.50, false);
        LOG.info("GENOME: {} gene | dcaGrid={} scalar={} tierMargin={} givebackFloor={} tsMult=[{},{}] | {}",
                GENOME.size(), Configs.DCA_GRID_ENABLED, Configs.DCA_GRID_SCALAR,
                Configs.DCA_TIER_MARGIN_ENABLED, Configs.TS_GIVEBACK_FLOOR, tsMultLo, tsMultHi,
                GENOME.keySet());
    }
    private static void put(String f, double lo, double hi, boolean isInt) {
        GENOME.put(f, new double[]{lo, hi}); IS_INT.put(f, isInt);
    }

    @Override public String type() { return TYPE; }

    // ======================= buildJobs =======================
    @Override
    public List<WfoJob> buildJobs() {
        int nSamples = DEFAULT_N_SAMPLES;
        String envN = System.getenv("WFO_N_SAMPLES");
        if (envN != null && !envN.isEmpty()) nSamples = Integer.parseInt(envN);

        List<long[]> wins = buildWindows();
        // WFO_MAX_WINDOWS: giới hạn số cửa sổ (chỉ để TEST kín luồng nhanh; full không set).
        String envMaxW = System.getenv("WFO_MAX_WINDOWS");
        int maxW = (envMaxW != null && !envMaxW.isEmpty()) ? Integer.parseInt(envMaxW) : wins.size();
        // GIỚI HẠN 3 (2026-07-13): loại OOS window vượt tầm dữ liệu selector (funding tới 2025-12).
        // WFO_MAX_OOS_DATE=yyyyMMdd → KHÔNG tạo window có oosEnd vượt mốc đó (rỗng = giữ nguyên).
        long maxOosMs = parseMaxOosDateMs(System.getenv("WFO_MAX_OOS_DATE"));
        List<WfoJob> jobs = new ArrayList<>();
        for (int i = 0; i < wins.size() && i < maxW; i++) {
            long[] w = wins.get(i);
            long oosEndReal = w[3] + Utils.TIME_MINUTE;   // w[3] = oosEnd - 1 phut; khoi phuc mep phai thuc
            if (oosEndReal > maxOosMs) {
                LOG.info("buildJobs: LOAI window w{} (OOS {}..{}) vi oosEnd vuot WFO_MAX_OOS_DATE",
                        i, Utils.normalizeDateYYYYMMDD(w[2]), Utils.normalizeDateYYYYMMDD(oosEndReal));
                continue;
            }
            JSONObject p = new JSONObject();
            p.put("winIdx", i);
            p.put("trainStart", w[0]); p.put("trainEnd", w[1]);
            p.put("oosStart", w[2]); p.put("oosEnd", w[3]);
            p.put("nSamples", nSamples);
            p.put("seed", SEED_BASE + i);
            String id = String.format("strat-w%02d", i);
            jobs.add(new WfoJob(id, TYPE, p.toString()));
        }
        LOG.info("buildJobs: {} cua so (train {}m, OOS {}m, truot {}m), N={}",
                jobs.size(), TRAIN_MONTHS, OOS_MONTHS, OOS_MONTHS, nSamples);
        return jobs;
    }

    private static int envInt(String name, int def) {
        String v = System.getenv(name);
        try { return (v != null && !v.isEmpty()) ? Integer.parseInt(v.trim()) : def; }
        catch (NumberFormatException e) { return def; }
    }

    private static long envLong(String name, long def) {
        String v = System.getenv(name);
        try { return (v != null && !v.isEmpty()) ? Long.parseLong(v.trim()) : def; }
        catch (NumberFormatException e) { return def; }
    }

    private static double envDouble(String name, double def) {
        String v = System.getenv(name);
        try { return (v != null && !v.isEmpty()) ? Double.parseDouble(v.trim()) : def; }
        catch (NumberFormatException e) { return def; }
    }

    private List<long[]> buildWindows() {
        try {
            long dataStart = Utils.sdfFile.parse(DATA_START).getTime() + 7 * Utils.TIME_HOUR;
            long dataEnd = Utils.sdfFile.parse(DATA_END).getTime() + 7 * Utils.TIME_HOUR;
            List<long[]> wins = new ArrayList<>();
            Calendar cal = Calendar.getInstance();
            cal.setTimeInMillis(dataStart);
            cal.add(Calendar.MONTH, TRAIN_MONTHS);
            while (true) {
                long oosStart = cal.getTimeInMillis();
                Calendar oe = (Calendar) cal.clone();
                oe.add(Calendar.MONTH, OOS_MONTHS);
                long oosEnd = oe.getTimeInMillis();
                if (oosEnd > dataEnd) break;
                Calendar ts = (Calendar) cal.clone();
                ts.add(Calendar.MONTH, -TRAIN_MONTHS);
                wins.add(new long[]{ts.getTimeInMillis(), oosStart - Utils.TIME_MINUTE, oosStart, oosEnd - Utils.TIME_MINUTE});
                cal.add(Calendar.MONTH, OOS_MONTHS);
            }
            return wins;
        } catch (Exception e) {
            throw new RuntimeException("buildWindows loi", e);
        }
    }

    // ======================= runJob =======================
    @Override
    public String runJob(WfoJob job, WfoContext ctx) throws Exception {
        JSONObject p = new JSONObject(job.payload);
        int winIdx = p.getInt("winIdx");
        long trainStart = p.getLong("trainStart"), trainEnd = p.getLong("trainEnd");
        long oosStart = p.getLong("oosStart"), oosEnd = p.getLong("oosEnd");
        int nSamples = p.getInt("nSamples");
        long seed = p.getLong("seed");
        try {

        String[] names = GENOME.keySet().toArray(new String[0]);
        double[] baseVals = new double[names.length];
        for (int i = 0; i < names.length; i++) baseVals[i] = getField(names[i]);

        // TASK (frozen leakage-free genome): env WFO_FROZEN_GENOME set -> dung vector co dinh lam sample-0
        //   + ep N=1 (bo random samples). Ap qua setField cho ca 17 gene moi window. Default (env rong)
        //   -> frozen=null -> giu hanh vi cu byte-identical (golden/parity-safe).
        double[] frozen = loadFrozenGenome(names);
        if (frozen != null) {
            baseVals = frozen;
            nSamples = 1;
            StringBuilder gs = new StringBuilder();
            for (int i = 0; i < names.length; i++) {
                gs.append(names[i]).append('=').append(round4(frozen[i]));
                if (i < names.length - 1) gs.append(", ");
            }
            LOG.info("[FROZEN] win{} genome nap tu WFO_FROZEN_GENOME, ep N=1 | {}", winIdx, gs);
        }

        // ===== TRAIN: random search N mẫu, mẫu 0 = baseline =====
        Random rnd = new Random(seed);
        double[] bestGenome = baseVals.clone();
        float bestIsFit = -Float.MAX_VALUE;
        float bestIsPnl = 0f;     // PnL_IS của bestGenome (cho WFE = PnL_OOS/PnL_IS, pre-reg)
        String bestIsNote = "";   // note V4.1 của bestGenome (chẩn đoán — window sentinel IS lộ rõ)
        int rejectCount = 0;
        for (int s = 0; s < nSamples; s++) {
            double[] cand;
            if (s == 0) {
                cand = baseVals.clone();
            } else {
                cand = new double[names.length];
                for (int gi = 0; gi < names.length; gi++) {
                    double[] rg = GENOME.get(names[gi]);
                    cand[gi] = rg[0] + rnd.nextDouble() * (rg[1] - rg[0]);
                }
            }
            applyGenome(names, cand);
            HPOFitnessCalculatorV4.FitnessReport isRep = backtest(ctx, trainStart, trainEnd);
            float isFit = isRep.finalFitness;
            if (isFit < -50000f) rejectCount++;
            if (isFit > bestIsFit) { bestIsFit = isFit; bestIsPnl = isRep.totalProfit; bestIsNote = isRep.note; bestGenome = cand.clone(); }
        }

        // ===== OOS =====
        // TASK-142 (RAM): cache ticker-file cua vong TRAIN KHONG tai dung o OOS (khac dai ngay) → xoa truoc OOS
        // de gioi han RAM ~1 cua so train thay vi train+OOS. Vo hai voi aerospike (FILE_STORE rong). Khong doi so.
        if (Configs.USE_SMART_CACHE) {
            int fd = com.binance.chuyennd.ai_ml.data.HPOSmartCache.fileCachedDays();
            if (fd > 0) {
                com.binance.chuyennd.ai_ml.data.HPOSmartCache.clearFileCache();
                LOG.info("[CACHE] clear ticker-file cache truoc OOS: giai phong {} ngay khoi RAM", fd);
            }
        }
        applyGenome(names, bestGenome);
        HPOFitnessCalculatorV4.FitnessReport oos = backtest(ctx, oosStart, oosEnd);
        // WFE pre-registered = PnL_OOS / PnL_IS (KHONG dung calmar). bestGenome luon co PnL_IS>0
        // (fitness chon best da loai BURN_ACCOUNT totalProfit<=0), nen mau so duong.
        float wfe = bestIsPnl != 0 ? oos.totalProfit / bestIsPnl : 0f;

        // khôi phục baseline (giữ sạch cho job sau trong cùng JVM)
        applyGenome(names, baseVals);

        JSONObject res = new JSONObject();
        res.put("winIdx", winIdx);
        res.put("label", Utils.normalizeDateYYYYMMDD(oosStart) + ".." + Utils.normalizeDateYYYYMMDD(oosEnd));
        res.put("isFit", round4(bestIsFit));
        res.put("isPnl", round4(bestIsPnl));
        res.put("oosFit", round4(oos.finalFitness));
        res.put("wfe", round4(wfe));
        res.put("oosPnl", round4(oos.totalProfit));
        res.put("oosMaxDD", round4(oos.maxDrawdown));
        res.put("oosDdPct", round4(oos.ddPct));   // TỶ LỆ maxDD/vốn — dùng cho VERDICT (pre-reg ≤50%)
        // 🟡 TASK-119 (REPORT-ONLY): maxDD mark-to-market + MARGIN_CALL, ghi SONG SONG. Verdict KHÔNG đọc.
        res.put("oosMaxDD_mtm", round4(oos.maxDDMtm));
        res.put("oosDdPct_mtm", round4(oos.ddPctMtm));
        res.put("oosMarginCall", oos.marginCallHit);
        res.put("oosMinEqPct_mtm", round4(oos.minEquityMtmPct));
        res.put("oosCalmar", round4(oos.calmar));
        res.put("oosTrades", oos.tradeCount);
        // METRIC SURFACE (additive, report-only — R-vs-M diagnosis). KHONG vao fitness/verdict.
        //   return% KHONG code o day = oosPnl/CAPITAL_START (35000), tinh luc report.
        //   oosCostPerTrade = (fee + slippage + funding) trung binh/lenh (funding=0 khi APPLY_FUNDING_FEE off).
        res.put("oosWinRate", round4(oos.winRate));
        res.put("oosAvgWin", round4(oos.avgWin));
        res.put("oosAvgLoss", round4(oos.avgLoss));
        res.put("oosProfitFactor", round4(oos.profitFactor));
        res.put("oosMedianTradePnl", round4(oos.medianTradePnl));
        res.put("oosCostPerTrade", round4(oos.costPerTrade));
        if (Configs.GATE_COUNT_ONLY) {
            // count-only: khong tao order -> oos.tradeCount=0. Surface so gate-pass per-window.
            res.put("gateSeen", lastGateSeen);
            res.put("gatePass", lastGatePass);
            res.put("oosTrades", lastGatePass);   // dung lai plumbing oosTrades cho frequency probe
        }
        // V4.1 (TASK-113): note tường minh — aggregate đếm %OOS-dương CHỈ khi oosNote=SUCCESS (giữ semantics
        // đếm hiện tại: window sentinel giờ có pnl thật nhưng KHÔNG bao giờ được tính là cửa-sổ-thành-công)
        res.put("oosNote", oos.note);
        res.put("isNote", bestIsNote);
        res.put("rejectSamples", rejectCount);
        res.put("nSamples", nSamples);
        JSONObject g = new JSONObject();
        for (int i = 0; i < names.length; i++) g.put(names[i], round4(bestGenome[i]));
        res.put("bestGenome", g);
        LOG.info("[WIN {}] {} IS={} OOS={} WFE={} pnl={} reject={}/{}",
                winIdx, res.getString("label"), res.get("isFit"), res.get("oosFit"),
                res.get("wfe"), res.get("oosPnl"), rejectCount, nSamples);
        return res.toString();
        } finally {
            // TỐI ƯU RAM (chống OOM tích lũy): mỗi job xong → xóa cache nén của window này.
            // Window sau nạp lại từ đầu. Giữ RAM ~1 window (~4.5GB nén) thay vì cộng dồn nhiều window.
            if (Configs.USE_SMART_CACHE) {
                int days = com.binance.chuyennd.ai_ml.data.HPOSmartCache.cachedDays();
                com.binance.chuyennd.ai_ml.data.HPOSmartCache.clearCache();
                LOG.info("[CACHE] clear sau job: giai phong {} ngay nen khoi RAM", days);
            }
        }
    }

    private HPOFitnessCalculatorV4.FitnessReport backtest(WfoContext ctx, long start, long end) throws Exception {
        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(ctx.dataset.market, ctx.dataset.pred, ctx.dataset.funding, new AIRejectFilter());
        sim.simulatorWithInitEntry(start, end);
        // count-only frequency probe: giu counter cua lan backtest nay (OOS la lan cuoi -> field mang gia tri OOS)
        this.lastGateSeen = sim.ablationSignalSeen;
        this.lastGatePass = sim.ablationPassCount;
        // V4.1 (TASK-113): windowDays = range backtest THẬT của chính window này, KHÔNG suy từ span lệnh
        int windowDays = (int) Math.max(1, (end - start) / Utils.TIME_DAY);
        HPOFitnessCalculatorV4.FitnessReport rep = HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone, windowDays);
        LOG.info("[BT {}..{}] note={} trades={} pnl={} ddPct={} maxDD={} held>7d={} posYr={} fit={} " +
                        "| [119 report-only] ddPct_mtm={} maxDD_mtm={} marginCall={} minEqPct_mtm={}",
                Utils.normalizeDateYYYYMMDD(start), Utils.normalizeDateYYYYMMDD(end),
                rep.note, rep.tradeCount, round4(rep.totalProfit), round4(rep.ddPct),
                round4(rep.maxDrawdown), round4(rep.pctHeldOver7d), round4(rep.posYearRatio), round4(rep.finalFitness),
                round4(rep.ddPctMtm), round4(rep.maxDDMtm), rep.marginCallHit, round4(rep.minEquityMtmPct));
        return rep;
    }

    // ======================= aggregate + VERDICT =======================
    @Override
    public String aggregate(List<WfoJob> doneJobs) {
        List<JSONObject> rows = new ArrayList<>();
        for (WfoJob j : doneJobs) {
            if (j.result == null || j.result.isEmpty()) continue;
            rows.add(new JSONObject(j.result));
        }
        rows.sort(Comparator.comparingInt(o -> o.getInt("winIdx")));

        int n = rows.size();
        int posCount = 0;
        double worstMaxDD = 0;     // abs USD (tham khảo)
        double worstDdPct = 0;     // TỶ LỆ — dùng cho VERDICT
        double worstDdPctMtm = 0;  // 🟡 TASK-119 report-only — KHÔNG vào verdict
        int marginCallCount = 0;   // 🟡 TASK-119 report-only
        for (JSONObject r : rows) {
            double oosPnl = r.getDouble("oosPnl");
            // V4.1 (TASK-113): đếm cửa-sổ-thành-công TƯỜNG MINH theo note — chỉ SUCCESS && pnl>0.
            // optString default "SUCCESS" để tương thích result cũ (chưa có oosNote). Semantics đếm GIỮ
            // NGUYÊN V4: window sentinel (TOO_FEW/BURN/...) giờ hiện pnl thật nhưng KHÔNG được đếm dương.
            if ("SUCCESS".equals(r.optString("oosNote", "SUCCESS")) && oosPnl > 0) posCount++;
            worstMaxDD = Math.max(worstMaxDD, r.getDouble("oosMaxDD"));
            worstDdPct = Math.max(worstDdPct, r.optDouble("oosDdPct", 0));
            worstDdPctMtm = Math.max(worstDdPctMtm, r.optDouble("oosDdPct_mtm", 0));   // report-only
            if (r.optBoolean("oosMarginCall", false)) marginCallCount++;               // report-only
        }
        double posRatio = n > 0 ? (double) posCount / n : 0;
        // BUG 1 (2026-07-13): WFE median CHỈ tính trên window SUCCESS (đồng bộ semantics posCount).
        // Trước đây gom MỌI window (ZERO_TRADES/TOO_FEW/BURN/CAPITAL_LOCK) làm median luôn kẹt ~0.010,
        // che khuất WFE thật của các window SUCCESS. Nếu KHÔNG có window SUCCESS nào → median=0 → giữ FAIL.
        List<Double> wfesSuccess = collectSuccessWfe(rows);
        double wfeMedian = median(wfesSuccess);
        LOG.info("aggregate: WFE median tinh tren {}/{} window SUCCESS (loai {} window sentinel/disqualify)",
                wfesSuccess.size(), n, n - wfesSuccess.size());

        boolean pass = n > 0
                && wfeMedian >= PASS_WFE
                && posRatio >= PASS_POS_RATIO
                && worstDdPct <= PASS_MAXDD_OOS;

        StringBuilder md = new StringBuilder();
        md.append("# WFO STRATEGY — report\n\n");
        md.append("## VERDICT: ").append(pass ? "✅ PASS" : "❌ FAIL/REVIEW").append("\n\n");
        md.append("Ngưỡng pre-registered: WFE_median ≥ ").append(PASS_WFE)
          .append(", %cửa-sổ-OOS-dương ≥ ").append((int) (PASS_POS_RATIO * 100)).append("%")
          .append(", maxDD-OOS xấu nhất ≤ ").append((int) (PASS_MAXDD_OOS * 100)).append("% vốn").append("\n\n");
        md.append("## Tổng hợp\n");
        md.append("- Số cửa sổ DONE: ").append(n).append("\n");
        md.append("- % cửa sổ OOS dương: ").append(String.format(Locale.US, "%.1f%%", posRatio * 100))
          .append(" (").append(posCount).append("/").append(n).append(")\n");
        md.append("- WFE trung vị: ").append(String.format(Locale.US, "%.3f", wfeMedian)).append("\n");
        md.append("- maxDD OOS xấu nhất: ").append(String.format(Locale.US, "%.1f%% vốn", worstDdPct * 100))
          .append(" (abs ").append(String.format(Locale.US, "%.0f", worstMaxDD)).append(")\n\n");
        // 🟡 TASK-119 (REPORT-ONLY): số đo song song — KHÔNG dùng cho VERDICT ở trên.
        md.append("- **[119 report-only]** maxDD_mtm OOS xấu nhất: ")
          .append(String.format(Locale.US, "%.1f%% vốn", worstDdPctMtm * 100))
          .append(" | cửa sổ dính MARGIN_CALL: ").append(marginCallCount).append("/").append(n)
          .append(" _(maxDD_mtm = drawdown equity mark-to-market từ đỉnh, gồm realized; margin-call = equity ≤ 0.5% notional, proxy Binance cross 1x — chỉ báo cáo, verdict vẫn đọc maxDD cũ)_\n\n");
        md.append("## Bảng cửa sổ\n");
        md.append("| win | OOS | IS_fit | OOS_fit | WFE | OOS_pnl | OOS_maxDD | OOS_calmar | trades | oosNote | reject | ddPct% | ddPct_mtm% | marginCall | minEq_mtm% |\n");
        md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n");
        for (JSONObject r : rows) {
            md.append("| ").append(r.getInt("winIdx"))
              .append(" | ").append(r.getString("label"))
              .append(" | ").append(r.get("isFit"))
              .append(" | ").append(r.get("oosFit"))
              .append(" | ").append(r.get("wfe"))
              .append(" | ").append(r.get("oosPnl"))
              .append(" | ").append(r.get("oosMaxDD"))
              .append(" | ").append(r.get("oosCalmar"))
              .append(" | ").append(r.optInt("oosTrades", -1))
              .append(" | ").append(r.optString("oosNote", "SUCCESS"))
              .append(" | ").append(r.optInt("rejectSamples", -1)).append("/").append(r.optInt("nSamples", -1))
              // 🟡 TASK-119 report-only cols
              .append(" | ").append(String.format(Locale.US, "%.1f", r.optDouble("oosDdPct", 0) * 100))
              .append(" | ").append(String.format(Locale.US, "%.1f", r.optDouble("oosDdPct_mtm", 0) * 100))
              .append(" | ").append(r.optBoolean("oosMarginCall", false) ? "⚠️YES" : "no")
              .append(" | ").append(String.format(Locale.US, "%.1f", r.optDouble("oosMinEqPct_mtm", 1) * 100))
              .append(" |\n");
        }
        md.append("\n## Độ ổn định gene qua cửa sổ (min..max best value)\n");
        md.append(geneStability(rows));
        md.append("\n> ⚠️ WFE<0.3 = overfit; WFE≥0.5 tốt. maxDD backtest hiểu nhẹ (chưa margin-call) → biên an toàn.\n");
        return md.toString();
    }

    private String geneStability(List<JSONObject> rows) {
        StringBuilder sb = new StringBuilder();
        for (String g : GENOME.keySet()) {
            double mn = Double.MAX_VALUE, mx = -Double.MAX_VALUE;
            for (JSONObject r : rows) {
                JSONObject bg = r.optJSONObject("bestGenome");
                if (bg == null || !bg.has(g)) continue;
                double v = bg.getDouble(g);
                mn = Math.min(mn, v); mx = Math.max(mx, v);
            }
            if (mn == Double.MAX_VALUE) continue;
            sb.append("- ").append(g).append(": ")
              .append(String.format(Locale.US, "%.4f", mn)).append(" .. ")
              .append(String.format(Locale.US, "%.4f", mx)).append("\n");
        }
        return sb.toString();
    }

    // ======================= helpers =======================
    /**
     * BUG 1 (2026-07-13): gom WFE CHỈ của window SUCCESS (bỏ ZERO_TRADES/TOO_FEW/BURN/CAPITAL_LOCK...).
     * optString default "SUCCESS" để tương thích result cũ (chưa có field oosNote). Package-private để test.
     */
    static List<Double> collectSuccessWfe(List<JSONObject> rows) {
        List<Double> out = new ArrayList<>();
        for (JSONObject r : rows) {
            if ("SUCCESS".equals(r.optString("oosNote", "SUCCESS"))) out.add(r.getDouble("wfe"));
        }
        return out;
    }

    /**
     * GIỚI HẠN 3 (2026-07-13): parse env WFO_MAX_OOS_DATE (yyyyMMdd) → millis mốc chặn oosEnd cuối.
     * Rỗng/null/sai định dạng → {@link Long#MAX_VALUE} (giữ nguyên hành vi, không cap). Package-private để test.
     */
    static long parseMaxOosDateMs(String env) {
        if (env == null || env.trim().isEmpty()) return Long.MAX_VALUE;
        try {
            return Utils.sdfFile.parse(env.trim()).getTime() + 7 * Utils.TIME_HOUR;
        } catch (Exception e) {
            LOG.warn("WFO_MAX_OOS_DATE='{}' sai dinh dang yyyyMMdd -> bo qua cap: {}", env, e.getMessage());
            return Long.MAX_VALUE;
        }
    }

    /**
     * TASK (frozen leakage-free genome): nap genome co dinh tu env WFO_FROZEN_GENOME.
     * Gia tri env = duong dan FILE chua 17 so CSV (dung thu tu names[] cua GENOME) HOAC CSV inline.
     * Tra null neu env rong -> giu hanh vi cu (sample-0 = baseVals default, byte-identical).
     * So phan tu PHAI = names.length; sai -> RuntimeException (fail-fast, chong chay nham genome).
     * Package-private de test.
     */
    static double[] loadFrozenGenome(String[] names) throws Exception {
        String env = System.getenv("WFO_FROZEN_GENOME");
        if (env == null || env.trim().isEmpty()) return null;
        String raw = env.trim();
        java.io.File f = new java.io.File(raw);
        if (f.isFile()) {
            raw = new String(java.nio.file.Files.readAllBytes(f.toPath())).trim();
        }
        String[] parts = raw.split("[,\\s]+");
        List<Double> vals = new ArrayList<>();
        for (String p : parts) { if (!p.trim().isEmpty()) vals.add(Double.parseDouble(p.trim())); }
        if (vals.size() != names.length) {
            throw new RuntimeException("WFO_FROZEN_GENOME co " + vals.size() + " so, can dung " + names.length
                    + " (thu tu names[]=" + Arrays.toString(names) + ")");
        }
        double[] out = new double[names.length];
        for (int i = 0; i < names.length; i++) out[i] = vals.get(i);
        return out;
    }

    static double median(List<Double> xs) {   // package-private: cho unit test (StrategyWfoTaskMetricTest)
        if (xs.isEmpty()) return 0;
        List<Double> s = new ArrayList<>(xs);
        Collections.sort(s);
        int m = s.size() / 2;
        return s.size() % 2 == 1 ? s.get(m) : (s.get(m - 1) + s.get(m)) / 2.0;
    }
    private static double round4(double v) { return Math.round(v * 1e4) / 1e4; }
    private void applyGenome(String[] names, double[] vals) throws Exception {
        for (int i = 0; i < names.length; i++) setField(names[i], vals[i], IS_INT.get(names[i]));
    }
    private double getField(String name) throws Exception {
        return ((Number) Configs.class.getField(name).get(null)).doubleValue();
    }
    private void setField(String name, double val, boolean isInt) throws Exception {
        Field f = Configs.class.getField(name);
        if (isInt) f.setInt(null, (int) Math.round(val)); else f.setFloat(null, (float) val);
    }
}
