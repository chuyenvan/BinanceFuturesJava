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
 * WFO TASK loại 1 — STRATEGY WFO (tối ưu 18 gene chiến lược, off-cứng 9 gene phẳng đã loại).
 *
 * <p>Mỗi JOB = 1 cửa sổ: train 12 tháng + OOS 3 tháng (trượt = OOS, không chồng lấn). runJob:
 * random-search N mẫu genome trên TRAIN → best theo fitness V4 → đo OOS → WFE. result JSON gồm
 * {winIdx, label, isFit, oosFit, wfe, oosPnl, oosMaxDD, oosCalmar, bestGenome}.
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

    // ===== cấu hình cửa sổ (khớp WFORunner) =====
    private static final String DATA_START = "20210101";
    private static final String DATA_END = "20260601";
    private static final int TRAIN_MONTHS = envInt("WFO_TRAIN_MONTHS", 12);
    private static final int OOS_MONTHS = envInt("WFO_OOS_MONTHS", 3);
    private static final int DEFAULT_N_SAMPLES = 30;
    private static final long SEED_BASE = 42L;

    // ===== ngưỡng VERDICT pre-registered (chốt TRƯỚC khi chạy — WFO_OBJECTIVE_RESEARCH.md) =====
    public static final float PASS_WFE = 0.5f;        // WFE = PnL_OOS/PnL_IS; ≥0.5 tốt, <0.3 overfit
    public static final float PASS_POS_RATIO = 0.70f; // ≥70% cửa sổ OOS dương
    public static final float PASS_MAXDD_OOS = 0.50f; // maxDD-OOS xấu nhất theo TỶ LỆ vốn (≤50%, pre-registered). Dùng ddPct, KHÔNG abs USD.

    // ===== GENOME 18 gene (cụm A REJECT + B nhạy vừa). Range vùng AN TOÀN tránh REJECT. =====
    static final LinkedHashMap<String, double[]> GENOME = new LinkedHashMap<>();
    static final LinkedHashMap<String, Boolean> IS_INT = new LinkedHashMap<>();
    static {
        put("MIN_MOMENTUM_15M", 0.030, 0.050, false);
        put("PREDICT_SYMBOL_RATE_MAX_THRESHOLD", 0.05, 0.20, false);
        put("AI_DYNAMIC_MULTIPLIER", 1.5, 2.0, false);
        put("AI_DYNAMIC_MIN", 0.10, 0.50, false);
        put("HARD_RISK_LIMIT_4H", -0.30, -0.05, false);
        put("MS_DOWN_BIG_AVG", -0.055, -0.020, false);
        put("DCA_LOSS_BIG_DOWN", -0.22, -0.08, false);
        put("DCA_TIME_BIG_DOWN", 3, 7, true);
        put("DCA_TIME_BIG_Up", 21, 30, true);
        put("RATE_PROFIT_STOP_MARKET", 0.012, 0.025, false);
        put("TS_PROFIT_MULTIPLIER", 4.0, 8.0, false);
        put("TS_DYNAMIC_K", 0.10, 0.25, false);
        put("TS_MAX_GAP", 0.04, 0.06, false);
        put("TS_MAX_GAP_WEAK", 0.045, 0.060, false);
        put("TS_WEAK_MOMENTUM_THRES", 0.004, 0.008, false);
        put("BUDGET_MARGIN_RATIO_1", 0.30, 0.50, false);
        put("BUDGET_MARGIN_RATIO_2", 0.60, 0.78, false);
        put("BUDGET_DIVIDER_2", 1.60, 2.50, false);
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
        List<WfoJob> jobs = new ArrayList<>();
        for (int i = 0; i < wins.size() && i < maxW; i++) {
            long[] w = wins.get(i);
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

        // ===== TRAIN: random search N mẫu, mẫu 0 = baseline =====
        Random rnd = new Random(seed);
        double[] bestGenome = baseVals.clone();
        float bestIsFit = -Float.MAX_VALUE;
        float bestIsPnl = 0f;     // PnL_IS của bestGenome (cho WFE = PnL_OOS/PnL_IS, pre-reg)
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
            if (isFit > bestIsFit) { bestIsFit = isFit; bestIsPnl = isRep.totalProfit; bestGenome = cand.clone(); }
        }

        // ===== OOS =====
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
        res.put("oosCalmar", round4(oos.calmar));
        res.put("oosTrades", oos.tradeCount);
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
        HPOFitnessCalculatorV4.FitnessReport rep = HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone);
        LOG.info("[BT {}..{}] note={} trades={} pnl={} ddPct={} maxDD={} held>7d={} posYr={} fit={}",
                Utils.normalizeDateYYYYMMDD(start), Utils.normalizeDateYYYYMMDD(end),
                rep.note, rep.tradeCount, round4(rep.totalProfit), round4(rep.ddPct),
                round4(rep.maxDrawdown), round4(rep.pctHeldOver7d), round4(rep.posYearRatio), round4(rep.finalFitness));
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
        List<Double> wfes = new ArrayList<>();
        double worstMaxDD = 0;     // abs USD (tham khảo)
        double worstDdPct = 0;     // TỶ LỆ — dùng cho VERDICT
        for (JSONObject r : rows) {
            double oosPnl = r.getDouble("oosPnl");
            if (oosPnl > 0) posCount++;
            wfes.add(r.getDouble("wfe"));
            worstMaxDD = Math.max(worstMaxDD, r.getDouble("oosMaxDD"));
            worstDdPct = Math.max(worstDdPct, r.optDouble("oosDdPct", 0));
        }
        double posRatio = n > 0 ? (double) posCount / n : 0;
        double wfeMedian = median(wfes);

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
        md.append("## Bảng cửa sổ\n");
        md.append("| win | OOS | IS_fit | OOS_fit | WFE | OOS_pnl | OOS_maxDD | OOS_calmar | trades | reject |\n");
        md.append("|---|---|---|---|---|---|---|---|---|---|\n");
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
              .append(" | ").append(r.optInt("rejectSamples", -1)).append("/").append(r.optInt("nSamples", -1))
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
    private static double median(List<Double> xs) {
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
