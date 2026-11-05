package com.binance.chuyennd.ops;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.util.*;

import static org.junit.Assert.*;

/**
 * [V12 R4p Bug3 — E2E F2b] 429 chi dinh duong DAT LENH, xen call doc thanh cong: bo dem C3 cu bi reset => khong latch. Bo dem 429
 * RIENG cho lenh (doc OK khong reset, lenh OK reset) => latch C3 cung nguong C3_CONSEC; tu go sau het cua so 429 + 30' sach +
 * >= 3 call OK (khoang latch -> go >= 30').
 */
public class KillSwitchOrder429Test {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_792_900_000_000L;
    static final long M = 60_000L;

    static final class ListSink implements KillSwitchEngine.Sink {
        final List<String> lines = new ArrayList<>();
        public void info(String m) { lines.add("I " + m); }
        public void warn(String m) { lines.add("W " + m); }
    }

    private KillSwitchEngine act(List<String> alerts, long now) {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.latchFile = new File(tmp.getRoot(), "run/killsw_latch.json");
        p.resetFile = new File(tmp.getRoot(), "run/killsw_reset.req");
        p.autoReleaseMs = 30 * M;
        p.autoReleaseCodes.add("C3");   // = OpsConfig c3_live
        KillSwitchEngine e = new KillSwitchEngine(KillSwitchEngine.Mode.ACT, "act", new ListSink(), null, () -> 10000d,
                () -> 0.60f, now, p);
        e.setAlert(alerts::add);
        return e;
    }

    private static Map<String, List<KlineObjectSimple>> window(long btcStart) {
        Map<String, List<KlineObjectSimple>> w = new HashMap<>();
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = btcStart;
        w.put("BTCUSDT", new ArrayList<>(Collections.singletonList(k)));
        return w;
    }

    private static void cleanMinute(KillSwitchEngine e, long t) {
        e.onTickStart(t);
        e.onMarketData(t, window(t - M));
        e.periodic(t);
        e.onApiResult(t, "positions", true);
    }

    /** 1 lenh MARKET 429, kem call doc OK truoc/sau (nhu runtime: positions/openOrders moi nhip). */
    private static void order429(KillSwitchEngine e, long t) {
        e.onApiResult(t, "positions", true);
        e.onApiResult(t, "newMarketOrder", false);
        e.onOrderResult(t, "newMarketOrder", false, true);
        e.onApiResult(t, "openOrders", true);
    }

    @Test
    public void f2bSixOrder429InterleavedWithOkReadsLatchesC3ThenReleasesAfterAtLeast30Min() {
        List<String> alerts = new ArrayList<>();
        KillSwitchEngine e = act(alerts, T0);
        long on = -1;
        for (int i = 0; i < 6; i++) {
            long t = T0 + i * 1_000L;
            order429(e, t);
            if (on < 0 && e.latchCodes().contains("C3")) on = t;
        }
        assertEquals("latch o lenh 429 thu 5 (nguong C3_CONSEC)", T0 + 4_000L, on);
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, e.requiredAction());
        long off = -1;
        for (int i = 1; i <= 90 && off < 0; i++) {
            long t = T0 + i * M;
            cleanMinute(e, t);
            if (e.requiredAction() == KillSwitchEngine.Action.NONE) off = t;
        }
        assertTrue("phai tu go", off > 0);
        assertTrue("go >= 30' sau latch: " + (off - on) / M, off - on >= 30 * M);
        assertTrue(alerts.stream().anyMatch(m -> m.contains("AUTO_RELEASE codes=[C3]")));
        // E2E F2b lan 1 (r4p): 429 thu 6 (xep hang) roi vao 1 lenh 3 h sau => KHONG duoc latch lai
        order429(e, off + 3 * 60 * M);
        assertEquals("1 lenh 429 le sau 3 h: khong latch lai", KillSwitchEngine.Action.NONE, e.requiredAction());
    }

    @Test
    public void order429OlderThanHoldWindowDoesNotAccumulate() {
        KillSwitchEngine e = act(new ArrayList<>(), T0);
        for (int i = 0; i < 4; i++) order429(e, T0 + i);
        order429(e, T0 + 3 + KillSwitchEngine.C3_ORDER429_HOLD_MS + 1);
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        assertFalse(e.latchCodes().contains("C3"));
    }

    @Test
    public void f2ThreeOrder429DoNotLatch() {
        KillSwitchEngine e = act(new ArrayList<>(), T0);
        for (int i = 0; i < 3; i++) order429(e, T0 + i);
        assertFalse(e.latchCodes().contains("C3"));
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
    }

    @Test
    public void successfulOrderResetsOrder429Counter() {
        KillSwitchEngine e = act(new ArrayList<>(), T0);
        for (int i = 0; i < 4; i++) order429(e, T0 + i);
        e.onApiResult(T0 + 10, "newStopMarket", true);
        e.onOrderResult(T0 + 10, "newStopMarket", true, false);
        for (int i = 0; i < 4; i++) order429(e, T0 + 20 + i);
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        order429(e, T0 + 30);
        assertTrue("5 lien tiep sau lenh OK => latch", e.latchCodes().contains("C3"));
    }

    @Test
    public void nonRateLimitOrderErrorNeitherCountsNorResets() {
        KillSwitchEngine e = act(new ArrayList<>(), T0);
        for (int i = 0; i < 4; i++) order429(e, T0 + i);
        e.onApiResult(T0 + 10, "newMarketOrder", false);
        e.onOrderResult(T0 + 10, "newMarketOrder", false, false);   // 5xx/timeout
        e.onApiResult(T0 + 11, "positions", true);
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        order429(e, T0 + 20);
        assertTrue(e.latchCodes().contains("C3"));
    }

    @Test
    public void legacyConsecutiveApiErrorsStillLatch() {
        KillSwitchEngine e = act(new ArrayList<>(), T0);
        for (int i = 0; i < 5; i++) e.onApiResult(T0 + i, "positions", false);
        assertTrue(e.latchCodes().contains("C3"));
    }

    @Test
    public void rateLimitedClassification() {
        assertTrue(C3LiveOrderExecutor.ApiObserver.rateLimited(
                new GatewayException(ErrorKind.RATE_LIMIT, 429, -1003, "429", true, 0L, null)));
        assertTrue(C3LiveOrderExecutor.ApiObserver.rateLimited(
                new GatewayException(ErrorKind.RATE_LIMIT, 418, -1003, "418", true, 0L, null)));
        assertTrue(C3LiveOrderExecutor.ApiObserver.rateLimited(
                new GatewayException(ErrorKind.RATE_LIMIT, 400, -1015, "too many orders", true, 0L, null)));
        assertFalse("guard client (http 0, chua gui)", C3LiveOrderExecutor.ApiObserver.rateLimited(
                new GatewayException(ErrorKind.RATE_LIMIT, 0, 0, "rate guard: het ngan sach", true, 0L, null)));
        assertFalse(C3LiveOrderExecutor.ApiObserver.rateLimited(
                new GatewayException(ErrorKind.FILTER, 400, -1013, "filter", true, 0L, null)));
        assertFalse(C3LiveOrderExecutor.ApiObserver.rateLimited(new IllegalStateException("x")));
    }
}
