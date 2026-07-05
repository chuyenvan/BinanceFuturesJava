package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Utils;

import java.util.Collection;
import java.util.TreeMap;

/**
 * TASK-043 — Fitness V4: CONSTRAINT-FIRST + Calmar mục tiêu + Sortino kiểm chứng.
 *
 * <p>KHÁC V3 (cộng-trừ penalty mềm nhiều trọng số → HPO luồn lách, nát hàm mục tiêu): V4 tách rõ
 * <b>mục tiêu</b> khỏi <b>ràng buộc</b>.
 * <ul>
 *   <li><b>Constraint cứng</b> (vi phạm = LOẠI, trả điểm rất âm, KHÔNG cộng-trừ): maxDD-cap,
 *       %lệnh-giữ-quá-lâu, %năm-dương, min-trade. Diễn đạt "điều tuyệt đối không chấp nhận".</li>
 *   <li><b>Mục tiêu</b> (1 số sạch để tối đa hóa): <b>Calmar = netPnl / maxDD</b>.</li>
 *   <li><b>Sortino</b>: TÍNH nhưng KHÔNG vào fitness — chỉ ghi vào report để kiểm chứng
 *       (Calmar cao mà Sortino thấp = lời nhờ vài cú may, gập ghềnh → cờ đỏ overfit).</li>
 * </ul>
 *
 * <p><b>Ngưỡng đặt từ SỐ THẬT</b> (MetricDistributionTool, gate cũ FULL 2021-2026, 70711 lệnh):
 * <ul>
 *   <li>maxDD hiện 58.24% vốn → MAX_DD_PCT = 0.65 (chặn tệ hơn rõ; mục tiêu là kéo xuống).</li>
 *   <li>holding p99=2d, %giữ>7d=0.31% → MAX_PCT_HELD_OVER_7D = 0.02 (2%, nới gấp ~6x mức hiện tại).</li>
 *   <li>%năm-dương hiện 100% → MIN_POS_YEAR_RATIO = 0.80 (≥5/6 năm; chống overfit 1 regime).</li>
 *   <li>min-trade giữ logic V3 (windowDays*0.33, sàn 5).</li>
 * </ul>
 * Ngưỡng là biến static — chỉnh được khi có thêm dữ liệu WFO. KHÔNG hardcode rải rác.
 */
public class HPOFitnessCalculatorV4 {

    // ===== NGƯỠNG CONSTRAINT (đặt từ số thật, chỉnh tập trung tại đây) =====
    public static float MAX_DD_PCT = 0.65f;            // maxDD > 65% vốn → loại (cháy)
    public static float MAX_PCT_HELD_OVER_7D = 0.02f;  // >2% số lệnh giữ quá 7 ngày → loại (giam vốn)
    public static float MIN_POS_YEAR_RATIO = 0.80f;    // <80% số năm dương → loại (không ổn định)
    public static int MIN_YEARS_FOR_RATIO = 2;         // chỉ áp %năm-dương khi backtest ≥2 năm
    public static long HELD_TOO_LONG = 7L * Utils.TIME_DAY;

    // điểm loại (rất âm, phân biệt lý do để debug; KHÔNG phải penalty mềm — chỉ để xếp đáy)
    private static final float REJECT_BASE = -100000f;

    public static class FitnessReport {
        public int tradeCount = 0;
        public float totalProfit = 0f;
        public float maxDrawdown = 0f;       // số dương (abs)
        public float netScore = 0f;          // = totalProfit (V4 không trừ penalty mềm)
        public float calmar = 0f;            // MỤC TIÊU
        public float sortino = 0f;           // KIỂM CHỨNG (không vào fitness)
        public float ddPct = 0f;
        public float pctHeldOver7d = 0f;
        public float posYearRatio = 0f;
        public float finalFitness = 0f;
        public String note = "";

