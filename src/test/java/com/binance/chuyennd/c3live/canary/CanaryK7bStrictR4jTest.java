package com.binance.chuyennd.c3live.canary;

import org.junit.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

/** [V12 R4j A1 MAJ-3 / DINH CHINH 1 ADD K7B] duong EXCHANGE_TERMINAL ban SIET cua K7b. */
public class CanaryK7bStrictR4jTest {

    static final String SID = "c3s-ZECUSDT-29889630-1";
    static final long T_INJ = 1_793_377_801_749L, SENT = 1_793_377_801_764L;

    static Map<String, Object> ev(Object ts, String x) {
        Map<String, Object> e = new LinkedHashMap<>();
        if (ts != null) e.put("ts", ts);
        e.put("type", "WS_EVENT");
        e.put("e", "ALGO_UPDATE");
        e.put("s", "ZECUSDT");
        e.put("caid", SID);
        e.put("X", x);
        return e;
    }

    static Map<String, Object> cancel(long ts) {
        Map<String, Object> c = new LinkedHashMap<>();
        c.put("ts", ts);
        c.put("type", "CALL_W");
        c.put("api", "cancelStop");
        c.put("symbol", "ZECUSDT");
        c.put("cid", SID);
        c.put("ok", true);
        return c;
    }

    static String k7b(List<Map<String, Object>> j) {
        return CanaryEngine.stopEndExchangeReject(j, SID, "ZECUSDT", SENT, true, true, true, T_INJ);
    }

    @Test
    public void real1030Accepted() {
        List<Map<String, Object>> j = new ArrayList<>();
        j.add(ev(1_793_377_802_212L, "EXPIRED"));
        assertNull(k7b(j));
    }

    @Test
    public void canceledRejected_evenWithoutOwnCancel() {
        List<Map<String, Object>> j = new ArrayList<>();
        j.add(ev(1_793_377_802_212L, "CANCELED"));
        assertNotNull(k7b(j));
    }

    @Test
    public void ownCancelAfterInjectionRejected() {
        List<Map<String, Object>> j = new ArrayList<>();
        j.add(cancel(T_INJ + 100));
        j.add(ev(1_793_377_802_212L, "EXPIRED"));
        assertTrue(k7b(j).contains("cancelStop"));
    }

    @Test
    public void ownCancelBeforeInjection_notCounted() {
        List<Map<String, Object>> j = new ArrayList<>();
        j.add(cancel(T_INJ - 60_000L));   // buoc truoc (stop cu cung cid khong the xay ra, nhung moc phai dung)
        j.add(ev(1_793_377_802_212L, "EXPIRED"));
        assertNull(k7b(j));
    }

    @Test
    public void tsMustBeNumber() {
        List<Map<String, Object>> j = new ArrayList<>();
        j.add(ev(null, "EXPIRED"));
        j.add(ev("1793377802212", "EXPIRED"));
        assertNotNull(k7b(j));
    }

    @Test
    public void eventBeforeSendRejected() {
        List<Map<String, Object>> j = new ArrayList<>();
        j.add(ev(SENT - 1, "EXPIRED"));
        assertNotNull(k7b(j));
    }

    @Test
    public void k5PathStillAcceptsCanceledFromExchange() {
        List<Map<String, Object>> j = new ArrayList<>();
        j.add(ev(SENT + 4, "CANCELED"));
        assertNull("K5 (§3k R1) giu nhan CANCELED tu san", CanaryEngine.stopEndExchangeReject(j, SID, "ZECUSDT", SENT, true, true));
    }
}
