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
 * SWEEP HARD_SL_PCT — hard stop-loss tinh tren GIA ENTRY DAU TIEN (firstEntryPrice, bat bien qua DCA).
 *
 * <p>Mirror {@link Mom15SweepProbe}: giu MOI tham so khac baseline, chi doi Configs.HARD_SL_PCT moi vong.
 * sl=0 = OFF = baseline (byte-identical) -> hang dau moi period la doi chung. Sweep de do:
 *   - hard-SL cat lo som co giam maxDD/margin-call ma khong giet PnL khong?
 *   - nguong nao (20/30/40%) danh doi DD<->PnL tot nhat qua nhieu regime?
 *
 * <p>MOI moc `to` <= 20251231 (KHONG dung 20260101 — thieu ticker 2026 gay fail-fast).
 */
public class HardSlSweepProbe {
    private static final Logger LOG = LoggerFactory.getLogger(HardSlSweepProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());
        LOG.info("baseline HARD_SL_PCT={}", Configs.HARD_SL_PCT);

        float[] sl = {0f, 0.20f, 0.30f, 0.40f};
        String[][] periods = {
            {"2023Q4_zero", "20231001", "20240101"},
            {"2024Q1_zero", "20240101", "20240401"},
            {"2025Q2_zero", "20250401", "20250701"},
            {"2025Q4_succ", "20251001", "20251231"},
        };

        float saved = Configs.HARD_SL_PCT;
        LOG.info(String.format("%-14s %8s %8s %10s %8s %10s %8s %8s %8s %6s",
                "period", "slPct", "trades", "pnl", "ddPct%", "maxDDMtm", "calmar", "sortino", "posYr%", "mCall"));
        for (String[] pr : periods) {
            long from = Utils.sdfFile.parse(pr[1]).getTime() + 7 * Utils.TIME_HOUR;
            long to = Utils.sdfFile.parse(pr[2]).getTime() + 7 * Utils.TIME_HOUR;
            int windowDays = (int) Math.max(1, (to - from) / Utils.TIME_DAY);
            for (float s : sl) {
                Configs.HARD_SL_PCT = s;
                BudgetManagerSimple.resetInstance();
                HistoryManager.getInstance().resetCache();
                CoinRankManager.getInstance().resetCache();
                AIRejectFilter.resetCounters();
                SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
                sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
                sim.simulatorWithInitEntry(from, to);
                HPOFitnessCalculatorV4.FitnessReport rep =
                        HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone, windowDays);
                LOG.info(String.format("%-14s %8.2f %8d %10.1f %8.1f %10.1f %8.3f %8.3f %8.0f %6s",
                        pr[0], s, rep.tradeCount, rep.totalProfit, rep.ddPct * 100,
                        rep.maxDDMtm, rep.calmar, rep.sortino, rep.posYearRatio * 100, rep.marginCallHit));
            }
            LOG.info("  ----");
        }
        Configs.HARD_SL_PCT = saved;
        LOG.info("========== HET SWEEP ==========");
    }
}
