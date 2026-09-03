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
 * BƯỚC 3 (ROADMAP) — ĐO TÁC ĐỘNG FUNDING FEE (code lại 2026-06-28) trên backtest ĐẦY ĐỦ 2021→2026.
 *
 * <p>Funding TRƯỚC ĐÂY bị TẮT hoàn toàn (updateFundingFee comment) → PnL/maxDD lạc quan. Đã code lại:
 * streaming theo mốc settlement THẬT của coin, notional = close-tại-settlement, quantity-cuối, long-only.
 *
 * <p>Runner này chạy 2 lần trên CÙNG data (khác biệt DUY NHẤT = APPLY_FUNDING_FEE):
 * <ul>
 *   <li>OFF — funding tắt (baseline, = mọi backtest trước nay). GATE: totalPnl phải khớp baseline đã biết.</li>
 *   <li>ON  — funding bật (mặc định mới). Đo chênh PnL/năm + maxDD + TỔNG phí funding đã trừ.</li>
 * </ul>
 *
 * <p>Kỳ vọng SANITY (để bắt code sai):
 * <ul>
 *   <li>Tổng funding phải DƯƠNG vừa phải (long trả phí ròng qua chu kỳ — bull markets rate thường dương).
 *       Nếu ÂM lớn (được thưởng nhiều) hoặc lớn bất thường (vài chục % PnL) → nghi notional/dấu sai.</li>
 *   <li>PnL ON ≤ PnL OFF (phí làm giảm lãi) ở hầu hết năm. Chênh = tổng funding ± lệch do đổi điểm đóng.</li>
 *   <li>maxDD ON ~ OFF (funding nhỏ, không đổi cấu trúc rủi ro nhiều).</li>
 * </ul>
 *
 * <p>BREAKER giữ mặc định (MARGIN 0.50) cho cả 2 run — ta đang đo RIÊNG funding trên hệ đã có phanh.
 * Chạy ORACLE. KHÔNG đụng 242.
 */
public class RunFundingImpact {

    private static final Logger LOG = LoggerFactory.getLogger(RunFundingImpact.class);

    private static final String START_DATE = "20210101";
    private static final String END_DATE = "20260601";
    private static final int[] YEARS = {2021, 2022, 2023, 2024, 2025, 2026};

    public static void main(String[] args) {
        try {
            new RunFundingImpact().run();
        } catch (Exception e) {
            LOG.error("FundingImpact error", e);
        }
    }

    public void run() throws Exception {
        Configs.TIME_RUN = START_DATE;

        LOG.info("🔒 PRE-FLIGHT: lookahead_block={} slippage_apply={} RATE_FEE={} BREAKER_MODE={} MARGIN_HALT={}",
                Configs.BLOCK_INTRABAR_LOOKAHEAD, Configs.APPLY_SLIPPAGE, Configs.RATE_FEE,
                "OFF", 0.50f);
        if (!Configs.BLOCK_INTRABAR_LOOKAHEAD || !Configs.APPLY_SLIPPAGE || Configs.RATE_FEE <= 0f) {
            LOG.error("⛔ Cấu hình ảo (look-ahead/slippage/fee tắt) — DỪNG.");
            return;
        }

        long startTime = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
        long endTime = Utils.sdfFile.parse(END_DATE).getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;

        SimpleSymbolMapper.getInstance().init();
        LOG.info("📥 Nạp data Aerospike (market / AI-pred / funding-pred)...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("✅ market={} pred={} funding-pred={}", time2MarketData.size(), predictionMap.size(), time2FundingPre.size());

        // Chạy XEN KẼ OFF→ON→OFF→ON để TÁCH NHIỄU JVM/JIT/GC (không tin 1 mẫu như trước).
        // Đo perfMs mỗi run → so trung bình ON vs OFF để áp QUY TẮC 5%.
        boolean[] applyFunding = {false, true, false, true};
        String[] names = {"OFF #1", "ON  #1", "OFF #2", "ON  #2"};
        List<Row> rows = new ArrayList<>();

        for (int r = 0; r < applyFunding.length; r++) {
            Configs.APPLY_FUNDING_FEE = applyFunding[r];
            LOG.info("\n================= ▶️ CHẠY {} (APPLY_FUNDING_FEE={}) =================", names[r], applyFunding[r]);

            BudgetManagerSimple.resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();

            SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
            sim.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());

            long t0 = System.currentTimeMillis();
            sim.simulatorWithInitEntry(startTime, endTime);
            long perfMs = System.currentTimeMillis() - t0;

            Row row = computeMetrics(names[r], sim);
            row.perfMs = perfMs;
            rows.add(row);
            LOG.info("⏱️ {} xong: simulate {} ms ({} phút), totalPnl={}, Σfunding={}",
                    names[r], perfMs, String.format(Locale.US, "%.1f", perfMs / 60000f),
                    fmt(row.totalPnl), fmt(row.totalFunding));
        }

        Configs.APPLY_FUNDING_FEE = true;   // trả về mặc định
        printTable(rows);
        printPerfRule(rows);
    }

