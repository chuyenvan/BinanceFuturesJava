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
 * BƯỚC 2 (ROADMAP) — Ablation: edge đến từ AI hay từ DCA?
 *
 * <p>Chạy 3 bản CÙNG mọi thứ (data/seed/range), chỉ khác cổng entry leg-đầu (Configs.ABLATION_MODE):
 * <ul>
 *   <li><b>A = control</b>: AI filter bật như thường.</li>
 *   <li><b>B = no-AI</b>: bỏ qua filter (mọi tín hiệu PASS) → đo DCA tự cõng được bao nhiêu.</li>
 *   <li><b>C = placebo</b>: PASS ngẫu nhiên CÙNG xác suất pass thực nghiệm của A (cùng số vị thế kỳ vọng)
 *       → tách "đúng nhờ chọn lọc" khỏi "đúng nhờ vào ít lệnh hơn".</li>
 * </ul>
 *
 * <p>So ở mức cụm/leg-đầu, KHÔNG chỉ tổng: avgMAE, worstMAE (đáy lỗ tạm sâu nhất / entry — nông hơn = AI
 * tránh được entry tệ), firstLegPnl, totalPnl, maxDD, Calmar (qua V4). PHÁN QUYẾT pre-register:
 * AI có edge ⇔ A có MAE NÔNG hơn + Calmar CAO hơn C ở cùng số vị thế. A≈C → AI vô dụng, DCA cõng.
 *
 * <p>"Đo không đoán": chạy FULL nhiều regime (long-only tự đẹp trong uptrend → 1 cửa sổ kết luận sai).
 * Chạy Oracle. Mode arg = FAST | FULL.
 */
public class AblationStep2Tool {

    private static final Logger LOG = LoggerFactory.getLogger(AblationStep2Tool.class);
    private static final String FAST_START = "20251001", FAST_END = "20260430";
    private static final String FULL_START = "20210101", FULL_END = "20260601";

    static class Result {
        String mode; int trades; double totalPnl, maxDD, avgMAE, worstMAE, calmar;
        long signalSeen, passCount; double passRate;
    }

    public static void main(String[] args) {
        try {
            Configs.IS_HPO_MODE = false;
            Configs.IS_KAGGLE_MODE = false;
            Configs.BREAKER_MODE = "OFF";
            String mode = args.length > 0 ? args[0] : "FAST";
            new AblationStep2Tool().run(mode);
            System.exit(0);
        } catch (Exception e) {
            LOG.error("❌ AblationStep2Tool lỗi", e);
            System.exit(1);
        }
    }

    void run(String mode) throws Exception {
        String start = mode.equalsIgnoreCase("FULL") ? FULL_START : FAST_START;
        String end = mode.equalsIgnoreCase("FULL") ? FULL_END : FAST_END;
        long s = Utils.sdfFile.parse(start).getTime() + 7 * Utils.TIME_HOUR;
        long e = Utils.sdfFile.parse(end).getTime() + 24 * Utils.TIME_HOUR - Utils.TIME_MINUTE;

        LOG.info("📥 Nạp data 1 lần (dùng chung 3 mode)...");
        TreeMap<Long, MarketDataObject> mkt = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> pred = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> fund = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("✅ market={} pred={} funding={}", mkt.size(), pred.size(), fund.size());

        // A trước (đo passRate để cấp cho C)
        Result rA = runOne("A", mkt, pred, fund, s, e, 0.5f);
        float passRateA = rA.passRate > 0 ? (float) rA.passRate : 0.5f;
        Result rB = runOne("B", mkt, pred, fund, s, e, passRateA);
        Result rC = runOne("C", mkt, pred, fund, s, e, passRateA);

        LOG.info("======================= ABLATION BƯỚC 2 ({}) =======================", mode);
        LOG.info(String.format("%-3s | %7s | %10s | %10s | %8s | %8s | %7s | %9s",
                "MODE", "trades", "totalPnl", "maxDD", "avgMAE%", "worstMAE%", "calmar", "passRate"));
        for (Result r : new Result[]{rA, rB, rC}) {
            LOG.info(String.format(Locale.US, "%-3s | %7d | %10.1f | %10.1f | %8.2f | %8.2f | %7.2f | %9.3f",
                    r.mode, r.trades, r.totalPnl, r.maxDD, r.avgMAE * 100, r.worstMAE * 100, r.calmar, r.passRate));
        }
        LOG.info("====================================================================");
        // phán quyết tự động (pre-register): A vs C
        boolean maeBetter = rA.avgMAE < rC.avgMAE && rA.worstMAE <= rC.worstMAE;
        boolean calmarBetter = rA.calmar > rC.calmar;
        LOG.info("PHÁN QUYẾT (A vs placebo C): MAE A nông hơn={} | Calmar A cao hơn={}", maeBetter, calmarBetter);
        if (maeBetter && calmarBetter) {
            LOG.info("→ AI CÓ EDGE: chọn lọc của AI tránh entry tệ + cải thiện Calmar so với vào ngẫu nhiên cùng số lệnh.");
        } else if (!maeBetter && !calmarBetter) {
            LOG.info("⚠️ AI ~ placebo: edge KHÔNG đến từ chọn lọc AI — nghi DCA cõng. Cần xem lại trước khi WFO.");
        } else {
            LOG.info("◐ Hỗn hợp: AI cải thiện một phần. Xem chi tiết MAE vs Calmar để quyết.");
        }
    }

    private Result runOne(String mode, TreeMap<Long, MarketDataObject> mkt, TreeMap<Long, AiPredictionData> pred,
                          TreeMap<Long, long[]> fund, long s, long e, float passRate) throws Exception {
        Configs.ABLATION_MODE = mode;
        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(mkt, pred, fund, new AIRejectFilter());
        sim.ablationPassRate = passRate;
        LOG.info("▶️ Chạy mode {} (passRate cấp cho placebo={})...", mode, passRate);
        sim.simulatorWithInitEntry(s, e);

        Result r = new Result();
        r.mode = mode;
        TreeMap<Long, OrderTargetInfoTest> done = sim.allOrderDone;
        r.trades = done.size();
        double sumMae = 0; int maeN = 0;
        for (OrderTargetInfoTest o : done.values()) {
            r.totalPnl += o.calTp();
            if (o.priceEntry != null && o.priceEntry > 0 && o.maeLow != null) {
                double mae = (o.priceEntry - o.maeLow) / o.priceEntry; // >0 = lỗ tạm
                if (mae > 0) { sumMae += mae; if (mae > r.worstMAE) r.worstMAE = mae; }
                maeN++;
            }
        }
        r.avgMAE = maeN > 0 ? sumMae / maeN : 0;
        Float ddRaw = BudgetManagerSimple.getInstance().balanceIndex.unProfitMin;
        r.maxDD = ddRaw != null ? Math.abs(ddRaw) : 0;
        r.calmar = r.maxDD > 1 ? r.totalPnl / r.maxDD : 0;
        r.signalSeen = sim.ablationSignalSeen;
        r.passCount = "C".equals(mode) ? sim.ablationPlaceboPass : sim.ablationPassCount;
        r.passRate = r.signalSeen > 0 ? (double) r.passCount / r.signalSeen : 0;
        LOG.info("   {} done: trades={} pnl={} maxDD={} passRate={}",
                mode, r.trades, String.format("%.1f", r.totalPnl), String.format("%.1f", r.maxDD),
                String.format("%.3f", r.passRate));
        return r;
    }
}
