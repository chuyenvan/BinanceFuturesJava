package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.TreeMap;

/**
 * TASK-113 — GATE tầng 1: unit-test fitness V4.1 (main + SLF4J, KHÔNG cần Aerospike/Oracle).
 *
 * <p>5 case (A-E) dùng lệnh tổng hợp (symbol=null tránh SimpleSymbolMapper → Aerospike):
 * <ul>
 *   <li><b>A</b>: 60 lệnh rải 90 ngày, profit dương, DD nhỏ → SUCCESS, fitness = calmar (so tính tay ±1e-3).</li>
 *   <li><b>B</b>: 8 lệnh window 90d → TOO_FEW, fitness=ramp V4.2 REJECT_BASE·(1−8/29)≈−72413.79, <b>totalProfit thật ≠ 0</b> (fix #1 reorder).</li>
 *   <li><b>C</b>: 10 lệnh dồn 3 ngày, windowDaysActual=90 → V4 cũ (span) PASS; V4.1 (window thật) TOO_FEW (fix #2).</li>
 *   <li><b>D</b>: profit ≤ 0 → BURN_ACCOUNT, <b>ddPct được điền thật</b> (fix #1 reorder), fitness=REJECT+profit.</li>
 *   <li><b>E</b>: pctHeld>2% profit dương → CAPITAL_LOCK, <b>totalProfit thật ≠ 0</b> (fix #1 reorder).</li>
 * </ul>
 */
public class TestFitnessV41 {

    private static final Logger LOG = LoggerFactory.getLogger(TestFitnessV41.class);

    // REJECT_BASE (khớp HPOFitnessCalculatorV4 — không import private constant)
    private static final float REJECT_BASE = -100000f;
    // priceEntry cố định để calTp() trả ra targetProfit chính xác (xem makeOrder)
    private static final float PRICE_ENTRY = 1000f;
    // Base timestamp: 2024-01-01 00:00 UTC
    private static final long T0 = 1704067200000L;

    public static void main(String[] args) {
        LOG.info("===== TestFitnessV41 GATE tầng 1 (A-E) =====");
        int pass = 0, fail = 0;
        if (caseA()) pass++; else fail++;
        if (caseB()) pass++; else fail++;
        if (caseC()) pass++; else fail++;
        if (caseD()) pass++; else fail++;
        if (caseE()) pass++; else fail++;
        LOG.info("===== KẾT QUẢ: {}/5 PASS, {} FAIL =====", pass, fail);
        if (fail > 0) {
            LOG.error("GATE tầng 1 FAIL — {} case thất bại", fail);
            System.exit(1);
        }
        LOG.info("GATE tầng 1 PASS ✅");
        System.exit(0);
    }

    // ===== Case A: 60 lệnh rải 90 ngày → SUCCESS, fitness = calmar =====
    private static boolean caseA() {
        LOG.info("----- Case A: 60 lệnh 90d → SUCCESS, fitness=calmar -----");
        int windowDays = 90;
        int nOrders = 60;
        float profitPerOrder = 5f;
        float ddAbs = 100f;
        float capital = 35000f;

        TreeMap<Long, OrderTargetInfoTest> orders = new TreeMap<>();
        long stepMs = (long) windowDays * Utils.TIME_DAY / nOrders;
        for (int i = 0; i < nOrders; i++) {
            long ts = T0 + i * stepMs;
            orders.put(ts, makeOrder(ts, ts + 12 * Utils.TIME_HOUR, profitPerOrder));
        }

        setBudget(ddAbs, capital);
        HPOFitnessCalculatorV4.FitnessReport r = HPOFitnessCalculatorV4.evaluateDetailed(orders, windowDays);

        float expectedTotalProfit = nOrders * profitPerOrder;    // 300
        float expectedCalmar     = expectedTotalProfit / ddAbs;  // 3.0
        LOG.info("  note={} fitness={} calmar={} totalProfit={} ddPct={}",
                r.note, r.finalFitness, r.calmar, r.totalProfit, r.ddPct);

        boolean ok = "SUCCESS".equals(r.note)
                && Math.abs(r.finalFitness - expectedCalmar) < 1e-3f
                && Math.abs(r.calmar - expectedCalmar) < 1e-3f
                && Math.abs(r.totalProfit - expectedTotalProfit) < 1e-2f;
        LOG.info("  Case A: {}", ok ? "PASS ✅" : "FAIL ❌");
        return ok;
    }

