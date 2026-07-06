package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.hpo.HPOFitnessCalculatorV4;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * TASK-139 — Sweep RATE_PROFIT_STOP_MARKET (ngưỡng lãi kích hoạt trailing SL) — giả thuyết Uni:
 * 0.01032 làm trailing kích hoạt QUÁ SỚM → coin pump/dump giật xuống 1-3% là bị quét stop non
 * (median hold 7 phút), tự cắt cụt đuôi phải. Nâng lên ~0.03 cho coin "thở" tới pump thật.
 *
 * <p>Sweep base rate + đo: PnL, #lệnh, calmar, sortino, holding median lệnh PRED, %lệnh giữ >60 phút.
 * Nhiều khoảng độc lập. Config baseline, chỉ đổi RATE_PROFIT_STOP_MARKET.
 * ĐỌC: nếu nâng rate → holding median tăng + PnL/calmar tăng → giả thuyết Uni ĐÚNG (trailing cắt non).
 */
public class TrailingStopSweepProbe {
    private static final Logger LOG = LoggerFactory.getLogger(TrailingStopSweepProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());
        LOG.info("baseline RATE_PROFIT_STOP_MARKET={} TS_MAX_GAP={} TS_MAX_GAP_WEAK={}",
                Configs.RATE_PROFIT_STOP_MARKET, Configs.TS_MAX_GAP, Configs.TS_MAX_GAP_WEAK);

        float[] sweep = {0.01032f, 0.02032f, 0.03032f, 0.04032f, 0.05032f};
        String[][] periods = {
            {"2024_bull", "20240101", "20241231"},
            {"2025Q2_phang", "20250401", "20250701"},
            {"toan_ky", "20210101", "20260501"},
        };
        float saved = Configs.RATE_PROFIT_STOP_MARKET;

        LOG.info(String.format("%-14s %8s %8s %10s %8s %8s %8s %10s %10s",
                "period", "rateTS", "trades", "pnl", "ddPct%", "calmar", "sortino", "holdMed", "%hold>60p"));
        for (String[] pr : periods) {
            long from = Utils.sdfFile.parse(pr[1]).getTime() + 7 * Utils.TIME_HOUR;
            long to = Utils.sdfFile.parse(pr[2]).getTime() + 7 * Utils.TIME_HOUR;
            int windowDays = (int) Math.max(1, (to - from) / Utils.TIME_DAY);
            for (float ts : sweep) {
                Configs.RATE_PROFIT_STOP_MARKET = ts;
                BudgetManagerSimple.resetInstance();
                HistoryManager.getInstance().resetCache();
                CoinRankManager.getInstance().resetCache();
                AIRejectFilter.resetCounters();
                SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
                sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
                sim.simulatorWithInitEntry(from, to);
                HPOFitnessCalculatorV4.FitnessReport rep =
                        HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone, windowDays);
                // holding median + %hold>60p cho lệnh PRED
                java.util.List<Double> holds = new java.util.ArrayList<>();
                int over60 = 0;
                for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
                    if (o.marketLevelChange != MarketLevelChange.PREDICT_SYMBOL_TRADE) continue;
                    double h = (o.timeUpdate - o.timeStart) / 60000.0;
                    holds.add(h);
                    if (h > 60) over60++;
                }
                double holdMed = median(holds);
                double pctOver60 = holds.isEmpty() ? 0 : 100.0 * over60 / holds.size();
                LOG.info(String.format("%-14s %8.5f %8d %10.1f %8.1f %8.3f %8.3f %10.1f %9.1f%%",
                        pr[0], ts, rep.tradeCount, rep.totalProfit, rep.ddPct * 100,
                        rep.calmar, rep.sortino, holdMed, pctOver60));
            }
            LOG.info("  ----");
        }
        Configs.RATE_PROFIT_STOP_MARKET = saved;
        LOG.info("========== HET TS-SWEEP ==========");
    }

    private static double median(java.util.List<Double> a) {
        if (a.isEmpty()) return 0;
        java.util.List<Double> c = new java.util.ArrayList<>(a);
        java.util.Collections.sort(c);
        int m = c.size() / 2;
        return c.size() % 2 == 1 ? c.get(m) : (c.get(m-1) + c.get(m)) / 2;
    }
}
