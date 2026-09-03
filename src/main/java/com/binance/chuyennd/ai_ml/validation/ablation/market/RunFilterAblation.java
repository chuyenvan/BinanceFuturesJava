package com.binance.chuyennd.ai_ml.validation.ablation.market;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.TreeMap;

/**
 * TASK-104: A/B test gate 15m — 4 mode × 3 golden range.
 *
 * <p>Mode A (full) vs E (tắt MOM15) để đo riêng tác dụng gate 15m.
 * F (chỉ MOM15) và OFF (tắt hết) là sàn so sánh.
 *
 * <p>3 range golden (ADR-0006):
 * <ul>
 *   <li>CRASH 2022: 20220401→20221231 (LUNA tháng 5 + FTX tháng 11)</li>
 *   <li>BULL 2023Q4: 20231001→20240131</li>
 *   <li>RECENT: 20251001→20260430 (range baseline)</li>
 * </ul>
 *
 * <p>⚠️ CRASH/BULL có thể trả về 0 trade nếu AI-pred/funding-pred không có data cũ trong Aerospike.
 * RECENT luôn có data đầy đủ.
 *
 * <p>Guard liêm chính (look-ahead off, slippage on, fee on) chạy trong simulatorWithInitEntry.
 * KHÔNG bump CONFIG_VERSION — ablation filter, không đổi model.
 */
public class RunFilterAblation {

    private static final Logger LOG = LoggerFactory.getLogger(RunFilterAblation.class);

    private static final String[] MODES = {"A", "E", "F", "OFF"};

    private static final Range[] RANGES = {
            new Range("CRASH-2022", "20220401", "20221231"),
            new Range("BULL-2023Q4", "20231001", "20240131"),
            new Range("RECENT", "20251001", "20260430"),
    };

    public static void main(String[] args) {
        try {
            new RunFilterAblation().run();
        } catch (Exception e) {
            LOG.error("Ablation error", e);
        }
        System.exit(0);
    }

    public void run() throws Exception {

        // ----- PRE-FLIGHT -----
        LOG.info("INTEGRITY PRE-FLIGHT: BLOCK_INTRABAR_LOOKAHEAD={} APPLY_SLIPPAGE={} SLIPPAGE_RATE={} RATE_FEE={}",
                Configs.BLOCK_INTRABAR_LOOKAHEAD, Configs.APPLY_SLIPPAGE, Configs.SLIPPAGE_RATE, Configs.RATE_FEE);
        if (!Configs.BLOCK_INTRABAR_LOOKAHEAD || !Configs.APPLY_SLIPPAGE || Configs.RATE_FEE <= 0f) {
            LOG.error("CAU HINH AO (look-ahead/slippage/fee tat) — DUNG. So sanh ablation se vo nghia.");
            return;
        }

        // ----- LOAD DATA MỘT LẦN, dùng chung (read-only), simulator tự filter theo range -----
        SimpleSymbolMapper.getInstance().init();
        LOG.info("Nap data tu Aerospike (market / AI-pred / funding-pred)...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("market={} pred={} funding={}",
                time2MarketData.size(), predictionMap.size(), time2FundingPre.size());
        if (time2FundingPre.isEmpty()) {
            LOG.warn("funding-pred RONG -> symbolPred null hang loat -> EARLY mat tac dung. CRASH/BULL co the lech live.");
        }

        List<Row> allRows = new ArrayList<>();

        for (Range range : RANGES) {
            long startTime = Utils.sdfFile.parse(range.start).getTime() + 7 * Utils.TIME_HOUR;
            long endTime   = Utils.sdfFile.parse(range.end).getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;
            LOG.info("\n==================== RANGE: {} ({} -> {}) ====================",
                    range.name, range.start, range.end);

            for (String mode : MODES) {
                Configs.FILTER_MODE = mode;
                Configs.TIME_RUN = range.start;
                AIRejectFilter.resetCounters();

                BudgetManagerSimple.resetInstance();
                HistoryManager.getInstance().resetCache();
                CoinRankManager.getInstance().resetCache();

                LOG.info("--- MODE {} | range {} ---", mode, range.name);
                SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
                AIRejectFilter filter = new AIRejectFilter();
                sim.initDataReady(time2MarketData, predictionMap, time2FundingPre, filter);
                sim.simulatorWithInitEntry(startTime, endTime);

                Row row = computeMetrics(range.name, mode, sim);
                row.mom15Rejects = AIRejectFilter.mom15RejectCount.get();
                allRows.add(row);
            }
        }

        printTables(allRows);
    }

