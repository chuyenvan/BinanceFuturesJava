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
 * TASK (2026-08-01) — CHAY LAI phan RATCHET voi METRIC DA VA. Thay {@code RatchetDecoupleSweepProbe}
 * va phan multiplier cua ban cu, vi ca 2 deu xep hang bang {@code ddPct}/{@code calmar} HONG va
 * {@code pnl} chua tach mark-to-market (xem EXIT_SWEEP PHAN 6 + INFRA_FACTS).
 *
 * <p>Sua so voi ban cu:
 * <ul>
 *   <li>Xep hang theo {@code pnlTotal = pnlClosed + pnlMtm} (khong tu thuong cho viec giau lo trong
 *       vi the chua dong).</li>
 *   <li>Rui ro doc bang {@code ddPctMtm} (maxDD mark-to-market that) + marginCall + minEquity.</li>
 *   <li>Funding BAT (env SIM_APPLY_FUNDING=true).</li>
 *   <li>Chay tren FOLD ROI (SWEEP_PERIODS) thay vi period long nhau.</li>
 *   <li>In counter audit F8/F9 moi dong.</li>
 * </ul>
 *
 * <p>Env: SWEEP_RATE_MIN (mac dinh 0.05 = gia tri da chot o buoc 1),
 *         SWEEP_MULTIPLIERS (CSV; gia tri &lt;=0 nghia la BAT TS_RATCHET_DECOUPLED = bo he so nhan),
 *         SWEEP_PERIODS (name:start:end,...).
 */
public class RatchetSweepV2Probe {
    private static final Logger LOG = LoggerFactory.getLogger(RatchetSweepV2Probe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());
        LOG.info("APPLY_FUNDING_FEE={} TS_CARRY_SL_ON_DCA={} SIM_TREAT_ZERO_VOL_AS_DELIST={} BLOCK_INTRABAR_LOOKAHEAD={}",
                Configs.APPLY_FUNDING_FEE, Configs.TS_CARRY_SL_ON_DCA,
                Configs.SIM_TREAT_ZERO_VOL_AS_DELIST, Configs.BLOCK_INTRABAR_LOOKAHEAD);

        String rmEnv = System.getenv("SWEEP_RATE_MIN");
        float rateMin = (rmEnv != null && !rmEnv.isEmpty()) ? Float.parseFloat(rmEnv.trim()) : 0.05f;

        String mEnv = System.getenv("SWEEP_MULTIPLIERS");
        float[] mults;
        if (mEnv != null && !mEnv.isEmpty()) {
            String[] p = mEnv.split(",");
            mults = new float[p.length];
            for (int i = 0; i < p.length; i++) mults[i] = Float.parseFloat(p[i].trim());
        } else {
            mults = new float[]{-1f, 1.0f, 2.0f, 3.0f, 5.21847f, 8.0f, 12.0f};
        }

        String pEnv = System.getenv("SWEEP_PERIODS");
        String[][] periods;
        if (pEnv != null && !pEnv.isEmpty()) {
            String[] items = pEnv.split(",");
            periods = new String[items.length][3];
            for (int i = 0; i < items.length; i++) {
                String[] q = items[i].trim().split(":");
                periods[i][0] = q[0]; periods[i][1] = q[1]; periods[i][2] = q[2];
            }
        } else {
            periods = new String[][]{{"lien_tuc", "20210101", "20260501"}};
        }

        float savedRate = Configs.RATE_PROFIT_STOP_MARKET;
        float savedMult = Configs.TS_PROFIT_MULTIPLIER;
        boolean savedDec = Configs.TS_RATCHET_DECOUPLED;
        Configs.RATE_PROFIT_STOP_MARKET = rateMin;
        LOG.info("rate-min CO DINH = {} | sweep {} muc multiplier | {} period", rateMin, mults.length, periods.length);

