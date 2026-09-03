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
 * COUNT-ONLY GROUND TRUTH — dem so candidate PASS gate o cac nguong cung MIN_MOMENTUM_15M.
 *
 * <p>Chay path admission THAT (checkSignalDynamic/checkSignal tren du lieu that), short-circuit
 * ngay sau khi dem (Configs.GATE_COUNT_ONLY) => KHONG tao order/DCA/PnL. Muc dich: do doc lap
 * voi moi doc/test cu (co the dinh bug an chung), tra loi thang "bao nhieu phut/candidate qua gate".
 *
 * <p>Bat: env SIM_GATE_COUNT_ONLY=1, WFO_DATA_DIR=/home/ubuntu/claudedata/wfo_dataset.
 */
public class GatePassCountProbe {
    private static final Logger LOG = LoggerFactory.getLogger(GatePassCountProbe.class);

    public static void main(String[] args) throws Exception {
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset");
        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={} GATE_COUNT_ONLY={} FILTER_MODE={}",
                ds.market.size(), ds.pred.size(), ds.funding.size(),
                Configs.GATE_COUNT_ONLY, "A");

        long from = Utils.sdfFile.parse("20210101").getTime() + 7 * Utils.TIME_HOUR;
        // Option A: bound end tai 2025-12-31 — thieu ticker kaggle_data_hpo/ticker_20260101.bin(.gz)
        // tren Oracle gay FAIL-FAST (SimulatorMarketLevelTicker1MStopLoss:135) khi cham moc 2026.
        long to = Utils.sdfFile.parse("20251231").getTime() + 7 * Utils.TIME_HOUR;

        float[] sweep = {0.03f, 0.0228f, 0.01f, 0.005f, 0.003f};
        float saved = Configs.MIN_MOMENTUM_15M;
        LOG.info(String.format("%-8s %12s %12s %9s %12s %12s %12s",
                "min15m", "seen", "pass", "passPct", "mom15Rej", "earlyRej", "psRej"));
        for (float m15 : sweep) {
            Configs.MIN_MOMENTUM_15M = m15;
            BudgetManagerSimple.resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();
            AIRejectFilter.resetCounters();
            SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
            sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
            sim.simulatorWithInitEntry(from, to);
            long seen = sim.ablationSignalSeen;
            long pass = sim.ablationPassCount;
            double passPct = seen > 0 ? 100.0 * pass / seen : 0.0;
            LOG.info(String.format("%-8.4f %12d %12d %8.3f%% %12d %12d %12d",
                    m15, seen, pass, passPct,
                    AIRejectFilter.mom15RejectCount.get(),
                    AIRejectFilter.earlyHardGateReject.get(),
                    sim.predictSymbolRejectedGate));
        }
        Configs.MIN_MOMENTUM_15M = saved;
        LOG.info("========== HET GATE COUNT ==========");
    }
}
