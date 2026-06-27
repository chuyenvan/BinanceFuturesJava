package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

/**
 * TASK-111 (B-kiểm chứng) — ABLATION CỤM GENE PHẲNG.
 *
 * <p>Sensitivity OAT đo TỪNG gene (giữ 26 gene kia ở baseline). Tool này kiểm chứng phần OAT bỏ sót:
 * OFF ĐỒNG THỜI cả cụm gene phẳng → xem fitness có tụt khỏi baseline không (bắt tương tác giữa các
 * gene phẳng mà OAT không thấy).
 *
 * <p><b>"Off" một gene phẳng</b> = đặt sang GIÁ TRỊ GIỮA range của nó (khác giá trị hiện tại nhưng hợp
 * lệ). Nếu cụm phẳng thật sự vô hại, đổi đồng thời cả cụm sang giá trị giữa cũng KHÔNG làm tụt fitness.
 *
 * <p><b>Kết luận:</b>
 * <ul>
 *   <li>off-cụm ≈ baseline (chênh &lt; ~2%) → cụm phẳng vô hại kể cả khi off đồng thời → NGẮT CỨNG được
 *       (xóa khỏi genome HPO, hardcode giá trị hiện tại).</li>
 *   <li>off-cụm tụt rõ → có tương tác → NGẮT MỀM (giữ trong code, đưa vào danh sách constant
 *       KHÔNG-HPO, comment lý do).</li>
 * </ul>
 *
 * Chạy Oracle. Arg: FAST (2024-01..2026-06) | FULL. Read-only Aerospike.
 */
public class AblationClusterTool {

    private static final Logger LOG = LoggerFactory.getLogger(AblationClusterTool.class);
    private static final String FAST_START = "20240101", FAST_END = "20260601";
    private static final String FULL_START = "20210101", FULL_END = "20260601";

    // CỤM GENE PHẲNG (range < 0.06 trong sensitivity FAST). field -> [min, max] để lấy giá trị GIỮA.
    // (Giá trị giữa = (min+max)/2, là giá trị "off" khác baseline để kiểm tương tác.)
    static final Map<String, double[]> FLAT_CLUSTER = new LinkedHashMap<>();
    static {
        FLAT_CLUSTER.put("PREDICT_SYMBOL_RATE_DOWN_15M", new double[]{-0.05, -0.015});   // range 0.0000
        FLAT_CLUSTER.put("PREDICT_SYMBOL_RATE_UP_AVG", new double[]{0.002, 0.010});       // range 0.0000
        FLAT_CLUSTER.put("PREDICT_SYMBOL_RATE_DOWN_AVG", new double[]{-0.010, -0.002});   // range 0.0000
        FLAT_CLUSTER.put("MS_UP_SMALL_THRES", new double[]{0.002, 0.010});                 // range 0.0038
        FLAT_CLUSTER.put("MS_DOWN_SMALL_AVG_OR_15M", new double[]{-0.040, -0.010});        // range 0.0044
        FLAT_CLUSTER.put("DCA_LOSS_BIG_UP", new double[]{-0.40, -0.10});                   // range 0.0092
        FLAT_CLUSTER.put("BUDGET_DIVIDER_1", new double[]{1.2, 2.5});                      // range 0.0096
        FLAT_CLUSTER.put("MS_UP_BIG_THRES", new double[]{0.010, 0.040});                   // range 0.0318
        FLAT_CLUSTER.put("AI_DYNAMIC_MAX", new double[]{1.5, 3.0});                        // range 0.0531
        // BUDGET_DIVIDER_2 sẽ thêm sau khi gene 26 chạy xong nếu phẳng (cùng loại DIVIDER_1)
    }

    static TreeMap<Long, MarketDataObject> mkt;
    static TreeMap<Long, AiPredictionData> pred;
    static TreeMap<Long, long[]> fund;
    static long simStart, simEnd;

