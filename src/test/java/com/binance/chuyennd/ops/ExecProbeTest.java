package com.binance.chuyennd.ops;

import org.junit.After;
import org.junit.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

/**
 * Engine {@link ExecProbe} chay DONG BO ({@code runOnce}) voi nguon so gia (khong mang) + dau ra list. Kiem: co TAT =
 * no-op, dinh dang dong khop HEADER, gom lo / tran stream / tran ket noi, hang doi day bo + dem, Collector websocket
 * voi message gia, va do tai CPU uoc tinh (parse depth20 + walk + format).
 */
public class ExecProbeTest {

    private static final Logger LOG = LoggerFactory.getLogger(ExecProbeTest.class);

    @After
    public void tearDown() {
        ExecProbe.installForTest(null);
    }

    /** Nguon so gia dem so lan goi + symbol moi lo. */
    static final class FakeSource implements ExecProbe.BookSource {
        final List<List<String>> calls = new ArrayList<>();
        final String name;
        final boolean empty;

        FakeSource(String name, boolean empty) {
            this.name = name;
            this.empty = empty;
        }

        @Override
        public Map<String, ExecProbeBook.Book> snapshot(List<String> symbols, Map<String, Double> refPx, long timeoutMs) {
            calls.add(new ArrayList<>(symbols));
            if (empty) return Collections.emptyMap();
            return new ExecProbe.MockSource(5).snapshot(symbols, refPx, timeoutMs);
        }

        @Override
        public String name() {
            return name;
        }

        @Override
        public long connects() {
            return calls.size();
        }
    }

    private static ExecProbe.Settings settings(int maxStreams, int maxConn) {
        return ExecProbe.Settings.parse("ws", null, "5", Integer.toString(maxStreams), "1000", "0", Integer.toString(maxConn));
    }

    private static int cols(String line) {
        return line.split(",", -1).length;
    }

    @Test
    public void offByDefaultIsNoOp() {
        // env test khong dat LIVE_EXEC_PROBE => TAT; hook khong tao engine, khong nem
        assertFalse(ExecProbe.on());
        ExecProbe.onPaperLeg("AAAUSDT", "BIG_DOWN", 0, 1f, 100f, 101f, 0L);
        ExecProbe.onPaperExit("AAAUSDT", "TRAILING_STOP", 1f, 100f, 99f, 1, 0L);
        assertTrue(ExecProbe.awaitIdle(10L));
    }

    @Test
    public void entryLineMatchesHeaderAndCosts() throws Exception {
        List<String> out = new ArrayList<>();
        ExecProbe.Engine e = new ExecProbe.Engine(settings(20, 30), new FakeSource("fake", false), out::add);
        ExecProbe.installForTest(e);
        assertTrue(ExecProbe.on());
        // nen: open 104, close 100 => bar_ret -3.85% => C2; qty 5 @100 = 500 USDT (mock: 1000 USDT/muc => 1 muc)
        ExecProbe.onPaperLeg("AAAUSDT", "BIG_DOWN", 0, 5f, 100f, 104f, 1_000_000L);
        assertEquals(1, e.runOnce(10L));   // 1 su kien => 1 dong (+ header lan dau)
        assertEquals(2, out.size());
        assertTrue(out.get(0).startsWith(ExecProbe.TAG + " #hdr,"));
        String[] h = ExecProbe.HEADER.split(",", -1);
        String line = out.get(1).substring(ExecProbe.TAG.length() + 1);
        String[] v = line.split(",", -1);
        assertEquals(h.length, v.length);
        Map<String, String> m = new HashMap<>();
        for (int i = 0; i < h.length; i++) m.put(h[i], v[i]);
        assertEquals("ENTRY", m.get("ev"));
        assertEquals("BUY", m.get("side"));
        assertEquals("C2", m.get("bucket"));
        assertEquals("ok", m.get("status"));
        assertEquals("1060000", m.get("t_bar_close"));
        assertEquals("500.00", m.get("notional"));
        // mock: ask1 = 100*(1+1e-4) => slip +1 bp; mid = 100 => drift 0; impact ~ +1 bp
        assertEquals(1.0d, Double.parseDouble(m.get("slip_bps")), 1e-3);
        assertEquals(0.0d, Double.parseDouble(m.get("drift_bps")), 1e-3);
        assertEquals(2.0d, Double.parseDouble(m.get("spread_bps")), 1e-3);
        assertEquals("1", m.get("walk_lvls"));
        // qty x0.25 van trong muc 1 (= slip); qty x4 = 2000 USDT => 2 muc => dat hon
        assertEquals(1.0d, Double.parseDouble(m.get("slip_x025")), 1e-3);
        assertTrue(Double.parseDouble(m.get("slip_x4")) > Double.parseDouble(m.get("slip_bps")) + 0.3);
    }

