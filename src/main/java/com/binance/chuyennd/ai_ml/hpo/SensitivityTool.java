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
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.TreeMap;

/**
 * TASK-111 (B) — SENSITIVITY ANALYSIS gene chiến lược (one-at-a-time / OAT).
 *
 * <p><b>Mục đích:</b> đo độ NHẠY của từng gene tới hàm mục tiêu (HPOFitnessCalculatorV4.finalFitness),
 * để cắt gene PHẲNG (vặn không đổi kết quả) và giữ gene quan trọng → đưa genome HPO về ~12 gene
 * thực sự nhạy (Uni đề xuất 12 — tool này đo để xác nhận con số đúng từ dữ liệu).
 *
 * <p><b>Phương pháp OAT:</b> baseline = giá trị Configs hiện tại. Với mỗi gene, đặt nó ở các MỨC quét
 * (quanh baseline, trong range hợp lý), GIỮ các gene khác ở baseline, chạy backtest, đo finalFitness.
 * Độ nhạy gene = (max finalFitness − min finalFitness) qua các mức. Gene phẳng → biên độ ~0.
 *
 * <p><b>HẠN CHẾ (ghi rõ):</b> OAT bỏ qua TƯƠNG TÁC giữa gene (gene phẳng đơn lẻ có thể nhạy khi kết hợp).
 * Đủ để phát hiện gene phẳng-mọi-nơi (ứng viên cắt rõ ràng), KHÔNG thay thế HPO đa biến. Dùng làm
 * bước SÀNG trước HPO, không phải kết luận cuối.
 *
 * <p><b>Hàm mục tiêu:</b> dùng V4 HIỆN CÓ (đã validate xếp hạng đúng A&gt;B&gt;C ở FAST). Khi hàm mục tiêu
 * được vá (đưa ổn-định-theo-thời-gian vào) thì CHẠY LẠI sensitivity — kết quả có thể đổi.
 *
 * <p>Chạy 226 (Aerospike local, -Xmx11g) hoặc Oracle. Arg: FAST | FULL, LEVELS (số mức mỗi gene, mặc định 4).
 * Mỗi gene × LEVELS backtest. ~22 gene × 4 ≈ 88 backtest. Read-only Aerospike.
 */
public class SensitivityTool {

    private static final Logger LOG = LoggerFactory.getLogger(SensitivityTool.class);
    private static final String FAST_START = "20240101", FAST_END = "20260601"; // 2.5y, qua bear+crash
    private static final String FULL_START = "20210101", FULL_END = "20260601";

    /** Mô tả 1 gene: tên field Configs, min, max range hợp lý (quét trong khoảng này quanh baseline). */
    static class Gene {
        String field; double min, max; boolean isInt; String tang;
        Gene(String tang, String field, double min, double max, boolean isInt) {
            this.tang = tang; this.field = field; this.min = min; this.max = max; this.isInt = isInt;
        }
    }

    // Danh sách gene = bản đồ rà GENE_AUDIT_TASK111.md (tham số THẬT engine dùng). Range quanh giá trị
    // hiện tại + biên hợp lý nghiệp vụ. LEVERAGE/FILTER_MODE/BREAKER (categorical/khóa) KHÔNG đưa vào.
    static List<Gene> genes() {
        List<Gene> g = new ArrayList<>();
        // Tầng 1 — entry filter
        g.add(new Gene("entry", "MIN_MOMENTUM_15M", 0.005, 0.05, false));
        g.add(new Gene("entry", "PREDICT_SYMBOL_RATE_MAX_THRESHOLD", 0.05, 0.30, false));
        g.add(new Gene("entry", "AI_DYNAMIC_MULTIPLIER", 0.8, 2.0, false));
        g.add(new Gene("entry", "AI_DYNAMIC_MIN", 0.1, 0.5, false));
        g.add(new Gene("entry", "AI_DYNAMIC_MAX", 1.5, 3.0, false));
        // Tầng 2 — market detect
        g.add(new Gene("market", "MS_UP_BIG_THRES", 0.010, 0.040, false));
        g.add(new Gene("market", "MS_DOWN_BIG_AVG", -0.060, -0.020, false));
        g.add(new Gene("market", "MS_UP_SMALL_THRES", 0.002, 0.010, false));
        g.add(new Gene("market", "MS_DOWN_SMALL_AVG_OR_15M", -0.040, -0.010, false));
        // Tầng 3 — DCA
        g.add(new Gene("dca", "DCA_TIME_BIG_DOWN", 3, 20, true));
        g.add(new Gene("dca", "DCA_LOSS_BIG_DOWN", -0.30, -0.08, false));
        // Tầng 4 — trailing exit
        // 2026-07-30: dong bo voi StrategyWfoTask (TASK-139 xac nhan [0.005,0.025] la vung CAT NON).
        // Tool OAT lich su (khong nam tren duong production), sua de khong con la vi du sai.
        g.add(new Gene("trail", "RATE_PROFIT_STOP_MARKET", 0.03, 0.05, false));
        g.add(new Gene("trail", "TS_MAX_GAP", 0.04, 0.15, false));
        g.add(new Gene("trail", "TS_MAX_GAP_WEAK", 0.01, 0.06, false));
        return g;
    }

