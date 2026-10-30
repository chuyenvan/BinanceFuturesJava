package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.exec.C3LiveCids;
import org.junit.Test;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

/** [V12 R4g] K5: moc "sau lenh dong" = firstSentMs (gui that) thay ts ACK — 10-29 ALGO_UPDATE EXPIRED toi truoc ACK. */
public class CanaryK5SinceR4gTest {

    @Test
    public void sinceUsesFirstSentWhenKnown() {
        Map<String, Object> close = new HashMap<>();
        close.put("ts", 1_000L);
        assertEquals(990L, CanaryEngine.k5Since(close, 990L));
        assertEquals("khong co firstSentMs => ts ACK (cu)", 1_000L, CanaryEngine.k5Since(close, -1L));
        assertEquals(0L, CanaryEngine.k5Since(null, -1L));
        assertEquals(990L, CanaryEngine.k5Since(null, 990L));
    }

    @Test
    public void algoBetweenSendAndAck_acceptedWithFirstSent_rejectedWithAck() {
        String sid = C3LiveCids.STOP_PREFIX + "k5test";
        Map<String, Object> e = new HashMap<>();
        e.put("type", "WS_EVENT");
        e.put("e", "ALGO_UPDATE");
        e.put("caid", sid);
        e.put("s", "ZECUSDT");
        e.put("X", "EXPIRED");
        e.put("ts", 995L);   // gui 990, khop ~991, san EXPIRE stop +4 ms, ACK 1000
        List<Map<String, Object>> j = Collections.singletonList(e);
        Map<String, Object> close = new HashMap<>();
        close.put("ts", 1_000L);
        assertNull(CanaryEngine.stopEndExchangeReject(j, sid, "ZECUSDT", CanaryEngine.k5Since(close, 990L), true, true));
        assertNotNull("moc ACK cu => TRUOT gia", CanaryEngine.stopEndExchangeReject(j, sid, "ZECUSDT",
                CanaryEngine.k5Since(close, -1L), true, true));
    }
}