    @Test
    public void dcaAndExitAndSkip() throws Exception {
        List<String> out = new ArrayList<>();
        ExecProbe.Engine e = new ExecProbe.Engine(settings(20, 30), new FakeSource("fake", false), out::add);
        ExecProbe.installForTest(e);
        ExecProbe.onPaperLeg("AAAUSDT", "DCA_LEVEL1", 2, 1f, 50f, 50f, 0L);
        ExecProbe.onPaperLeg("BBBUSDT", "BIG_DOWN", -1, 1f, 50f, 50f, 0L);   // so khong ghi => bo
        ExecProbe.onPaperExit("CCCUSDT", "TRAILING_STOP", 30f, 100f, 98f, 3, 5L);
        e.runOnce(10L);
        assertEquals(3, out.size());
        assertTrue(out.get(1).contains(",DCA,AAAUSDT,BUY,DCA_LEVEL1,2,"));
        String ex = out.get(2);
        assertTrue(ex.contains(",EXIT,CCCUSDT,SELL,,3,TRAILING_STOP,"));
        // 30 x 100 = 3000 USDT; mock bid 1000 USDT/muc => 3 muc, ban thap hon => slip > 0
        String[] h = ExecProbe.HEADER.split(",", -1);
        String[] v = ex.substring(ExecProbe.TAG.length() + 1).split(",", -1);
        Map<String, String> m = new HashMap<>();
        for (int i = 0; i < h.length; i++) m.put(h[i], v[i]);
        assertEquals("3", m.get("walk_lvls"));
        assertTrue(Double.parseDouble(m.get("slip_bps")) > 1.0);
        assertEquals("98", m.get("trig_px"));
        assertEquals("", m.get("lat_dec_ms"));
    }

    @Test
    public void noBookAndRateCap() throws Exception {
        List<String> out = new ArrayList<>();
        FakeSource src = new FakeSource("fake", true);
        ExecProbe.Engine e = new ExecProbe.Engine(settings(20, 2), src, out::add);
        ExecProbe.installForTest(e);
        for (int i = 0; i < 3; i++) {
            ExecProbe.onPaperLeg("S" + i + "USDT", "BIG_DOWN", 0, 1f, 10f, 10f, 0L);
            e.runOnce(10L);
        }
        assertEquals(2, src.calls.size());           // lo thu 3 bi tran 2 ket noi / 5 phut
        assertTrue(out.get(1).endsWith(",no_book,fake"));
        assertTrue(out.get(3).endsWith(",rate_capped,fake"));
        assertEquals(2, e.noBook.get());
        assertEquals(1, e.rateCapped.get());
    }

    @Test
    public void batchRespectsMaxStreams() throws Exception {
        List<String> out = new ArrayList<>();
        FakeSource src = new FakeSource("fake", false);
        ExecProbe.Engine e = new ExecProbe.Engine(settings(2, 30), src, out::add);
        ExecProbe.installForTest(e);
        for (String s : Arrays.asList("AUSDT", "BUSDT", "AUSDT", "CUSDT", "DUSDT")) {
            ExecProbe.onPaperLeg(s, "BIG_DOWN", 0, 1f, 10f, 10f, 0L);
        }
        e.runOnce(10L);
        e.runOnce(10L);
        assertEquals(Arrays.asList(Arrays.asList("AUSDT", "BUSDT"), Arrays.asList("CUSDT", "DUSDT")), src.calls);
        assertEquals(1 + 5, out.size());
        assertTrue(e.idle());
    }

    @Test
    public void queueFullDropsAndCounts() {
        ExecProbe.Engine e = new ExecProbe.Engine(settings(20, 30), new FakeSource("fake", false), s -> { });
        ExecProbe.installForTest(e);
        for (int i = 0; i < ExecProbe.QUEUE_CAP + 7; i++) {
            ExecProbe.onPaperLeg("AUSDT", "BIG_DOWN", 0, 1f, 10f, 10f, 0L);
        }
        assertEquals(ExecProbe.QUEUE_CAP + 7, e.offered.get());
        assertEquals(7, e.dropped.get());
        assertTrue(e.statLine().contains("dropped=7"));
    }

