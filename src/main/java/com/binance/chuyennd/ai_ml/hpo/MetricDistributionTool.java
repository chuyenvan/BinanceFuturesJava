package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * TASK-043 — ĐO PHÂN PHỐI METRIC THẬT (đo không đoán) trước khi đặt ngưỡng constraint cho fitness V4.
 *
 * <p>Chạy 1 backtest (gate cũ hoặc gate v2 qua env GATE_SET) rồi in phân phối:
 * <ul>
 *   <li>holding-time mỗi lệnh: median/p90/p99 (ngày) → đặt ngưỡng giam vốn.</li>
 *   <li>maxDD% toàn danh mục → đặt ngưỡng cháy.</li>
 *   <li>Calmar (netPnl/maxDD), Sortino (theo return ngày) → xem số thật của 2 ứng viên mục tiêu.</li>
 *   <li>PnL theo năm (proxy fold) → xem độ ổn định qua thời gian.</li>
 * </ul>
 *
 * <p>KHÔNG quyết định gì — chỉ ĐO + IN. Ngưỡng do người đặt sau khi xem số.
 * Chạy trên 226/Oracle. Mode = FAST | FULL. Env GATE_SET (mặc định set gate cũ).
 */
public class MetricDistributionTool {

    private static final Logger LOG = LoggerFactory.getLogger(MetricDistributionTool.class);
    private static final String FAST_START = "20251001", FAST_END = "20260430";
    private static final String FULL_START = "20210101", FULL_END = "20260601";

    public static void main(String[] args) {
        try {
            Configs.IS_HPO_MODE = false;
            Configs.IS_KAGGLE_MODE = false;
            Configs.BREAKER_MODE = "OFF";
            String mode = args.length > 0 ? args[0] : "FAST";
            new MetricDistributionTool().run(mode);
            System.exit(0);
        } catch (Exception e) {
            LOG.error("❌ MetricDistributionTool lỗi", e);
            System.exit(1);
        }
    }

    void run(String mode) throws Exception {
        String start = mode.equalsIgnoreCase("FULL") ? FULL_START : FAST_START;
        String end = mode.equalsIgnoreCase("FULL") ? FULL_END : FAST_END;
        long s = Utils.sdfFile.parse(start).getTime() + 7 * Utils.TIME_HOUR;
        long e = Utils.sdfFile.parse(end).getTime() + 24 * Utils.TIME_HOUR - Utils.TIME_MINUTE;

        String gateSet = System.getenv("GATE_SET");
        LOG.info("📥 Nạp data (gateSet={})...", gateSet == null ? "[gate cũ mặc định]" : gateSet);
        TreeMap<Long, MarketDataObject> mkt = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> pred = (gateSet != null && !gateSet.isBlank())
                ? DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospikeSet(gateSet)
                : DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> fund = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("✅ market={} pred={} funding={}", mkt.size(), pred.size(), fund.size());

        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(mkt, pred, fund, new AIRejectFilter());
        sim.simulatorWithInitEntry(s, e);

        analyze(sim.allOrderDone);
    }

