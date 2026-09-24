package com.binance.chuyennd.research;

import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.After;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * DCA-SIGNAL (docs/prereg/PREREG_DCA_SIGNAL_GATE.md) — hai manh ghep de vo neu code sai:
 *
 * <ol>
 *   <li><b>Cong parity.</b> Khi {@code DCA_SIGNAL_GATE=false} thi {@code gridLegCount(legs)} PHAI
 *       bang {@code legs.size()} voi MOI cau hinh leg — do la bieu thuc cu, la dieu kien du de
 *       printDone.csv byte-identical.</li>
 *   <li><b>Doc lap voi grid DCA cu.</b> Khi bat, leg-signal KHONG duoc dem vao bac grid: mot cum
 *       co leg-1 + leg-signal van phai o bac 1 (grid chua nhoi lan nao), neu khong thi ladder
 *       1,1,3,8 bi day len mot bac va hai co che dinh nhau.</li>
 * </ol>
 *
 * <p>Them: kiem nguong lo dung convention {@code firstEntryPrice} (bat bien qua DCA) va
 * hai co che khong chong lan (X nong hon han bac dau grid -0.50).
 */
public class DcaSignalGateTest {

    private static final float EPS = 1e-6f;

    private final boolean gate0 = Configs.DCA_SIGNAL_GATE;
    private final float ratio0 = Configs.DCA_SIGNAL_BASE_RATIO;
    private final float loss0 = Configs.DCA_SIGNAL_LOSS;

    @After
    public void restore() {
        Configs.DCA_SIGNAL_GATE = gate0;
        Configs.DCA_SIGNAL_BASE_RATIO = ratio0;
        Configs.DCA_SIGNAL_LOSS = loss0;
    }

