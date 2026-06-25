package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Locale;
import java.util.Map;
import java.util.TreeMap;

/**
 * TASK-111 — BASELINE HÀM MỤC TIÊU: chạy các chiến lược THAM CHIẾU, mỗi cái cho ra ĐẦY ĐỦ
 * {@link HPOFitnessCalculatorV4.FitnessReport} + chuỗi PnL per-quý mark-to-market, in bảng đối chiếu.
 *
 * <p><b>Mục đích (Uni nêu):</b> hàm mục tiêu hiện chưa có BASELINE để biết "Calmar=X là giỏi hay may",
 * và chưa được VALIDATE là xếp hạng đúng. Tool này tạo baseline đó:
 * <ul>
 *   <li><b>A</b> = cấu hình AI thật (control).</li>
 *   <li><b>B</b> = no-filter (mọi tín hiệu PASS) — sàn "DCA trần trụi".</li>
 *   <li><b>C</b> = placebo random cùng passRate — sàn "không có chọn lọc".</li>
 * </ul>
 * <b>Kiểm chứng hàm mục tiêu:</b> nếu V4 đúng, finalFitness phải xếp A &gt; C và A &gt; B (random/no-filter
 * KHÔNG được xếp trên cấu hình thật). Nếu V4 xếp sai → hàm mục tiêu hỏng, sửa trước khi HPO.
 *
 * <p>Đồng thời in chuỗi PnL per-quý (lấy từ BudgetManagerSimple.quarter2EquityLast) để Uni xem
 * PHÂN PHỐI lãi/quý THẬT — dữ liệu quyết định ngưỡng ổn-định (vd %quý dương, trần lỗ/quý) thay vì
 * đặt mục tiêu tuyệt đối kiểu "5%/quý" (đã thống nhất là sai/nguy hiểm).
 *
 * <p>Chạy Oracle. Arg: FAST (2025-10..2026-04) | FULL (2021..2026). Read-only Aerospike.
 */
public class FitnessBaselineTool {

    private static final Logger LOG = LoggerFactory.getLogger(FitnessBaselineTool.class);
    private static final String FAST_START = "20251001", FAST_END = "20260430";
    private static final String FULL_START = "20210101", FULL_END = "20260601";

    public static void main(String[] args) {
        try {
            Configs.IS_HPO_MODE = false;
            Configs.IS_KAGGLE_MODE = false;
            Configs.BREAKER_MODE = "OFF";
            String mode = args.length > 0 ? args[0] : "FAST";
            new FitnessBaselineTool().run(mode);
            System.exit(0);
        } catch (Exception e) {
            LOG.error("FitnessBaselineTool loi", e);
            System.exit(1);
        }
    }

