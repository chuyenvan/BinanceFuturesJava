package com.binance.chuyennd.tradecore;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * TRAIL-LADDER — bang gap BAC THANG (docs/prereg/PREREG_TRAIL_LADDER.md muc 3).
 *
 * <p>Test nay chot bang so DUNG NHU PRE-REG (L1/L2/L3) + BAT BIEN "SL luon tren entry"
 * ({@code rate > 0} voi moi dinh) + duong FALLBACK ve cong thuc cu khi dinh duoi bac thap nhat
 * (L3 "chi noi o vung lai lon").
 *
 * <p>Khong cham vao Configs.TS_LADDER_ON (khong bat/tat trang thai toan cuc) — chi goi ham thuan
 * {@link TradeUtils#ladderGap}/{@link TradeUtils#trailFromLadder} voi bang truyen vao.
 */
public class TrailLadderTest {

    // Bang CHOT TRUOC o pre-reg §3.1 (khong duoc sua sau khi thay ket qua).
    private static final float[] L1_LO = {0.00f, 0.10f, 0.25f, 0.50f, 1.00f};
    private static final float[] L1_GAPS = {0.04f, 0.08f, 0.15f, 0.25f, 0.35f};
    private static final float[] L2_LO = {0.00f, 0.10f, 0.25f, 0.50f, 1.00f};
    private static final float[] L2_GAPS = {0.04f, 0.10f, 0.20f, 0.35f, 0.50f};
    private static final float[] L3_LO = {0.50f, 1.00f};
    private static final float[] L3_GAPS = {0.25f, 0.40f};

    private static final float STRONG = 0.08f;   // Configs.TS_MAX_GAP
    private static final float WEAK = 0.03f;     // Configs.TS_MAX_GAP_WEAK

    /** L1 "thang nhe": <10%->4%; 10-25%->8%; 25-50%->15%; 50-100%->25%; >100%->35%. */
    @Test
    public void l1ThangNhe() {
        assertEquals(0.04f, TradeUtils.ladderGap(0.08f, L1_LO, L1_GAPS), 1e-7f);
        assertEquals(0.08f, TradeUtils.ladderGap(0.20f, L1_LO, L1_GAPS), 1e-7f);
        assertEquals(0.15f, TradeUtils.ladderGap(0.40f, L1_LO, L1_GAPS), 1e-7f);
        assertEquals(0.25f, TradeUtils.ladderGap(0.80f, L1_LO, L1_GAPS), 1e-7f);
        assertEquals(0.35f, TradeUtils.ladderGap(1.50f, L1_LO, L1_GAPS), 1e-7f);
        // menh de: dinh cang cao => gap cang LON (khong bi "truot song")
        float prev = -1f;
        for (float pk : new float[]{0.09f, 0.24f, 0.49f, 0.99f, 2.50f}) {
            float g = TradeUtils.ladderGap(pk, L1_LO, L1_GAPS);
            assertTrue("gap phai TANG dan theo dinh", g > prev);
            prev = g;
        }
    }

    /** L2 "thang doc": <10%->4%; 10-25%->10%; 25-50%->20%; 50-100%->35%; >100%->50%. */
    @Test
    public void l2ThangDoc() {
        assertEquals(0.04f, TradeUtils.ladderGap(0.05f, L2_LO, L2_GAPS), 1e-7f);
        assertEquals(0.10f, TradeUtils.ladderGap(0.15f, L2_LO, L2_GAPS), 1e-7f);
        assertEquals(0.20f, TradeUtils.ladderGap(0.30f, L2_LO, L2_GAPS), 1e-7f);
        assertEquals(0.35f, TradeUtils.ladderGap(0.75f, L2_LO, L2_GAPS), 1e-7f);
        assertEquals(0.50f, TradeUtils.ladderGap(1.50f, L2_LO, L2_GAPS), 1e-7f);
        // SL tai dinh 150% la 100% (rate = 1.5 - 0.5)
        assertEquals(1.00f, TradeUtils.trailFromLadder(1.50f, L2_LO, L2_GAPS, STRONG), 1e-6f);
    }

    /** L3 "chi noi o vung lai lon": duoi 50% => CONG THUC CU; 50-100%->25%; >100%->40%. */
    @Test
    public void l3ChiNoiOvungLaiLon() {
        // duoi bac thap nhat: gap = NaN => fallback trailFromCap(peak, cap STRONG/WEAK)
        assertTrue(Float.isNaN(TradeUtils.ladderGap(0.30f, L3_LO, L3_GAPS)));
        assertEquals(TradeUtils.trailFromCap(0.30f, STRONG),
                TradeUtils.trailFromLadder(0.30f, L3_LO, L3_GAPS, STRONG), 0f);
        assertEquals(TradeUtils.trailFromCap(0.30f, WEAK),
                TradeUtils.trailFromLadder(0.30f, L3_LO, L3_GAPS, WEAK), 0f);
        // 50-100% => 25%
        assertEquals(0.55f, TradeUtils.trailFromLadder(0.80f, L3_LO, L3_GAPS, STRONG), 1e-6f);
        // >100% => 40%
        assertEquals(1.10f, TradeUtils.trailFromLadder(1.50f, L3_LO, L3_GAPS, STRONG), 1e-6f);
    }

    /** BAT BIEN: SL LUON TREN entry (rate > 0) va gap < dinh — voi MOI dinh du arm. */
    @Test
    public void slLuonTrenEntry() {
        float[][] los = {L1_LO, L2_LO, L3_LO};
        float[][] gaps = {L1_GAPS, L2_GAPS, L3_GAPS};
        for (int i = 0; i < los.length; i++) {
            for (float pk = 0.07f; pk <= 3.0f; pk += 0.01f) {
                for (float cap : new float[]{STRONG, WEAK}) {
                    float r = TradeUtils.trailFromLadder(pk, los[i], gaps[i], cap);
                    assertTrue("rate phai > 0 (SL tren entry) @peak=" + pk, r > 0f);
                    assertTrue("rate phai < dinh @peak=" + pk, r < pk);
                    assertEquals("lam tron buoc 0.005", 0f, Math.abs(r / 0.005f - Math.round(r / 0.005f)), 1e-3f);
                }
            }
        }
    }

    /** Gap khong bao gio vuot dinh*0.9 du bang co bac gap rat lon (bien an toan). */
    @Test
    public void gapBiCapBangChinMuoiPhanTramDinh() {
        float[] lo = {0f};
        float[] g = {10f};
        assertEquals(0.01f, TradeUtils.trailFromLadder(0.10f, lo, g, STRONG), 1e-6f);
    }
}
