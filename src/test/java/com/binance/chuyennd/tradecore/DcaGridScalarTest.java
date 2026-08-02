package com.binance.chuyennd.tradecore;

import org.junit.After;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

/**
 * FUNCTION-TEST cho DCA GRID dang SCALAR (2026-08-01). Ham thuan — khong Aerospike, khong backtest I/O.
 *
 * <p>Hai cau hoi phai tra loi truoc khi tin bat cu ket qua HPO nao ve DCA:
 * <ol>
 *   <li><b>Parity</b>: DCA_GRID_SCALAR=false co THUC SU giu nguyen hanh vi mang cu khong?
 *       Neu khong thi moi so lieu chot tam trong HANDOFF_20260801 mat hieu luc.</li>
 *   <li><b>HPO co cham toi khong</b>: doi field scalar (dung nhu reflection cua StrategyWfoTask lam)
 *       co lam doi ket qua shouldDcaGrid/gridLegWeightRatio khong? Loi im lang o day (ham van doc
 *       mang cu) se khien HPO chay ca ngan sample ma khong tune duoc gi — rat kho phat hien tu log.</li>
 * </ol>
 *
 * <p>Configs.DCA_GRID_* KHONG final nen test gan lai truc tiep duoc; {@link #restore()} tra ve default.
 */
public class DcaGridScalarTest {

    private static final float EPS = 1e-5f;

    private final boolean scalar0 = Configs.DCA_GRID_SCALAR;
    private final float l1_0 = Configs.DCA_GRID_L1;
    private final float step0 = Configs.DCA_GRID_STEP;
    private final int legs0 = Configs.DCA_GRID_LEGS;
    private final float wr0 = Configs.DCA_GRID_W_RATIO;
    private final float scale0 = Configs.DCA_GRID_SCALE;
    private final float capBase0 = Configs.DCA_TIER_CAP_BASE;
    private final float capStep0 = Configs.DCA_TIER_CAP_STEP;

    @After
    public void restore() {
        Configs.DCA_GRID_SCALAR = scalar0;
        Configs.DCA_GRID_L1 = l1_0;
        Configs.DCA_GRID_STEP = step0;
        Configs.DCA_GRID_LEGS = legs0;
        Configs.DCA_GRID_W_RATIO = wr0;
        Configs.DCA_GRID_SCALE = scale0;
        Configs.DCA_TIER_CAP_BASE = capBase0;
        Configs.DCA_TIER_CAP_STEP = capStep0;
    }

    /** PARITY: SCALAR=false -> accessor tra dung phan tu mang, KHONG dung cong thuc scalar. */
    @Test
    public void arrayModeIsUnchanged() {
        Configs.DCA_GRID_SCALAR = false;
        // co tinh dat scalar sang gia tri "sai" hoan toan: neu accessor lo doc scalar thi test gay.
        Configs.DCA_GRID_L1 = -0.11f;
        Configs.DCA_GRID_STEP = 0.01f;
        Configs.DCA_GRID_LEGS = 99;
        Configs.DCA_GRID_W_RATIO = 7f;

        assertEquals(Configs.DCA_GRID_LEVELS.length, Configs.dcaGridLegs());
        for (int i = 0; i < Configs.DCA_GRID_LEVELS.length; i++) {
            assertEquals("level[" + i + "] phai lay tu mang", Configs.DCA_GRID_LEVELS[i], Configs.dcaGridLevel(i), EPS);
        }
        for (int i = 0; i < Configs.DCA_GRID_WEIGHTS.length; i++) {
            assertEquals("weight[" + i + "] phai lay tu mang", Configs.DCA_GRID_WEIGHTS[i], Configs.dcaGridWeight(i), EPS);
        }
        float sum = 0;
        for (float w : Configs.DCA_GRID_WEIGHTS) sum += w;
        assertEquals(sum, Configs.dcaGridTotalWeight(), EPS);
    }

    /** SCALAR=true -> levels = L1 - STEP*i, weights = W_RATIO^i (w0=1). */
    @Test
    public void scalarModeDerivesGrid() {
        Configs.DCA_GRID_SCALAR = true;
        Configs.DCA_GRID_L1 = -0.50f;
        Configs.DCA_GRID_STEP = 0.20f;
        Configs.DCA_GRID_LEGS = 3;
        Configs.DCA_GRID_W_RATIO = 2.0f;

        assertEquals(3, Configs.dcaGridLegs());
        assertEquals(-0.50f, Configs.dcaGridLevel(0), EPS);
        assertEquals(-0.70f, Configs.dcaGridLevel(1), EPS);
        assertEquals(-0.90f, Configs.dcaGridLevel(2), EPS);
        assertEquals("vuot so bac -> 0f (caller hieu la het bac)", 0f, Configs.dcaGridLevel(3), EPS);

        assertEquals(1f, Configs.dcaGridWeight(0), EPS);
        assertEquals(2f, Configs.dcaGridWeight(1), EPS);
        assertEquals(4f, Configs.dcaGridWeight(2), EPS);
        assertEquals(8f, Configs.dcaGridWeight(3), EPS);
        assertEquals(15f, Configs.dcaGridTotalWeight(), EPS);
    }

