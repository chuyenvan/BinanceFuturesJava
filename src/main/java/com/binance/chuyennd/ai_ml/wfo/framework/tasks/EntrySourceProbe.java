package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
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
 * TASK-134 — ĐO đóng góp funding-selector (PREDICT_SYMBOL_TRADE) vs bắt-đáy (BIG_DOWN).
 * Chạy backtest trên vài khoảng đại diện, đếm entry theo nguồn + số coin funding bị gate reject.
 * Dùng CONFIG BASELINE hiện tại (không tối ưu genome) — mục đích đo CƠ CHẾ, không đo hiệu năng.
 */
public class EntrySourceProbe {
    private static final Logger LOG = LoggerFactory.getLogger(EntrySourceProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset_wf");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());
        LOG.info("CONFIG: MIN_MOM15M={} PRED_MAX_THRES={} FILTER_MODE={} OFF_FLAT_HARD={}",
                Configs.MIN_MOMENTUM_15M, Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD, "A", true);

        // các khoảng: [nhãn, từ, đến]
        String[][] periods = {
            {"2025Q2_phang_w13", "20250401", "20250701"},
            {"2024Q2_thi_truong_thuong", "20240401", "20240701"},
            {"2022_crash_LUNA_FTT", "20220101", "20221231"},
            {"toan_ky_2021_2026", "20210101", "20260501"},
        };

        for (String[] pr : periods) {
            long from = Utils.sdfFile.parse(pr[1]).getTime() + 7 * Utils.TIME_HOUR;
            long to = Utils.sdfFile.parse(pr[2]).getTime() + 7 * Utils.TIME_HOUR;

            BudgetManagerSimple.resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();
            AIRejectFilter.resetCounters();

            SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
            sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
            sim.simulatorWithInitEntry(from, to);

            long totalEntry = sim.entryBigDown + sim.entryPredictSymbol + sim.entryDcaLevel + sim.entryOther;
            LOG.info("========== {} ({}..{}) ==========", pr[0], pr[1], pr[2]);
            LOG.info("  legEntry: BIG_DOWN={} PREDICT_SYMBOL={} DCA={} other={} | TỔNG={}",
                    sim.entryBigDown, sim.entryPredictSymbol, sim.entryDcaLevel, sim.entryOther, totalEntry);
            LOG.info("  PREDICT_SYMBOL bị gate REJECT={} | gate MOM15 reject tổng={}",
                    sim.predictSymbolRejectedGate, AIRejectFilter.mom15RejectCount.get());
            long predTotal = sim.entryPredictSymbol + sim.predictSymbolRejectedGate;
            if (predTotal > 0) {
                LOG.info("  => funding-selector: {} coin đủ điều kiện, {} PASS ({}%), {} bị gate chặn",
                        predTotal, sim.entryPredictSymbol,
                        String.format("%.1f", 100.0 * sim.entryPredictSymbol / predTotal),
                        sim.predictSymbolRejectedGate);
            }
            if (totalEntry > 0) {
                LOG.info("  => tỉ trọng nguồn: BIG_DOWN {}% | PREDICT_SYMBOL {}% | DCA {}%",
                        String.format("%.1f", 100.0 * sim.entryBigDown / totalEntry),
                        String.format("%.1f", 100.0 * sim.entryPredictSymbol / totalEntry),
                        String.format("%.1f", 100.0 * sim.entryDcaLevel / totalEntry));
            }
        }
        LOG.info("========== HET ==========");
    }
}
