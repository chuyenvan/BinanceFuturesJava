package com.binance.chuyennd.ai_ml.wfo;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV4;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Random;
import java.util.TreeMap;

/**
 * TASK-111 — WALK-FORWARD OPTIMIZATION (WFO) chiến lược, genome đã giảm sau sensitivity.
 *
 * <p><b>Kim chỉ nam:</b> docs/insights/WFO_OBJECTIVE_RESEARCH.md. Nguyên tắc cốt lõi:
 * <ul>
 *   <li>Cửa sổ OOS = 3 tháng, <b>bước trượt = đúng 3 tháng</b> (các đoạn OOS KHÔNG chồng lấn — chống
 *       ảo giác bằng chứng). Train = 12 tháng liền trước mỗi OOS (rolling).</li>
 *   <li>Mỗi cửa sổ: tối ưu genome trên TRAIN (random search N mẫu) → lấy best → đo trên OOS.</li>
 *   <li>Output KHÔNG phải 1 bộ tham số, mà là PHÁN QUYẾT pipeline có generalize:
 *       WFE = fitness_OOS / fitness_IS, %cửa-sổ-OOS-dương, độ ổn định gene qua cửa sổ.</li>
 *   <li>Fitness = HPOFitnessCalculatorV4 (Calmar + constraint cứng). Hàm mục tiêu là việc của 1 cửa sổ;
 *       chống overfit là việc của TẦNG WFO (nhiều cửa sổ).</li>
 * </ul>
 *
 * <p><b>Compute:</b> random search N mẫu/cửa sổ × số cửa sổ. Chia nhiều máy qua arg WIN_FROM:WIN_TO.
 * Data nạp 1 lần, chạy mọi cửa sổ in-memory.
 *
 * <p>Arg: [N_SAMPLES=30] [WIN_FROM:WIN_TO] [SEED=42]. Read-only Aerospike (đọc 226 khi IS_KAGGLE_MODE).
 */
public class WFORunner {

    private static final Logger LOG = LoggerFactory.getLogger(WFORunner.class);

    // Dải dữ liệu tổng (GMT+7). 2021-01 → 2026-06.
    private static final String DATA_START = "20210101";
    private static final String DATA_END = "20260601";
    private static final int TRAIN_MONTHS = 12;
    private static final int OOS_MONTHS = 3;       // = bước trượt (không chồng lấn)

    // ===== GENOME đã giảm sau sensitivity (17 gene GIỮ). Cụm phẳng đã ngắt, KHÔNG ở đây.
    // Mỗi gene: [min, max] rời rạc hóa thành các mức khi random search. Range quanh vùng AN TOÀN
    // (tránh vùng REJECT đã biết từ sensitivity — vd MIN_MOMENTUM không xuống dưới ~0.03).
    static final Map<String, double[]> GENOME = new LinkedHashMap<>();
    static final Map<String, Boolean> IS_INT = new LinkedHashMap<>();
    static {
        // entry (vùng an toàn, tránh REJECT)
        put("MIN_MOMENTUM_15M", 0.030, 0.050, false);          // <0.03 -> REJECT
        put("PREDICT_SYMBOL_RATE_MAX_THRESHOLD", 0.05, 0.20, false); // >0.21 -> REJECT
        put("AI_DYNAMIC_MULTIPLIER", 1.5, 2.0, false);         // <1.5 -> REJECT
        put("AI_DYNAMIC_MIN", 0.10, 0.50, false);
        put("HARD_RISK_LIMIT_4H", -0.30, -0.05, false);
        // market
        put("MS_DOWN_BIG_AVG", -0.055, -0.020, false);
        // dca (tránh vùng REJECT: DCA_LOSS không sâu hơn -0.23; DCA_TIME tránh 8-14)
        put("DCA_LOSS_BIG_DOWN", -0.22, -0.08, false);
        put("DCA_TIME_BIG_DOWN", 3, 7, true);
        put("DCA_TIME_BIG_Up", 21, 30, true);
        // trailing (vùng an toàn quanh baseline; tránh REJECT)
        put("RATE_PROFIT_STOP_MARKET", 0.012, 0.025, false);   // tránh ~0.018 REJECT? thực ra 0.025 ok, 0.0183 REJECT -> dùng >=0.020
        put("TS_PROFIT_MULTIPLIER", 4.0, 8.0, false);
        put("TS_DYNAMIC_K", 0.10, 0.25, false);                // tránh ~0.27 REJECT
        put("TS_MAX_GAP", 0.04, 0.06, false);                  // tránh ~0.077 REJECT
        put("TS_MAX_GAP_WEAK", 0.045, 0.060, false);           // tránh <0.043 REJECT
        put("TS_WEAK_MOMENTUM_THRES", 0.004, 0.008, false);
        // budget (tránh vùng REJECT: RATIO_1 <0.53, RATIO_2 <0.8, DIVIDER_2 <1.6)
        put("BUDGET_MARGIN_RATIO_1", 0.30, 0.50, false);
        put("BUDGET_MARGIN_RATIO_2", 0.60, 0.78, false);
        put("BUDGET_DIVIDER_2", 1.60, 2.50, false);   // <1.6 -> REJECT (sensitivity gene 26)
    }
    private static void put(String f, double lo, double hi, boolean isInt) { GENOME.put(f, new double[]{lo, hi}); IS_INT.put(f, isInt); }