    // ====================== METRIC ======================
    private Row computeMetrics(String range, String mode, SimulatorMarketLevelTicker1MStopLoss sim) {
        Row r = new Row();
        r.range = range;
        r.mode = mode;

        double sumWin = 0, sumLossAbs = 0;
        int nWin = 0, nLoss = 0;
        float worst = 0f;
        if (sim.allOrderDone != null) {
            for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
                float pnl = o.calTp();
                r.totalPnl += pnl;
                if (pnl >= 0) { sumWin += pnl; nWin++; }
                else { sumLossAbs += -pnl; nLoss++; }
                if (pnl < worst) worst = pnl;
            }
            r.tradeCount = sim.allOrderDone.size();
        }
        r.worstSingleLoss = worst;
        r.profitFactor = (sumLossAbs > 0) ? (float) (sumWin / sumLossAbs) : (sumWin > 0 ? Float.POSITIVE_INFINITY : 0f);
        float avgWin  = nWin > 0 ? (float) (sumWin / nWin) : 0f;
        float avgLoss = nLoss > 0 ? (float) (sumLossAbs / nLoss) : 0f;
        r.payoffRatio = (avgLoss > 0) ? avgWin / avgLoss : (avgWin > 0 ? Float.POSITIVE_INFINITY : 0f);

        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        r.maxDrawdown = (bm.balanceIndex.unProfitMin != null) ? bm.balanceIndex.unProfitMin : 0f;
        float capital = (bm.balanceBasic != null && bm.balanceBasic > 0) ? bm.balanceBasic : 1f;
        int nearLiq = 0;
        float maxRatio = 0f;
        for (Float marginMax : bm.balanceIndex.date2MarginMax.values()) {
            if (marginMax == null) continue;
            float ratio = marginMax / capital;
            if (ratio > maxRatio) maxRatio = ratio;
            if (ratio >= 0.7475f) nearLiq++;   // cu: Configs.BUDGET_MARGIN_RATIO_2 (field da xoa, gia tri giu nguyen)
        }
        r.nearLiqDays = nearLiq;
        r.maxMarginRatio = maxRatio;
        r.returnOverDD = (r.maxDrawdown < 0) ? r.totalPnl / Math.abs(r.maxDrawdown) : Float.NaN;
        return r;
    }

    private void printTables(List<Row> rows) {
        String header = String.format(Locale.US,
                "%-8s %-6s %8s %12s %8s %12s %12s %8s %8s %9s %10s",
                "RANGE", "MODE", "trades", "totalPnl", "PF", "maxDD", "worstLoss", "payoff", "nearLiq2", "maxMargR", "retOverDD");
        String sep = "-".repeat(header.length());

        for (Range range : RANGES) {
            LOG.info("\n\n=== RANGE: {} ===", range.name);
            LOG.info(header);
            LOG.info(sep);
            for (Row r : rows) {
                if (!range.name.equals(r.range)) continue;
                LOG.info(String.format(Locale.US,
                        "%-8s %-6s %8d %12.1f %8s %12.1f %12.1f %8s %8d %9.2f %10s",
                        r.range, r.mode, r.tradeCount, r.totalPnl, fmt(r.profitFactor),
                        r.maxDrawdown, r.worstSingleLoss, fmt(r.payoffRatio),
                        r.nearLiqDays, r.maxMarginRatio,
                        Float.isNaN(r.returnOverDD) ? "N/A" : String.format(Locale.US, "%.2f", r.returnOverDD)));
            }
            LOG.info(sep);
        }

        // A vs E: tác dụng gate 15m
        LOG.info("\n\n=== SO SANH A (full) vs E (tat MOM15) — tac dung gate 15m ===");
        LOG.info(String.format(Locale.US, "%-13s %8s %12s %12s %12s %10s %12s",
                "RANGE+MODE", "trades", "totalPnl", "maxDD", "worstLoss", "retOverDD", "mom15Rej"));
        for (Range range : RANGES) {
            Row rowA = findRow(rows, range.name, "A");
            Row rowE = findRow(rows, range.name, "E");
            if (rowA == null || rowE == null) continue;
            LOG.info(String.format(Locale.US, "%-13s %8d %12.1f %12.1f %12.1f %10s %12d",
                    range.name + "/A", rowA.tradeCount, rowA.totalPnl, rowA.maxDrawdown, rowA.worstSingleLoss,
                    Float.isNaN(rowA.returnOverDD) ? "N/A" : String.format(Locale.US, "%.2f", rowA.returnOverDD),
                    rowA.mom15Rejects));
            LOG.info(String.format(Locale.US, "%-13s %8d %12.1f %12.1f %12.1f %10s %12d",
                    range.name + "/E", rowE.tradeCount, rowE.totalPnl, rowE.maxDrawdown, rowE.worstSingleLoss,
                    Float.isNaN(rowE.returnOverDD) ? "N/A" : String.format(Locale.US, "%.2f", rowE.returnOverDD),
                    rowE.mom15Rejects));
            LOG.info("---");
        }
        LOG.info("CACH DOC: A.maxDD < E.maxDD => gate 15m chon duoi. A.retOverDD > E.retOverDD => gate dang giu.");
        LOG.info("          A.pnl < E.pnl + DD tuong duong => gate chi bo lo lenh tot, nen bo.");
        LOG.info("          mom15Rej (A) = so lenh bi gate 15m loc ra.");
        LOG.info("ABLATION DONE");
    }

    private static Row findRow(List<Row> rows, String range, String mode) {
        for (Row r : rows) {
            if (range.equals(r.range) && mode.equals(r.mode)) return r;
        }
        return null;
    }

    private static String fmt(float v) {
        if (Float.isInfinite(v)) return "INF";
        return String.format(Locale.US, "%.2f", v);
    }

    private static class Range {
        final String name, start, end;
        Range(String name, String start, String end) {
            this.name = name; this.start = start; this.end = end;
        }
    }

    private static class Row {
        String range, mode;
        int tradeCount = 0;
        float totalPnl = 0f;
        float profitFactor = 0f;
        float maxDrawdown = 0f;
        float worstSingleLoss = 0f;
        float payoffRatio = 0f;
        int nearLiqDays = 0;
        float maxMarginRatio = 0f;
        float returnOverDD = Float.NaN;
        int mom15Rejects = 0;
    }
}
