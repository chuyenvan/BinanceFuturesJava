package com.binance.chuyennd.ai_ml.validation.ablation.market;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.validation.EdgeAttributionReport;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
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
 * NHIỆM VỤ 1 — Monotonicity nội nhóm funding.
 *
 * Câu hỏi: trong nhóm ĐƯỢC trade (symbolPred <= maxThres), symbol pred-THẤP có entry TỐT hơn pred-CAO?
 * => funding ranking có thông tin (nên siết maxThres) hay phẳng (ranking là nhiễu)?
 *
 * 1 run baseline (funding THẬT, full 2021->2026, KHÔNG breaker). Lấy mọi LEG ĐẦU PREDICT_SYMBOL_TRADE
 * (order.symbolPred set lúc tạo), bin theo symbolPred: [0-0.05] / (0.05-0.15] / (0.15-maxThres].
 * Đo per-bin (qua EdgeAttributionReport): avgMAE%, worstMAE%, winRate, payoff(net), totalPnl, count. Tách năm.
 *
 * MAE = (maeLow - entry)/entry — ĐÁY THẬT của cụm tính từ leg đầu (field maeLow, không reset-lên như
 * minPrice cũ). Đã verify maeLow khớp đáy-độc-lập-từ-ticker 100% (xem VerifyMinPriceMae). Trước fix,
 * MAE dựa minPrice bị reset-lên trailing nên NÔNG GIẢ (chỉ ~4.7% khớp) — số monotonicity cũ KHÔNG tin được.
 *
 * Lưu ý: đây là attribution CHẤT LƯỢNG ENTRY ở mức LEG ĐẦU (calTp net, gán theo NĂM MỞ leg) — KHÁC với
 * PnL chiến lược/năm dạng MTM (dùng ở nhiệm vụ tổng PnL). READ-ONLY.
 */
public class RunFundingMonotonicity {

    private static final Logger LOG = LoggerFactory.getLogger(RunFundingMonotonicity.class);

    private static final String START_DATE = "20210101";
    private static final String END_DATE = "20260601";
    private static final int[] YEARS = {2021, 2022, 2023, 2024, 2025, 2026};

    public static void main(String[] args) {
        try {
            new RunFundingMonotonicity().run();
        } catch (Exception e) {
            LOG.error("Monotonicity error", e);
        }
    }

    public void run() throws Exception {
        Configs.IS_HPO_MODE = false;
        Configs.IS_KAGGLE_MODE = false;
        Configs.TIME_RUN = START_DATE;
        Configs.BREAKER_MODE = "OFF";

        float maxThres = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * Configs.AI_DYNAMIC_MAX;
        LOG.info("🔒 PRE-FLIGHT: lookahead_block={} slippage_apply={} SLIPPAGE_RATE={} RATE_FEE={} | FILTER_MODE={} | maxThres={}",
                Configs.BLOCK_INTRABAR_LOOKAHEAD, Configs.APPLY_SLIPPAGE, Configs.SLIPPAGE_RATE,
                Configs.RATE_FEE, Configs.FILTER_MODE, String.format(Locale.US, "%.4f", maxThres));
        if (!Configs.BLOCK_INTRABAR_LOOKAHEAD || !Configs.APPLY_SLIPPAGE || Configs.RATE_FEE <= 0f) {
            LOG.error("⛔ Cấu hình ảo — DỪNG."); return;
        }
        LOG.info("⚠️ PnL net slippage+fee (funding fee chưa trừ — updateFundingFee comment).");

        long startTime = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
        long endTime = Utils.sdfFile.parse(END_DATE).getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;

        SimpleSymbolMapper.getInstance().init();
        LOG.info("📥 Nạp data Aerospike...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();

        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();

        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());
        LOG.info("🚀 Chạy baseline full {} -> {} (funding THẬT)...", START_DATE, END_DATE);
        sim.simulatorWithInitEntry(startTime, endTime);

        analyze(sim, maxThres);
    }

