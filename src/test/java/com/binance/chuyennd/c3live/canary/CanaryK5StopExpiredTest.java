package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;

import static org.junit.Assert.*;

/**
 * [3k R1] K5 (time-stop 168h) — san TU ket thuc stop closePosition khi vi the ve 0.
 *
 * <p>That 2026-10-29 (journal {@code report_20261029_112139/files/canary_20261029_112031_step_K5.jsonl}):
 * {@code c3x-ZECUSDT-29887460-1} FILLED 0.016 @1236.60, {@code ALGO_UPDATE caid=c3s-ZECUSDT-29887460-1 X=EXPIRED}
 * o T+4 ms, journal KHONG co {@code cancelStop} => ban cu TRUOT o buoc con "guard khong huy stop".
 * Test mock offline, khong goi san, dong ho gia.
 */
public class CanaryK5StopExpiredTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final String MAIN = "C00USDT";
    static final String AUX = "C01USDT";
    static final long T0 = 1_793_000_000_000L;

    MockExchangeGateway mock;
    final AtomicLong now = new AtomicLong(T0);
    File dir;
    final List<String> telegram = Collections.synchronizedList(new ArrayList<>());
    volatile Consumer<Long> hook = t -> { };
    final AtomicBoolean expired = new AtomicBoolean(false);
    volatile String mainSym = MAIN;

    @Before
    public void setUp() throws Exception {
        mock = new MockExchangeGateway();
        mock.dynamicAccount = true;
        mock.feeRate = new BigDecimal("0.0005");
        mock.now = T0;
        mock.setPrice(MAIN, new BigDecimal("1310.36"));
        mock.setPrice(AUX, new BigDecimal("100"));
        mock.exchangeInfo = info(MAIN, AUX);
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
        d.sleeper = ms -> {
            long t = now.addAndGet(ms);
            mock.now = t;
            hook.accept(t);
        };
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

    private ExchangeInfo info(String... syms) {
        List<SymbolMeta> l = new ArrayList<>();
        for (String s : syms) {
            l.add(SymbolMeta.builder(s).pair(s).status("TRADING").contractType("PERPETUAL").baseAsset(s.replace("USDT", ""))
                    .quoteAsset("USDT").marginAsset("USDT").underlyingType("COIN").underlyingSubType(Collections.emptyList())
                    .onboardDate(1_600_000_000_000L).deliveryDate(4_133_404_800_000L).tickSize(new BigDecimal("0.01"))
                    .minPrice(new BigDecimal("0.01")).maxPrice(new BigDecimal("100000")).stepSize(new BigDecimal("0.001"))
                    .minQty(new BigDecimal("0.001")).maxQty(new BigDecimal("10000000"))
                    .marketStepSize(new BigDecimal("0.001")).marketMinQty(new BigDecimal("0.001"))
                    .marketMaxQty(new BigDecimal("1000000")).minNotional(new BigDecimal("5")).build());
        }
        return new ExchangeInfo(0L, Collections.emptyList(), l);
    }

    private void sess(CanaryEngine e) {
        e.state().symMain = mainSym;
        e.state().symAux = AUX;
        e.state().tmb0 = 10_000d;
        e.state().tmb0Ms = now.get();
    }

    /** K1 mo leg + stop bao ve; tra ve sid stop. */
    private String openWithStop(CanaryEngine e) throws Exception {
        CanaryEngine.Result r = e.step("K1");
        assertEquals(r.line() + " data=" + r.data, CanaryEngine.DAT, r.verdict);
        List<OrderInfo> st = mock.openStops(MAIN);
        assertEquals(1, st.size());
        return st.get(0).getClientOrderId();
    }

    /**
     * T1 (mock): duong guard huy stop (mock huy dong bo, khong co race 4 ms nhu san) van DAT va ghi stopEnd=GUARD_CANCELED
     * => fix KHONG noi long duong cu.
     */
    @Test
    public void t1GuardCancelPathStillPasses() throws Exception {
        CanaryEngine e = engine();
        sess(e);
        String sid = openWithStop(e);
        CanaryEngine.Result r = e.step("K5");
        assertEquals(r.line() + " data=" + r.data, CanaryEngine.DAT, r.verdict);
        Object end = e.state().steps.get("K5").data.get("stopEnd");
        assertEquals("GUARD_CANCELED", end);
        assertEquals(Boolean.TRUE, e.state().steps.get("K5").data.get("stopClosePosition"));
        assertNotNull("guard da huy (journal cancelStop ok)", e.state().steps.get("K5").data.get("guardCancel"));
        assertEquals(0, BigDecimal.ZERO.compareTo(mock.position(MAIN)));
        assertTrue(mock.openStops(MAIN).isEmpty());
        e.close();
    }

    /**
     * T3 (fixture THAT 10-29): nguyen van ALGO_UPDATE X=EXPIRED cua K5 (journal
     * report_20261029_112139/files/canary_20261029_112031_step_K5.jsonl, ts=1793247645792) + close order ts=1793247645611,
     * vi the da xac nhan 0 => CHAP NHAN (ket thuc hop le), khong doi hoi guard cancelStop.
     */
    @Test
    public void t3RealJournalFixtureIsAccepted() {
        String sid = "c3s-ZECUSDT-29887460-1";
        Map<String, Object> j = new HashMap<>();
        j.put("type", "WS_EVENT");
        j.put("e", "ALGO_UPDATE");
        j.put("s", "ZECUSDT");
        j.put("caid", sid);
        j.put("X", "EXPIRED");
        j.put("ts", 1793247645792L);   // ts ghi journal (nhan event), su kien T=1793247645571
        long closeTs = 1793247645611L;  // CALL_W newMarketOrder:SELL:RO (c3x-...-1)
        assertNull(CanaryEngine.stopEndExchangeReject(Arrays.asList(j), sid, "ZECUSDT", closeTs, true, true));
        // doi chung: su kien TRUOC moc dong (hoac thieu caid) KHONG duoc chap nhan — dung nhu journal that (chi 1 dong EXPIRED)
        assertEquals("khong co ALGO_UPDATE terminal dung caid sau khi dong",
                CanaryEngine.stopEndExchangeReject(Arrays.asList(j), sid, "ZECUSDT", 1793247645793L, true, true));
    }

    /**
     * T2: helper — terminal dung caid, SAU khi dong, vi the 0, closePosition => nhan; cac truong hop khac TU CHOI.
     * (EXPIRED khi vi the != 0 la MAT STOP, khong phai ket thuc.)
     */
    @Test
    public void t2HelperOnlyAcceptsTerminalOfSameCidAfterClose() {
        String sid = "c3s-X-1";
        Map<String, Object> ok = ev(sid, "X", "EXPIRED", 200L);
        Map<String, Object> old = ev(sid, "X", "EXPIRED", 100L);
        Map<String, Object> trig = ev(sid, "X", "TRIGGERING", 200L);
        Map<String, Object> other = ev("c3s-Y-1", "X", "EXPIRED", 200L);
        Map<String, Object> cancel = ev(sid, "X", "CANCELED", 200L);
        Map<String, Object> foreign = ev("c3x-X-1", "X", "EXPIRED", 200L);
        Map<String, Object> wrongSym = ev(sid, "X", "EXPIRED", 200L);
        wrongSym.put("s", "D00USDT");
        List<Map<String, Object>> es = Arrays.asList(old, trig, other, ok);
        assertNull(CanaryEngine.stopEndExchangeReject(es, sid, "C00USDT", 150L, true, true));
        assertEquals("terminal truoc khi dong khong duoc tinh", "khong co ALGO_UPDATE terminal dung caid sau khi dong",
                CanaryEngine.stopEndExchangeReject(es, sid, "C00USDT", 250L, true, true));
        assertEquals("chi TRIGGERING thi chua xong", "khong co ALGO_UPDATE terminal dung caid sau khi dong",
                CanaryEngine.stopEndExchangeReject(Arrays.asList(trig), sid, "C00USDT", 0L, true, true));
        assertEquals("caid la", "khong co ALGO_UPDATE terminal dung caid sau khi dong",
                CanaryEngine.stopEndExchangeReject(Arrays.asList(other), sid, "C00USDT", 0L, true, true));
        assertNull(CanaryEngine.stopEndExchangeReject(Arrays.asList(cancel), sid, "C00USDT", 0L, true, true));
        assertEquals("caid khong phai c3s- (khong thuoc canary)", "caid khong thuoc canary",
                CanaryEngine.stopEndExchangeReject(Arrays.asList(foreign), "c3x-X-1", "C00USDT", 0L, true, true));
        assertEquals("sai symbol", "khong co ALGO_UPDATE terminal dung caid sau khi dong",
                CanaryEngine.stopEndExchangeReject(Arrays.asList(wrongSym), sid, "C00USDT", 0L, true, true));
        assertEquals("sid null", "caid khong thuoc canary",
                CanaryEngine.stopEndExchangeReject(es, null, "C00USDT", 0L, true, true));
    }

    /** T4: EXPIRED khi vi the san != 0 => TU CHOI (mat stop, khong phai ket thuc) => K5 TRUOT. Mock: fill SELL khong an vi the. */
    @Test
    public void t4ExpiredWhilePositionOpenIsRejected() throws Exception {
        CanaryEngine e = engine();
        sess(e);
        openWithStop(e);
        mock.keepPositionOnSell = true;      // su co: lenh dong khong an vi the
        mock.expireStopsOnSellFill = true;   // san ket thuc stop ngay sau fill
        CanaryEngine.Result r = e.step("K5");
        assertEquals(r.line() + " data=" + r.data, CanaryEngine.TRUOT, r.verdict);
        Map<String, Object> d = e.state().steps.get("K5").data;
        assertEquals("stopEnd", "NONE", d.get("stopEnd"));
        assertEquals("vi the != 0", d.get("exchangeTerminalWhy"));
        assertTrue("phai noi ro ly do tu choi: " + r.line(), r.line().contains("[vi the != 0]"));
        assertTrue("vi the con duoc bao lai", r.line().contains("vi the con"));
        assertEquals("vi the san van con (fill SELL khong an vi the)", 1, mock.position(MAIN).signum());
        e.close();
    }

    /** T5: stop qty reduce-only (khong phai closePosition) bi san ket thuc => TU CHOI du vi the 0. */
    @Test
    public void t5QtyModeStopTerminalIsNotAccepted() {
        Map<String, Object> ok = ev("c3s-X-1", "X", "EXPIRED", 200L);
        assertEquals("stop khong phai closePosition", "stop khong phai closePosition",
                CanaryEngine.stopEndExchangeReject(Arrays.asList(ok), "c3s-X-1", "C00USDT", 0L, true, false));
    }

    private static Map<String, Object> ev(String caid, String k, String x, long ts) {
        Map<String, Object> m = new HashMap<>();
        m.put("type", "WS_EVENT");
        m.put("e", "ALGO_UPDATE");
        m.put("caid", caid);
        m.put(k, x);
        m.put("ts", ts);
        return m;
    }
}
