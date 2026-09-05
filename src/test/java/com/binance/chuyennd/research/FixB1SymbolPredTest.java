package com.binance.chuyennd.research;

import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;
import org.junit.After;
import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

/**
 * BUG B1 (docs/QUEUE.md muc BUGS) — mergeOrder() KHONG chep symbolPred sang object cum, ma
 * OrderTargetInfoTest.trailRate() chay tren CHINH object cum va fallback pnp=1f khi null
 * => 1f > TS_PNOPUMP_WEAK_THR(0.29) luon dung => 100% lenh di nhanh WEAK (cap 0.03).
 * Nhanh STRONG (cap 0.08) chua bao gio chay trong suot lich su DEV.
 *
 * <p>Test khong dung mergeOrder() truc tiep (ham do can KlineObjectSimple + instance Simulator);
 * no do DUNG HAI manh ghep tao ra bug: (a) chon leg nao, (b) hau qua len trailRate().
 */
public class FixB1SymbolPredTest {

    private static final float EPS = 1e-6f;

    private final float gap0 = Configs.TS_MAX_GAP;
    private final float gapW0 = Configs.TS_MAX_GAP_WEAK;
    private final float ratio0 = Configs.TS_GIVEBACK_RATIO;
    private final Float thr0 = Configs.TS_PNOPUMP_WEAK_THR_OVR;

    @After
    public void restore() {
        Configs.TS_MAX_GAP = gap0;
        Configs.TS_MAX_GAP_WEAK = gapW0;
        Configs.TS_GIVEBACK_RATIO = ratio0;
        Configs.TS_PNOPUMP_WEAK_THR_OVR = thr0;
    }

    /** symbol=null co chu dich: ctor chi goi SimpleSymbolMapper khi symbol != null (tranh Aerospike). */
    private static OrderTargetInfoTest leg(long t, Float pred) {
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, 100f, null, 1f,
                Configs.LEVERAGE_ORDER, null, t, t, OrderSide.BUY);
        o.symbolPred = pred;
        return o;
    }

    /**
     * Leg BIG_DOWN / DCA_LEVEL1 duoc tao voi symbolPred=null (chung BO QUA gate AI). Neu lay
     * "leg cuoi" thi moi cum co DCA se lai ve null => rot dung lai bug cu. Phai lay leg
     * KHONG-NULL DAU TIEN theo thoi gian.
     */
    @Test
    public void dcaLegsDoNotEraseSelectorPred() {
        assertEquals(0.12f,
                SimulatorMarketLevelTicker1MStopLoss.clusterSymbolPred(
                        Arrays.asList(leg(1L, null), leg(2L, 0.12f), leg(3L, null))),
                EPS);
    }

    /** Nhieu leg co pred -> lay leg SOM NHAT (dac trung selector luc MO cum, bat bien qua DCA). */
    @Test
    public void firstNonNullWins() {
        assertEquals(0.40f,
                SimulatorMarketLevelTicker1MStopLoss.clusterSymbolPred(
                        Arrays.asList(leg(1L, 0.40f), leg(2L, 0.12f))),
                EPS);
    }

    /** Khong leg nao co pred -> null => hanh vi Y HET truoc khi sua (khong sinh nhanh moi). */
    @Test
    public void allNullStaysNull() {
        assertNull(SimulatorMarketLevelTicker1MStopLoss.clusterSymbolPred(
                Arrays.asList(leg(1L, null), leg(2L, null))));
        assertNull(SimulatorMarketLevelTicker1MStopLoss.clusterSymbolPred(Collections.emptyList()));
        assertNull(SimulatorMarketLevelTicker1MStopLoss.clusterSymbolPred(null));
    }

    /**
     * HAU QUA: chi khi symbolPred duoc chep thi nhanh STRONG moi voi toi duoc.
     * Ban le: pNoPump <= 0.29 -> STRONG (cap TS_MAX_GAP 0.08); > 0.29 hoac null -> WEAK (0.03).
     * arm 30%: giveback = min(0.30*0.5, cap) => STRONG chot 0.22, WEAK chot 0.27.
     */
    @Test
    public void strongBranchReachableOnlyWithPred() {
        Configs.TS_MAX_GAP = 0.08f;
        Configs.TS_MAX_GAP_WEAK = 0.03f;
        Configs.TS_GIVEBACK_RATIO = 0.5f;
        Configs.TS_PNOPUMP_WEAK_THR_OVR = 0.29f;

        OrderTargetInfoTest cluster = leg(1L, null);

        cluster.symbolPred = null;                       // BUG CU: cum luon rong
        float weakNull = cluster.trailRate(0.30f);
        cluster.symbolPred = 0.50f;                      // pred cao -> van WEAK (dung ban le)
        float weakHigh = cluster.trailRate(0.30f);
        cluster.symbolPred = 0.12f;                      // SAU KHI SUA: pred thap -> STRONG
        float strong = cluster.trailRate(0.30f);

        assertEquals("null -> WEAK cap 0.03", 0.27f, weakNull, 1e-4f);
        assertEquals("pred > 0.29 -> WEAK cap 0.03", 0.27f, weakHigh, 1e-4f);
        assertEquals("pred <= 0.29 -> STRONG cap 0.08", 0.22f, strong, 1e-4f);
        assertTrue("STRONG phai nuoi winner lau hon (chot thap hon)", strong < weakNull);
    }
}
