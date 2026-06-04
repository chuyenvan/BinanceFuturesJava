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
 * ABLATION FILTER: chạy backtest 4 mode (A/B/C/D) trên CÙNG giai đoạn, CÙNG predict, CÙNG data,
 * chỉ khác {@code Configs.FILTER_MODE}. Đo xem bỏ nhánh RISK(DD4H) / MOM24 có làm XẤU ĐUÔI không.
 *
 * A=full | B=bỏ RISK | C=bỏ MOM24 | D=bỏ cả RISK+MOM24 (chỉ 15M+EARLY).
 *
 * NGUYÊN TẮC (đọc CẠM BẪY trong yêu cầu):
 *  - 4 run y hệt nhau trừ FILTER_MODE: load data MỘT lần, KHÔNG override tham số tuning nào
 *    (Configs giữ nguyên hiện trạng => mode A = hành vi live).
 *  - Mọi run đi qua BacktestIntegrityGuard (đã cắm trong simulatorWithInitEntry): look-ahead off,
 *    APPLY_SLIPPAGE=true, fee 2 chân. Pre-flight log + chặn nếu cấu hình ảo.
 *  - ĐỪNG đọc PnL tổng để kết luận. Trọng tâm: maxDrawdown + worstSingleLoss + số-ngày-gần-cháy.
 *  - KHÔNG bump CONFIG_VERSION (ablation filter, không đổi model/predict).
 *
 * Nguồn data = Aerospike (live-faithful): IS_KAGGLE_MODE=false (simulator đọc ticker từ Aerospike),
 * market/AI-pred/funding-pred từ getAll*FromAerospike — giống live + ValidateBrakeDynamic.
 */
public class RunFilterAblation {

    private static final Logger LOG = LoggerFactory.getLogger(RunFilterAblation.class);

    // ⚙️ Giai đoạn đo — CHỈNH để phủ rộng đuôi (càng dài càng dễ gặp cú sập hiếm).
    private static final String START_DATE = "20251001";
    private static final String END_DATE = "20260430";

    private static final String[] MODES = {"A", "B", "C", "D"};

    public static void main(String[] args) {
        try {
            new RunFilterAblation().run();
        } catch (Exception e) {
            LOG.error("Ablation error", e);
        }
    }

    public void run() throws Exception {
        // Cấu hình chạy thuần, nguồn Aerospike (không Kaggle file). KHÔNG đụng tham số tuning nào.
        Configs.IS_HPO_MODE = false;
        Configs.IS_KAGGLE_MODE = false;
        Configs.TIME_RUN = START_DATE;

        // ----- PRE-FLIGHT: xác nhận cấu hình KHÔNG ảo (guard sẽ throw nếu sai, nhưng log sớm cho rõ) -----
        LOG.info("🔒 INTEGRITY PRE-FLIGHT: BLOCK_INTRABAR_LOOKAHEAD={} APPLY_SLIPPAGE={} SLIPPAGE_RATE={} RATE_FEE={}",
                Configs.BLOCK_INTRABAR_LOOKAHEAD, Configs.APPLY_SLIPPAGE, Configs.SLIPPAGE_RATE, Configs.RATE_FEE);
        if (!Configs.BLOCK_INTRABAR_LOOKAHEAD || !Configs.APPLY_SLIPPAGE || Configs.RATE_FEE <= 0f) {
            LOG.error("⛔ Cấu hình ảo (look-ahead/slippage/fee tắt) — DỪNG. So sánh ablation sẽ vô nghĩa.");
            return;
        }

        long startTime = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
        long endTime = Utils.sdfFile.parse(END_DATE).getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;

        // ----- LOAD DATA MỘT LẦN, dùng chung cho cả 4 mode (read-only) -----
        SimpleSymbolMapper.getInstance().init();
        LOG.info("📥 Nạp data từ Aerospike (market / AI-pred / funding-pred)...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("✅ market={} pred={} funding={} | giai đoạn {} -> {}",
                time2MarketData.size(), predictionMap.size(), time2FundingPre.size(), START_DATE, END_DATE);
        if (time2FundingPre.isEmpty()) {
            LOG.warn("⚠️ funding-pred RỖNG -> symbolPred null hàng loạt -> nhánh EARLY mất tác dụng, lệch live. Kiểm tra Aerospike trước khi tin kết quả.");
        }

        List<Row> rows = new ArrayList<>();
        for (String mode : MODES) {
            Configs.FILTER_MODE = mode;   // KHÁC BIỆT DUY NHẤT giữa 4 run (A/C giữ RISK; B/D bỏ RISK. MOM24 đã bỏ khỏi hệ)
            LOG.info("\n================= ▶️ CHẠY MODE {} (FILTER_MODE={}) =================", mode, mode);

            // reset y hệt BackTestEngineMaster.run để mỗi mode bắt đầu sạch
            BudgetManagerSimple.resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();

            SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
            AIRejectFilter filter = new AIRejectFilter();   // KHÔNG setConfig -> dùng đúng Configs hiện trạng
            sim.initDataReady(time2MarketData, predictionMap, time2FundingPre, filter);
            sim.simulatorWithInitEntry(startTime, endTime);  // guard liêm chính chạy ở đây

            rows.add(computeMetrics(mode, sim));
        }

        printTable(rows);
    }

