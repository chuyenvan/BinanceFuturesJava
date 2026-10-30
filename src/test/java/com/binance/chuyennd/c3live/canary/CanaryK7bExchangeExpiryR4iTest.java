package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.entry.C3LiveFixtures;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;

import static org.junit.Assert.*;

/**
 * [V12 R4i] K7b TRUOT 10-30 23:30 (canary 3k, tai khoan chinh): san TU EXPIRE stop closePosition +4 ms sau khop c3x-, truoc luc
 * guard doc openStops ⇒ guard GONE (khong co stop de giu) ⇒ khong co (B) — production DUNG (c3x- FILLED du qty = phang). Loi o
 * checker K7b (chi chap nhan duong "giu stop"). Tai hien bang mock {@code expireStopsOnSellFill} (cung chuoi su kien) + duong cu.
 */
public class CanaryK7bExchangeExpiryR4iTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();
    static final long T0 = 1_793_000_000_000L;
    MockExchangeGateway mock;
    final AtomicLong now = new AtomicLong(T0);
    File dir;
    final List<String> telegram = Collections.synchronizedList(new ArrayList<>());

    @Before
    public void setUp() throws Exception {
        mock = new MockExchangeGateway();
        mock.exchangeInfo = C3LiveFixtures.info(6);
        mock.dynamicAccount = true;
        mock.feeRate = new BigDecimal("0.0005");
        mock.now = T0;
        for (int i = 0; i < 6; i++) {
            mock.setPrice(C3LiveFixtures.sym(i), BigDecimal.ONE);
            mock.quoteVolumes.put(C3LiveFixtures.sym(i), new BigDecimal(1000 - i * 100));
        }
        dir = tmp.newFolder("run", "canary");
    }

    UserStream.Connector fakeWs() {
        return (url, l) -> {
            Consumer<String> sink = l::onText;
            mock.wsSink = sink;
            l.onOpen();
            return () -> {
                if (mock.wsSink == sink) mock.wsSink = null;
            };
        };
    }

    CanaryEngine engine() throws Exception {
        CanaryEngine.Deps d = new CanaryEngine.Deps();
        d.raw = mock;
        d.dir = dir;
        d.clock = now::get;
        d.sleeper = ms -> mock.now = now.addAndGet(ms);
        d.connector = fakeWs();
        d.wsUrls = UserStream.parseUrls(UserStream.DEFAULT_URLS);
        d.alert = telegram::add;
        d.legacy = s -> false;
        d.usedWeight1m = () -> 7;
        d.journalName = "j_" + now.get() + "_" + System.nanoTime() + ".jsonl";
        d.jarId = () -> new String[]{"jarA", String.valueOf(T0 - 3_600_000L)};
        d.legacySize = -1;
        CanaryEngine.Config c = new CanaryEngine.Config();
        c.expectTmb = 10_000d;
        c.priorLossUsdt = 0d;
        return new CanaryEngine(d, c);
    }

    private CanaryEngine.Result k7b() throws Exception {
        CanaryEngine e0 = engine();
        CanaryEngine.Result k0 = e0.preflight();
        e0.close();
        assertEquals(k0.line(), CanaryEngine.DAT, k0.verdict);
        CanaryEngine e = engine();
        CanaryEngine.Result r = e.step("K7B");
        e.close();
        return r;
    }

    @Test
    public void exchangeExpiresClosePositionStop_beforeGuard_noB_isLegit() throws Exception {
        mock.expireStopsOnSellFill = true;   // nhu san that 10-29 (K5) va 10-30 (K7b): EXPIRE stop closePosition ngay sau khop SELL
        CanaryEngine.Result r = k7b();
        assertEquals(r.line() + " data=" + r.data, CanaryEngine.DAT, r.verdict);
        assertEquals("EXCHANGE_TERMINAL", r.data.get("s1.stopEnd"));
        assertEquals(Boolean.TRUE, r.data.get("s1.closeFull"));
        assertNull("khong len (A)", r.data.get("A.firstSeenAfterCloseMs"));
        assertTrue(mock.openStops(null).isEmpty());
    }

    @Test
    public void stopStillOpen_guardKeeps_BRequired_unchanged() throws Exception {
        CanaryEngine.Result r = k7b();
        assertEquals(r.line() + " data=" + r.data, CanaryEngine.DAT, r.verdict);
        assertEquals("KEPT_B", r.data.get("s1.stopEnd"));
    }

    @Test
    public void closeFullHelper() {
        Map<String, Object> c = new HashMap<>();
        c.put("status", "FILLED");
        c.put("executedQty", "0.016");
        assertTrue(CanaryEngine.k7bCloseFull(c, new BigDecimal("0.016")));
        assertFalse("khop thieu", CanaryEngine.k7bCloseFull(c, new BigDecimal("0.020")));
        c.put("status", "NEW");
        assertFalse(CanaryEngine.k7bCloseFull(c, new BigDecimal("0.016")));
        assertFalse(CanaryEngine.k7bCloseFull(null, new BigDecimal("0.016")));
    }

    @Test
    public void noExchangeEvidence_stillFails() {
        // khong co ALGO_UPDATE terminal dung caid => checker van TRUOT (fail-closed)
        assertNotNull(CanaryEngine.stopEndExchangeReject(Collections.<Map<String, Object>>emptyList(), "c3s-X-1-1", "XUSDT", 0L,
                true, true));
        assertNotNull("c3x- khong du qty => khong coi la phang", CanaryEngine.stopEndExchangeReject(
                Collections.<Map<String, Object>>emptyList(), "c3s-X-1-1", "XUSDT", 0L, false, true));
    }
}
