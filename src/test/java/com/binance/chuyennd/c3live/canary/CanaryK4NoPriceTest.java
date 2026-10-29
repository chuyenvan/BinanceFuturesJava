package com.binance.chuyennd.c3live.canary;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.OrderInfo;
import com.binance.chuyennd.c3live.api.OrderKind;
import com.binance.chuyennd.c3live.api.OrderStatus;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import com.binance.chuyennd.c3live.api.Side;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.exec.C3LiveCids;
import com.binance.chuyennd.c3live.fill.UserStream;
import com.binance.chuyennd.c3live.mock.MockExchangeGateway;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;

import static org.junit.Assert.*;

/**
 * [3j] Round 3j — K4 fix (ACK MARKET {@code status=FILLED} KHONG co {@code avgPrice}).
 *
 * <p>Bug 2026-10-28 (canary step K4): ACK FILLED qty 0.015, {@code px=-} => {@code LiveBookC3.confirm(cid,0.015,0.0)}
 * huy giu cho + xoa cum du vi the san CO THAT => leg bi coi la "khong khop", vi the khong stop. Test tai hien dung
 * chuoi that (T7: fixture lay tu journal {@code report_20261028_092055/files/canary_20261028_091916_step_K4.jsonl}).
 *
 * <p>Moi test la mock offline (khong goi san), dong ho gia, websocket gia.
 */
public class CanaryK4NoPriceTest {

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
    volatile String[] jarIdVal = {"jarA", String.valueOf(T0 - 3_600_000L)};

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

    /** websocket gia: noi wsSink cua mock vao listener. */
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

    CanaryEngine engine(CanaryEngine.Config cfg) throws Exception {
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
        d.jarId = () -> jarIdVal;
        d.legacySize = -1;
        return new CanaryEngine(d, cfg);
    }

    static CanaryEngine.Config cfg() {
        CanaryEngine.Config c = new CanaryEngine.Config();
        c.expectTmb = 10_000d;
        c.priorLossUsdt = 0d;
        return c;
    }

    static final String CID_K4 = "c3-ZECUSDT-29885900-0";
    static final long ORDER_ID_K4 = 812083551851L;
    static final long K4_SEND_MS = 1_793_154_001_683L;

    /**
     * ACK that 10-28 (journal, type=CALL_W api=newMarketOrder:BUY): KHONG co truong avgPrice => OrderInfo.avgPrice = null.
     */
    static final String REAL_ACK_20261028 =
            "{\"ts\":1793154001683,\"type\":\"CALL_W\",\"api\":\"newMarketOrder:BUY\",\"symbol\":\"ZECUSDT\","
                    + "\"cid\":\"c3-ZECUSDT-29885900-0\",\"ok\":true,\"status\":\"FILLED\",\"orderId\":812083551851,"
                    + "\"executedQty\":\"0.015\",\"stopPrice\":\"0.00\",\"origQty\":\"0.015\",\"closePosition\":false,"
                    + "\"latMs\":100,\"wOwn\":8}";

    /**
     * ORDER_TRADE_UPDATE that 10-28 (journal, type=WS_EVENT e=ORDER_TRADE_UPDATE c=c3-ZECUSDT-29885900-0 X=FILLED):
     * ap=1310.36, L=1310.36, z=0.015 — nguyen van truong {@code raw}.
     */
    static final String REAL_WS_FILLED_20261028 =
            "{\"e\":\"ORDER_TRADE_UPDATE\",\"T\":1793154001635,\"E\":1793154001635,\"o\":{\"s\":\"ZECUSDT\","
                    + "\"c\":\"c3-ZECUSDT-29885900-0\",\"S\":\"BUY\",\"o\":\"MARKET\",\"f\":\"GTC\",\"q\":\"0.015\","
                    + "\"p\":\"0\",\"ap\":\"1310.36\",\"sp\":\"0\",\"x\":\"TRADE\",\"X\":\"FILLED\",\"i\":812083551851,"
                    + "\"l\":\"0.015\",\"z\":\"0.015\",\"L\":\"1310.36\",\"n\":\"0.0098277\",\"N\":\"USDT\","
                    + "\"T\":1793154001635,\"t\":1739701662,\"b\":\"0\",\"a\":\"0\",\"m\":false,\"R\":false,"
                    + "\"wt\":\"CONTRACT_PRICE\",\"ot\":\"MARKET\",\"ps\":\"BOTH\",\"cp\":false,\"rp\":\"0\",\"pP\":false,"
                    + "\"si\":0,\"ss\":0,\"V\":\"EXPIRE_MAKER\",\"pm\":\"NONE\",\"gtd\":0,\"er\":\"0\"}}";