    // ====================== METRIC (đúng cho martingale, KHÔNG dùng win-rate) ======================
    private Row computeMetrics(String mode, SimulatorMarketLevelTicker1MStopLoss sim) {
        Row r = new Row();
        r.mode = mode;

        double sumWin = 0, sumLossAbs = 0;
        int nWin = 0, nLoss = 0;
        float worst = 0f;
        if (sim.allOrderDone != null) {
            for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
                float pnl = o.calTp();           // P&L thực hiện của lệnh/cụm khi đóng
                r.totalPnl += pnl;
                if (pnl >= 0) { sumWin += pnl; nWin++; }
                else { sumLossAbs += -pnl; nLoss++; }
                if (pnl < worst) worst = pnl;    // lỗ nặng nhất (âm nhất)
            }
            r.tradeCount = sim.allOrderDone.size();
        }
        r.worstSingleLoss = worst;
        r.profitFactor = (sumLossAbs > 0) ? (float) (sumWin / sumLossAbs) : (sumWin > 0 ? Float.POSITIVE_INFINITY : 0f);
        float avgWin = nWin > 0 ? (float) (sumWin / nWin) : 0f;
        float avgLoss = nLoss > 0 ? (float) (sumLossAbs / nLoss) : 0f;
        r.payoffRatio = (avgLoss > 0) ? avgWin / avgLoss : (avgWin > 0 ? Float.POSITIVE_INFINITY : 0f);

        // maxDrawdown danh mục + đếm ngày chạm "vùng bóp vốn 2" (margin/vốn >= BUDGET_MARGIN_RATIO_2)
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        r.maxDrawdown = (bm.balanceIndex.unProfitMin != null) ? bm.balanceIndex.unProfitMin : 0f;
        float capital = (bm.balanceBasic != null && bm.balanceBasic > 0) ? bm.balanceBasic : 1f;
        int nearLiq = 0;
        float maxRatio = 0f;
        for (Float marginMax : bm.balanceIndex.date2MarginMax.values()) {
            if (marginMax == null) continue;
            float ratio = marginMax / capital;
            if (ratio > maxRatio) maxRatio = ratio;
            if (ratio >= Configs.BUDGET_MARGIN_RATIO_2) nearLiq++;
        }
        r.nearLiqDays = nearLiq;
        r.maxMarginRatio = maxRatio;
        return r;
    }

    private void printTable(List<Row> rows) {
        LOG.info("\n\n================= 📊 BẢNG ABLATION FILTER ({} -> {}) =================", START_DATE, END_DATE);
        LOG.info("Bóp vốn 2 = số NGÀY có margin-max/vốn >= BUDGET_MARGIN_RATIO_2 ({}). Trọng tâm: maxDD + worstLoss + nearLiq2.",
                Configs.BUDGET_MARGIN_RATIO_2);
        LOG.info(String.format(Locale.US, "%-6s %8s %12s %8s %12s %12s %8s %8s %9s",
                "MODE", "trades", "totalPnl", "PF", "maxDD", "worstLoss", "payoff", "nearLiq2", "maxMargR"));
        for (Row r : rows) {
            LOG.info(String.format(Locale.US, "%-6s %8d %12.1f %8s %12.1f %12.1f %8s %8d %9.2f",
                    r.mode, r.tradeCount, r.totalPnl, fmt(r.profitFactor), r.maxDrawdown, r.worstSingleLoss,
                    fmt(r.payoffRatio), r.nearLiqDays, r.maxMarginRatio));
        }
        LOG.info("------------------------------------------------------------------------------------------");
        LOG.info("CÁCH ĐỌC: D≈A ở (maxDD, worstLoss, nearLiq2) => bỏ 24H+DD4H AN TOÀN, đơn giản hoá filter.");
        LOG.info("          D xấu hơn A rõ ở đuôi => GIỮ (đã có số chứng minh). So B vs C để biết nhánh nào đáng giữ.");
        LOG.info("          ⚠️ totalPnl cao hơn KHÔNG có nghĩa tốt hơn — bỏ lá chắn thường tăng PnL mà xấu đuôi.");
    }

    private static String fmt(float v) {
        if (Float.isInfinite(v)) return "INF";
        return String.format(Locale.US, "%.2f", v);
    }

    private static class Row {
        String mode;
        int tradeCount = 0;
        float totalPnl = 0f;
        float profitFactor = 0f;
        float maxDrawdown = 0f;
        float worstSingleLoss = 0f;
        float payoffRatio = 0f;
        int nearLiqDays = 0;
        float maxMarginRatio = 0f;
    }
}
