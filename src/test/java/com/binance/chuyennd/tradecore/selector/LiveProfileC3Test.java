package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.TradeUtils;
import org.junit.Test;

import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.*;

/**
 * CONG HOI QUY cua profile {@code c3_shadow}: khi co TAT (mac dinh trong surefire — khong ai
 * dat {@code LIVE_PROFILE}), moi diem noi phai tra DUNG gia tri cua HEAD.
 *
 * <p>Cac nhanh BAT duoc kiem bang cach goi thang cong thuc (khong the doi env trong JVM dang
 * chay), xem {@link ShadowBookC3Test} cho phan exit.
 */
public class LiveProfileC3Test {

    /** Co mac dinh TAT: khong dat LIVE_PROFILE => on() = false. */
    @Test
    public void flagOffByDefault() {
        assertFalse("LIVE_PROFILE khong dat ma on()=true => moi cong hoi quy vo nghia",
                LiveProfileC3.on());
    }

    /** (a) co TAT: nguong arm = Configs.RATE_PROFIT_STOP_MARKET (duong HEAD). */
    @Test
    public void armRateFallsBackWhenOff() {
        assertEquals(0.05f, LiveProfileC3.armRate(0.05f), 0f);
        assertEquals(0.01f, LiveProfileC3.armRate(0.01f), 0f);
        assertEquals(Configs.RATE_PROFIT_STOP_MARKET,
                TradeUtils.calRateMinWithPredReturn15MForTradingStop(0.0123f), 0f);
    }

    /** (c) co TAT: he so dead-zone giu 5.21847 cua live. */
    @Test
    public void ratchetDeadzoneFallsBackWhenOff() {
        assertEquals(5.21847f, LiveProfileC3.ratchetDeadzoneMult(5.21847f), 0f);
    }

    /** Co TAT: KHONG tu ep no-push (duong cu doc Cfg.get("SHADOW_NO_PUSH")). */
    @Test
    public void noForceNoPushWhenOff() {
        assertFalse(LiveProfileC3.forceNoPush());
        assertEquals(0f, LiveProfileC3.paperEquity(), 0f);
    }

    /** Hang so profile dung theo C3 (docs/experiment/C3_BASELINE.md / L1 muc 2). */
    @Test
    public void c3Constants() {
        assertEquals(0.07f, LiveProfileC3.ARM_RATE, 0f);
        assertEquals(168, LiveProfileC3.TIME_STOP_HOURS);
        assertEquals(1.0f, LiveProfileC3.RATCHET_DEADZONE_MULT_ON, 0f);
        assertEquals(0.045f, LiveProfileC3.SIZE_CAP_OF_EQUITY, 1e-9f);
    }

    /**
     * (c) Cong thuc ratchet C3: {@code gap = min(peak * 0.5, cap)}, cap 0.08 khi
     * {@code symbolPred <= 0.29} (STRONG), 0.03 khi lon hon (WEAK).
     */
    @Test
    public void trailRateC3Shape() {
        float thr = Configs.tsPnoPumpWeakThr();
        assertEquals(0.29f, thr, 1e-6f);
        // peak 10%, STRONG: gap = min(0.05, 0.08) = 0.05 -> rate 0.05
        assertEquals(0.05f, ShadowBookC3.trailRate(0.10f, 0.10f), 1e-6f);
        // peak 10%, WEAK: gap = min(0.05, 0.03) = 0.03 -> rate 0.07
        assertEquals(0.07f, ShadowBookC3.trailRate(0.10f, 0.50f), 1e-6f);
        // peak 30%, STRONG: gap = min(0.15, 0.08) = 0.08 -> rate 0.22
        assertEquals(0.22f, ShadowBookC3.trailRate(0.30f, 0.10f), 1e-6f);
        // chua co symbolPred -> coi nhu YEU (bao thu)
        assertEquals(ShadowBookC3.trailRate(0.10f, 1f), ShadowBookC3.trailRate(0.10f, null), 1e-9f);
    }

    /** (d) tran size 4.5% equity ap SAU managerBudget. */
    @Test
    public void sizeCapMath() {
        float equity = 35000f;
        Float b = TradeUtils.managerBudget(0f, 0f, equity, null);
        assertNotNull(b);
        float cap = LiveProfileC3.SIZE_CAP_OF_EQUITY * equity;
        assertTrue("budget C3 (equity*F_BASE/ladder) phai nam duoi tran 4.5%", b <= cap);
    }

    /** {@code marginRunning >= U_MAX * equity} van chan lenh moi (khong bi profile lam hong). */
    @Test
    public void uMaxStillBlocks() {
        Map<String, Float> m = new HashMap<>();
        assertNull(TradeUtils.managerBudget(0f, 35000f * Configs.U_MAX, 35000f, null));
        assertNotNull(TradeUtils.managerBudget(0f, 0f, 35000f, null));
        assertTrue(m.isEmpty());
    }
}
