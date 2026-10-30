package com.binance.chuyennd.c3live.canary;

import org.junit.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

/** [A1 R4i ADV] KHONG commit. K7b duong EXCHANGE_TERMINAL co phan biet duoc guard TU HUY stop (loi that) voi san tu EXPIRE? */
public class A1R4iAdvK7bTest {

    static final String SID = "c3s-ZECUSDT-29889630-1";

    static Map<String, Object> ev(long ts, String x) {
        Map<String, Object> e = new LinkedHashMap<>();
        e.put("ts", ts);
        e.put("type", "WS_EVENT");
        e.put("e", "ALGO_UPDATE");
        e.put("s", "ZECUSDT");
        e.put("caid", SID);
        e.put("X", x);
        return e;
    }

    /**
     * Loi production gia dinh: guard KHONG giu (B) ma tu huy stop du positionRisk loi (khong xac minh duoc phang).
     * Journal: CALL_W cancelStop sid ok=true roi ALGO_UPDATE X=CANCELED. Checker phai TU CHOI (khong phai san tu ket thuc).
     */
    @Test
    public void guardOwnCancelMustNotPassAsExchangeTerminal() {
        List<Map<String, Object>> j = new ArrayList<>();
        Map<String, Object> c = new LinkedHashMap<>();
        c.put("ts", 1_010L);
        c.put("type", "CALL_W");
        c.put("api", "cancelStop");
        c.put("symbol", "ZECUSDT");
        c.put("cid", SID);
        c.put("ok", true);
        j.add(c);
        j.add(ev(1_060L, "CANCELED"));
        assertNotNull("guard tu huy stop (loi that) bi checker coi la EXCHANGE_TERMINAL => K7b DAT gia",
                CanaryEngine.stopEndExchangeReject(j, SID, "ZECUSDT", 1_000L, true, true));
    }

    /** Su kien thieu ts (khong phai Number) — khong chung minh duoc 'sau lenh dong'. */
    @Test
    public void eventWithoutTsMustNotPass() {
        List<Map<String, Object>> j = new ArrayList<>();
        Map<String, Object> e = ev(0L, "EXPIRED");
        e.remove("ts");
        j.add(e);
        assertNotNull(CanaryEngine.stopEndExchangeReject(j, SID, "ZECUSDT", 1_000L, true, true));
    }

    /** Doi chung: chuoi that 10-30 (EXPIRED, ts nhan sau firstSent) => chap nhan. */
    @Test
    public void real1030SequenceAccepted() {
        List<Map<String, Object>> j = new ArrayList<>();
        j.add(ev(1_793_377_802_212L, "EXPIRED"));
        assertNull(CanaryEngine.stopEndExchangeReject(j, SID, "ZECUSDT", 1_793_377_801_764L, true, true));
    }
}
