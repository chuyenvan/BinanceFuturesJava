package com.binance.chuyennd.c3live.canary;

import org.junit.Test;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.*;

/** [A1 R4j ADV] KHONG commit. Ham siet dung chung K5/K7b: truot oan? lot? */
public class A1R4jAdvK5Test {

    static final String SID = "c3s-ZECUSDT-29887460-1";

    static Map<String, Object> m(Object... kv) {
        Map<String, Object> e = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) e.put((String) kv[i], kv[i + 1]);
        return e;
    }

    static Map<String, Object> algo(long ts, String x) {
        return m("ts", ts, "type", "WS_EVENT", "e", "ALGO_UPDATE", "s", "ZECUSDT", "caid", SID, "X", x);
    }

    /**
     * K5 dua: guard doc openStops thay NEW (truoc khi san EXPIRE +4 ms) => goi cancelStop => san tra loi (lenh da EXPIRED, ok=false).
     * Thuc te: san tu ket thuc, vi the phang. Checker K5 (guardOk=false vi cancel loi) + duong san (bi loai vi co CALL_W cancelStop) => TRUOT oan.
     */
    @Test
    public void k5_failedCancelAfterExchangeExpire_isNotOwnCancel() {
        List<Map<String, Object>> j = new ArrayList<>();
        j.add(algo(1_020L, "EXPIRED"));
        j.add(m("ts", 1_050L, "type", "CALL_W", "api", "cancelStop", "symbol", "ZECUSDT", "cid", SID, "ok", false, "err", "UNKNOWN_ORDER"));
        assertNull("cancelStop LOI (ok=false) khong phai bot huy that => khong duoc lam K5 truot oan",
                CanaryEngine.stopEndExchangeReject(j, SID, "ZECUSDT", 1_000L, true, true));
    }

    /** K7b: cancelStop TRUOC moc tiem loi (vd don dep buoc truoc) khong anh huong. */
    @Test
    public void k7b_cancelBeforeInjectIgnored() {
        List<Map<String, Object>> j = new ArrayList<>();
        j.add(m("ts", 500L, "type", "CALL_W", "api", "cancelStop", "cid", SID, "ok", true));
        j.add(algo(1_200L, "EXPIRED"));
        assertNull(CanaryEngine.stopEndExchangeReject(j, SID, "ZECUSDT", 1_100L, true, true, true, 1_000L));
    }

    /** K7b: CANCELED (khong co cancelStop trong journal, vd huy tay/LEGACY) van bi tu choi; ts chuoi bi tu choi. */
    @Test
    public void k7b_canceledAndStringTsRejected() {
        List<Map<String, Object>> j = new ArrayList<>();
        j.add(algo(1_200L, "CANCELED"));
        assertNotNull(CanaryEngine.stopEndExchangeReject(j, SID, "ZECUSDT", 1_100L, true, true, true, 1_000L));
        List<Map<String, Object>> j2 = new ArrayList<>();
        Map<String, Object> e = algo(0L, "EXPIRED");
        e.put("ts", "1200");
        j2.add(e);
        assertNotNull(CanaryEngine.stopEndExchangeReject(j2, SID, "ZECUSDT", 1_100L, true, true, true, 1_000L));
    }

    /** Doi chung: chuoi K5 that 10-29 va K7b that 10-30 van DAT voi ham siet. */
    @Test
    public void realSequencesStillPass() {
        List<Map<String, Object>> k5 = new ArrayList<>();
        k5.add(algo(1_793_247_645_792L, "EXPIRED"));
        assertNull(CanaryEngine.stopEndExchangeReject(k5, SID, "ZECUSDT", 1_793_247_645_522L, true, true));
        List<Map<String, Object>> k7 = new ArrayList<>();
        k7.add(m("ts", 1_793_377_802_212L, "type", "WS_EVENT", "e", "ALGO_UPDATE", "s", "ZECUSDT", "caid",
                "c3s-ZECUSDT-29889630-1", "X", "EXPIRED"));
        assertNull(CanaryEngine.stopEndExchangeReject(k7, "c3s-ZECUSDT-29889630-1", "ZECUSDT", 1_793_377_801_764L, true, true, true,
                1_793_377_801_749L));
    }
}