        for (String[] pr : periods) {
            long from = Utils.sdfFile.parse(pr[1]).getTime() + 7 * Utils.TIME_HOUR;
            long to = Utils.sdfFile.parse(pr[2]).getTime() + 7 * Utils.TIME_HOUR;
            int windowDays = (int) Math.max(1, (to - from) / Utils.TIME_DAY);
            for (float mult : mults) {
                boolean decoupled = mult <= 0f;
                Configs.TS_RATCHET_DECOUPLED = decoupled;
                if (!decoupled) Configs.TS_PROFIT_MULTIPLIER = mult;

                BudgetManagerSimple.resetInstance();
                HistoryManager.getInstance().resetCache();
                CoinRankManager.getInstance().resetCache();
                AIRejectFilter.resetCounters();
                SimulatorMarketLevelTicker1MStopLoss.resetAuditCounters();
                SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
                sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
                sim.simulatorWithInitEntry(from, to);
                HPOFitnessCalculatorV4.FitnessReport rep =
                        HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone, windowDays);

                int nMtm = 0, nClosed = 0, over7d = 0;
                double pnlMtm = 0, pnlClosed = 0;
                java.util.List<Double> holds = new java.util.ArrayList<>();
                for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
                    Float tp = o.calTp();
                    if (o.status == com.binance.chuyennd.trading.OrderTargetStatus.REQUEST) {
                        nMtm++; pnlMtm += (tp != null ? tp : 0f);
                    } else {
                        nClosed++; pnlClosed += (tp != null ? tp : 0f);
                    }
                    if (o.marketLevelChange != MarketLevelChange.PREDICT_SYMBOL_TRADE) continue;
                    double h = (o.timeUpdate - o.timeStart) / 60000.0;
                    holds.add(h);
                    if (h > 7 * 24 * 60) over7d++;
                }
                java.util.Collections.sort(holds);
                double holdMed = holds.isEmpty() ? 0
                        : (holds.size() % 2 == 1 ? holds.get(holds.size()/2)
                        : (holds.get(holds.size()/2 - 1) + holds.get(holds.size()/2)) / 2.0);
                double pctOver7d = holds.isEmpty() ? 0 : 100.0 * over7d / holds.size();
                Float fundTot = BudgetManagerSimple.getInstance().totalFundingFee;
                String tag = decoupled ? "DECOUPLED" : String.format("%.5f", mult);
                double ratchetAt = decoupled ? rateMin * 100 : mult * rateMin * 100;

                if (SimulatorMarketLevelTicker1MStopLoss.orderKeyCollisions > 0
                        || SimulatorMarketLevelTicker1MStopLoss.dayDataErrors > 0
                        || SimulatorMarketLevelTicker1MStopLoss.swallowedExceptions > 0) {
                    LOG.error("⚠️ AUDIT mult={} period={} -> {}", tag, pr[0],
                            SimulatorMarketLevelTicker1MStopLoss.auditCountersSummary());
                }
                LOG.info(String.format(
                        "%-12s mult=%-10s ratchet=%6.2f%% | total %10.1f = closed %10.1f + mtm %9.1f (%d lenh) | ddMtm %6.2f%% minEq %6.1f%% MC=%s | hold %8.1f %%>7d %5.1f%% | fund %8.1f | trades %d",
                        pr[0], tag, ratchetAt, pnlClosed + pnlMtm, pnlClosed, pnlMtm, nMtm,
                        rep.ddPctMtm * 100, rep.minEquityMtmPct * 100, rep.marginCallHit,
                        holdMed, pctOver7d, (fundTot != null ? fundTot : 0f), rep.tradeCount));
                LOG.info(String.format("CSVROW,%s,%s,%s,%d,%.2f,%d,%.2f,%d,%.2f,%.4f,%.4f,%.4f,%s,%.1f,%.2f,%.2f,%d,%d,%d",
                        tag, pr[0], String.format("%.5f", rateMin), rep.tradeCount, (float)(pnlClosed + pnlMtm),
                        nClosed, pnlClosed, nMtm, pnlMtm,
                        rep.ddPct, rep.ddPctMtm, rep.minEquityMtmPct, rep.marginCallHit,
                        holdMed, pctOver7d, (fundTot != null ? fundTot : 0f),
                        SimulatorMarketLevelTicker1MStopLoss.orderKeyCollisions,
                        SimulatorMarketLevelTicker1MStopLoss.dayDataErrors,
                        SimulatorMarketLevelTicker1MStopLoss.swallowedExceptions));
            }
            LOG.info("  ----");
        }
        Configs.RATE_PROFIT_STOP_MARKET = savedRate;
        Configs.TS_PROFIT_MULTIPLIER = savedMult;
        Configs.TS_RATCHET_DECOUPLED = savedDec;
        LOG.info("========== HET RATCHET-SWEEP-V2 (rateMin={}) ==========", rateMin);
        System.exit(0);
    }
}
