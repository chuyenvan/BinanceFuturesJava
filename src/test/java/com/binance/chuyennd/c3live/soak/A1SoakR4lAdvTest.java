package com.binance.chuyennd.c3live.soak;

import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Test;

import java.util.Collections;
import java.util.List;

import static org.junit.Assert.*;

/** [A1 SOAK R4l ADV] KHONG commit. */
public class A1SoakR4lAdvTest {

    /** San KHONG tra close frame: okhttp huy sau 60 s (onFailure) => ket noi lai > 10 s => KHONG duoc DAT. */
    @Test
    public void noCloseFrame_failureAfter60s_mustNotPass() {
        MockExchangeGateway m = new MockExchangeGateway();
        long[] now = {1_000L};
        UserStream.Listener[] l = new UserStream.Listener[1];
        UserStream.Connector raw = (url, li) -> {
            l[0] = li;
            li.onOpen();
            return () -> { };   // close() khong gay callback nao
        };
        UserStreamSoak.ForceCloseConnector fc = new UserStreamSoak.ForceCloseConnector(raw, () -> now[0]);
        UserStream us = UserStream.forSink(SoakGuard.readOnly(m), fc, Collections.singletonList("wss://x/{key}"), e -> { }, s -> { },
                (a, ok) -> { }, () -> now[0], 15_000L, 60_000L);
        us.tick(now[0]);
        now[0] += 600_000L;
        us.tick(now[0]);
        assertTrue(fc.forceClose());
        for (int i = 0; i < 60; i++) {
            now[0] += 1_000L;
            us.tick(now[0]);
        }
        l[0].onClosed("failure SocketTimeoutException");
        now[0] += 1_000L;
        us.tick(now[0]);
        assertTrue(us.isConnected());
        List<Long> r = fc.reconnectMs();
        assertEquals(1, r.size());
        assertTrue("do tu luc dong: " + r, r.get(0) >= 61_000L);
        assertFalse(UserStreamSoak.forcePass(6, java.util.Arrays.asList(1L, 1L, 1L, 1L, 1L, r.get(0)), 6, 1_000L, 0, 0, 0, true));
    }

    /** San tu cat (khong cuong buc) giua 2 lan dong: KHONG duoc tinh la ket noi lai cuong buc; so lan dong khong doi. */
    @Test
    public void spontaneousDropNotCountedAsForced() {
        MockExchangeGateway m = new MockExchangeGateway();
        long[] now = {1_000L};
        UserStream.Listener[] l = new UserStream.Listener[1];
        UserStream.Connector raw = (url, li) -> {
            l[0] = li;
            li.onOpen();
            return () -> { };
        };
        UserStreamSoak.ForceCloseConnector fc = new UserStreamSoak.ForceCloseConnector(raw, () -> now[0]);
        UserStream us = UserStream.forSink(SoakGuard.readOnly(m), fc, Collections.singletonList("wss://x/{key}"), e -> { }, s -> { },
                (a, ok) -> { }, () -> now[0], 15_000L, 60_000L);
        us.tick(now[0]);
        now[0] += 300_000L;
        us.tick(now[0]);
        l[0].onClosed("closing 1001");   // san tu cat
        now[0] += 1_000L;
        us.tick(now[0]);
        assertTrue(us.isConnected());
        assertEquals(0, fc.forced());
        assertTrue(fc.reconnectMs().isEmpty());
        assertFalse(fc.pending());
    }
}