    void run(String mode) throws Exception {
        String start = mode.equalsIgnoreCase("FULL") ? FULL_START : FAST_START;
        String end = mode.equalsIgnoreCase("FULL") ? FULL_END : FAST_END;
        long s = Utils.sdfFile.parse(start).getTime() + 7 * Utils.TIME_HOUR;
        long e = Utils.sdfFile.parse(end).getTime() + 24 * Utils.TIME_HOUR - Utils.TIME_MINUTE;

        LOG.info("Nap data 1 lan (dung chung)...");
        TreeMap<Long, MarketDataObject> mkt = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> pred = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> fund = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("market={} pred={} funding={}", mkt.size(), pred.size(), fund.size());

        // A truoc (do passRate cap cho C placebo)
        Eval a = runOne("A", mkt, pred, fund, s, e, 0.5f);
        float passRateA = a.passRate > 0 ? a.passRate : 0.5f;
        Eval b = runOne("B", mkt, pred, fund, s, e, passRateA);
        Eval c = runOne("C", mkt, pred, fund, s, e, passRateA);

        // ===== BANG TONG HOP FITNESS V4 =====
        LOG.info("======================= FITNESS V4 BASELINE ({}) =======================", mode);
        LOG.info(String.format("%-3s | %7s | %10s | %9s | %7s | %7s | %7s | %8s | %s",
                "CFG", "trades", "totalPnl", "maxDD", "ddPct", "calmar", "sortino", "posYear%", "fitness/note"));
        for (Eval ev : new Eval[]{a, b, c}) {
            HPOFitnessCalculatorV4.FitnessReport r = ev.report;
            LOG.info(String.format(Locale.US, "%-3s | %7d | %10.1f | %9.1f | %6.1f%% | %7.3f | %7.3f | %7.1f%% | %.3f (%s)",
                    ev.mode, r.tradeCount, r.totalProfit, r.maxDrawdown, r.ddPct * 100,
                    r.calmar, r.sortino, r.posYearRatio * 100, r.finalFitness, r.note));
        }
        LOG.info("========================================================================");

        // ===== KIEM CHUNG HAM MUC TIEU: A phai xep tren B va C =====
        boolean aBeatsC = a.report.finalFitness > c.report.finalFitness;
        boolean aBeatsB = a.report.finalFitness > b.report.finalFitness;
        LOG.info("VALIDATE V4: A>C={} | A>B={}", aBeatsC, aBeatsB);
        if (aBeatsC && aBeatsB) {
            LOG.info("-> HAM MUC TIEU XEP HANG DUNG: cau hinh AI that xep tren random/no-filter. V4 tin duoc.");
        } else {
            LOG.info("-> CO BAO: V4 KHONG xep A len tren B/C -> ham muc tieu co the hong (hoac cau hinh AI yeu). Xem ky.");
        }

        // ===== CHUOI PER-QUY cho cau hinh A (de Uni xem phan phoi lai/quy) =====
        LOG.info("======================= PER-QUY cau hinh A (phan phoi lai/quy) =======================");
        printQuarters(a);
    }

    static class Eval {
        String mode;
        float passRate;
        HPOFitnessCalculatorV4.FitnessReport report;
        TreeMap<Integer, Float> quarterEquityLast;
        float capital;
    }

    private Eval runOne(String mode, TreeMap<Long, MarketDataObject> mkt, TreeMap<Long, AiPredictionData> pred,
                        TreeMap<Long, long[]> fund, long s, long e, float passRate) throws Exception {
        Configs.ABLATION_MODE = mode;
        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(mkt, pred, fund, new AIRejectFilter());
        sim.ablationPassRate = passRate;
        LOG.info("Chay mode {} (passRate={})...", mode, passRate);
        sim.simulatorWithInitEntry(s, e);

        Eval ev = new Eval();
        ev.mode = mode;
        ev.report = HPOFitnessCalculatorV4.evaluateDetailed(sim.allOrderDone);
        // passRate do tu sim (de cap cho C)
        long seen = sim.ablationSignalSeen;
        long passed = "C".equals(mode) ? sim.ablationPlaceboPass : sim.ablationPassCount;
        ev.passRate = seen > 0 ? (float) passed / seen : 0f;
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        ev.quarterEquityLast = new TreeMap<>(bm.quarter2EquityLast);
        ev.capital = bm.balanceBasic;
        LOG.info("   {} done: trades={} fitness={} note={}", mode, ev.report.tradeCount,
                String.format("%.3f", ev.report.finalFitness), ev.report.note);
        return ev;
    }

    private void printQuarters(Eval ev) {
        if (ev.quarterEquityLast.isEmpty()) { LOG.warn("Khong co du lieu per-quy"); return; }
        float prev = ev.capital;
        int pos = 0, total = 0;
        LOG.info("quy | equityEnd | PnL_quy | PnL_quy_%vonDauKy");
        for (Map.Entry<Integer, Float> en : ev.quarterEquityLast.entrySet()) {
            int qk = en.getKey();
            float eqEnd = en.getValue();
            float pnlQ = eqEnd - prev;
            float pctQ = prev != 0 ? pnlQ / Math.abs(prev) * 100 : 0;
            int year = qk / 10, q = qk % 10;
            LOG.info(String.format(Locale.US, "%d-Q%d | %.1f | %+.1f | %+.2f%%", year, q, eqEnd, pnlQ, pctQ));
            if (pnlQ > 0) pos++;
            total++;
            prev = eqEnd;
        }
        LOG.info("-> TONG {} quy | %quy duong = {}/{} = {}%", total, pos, total,
                String.format(Locale.US, "%.0f", 100.0 * pos / Math.max(1, total)));
    }
}
