package com.binance.chuyennd.websocket;

import org.junit.Test;

import java.util.HashSet;
import java.util.Set;

import static org.junit.Assert.*;

/** [INGEST-QF2] Xoay WS lệch mốc, phát hiện im lặng ≤15 s, watchdog tuổi giá X/Y (prereg ADD1). */
public class Qf2SelfHealTest {
    static final long H = 3_600_000L, MIN = 60_000L;

    @Test
    public void sixConnectionsRotateAtDistinctTimesBefore24h() {
        Set<Long> at = new HashSet<>();
        for (int i = 0; i < 6; i++) {
            long t = KlineWsClient.rotateAfterMs(i);
            assertTrue("truoc moc 24h sàn: " + t, t <= 23 * H);
            assertTrue(t >= 20 * H);
            at.add(t);
        }
        assertEquals("6 moc xoay khac nhau", 6, at.size());
        for (int i = 1; i < 6; i++) assertEquals(25 * MIN, KlineWsClient.rotateAfterMs(i) - KlineWsClient.rotateAfterMs(i - 1));
        assertTrue(KlineWsClient.rotateAfterMs(7) <= 23 * H);
    }

    @Test
    public void silentDetectionWithin15s() {
        assertTrue(TickerIngestor2AerospikeNew.WS_STALE_MS + TickerIngestor2AerospikeNew.WS_WATCHDOG_MS <= 15_000L);
        KlineWsClient c = new KlineWsClient(null, null, 150, TickerIngestor2AerospikeNew.WS_STALE_MS, TickerIngestor2AerospikeNew.WS_WATCHDOG_MS);
        assertTrue(c.maxDetectMs() <= 15_000L);
    }

    @Test
    public void priceAgeWatchdogDecisions() {
        long now = 10 * H;
        long up = 10 * MIN;
        assertEquals("an han sau start", 0, BinanceDataIngestor.decidePriceAge(200_000L, 60_000L, 0, now));
        assertEquals(0, BinanceDataIngestor.decidePriceAge(3_000L, up, 0, now));
        assertEquals(0, BinanceDataIngestor.decidePriceAge(15_000L, up, 0, now));
        assertEquals("X=15 s => canh bao", 1, BinanceDataIngestor.decidePriceAge(15_001L, up, 0, now));
        assertEquals(1, BinanceDataIngestor.decidePriceAge(90_000L, up, 0, now));
        assertEquals("Y=90 s => restart", 2, BinanceDataIngestor.decidePriceAge(90_001L, up, 0, now));
        assertEquals("<=1 restart/gio", 3, BinanceDataIngestor.decidePriceAge(120_000L, up, now - 30 * MIN, now));
        assertEquals(2, BinanceDataIngestor.decidePriceAge(120_000L, up, now - H, now));
    }
}
