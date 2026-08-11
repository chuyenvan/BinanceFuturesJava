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
 * TASK (2026-07-31, EXIT_SWEEP): sweep TS_PROFIT_MULTIPLIER — he so quyet dinh NGUONG RATCHET.
 *
 * <p>VAN DE (Uni chi ra): ratchet threshold = TS_PROFIT_MULTIPLIER x rate-min-base, tuc no la HE SO
 * NHAN chu khong phai nguong doc lap. 5.21847 duoc tune cho rate-min = 0.0103 (=> ratchet 5.4%, dead
 * zone 4.35pp - hop ly). Nhung sau khi nang rate-min len 0.045 vi ly do CHI PHI, ratchet tu dong
 * phinh len 5.21847 x 0.045 = 23.5% (dead zone 19pp) - gan nhu KHONG lenh nao cham toi => trailing
 * that su KHONG BAO GIO chay, moi lenh thoat o muc SL dong bang ~arm x giveback (~2.5%).
 *
 * <p>Da biet 2 dau mut: multiplier = 1.0 (tuong duong TS_RATCHET_DECOUPLED=true) thua 4.8% tai
 * rate-min 0.03; multiplier = 5.21847 (hien tai) lam ratchet gan nhu chet. Khoang 1.5-3 CHUA DO.
 *
 * <p>Env: SWEEP_RATE_MIN (mac dinh 0.045), SWEEP_MULTIPLIERS (CSV, mac dinh "1.0,1.5,2.0,3.0,5.21847").
 */
public class TsMultiplierSweepProbe {
    private static final Logger LOG = LoggerFactory.getLogger(TsMultiplierSweepProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());

        String rmEnv = System.getenv("SWEEP_RATE_MIN");
        float rateMin = (rmEnv != null && !rmEnv.isEmpty()) ? Float.parseFloat(rmEnv.trim()) : 0.045f;

        String mEnv = System.getenv("SWEEP_MULTIPLIERS");
        float[] sweep;
        if (mEnv != null && !mEnv.isEmpty()) {
            String[] parts = mEnv.split(",");
            sweep = new float[parts.length];
            for (int i = 0; i < parts.length; i++) sweep[i] = Float.parseFloat(parts[i].trim());
        } else {
            sweep = new float[]{1.0f, 1.5f, 2.0f, 3.0f, 5.21847f};
        }

        String[][] periods = {
            {"2024_bull", "20240101", "20241231"},
            {"2025Q4_crash", "20251001", "20260101"},
            {"toan_ky", "20210101", "20260501"},
        };

        float savedRate = Configs.RATE_PROFIT_STOP_MARKET;
        float savedMult = Configs.TS_PROFIT_MULTIPLIER;
        Configs.RATE_PROFIT_STOP_MARKET = rateMin;
        LOG.info("rate-min CO DINH = {} | sweep TS_PROFIT_MULTIPLIER = {} phan tu", rateMin, sweep.length);

        LOG.info(String.format("%-14s %8s %10s %8s %10s %8s %8s %10s %10s %10s",
                "period", "mult", "ratchet%", "trades", "pnl", "ddPct%", "calmar", "holdMed",
                "%h>60p", "%h>7d"));
        for (String[] pr : periods) {
            long from = Utils.sdfFile.parse(pr[1]).getTime() + 7 * Utils.TIME_HOUR;
            long to = Utils.sdfFile.parse(pr[2]).getTime() + 7 * Utils.TIME_HOUR;
            int windowDays = (int) Math.max(1, (to - from) / Utils.TIME_DAY);
            for (float mult : sweep) {
                Configs.TS_PROFIT_MULTIPLIER = mult;
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
                int over60 = 0, over7d = 0;
                for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
                    if (o.marketLevelChange != MarketLevelChange.PREDICT_SYMBOL_TRADE) continue;
                    double h = (o.timeUpdate - o.timeStart) / 60000.0;
                    holds.add(h);
                    if (h > 60) over60++;
                    if (h > 7 * 24 * 60) over7d++;
                }
                double holdMed = median(holds);
                double pctOver60 = holds.isEmpty() ? 0 : 100.0 * over60 / holds.size();
                double pctOver7d = holds.isEmpty() ? 0 : 100.0 * over7d / holds.size();
                LOG.info(String.format("%-14s %8.5f %9.2f%% %8d %10.1f %8.1f %8.3f %10.1f %9.1f%% %9.1f%%",
                        pr[0], mult, mult * rateMin * 100, rep.tradeCount, rep.totalProfit,
                        rep.ddPct * 100, rep.calmar, holdMed, pctOver60, pctOver7d));
            }
            LOG.info("  ----");
        }
        Configs.RATE_PROFIT_STOP_MARKET = savedRate;
        Configs.TS_PROFIT_MULTIPLIER = savedMult;
        LOG.info("========== HET TS-MULTIPLIER SWEEP (rateMin={}) ==========", rateMin);
        System.exit(0);
    }

    private static double median(java.util.List<Double> a) {
        if (a.isEmpty()) return 0;
        java.util.List<Double> c = new java.util.ArrayList<>(a);
        java.util.Collections.sort(c);
        int m = c.size() / 2;
        return c.size() % 2 == 1 ? c.get(m) : (c.get(m - 1) + c.get(m)) / 2;
    }
}
