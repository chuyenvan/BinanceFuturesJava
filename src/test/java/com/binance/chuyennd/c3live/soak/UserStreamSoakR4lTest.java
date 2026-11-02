package com.binance.chuyennd.c3live.soak;

import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.Assert.*;

/** [V12 R4l] bai thu ket noi lai cuong buc (ADDENDUM R4l): boc Connector, UserStream production tu ket noi lai, 0 DELETE. */
public class UserStreamSoakR4lTest {

    @Test
    public void forceCloseMinParse() {
        assertEquals(0, UserStreamSoak.forceCloseMin(null));
        assertEquals(0, UserStreamSoak.forceCloseMin(" "));
        assertEquals(0, UserStreamSoak.forceCloseMin("0"));
        assertEquals(10, UserStreamSoak.forceCloseMin("10"));
        assertEquals(3, UserStreamSoak.forceCloseMin("3"));
        assertEquals(10, UserStreamSoak.forceCloseMin("abc"));
        assertEquals(10, UserStreamSoak.forceCloseMin("999"));
    }

    @Test
    public void forceClose6x_productionReconnect_noDelete() {
        MockExchangeGateway m = new MockExchangeGateway();
        long b0 = SoakGuard.blockedCount();
        long[] now = {1_000L};
        int[] opened = {0}, closes = {0};
        UserStream.Listener[] l = new UserStream.Listener[1];
        UserStream.Connector raw = (url, li) -> {   // okhttp gia: onOpen ngay; close() chi gui close frame
            opened[0]++;
            l[0] = li;
            li.onOpen();
            return () -> closes[0]++;
        };
        UserStreamSoak.ForceCloseConnector fc = new UserStreamSoak.ForceCloseConnector(raw, () -> now[0]);
        assertFalse("chua co socket", fc.forceClose());
        UserStream us = UserStream.forSink(SoakGuard.readOnly(m), fc, Collections.singletonList("wss://x/{key}"), e -> { }, s -> { },
                (a, ok) -> { }, () -> now[0], 15_000L, 60_000L);
        us.tick(now[0]);
        assertTrue(us.isConnected());
        for (int i = 1; i <= UserStreamSoak.FORCE_CLOSE_N; i++) {
            now[0] += 600_000L;
            us.tick(now[0]);
            assertTrue(fc.forceClose());
            assertFalse("dang cho ket noi lai => khong dong chong", fc.forceClose());
            l[0].onClosed("closing 1000");          // san tra close frame => duong production onClosed -> markDown
            assertFalse(us.isConnected());
            now[0] += 1_000L;                        // backoff 1 s
            us.tick(now[0]);
            assertTrue("lan " + i + " phai ket noi lai", us.isConnected());
        }
        assertEquals(6, fc.forced());
        assertEquals(Arrays.asList(1_000L, 1_000L, 1_000L, 1_000L, 1_000L, 1_000L), fc.reconnectMs());
        assertEquals(7, opened[0]);
        assertTrue(closes[0] >= 6);
        assertFalse(fc.pending());
        assertEquals("0 goi bi chan (khong DELETE listenKey)", b0, SoakGuard.blockedCount());
        List<Long> ok = fc.reconnectMs();
        assertTrue(UserStreamSoak.forcePass(6, ok, 6, 2_000L, 0, 0, 0, true));
        assertFalse("thieu 1 lan", UserStreamSoak.forcePass(5, ok.subList(0, 5), 5, 2_000L, 0, 0, 0, true));
        assertFalse("p100 > 10 s", UserStreamSoak.forcePass(6, Arrays.asList(1L, 1L, 1L, 1L, 1L, 10_001L), 6, 2_000L, 0, 0, 0, true));
        assertFalse("khe ho > p100 + 1 s", UserStreamSoak.forcePass(6, ok, 6, 2_001L, 0, 0, 0, true));
        assertFalse("khe ho ngoai ke hoach", UserStreamSoak.forcePass(6, ok, 7, 2_000L, 0, 0, 0, true));
        assertFalse("goi bi chan (DELETE)", UserStreamSoak.forcePass(6, ok, 6, 2_000L, 0, 0, 1, true));
        assertFalse("keepAlive loi", UserStreamSoak.forcePass(6, ok, 6, 2_000L, 1, 0, 0, true));
        assertFalse("POST loi", UserStreamSoak.forcePass(6, ok, 6, 2_000L, 0, 1, 0, true));
        assertFalse("ket thuc mat ket noi", UserStreamSoak.forcePass(6, ok, 6, 2_000L, 0, 0, 0, false));
    }
}