    /** Clamp: STEP lon + LEGS sau khong duoc sinh muc <= -100% (gia am, vo nghia). */
    @Test
    public void scalarLevelsAreClamped() {
        Configs.DCA_GRID_SCALAR = true;
        Configs.DCA_GRID_L1 = -0.60f;
        Configs.DCA_GRID_STEP = 0.30f;
        Configs.DCA_GRID_LEGS = 5;
        assertEquals(-0.60f, Configs.dcaGridLevel(0), EPS);
        assertEquals(-0.90f, Configs.dcaGridLevel(1), EPS);
        assertEquals(-0.99f, Configs.dcaGridLevel(2), EPS);   // -1.20 bi clamp
        assertEquals(-0.99f, Configs.dcaGridLevel(4), EPS);
        assertTrue("moi muc phai > -1.0", Configs.dcaGridLevel(4) > -1.0f);
    }

    /**
     * Diem MAU CHOT: HPO doi field scalar thi shouldDcaGrid PHAI doi theo.
     * Neu ham con doc thang DCA_GRID_LEVELS thi test nay fail — dung loi im lang can bat.
     */
    @Test
    public void hpoTouchesShouldDcaGrid() {
        Configs.DCA_GRID_SCALAR = true;
        Configs.DCA_GRID_LEGS = 3;
        Configs.DCA_GRID_STEP = 0.20f;

        Configs.DCA_GRID_L1 = -0.50f;
        // gia tut 40% -> chua toi moc -50% -> khong nhoi
        assertFalse(DcaUtils.shouldDcaGrid(100f, 60f, 1));
        // gia tut 55% -> qua moc -50% -> nhoi
        assertTrue(DcaUtils.shouldDcaGrid(100f, 45f, 1));

        // HPO keo moc dau ve -30%: cung gia 60 (tut 40%) gio PHAI nhoi
        Configs.DCA_GRID_L1 = -0.30f;
        assertTrue("doi DCA_GRID_L1 ma ket qua khong doi => gene chet", DcaUtils.shouldDcaGrid(100f, 60f, 1));

        // TRAN so leg: legCount vuot DCA_GRID_LEGS -> khong nhoi du gia sap thang dung
        Configs.DCA_GRID_LEGS = 2;
        assertFalse(DcaUtils.shouldDcaGrid(100f, 1f, 3));
    }

    /** Ti trong quy ve ti le tren TONG roi nhan SCALE — tong cac leg = SCALE (khong phinh exposure ngau nhien). */
    @Test
    public void weightRatioSumsToScale() {
        Configs.DCA_GRID_SCALAR = true;
        Configs.DCA_GRID_LEGS = 3;
        Configs.DCA_GRID_W_RATIO = 2.0f;
        Configs.DCA_GRID_SCALE = 8.0f;

        float sum = 0;
        for (int i = 0; i <= 3; i++) sum += DcaUtils.gridLegWeightRatio(i);
        assertEquals("tong ti trong x SCALE phai = SCALE", 8.0f, sum, 1e-3f);
        assertEquals("het bac -> 0", 0f, DcaUtils.gridLegWeightRatio(4), EPS);
        assertTrue("leg sau phai nang hon leg truoc khi W_RATIO>1",
                DcaUtils.gridLegWeightRatio(3) > DcaUtils.gridLegWeightRatio(0));
    }

    /** Tran margin theo bac dang scalar: BASE + STEP*i, clamp <=0.98; STEP=0 => tran phang. */
    @Test
    public void tierCapScalarShape() {
        Configs.DCA_GRID_SCALAR = true;
        Configs.DCA_TIER_CAP_BASE = 0.50f;
        Configs.DCA_TIER_CAP_STEP = 0.10f;
        assertEquals(0.50f, Configs.tierMarginCap(0), EPS);
        assertEquals(0.60f, Configs.tierMarginCap(1), EPS);
        assertEquals(0.80f, Configs.tierMarginCap(3), EPS);
        assertEquals("clamp tran tren", 0.98f, Configs.tierMarginCap(20), EPS);

        Configs.DCA_TIER_CAP_STEP = 0f;
        assertEquals(0.50f, Configs.tierMarginCap(0), EPS);
        assertEquals("STEP=0 => tran phang = BREAKER_MARGIN_HALT cu", 0.50f, Configs.tierMarginCap(5), EPS);
    }

    /** SCALAR=false -> tierMarginCap van doc mang cu (parity voi ban chot tam). */
    @Test
    public void tierCapArrayModeUnchanged() {
        Configs.DCA_GRID_SCALAR = false;
        Configs.DCA_TIER_CAP_BASE = 0.99f;   // co tinh dat sai
        Configs.DCA_TIER_CAP_STEP = 0.99f;
        float[] c = Configs.DCA_TIER_MARGIN_CAPS;
        for (int i = 0; i < c.length; i++) {
            assertEquals("cap[" + i + "] phai lay tu mang", c[i], Configs.tierMarginCap(i), EPS);
        }
        assertEquals("vuot mang -> giu phan tu cuoi", c[c.length - 1], Configs.tierMarginCap(c.length + 5), EPS);
    }
}
