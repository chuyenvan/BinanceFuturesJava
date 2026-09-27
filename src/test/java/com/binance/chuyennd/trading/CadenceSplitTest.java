package com.binance.chuyennd.trading;

import org.junit.Test;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * [CADENCE-SPLIT 2026-09-27] docs/plan/PLAN_LIVE_CADENCE_SPLIT.md — bang chung LOGIC cho 2 dieu kien:
 * (i)  key {@code MARKET_SCAN_MIN} KHONG khai (&lt;=0) =&gt; cong nhip 1' luon FALSE =&gt; thread chi con
 *      duong 15' cu =&gt; hanh vi y nguyen;
 * (ii) key = 1 =&gt; cong nhip MARKET-LEVEL TRUE dung 1 lan cho MOI phut (con SELECTOR van dung luoi 15').
 * Chi goi 2 ham THUAN (pure), khong cham mang/ONNX/live.
 */
public class CadenceSplitTest {

    private static final long WINDOW_SEC = 7; // giay trong cua so quet (6..10)

    // ---- (i) khong khai key => y nguyen ----

    @Test
    public void keyKhongKhai_thiKhongBaoGioCoNhip1Phut() {
        for (long sec = 0; sec < 60; sec++) {
            for (long min = 0; min < 60; min++) {
                assertFalse("scanMin=0 (khong khai) phai luon false",
                        DetectEntrySignal2TradeNormal.marketScanGrid(sec, min, -1, 0));
                assertFalse("scanMin=-1 (khong khai) phai luon false",
                        DetectEntrySignal2TradeNormal.marketScanGrid(sec, min, -1, -1));
            }
        }
    }

    // ---- (i) cong SELECTOR giu nguyen: chi moc luoi 15', 1 lan/moc ----

    @Test
    public void congSelector_vanChiChayTaiMocLuoi15Phut() {
        assertTrue(DetectEntrySignal2TradeNormal.selectorGrid(7, 900, 899));   // 900 % 15 == 0
        assertTrue(DetectEntrySignal2TradeNormal.selectorGrid(6, 900, 0));
        assertTrue(DetectEntrySignal2TradeNormal.selectorGrid(10, 915, 900));
        assertFalse(DetectEntrySignal2TradeNormal.selectorGrid(5, 900, 0));    // ngoai cua so giay
        assertFalse(DetectEntrySignal2TradeNormal.selectorGrid(11, 900, 0));   // ngoai cua so giay
        assertFalse(DetectEntrySignal2TradeNormal.selectorGrid(7, 901, 0));    // 901 % 15 != 0
        assertFalse(DetectEntrySignal2TradeNormal.selectorGrid(7, 900, 900));  // da quet moc nay
    }

    // ---- (ii) key = 1 => MARKET-LEVEL moi phut ----

    @Test
    public void keyBang1_thiMarketLevelChayMoiPhut() {
        long last = 1000;
        int hit = 0;
        // quet 60 phut lien tiep, moi phut thu 6 giay trong cua so
        for (long min = 1001; min <= 1060; min++) {
            if (DetectEntrySignal2TradeNormal.marketScanGrid(7, min, last, 1)) {
                last = min;
                hit++;
            }
        }
        assertTrue("phai quet du 60/60 phut", hit == 60);
    }

    @Test
    public void keyBang1_vanDung1LanMoiPhut_vaNgoaiCuaSoThiKhong() {
        assertTrue(DetectEntrySignal2TradeNormal.marketScanGrid(6, 901, 900, 1));
        assertTrue(DetectEntrySignal2TradeNormal.marketScanGrid(10, 901, 900, 1));
        assertFalse(DetectEntrySignal2TradeNormal.marketScanGrid(5, 901, 900, 1));   // truoc cua so
        assertFalse(DetectEntrySignal2TradeNormal.marketScanGrid(11, 901, 900, 1));  // sau cua so
        assertFalse(DetectEntrySignal2TradeNormal.marketScanGrid(7, 901, 901, 1));   // da quet phut nay
    }

    /**
     * (ii) + (i) gop lai: mo phong DUNG quyet dinh cua thread trong 1 gio, dem so lan
     * MARKET-LEVEL duoc danh gia. key=1 => BGI_DOWN/DCA co 60 co hoi/gio; key=0 => 4 (moc 15').
     */
    @Test
    public void moPhongThread_1Gio_demCoHoiMarketLevel() {
        // MARKET-LEVEL duoc danh gia moi khi body ham chay = (selectorTick || marketTick).
        assertTrue("key=1 phai co 60 co hoi/gio", countMarketLevelEvaluations(1) == 60);
        assertTrue("key khong khai chi 4 moc 15' => y nguyen", countMarketLevelEvaluations(0) == 4);
    }

    /** So lan MARKET-LEVEL duoc danh gia trong 1 gio (mo phong DUNG vong while cua thread). */
    private static int countMarketLevelEvaluations(int scanMin) {
        long lastSel = 899, lastMkt = 899;
        int n = 0;
        // 1 gio = 60 phut, moi phut quet 1 lan trong cua so giay 6..10
        for (long min = 900; min < 960; min++) {
            boolean selectorTick = DetectEntrySignal2TradeNormal.selectorGrid(WINDOW_SEC, min, lastSel);
            if (selectorTick) lastSel = min;
            boolean marketTick = !selectorTick
                    && DetectEntrySignal2TradeNormal.marketScanGrid(WINDOW_SEC, min, lastMkt, scanMin);
            if (marketTick) lastMkt = min;
            if (selectorTick || marketTick) n++;
        }
        return n;
    }
}