    @Test
    public void settingsParse() {
        ExecProbe.Settings d = ExecProbe.Settings.parse(null, null, null, null, null, null, null);
        assertEquals("ws", d.source);
        assertEquals(20, d.depth);
        assertEquals(20, d.maxStreams);
        assertEquals(3000L, d.timeoutMs);
        assertEquals(2, d.bases.size());
        assertTrue(d.bases.get(0).startsWith("wss://fstream.binance.com/public/"));
        ExecProbe.Settings x = ExecProbe.Settings.parse("MOCK", "http://x, wss://a/b?streams=", "7", "999", "5", "abc", "0");
        assertEquals("mock", x.source);
        assertEquals(Collections.singletonList("wss://a/b?streams="), x.bases);
        assertEquals(20, x.depth);       // 7 khong hop le
        assertEquals(20, x.maxStreams);  // 999 ngoai mien
        assertEquals(3000L, x.timeoutMs);
        assertEquals(500L, x.batchMs);
        assertEquals(30, x.maxConn5m);
    }

    @Test
    public void wsUrlAndCollectorWithFakeMessages() throws Exception {
        assertEquals("wss://h/stream?streams=btcusdt@depth20@100ms/ethusdt@depth20@100ms",
                ExecProbeWsSource.url("wss://h/stream?streams=", Arrays.asList("BTCUSDT", "ETHUSDT"), 20));
        ExecProbeWsSource.Collector c = new ExecProbeWsSource.Collector(Arrays.asList("BTCUSDT", "ETHUSDT"));
        c.onText("{\"stream\":\"btcusdt@depth20@100ms\",\"data\":{\"s\":\"BTCUSDT\",\"b\":[[\"1\",\"1\"]],\"a\":[[\"2\",\"1\"]]}}", 1L);
        c.onText("{\"stream\":\"btcusdt@depth20@100ms\",\"data\":{\"s\":\"BTCUSDT\",\"b\":[[\"5\",\"1\"]],\"a\":[[\"6\",\"1\"]]}}", 2L);
        c.onText("{\"stream\":\"xrpusdt@depth20@100ms\",\"data\":{\"s\":\"XRPUSDT\",\"b\":[[\"1\",\"1\"]],\"a\":[[\"2\",\"1\"]]}}", 3L);
        assertFalse(c.await(1L));
        c.onText("{\"stream\":\"ethusdt@depth20@100ms\",\"data\":{\"s\":\"ETHUSDT\",\"b\":[[\"1\",\"1\"]],\"a\":[[\"2\",\"1\"]]}}", 4L);
        assertTrue(c.await(1L));
        assertEquals(1d, c.got.get("BTCUSDT").bestBid(), 0d);   // giu message DAU
        assertEquals(2, c.got.size());
        ExecProbeWsSource.Collector f = new ExecProbeWsSource.Collector(Collections.singletonList("BTCUSDT"));
        f.onFail("SocketTimeoutException");
        assertTrue(f.await(1L));
        assertTrue(f.got.isEmpty());
        assertEquals("SocketTimeoutException", f.failure);
    }

    /** Do tai: parse 1 message depth20 + walk + format. Chi in (SLF4J), khong assert nguong thoi gian. */
    @Test
    public void cpuCostEstimate() {
        StringBuilder sb = new StringBuilder("{\"stream\":\"ethusdt@depth20@100ms\",\"data\":{\"e\":\"depthUpdate\",\"E\":1,\"s\":\"ETHUSDT\",\"b\":[");
        for (int i = 0; i < 20; i++) sb.append(i > 0 ? "," : "").append("[\"").append(2000 - i * 0.1).append("\",\"").append(1 + i).append("\"]");
        sb.append("],\"a\":[");
        for (int i = 0; i < 20; i++) sb.append(i > 0 ? "," : "").append("[\"").append(2000.1 + i * 0.1).append("\",\"").append(1 + i).append("\"]");
        sb.append("]}}");
        String msg = sb.toString();
        ExecProbe.Event ev = new ExecProbe.Event("ENTRY", "ETHUSDT", true, "BIG_DOWN", 0, "", 3.0, 2000.0, 2050.0, 0L, 70_000L, Double.NaN);
        AtomicInteger sink = new AtomicInteger();
        int n = 20_000;
        for (int i = 0; i < 2_000; i++) sink.addAndGet(ExecProbe.format(ev, ExecProbeBook.parseDepth(msg, 1L), null, "ws").length());
        long t0 = System.nanoTime();
        for (int i = 0; i < n; i++) sink.addAndGet(ExecProbe.format(ev, ExecProbeBook.parseDepth(msg, 1L), null, "ws").length());
        long ns = (System.nanoTime() - t0) / n;
        LOG.info("[EXEC-PROBE-BENCH] parse(depth20 {} byte)+walk+format = {} us/su kien (n={}, chk={})",
                msg.length(), ns / 1000.0, n, sink.get() > 0);
        assertTrue(sink.get() > 0);
    }
}
