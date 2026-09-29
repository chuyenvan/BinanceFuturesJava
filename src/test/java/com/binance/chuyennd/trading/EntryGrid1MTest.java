package com.binance.chuyennd.trading;

import com.binance.chuyennd.tradecore.Configs;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * [R4-1M 2026-09-29] docs/plan/PLAN_R4_1M_SHADOW.md — bang chung LOGIC cho nhip luoi SELECTOR cua LIVE:
 * (i)   key {@code LIVE_ENTRY_GRID_MIN} mac dinh = 15 (khong khai / &lt;=0) =&gt; hanh vi y nguyen (luoi 15');
 * (ii)  gridMin = 1 =&gt; SELECTOR duoc danh gia DUNG 1 lan cho MOI phut (nhip 1 PHUT cho R4);
 * (iii) cua so giay + co lastProcessedMin van giu nguyen (khong doi logic ngoai tham so grid).
 * Chi goi ham THUAN (pure) selectorGrid, khong cham mang/ONNX/live.
 */
public class EntryGrid1MTest {

    private static final long WINDOW_SEC = 7; // giay trong cua so quet (6..10)

    // ---- (i) mac dinh la 15 (byte-identical hanh vi cu) ----

    @Test
    public void keyMacDinh_luoi15() {
        assertEquals("LIVE_ENTRY_GRID_MIN mac dinh phai la 15 (nhu hang so cu)", 15, Configs.LIVE_ENTRY_GRID_MIN);
    }

    @Test
    public void luoi15_chiTaiMoc15Phut() {
        assertTrue(DetectEntrySignal2TradeNormal.selectorGrid(7, 900, 899, 15));   // 900 % 15 == 0
        assertFalse(DetectEntrySignal2TradeNormal.selectorGrid(7, 901, 0, 15));    // 901 % 15 != 0
        assertFalse(DetectEntrySignal2TradeNormal.selectorGrid(7, 902, 0, 15));
    }

    // ---- (ii) gridMin = 1 => moi phut ----

    @Test
    public void luoi1Phut_chayMoiPhut() {
        long last = 1000;
        int hit = 0;
        // quet 60 phut lien tiep, moi phut tai giay 7 (trong cua so)
        for (long min = 1001; min <= 1060; min++) {
            if (DetectEntrySignal2TradeNormal.selectorGrid(7, min, last, 1)) {
                last = min;
                hit++;
            }
        }
        assertEquals("grid=1 phai quet du 60/60 phut", 60, hit);
    }

    @Test
    public void luoi1Phut_vanDung1LanMoiPhut_vaNgoaiCuaSoThiKhong() {
        assertTrue(DetectEntrySignal2TradeNormal.selectorGrid(6, 901, 900, 1));
        assertTrue(DetectEntrySignal2TradeNormal.selectorGrid(10, 901, 900, 1));
        assertFalse(DetectEntrySignal2TradeNormal.selectorGrid(5, 901, 900, 1));   // truoc cua so
        assertFalse(DetectEntrySignal2TradeNormal.selectorGrid(11, 901, 900, 1));  // sau cua so
        assertFalse(DetectEntrySignal2TradeNormal.selectorGrid(7, 901, 901, 1));   // da quet phut nay
    }

    // ---- (iii) so sanh 15 vs 1 tren cung 1 gio ----

    @Test
    public void soSanh_coHoiSelector_15vs1() {
        assertEquals("luoi 15' chi 4 moc/gio", 4, countSelectorHits(15));
        assertEquals("luoi 1' du 60 moc/gio", 60, countSelectorHits(1));
    }

    /** So lan SELECTOR duoc danh gia trong 1 gio (mo phong DUNG vong while cua thread). */
    private static int countSelectorHits(int gridMin) {
        long lastSel = 899;
        int n = 0;
        for (long min = 900; min < 960; min++) {
            if (DetectEntrySignal2TradeNormal.selectorGrid(WINDOW_SEC, min, lastSel, gridMin)) {
                lastSel = min;
                n++;
            }
        }
        return n;
    }
}
