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
 * BƯỚC 3 (ROADMAP) — TINH CHỈNH NGƯỠNG BREAKER_MARGIN_HALT trên backtest ĐẦY ĐỦ 2021→2026.
 *
 * <p>Bối cảnh (đo 2026-06-28): cap %vốn/cụm vô dụng trên danh mục (veto 0-8 lần) vì budget phân tán
 * qua hàng trăm cụm nhỏ. Lá chắn THẬT là MARGIN_HALT tổng — tại 0.70: DD -58.6%→-42.5%, maxMargR 0.99→0.71,
 * PnL 69379→63164 (-9%). Đã chốt hướng: BỎ cap per-cluster, dùng MARGIN_HALT. Việc còn lại: chọn NGƯỠNG.
 *
 * <p>Runner này quét nhiều mức HALT để vẽ đường cong đánh đổi DD↔PnL, từ đó chốt ngưỡng có
 * return/maxDD (Calmar-like) tốt nhất. KHÁC BIỆT DUY NHẤT giữa các run = BREAKER_MARGIN_HALT.
 * BREAKER_MODE = MARGIN cho mọi run trừ OFF (baseline để neo + verify GATE liêm chính).
 *
 * <p>GATE liêm chính: totalPnl của OFF phải trùng baseline RunBreakerBacktest OFF (cùng commit/data).
 *
 * <p>⚠️ funding fee CHƯA tính → PnL tuyệt đối hơi lạc quan; so giữa mode vẫn đúng (cùng thiếu như nhau).
 * Chạy ORACLE (cần 3 khối Aerospike 226). KHÔNG đụng 242.
 */
public class RunMarginHaltSweep {

    private static final Logger LOG = LoggerFactory.getLogger(RunMarginHaltSweep.class);

    private static final String START_DATE = "20210101";
    private static final String END_DATE = "20260601";
    private static final int[] YEARS = {2021, 2022, 2023, 2024, 2025, 2026};

    /** 1 cấu hình: tên + chế độ + ngưỡng halt. halt<0 nghĩa OFF (không quét ngưỡng). */
    private static class Cfg {
        String name;
        boolean on;       // true = BREAKER_MODE MARGIN
        float halt;       // BREAKER_MARGIN_HALT (chỉ dùng khi on=true)
        Cfg(String name, boolean on, float halt) { this.name = name; this.on = on; this.halt = halt; }
    }

    public static void main(String[] args) {
        try {
            new RunMarginHaltSweep().run();
        } catch (Exception e) {
            LOG.error("MarginHalt sweep error", e);
        }
    }

    public void run() throws Exception {
        Configs.TIME_RUN = START_DATE;

        // Quét ngưỡng: OFF (neo) + 5 mức HALT từ chặt→lỏng. 0.70 là điểm đã đo (để đối chiếu lại).
        List<Cfg> cfgs = new ArrayList<>();
        cfgs.add(new Cfg("OFF", false, -1f));
        cfgs.add(new Cfg("HALT-0.50", true, 0.50f));
        cfgs.add(new Cfg("HALT-0.60", true, 0.60f));
        cfgs.add(new Cfg("HALT-0.70", true, 0.70f));
        cfgs.add(new Cfg("HALT-0.80", true, 0.80f));
        cfgs.add(new Cfg("HALT-0.90", true, 0.90f));

        LOG.info("🔒 PRE-FLIGHT: lookahead_block={} slippage_apply={} SLIPPAGE_RATE={} RATE_FEE={} | FILTER_MODE={} OFF_FLAT_HARD={}",
                Configs.BLOCK_INTRABAR_LOOKAHEAD, Configs.APPLY_SLIPPAGE, Configs.SLIPPAGE_RATE,
                Configs.RATE_FEE, Configs.FILTER_MODE, Configs.OFF_FLAT_HARD);
        if (!Configs.BLOCK_INTRABAR_LOOKAHEAD || !Configs.APPLY_SLIPPAGE || Configs.RATE_FEE <= 0f) {
            LOG.error("⛔ Cấu hình ảo (look-ahead/slippage/fee tắt) — DỪNG.");
            return;
        }
        LOG.info("⚠️ PnL tuyệt đối hơi lạc quan: funding fee CHƯA tính. Quét ngưỡng MARGIN_HALT {} -> {}.", START_DATE, END_DATE);

        long startTime = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
        long endTime = Utils.sdfFile.parse(END_DATE).getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;

        SimpleSymbolMapper.getInstance().init();
        LOG.info("📥 Nạp data Aerospike (market / AI-pred / funding-pred)...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("✅ market={} pred={} funding={}", time2MarketData.size(), predictionMap.size(), time2FundingPre.size());

        List<Row> rows = new ArrayList<>();
        for (Cfg cfg : cfgs) {
            Configs.BREAKER_MODE = cfg.on ? "MARGIN" : "OFF";
            if (cfg.on) Configs.BREAKER_MARGIN_HALT = cfg.halt;
            LOG.info("\n================= ▶️ CHẠY {} (mode={} halt={}) =================",
                    cfg.name, Configs.BREAKER_MODE, cfg.on ? cfg.halt : "n/a");

            BudgetManagerSimple.resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();

            SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
            sim.initDataReady(time2MarketData, predictionMap, time2FundingPre, new AIRejectFilter());
            sim.simulatorWithInitEntry(startTime, endTime);

            rows.add(computeMetrics(cfg.name, sim));
        }

        // reset về mặc định sau khi chạy
        Configs.BREAKER_MODE = "OFF";
        Configs.BREAKER_MARGIN_HALT = 0.70f;

        printTable(rows);
    }

    private Row computeMetrics(String mode, SimulatorMarketLevelTicker1MStopLoss sim) {
        Row r = new Row();
        r.mode = mode;
        r.breakerMarginHalt = sim.breakerMarginHaltCount;

        if (sim.allOrderDone != null) {
            r.tradeCount = sim.allOrderDone.size();
            for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
                float pnl = o.calTp();
                r.totalPnl += pnl;
                int y = Utils.getYear(o.timeUpdate);
                r.yearPnl.merge(y, pnl, Float::sum);
            }
        }

        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        r.maxDrawdownTrue = (bm.trueUnrealizedMin != null) ? bm.trueUnrealizedMin : 0f;
        r.capital = (bm.balanceBasic != null && bm.balanceBasic > 0) ? bm.balanceBasic : 1f;
        r.balanceEnd = r.capital + r.totalPnl;
        r.yearDdTrue.putAll(bm.year2TrueUnrealizedMin);

        float maxRatio = 0f;
        for (Float marginMax : bm.balanceIndex.date2MarginMax.values()) {
            if (marginMax != null && marginMax / r.capital > maxRatio) maxRatio = marginMax / r.capital;
        }
        r.maxMarginRatio = maxRatio;
        return r;
    }

