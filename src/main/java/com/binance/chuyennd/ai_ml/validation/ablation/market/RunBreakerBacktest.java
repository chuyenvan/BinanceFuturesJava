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
import java.util.Map;
import java.util.TreeMap;

/**
 * TEST CIRCUIT BREAKER trên backtest ĐẦY ĐỦ 2021→2026 (gồm bear 2022 + sập 2025-2026).
 * 4 run CÙNG commit/data/tham số, chỉ khác Configs.BREAKER_MODE: OFF / MARGIN / DCA / BOTH.
 *
 * Giả thuyết: entry CÓ edge nhưng DCA-không-giới-hạn + mở tới cạn vốn phá edge qua chu kỳ.
 * => Xem breaker có biến PnL 5 năm từ ÂM thành DƯƠNG + giảm maxDD không.
 *
 * Trọng tâm: PnL TỪNG NĂM (sống sót qua bear/sập?) + maxDD + so MARGIN vs DCA.
 * Lưu ý: funding fee CHƯA tính (updateFundingFee comment) => PnL tuyệt đối hơi lạc quan, nhưng
 * so giữa các mode vẫn đúng (cùng thiếu như nhau).
 */
public class RunBreakerBacktest {

    private static final Logger LOG = LoggerFactory.getLogger(RunBreakerBacktest.class);

    private static final String START_DATE = "20210101";
    private static final String END_DATE = "20260601";
    private static final String[] MODES = {"OFF", "MARGIN", "DCA", "BOTH"};
    private static final int[] YEARS = {2021, 2022, 2023, 2024, 2025, 2026};

    public static void main(String[] args) {
        try {
            new RunBreakerBacktest().run();
        } catch (Exception e) {
            LOG.error("Breaker backtest error", e);
        }
    }

    public void run() throws Exception {
        Configs.TIME_RUN = START_DATE;

        // PRE-FLIGHT (tái lập): cấu hình nền + ngưỡng breaker.
        LOG.info("🔒 PRE-FLIGHT: lookahead_block={} slippage_apply={} SLIPPAGE_RATE={} RATE_FEE={} | FILTER_MODE={}",
                Configs.BLOCK_INTRABAR_LOOKAHEAD, Configs.APPLY_SLIPPAGE, Configs.SLIPPAGE_RATE,
                Configs.RATE_FEE, Configs.FILTER_MODE);
        LOG.info("🔒 BREAKER ngưỡng: MARGIN_HALT={} CLUSTER_DD_MAX={} | giai đoạn {} -> {}",
                Configs.BREAKER_MARGIN_HALT, Configs.BREAKER_CLUSTER_DD_MAX, START_DATE, END_DATE);
        if (!Configs.BLOCK_INTRABAR_LOOKAHEAD || !Configs.APPLY_SLIPPAGE || Configs.RATE_FEE <= 0f) {
            LOG.error("⛔ Cấu hình ảo (look-ahead/slippage/fee tắt) — DỪNG.");
            return;
        }
        LOG.info("⚠️ PnL tuyệt đối hơi lạc quan: funding fee CHƯA tính (updateFundingFee comment).");

        long startTime = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
        long endTime = Utils.sdfFile.parse(END_DATE).getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;

        SimpleSymbolMapper.getInstance().init();
        LOG.info("📥 Nạp data Aerospike (market / AI-pred / funding-pred)...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("✅ market={} pred={} funding={}", time2MarketData.size(), predictionMap.size(), time2FundingPre.size());

        List<Row> rows = new ArrayList<>();
        for (String mode : MODES) {
            Configs.BREAKER_MODE = mode;   // KHÁC BIỆT DUY NHẤT giữa 4 run
            LOG.info("\n================= ▶️ CHẠY BREAKER_MODE {} =================", mode);

            BudgetManagerSimple.resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();

            SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
            sim.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());
            sim.simulatorWithInitEntry(startTime, endTime);

            rows.add(computeMetrics(mode, sim));
        }

        printTable(rows);
    }

    private Row computeMetrics(String mode, SimulatorMarketLevelTicker1MStopLoss sim) {
        Row r = new Row();
        r.mode = mode;
        r.breakerMarginHalt = sim.breakerMarginHaltCount;
        r.breakerDcaCap = sim.breakerDcaCapCount;

        if (sim.allOrderDone != null) {
            for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
                float pnl = o.calTp();
                r.totalPnl += pnl;
                int y = Utils.getYear(o.timeUpdate);
                r.yearPnl.merge(y, pnl, Float::sum);
            }
        }

        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        r.maxDrawdown = (bm.balanceIndex.unProfitMin != null) ? bm.balanceIndex.unProfitMin : 0f;
        r.maxDrawdownTrue = (bm.trueUnrealizedMin != null) ? bm.trueUnrealizedMin : 0f;
        r.capital = (bm.balanceBasic != null && bm.balanceBasic > 0) ? bm.balanceBasic : 1f;
        r.balanceEnd = r.capital + r.totalPnl;