    // ===== Case B: 8 lệnh window 90d → TOO_FEW, totalProfit thật ≠ 0 =====
    private static boolean caseB() {
        LOG.info("----- Case B: 8 lệnh 90d → TOO_FEW, totalProfit thật (fix #1) -----");
        int windowDays = 90;
        int nOrders = 8;
        float profitPerOrder = 20f;

        TreeMap<Long, OrderTargetInfoTest> orders = new TreeMap<>();
        for (int i = 0; i < nOrders; i++) {
            long ts = T0 + (long) i * 3 * Utils.TIME_DAY;
            orders.put(ts, makeOrder(ts, ts + 12 * Utils.TIME_HOUR, profitPerOrder));
        }

        setBudget(0f, 35000f);
        HPOFitnessCalculatorV4.FitnessReport r = HPOFitnessCalculatorV4.evaluateDetailed(orders, windowDays);

        // V4.2: TOO_FEW cliff → ramp tỉ lệ REJECT_BASE·(1 − tradeCount/minTrades).
        // minTrades=max(5,(int)(90*0.33))=29 → REJECT_BASE·(1 − 8/29) ≈ -72413.79 (cũ V4.1: -99992).
        int minTrades             = Math.max(5, (int) (windowDays * 0.33f));  // 29
        float expectedFitness     = REJECT_BASE * (1f - (float) nOrders / minTrades);  // ≈ -72413.79
        float expectedTotalProfit = nOrders * profitPerOrder;         // 160
        LOG.info("  note={} fitness={} (expected ramp {}) totalProfit={} (expected totalProfit≠0)",
                r.note, r.finalFitness, expectedFitness, r.totalProfit);

        // totalProfit phải là số thật (≠ 0) — đây là điểm fix #1
        boolean ok = "TOO_FEW_TRADES".equals(r.note)
                && Math.abs(r.finalFitness - expectedFitness) < 1f
                && Math.abs(r.totalProfit - expectedTotalProfit) < 1e-2f;
        LOG.info("  Case B: {}", ok ? "PASS ✅" : "FAIL ❌");
        return ok;
    }

    // ===== Case C: 10 lệnh dồn 3 ngày, window=90d → V4 cũ PASS; V4.1 TOO_FEW =====
    private static boolean caseC() {
        LOG.info("----- Case C: 10 lệnh/3d window=90d → V4(span) PASS; V4.1(window) TOO_FEW (fix #2) -----");
        int windowDays = 90;
        int nOrders = 10;
        long spanDays = 3L;   // dồn cục trong 3 ngày của window 90 ngày
        long stepMs = spanDays * Utils.TIME_DAY / nOrders;

        TreeMap<Long, OrderTargetInfoTest> orders = new TreeMap<>();
        for (int i = 0; i < nOrders; i++) {
            long ts = T0 + i * stepMs;
            orders.put(ts, makeOrder(ts, ts + 12 * Utils.TIME_HOUR, 20f));
        }

        setBudget(0f, 35000f);
        HPOFitnessCalculatorV4.FitnessReport r = HPOFitnessCalculatorV4.evaluateDetailed(orders, windowDays);

        // V4.1: windowDaysActual=90 → minTrades=max(5,(int)(90*0.33))=max(5,29)=29 → 10<29 → TOO_FEW
        // V4 cũ: span=(max_ts-min_ts)/TIME_DAY=3d → minTrades=max(5,(int)(3*0.33))=max(5,0)=5 → 10>=5 → PASS
        int minTradesOld  = Math.max(5, (int)(spanDays * 0.33f));    // = 5 (span=3d)
        int minTradesNew  = Math.max(5, (int)(windowDays * 0.33f));  // = 29 (window=90d)
        LOG.info("  minTrades V4-cũ(span={}d)={} vs V4.1(window={}d)={} | 10<{} → V4.1 TOO_FEW={}",
                spanDays, minTradesOld, windowDays, minTradesNew, minTradesNew,
                "TOO_FEW_TRADES".equals(r.note));
        LOG.info("  note={} fitness={}", r.note, r.finalFitness);

        boolean v41IsTooFew = "TOO_FEW_TRADES".equals(r.note);
        boolean v4OldWouldPass = nOrders >= minTradesOld;  // 10 >= 5 = true
        LOG.info("  Case C: {} (V4-cũ sẽ PASS={}, V4.1 đúng TOO_FEW={})",
                (v41IsTooFew && v4OldWouldPass) ? "PASS ✅" : "FAIL ❌", v4OldWouldPass, v41IsTooFew);
        return v41IsTooFew && v4OldWouldPass;
    }

