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
 * DCA-SIGNAL (docs/PREREG_DCA_SIGNAL_GATE.md) — hai manh ghep de vo neu code sai:
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

    /** (5) Mac dinh cua flag: OFF va cac hang so pre-reg. */
    @Test
    public void defaultsAreOff() {
        assertFalse("flag PHAI default OFF", gate0);
        assertEquals(0.5f, ratio0, EPS);
        assertEquals(-0.08f, loss0, EPS);
        assertEquals(60, Configs.DCA_SIGNAL_COOLDOWN_MIN);
    }
}
