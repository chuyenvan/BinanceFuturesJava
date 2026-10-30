package com.binance.chuyennd.c3live.soak;

import com.binance.chuyennd.c3live.api.ExchangeGateway;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.fill.UserStreamEvents;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import static org.junit.Assert.*;

/** [V12 R4h] soak user-data stream CHI DOC: guard chan DELETE/lenh; monitor khe ho; UserStream.forSink. */
public class UserStreamSoakR4hTest {

    @Test
    public void guardAllowsOnlyListenKeyPostPut() {
        MockExchangeGateway m = new MockExchangeGateway();
        ExchangeGateway g = SoakGuard.readOnly(m);
        long b0 = SoakGuard.blockedCount();
        String k = g.startUserStream();
        assertNotNull(k);
        g.keepAliveUserStream(k);
        try {
            g.closeUserStream(k);
            fail("DELETE listenKey phai bi chan");
        } catch (UnsupportedOperationException expected) {
            // ok
        }
        try {
            g.account();
            fail("moi ham khac phai bi chan");
        } catch (UnsupportedOperationException expected) {
            // ok
        }
        assertEquals(b0 + 2, SoakGuard.blockedCount());
        assertNotNull(g.toString());
    }

    @Test
    public void gapMonitor_24hCut() {
        SoakGapMonitor mon = new SoakGapMonitor();
        long t = 1_000_000L, h = 3_600_000L;
        assertNull(mon.sample(t, false));          // khoi dong chua ket noi: khong tinh khe ho
        assertNull(mon.sample(t + 2_000, true));
        assertNull(mon.sample(t + 2_000 + 24 * h, false));   // san cat sau 24h
        SoakGapMonitor.Gap g = mon.sample(t + 2_000 + 24 * h + 3_000, true);
        assertNotNull(g);
        assertEquals(3_000, g.gapMs());
        assertTrue(g.is24hCut());
        assertNull(mon.sample(t + 25 * h, false));
        SoakGapMonitor.Gap g2 = mon.sample(t + 25 * h + 1_000, true);
        assertFalse("mat sau ~1h khong phai cat 24h", g2.is24hCut());
        assertTrue(mon.cut24hSeen());
        assertEquals(2, mon.gaps().size());
        assertEquals(3_000, mon.maxGapMs());
        assertTrue(mon.maxConnectedMs() >= 24 * h);
    }

    @Test
    public void forSinkDeliversEventsWithoutFillAccounting() {
        MockExchangeGateway m = new MockExchangeGateway();
        List<UserStreamEvents.Event> got = new ArrayList<>();
        UserStream.Listener[] l = new UserStream.Listener[1];
        UserStream us = UserStream.forSink(SoakGuard.readOnly(m), (url, li) -> {
            l[0] = li;
            li.onOpen();
            return () -> { };
        }, Collections.singletonList("wss://x/{key}"), got::add, s -> { }, (a, ok) -> { }, () -> 1_000L, 15_000L, 60_000L);
        us.tick(1_000L);
        assertTrue(us.isConnected());
        l[0].onText("{\"e\":\"ACCOUNT_UPDATE\",\"E\":1,\"a\":{\"B\":[],\"P\":[]}}");
        assertEquals(1, got.size());
        assertEquals("ACCOUNT_UPDATE", got.get(0).type);
    }

    @Test
    public void hoursParse() {
        assertEquals(26d, UserStreamSoak.hours(null), 0);
        assertEquals(30d, UserStreamSoak.hours("30"), 0);
        assertEquals(26d, UserStreamSoak.hours("0.5"), 0);
        assertEquals(26d, UserStreamSoak.hours("abc"), 0);
    }
}