    public static void main(String[] args) {
        try {
            Configs.IS_HPO_MODE = false;
            Configs.ABLATION_MODE = "A";
            Configs.BREAKER_MODE = "OFF";
            String mode = args.length > 0 ? args[0] : "FAST";
            new AblationClusterTool().run(mode);
            System.exit(0);
        } catch (Exception ex) {
            LOG.error("AblationClusterTool loi", ex);
            System.exit(1);
        }
    }

    void run(String mode) throws Exception {
        String start = mode.equalsIgnoreCase("FULL") ? FULL_START : FAST_START;
        String end = mode.equalsIgnoreCase("FULL") ? FULL_END : FAST_END;
        simStart = Utils.sdfFile.parse(start).getTime() + 7 * Utils.TIME_HOUR;
        simEnd = Utils.sdfFile.parse(end).getTime() + 24 * Utils.TIME_HOUR - Utils.TIME_MINUTE;

        LOG.info("Nap data 1 lan...");
        mkt = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        pred = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        fund = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("market={} pred={} funding={} | range {}..{}", mkt.size(), pred.size(), fund.size(), start, end);

        // 1) BASELINE — tất cả gene giá trị hiện tại
        HPOFitnessCalculatorV4.FitnessReport base = runBacktest();
        LOG.info("===== BASELINE: fitness={} pnl={} maxDD={} calmar={} trades={} =====",
                f(base.finalFitness), f(base.totalProfit), f(base.maxDrawdown), f(base.calmar), base.tradeCount);

        // 2) OFF ĐỒNG THỜI cụm phẳng — đặt mỗi gene sang giá trị giữa range
        Map<String, Double> saved = new LinkedHashMap<>();
        for (Map.Entry<String, double[]> e : FLAT_CLUSTER.entrySet()) {
            saved.put(e.getKey(), getField(e.getKey()));
            double mid = (e.getValue()[0] + e.getValue()[1]) / 2.0;
            setField(e.getKey(), mid);
            LOG.info("OFF {} : {} -> {} (giua range)", e.getKey(), f(saved.get(e.getKey())), f(mid));
        }
        HPOFitnessCalculatorV4.FitnessReport off = runBacktest();
        LOG.info("===== OFF-CUM-PHANG: fitness={} pnl={} maxDD={} calmar={} trades={} =====",
                f(off.finalFitness), f(off.totalProfit), f(off.maxDrawdown), f(off.calmar), off.tradeCount);

        // khoi phuc
        for (Map.Entry<String, Double> e : saved.entrySet()) setField(e.getKey(), e.getValue());

        // 3) KET LUAN
        float baseFit = base.finalFitness, offFit = off.finalFitness;
        float deltaPct = baseFit != 0 ? (offFit - baseFit) / Math.abs(baseFit) * 100f : 0f;
        LOG.info("======================= KET LUAN ABLATION CUM PHANG =======================");
        LOG.info("baseline fitness = {}", f(baseFit));
        LOG.info("off-cum   fitness = {}", f(offFit));
        LOG.info("delta = {}% ({} gene off dong thoi)", f(deltaPct), FLAT_CLUSTER.size());
        if (Math.abs(deltaPct) < 2.0f) {
            LOG.info(">>> CUM PHANG VO HAI ke ca off dong thoi (delta<2%) -> NGAT CUNG duoc (xoa khoi genome HPO).");
        } else {
            LOG.info(">>> CO TUONG TAC (delta>=2%) -> NGAT MEM (giu code, danh sach constant KHONG-HPO, comment).");
        }
    }

    private static String f(double v) { return String.format(Locale.US, "%.4f", v); }

    private HPOFitnessCalculatorV4.FitnessReport runBacktest() throws Exception {
        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(mkt, pred, fund, new AIRejectFilter());
        sim.simulatorWithInitEntry(simStart, simEnd);
        return HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone);
    }

    private double getField(String name) throws Exception {
        return ((Number) Configs.class.getField(name).get(null)).doubleValue();
    }

    private void setField(String name, double val) throws Exception {
        Field f = Configs.class.getField(name);
        if (f.getType() == int.class || f.getType() == Integer.class) f.setInt(null, (int) Math.round(val));
        else f.setFloat(null, (float) val);
    }
}
