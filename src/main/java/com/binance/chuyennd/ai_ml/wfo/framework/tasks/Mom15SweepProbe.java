package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV4;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * TASK-135 — SWEEP MIN_MOMENTUM_15M (giữ mọi tham số khác baseline).
 *
 * <p>Mục đích: gate MOM15 lọc đúng (A/B đã chứng minh), nhưng WFO gene range [0.030,0.050] có thể đẩy
 * ngưỡng lên cực đoan → giết cơ hội tốt. Baseline 0.0228 tốt hơn ở 2025Q2. Sweep để tìm:
 *   - ngưỡng nào tối đa PnL/calmar robust QUA NHIỀU KHOẢNG (không chỉ 1 regime)?
 *   - cận trên gene 0.050 có phải vùng "over-tighten" (PnL rơi vì trade quá ít)?
 *
 * <p>Chạy trên NHIỀU khoảng độc lập + toàn kỳ. Config baseline, chỉ đổi MIN_MOMENTUM_15M.
 */
public class Mom15SweepProbe {
    private static final Logger LOG = LoggerFactory.getLogger(Mom15SweepProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());
        LOG.info("baseline MIN_MOMENTUM_15M={}", Configs.MIN_MOMENTUM_15M);

        float[] sweep = {0.010f, 0.0150f, 0.0228f, 0.030f, 0.040f, 0.050f, 0.070f};
        String[][] periods = {
            {"2023_hoi_phuc", "20230101", "20231231"},
            {"2024_bull", "20240101", "20241231"},
            {"2025Q2_phang", "20250401", "20250701"},
            {"toan_ky", "20210101", "20260501"},
        };

        float saved = Configs.MIN_MOMENTUM_15M;
        LOG.info(String.format("%-14s %8s %8s %10s %8s %8s %8s %8s %-8s",
                "period", "min15m", "trades", "pnl", "ddPct%", "calmar", "sortino", "posYr%", "note"));
        for (String[] pr : periods) {
            long from = Utils.sdfFile.parse(pr[1]).getTime() + 7 * Utils.TIME_HOUR;
            long to = Utils.sdfFile.parse(pr[2]).getTime() + 7 * Utils.TIME_HOUR;
            int windowDays = (int) Math.max(1, (to - from) / Utils.TIME_DAY);
            for (float m15 : sweep) {
                Configs.MIN_MOMENTUM_15M = m15;
                BudgetManagerSimple.resetInstance();
                HistoryManager.getInstance().resetCache();
                CoinRankManager.getInstance().resetCache();
                AIRejectFilter.resetCounters();
                SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
                sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
                sim.simulatorWithInitEntry(from, to);
                HPOFitnessCalculatorV4.FitnessReport rep =
                        HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone, windowDays);
                LOG.info(String.format("%-14s %8.4f %8d %10.1f %8.1f %8.3f %8.3f %7.0f %-8s",
                        pr[0], m15, rep.tradeCount, rep.totalProfit, rep.ddPct * 100,
                        rep.calmar, rep.sortino, rep.posYearRatio * 100, rep.note));
            }
            LOG.info("  ----");
        }
        Configs.MIN_MOMENTUM_15M = saved;
        LOG.info("========== HET SWEEP ==========");
    }
}
