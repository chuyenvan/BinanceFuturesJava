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
 * TASK (2026-07-31, EXIT_MACHINE): so sanh truc tiep TS_RATCHET_DECOUPLED true/false (KHONG qua
 * WFO/HPO/argmax/verdict M — theo yeu cau Uni: harness dang co van de (fitness Calmar-vs-WFE
 * mismatch, HPO argmax), nen so sanh so THO (PnL/maxDD/calmar/holdMed) truoc, khong quy ve pass/fail.
 *
 * <p>CHAY SAU KHI da chon xong RATE_PROFIT_STOP_MARKET (viec 1) — truyen gia tri da chon qua env
 * SWEEP_RATE_MIN (mac dinh = Configs.RATE_PROFIT_STOP_MARKET hien tai = 0.03). Y nghia: viec 2
 * (ratchet dead-zone) PHU THUOC viec 1 (ratchet threshold = 5.21847 x rate-min-base), nen phai co
 * rate-min truoc roi moi so sanh true/false co y nghia.
 *
 * <p>Cung 4 giai doan nhu TrailingStopSweepProbe (2024_bull, 2025Q2_phang, 2025Q4_crash rieng de lo
 * ro anh huong black-swan 10/10-11/10/2025, toan_ky).
 */
public class RatchetDecoupleSweepProbe {
    private static final Logger LOG = LoggerFactory.getLogger(RatchetDecoupleSweepProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());

        String rateMinEnv = System.getenv("SWEEP_RATE_MIN");
        float rateMin = rateMinEnv != null && !rateMinEnv.isEmpty()
                ? Float.parseFloat(rateMinEnv.trim()) : Configs.RATE_PROFIT_STOP_MARKET;
        LOG.info("RATE_PROFIT_STOP_MARKET co dinh cho sweep nay = {} (viec 1 da chon, truyen qua SWEEP_RATE_MIN neu can doi)", rateMin);

        // env SWEEP_DECOUPLED (CSV true/false) override -> chay 1 gia tri/1 process, song song 2 core.
        String decEnv = System.getenv("SWEEP_DECOUPLED");
        boolean[] sweep;
        if (decEnv != null && !decEnv.isEmpty()) {
            String[] parts = decEnv.split(",");
            sweep = new boolean[parts.length];
            for (int i = 0; i < parts.length; i++) sweep[i] = Boolean.parseBoolean(parts[i].trim());
        } else {
            sweep = new boolean[]{false, true};
        }
        String[][] periods = {
            {"2024_bull", "20240101", "20241231"},
            {"2025Q2_phang", "20250401", "20250701"},
            {"2025Q4_crash", "20251001", "20260101"},
            {"toan_ky", "20210101", "20260501"},
        };
        float savedRate = Configs.RATE_PROFIT_STOP_MARKET;
        Configs.RATE_PROFIT_STOP_MARKET = rateMin;

        LOG.info(String.format("%-14s %8s %8s %10s %8s %8s %8s %10s %10s",
                "period", "decoupled", "trades", "pnl", "ddPct%", "calmar", "sortino", "holdMed", "%hold>60p"));
        for (String[] pr : periods) {
            long from = Utils.sdfFile.parse(pr[1]).getTime() + 7 * Utils.TIME_HOUR;
            long to = Utils.sdfFile.parse(pr[2]).getTime() + 7 * Utils.TIME_HOUR;
            int windowDays = (int) Math.max(1, (to - from) / Utils.TIME_DAY);
            for (boolean decoupled : sweep) {
                Configs.TS_RATCHET_DECOUPLED = decoupled;
                BudgetManagerSimple.resetInstance();
                HistoryManager.getInstance().resetCache();
                CoinRankManager.getInstance().resetCache();
                AIRejectFilter.resetCounters();
                SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
                sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
                sim.simulatorWithInitEntry(from, to);
                HPOFitnessCalculatorV4.FitnessReport rep =
                        HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone, windowDays);
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
                LOG.info(String.format("%-14s %8s %8d %10.1f %8.1f %8.3f %8.3f %10.1f %9.1f%%",
                        pr[0], decoupled, rep.tradeCount, rep.totalProfit, rep.ddPct * 100,
                        rep.calmar, rep.sortino, holdMed, pctOver60));
            }
            LOG.info("  ----");
        }
        Configs.RATE_PROFIT_STOP_MARKET = savedRate;
        LOG.info("========== HET RATCHET-DECOUPLE SWEEP (rateMin={}) ==========", rateMin);
        System.exit(0); // xem ghi chu trong TrailingStopSweepProbe (non-daemon thread treo JVM).
    }

    private static double median(java.util.List<Double> a) {
        if (a.isEmpty()) return 0;
        java.util.List<Double> c = new java.util.ArrayList<>(a);
        java.util.Collections.sort(c);
        int m = c.size() / 2;
        return c.size() % 2 == 1 ? c.get(m) : (c.get(m-1) + c.get(m)) / 2;
    }
}