        // 🟡 TASK-119 (REPORT-ONLY) — maxDD mark-to-market + MARGIN_CALL, đo SONG SONG, KHÔNG vào fitness/verdict.
        public float maxDDMtm = 0f;          // abs USD (drawdown equity_mtm từ đỉnh)
        public float ddPctMtm = 0f;          // maxDDMtm / vốn (so trực tiếp với ddPct cũ)
        public boolean marginCallHit = false;
        public float minEquityMtmPct = 1f;   // minEquity_mtm / vốn (1.0 = chưa từng có vị thế mở)
    }

    /**
     * TASK-113 — V4.1: đo ĐỦ metrics mọi nhánh + min-trade theo window THẬT.
     *
     * <p>Khác V4 (2 fix, công thức fitness GIỮ NGUYÊN từng nhánh):
     * <ul>
     *   <li><b>Reorder:</b> khối thống kê (totalProfit, pctHeldOver7d, ddPct/maxDrawdown, posYearRatio,
     *       calmar, sortino) tính TRƯỚC chuỗi constraint → nhánh bị loại sớm (TOO_FEW/BURN/...) vẫn có
     *       số thật trong report, không còn PnL bị che thành 0.</li>
     *   <li><b>Min-trade theo window thật:</b> caller truyền {@code windowDaysActual} từ range backtest
     *       của CHÍNH NÓ; bỏ hoàn toàn suy-windowDays-từ-span-lệnh (V4 cũ: genome dồn 10 lệnh trong 3
     *       ngày của window 90 ngày → span=3 → minTrades=5 → PASS ngược đời).</li>
     * </ul>
     * Bất biến: với cùng input + cùng windowDays, {@code finalFitness} V4.1 ≡ V4 (chỉ FitnessReport có
     * thêm số thật ở nhánh sentinel). Khác duy nhất: case min-trade khi windowDaysActual ≠ span-lệnh.
     *
     * @param allOrderDone     lệnh đã đóng của backtest (key = ts đóng lệnh)
     * @param windowDaysActual độ dài THẬT của range backtest (ngày) = max(1,(end−start)/TIME_DAY),
     *                         KHÔNG phải span lệnh
     * @return FitnessReport đủ metrics mọi nhánh (trừ ZERO_TRADES — không có lệnh để đo)
     */
    public static FitnessReport evaluateDetailed(TreeMap<Long, OrderTargetInfoTest> allOrderDone, int windowDaysActual) {
        FitnessReport r = new FitnessReport();
        if (allOrderDone == null || allOrderDone.isEmpty()) {
            r.finalFitness = REJECT_BASE; r.note = "ZERO_TRADES"; return r;
        }
        Collection<OrderTargetInfoTest> orders = allOrderDone.values();
        r.tradeCount = orders.size();
        int windowDays = Math.max(1, windowDaysActual);
        int minTrades = Math.max(5, (int) (windowDays * 0.33f));

        // ===== gom thống kê 1 lượt — TRƯỚC chuỗi constraint (V4.1): nhánh loại sớm vẫn có số thật =====
        long heldTooLong = 0;
        TreeMap<Integer, Double> pnlByYear = new TreeMap<>();
        TreeMap<Long, Double> pnlByDay = new TreeMap<>();
        for (OrderTargetInfoTest o : orders) {
            double tp = o.calTp();
            r.totalProfit += tp;
            if (o.timeUpdate - o.timeStart > HELD_TOO_LONG) heldTooLong++;
            pnlByYear.merge(Utils.getYear(o.timeUpdate), tp, Double::sum);
            pnlByDay.merge(o.timeUpdate / Utils.TIME_DAY, tp, Double::sum);
        }
        r.netScore = r.totalProfit;
        r.pctHeldOver7d = (float) heldTooLong / r.tradeCount;

        // maxDD toàn danh mục (số âm → abs)
        Float ddRaw = BudgetManagerSimple.getInstance().balanceIndex.unProfitMin;
        r.maxDrawdown = ddRaw != null ? Math.abs(ddRaw) : 0f;
        float absDD = Math.max(1f, r.maxDrawdown);
        float capital = BudgetManagerSimple.getInstance().balanceBasic;
        r.ddPct = capital > 0 ? r.maxDrawdown / capital : 0f;

        // 🟡 TASK-119 (REPORT-ONLY): copy maxDD_mtm + MARGIN_CALL từ BudgetManagerSimple — CHỈ điền report,
        //    KHÔNG dùng cho constraint/fitness bên dưới (verdict giữ đọc ddPct cũ).
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        r.maxDDMtm = bm.maxDDMtm != null ? bm.maxDDMtm : 0f;
        r.ddPctMtm = capital > 0 ? r.maxDDMtm / capital : 0f;
        r.marginCallHit = bm.marginCallHit;
        r.minEquityMtmPct = (bm.minEquityMtm != null && capital > 0) ? bm.minEquityMtm / capital : 1f;

        // %năm-dương
        long posYears = pnlByYear.values().stream().filter(x -> x > 0).count();
        r.posYearRatio = pnlByYear.isEmpty() ? 0f : (float) posYears / pnlByYear.size();

        // Calmar (mục tiêu) + Sortino (kiểm chứng)
        r.calmar = r.netScore / absDD;
        r.sortino = computeSortino(pnlByDay);

        // ===== CONSTRAINT CỨNG (vi phạm = loại, KHÔNG cộng-trừ) — thứ tự + công thức GIỮ NGUYÊN V4 =====
        if (r.tradeCount < minTrades) {
            r.finalFitness = REJECT_BASE + r.tradeCount; r.note = "TOO_FEW_TRADES"; return r;
        }
        if (r.totalProfit <= 0) { r.finalFitness = REJECT_BASE + r.totalProfit; r.note = "BURN_ACCOUNT"; return r; }
        if (r.ddPct > MAX_DD_PCT) { r.finalFitness = REJECT_BASE - r.ddPct * 100; r.note = "OVER_MAXDD"; return r; }
        if (r.pctHeldOver7d > MAX_PCT_HELD_OVER_7D) {
            r.finalFitness = REJECT_BASE - r.pctHeldOver7d * 100; r.note = "TOO_MUCH_CAPITAL_LOCK"; return r;
        }
        // CHỈ áp %năm-dương khi backtest đủ DÀI theo RANGE THẬT (≥ MIN_YEARS_FOR_RATIO năm), KHÔNG dựa
        // pnlByYear.size(). Cửa sổ WFO 12 tháng (~365 ngày) có thể chạm 2 NĂM LỊCH do tràn biên (lệch
        // GMT+7 + lệnh mở cuối năm đóng sang đầu năm sau) → size()=2 nhưng không phải 2 năm thực →
        // trước đây loại oan genome tốt (UNSTABLE giả). Ổn định qua nhiều năm là việc của vế OOS-qua-
        // window của WFO, không phải IS 1 năm. Ràng buộc này chỉ còn hiệu lực cho backtest full đa năm.
        double spanYears = windowDays / 365.0;
        if (spanYears >= MIN_YEARS_FOR_RATIO && r.posYearRatio < MIN_POS_YEAR_RATIO) {
            r.finalFitness = REJECT_BASE - (1 - r.posYearRatio) * 100; r.note = "UNSTABLE_ACROSS_YEARS"; return r;
        }

        // ===== QUA HẾT CONSTRAINT → fitness = Calmar thuần (1 số sạch) =====
        r.finalFitness = r.calmar;
        r.note = "SUCCESS";
        return r;
    }

    /** Sortino theo chuỗi PnL NGÀY của danh mục: meanDaily / downsideDeviation (chỉ phạt phiên âm). */
    private static float computeSortino(TreeMap<Long, Double> pnlByDay) {
        if (pnlByDay.isEmpty()) return 0f;
        double mean = pnlByDay.values().stream().mapToDouble(x -> x).average().orElse(0);
        double dsVar = 0; int dsN = 0;
        for (double v : pnlByDay.values()) if (v < 0) { dsVar += v * v; dsN++; }
        double dsDev = dsN > 0 ? Math.sqrt(dsVar / dsN) : 0;
        return dsDev > 1e-9 ? (float) (mean / dsDev) : 0f;
    }
}