    private void analyze(TreeMap<Long, OrderTargetInfoTest> done) {
        if (done == null || done.isEmpty()) { LOG.error("⛔ 0 order — không đo được."); return; }
        Collection<OrderTargetInfoTest> orders = done.values();
        int n = orders.size();

        // 1. holding-time (ngày) mỗi lệnh
        double[] holdDays = new double[n];
        double totalPnl = 0;
        Map<Integer, Double> pnlByYear = new TreeMap<>();
        int i = 0;
        for (OrderTargetInfoTest o : orders) {
            holdDays[i++] = (o.timeUpdate - o.timeStart) / (double) Utils.TIME_DAY;
            double tp = o.calTp();
            totalPnl += tp;
            pnlByYear.merge(Utils.getYear(o.timeUpdate), tp, Double::sum);
        }
        Arrays.sort(holdDays);

        // 2. maxDD
        Float ddRaw = BudgetManagerSimple.getInstance().balanceIndex.unProfitMin;
        float maxDD = ddRaw != null ? Math.abs(ddRaw) : 0f;
        float capital = BudgetManagerSimple.getInstance().balanceBasic;
        double ddPct = capital > 0 ? maxDD / capital : 0;

        // 3. Calmar (netPnl/maxDD)
        double calmar = maxDD > 1 ? totalPnl / maxDD : 0;

        // 4. Sortino: chuỗi return THEO NGÀY của danh mục (xấp xỉ từ pnl đóng lệnh theo ngày)
        TreeMap<Long, Double> pnlByDay = new TreeMap<>();
        for (OrderTargetInfoTest o : orders) {
            long day = o.timeUpdate / Utils.TIME_DAY;
            pnlByDay.merge(day, (double) o.calTp(), Double::sum);
        }
        double meanDaily = pnlByDay.values().stream().mapToDouble(x -> x).average().orElse(0);
        double downsideVar = 0; int downN = 0;
        for (double r : pnlByDay.values()) if (r < 0) { downsideVar += r * r; downN++; }
        double downsideDev = downN > 0 ? Math.sqrt(downsideVar / downN) : 0;
        double sortino = downsideDev > 1e-9 ? meanDaily / downsideDev : 0;

        // ===== IN =====
        LOG.info("================ PHÂN PHỐI METRIC ({} lệnh) ================", n);
        LOG.info("HOLDING-TIME (ngày): median={} p75={} p90={} p99={} max={}",
                f(pct(holdDays, 50)), f(pct(holdDays, 75)), f(pct(holdDays, 90)), f(pct(holdDays, 99)), f(holdDays[n-1]));
        LOG.info("  → giam vốn: %lệnh giữ >3d={}%  >7d={}%  >14d={}%",
                f(pctOver(holdDays, 3)), f(pctOver(holdDays, 7)), f(pctOver(holdDays, 14)));
        LOG.info("PnL tổng={} | maxDD={} ({}% vốn) | vốn nền={}",
                f(totalPnl), f(maxDD), f(ddPct * 100), f(capital));
        LOG.info("MỤC TIÊU ứng viên: Calmar(netPnl/maxDD)={} | Sortino(daily)={}", f(calmar), f(sortino));
        LOG.info("PnL THEO NĂM (proxy fold — xem ổn định):");
        pnlByYear.forEach((y, p) -> LOG.info("  {}: {}", y, f(p)));
        long posYears = pnlByYear.values().stream().filter(x -> x > 0).count();
        LOG.info("  → {}/{} năm dương ({}%)", posYears, pnlByYear.size(),
                f(100.0 * posYears / pnlByYear.size()));
        LOG.info("===========================================================");

        // ===== Verdict fitness V4 trên CHÍNH backtest này (kiểm chứng V4 chạy đúng) =====
        HPOFitnessCalculatorV4.FitnessReport v4 = HPOFitnessCalculatorV4.evaluateDetailed(done);
        LOG.info("FITNESS V4: note={} finalFitness={} | calmar={} sortino={} ddPct={}% pctHeld>7d={}% posYear={}%",
                v4.note, f(v4.finalFitness), f(v4.calmar), f(v4.sortino),
                f(v4.ddPct * 100), f(v4.pctHeldOver7d * 100), f(v4.posYearRatio * 100));
        LOG.info("===========================================================");
    }

    private static double pct(double[] sorted, double p) {
        if (sorted.length == 0) return 0;
        double idx = p / 100.0 * (sorted.length - 1);
        int lo = (int) Math.floor(idx), hi = (int) Math.ceil(idx);
        if (lo == hi) return sorted[lo];
        return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
    }
    private static double pctOver(double[] sorted, double thr) {
        int c = 0; for (double v : sorted) if (v > thr) c++;
        return 100.0 * c / sorted.length;
    }
    private static String f(double v) { return String.format(Locale.US, "%.2f", v); }
}
