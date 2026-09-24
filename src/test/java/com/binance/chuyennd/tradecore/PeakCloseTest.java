package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;

/**
 * [PEAK-CLOSE 2026-09-23] docs/prereg/PREREG_PEAK_CLOSE.md — flag `TS_PEAK_MODE` va helper
 * {@link TradeUtils#peakPrice(KlineObjectSimple)}.
 *
 * <p>Test nay canh cong hoi quy QUAN TRONG NHAT: khi KHONG khai bao `TS_PEAK_MODE` (moi profile khac,
 * moi duong WFO/HPO), helper phai tra ve DUNG `ticker.maxPrice` (HIGH nen 1m) => byte-identical.
 * Tien le `TrailLadderTest` (commit a7b7725).
 */
public class PeakCloseTest {

    private static KlineObjectSimple bar() {
        KlineObjectSimple k = new KlineObjectSimple();
        k.maxPrice = 1.2345f;
        k.priceClose = 1.1111f;
        return k;
    }

    @Test
    public void macDinhLaHigh() {
        // JVM test nay khong dat TS_PEAK_MODE => phai roi ve default `high`.
        assertEquals("high", Configs.TS_PEAK_MODE);
        assertFalse(Configs.TS_PEAK_CLOSE);
    }

    @Test
    public void macDinhTraVeMaxPrice() {
        assertEquals(1.2345f, TradeUtils.peakPrice(bar()), 0f);
    }

    @Test
    public void validatePeakModeHighKhongDung() {
        Configs.validatePeakMode();          // `high` => khong exit
    }
}