    /** exchangeInfo tong hop: 2 symbol canary voi buoc gia/qty nhu ZECUSDT that. */
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

    private void sess(CanaryEngine e, String main, String aux) {
        e.state().symMain = main;
        e.state().symAux = aux;
        e.state().tmb0 = 10_000d;
        e.state().tmb0Ms = now.get();
    }

    /** cid cua leg da mo trong buoc (doc tu data buoc, khong doan phut). */
    @SuppressWarnings("unchecked")
    private static String legCid(CanaryEngine e, String step) {
        CanaryState.StepRecord s = e.state().steps.get(step);
        assertNotNull("thieu ket qua " + step, s);
        Map<String, Object> leg = (Map<String, Object>) s.data.get("leg");
        assertNotNull("thieu leg trong " + step, leg);
        return String.valueOf(leg.get("cid"));
    }

    private static void ok(CanaryEngine.Result r) {
        assertEquals(r.line() + " data=" + r.data, CanaryEngine.DAT, r.verdict);
    }

    private static List<Map<String, Object>> events(CanaryEngine e, String type) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> m : e.journal().entries()) if (type.equals(m.get("type"))) out.add(m);
        return out;
    }

    private static Map<String, Object> firstEvent(CanaryEngine e, String type, String cid) {
        for (Map<String, Object> m : e.journal().entries()) {
            if (!type.equals(m.get("type"))) continue;
            if (cid == null || cid.equals(m.get("cid"))) return m;
        }
        return null;
    }

    /** Dung OrderInfo tu dung dong journal CALL_W (khong them/bot truong nao). */
    private OrderInfo ackFromFixture(String json, String mustCid) {
        JsonObject o = JsonParser.parseString(json).getAsJsonObject();
        assertEquals("cid sinh ra phai trung cid that", mustCid, o.get("cid").getAsString());
        return OrderInfo.builder().kind(OrderKind.REGULAR).symbol(o.get("symbol").getAsString())
                .orderId(o.get("orderId").getAsLong()).clientOrderId(o.get("cid").getAsString()).side(Side.BUY)
                .type("MARKET").status(OrderStatus.parse(o.get("status").getAsString()))
                .rawStatus(o.get("status").getAsString()).origQty(new BigDecimal(o.get("origQty").getAsString()))
                .executedQty(new BigDecimal(o.get("executedQty").getAsString()))
                .avgPrice(o.has("avgPrice") ? new BigDecimal(o.get("avgPrice").getAsString()) : null)
                .stopPrice(new BigDecimal(o.get("stopPrice").getAsString()))
                .closePosition(o.has("closePosition") && o.get("closePosition").getAsBoolean())
                .updateTimeMs(o.get("ts").getAsLong()).build();
    }

    /** 1 stop c3s- closePosition, stop / gia vao trong [1 - dist - tol, 1 - MIN + tol]. */
    private void assertStop(String sym, double entryPx, double dist) {
        List<OrderInfo> s = mock.openStops(sym);
        assertEquals("so stop " + sym, 1, s.size());
        assertTrue(s.get(0).isClosePosition());
        double r = s.get(0).getStopPrice().doubleValue() / entryPx;
        assertTrue("stop/entry=" + r, r >= 1d - dist - CanaryLimits.STOP_ROUND_TOL && r <= 1d - CanaryLimits.MIN_STOP_DIST + 1e-9);
    }

    // ------------------------------------------------------------------ T1
    /**
     * T1: ACK FILLED khong avgPrice, stream {@code ap} den 300 ms sau => leg DUOC GIU, gia = ap, CO stop, K1 DAT.
     */
    @Test
    public void t1AckFilledWithoutPriceStreamAp300msLaterKeepsLegAndPlacesStop() throws Exception {
        mock.exchangeInfo = info(MAIN, AUX);
        mock.setPrice(MAIN, new BigDecimal("1310.36"));
        mock.setPrice(AUX, new BigDecimal("100"));
        mock.ackWithoutAvgPrice = true;
        mock.holdFillEvents = true;
        final long t0 = now.get();
        hook = t -> {
            if (t - t0 >= 300L && mock.heldEventCount() > 0) mock.flushEvents();
        };
        CanaryEngine e = engine(cfg());
        sess(e, MAIN, AUX);
        CanaryEngine.Result r = e.step("K1");
        hook = t -> { };
        try {
            ok(r);
            String cid = legCid(e, "K1");
            assertEquals("qty 20 USDT @1310.36 (buoc 0.001)", 0, new BigDecimal("0.015").compareTo(mock.position(MAIN)));
            LiveBookC3.LegView lv = e.book().leg(cid).orElse(null);
            assertNotNull("leg phai con (bug K4 cu: bi xoa cum)", lv);
            assertEquals(LiveBookC3.LegState.CONFIRMED, lv.state);
            assertEquals("gia = ap cua stream", 1310.36, lv.avgPx, 1e-9);
            assertFalse("gia that => khong phai gia tam", lv.pxProvisional);
            assertStop(MAIN, 1310.36, CanaryLimits.MAX_STOP_DIST);
            Map<String, Object> px = firstEvent(e, "PX_RESOLVED", cid);
            assertNotNull("phai co PX_RESOLVED tu stream", px);
            assertEquals("STREAM_AP", px.get("source"));
            assertTrue("khong duoc ghi gia TAM", events(e, "PX_PROVISIONAL").isEmpty());
        } finally {
            e.close();
        }
    }


    // ------------------------------------------------------------------ T2
    /** T2: ACK khong gia, KHONG co stream (stream den rat tre), queryOrder co avgPrice => gia tu queryOrder. */
    @Test
    public void t2AckWithoutPriceQueryOrderProvidesPrice() throws Exception {
        mock.exchangeInfo = info(MAIN, AUX);
        mock.setPrice(MAIN, new BigDecimal("1310.36"));
        mock.setPrice(AUX, new BigDecimal("100"));
        mock.ackWithoutAvgPrice = true;
        mock.holdFillEvents = true;   // stream KHONG den trong ngan sach giai gia
        mock.queryOrderWithoutAvgPrice = false;
        final long t0 = now.get();
        hook = t -> {
            if (t - t0 >= 1_500L && mock.heldEventCount() > 0) mock.flushEvents();   // FILLED den <= 2 s (tieu chi K1)
        };
        CanaryEngine e = engine(cfg());
        sess(e, MAIN, AUX);
        CanaryEngine.Result r = e.step("K1");
        hook = t -> { };
        try {
            ok(r);
            String cid = legCid(e, "K1");
            LiveBookC3.LegView lv = e.book().leg(cid).orElse(null);
            assertNotNull(lv);
            assertEquals(LiveBookC3.LegState.CONFIRMED, lv.state);
            assertEquals(1310.36, lv.avgPx, 1e-9);
            assertFalse(lv.pxProvisional);
            assertStop(MAIN, 1310.36, CanaryLimits.MAX_STOP_DIST);
            Map<String, Object> px = firstEvent(e, "PX_RESOLVED", cid);
            assertNotNull(px);
            assertEquals("QUERY", px.get("source"));
            assertTrue(mock.calls("queryOrder") >= 1);
            assertTrue("khong duoc ghi gia TAM", events(e, "PX_PROVISIONAL").isEmpty());
        } finally {
            e.close();
        }
    }

    // ------------------------------------------------------------------ T3
    /**
     * T3: khong nguon nao co gia => PX_PROVISIONAL tai mark, CO stop, sau do queryOrder tra gia that =>
     * PX_CORRECTED + ledger (avg_entry/realized) tinh lai theo gia that.
     */
    @Test
    public void t3NoPriceAnywhereProvisionalAtMarkThenQueryOrderCorrects() throws Exception {
        mock.exchangeInfo = info(MAIN, AUX);
        mock.setPrice(MAIN, new BigDecimal("1310.00"));   // gia khop THAT
        mock.setPrice(AUX, new BigDecimal("100"));
        mock.ackWithoutAvgPrice = true;
        mock.holdFillEvents = true;          // stream khong den trong luc mo
        mock.queryOrderWithoutAvgPrice = true;
        mock.userTradesEmpty = true;
        CanaryEngine e = engine(cfg());
        sess(e, MAIN, AUX);
        e.build();
        e.loadRules();
        final String cid = C3LiveCids.entry(MAIN, Math.floorDiv(now.get(), 60_000L), 0);
        final long sendAt = now.get();
        final boolean[] filledEv = {false};
        hook = t -> {
            if (t - sendAt >= 100L) mock.setPrice(MAIN, new BigDecimal("1305.00"));   // mark tut sau khi khop
            if (t - sendAt >= 300L && !filledEv[0]) {   // FILLED nhung KHONG co gia (ap=0, L=0)
                filledEv[0] = true;
                mock.emitRaw("{\"e\":\"ORDER_TRADE_UPDATE\",\"T\":" + t + ",\"E\":" + t + ",\"o\":{\"s\":\"" + MAIN
                        + "\",\"c\":\"" + cid + "\",\"S\":\"BUY\",\"o\":\"MARKET\",\"f\":\"GTC\",\"q\":\"0.015\","
                        + "\"p\":\"0\",\"ap\":\"0\",\"sp\":\"0\",\"x\":\"TRADE\",\"X\":\"FILLED\",\"i\":" + ORDER_ID_K4
                        + ",\"l\":\"0.015\",\"z\":\"0.015\",\"L\":\"0\",\"n\":\"0.0098277\",\"N\":\"USDT\",\"T\":" + t
                        + ",\"R\":false,\"ot\":\"MARKET\",\"cp\":false,\"rp\":\"0\"}}");
            }
        };
        try {
            CanaryEngine.Leg l = e.openLeg(MAIN);
            hook = t -> { };
            assertTrue("leg phai CONFIRMED du khong co gia that: " + l.error, l.confirmed);
            assertEquals("gia TAM = mark luc xac nhan", 1305.00, l.avg, 1e-9);
            LiveBookC3.LegView lv = e.book().leg(cid).orElse(null);
            assertNotNull(lv);
            assertEquals(LiveBookC3.LegState.CONFIRMED, lv.state);
            assertEquals(0, new BigDecimal("0.015").compareTo(lv.execQty));
            assertTrue("phai co co pxProvisional", lv.pxProvisional);
            assertEquals(1305.00, lv.avgPx, 1e-9);
            Map<String, Object> prov = firstEvent(e, "PX_PROVISIONAL", cid);
            assertNotNull("phai co journal PX_PROVISIONAL", prov);
            assertEquals(1305.00, ((Number) prov.get("px")).doubleValue(), 1e-9);
            // stop bao ve dat theo gia XAU nhat (max(mark,last,entry san)) = 1310.00
            assertStop(MAIN, 1310.00, CanaryLimits.MAX_STOP_DIST);

            // gia that den tu queryOrder (sau khi stream khong bao gio co gia)
            mock.queryOrderWithoutAvgPrice = false;
            now.addAndGet(6_000L);
            mock.now = now.get();
            assertEquals("phai sua duoc 1 leg", 1, e.executor.correctProvisional());
            LiveBookC3.LegView fixed = e.book().leg(cid).orElse(null);
            assertNotNull(fixed);
            assertFalse(fixed.pxProvisional);
            assertEquals("gia that 1310.00 (khong phai tam 1305)", 1310.00, fixed.avgPx, 1e-9);
            Map<String, Object> corr = firstEvent(e, "PX_CORRECTED", cid);
            assertNotNull("phai co journal PX_CORRECTED", corr);
            assertEquals("gia that 1310.00", 1310.00, ((Number) corr.get("px")).doubleValue(), 1e-9);
            assertEquals("QUERY", corr.get("source"));

            // dong vi the => dong ledger phai dung gia THAT (avg_entry 1310, PnL theo gia that)
            mock.holdFillEvents = false;
            mock.flushEvents();
            long w = e.closeCluster(MAIN, "TIME_STOP_168H");
            assertTrue("cum phai dong", w >= 0);
            String led = lastLedgerLine(e, MAIN);
            assertNotNull("phai co dong ledger", led);
            String[] f = led.split(",");
            assertEquals("qty", 0, new BigDecimal("0.015").compareTo(new BigDecimal(f[3])));
            assertEquals("avg_entry phai la gia THAT (hieu chinh), khong phai gia tam", 1310.00,
                    Double.parseDouble(f[4]), 1e-9);
            assertEquals("exit_avg", 1305.00, Double.parseDouble(f[6]), 1e-9);
            assertEquals("realized PnL theo gia that: (1305-1310)*0.015", -0.075d, Double.parseDouble(f[7]), 1e-9);
        } finally {
            e.close();
        }
    }

    private String lastLedgerLine(CanaryEngine e, String sym) throws Exception {
        File f = new File(dir, LiveBookC3.LEDGER_NAME);
        if (!f.exists()) return null;
        List<String> ls = Files.readAllLines(f.toPath(), StandardCharsets.UTF_8);
        for (int i = ls.size() - 1; i >= 0; i--) if (ls.get(i).startsWith(sym + ",")) return ls.get(i);
        return null;
    }

    // ------------------------------------------------------------------ T5
    /** T5: ACK mat (MO-5 tiem timeout) => hanh vi cu KHONG doi: 1 lan gui, queryOrder theo cid, K1 DAT. */
    @Test
    public void t5AckLostWithMo5InjectionUnchanged() throws Exception {
        mock.exchangeInfo = info(MAIN, AUX);
        mock.setPrice(MAIN, new BigDecimal("1310.36"));
        mock.setPrice(AUX, new BigDecimal("100"));
        CanaryEngine.Config c = cfg();
        c.injectTimeout = true;
        CanaryEngine e = engine(c);
        sess(e, MAIN, AUX);
        CanaryEngine.Result r = e.step("K1");
        try {
            ok(r);
            String cid = legCid(e, "K1");
            assertEquals("chi 1 lan gui", 1, mock.calls("newMarketOrder"));
            assertTrue("phai tra san theo cid", mock.calls("queryOrder") >= 1);
            assertTrue(e.state().injectTimeoutUsed);
            assertEquals(0, new BigDecimal("0.015").compareTo(mock.position(MAIN)));
            LiveBookC3.LegView lv = e.book().leg(cid).orElse(null);
            assertNotNull(lv);
            assertEquals(LiveBookC3.LegState.CONFIRMED, lv.state);
            assertEquals(1310.36, lv.avgPx, 1e-9);
            assertStop(MAIN, 1310.36, CanaryLimits.MAX_STOP_DIST);
        } finally {
            e.close();
        }
    }

    // ------------------------------------------------------------------ T7
    /**
     * T7: tai hien NGUYEN VAN chuoi that 10-28 (ACK khong avgPrice + ORDER_TRADE_UPDATE ap=1310.36) voi cid/phut that
     * => buoc K4 mo duoc leg (truoc day TRUOT "leg bi huy (khong khop)") va ca K4 DAT.
     */
    @Test
    public void t7RealK4Sequence20261028OpensLegThenK4Passes() throws Exception {
        now.set(1_793_154_000_000L);
        mock.now = now.get();
        mock.exchangeInfo = info("ZECUSDT", "SOLUSDT");
        mock.setPrice("ZECUSDT", new BigDecimal("1310.36"));
        mock.setPrice("SOLUSDT", new BigDecimal("150.00"));
        mock.ackTemplate = ackFromFixture(REAL_ACK_20261028, CID_K4);   // [3j] ACK y nguyen dong journal that
        mock.holdFillEvents = true;                       // stream that duoc phat rieng ben duoi
        final long k4Start = now.get();
        final boolean[] streamed = {false};
        final boolean[] fired = {false};
        hook = t -> {
            if (!streamed[0] && t - K4_SEND_MS >= 30L) {   // that: ACK .682, stream .712 (~30 ms)
                streamed[0] = true;
                mock.emitRaw(REAL_WS_FILLED_20261028);
            }
            if (!fired[0] && t - k4Start > 120_000L && !mock.openStops("ZECUSDT").isEmpty()) {
                fired[0] = true;
                mock.holdFillEvents = false;               // tu day su kien that (stop kich) phai den duoc
                mock.triggerStops("ZECUSDT", new BigDecimal("1308.00"));
            }
        };
        CanaryEngine e = engine(cfg());
        sess(e, "ZECUSDT", "SOLUSDT");
        CanaryEngine.Result r = e.step("K4");
        hook = t -> { };
        try {
            ok(r);
            assertTrue("stop phai kich", fired[0]);
            assertEquals("vi the da dong", 0, mock.position("ZECUSDT").signum());
            assertTrue(mock.openStops(null).isEmpty());
            assertTrue("cum da dong", !e.book().isHolding("ZECUSDT"));
            // ACK tai hien dung fixture: cid + orderId that, KHONG co avgPrice
            Map<String, Object> ack = null;
            for (Map<String, Object> m : e.journal().entries()) {
                if ("newMarketOrder:BUY".equals(m.get("api")) && CID_K4.equals(m.get("cid"))) ack = m;
            }
            assertNotNull("phai co CALL_W newMarketOrder cua fixture", ack);
            assertEquals("orderId that", ORDER_ID_K4, ((Number) ack.get("orderId")).longValue());
            assertFalse("ACK that KHONG co avgPrice", ack.containsKey("avgPrice"));
            String led = lastLedgerLine(e, "ZECUSDT");
            assertNotNull(led);
            assertTrue(led, led.contains("TRAILING_STOP"));
            String[] f = led.split(",");
            assertEquals("qty that cua fixture", 0, new BigDecimal("0.015").compareTo(new BigDecimal(f[3])));
            assertEquals("gia vao that 1310.36", 1310.36, Double.parseDouble(f[4]), 1e-9);
            assertTrue("gia vao phai la 1310.36 (tu stream ap), khong phai gia tam",
                    events(e, "PX_PROVISIONAL").isEmpty());
            Map<String, Object> done = firstEvent(e, "LEG_DONE", CID_K4);
            assertNotNull(done);
            assertEquals(Boolean.TRUE, done.get("confirmed"));
            assertEquals(1310.36, ((Number) done.get("avg")).doubleValue(), 1e-9);
        } finally {
            e.close();
        }
    }
}