    /** QUY TẮC 5%: trung bình thời gian ON vs OFF. Nếu ON chậm >5% → khuyến nghị mặc định TẮT funding trong HPO/WFO. */
    private void printPerfRule(List<Row> rows) {
        double offAvg = rows.stream().filter(r -> r.mode.startsWith("OFF")).mapToLong(r -> r.perfMs).average().orElse(0);
        double onAvg = rows.stream().filter(r -> r.mode.startsWith("ON")).mapToLong(r -> r.perfMs).average().orElse(0);
        double slowPct = offAvg > 0 ? (onAvg - offAvg) / offAvg * 100.0 : 0;
        LOG.info("\n================= ⏱️ QUY TẮC 5% (PERF) =================");
        LOG.info("OFF trung bình = {} ms | ON trung bình = {} ms | ON chậm hơn {}%",
                String.format(Locale.US, "%.0f", offAvg), String.format(Locale.US, "%.0f", onAvg),
                String.format(Locale.US, "%.1f", slowPct));
        if (slowPct > 5.0) {
            LOG.info("➡️ KẾT LUẬN: ON chậm >5% → KHUYẾN NGHỊ mặc định APPLY_FUNDING_FEE=false trong HPO/WFO,");
            LOG.info("   CHỈ bật ở Golden backtest cuối (đo PnL/DD thật). Funding tác động nhỏ nên HPO không méo nhiều.");
        } else {
            LOG.info("➡️ KẾT LUẬN: ON chậm ≤5% → GIỮ APPLY_FUNDING_FEE=true mặc định (kể cả trong HPO/WFO). Đủ rẻ.");
        }
    }

    private Row computeMetrics(String mode, SimulatorMarketLevelTicker1MStopLoss sim) {
        Row r = new Row();
        r.mode = mode;
        if (sim.allOrderDone != null) {
            r.tradeCount = sim.allOrderDone.size();
            for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
                float pnl = o.calTp();
                r.totalPnl += pnl;
                float f = o.calFundingFee();
                r.totalFunding += f;
                int y = Utils.getYear(o.timeUpdate);
                r.yearPnl.merge(y, pnl, Float::sum);
                r.yearFunding.merge(y, f, Float::sum);
            }
        }
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        r.maxDrawdownTrue = (bm.trueUnrealizedMin != null) ? bm.trueUnrealizedMin : 0f;
        r.capital = (bm.balanceBasic != null && bm.balanceBasic > 0) ? bm.balanceBasic : 1f;
        r.balanceEnd = r.capital + r.totalPnl;
        return r;
    }

    private void printTable(List<Row> rows) {
        LOG.info("\n\n================= 📊 BẢNG TÁC ĐỘNG FUNDING FEE ({} -> {}) =================", START_DATE, END_DATE);
        for (Row r : rows) {
            LOG.info(String.format(Locale.US,
                    "─ %-18s | trades=%d | totalPnl=%s | ΣfundingĐãTrừ=%s | maxDD_THẬT=%s (%.1f%%) | balEnd=%s",
                    r.mode, r.tradeCount, fmt(r.totalPnl), fmt(r.totalFunding),
                    fmt(r.maxDrawdownTrue), r.maxDrawdownTrue / r.capital * 100f, fmt(r.balanceEnd)));
            StringBuilder yb = new StringBuilder("    PnL/năm:     ");
            for (int y : YEARS) {
                Float p = r.yearPnl.get(y);
                yb.append(y).append("=").append(p != null ? fmt(p) : "0").append("  ");
            }
            LOG.info(yb.toString());
            StringBuilder fb = new StringBuilder("    funding/năm: ");
            for (int y : YEARS) {
                Float f = r.yearFunding.get(y);
                fb.append(y).append("=").append(f != null ? fmt(f) : "0").append("  ");
            }
            LOG.info(fb.toString());
        }
        // chênh lệch trực tiếp — so cặp OFF đầu vs ON đầu (PnL giống nhau ở mọi cặp, chỉ perf khác do nhiễu)
        Row off = rows.stream().filter(x -> x.mode.startsWith("OFF")).findFirst().orElse(null);
        Row on = rows.stream().filter(x -> x.mode.startsWith("ON")).findFirst().orElse(null);
        if (off != null && on != null) {
            LOG.info("------------------------------------------------------------------------------------------");
            LOG.info("CHÊNH ON-OFF: ΔtotalPnl={} (= -Σfunding nếu điểm đóng không đổi: Σfunding_on={}), ΔmaxDD={}, Δtrades={}",
                    fmt(on.totalPnl - off.totalPnl), fmt(on.totalFunding),
                    fmt(on.maxDrawdownTrue - off.maxDrawdownTrue), on.tradeCount - off.tradeCount);
            LOG.info("SANITY:");
            LOG.info(" - 🔒 GATE: totalPnl OFF ({}) phải khớp baseline RunMarginHaltSweep HALT-0.50 (50311 ở 5y).", fmt(off.totalPnl));
            LOG.info(" - Σfunding_on DƯƠNG vừa phải = long trả phí ròng. ÂM lớn / quá lớn (>vài chục % PnL) => nghi dấu/notional sai.");
            LOG.info(" - ΔtotalPnl ≈ -Σfunding (lệch nhỏ do đổi điểm đóng cuối kỳ). maxDD ~ không đổi nhiều.");
        }
    }

    private static String fmt(float v) {
        return String.format(Locale.US, "%.0f", v);
    }

    private static class Row {
        String mode;
        int tradeCount = 0;
        float totalPnl = 0f;
        float totalFunding = 0f;
        float maxDrawdownTrue = 0f;
        float capital = 1f;
        float balanceEnd = 0f;
        long perfMs = 0L;
        TreeMap<Integer, Float> yearPnl = new TreeMap<>();
        TreeMap<Integer, Float> yearFunding = new TreeMap<>();
    }
}
