package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.research.BudgetManagerSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * TASK-119 — unit test (chạy main() thủ công, repo không có JUnit suite; xem docs/rules/backtest.md §Tests).
 *
 * <p>Kiểm chứng metric REPORT-ONLY {@link BudgetManagerSimple#updateEquityMtm}:
 * <ol>
 *   <li><b>Case A (maxDD_mtm &gt; maxDD cũ):</b> 2 vị thế mở + giá rơi + realized đã tích luỹ rồi trả lại.
 *       maxDD cũ (|unProfitMin|) chỉ thấy đáy unrealized; maxDD_mtm thấy cả phần lãi realized bị nuốt →
 *       lớn hơn hẳn. Đây chính là cái maxDD cũ "hiểu nhẹ".</li>
 *   <li><b>Case B (MARGIN_CALL):</b> lỗ realized ăn hết vốn + còn vị thế mở → equity_mtm ≤ 0.5%·notional → cờ bật.</li>
 * </ol>
 * Số tổng hợp trực tiếp trên arithmetic của method (không cần Aerospike/data), chạy vài ms.
 */
public class MaxDDMtmChecker {

    private static final Logger LOG = LoggerFactory.getLogger(MaxDDMtmChecker.class);

    public static void main(String[] args) {
        boolean ok = true;
        ok &= caseA_maxDDMtmGreaterThanOld();
        ok &= caseB_marginCall();

        if (ok) {
            LOG.info("✅ TASK-119 MaxDDMtmChecker: TẤT CẢ CASE PASS");
            System.exit(0);
        } else {
            LOG.error("❌ TASK-119 MaxDDMtmChecker: CÓ CASE FAIL");
            System.exit(1);
        }
    }

    /**
     * Case A — 2 vị thế mở, giá rơi, có realized give-back → maxDD_mtm > maxDD cũ.
     *
     * Chuỗi tick (vốn=1000):
     *   t1: realized=0,   unreal@low=0             → equity 1000, đỉnh 1000
     *   t2: realized=+500 (thắng đã chốt), unreal 0 → equity 1500, đỉnh 1500
     *   t3: đã chốt lỗ bớt (realized 500→300) + 2 vị thế mở còn lỗ tạm -100 @low, notional 2000
     *       → equity = 1000+300-100 = 1200
     * maxDD cũ = |min unreal| = 100 (đáy unrealized). maxDD_mtm = 1500-1200 = 300 = 100 unreal + 200 realized bị nuốt.
     */
    private static boolean caseA_maxDDMtmGreaterThanOld() {
        BudgetManagerSimple.resetInstance();
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        bm.balanceBasic = 1000f;

        // t1
        bm.profit = 0f;
        bm.updateTrueUnrealizedMin(0f, 1L);
        bm.updateEquityMtm(0f, 0f, 1L);
        // t2 — thắng đã chốt (realized +500), chưa vị thế mở
        bm.profit = 500f;
        bm.updateTrueUnrealizedMin(0f, 2L);
        bm.updateEquityMtm(0f, 0f, 2L);
        // t3 — chốt lỗ bớt (realized 500→300) + 2 vị thế mở lỗ tạm -100 @low (mỗi con -50), notional 2000
        bm.profit = 300f;
        bm.updateTrueUnrealizedMin(-100f, 3L);
        bm.updateEquityMtm(-100f, 2000f, 3L);

        float oldMaxDD = Math.abs(bm.balanceIndex.unProfitMin);   // = 100
        float maxDDMtm = bm.maxDDMtm;                              // = 300
        boolean pass = Math.abs(oldMaxDD - 100f) < 1e-3
                && Math.abs(maxDDMtm - 300f) < 1e-3
                && maxDDMtm > oldMaxDD
                && !bm.marginCallHit;

        LOG.info("[Case A] maxDD cũ={} maxDD_mtm={} (kỳ vọng 100 & 300, mtm>cũ, no margin-call) → {}",
                oldMaxDD, maxDDMtm, pass ? "PASS" : "FAIL");
        return pass;
    }

    /**
     * Case B — lỗ realized ăn hết vốn + còn 2 vị thế mở → equity_mtm âm ≤ 0.5%·notional → MARGIN_CALL bật.
     * (Synthetic: cố ý dựng equity dưới maintenance để nghiệm thu logic cờ; ở 1x thật ca này hiếm.)
     */
    private static boolean caseB_marginCall() {
        BudgetManagerSimple.resetInstance();
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        bm.balanceBasic = 1000f;

        // đỉnh lành mạnh trước
        bm.profit = 0f;
        bm.updateEquityMtm(0f, 0f, 10L);
        // realized lỗ nặng ăn hết vốn (martingale chốt lỗ dồn) + 2 vị thế mở còn lỗ tạm, notional 100
        bm.profit = -1000f;
        bm.updateTrueUnrealizedMin(-5f, 11L);
        bm.updateEquityMtm(-5f, 100f, 11L);   // equity = 1000-1000-5 = -5 ≤ 0.005*100 = 0.5

        boolean pass = bm.marginCallHit
                && bm.timeMarginCall != null && bm.timeMarginCall == 11L
                && bm.minEquityMtm != null && Math.abs(bm.minEquityMtm - (-5f)) < 1e-3;

        LOG.info("[Case B] marginCallHit={} timeMarginCall={} minEquityMtm={} → {}",
                bm.marginCallHit, bm.timeMarginCall, bm.minEquityMtm, pass ? "PASS" : "FAIL");
        return pass;
    }
}