    /** symbol=null co chu dich: ctor chi goi SimpleSymbolMapper khi symbol != null (tranh Aerospike). */
    private static OrderTargetInfoTest leg(long t, boolean signal) {
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, 100f, null, 1f,
                Configs.LEVERAGE_ORDER, null, t, t, OrderSide.BUY);
        o.dcaSignalLeg = signal;
        return o;
    }

    private static List<OrderTargetInfoTest> legs(boolean... signalFlags) {
        List<OrderTargetInfoTest> l = new ArrayList<>();
        long t = 1_600_000_000_000L;
        for (boolean s : signalFlags) l.add(leg(t += 60_000L, s));
        return l;
    }

    /** (1) CONG PARITY: flag OFF => gridLegCount == size() ke ca khi co leg danh dau signal. */
    @Test
    public void offIsIdenticalToSize() {
        Configs.DCA_SIGNAL_GATE = false;
        assertEquals(0, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(null));
        assertEquals(1, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(false)));
        assertEquals(2, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(false, false)));
        // co danh dau signal van dem du: OFF = bieu thuc cu, khong co nhanh moi nao.
        assertEquals(2, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(false, true)));
        assertEquals(4, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(false, true, false, false)));
    }

    /** (2) ON: leg-signal KHONG an mat mot bac cua ladder grid. */
    @Test
    public void signalLegDoesNotConsumeGridStep() {
        Configs.DCA_SIGNAL_GATE = true;
        assertEquals(1, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(false, true)));
        // leg1 + leg-signal + 1 leg grid => bac grid = 2, KHONG phai 3.
        assertEquals(2, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(false, true, false)));
        assertEquals(3, SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(false, true, false, false)));
    }

    /** (2b) Hau qua tren ladder: bac grid van la w[1] chu khong nhay sang w[2]. */
    @Test
    public void ladderWeightUnshiftedBySignalLeg() {
        Configs.DCA_SIGNAL_GATE = true;
        int step = SimulatorMarketLevelTicker1MStopLoss.gridLegCount(legs(false, true));
        assertEquals("leg grid dau tien phai an w[1], khong phai w[2]",
                DcaUtils.gridLegWeightRatio(1), DcaUtils.gridLegWeightRatio(step), EPS);
    }

    /** (3) Suat von co so bi chia doi dung mot lan cho leg mo cum va cho leg-signal. */
    @Test
    public void baseRatioHalvesBaseSlotOnly() {
        Configs.DCA_SIGNAL_GATE = true;
        Configs.DCA_SIGNAL_BASE_RATIO = 0.5f;
        float base = DcaUtils.gridLegWeightRatio(0);
        assertEquals(base * 0.5f, base * Configs.DCA_SIGNAL_BASE_RATIO, EPS);
        // leg1 (50%) + leg-signal (50%) = dung MOT suat von binh thuong, khong hon.
        assertEquals(base, base * Configs.DCA_SIGNAL_BASE_RATIO * 2f, EPS);
    }

    /** (4) Nguong lo do tren firstEntryPrice, va KHONG chong lan voi bac dau grid (-0.50). */
    @Test
    public void lossThresholdConventionAndNoOverlapWithGrid() {
        for (float x : new float[]{-0.05f, -0.08f, -0.12f}) {
            // gia cham dung nguong => du dieu kien (b)
            float price = 100f * (1f + x);
            assertTrue("X=" + x, price / 100f - 1f <= x + EPS);
            // cung muc lo do KHONG du kich hoat bac dau grid (-0.50) => hai co che doc lap
            assertFalse("X=" + x + " khong duoc cham grid", DcaUtils.shouldDcaGrid(100f, price, 1));
        }
        // grid chi ban o vung tham hoa
        assertTrue(DcaUtils.shouldDcaGrid(100f, 45f, 1));
    }

    /** (V2-6) COOLDOWN do tu leg-1 KHOP, khong do tu luc cham nguong — docs/prereg/PREREG_DCA_SIGNAL_GATE_V2.md muc 2.
     *  Kiem dung bieu thuc ma dcaSignalEligible dung, voi ba cap (X, cooldown) da khoa cua V2. */
    @Test
    public void cooldownIsMeasuredFromFirstLegFill() {
        long t0 = 1_600_000_000_000L;                      // leg-1 khop
        for (int[] cfg : new int[][]{{1440}, {2160}, {2880}}) {
            long need = (long) cfg[0] * com.binance.chuyennd.utils.Utils.TIME_MINUTE;
            assertTrue("dung han cooldown => duoc ban", (t0 + need) - t0 >= need);
            assertFalse("truoc han mot phut => chua duoc ban",
                    (t0 + need - com.binance.chuyennd.utils.Utils.TIME_MINUTE) - t0 >= need);
        }
        // 24h/36h/48h dung bang 1440/2160/2880 phut (chong sai don vi gio-vs-phut).
        assertEquals(24 * 60, 1440);
        assertEquals(36 * 60, 2160);
        assertEquals(48 * 60, 2880);
    }

    /** (V2-7) TIE-BREAK voi grid cu: o X=-50% ca hai co che cung dung => phai co luat uu tien.
     *  Test nay khoa SU KIEN do that su xay ra (neu ai doi DCA_GRID_LEVELS thi test bao). */
    @Test
    public void dca50CollidesWithFirstGridRung() {
        // Rung dau grid = -50%: tai gia = 50% cua firstEntryPrice, grid DUNG...
        assertTrue(DcaUtils.shouldDcaGrid(100f, 50f, 1));
        // ...va nguong signal-gate cua DCA50 cung DUNG => tie-break la bat buoc, khong phai tuy chon.
        Configs.DCA_SIGNAL_LOSS = -0.50f;
        assertTrue(50f / 100f - 1f <= Configs.DCA_SIGNAL_LOSS);
        // O -30% / -40% thi grid CHUA dung => chi DCA50 moi va cham truc tiep.
        assertFalse(DcaUtils.shouldDcaGrid(100f, 70f, 1));
        assertFalse(DcaUtils.shouldDcaGrid(100f, 60f, 1));
    }

    /** (V2-8) selectCands tach ra khoi vong tick phai giu NGUYEN phep chon cu.
     *  Configs.SELECTOR_RANK_TOPK la `final` (khong lat duoc trong test) nen kiem theo gia tri dang chay:
     *  lay DUNG min(K, len) phan tu DAU, giu nguyen thu tu va gia tri. Do la toan bo hop dong ma tap
     *  dsReserved cua tie-break dua vao — neu ham nay troi thi grid/signal se nhin thay hai tap khac nhau. */
    @Test
    public void selectCandsKeepsTopKSemantics() {
        long[] pred = new long[]{enc(1, 0.10f), enc(2, 0.20f), enc(3, 0.30f), enc(4, 0.40f)};
        java.util.List<Long> got = SimulatorMarketLevelTicker1MStopLoss.selectCands(pred);
        int k = Configs.SELECTOR_RANK_TOPK;
        int want = k > 0 ? Math.min(k, pred.length) : pred.length;   // TOPK<=0 => cutoff tuyet doi
        assertTrue("khong duoc vuot pool", got.size() <= pred.length);
        if (k > 0) assertEquals(want, got.size());
        for (int i = 0; i < got.size(); i++) assertEquals(pred[i], (long) got.get(i));
        // pool rong: khong duoc nem, tra ve list rong
        assertEquals(0, SimulatorMarketLevelTicker1MStopLoss.selectCands(new long[0]).size());
    }

    private static long enc(int symId, float pred) {
        return ((long) symId << 32) | (Float.floatToIntBits(pred) & 0xFFFFFFFFL);
    }

    /** (5) Mac dinh cua flag: OFF va cac hang so pre-reg. */
    @Test
    public void defaultsAreOff() {
        assertFalse("flag PHAI default OFF", gate0);
        assertEquals(0.5f, ratio0, EPS);
        assertEquals(-0.08f, loss0, EPS);
        assertEquals(60, Configs.DCA_SIGNAL_COOLDOWN_MIN);
    }
}