    static TreeMap<Long, MarketDataObject> mkt;
    static TreeMap<Long, AiPredictionData> pred;
    static TreeMap<Long, long[]> fund;
    static long simStart, simEnd;

    public static void main(String[] args) {
        try {
            // TASK-112: cluster doc theo config per-box AEROSPIKE_READ_CLUSTER (env SENS_KAGGLE cu da bo).
            String mode = args.length > 0 ? args[0] : "FAST";
            int levels = args.length > 1 ? Integer.parseInt(args[1]) : 4;
            // arg[2] = "from:to" chia gene cho tung may (vd "0:9" chay gene 0..8). Mac dinh ca bo.
            int from = 0, to = Integer.MAX_VALUE;
            if (args.length > 2 && args[2].contains(":")) {
                String[] p = args[2].split(":");
                from = Integer.parseInt(p[0]);
                to = Integer.parseInt(p[1]);
            }
            new SensitivityTool().run(mode, levels, from, to);
            System.exit(0);
        } catch (Exception ex) {
            LOG.error("SensitivityTool loi", ex);
            System.exit(1);
        }
    }

    void run(String mode, int levels, int from, int to) throws Exception {
        String start = mode.equalsIgnoreCase("FULL") ? FULL_START : FAST_START;
        String end = mode.equalsIgnoreCase("FULL") ? FULL_END : FAST_END;
        simStart = Utils.sdfFile.parse(start).getTime() + 7 * Utils.TIME_HOUR;
        simEnd = Utils.sdfFile.parse(end).getTime() + 24 * Utils.TIME_HOUR - Utils.TIME_MINUTE;

        LOG.info("Nap data 1 lan...");
        mkt = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        pred = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        fund = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        List<Gene> genes = genes();
        to = Math.min(to, genes.size());
        LOG.info("market={} pred={} funding={} | range {}..{} levels={} | GENE {}..{} ({} gene)",
                mkt.size(), pred.size(), fund.size(), start, end, levels, from, to, to - from);

        // BASELINE (gia tri Configs hien tai)
        float baseFit = runBacktest();
        LOG.info("===== BASELINE finalFitness = {} =====", String.format("%.5f", baseFit));

        List<String> results = new ArrayList<>();
        results.add(String.format("%-32s | %-7s | %9s | %9s | %9s | %s", "GENE", "tang", "minFit", "maxFit", "range", "muc->fitness"));
        for (int gi = from; gi < to; gi++) {
            Gene g = genes.get(gi);
            double base = getField(g.field);
            StringBuilder detail = new StringBuilder();
            float minFit = Float.MAX_VALUE, maxFit = -Float.MAX_VALUE;
            for (int i = 0; i < levels; i++) {
                double v = g.min + (g.max - g.min) * i / (levels - 1);
                setField(g.field, v, g.isInt);
                float fit = runBacktest();
                minFit = Math.min(minFit, fit);
                maxFit = Math.max(maxFit, fit);
                detail.append(String.format(Locale.US, "%.4g->%.3f ", v, fit));
            }
            setField(g.field, base, g.isInt); // tra ve baseline
            float rangeFit = maxFit - minFit;
            results.add(String.format(Locale.US, "%-32s | %-7s | %9.3f | %9.3f | %9.4f | %s",
                    g.field, g.tang, minFit, maxFit, rangeFit, detail.toString().trim()));
            LOG.info("[{}] {} range={} (base={})", g.tang, g.field, String.format("%.4f", rangeFit), String.format("%.4g", base));
        }

        LOG.info("======================= SENSITIVITY (range fitness moi gene, GIAM DAN) =======================");
        // sort theo range giam dan de xem "vach" cat
        results.subList(1, results.size()).sort((a, b) -> {
            double ra = Double.parseDouble(a.split("\\|")[4].trim());
            double rb = Double.parseDouble(b.split("\\|")[4].trim());
            return Double.compare(rb, ra);
        });
        for (String line : results) LOG.info(line);
        LOG.info("==> Cat gene co range ~0 (phang). Xem 'vach' tren duong cong de chot so gene giu (~12).");
    }

    private float runBacktest() throws Exception {
        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(mkt, pred, fund, new AIRejectFilter());
        sim.simulatorWithInitEntry(simStart, simEnd);
        // V4.1 (TASK-113): windowDays = range backtest THẬT của chính lần chạy này, KHÔNG suy từ span lệnh
        int windowDays = (int) Math.max(1, (simEnd - simStart) / Utils.TIME_DAY);
        return HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone, windowDays).finalFitness;
    }

    private double getField(String name) throws Exception {
        Field f = Configs.class.getField(name);
        Object v = f.get(null);
        return ((Number) v).doubleValue();
    }

    private void setField(String name, double val, boolean isInt) throws Exception {
        Field f = Configs.class.getField(name);
        if (isInt) f.setInt(null, (int) Math.round(val));
        else f.setFloat(null, (float) val);
    }
}