    // ===== Case D: profit ≤ 0 → BURN_ACCOUNT, ddPct điền thật (fix #1) =====
    private static boolean caseD() {
        LOG.info("----- Case D: profit ≤ 0 → BURN, ddPct được điền thật (fix #1) -----");
        int windowDays = 30;
        int nOrders = 30;
        float profitPerOrder = -2f;  // mỗi lệnh lỗ 2
        float ddAbs = 200f;
        float capital = 35000f;

        TreeMap<Long, OrderTargetInfoTest> orders = new TreeMap<>();
        long stepMs = (long) windowDays * Utils.TIME_DAY / nOrders;
        for (int i = 0; i < nOrders; i++) {
            long ts = T0 + i * stepMs;
            orders.put(ts, makeOrder(ts, ts + 6 * Utils.TIME_HOUR, profitPerOrder));
        }

        setBudget(ddAbs, capital);
        HPOFitnessCalculatorV4.FitnessReport r = HPOFitnessCalculatorV4.evaluateDetailed(orders, windowDays);

        float expectedTotalProfit = nOrders * profitPerOrder;          // -60
        float expectedFitness     = REJECT_BASE + expectedTotalProfit; // -100060
        LOG.info("  note={} fitness={} totalProfit={} ddPct={} (expected ddPct>0)",
                r.note, r.finalFitness, r.totalProfit, r.ddPct);

        // ddPct phải được điền thật — đây là điểm fix #1 (reorder thống kê trước constraint)
        boolean ok = "BURN_ACCOUNT".equals(r.note)
                && Math.abs(r.finalFitness - expectedFitness) < 1f
                && Math.abs(r.totalProfit - expectedTotalProfit) < 1e-2f
                && r.ddPct > 0f;
        LOG.info("  Case D: {}", ok ? "PASS ✅" : "FAIL ❌");
        return ok;
    }

    // ===== Case E: pctHeld>2% profit dương → CAPITAL_LOCK, totalProfit thật =====
    private static boolean caseE() {
        LOG.info("----- Case E: pctHeld>2% profit dương → CAPITAL_LOCK, totalProfit thật (fix #1) -----");
        int windowDays = 90;
        int nOrders = 30;
        float profitPerOrder = 5f;

        TreeMap<Long, OrderTargetInfoTest> orders = new TreeMap<>();
        long stepMs = (long) windowDays * Utils.TIME_DAY / nOrders;
        for (int i = 0; i < nOrders; i++) {
            long ts = T0 + i * stepMs;
            // 2 lệnh đầu held 8 ngày (>7d) → heldTooLong; còn lại held 12h
            long holdMs = (i < 2) ? 8L * Utils.TIME_DAY : 12L * Utils.TIME_HOUR;
            orders.put(ts, makeOrder(ts, ts + holdMs, profitPerOrder));
        }

        setBudget(50f, 35000f);
        HPOFitnessCalculatorV4.FitnessReport r = HPOFitnessCalculatorV4.evaluateDetailed(orders, windowDays);

        float expectedTotalProfit = nOrders * profitPerOrder;   // 150
        float expectedPctHeld     = 2f / nOrders;               // 2/30 ≈ 6.67%
        LOG.info("  note={} fitness={} totalProfit={} pctHeld>7d={} (expected {})",
                r.note, r.finalFitness, r.totalProfit, r.pctHeldOver7d, expectedPctHeld);

        // totalProfit phải là số thật (≠ 0) — đây là điểm fix #1
        boolean ok = "TOO_MUCH_CAPITAL_LOCK".equals(r.note)
                && Math.abs(r.totalProfit - expectedTotalProfit) < 1e-2f
                && Math.abs(r.pctHeldOver7d - expectedPctHeld) < 1e-4f;
        LOG.info("  Case E: {}", ok ? "PASS ✅" : "FAIL ❌");
        return ok;
    }

    // ========================= helpers =========================

    /**
     * Tạo order tổng hợp với calTp() = targetProfit CHÍNH XÁC.
     *
     * <p>priceTP được tính để bù đắp RATE_FEE và SLIPPAGE (nếu bật), đảm bảo
     * calTp() == targetProfit bất kể cấu hình Configs. symbol=null → tránh SimpleSymbolMapper → Aerospike.
     */
    private static OrderTargetInfoTest makeOrder(long timeStart, long timeUpdate, float targetProfit) {
        // calTp() = qty*(priceTP-priceEntry) - qty*priceEntry*RATE_FEE - (APPLY_SLIPPAGE ? qty*priceEntry*SLIPPAGE_RATE*2 : 0)
        // Đặt priceTP = priceEntry + RATE_FEE*priceEntry + (slippage)*2 + targetProfit
        // → calTp() trả ra đúng targetProfit
        float deductions = PRICE_ENTRY * Configs.RATE_FEE
                + (Configs.APPLY_SLIPPAGE ? PRICE_ENTRY * Configs.SLIPPAGE_RATE * 2f : 0f);
        float priceTP = PRICE_ENTRY + deductions + targetProfit;
        return new OrderTargetInfoTest(
                OrderTargetStatus.TAKE_PROFIT_DONE,
                PRICE_ENTRY, priceTP,
                1f, 1, null,    // symbol=null: bỏ qua SimpleSymbolMapper (không cần Aerospike)
                timeStart, timeUpdate, OrderSide.BUY
        );
    }

    /** Reset BudgetManagerSimple và đặt DD + capital thủ công cho test. */
    private static void setBudget(float ddAbs, float capital) {
        BudgetManagerSimple.resetInstance();
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        bm.balanceBasic = capital;
        // unProfitMin âm = đáy unrealized; Math.abs() cho maxDrawdown trong V4.1
        bm.balanceIndex.unProfitMin = ddAbs > 0f ? -ddAbs : 0f;
    }
}