        // maxDD MỚI theo năm (đáy THẬT mỗi tick)
        r.yearDdTrue.putAll(bm.year2TrueUnrealizedMin);
        // maxDD CŨ theo năm: gom min của date2ProfitMin theo năm (key = mốc ngày GMT+7)
        for (Map.Entry<Long, Float> e : bm.balanceIndex.date2ProfitMin.entrySet()) {
            if (e.getValue() == null) continue;
            int y = Utils.getYear(e.getKey());
            r.yearDdOld.merge(y, e.getValue(), Math::min);
        }

        float maxRatio = 0f;
        for (Float marginMax : bm.balanceIndex.date2MarginMax.values()) {
            if (marginMax != null && marginMax / r.capital > maxRatio) maxRatio = marginMax / r.capital;
        }
        r.maxMarginRatio = maxRatio;
        return r;
    }

    private void printTable(List<Row> rows) {
        LOG.info("\n\n================= 📊 BẢNG CIRCUIT BREAKER ({} -> {}) =================", START_DATE, END_DATE);
        LOG.info("Trọng tâm: PnL từng năm (sống sót bear 2022 + sập 2025-2026?) + maxDD. So MARGIN vs DCA.");
        for (Row r : rows) {
            LOG.info(String.format(Locale.US,
                    "─ MODE %-6s | totalPnl=%s | maxDD_cũ=%s (%.1f%%) maxDD_THẬT=%s (%.1f%%) | balEnd=%s | halt=%d dcaCap=%d | maxMargR=%.2f",
                    r.mode, fmt(r.totalPnl),
                    fmt(r.maxDrawdown), r.maxDrawdown / r.capital * 100f,
                    fmt(r.maxDrawdownTrue), r.maxDrawdownTrue / r.capital * 100f,
                    fmt(r.balanceEnd), r.breakerMarginHalt, r.breakerDcaCap, r.maxMarginRatio));
            StringBuilder yb = new StringBuilder("    PnL/năm: ");
            for (int y : YEARS) {
                Float p = r.yearPnl.get(y);
                yb.append(y).append("=").append(p != null ? fmt(p) : "0").append("  ");
            }
            LOG.info(yb.toString());
            StringBuilder db = new StringBuilder("    maxDD/năm (cũ→THẬT): ");
            for (int y : YEARS) {
                Float o = r.yearDdOld.get(y), t = r.yearDdTrue.get(y);
                db.append(y).append("=").append(o != null ? fmt(o) : "0").append("→")
                        .append(t != null ? fmt(t) : "0").append("  ");
            }
            LOG.info(db.toString());
        }
        LOG.info("------------------------------------------------------------------------------------------");
        LOG.info("CÁCH ĐỌC:");
        LOG.info(" - 🔒 GATE LIÊM CHÍNH: totalPnl PHẢI trùng run trước khi thêm field maeLow/trueUnrealizedMin.");
        LOG.info("      Nếu totalPnl đổi => đã phá nhầm logic => DỪNG, rollback. (field mới chỉ đo, không quyết định).");
        LOG.info(" - maxDD_THẬT sâu hơn maxDD_cũ = bằng chứng DD cũ (từ profitMin/minPrice, mẫu theo giờ) từng hụt.");
        LOG.info(" - PnL tổng 5 năm ÂM→DƯƠNG nhờ breaker => DCA-không-giới-hạn ĐÚNG là thủ phạm (bước ngoặt).");
        LOG.info(" - Breaker giảm maxDD mạnh mà PnL ~giữ => đáng áp. So MARGIN vs DCA để biết cơ chế nào gánh chính.");
    }

    private static String fmt(float v) {
        return String.format(Locale.US, "%.0f", v);
    }

    private static class Row {
        String mode;
        float totalPnl = 0f;
        float maxDrawdown = 0f;        // CŨ: unProfitMin (Σ profitMin, lấy mẫu theo giờ) — nghi hụt
        float maxDrawdownTrue = 0f;    // MỚI: trueUnrealizedMin (bar.low, mỗi tick) — đáy THẬT
        float capital = 1f;
        float balanceEnd = 0f;
        float maxMarginRatio = 0f;
        long breakerMarginHalt = 0;
        long breakerDcaCap = 0;
        TreeMap<Integer, Float> yearPnl = new TreeMap<>();
        TreeMap<Integer, Float> yearDdOld = new TreeMap<>();   // maxDD cũ theo năm (gom từ date2ProfitMin)
        TreeMap<Integer, Float> yearDdTrue = new TreeMap<>();  // maxDD mới theo năm (year2TrueUnrealizedMin)
    }
}