    private void printTable(List<Row> rows) {
        LOG.info("\n\n================= 📊 BẢNG QUÉT NGƯỠNG MARGIN_HALT ({} -> {}) =================", START_DATE, END_DATE);
        LOG.info("Chọn ngưỡng theo return/maxDD (Calmar-like) tốt nhất: chặn đủ để giảm DD nhưng không cắt quá nhiều PnL.");
        for (Row r : rows) {
            float calmar = (r.maxDrawdownTrue < 0) ? (r.totalPnl / -r.maxDrawdownTrue) : Float.NaN;
            LOG.info(String.format(Locale.US,
                    "─ %-10s | trades=%d | totalPnl=%s | maxDD_THẬT=%s (%.1f%%) | balEnd=%s | halt=%d | maxMargR=%.2f | return/maxDD=%.2f",
                    r.mode, r.tradeCount, fmt(r.totalPnl),
                    fmt(r.maxDrawdownTrue), r.maxDrawdownTrue / r.capital * 100f,
                    fmt(r.balanceEnd), r.breakerMarginHalt, r.maxMarginRatio, calmar));
            StringBuilder yb = new StringBuilder("    PnL/năm: ");
            for (int y : YEARS) {
                Float p = r.yearPnl.get(y);
                yb.append(y).append("=").append(p != null ? fmt(p) : "0").append("  ");
            }
            LOG.info(yb.toString());
            StringBuilder db = new StringBuilder("    maxDD_THẬT/năm: ");
            for (int y : YEARS) {
                Float t = r.yearDdTrue.get(y);
                db.append(y).append("=").append(t != null ? fmt(t) : "0").append("  ");
            }
            LOG.info(db.toString());
        }
        LOG.info("------------------------------------------------------------------------------------------");
        LOG.info("CÁCH ĐỌC:");
        LOG.info(" - 🔒 GATE: totalPnl của OFF PHẢI trùng baseline RunBreakerBacktest OFF (cùng commit/data).");
        LOG.info(" - return/maxDD CAO NHẤT = ngưỡng đáng chốt (đánh đổi tốt nhất giữa PnL giữ lại và DD cắt được).");
        LOG.info(" - HALT càng CHẶT (số nhỏ) → DD giảm nhiều nhưng cũng cắt nhiều cơ hội → PnL giảm. Tìm điểm cân.");
        LOG.info(" - maxMargR mục tiêu: kéo từ 0.99 (cháy gần hết vốn) xuống vùng an toàn (~0.70 hoặc thấp hơn).");
    }

    private static String fmt(float v) {
        return String.format(Locale.US, "%.0f", v);
    }

    private static class Row {
        String mode;
        int tradeCount = 0;
        float totalPnl = 0f;
        float maxDrawdownTrue = 0f;
        float capital = 1f;
        float balanceEnd = 0f;
        float maxMarginRatio = 0f;
        long breakerMarginHalt = 0;
        TreeMap<Integer, Float> yearPnl = new TreeMap<>();
        TreeMap<Integer, Float> yearDdTrue = new TreeMap<>();
    }
}
