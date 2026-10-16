package com.binance.chuyennd.tradecore;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public class BurstCooldownTest {
    private static final long M = 60_000L;
    private static final long T0 = 1_700_000_040_000L; // dau phut

    @Test
    public void offNeverBlocks() {
        BurstCooldown b = BurstCooldown.off();
        assertFalse(b.enabled());
        for (int i = 0; i < 50; i++) b.recordOpen(T0);
        assertFalse(b.blocks(T0 + M));
        assertEquals(0, b.triggers());
        assertEquals(0, b.blocked());
        assertFalse(new BurstCooldown(13, 0).enabled());
        assertFalse(new BurstCooldown(0, 120).enabled());
    }

    @Test
    public void belowNNoCooldown() {
        BurstCooldown b = new BurstCooldown(3, 120);
        b.recordOpen(T0);
        b.recordOpen(T0 + 5_000);
        assertFalse(b.blocks(T0 + M));
        assertEquals(0, b.triggers());
    }

    @Test
    public void countResetsPerMinute() {
        BurstCooldown b = new BurstCooldown(3, 120);
        b.recordOpen(T0);
        b.recordOpen(T0);
        b.recordOpen(T0 + M); // phut moi -> dem lai 1
        assertFalse(b.blocks(T0 + 2 * M));
        assertEquals(0, b.triggers());
    }

    @Test
    public void triggerBlocksLaterMinutesUntilEnd() {
        BurstCooldown b = new BurstCooldown(3, 120);
        b.recordOpen(T0);
        b.recordOpen(T0);
        b.recordOpen(T0);
        assertEquals(1, b.triggers());
        assertFalse(b.blocks(T0 + 30_000)); // cung phut kich hoat: khong chan
        b.recordOpen(T0 + 30_000);
        assertEquals(1, b.triggers());
        assertTrue(b.blocks(T0 + M));
        assertTrue(b.blocks(T0 + M + 120 * M - 1));
        assertFalse(b.blocks(T0 + M + 120 * M));
        assertEquals(2, b.blocked());
    }

    @Test
    public void retriggerAfterCooldown() {
        BurstCooldown b = new BurstCooldown(2, 60);
        b.recordOpen(T0);
        b.recordOpen(T0);
        long t1 = T0 + 200 * M;
        assertFalse(b.blocks(t1));
        b.recordOpen(t1);
        b.recordOpen(t1);
        assertEquals(2, b.triggers());
        assertTrue(b.blocks(t1 + M));
    }
}