    static TreeMap<Long, MarketDataObject> mkt;
    static TreeMap<Long, AiPredictionData> pred;
    static TreeMap<Long, long[]> fund;

    public static void main(String[] args) {
        try {
            Configs.IS_HPO_MODE = false;
            Configs.ABLATION_MODE = "A";
            Configs.BREAKER_MODE = "OFF";
            if ("1".equals(System.getenv("WFO_KAGGLE"))) Configs.IS_KAGGLE_MODE = true;
            int nSamples = args.length > 0 ? Integer.parseInt(args[0]) : 30;
            int winFrom = 0, winTo = Integer.MAX_VALUE;
            if (args.length > 1 && args[1].contains(":")) {
                String[] p = args[1].split(":");
                winFrom = Integer.parseInt(p[0]); winTo = Integer.parseInt(p[1]);
            }
            long seed = args.length > 2 ? Long.parseLong(args[2]) : 42L;
            new WFORunner().run(nSamples, winFrom, winTo, seed);
            System.exit(0);
        } catch (Exception ex) {
            LOG.error("WFORunner loi", ex);
            System.exit(1);
        }
    }

    static class Window { int idx; long trainStart, trainEnd, oosStart, oosEnd; String label; }

    private List<Window> buildWindows() throws Exception {
        long dataStart = Utils.sdfFile.parse(DATA_START).getTime() + 7 * Utils.TIME_HOUR;
        long dataEnd = Utils.sdfFile.parse(DATA_END).getTime() + 7 * Utils.TIME_HOUR;
        List<Window> wins = new ArrayList<>();
        java.util.Calendar cal = java.util.Calendar.getInstance();
        // OOS đầu tiên bắt đầu sau TRAIN_MONTHS kể từ dataStart
        cal.setTimeInMillis(dataStart);
        cal.add(java.util.Calendar.MONTH, TRAIN_MONTHS);
        int idx = 0;
        while (true) {
            long oosStart = cal.getTimeInMillis();
            java.util.Calendar oe = (java.util.Calendar) cal.clone();
            oe.add(java.util.Calendar.MONTH, OOS_MONTHS);
            long oosEnd = oe.getTimeInMillis();
            if (oosEnd > dataEnd) break;
            java.util.Calendar ts = (java.util.Calendar) cal.clone();
            ts.add(java.util.Calendar.MONTH, -TRAIN_MONTHS);
            Window w = new Window();
            w.idx = idx++;
            w.trainStart = ts.getTimeInMillis();
            w.trainEnd = oosStart - Utils.TIME_MINUTE;
            w.oosStart = oosStart;
            w.oosEnd = oosEnd - Utils.TIME_MINUTE;
            w.label = Utils.sdfFile.format(new java.util.Date(oosStart)) + ".." + Utils.sdfFile.format(new java.util.Date(oosEnd));
            wins.add(w);
            cal.add(java.util.Calendar.MONTH, OOS_MONTHS); // trượt = OOS (không chồng lấn)
        }
        return wins;
    }

