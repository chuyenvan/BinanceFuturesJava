package com.binance.chuyennd.tradecore;

import org.junit.After;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * X2 — pre-arm hard stop-loss ({@link PreArmSlUtils}). Xem docs/prereg/PREREG_X2.md muc 2.2.
 *
 * <p>Khoa 4 tinh chat: (1) TAT = mac dinh = khong bao gio kich hoat; (2) nguong do tren
 * firstEntryPrice va BAT BIEN qua DCA; (3) gia dong khong bao gio TOT hon muc stop
 * (chan look-ahead); (4) gia dong XAU HON muc stop khi nen dong duoi do (chiu gap).
 */
public class PreArmSlTest {

    private static final float EPS = 1e-6f;

    @After
    public void reset() {
        Configs.PRE_ARM_SL = 0f;
    }

    /** (1) Mac dinh 0 = TAT: khong kich hoat ke ca khi lo 99%. */
    @Test
    public void disabledByDefaultNeverHits() {
        Configs.PRE_ARM_SL = 0f;
        assertFalse(PreArmSlUtils.enabled());
        assertFalse(PreArmSlUtils.hit(100f, 1f));
        Configs.PRE_ARM_SL = 0.20f;      // gia tri DUONG cung phai coi la TAT
        assertFalse(PreArmSlUtils.enabled());
        assertFalse(PreArmSlUtils.hit(100f, 1f));
    }

    /** (2) Nguong dung = first*(1+pct); bien tren/duoi/bang. */
    @Test
    public void hitsExactlyAtThreshold() {
        Configs.PRE_ARM_SL = -0.20f;
        assertEquals(80f, PreArmSlUtils.stopLevel(100f), EPS);
        assertFalse("tren nguong 1 tick => chua cham", PreArmSlUtils.hit(100f, 80.01f));
        assertTrue("bang nguong => cham", PreArmSlUtils.hit(100f, 80f));
        assertTrue("duoi nguong => cham", PreArmSlUtils.hit(100f, 60f));
        assertFalse("firstEntryPrice null => khong quyet dinh", PreArmSlUtils.hit(null, 1f));
        assertFalse("firstEntryPrice <= 0 => khong quyet dinh", PreArmSlUtils.hit(0f, 1f));
    }

    /** (2b) BAT BIEN qua DCA: nguong bam firstEntryPrice, khong theo gia binh quan. */
    @Test
    public void thresholdInvariantAcrossDca() {
        Configs.PRE_ARM_SL = -0.30f;
        float first = 100f;
        float avgAfterDca = 85f;         // sau khi nhoi, priceEntry binh quan tut xuong
        assertEquals(70f, PreArmSlUtils.stopLevel(first), EPS);
        // neu (SAI) do tren gia binh quan thi nguong se la 59.5 => noi long 10.5 don vi gia
        assertEquals(59.5f, avgAfterDca * (1f + Configs.PRE_ARM_SL), EPS);
        assertTrue("do tren first => 65 DA cham", PreArmSlUtils.hit(first, 65f));
    }

    /** (3) Gia dong khong bao gio TOT hon muc stop, du nen bat lai len. */
    @Test
    public void exitNeverBetterThanStop() {
        Configs.PRE_ARM_SL = -0.20f;
        // nen: low 70 (thung sau) nhung open 95 / close 96 => neu lay min(open,close) se duoc 95 (qua tot)
        assertEquals(80f, PreArmSlUtils.exitPrice(100f, 95f, 96f), EPS);
    }

    /** (4) Gia dong XAU HON muc stop khi nen dong duoi stop (gap). */
    @Test
    public void exitWorseThanStopOnGap() {
        Configs.PRE_ARM_SL = -0.20f;
        assertEquals(72f, PreArmSlUtils.exitPrice(100f, 74f, 72f), EPS);
        assertEquals(74f, PreArmSlUtils.exitPrice(100f, 74f, 79f), EPS);
    }

    /** (5) SL-ADAPTIVE: ban *Val doc lap Configs.PRE_ARM_SL (lever A dung theo selRank). */
    @Test
    public void valVariantsIndependentOfGlobal() {
        Configs.PRE_ARM_SL = 0f;                 // global TAT
        assertFalse(PreArmSlUtils.enabledVal(0f));
        assertTrue(PreArmSlUtils.enabledVal(-0.08f));
        assertEquals(92f, PreArmSlUtils.stopLevelVal(100f, -0.08f), EPS);
        assertFalse("global off nhung Val -0.08 van quyet dinh doc lap",
                PreArmSlUtils.hitVal(100f, 92.01f, -0.08f));
        assertTrue(PreArmSlUtils.hitVal(100f, 92f, -0.08f));
        assertEquals(92f, PreArmSlUtils.exitPriceVal(100f, 95f, 96f, -0.08f), EPS);
        assertEquals(90f, PreArmSlUtils.exitPriceVal(100f, 91f, 90f, -0.08f), EPS);
    }

    /** (6) Ban khong tham so = *Val voi Configs.PRE_ARM_SL (uy quyen, khong doi hanh vi cu). */
    @Test
    public void noArgDelegatesToVal() {
        Configs.PRE_ARM_SL = -0.20f;
        assertEquals(PreArmSlUtils.stopLevelVal(100f, -0.20f), PreArmSlUtils.stopLevel(100f), EPS);
        assertEquals(Boolean.valueOf(PreArmSlUtils.hitVal(100f, 80f, -0.20f)),
                Boolean.valueOf(PreArmSlUtils.hit(100f, 80f)));
        assertEquals(PreArmSlUtils.exitPriceVal(100f, 95f, 96f, -0.20f),
                PreArmSlUtils.exitPrice(100f, 95f, 96f), EPS);
    }
}
