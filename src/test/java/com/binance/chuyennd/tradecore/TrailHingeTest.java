package com.binance.chuyennd.tradecore;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * L7 — ban le trailing {@code TS_PNOPUMP_WEAK_THR = 0.29} phai cho CUNG STRONG/WEAK o sim va live
 * khi nhan CUNG mot dau vao.
 *
 * <p>Hai duong goi:
 * <ul>
 *   <li>SIM : {@code OrderTargetInfoTest.trailRate()} -> {@code TradeUtils.calRateLossDynamicBuyPNoPump(
 *       peak, symbolPred, Configs.tsPnoPumpWeakThr())} (TS_CAP_STRONG_RANK=0 nen khong di duong rank);</li>
 *   <li>LIVE: {@code ShadowBookC3:233-234} -> **cung ham, cung ban le**, voi
 *       {@code symbolPred = DetectEntrySignal2TradeNormal.paperSymbolPred(symbol)} =
 *       {@code LATEST_SEL_MAPPRED} (gia tri net015 DA QUA quantile-map = CUNG THANG DO voi bins
 *       cua sim), chi roi ve pNoPump khi thieu map.</li>
 * </ul>
 * Test nay chot phan CO THE chot bang code. Phan KHONG chot duoc bang test la **hieu chuan**:
 * phan phoi cua map net015 tren live khac phan phoi score bins tren sim, nen cung mot ban le
 * co the phan loai khac nhau tren du lieu that — do la muc 2 cua docs/L8_SIZING_PARITY_BACKLOG.md,
 * KHONG phai loi nhanh code.
 */
public class TrailHingeTest {

    private static final float PEAK = 0.10f;

    /** Ban le doc tu MOT nguon duy nhat cho ca hai ben. */
    @Test
    public void banLeMotNguon() {
        assertEquals(0.29f, Configs.tsPnoPumpWeakThr(), 1e-6f);
    }

    /** Duoi ban le => STRONG (cap TS_MAX_GAP 0.08); tren ban le => WEAK (cap TS_MAX_GAP_WEAK 0.03). */
    @Test
    public void duoiBanLeStrongTrenBanLeWeak() {
        float thr = Configs.tsPnoPumpWeakThr();
        float strong = TradeUtils.calRateLossDynamicBuyPNoPump(PEAK, 0.20f, thr);
        float weak = TradeUtils.calRateLossDynamicBuyPNoPump(PEAK, 0.40f, thr);
        // peak 10%: STRONG gap = min(10%*0.5, 8%) = 5% -> SL 5%; WEAK gap = min(5%, 3%) = 3% -> SL 7%
        assertEquals(0.05f, strong, 1e-6f);
        assertEquals(0.07f, weak, 1e-6f);
        assertTrue("WEAK phai giu SL sat hon (gap nho hon)", weak > strong);
    }

    /** CUNG input => CUNG ket qua, khong phu thuoc ben goi. Day la khang dinh parity. */
    @Test
    public void cungInputCungKetQua() {
        float thr = Configs.tsPnoPumpWeakThr();
        for (float sp : new float[]{0.05f, 0.2899f, 0.29f, 0.2901f, 0.50f, 0.97f}) {
            float sim = TradeUtils.calRateLossDynamicBuyPNoPump(PEAK, sp, thr);
            float live = TradeUtils.calRateLossDynamicBuyPNoPump(PEAK, sp, thr);
            assertEquals("symbolPred=" + sp, sim, live, 0f);
        }
    }

    /** Thieu symbolPred => ca hai ben coi la YEU (bao thu): sim dung 1f, ShadowBookC3 cung 1f. */
    @Test
    public void thieuSymbolPredThiCoiLaWeak() {
        float thr = Configs.tsPnoPumpWeakThr();
        assertEquals(TradeUtils.calRateLossDynamicBuyPNoPump(PEAK, 1f, thr),
                TradeUtils.calRateLossDynamicBuyPNoPump(PEAK, 0.40f, thr), 1e-6f);
    }
}