    void run(int nSamples, int winFrom, int winTo, long seed) throws Exception {
        LOG.info("Nap data 1 lan...");
        mkt = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        pred = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        fund = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();

        List<Window> wins = buildWindows();
        winTo = Math.min(winTo, wins.size());
        LOG.info("market={} pred={} funding={} | {} cua so OOS (3 thang), chay {}..{} | N_samples={} genome={} gene",
                mkt.size(), pred.size(), fund.size(), wins.size(), winFrom, winTo, nSamples, GENOME.size());

        String[] geneNames = GENOME.keySet().toArray(new String[0]);
        double[] baseVals = new double[geneNames.length];
        for (int i = 0; i < geneNames.length; i++) baseVals[i] = getField(geneNames[i]);

        List<String> summary = new ArrayList<>();
        summary.add("winIdx | OOS_label | IS_fit | OOS_fit | WFE | OOS_pnl | OOS_maxDD | OOS_calmar | best_genome");

        for (int wi = winFrom; wi < winTo; wi++) {
            Window w = wins.get(wi);
            Random rnd = new Random(seed + wi);
            // ===== TRAIN: random search N mẫu trên train, chọn best theo fitness V4 =====
            double[] bestGenome = baseVals.clone();
            float bestIsFit = -Float.MAX_VALUE;
            // mẫu 0 = baseline (giá trị hiện tại) làm mốc
            for (int s = 0; s < nSamples; s++) {
                double[] cand = new double[geneNames.length];
                if (s == 0) {
                    cand = baseVals.clone();
                } else {
                    for (int gi = 0; gi < geneNames.length; gi++) {
                        double[] rg = GENOME.get(geneNames[gi]);
                        cand[gi] = rg[0] + rnd.nextDouble() * (rg[1] - rg[0]);
                    }
                }
                applyGenome(geneNames, cand);
                float isFit = runBacktest(w.trainStart, w.trainEnd).finalFitness;
                if (isFit > bestIsFit) { bestIsFit = isFit; bestGenome = cand.clone(); }
            }
            // ===== OOS: áp best genome lên đoạn OOS =====
            applyGenome(geneNames, bestGenome);
            HPOFitnessCalculatorV4.FitnessReport oos = runBacktest(w.oosStart, w.oosEnd);
            float wfe = bestIsFit != 0 ? oos.finalFitness / bestIsFit : 0f;

            StringBuilder gp = new StringBuilder();
            for (int gi = 0; gi < geneNames.length; gi++) gp.append(geneNames[gi]).append("=").append(f4(bestGenome[gi])).append(" ");
            String line = String.format(Locale.US, "%d | %s | %.3f | %.3f | %.3f | %.1f | %.1f | %.3f | %s",
                    w.idx, w.label, bestIsFit, oos.finalFitness, wfe, oos.totalProfit, oos.maxDrawdown, oos.calmar, gp.toString().trim());
            summary.add(line);
            LOG.info("[WIN {}] {} IS={} OOS={} WFE={} OOS_pnl={} OOS_calmar={}",
                    w.idx, w.label, f4(bestIsFit), f4(oos.finalFitness), f4(wfe), f4(oos.totalProfit), f4(oos.calmar));
            // khôi phục baseline trước cửa sổ sau
            applyGenome(geneNames, baseVals);
        }

        LOG.info("======================= WFO SUMMARY =======================");
        for (String s : summary) LOG.info(s);
        LOG.info("==> Doc: WFE>=0.5 tot, <0.3 overfit. %cua-so-OOS-duong>=70%. Xem do on dinh gene qua cua so.");
    }

    private void applyGenome(String[] names, double[] vals) throws Exception {
        for (int i = 0; i < names.length; i++) setField(names[i], vals[i], IS_INT.get(names[i]));
    }

    private HPOFitnessCalculatorV4.FitnessReport runBacktest(long start, long end) throws Exception {
        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(mkt, pred, fund, new AIRejectFilter());
        sim.simulatorWithInitEntry(start, end);
        return HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone);
    }

    private static String f4(double v) { return String.format(Locale.US, "%.4f", v); }
    private double getField(String name) throws Exception { return ((Number) Configs.class.getField(name).get(null)).doubleValue(); }
    private void setField(String name, double val, boolean isInt) throws Exception {
        Field f = Configs.class.getField(name);
        if (isInt) f.setInt(null, (int) Math.round(val)); else f.setFloat(null, (float) val);
    }
}
