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
 * TASK (2026-08-01) — sweep CAC LEVER EXIT CHUA TUNG DO, metric dung (pnlTotal + ddPctMtm + funding).
 *
 * <p>Uni chi ra: tran {@code TS_MAX_GAP = 8%} CHUA HE duoc test — moi chi ban ly thuyet o EXIT_MACHINE
 * PHAN 1 ("PHAT HIEN 2: min() dao dau, ti le nha TEO DAN theo lai"). Tuong tu {@code TS_GIVEBACK_RATIO}
 * (quyet dinh muc SL DONG BANG = arm x (1-giveback), noi DA SO lenh thoat) va {@code TS_MAX_GAP_WEAK}.
 *
 * <p>Env:
 * <ul>
 *   <li>{@code SWEEP_PARAM} = MAX_GAP | GIVEBACK | MAX_GAP_WEAK | MIN_GAP (MIN_GAP tu bat
 *       TS_GIVEBACK_FLOOR = doi min(peak*g, maxGap) -> max(peak*g, minGap), bo TRAN them SAN)</li>
 *   <li>{@code SWEEP_VALUES} = CSV gia tri</li>
 *   <li>{@code SWEEP_RATE_MIN} (mac dinh 0.05), {@code SWEEP_MULT} (mac dinh 5.21847)</li>
 *   <li>{@code SWEEP_PERIODS} = name:start:end,...</li>
 * </ul>
 */
public class ExitParamSweepProbe {
    private static final Logger LOG = LoggerFactory.getLogger(ExitParamSweepProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());

        String param = System.getenv().getOrDefault("SWEEP_PARAM", "MAX_GAP").trim().toUpperCase();
        String vEnv = System.getenv("SWEEP_VALUES");
        if (vEnv == null || vEnv.isEmpty()) throw new IllegalStateException("Thieu SWEEP_VALUES");
        String[] vp = vEnv.split(",");
        float[] vals = new float[vp.length];
        for (int i = 0; i < vp.length; i++) vals[i] = Float.parseFloat(vp[i].trim());

        float rateMin = Float.parseFloat(System.getenv().getOrDefault("SWEEP_RATE_MIN", "0.05").trim());
        float mult = Float.parseFloat(System.getenv().getOrDefault("SWEEP_MULT", "5.21847").trim());

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

        Configs.RATE_PROFIT_STOP_MARKET = rateMin;
        Configs.TS_PROFIT_MULTIPLIER = mult;
        LOG.info("SWEEP_PARAM={} | rate-min={} mult={} | {} gia tri x {} period | funding={}",
                param, rateMin, mult, vals.length, periods.length, Configs.APPLY_FUNDING_FEE);

        for (String[] pr : periods) {
            long from = Utils.sdfFile.parse(pr[1]).getTime() + 7 * Utils.TIME_HOUR;
            long to = Utils.sdfFile.parse(pr[2]).getTime() + 7 * Utils.TIME_HOUR;
            int windowDays = (int) Math.max(1, (to - from) / Utils.TIME_DAY);
            for (float v : vals) {
                // reset ve mac dinh truoc moi lan, roi ap dung 1 thay doi duy nhat
                Configs.TS_MAX_GAP = 0.08f;
                Configs.TS_MAX_GAP_WEAK = 0.03f;
                Configs.TS_GIVEBACK_RATIO = 0.5f;
                Configs.TS_GIVEBACK_FLOOR = false;
                switch (param) {
                    case "MAX_GAP":      Configs.TS_MAX_GAP = v; break;
                    case "MAX_GAP_WEAK": Configs.TS_MAX_GAP_WEAK = v; break;
                    case "GIVEBACK":     Configs.TS_GIVEBACK_RATIO = v; break;
                    case "MIN_GAP":      Configs.TS_GIVEBACK_FLOOR = true; Configs.TS_MIN_GAP = v; break;
                    default: throw new IllegalStateException("SWEEP_PARAM khong hop le: " + param);
                }

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
                    } else { nClosed++; pnlClosed += (tp != null ? tp : 0f); }
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

                if (SimulatorMarketLevelTicker1MStopLoss.orderKeyCollisions > 0
                        || SimulatorMarketLevelTicker1MStopLoss.dayDataErrors > 0
                        || SimulatorMarketLevelTicker1MStopLoss.swallowedExceptions > 0) {
                    LOG.error("⚠️ AUDIT {}={} period={} -> {}", param, v, pr[0],
                            SimulatorMarketLevelTicker1MStopLoss.auditCountersSummary());
                }
                LOG.info(String.format("%-12s %s=%-8.4f | total %10.1f = closed %10.1f + mtm %9.1f | ddMtm %6.2f%% | hold %8.1f %%>7d %5.1f%% | trades %d",
                        pr[0], param, v, pnlClosed + pnlMtm, pnlClosed, pnlMtm,
                        rep.ddPctMtm * 100, holdMed, pctOver7d, rep.tradeCount));
                LOG.info(String.format("CSVROW,%s,%.5f,%s,%d,%.2f,%d,%.2f,%d,%.2f,%.4f,%.4f,%.4f,%s,%.1f,%.2f,%.2f,%d,%d,%d",
                        param, v, pr[0], rep.tradeCount, (float)(pnlClosed + pnlMtm),
                        nClosed, pnlClosed, nMtm, pnlMtm,
                        rep.ddPct, rep.ddPctMtm, rep.minEquityMtmPct, rep.marginCallHit,
                        holdMed, pctOver7d, (fundTot != null ? fundTot : 0f),
                        SimulatorMarketLevelTicker1MStopLoss.orderKeyCollisions,
                        SimulatorMarketLevelTicker1MStopLoss.dayDataErrors,
                        SimulatorMarketLevelTicker1MStopLoss.swallowedExceptions));
            }
            LOG.info("  ----");
        }
        LOG.info("========== HET EXIT-PARAM SWEEP param={} ==========", param);
        System.exit(0);
    }
}
