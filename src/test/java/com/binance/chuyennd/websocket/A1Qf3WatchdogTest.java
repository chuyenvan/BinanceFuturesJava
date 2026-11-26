package com.binance.chuyennd.websocket;

import com.binance.chuyennd.utils.BinanceRestGuard;
import org.junit.After;
import org.junit.Test;

import static org.junit.Assert.*;

/** A1 re-audit QF3 (chi a1_wt3, KHONG commit): decidePriceAge quanh ban. 0 on,1 canh bao,2 restart,3 da restart <1h,4 dang ban. */
public class A1Qf3WatchdogTest {
    static final long H = 3_600_000L;

    @After
    public void tearDown() {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
    }

    @Test
    public void w1_longBanThenRecovery() {
        long now = System.currentTimeMillis();
        long until = now + 3 * 24 * H;   // ban 3 ngay
        BinanceRestGuard.BANNED_UNTIL_MS.set(until);
        assertEquals(4, BinanceDataIngestor.decidePriceAge(2 * 24 * H, 10 * H, 0, now + 2 * 24 * H));
        // vua het ban 30 s, gia van dung tu 3 ngay: chi canh bao (90 s dem tu luc het ban)
        assertEquals(1, BinanceDataIngestor.decidePriceAge(3 * 24 * H, 80 * H, 0, until + 30_000L));
        // het ban 95 s, gia van dung => restart (1 lan/gio)
        assertEquals(2, BinanceDataIngestor.decidePriceAge(3 * 24 * H, 80 * H, 0, until + 95_000L));
        assertEquals(3, BinanceDataIngestor.decidePriceAge(3 * 24 * H, 80 * H, until + 95_000L - 60_000L, until + 95_000L));
    }

    @Test
    public void w2_418RightAfterNewJvmStart() {
        long now = System.currentTimeMillis();
        BinanceRestGuard.BANNED_UNTIL_MS.set(now + 130_000L);
        assertEquals("trong an han", 0, BinanceDataIngestor.decidePriceAge(10_000L, 10_000L, 0, now));
        assertEquals("het an han, dang ban", 4, BinanceDataIngestor.decidePriceAge(200_000L, 200_000L, 0, now + 100_000L));
    }

    @Test
    public void w3_a1t6Rerun() {
        long now = System.currentTimeMillis();
        BinanceRestGuard.BANNED_UNTIL_MS.set(now + 300_000L);
        assertNotEquals(2, BinanceDataIngestor.decidePriceAge(130_000L, H, 0L, now));
    }
}
