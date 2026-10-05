package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

/**
 * [LIVE-DCA-GRID 2026-10-03] E5 parity: cung chuoi gia gia => leg DCA giay sinh ra (bac + size) TRUNG
 * BIT voi ham sim (DcaProcessor.getDCA nhanh grid -> createOrder: managerBudget x gridLegWeightRatio(gridLegCount)).
 * Co TAT => khong leg.
 */
public class LiveDcaGridC3Test {

    private float fBase0, uMax0, scale0;
    private float[] w0, lv0;
    private boolean fix0, scalar0;
    private static final float EQ = 35000f;
    private static final int LEV = 1;   // danh 1x (margin = notional), dung de quy doi qty o day

    @Before
    public void setUp() {
        fBase0 = Configs.F_BASE; uMax0 = Configs.U_MAX; scale0 = Configs.DCA_GRID_SCALE;
        w0 = Configs.DCA_GRID_WEIGHTS; lv0 = Configs.DCA_GRID_LEVELS;
        fix0 = Configs.FIX_B2; scalar0 = Configs.DCA_GRID_SCALAR;
        Configs.F_BASE = 0.015f;
        Configs.U_MAX = 0.60f;
        Configs.DCA_GRID_SCALE = 6.0f;
        Configs.DCA_GRID_WEIGHTS = new float[]{1f, 1f, 1f, 1f};
        Configs.DCA_GRID_LEVELS = new float[]{-0.50f, -0.75f, -0.90f};
        Configs.FIX_B2 = true;
        Configs.DCA_GRID_SCALAR = false;
    }

    @After
    public void restore() {
        Configs.F_BASE = fBase0; Configs.U_MAX = uMax0; Configs.DCA_GRID_SCALE = scale0;
        Configs.DCA_GRID_WEIGHTS = w0; Configs.DCA_GRID_LEVELS = lv0;
        Configs.FIX_B2 = fix0; Configs.DCA_GRID_SCALAR = scalar0;
    }

    /** Chuoi gia: leg dau @100, roi rot dan; nguong -50/-75/-90 => leg 1 @49, leg 2 @24, leg 3 @9.5, het bac. */
    private static final float[] PATH = {100f, 80f, 55f, 49f, 45f, 30f, 24f, 20f, 11f, 9.5f, 5f, 2f};

    /** "SIM": DcaUtils.shouldDcaGrid + (managerBudget; budget *= gridLegWeightRatio(gridLegCount)). */
    private static List<String> simLegs() {
        List<String> out = new ArrayList<>();
        float first = PATH[0];
        int legCount = 1;
        Float mb0 = TradeUtils.managerBudget(null, 0f, EQ, null);
        mb0 *= DcaUtils.gridLegWeightRatio(0);
        float margin = mb0;
        for (int i = 1; i < PATH.length; i++) {
            if (!DcaUtils.shouldDcaGrid(first, PATH[i], legCount)) continue;
            Float b = TradeUtils.managerBudget(null, margin, EQ, MarketLevelChange.DCA_LEVEL1);
            if (b == null) continue;
            float ratio = DcaUtils.gridLegWeightRatio(legCount);   // gridLegCount(cur) = legs.size()
            if (ratio <= 0f) continue;
            b *= ratio;
            out.add(i + ":" + legCount + ":" + Float.floatToIntBits(b));
            margin += b;
            legCount++;
        }
        return out;
    }

    /** "LIVE": LiveDcaGridC3.dueSymbols -> legIdxFor(legCount) -> LiveGridSizing.legBudget(managerBudget). */
    private static List<String> liveLegs(boolean enabled) {
        List<String> out = new ArrayList<>();
        float first = PATH[0];
        int legCount = 1;
        float margin = LiveGridSizing.legBudget(TradeUtils.managerBudget(null, 0f, EQ, null), 0, true);
        for (int i = 1; i < PATH.length; i++) {
            Map<String, Float> px = new HashMap<>();
            px.put("XUSDT", PATH[i]);
            List<String> due = LiveDcaGridC3.dueSymbols(
                    Collections.singletonList(new LiveDcaGridC3.GridState("XUSDT", first, legCount)),
                    LiveDcaGridC3.priceOf(px), enabled);
            if (due.isEmpty()) continue;
            int legIdx = LiveDcaGridC3.legIdxFor(legCount);
            Float b = LiveGridSizing.legBudget(
                    TradeUtils.managerBudget(null, margin, EQ, MarketLevelChange.DCA_LEVEL1), legIdx, true);
            if (b == null || b < 5f) continue;   // createOrderBuyRequest: budget null/<5 => khong leg
            out.add(i + ":" + legIdx + ":" + Float.floatToIntBits(b));
            margin += b;
            legCount++;
        }
        return out;
    }

    @Test
    public void sameLevelsAndSizesAsSim() {
        List<String> sim = simLegs();
        List<String> live = liveLegs(true);
        assertEquals("3 leg grid (-50/-75/-90)", 3, sim.size());
        assertEquals(sim, live);
        // bac va gia khop dung: PATH[3]=49 (leg1), PATH[6]=24 (leg2), PATH[9]=9.5 (leg3)
        assertTrue(live.get(0).startsWith("3:1:"));
        assertTrue(live.get(1).startsWith("6:2:"));
        assertTrue(live.get(2).startsWith("9:3:"));
    }

    /** Size leg 1 = 35000 x 0.015 x (1 - U/0.6) / 4 x 6, U = 787.5/35000. */
    @Test
    public void legSizeFollowsThrottle() {
        float u = 787.5f / EQ;
        float expect = EQ * 0.015f * (1f - u / 0.60f) / 4f * 6f;
        String leg1 = liveLegs(true).get(0);
        float b = Float.intBitsToFloat(Integer.parseInt(leg1.split(":")[2]));
        assertEquals(expect, b, 0.01f);
    }

    /** U >= U_MAX => managerBudget null => KHONG leg (giong sim). */
    @Test
    public void uMaxBlocksLeg() {
        assertNull(TradeUtils.managerBudget(null, 0.61f * EQ, EQ, MarketLevelChange.DCA_LEVEL1));
    }

    @Test
    public void offProducesNoLeg() {
        assertTrue(liveLegs(false).isEmpty());
        assertFalse("surefire khong dat LIVE_DCA_GRID_ENABLED", LiveDcaGridC3.enabled());
        assertFalse(LiveDcaGridC3.active());
        assertTrue(LiveDcaGridC3.candidates(null, s -> 1f).isEmpty());
    }

    /** Gia null/0 (thieu ticker) => khong ung vien. */
    @Test
    public void missingPriceSkipped() {
        List<String> due = LiveDcaGridC3.dueSymbols(
                Collections.singletonList(new LiveDcaGridC3.GridState("XUSDT", 100f, 1)), s -> null, true);
        assertTrue(due.isEmpty());
    }
}
