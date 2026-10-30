package com.binance.chuyennd.websocket;

import com.binance.chuyennd.utils.BinanceRestGuard;
import org.junit.After;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

/** [INGEST-QF3] Watchdog tuổi giá khi ban / sau ban (MAJ-A), chia WS đều + ngưỡng im lặng kết nối nhỏ (MIN-B). */
public class Qf3WsTest {
    static final long MIN = 60_000L, UP = 10 * MIN;

    @After
    public void tearDown() {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
    }

    @Test
    public void noRestartWhileBannedAndCount90sFromBanEnd() {
        long now = System.currentTimeMillis();
        BinanceRestGuard.BANNED_UNTIL_MS.set(now + 300_000L);
        assertEquals("dang ban => chi canh bao (4)", 4, BinanceDataIngestor.decidePriceAge(500_000L, UP, 0L, now));
        BinanceRestGuard.BANNED_UNTIL_MS.set(now - 30_000L);    // het ban 30 s truoc, gia dung 500 s
        assertEquals("tuoi tinh tu luc het ban = 30 s => chi canh bao", 1, BinanceDataIngestor.decidePriceAge(500_000L, UP, 0L, now));
        BinanceRestGuard.BANNED_UNTIL_MS.set(now - 91_000L);
        assertEquals("91 s sau het ban van dung => restart", 2, BinanceDataIngestor.decidePriceAge(500_000L, UP, 0L, now));
        BinanceRestGuard.BANNED_UNTIL_MS.set(now - 10 * MIN);
        assertEquals("ban cu khong anh huong", 0, BinanceDataIngestor.decidePriceAge(5_000L, UP, 0L, now));
    }

    @Test
    public void wsChunksEvenNoTinyConnection() {
        List<String> s = new ArrayList<>();
        for (int i = 0; i < 752; i++) s.add(String.format("S%03dUSDT", i));
        List<List<String>> c = KlineWsClient.chunk(s, 150);
        assertEquals(6, c.size());
        int total = 0;
        for (List<String> g : c) {
            assertTrue("125-126/ket noi: " + g.size(), g.size() >= 125 && g.size() <= 126);
            total += g.size();
        }
        assertEquals(752, total);
        assertEquals(1, KlineWsClient.chunk(s.subList(0, 150), 150).size());
        assertEquals(2, KlineWsClient.chunk(s.subList(0, 151), 150).size());
        assertEquals(76, KlineWsClient.chunk(s.subList(0, 151), 150).get(0).size());
    }

    @Test
    public void smallConnectionUsesLongerSilenceThreshold() {
        KlineWsClient w = new KlineWsClient(null, null, 150, 10_000L, 5_000L);
        assertEquals(10_000L, w.staleFor(126));
        assertEquals(10_000L, w.staleFor(20));
        assertEquals("ket noi symbol moi niem yet: 90 s + ping OkHttp", 90_000L, w.staleFor(1));
        assertTrue(w.maxDetectMs() <= 15_000L);
    }
}