    private void analyze(SimulatorMarketLevelTicker1MStopLoss sim, float maxThres) {
        if (sim.allOrderDone == null || sim.allOrderDone.isEmpty()) { LOG.warn("⚠️ Không có lệnh."); return; }

        // chỉ LEG ĐẦU path PREDICT_SYMBOL_TRADE, có symbolPred
        List<OrderTargetInfoTest> firstLegs = new ArrayList<>();
        for (OrderTargetInfoTest o : EdgeAttributionReport.firstLegsOf(sim.allOrderDone.values(),
                MarketLevelChange.PREDICT_SYMBOL_TRADE)) {
            if (o.symbolPred != null) firstLegs.add(o);
        }
        LOG.info("\n================ MONOTONICITY — {} leg đầu PREDICT_SYMBOL_TRADE ================", firstLegs.size());
        if (firstLegs.isEmpty()) { LOG.warn("⚠️ Không có leg PREDICT_SYMBOL_TRADE."); return; }

        // 🔎 Đảm bảo MAE dùng đáy THẬT (maeLow), không fallback nhầm về minPrice CŨ (chỉ xảy ra với data cũ).
        long nullMae = firstLegs.stream().filter(o -> o.maeLow == null).count();
        if (nullMae > 0) {
            LOG.warn("⚠️ {}/{} leg THIẾU maeLow => legMaePct fallback minPrice CŨ (SAI). Data cũ? Chạy lại sim tươi.",
                    nullMae, firstLegs.size());
        } else {
            LOG.info("✅ MAE nguồn = maeLow (đáy THẬT) cho toàn bộ {} leg.", firstLegs.size());
        }

        String[] binName = {"[0-0.05]", "(0.05-0.15]", "(0.15-" + String.format(Locale.US, "%.2f", maxThres) + "]"};

        // TỔNG 2021-2026
        LOG.info("--- TỔNG (2021-2026) ---");
        printHeader();
        List<EdgeAttributionReport.LegStats> all = new ArrayList<>();
        for (int b = 0; b < 3; b++) {
            EdgeAttributionReport.LegStats s = EdgeAttributionReport.stats(filterBin(firstLegs, b, -1));
            all.add(s);
            printRow(binName[b], s);
        }

        // theo NĂM
        LOG.info("--- THEO NĂM (bin x năm: count | avgMAE%% | payoff | totalPnl) ---");
        for (int y : YEARS) {
            StringBuilder sb = new StringBuilder(String.format(Locale.US, "%d: ", y));
            for (int b = 0; b < 3; b++) {
                EdgeAttributionReport.LegStats s = EdgeAttributionReport.stats(filterBin(firstLegs, b, y));
                sb.append(String.format(Locale.US, "%s[n=%d mae=%.2f%% pf=%s pnl=%.0f]  ",
                        binName[b], s.count, s.avgMaePct * 100, payoffStr(s.payoff), s.totalPnl));
            }
            LOG.info(sb.toString());
        }

        // PHÁN QUYẾT
        EdgeAttributionReport.LegStats lo = all.get(0), hi = all.get(2);
        LOG.info("\n📌 PHÁN QUYẾT MONOTONICITY:");
        LOG.info("   bin THẤP [0-0.05]:   avgMAE={}%% worstMAE={}%% payoff={} pnl={}",
                f2(lo.avgMaePct * 100), f2(lo.worstMaePct * 100), payoffStr(lo.payoff), f0(lo.totalPnl));
        LOG.info("   bin CAO (0.15-max):  avgMAE={}%% worstMAE={}%% payoff={} pnl={}",
                f2(hi.avgMaePct * 100), f2(hi.worstMaePct * 100), payoffStr(hi.payoff), f0(hi.totalPnl));
        boolean maeMonotone = lo.avgMaePct > hi.avgMaePct;      // bin thấp MAE nông hơn (ít âm hơn)
        boolean payoffMonotone = lo.payoff > hi.payoff;
        if (maeMonotone && payoffMonotone) {
            LOG.info("   => ĐƠN ĐIỆU (pred thấp = MAE nông + payoff cao): funding ranking CÓ giá trị.");
            LOG.info("      Đề xuất bước sau: quét maxThres giảm dần (sensitivity, 1 gene) đo payoff/PnL/DD.");
        } else {
            LOG.info("   => PHẲNG/không đơn điệu: ranking trong <=maxThres là NHIỄU; siết maxThres vô ích.");
            LOG.info("      Dự báo shuffle ablation (NV3) sẽ ra A≈SHUFFLE.");
        }
    }

    private List<OrderTargetInfoTest> filterBin(List<OrderTargetInfoTest> legs, int bin, int year) {
        List<OrderTargetInfoTest> out = new ArrayList<>();
        for (OrderTargetInfoTest o : legs) {
            float p = o.symbolPred;
            int b = (p <= 0.05f) ? 0 : (p <= 0.15f ? 1 : 2);
            if (b != bin) continue;
            if (year > 0 && Utils.getYear(o.timeStart) != year) continue;
            out.add(o);
        }
        return out;
    }

    private void printHeader() {
        LOG.info(String.format(Locale.US, "%-14s %7s %9s %10s %8s %8s %10s",
                "bin", "count", "avgMAE%", "worstMAE%", "winRate", "payoff", "totalPnl"));
    }

    private void printRow(String bin, EdgeAttributionReport.LegStats s) {
        LOG.info(String.format(Locale.US, "%-14s %7d %8.2f%% %9.2f%% %7.1f%% %8s %10.0f",
                bin, s.count, s.avgMaePct * 100, s.worstMaePct * 100, s.winRate * 100, payoffStr(s.payoff), s.totalPnl));
    }

    private static String payoffStr(double v) { return Double.isInfinite(v) ? "INF" : String.format(Locale.US, "%.2f", v); }
    private static String f2(double v) { return String.format(Locale.US, "%.2f", v); }
    private static String f0(double v) { return String.format(Locale.US, "%.0f", v); }
}
