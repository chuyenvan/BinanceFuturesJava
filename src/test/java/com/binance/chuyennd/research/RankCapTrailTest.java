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
 * X3 viec A — TRAILING CAP THEO RANK SELECTOR ({@code TS_CAP_STRONG_RANK}).
 *
 * <p>Truoc X3, cap trailing chon theo GIA TRI {@code symbolPred} so voi ban le TUYET DOI 0.29,
 * ma gia tri do la thang do G015x26 (build_map chi gan lai theo thu hang S1). Ban le tuyet doi
 * nam NGOAI tick => tick nong ca K coin STRONG, tick lanh ca K coin WEAK. X3 doi sang RANK.
 *
 * <p>Hai manh ghep phai dung: (a) rank song sot qua {@code mergeOrder} (dung cho bug B1 da chet),
 * (b) {@code trailRate()} chon cap theo rank va BO QUA ban le 0.29.
 */
public class RankCapTrailTest {

    private final float gap0 = Configs.TS_MAX_GAP;
    private final float gapW0 = Configs.TS_MAX_GAP_WEAK;
    private final float ratio0 = Configs.TS_GIVEBACK_RATIO;
    private final Float thr0 = Configs.TS_PNOPUMP_WEAK_THR_OVR;
    private final int cap0 = Configs.TS_CAP_STRONG_RANK;

    @After
    public void restore() {
        Configs.TS_MAX_GAP = gap0;
        Configs.TS_MAX_GAP_WEAK = gapW0;
        Configs.TS_GIVEBACK_RATIO = ratio0;
        Configs.TS_PNOPUMP_WEAK_THR_OVR = thr0;
        Configs.TS_CAP_STRONG_RANK = cap0;
    }

    /** symbol=null co chu dich: ctor chi goi SimpleSymbolMapper khi symbol != null. */
    private static OrderTargetInfoTest leg(long t, Float pred, Integer rank) {
        OrderTargetInfoTest o = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, 100f, null, 1f,
                Configs.LEVERAGE_ORDER, null, t, t, OrderSide.BUY);
        o.symbolPred = pred;
        o.selRank = rank;
        return o;
    }

    private void grid() {
        Configs.TS_MAX_GAP = 0.08f;
        Configs.TS_MAX_GAP_WEAK = 0.03f;
        Configs.TS_GIVEBACK_RATIO = 0.5f;
        Configs.TS_PNOPUMP_WEAK_THR_OVR = 0.29f;
    }

    // ---------- (a) rank song sot qua cum ----------

    /** Leg DCA/BIG_DOWN co rank null -> KHONG duoc xoa rank cua cum (dung bay da sinh ra bug B1). */
    @Test
    public void dcaLegsDoNotEraseSelRank() {
        assertEquals(Integer.valueOf(3),
                SimulatorMarketLevelTicker1MStopLoss.clusterSelRank(
                        Arrays.asList(leg(1L, null, null), leg(2L, 0.12f, 3), leg(3L, null, null))));
    }

    /** Nhieu leg co rank -> lay leg SOM NHAT (rank luc MO cum, bat bien qua DCA). */
    @Test
    public void firstNonNullRankWins() {
        assertEquals(Integer.valueOf(1),
                SimulatorMarketLevelTicker1MStopLoss.clusterSelRank(
                        Arrays.asList(leg(1L, 0.40f, 1), leg(2L, 0.12f, 7))));
    }

    @Test
    public void allNullRankStaysNull() {
        assertNull(SimulatorMarketLevelTicker1MStopLoss.clusterSelRank(
                Arrays.asList(leg(1L, null, null), leg(2L, 0.5f, null))));
        assertNull(SimulatorMarketLevelTicker1MStopLoss.clusterSelRank(Collections.emptyList()));
        assertNull(SimulatorMarketLevelTicker1MStopLoss.clusterSelRank(null));
    }

    // ---------- (b) trailRate ----------

    /** TS_CAP_STRONG_RANK = 0 (mac dinh) -> duong CU: cap theo symbolPred, rank khong duoc doc. */
    @Test
    public void capZeroKeepsLegacyPnoPumpPath() {
        grid();
        Configs.TS_CAP_STRONG_RANK = 0;
        OrderTargetInfoTest c = leg(1L, 0.12f, 8);       // pred THAP + rank SAU
        assertEquals("pred <= 0.29 -> STRONG du rank sau", 0.22f, c.trailRate(0.30f), 1e-4f);
        c.symbolPred = 0.90f;
        c.selRank = 1;                                    // pred CAO + rank DAU
        assertEquals("pred > 0.29 -> WEAK du rank 1", 0.27f, c.trailRate(0.30f), 1e-4f);
        c.symbolPred = null;
        assertEquals("pred null -> WEAK (bao thu)", 0.27f, c.trailRate(0.30f), 1e-4f);
    }

    /**
     * TS_CAP_STRONG_RANK = 4: rank <= 4 -> STRONG (cap 0.08), rank > 4 -> WEAK (cap 0.03),
     * VA gia tri symbolPred KHONG con tac dung (ban le 0.29 bi bo qua) — day la muc dich cua X3.
     */
    @Test
    public void capRankIgnoresPnoPumpHinge() {
        grid();
        Configs.TS_CAP_STRONG_RANK = 4;
        OrderTargetInfoTest c = leg(1L, 0.90f, 2);        // pred RAT CAO nhung rank NONG
        assertEquals("rank 2 <= 4 -> STRONG du pred 0.90", 0.22f, c.trailRate(0.30f), 1e-4f);
        c.symbolPred = 0.01f;
        c.selRank = 6;                                    // pred RAT THAP nhung rank SAU
        assertEquals("rank 6 > 4 -> WEAK du pred 0.01", 0.27f, c.trailRate(0.30f), 1e-4f);
    }

    /** Bien: rank == N -> STRONG; rank == N+1 -> WEAK. */
    @Test
    public void capRankBoundaryInclusive() {
        grid();
        Configs.TS_CAP_STRONG_RANK = 2;
        OrderTargetInfoTest c = leg(1L, 0.50f, 2);
        assertEquals(0.22f, c.trailRate(0.30f), 1e-4f);
        c.selRank = 3;
        assertEquals(0.27f, c.trailRate(0.30f), 1e-4f);
    }

    /** rank null (leg khong qua selector) -> WEAK, dung quy uoc bao thu cua nhanh pNoPump null. */
    @Test
    public void capRankNullIsWeak() {
        grid();
        Configs.TS_CAP_STRONG_RANK = 6;
        OrderTargetInfoTest c = leg(1L, 0.01f, null);
        assertEquals(0.27f, c.trailRate(0.30f), 1e-4f);
    }

    /** STRONG phai nha nhieu hon => chot THAP hon => nuoi winner lau hon. */
    @Test
    public void strongReleasesMoreThanWeak() {
        grid();
        Configs.TS_CAP_STRONG_RANK = 4;
        OrderTargetInfoTest s = leg(1L, 0.5f, 1);
        OrderTargetInfoTest w = leg(1L, 0.5f, 8);
        assertTrue(s.trailRate(0.30f) < w.trailRate(0.30f));
        // arm nho (0.04): giveback = min(0.02, cap) = 0.02 o CA HAI nhanh => cap khong con tac dung
        assertEquals(s.trailRate(0.04f), w.trailRate(0.04f), 1e-6f);
    }
}
