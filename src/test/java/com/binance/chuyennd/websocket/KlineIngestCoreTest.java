package com.binance.chuyennd.websocket;

import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

/** [KFIX] Logic chot/ghi lai nen 1m (KlineIngestCore) voi REST/WS gia lap. */
public class KlineIngestCoreTest {
    static final long MIN = 60_000L;
    static final long M = 1_760_000_000_000L / MIN * MIN;   // phut vua dong (openTime)
    static final long AGE = 20_000L;

    /** Store gia: merge theo symbol nhu writeMinuteBatch, dem so lan ghi. */
    static final class FakeStore implements KlineIngestCore.MinuteStore {
        final Map<Long, Map<String, KlineObjectOptimized>> db = new ConcurrentHashMap<>();
        final AtomicInteger writes = new AtomicInteger();

        public Map<String, KlineObjectOptimized> read(long minute) {
            return new HashMap<>(db.getOrDefault(minute, Collections.emptyMap()));
        }

        public void write(long minute, Map<String, KlineObjectOptimized> c) {
            writes.incrementAndGet();
            db.computeIfAbsent(minute, k -> new ConcurrentHashMap<>()).putAll(c);
        }

        KlineObjectOptimized get(long minute, String s) {
            Map<String, KlineObjectOptimized> m = db.get(minute);
            return m == null ? null : m.get(s);
        }
    }

    /** REST gia: hang doi phan hoi theo symbol (List<Bar> hoac Exception); het hang ⇒ lap phan hoi cuoi. */
    static final class FakeRest implements KlineIngestCore.RestFetcher {
        final Map<String, Deque<Object>> q = new ConcurrentHashMap<>();
        final AtomicInteger calls = new AtomicInteger();

        FakeRest on(String sym, Object... resp) {
            q.computeIfAbsent(sym, k -> new ArrayDeque<>()).addAll(Arrays.asList(resp));
            return this;
        }

        @SuppressWarnings("unchecked")
        public List<KlineIngestCore.Bar> fetch(String symbol, int limit) throws Exception {
            calls.incrementAndGet();
            Deque<Object> d = q.get(symbol);
            if (d == null || d.isEmpty()) throw new IllegalStateException("no script for " + symbol);
            Object o = d.size() > 1 ? d.pollFirst() : d.peekFirst();
            if (o instanceof Exception) throw (Exception) o;
            return (List<KlineIngestCore.Bar>) o;
        }
    }

    static KlineObjectOptimized k(float o, float h, float l, float c, float q) {
        return KlineObjectOptimized.newBuilder().setPriceOpen(o).setMaxPrice(h).setMinPrice(l).setPriceClose(c).setTotalUsdt(q).build();
    }

    static KlineIngestCore.Bar bar(long t, KlineObjectOptimized k) {
        return new KlineIngestCore.Bar(t, k);
    }

    static List<KlineIngestCore.Bar> bars(KlineIngestCore.Bar... b) {
        return new ArrayList<>(Arrays.asList(b));
    }

    // nen M chua settle (thieu trade cuoi phut: close truoc trade cuoi, H cat ben trong, Q thieu) va ban final
    static final KlineObjectOptimized UNSETTLED = k(100f, 101f, 99.5f, 100.4f, 9_000f);
    static final KlineObjectOptimized FINAL = k(100f, 101.2f, 99.5f, 100.9f, 10_000f);
    static final KlineObjectOptimized PREV = k(99f, 100.1f, 98.9f, 100f, 8_000f);
    static final KlineObjectOptimized OPEN = k(100.9f, 100.9f, 100.8f, 100.85f, 120f);

    FakeStore store;
    FakeRest rest;
    ExecutorService pool;
    KlineIngestCore core;

    @Before
    public void setUp() {
        store = new FakeStore();
        rest = new FakeRest();
        pool = Executors.newFixedThreadPool(4);
        core = new KlineIngestCore(store, rest, pool, 2, 0L, AGE, 5_000L);
    }

    @After
    public void tearDown() {
        pool.shutdownNow();
    }

    @Test
    public void wsFinalFlushedAndMissingListed() {
        core.onWsFinal("BTCUSDT", M, FINAL);
        assertEquals(1, core.flushWsFinals(M));
        assertTrue(KlineIngestCore.sameBits(FINAL, store.get(M, "BTC")));
        assertEquals(Collections.singletonList("ETHUSDT"), core.missingFinals(M, Arrays.asList("BTCUSDT", "ETHUSDT")));
        assertEquals(M, core.finalizedThrough());
    }

    @Test
    public void unsettledEarlyThenSettleRewritesWithCounter() {
        rest.on("ETHUSDT", bars(bar(M, UNSETTLED), bar(M + MIN, OPEN)),
                bars(bar(M - MIN, PREV), bar(M, FINAL), bar(M + MIN, OPEN)));
        KlineIngestCore.EarlyResult e = core.earlyRest(M, Collections.singletonList("ETHUSDT"));
        assertTrue(KlineIngestCore.sameBits(UNSETTLED, store.get(M, "ETH")));
        assertTrue(KlineIngestCore.sameBits(OPEN, e.open.get("ETH")));
        assertTrue(e.failed.isEmpty());
        // pass settle o giay 30 cua M+1: M du tuoi (30s >= 20s), M+1 dang mo => khong ghi
        KlineIngestCore.SettleResult r = core.settle(M + MIN + 30_000L, Collections.singletonList("ETHUSDT"), 3);
        assertEquals(1, r.rewrittenDiff);
        assertEquals(1, r.filledMissing);           // M-1 chua co trong store
        assertEquals(1, r.immature);                // M+1
        assertEquals(Integer.valueOf(1), r.diffByMinute.get(M));
        assertTrue(KlineIngestCore.sameBits(FINAL, store.get(M, "ETH")));
        assertTrue(KlineIngestCore.sameBits(PREV, store.get(M - MIN, "ETH")));
        assertNull(store.get(M + MIN, "ETH"));
        assertTrue(core.statsLine().contains("rewritten_diff=1(+1)"));
    }

    @Test
    public void settleSameDoesNotWrite() {
        store.write(M, Collections.singletonMap("BTC", FINAL));
        int w0 = store.writes.get();
        rest.on("BTCUSDT", bars(bar(M, FINAL)));
        KlineIngestCore.SettleResult r = core.settle(M + MIN + 30_000L, Collections.singletonList("BTCUSDT"), 3);
        assertEquals(1, r.same);
        assertEquals(0, r.rewrittenDiff);
        assertEquals(w0, store.writes.get());
    }

    @Test
    public void minuteBoundaryMaturityInclusive() {
        store.write(M, Collections.singletonMap("BTC", UNSETTLED));
        rest.on("BTCUSDT", bars(bar(M, FINAL)));
        // dung bien: openTime + 1' == now - AGE => du tuoi
        KlineIngestCore.SettleResult r0 = core.settle(M + MIN + AGE - 1, Collections.singletonList("BTCUSDT"), 3);
        assertEquals(1, r0.immature);
        assertTrue(KlineIngestCore.sameBits(UNSETTLED, store.get(M, "BTC")));
        KlineIngestCore.SettleResult r1 = core.settle(M + MIN + AGE, Collections.singletonList("BTCUSDT"), 3);
        assertEquals(1, r1.rewrittenDiff);
        assertTrue(KlineIngestCore.sameBits(FINAL, store.get(M, "BTC")));
    }

    @Test
    public void restMissingElementCountsAsFailedAndWritesNothing() {
        rest.on("SOLUSDT", bars(bar(M + MIN, OPEN)));          // phan tu tra thieu nen M
        KlineIngestCore.EarlyResult e = core.earlyRest(M, Collections.singletonList("SOLUSDT"));
        assertEquals(Collections.singletonList("SOLUSDT"), e.failed);
        assertNull(store.get(M, "SOL"));
        assertTrue(core.statsLine().contains("early_failed=1"));
    }

    @Test
    public void symbolErrorRetriedFailedThenHealedNextPass() {
        rest.on("XRPUSDT", new java.io.IOException("timeout"), new java.io.IOException("timeout"),
                bars(bar(M - MIN, PREV), bar(M, FINAL)));
        KlineIngestCore.SettleResult r = core.settle(M + MIN + 30_000L, Collections.singletonList("XRPUSDT"), 3);
        assertEquals(1, r.failed);
        assertEquals(Collections.singletonList("XRPUSDT"), r.failedSymbols);
        assertEquals(2, rest.calls.get());                    // retry = 2 lan
        assertNull(store.get(M, "XRP"));
        // pass phut sau (M van nam trong limit=3) => tu lanh
        KlineIngestCore.SettleResult r2 = core.settle(M + 2 * MIN + 30_000L, Collections.singletonList("XRPUSDT"), 3);
        assertEquals(0, r2.failed);
        assertTrue(KlineIngestCore.sameBits(FINAL, store.get(M, "XRP")));
    }

    @Test
    public void retrySucceedsOnSecondAttempt() {
        rest.on("ADAUSDT", new java.io.IOException("reset"), bars(bar(M, FINAL)));
        KlineIngestCore.SettleResult r = core.settle(M + MIN + 30_000L, Collections.singletonList("ADAUSDT"), 3);
        assertEquals(0, r.failed);
        assertEquals(1, r.fetched);
        assertEquals(2, rest.calls.get());
        assertTrue(KlineIngestCore.sameBits(FINAL, store.get(M, "ADA")));
    }

    @Test
    public void openMinuteWriteBlockedOnceMinuteFinalized() {
        core.onWsFinal("BTCUSDT", M, FINAL);
        core.flushWsFinals(M);
        // vong ticker/price lo nhip qua ranh phut: ghi nen nan cua M => phai bi CHAN
        assertFalse(core.writeOpenMinute(M, Collections.singletonMap("BTC", OPEN)));
        assertTrue(KlineIngestCore.sameBits(FINAL, store.get(M, "BTC")));
        assertTrue(core.writeOpenMinute(M + MIN, Collections.singletonMap("BTC", OPEN)));
        assertTrue(core.statsLine().contains("open_write_blocked=1"));
    }

    @Test
    public void lateWsFinalOverridesEarlyRest() {
        assertEquals(0, core.flushWsFinals(M));                 // chua co WS final o giay 1.5
        rest.on("ETHUSDT", bars(bar(M, UNSETTLED), bar(M + MIN, OPEN)));
        core.earlyRest(M, core.missingFinals(M, Collections.singletonList("ETHUSDT")));
        assertTrue(KlineIngestCore.sameBits(UNSETTLED, store.get(M, "ETH")));
        core.onWsFinal("ETHUSDT", M, FINAL);                    // WS final toi muon
        assertEquals(1, core.flushLateFinals());
        assertTrue(KlineIngestCore.sameBits(FINAL, store.get(M, "ETH")));
        assertTrue(core.statsLine().contains("ws_late=1"));
    }

    @Test
    public void earlyRestNeverOverwritesSeenWsFinal() {
        core.onWsFinal("ETHUSDT", M, FINAL);
        core.flushWsFinals(M);
        rest.on("ETHUSDT", bars(bar(M, UNSETTLED), bar(M + MIN, OPEN)));
        core.earlyRest(M, Collections.singletonList("ETHUSDT"));
        assertTrue(KlineIngestCore.sameBits(FINAL, store.get(M, "ETH")));
    }

    @Test
    public void gcDropsOldState() {
        core.onWsFinal("BTCUSDT", M - 20 * MIN, FINAL);
        core.gc(M - 10 * MIN);
        assertEquals(1, core.missingFinals(M - 20 * MIN, Collections.singletonList("BTCUSDT")).size());
        assertEquals(0, core.flushLateFinals());
    }

    @Test
    public void wsParseClosedOpenAndJunk() {
        String closed = "{\"stream\":\"btcusdt@kline_1m\",\"data\":{\"e\":\"kline\",\"E\":1760000060100,\"s\":\"BTCUSDT\","
                + "\"k\":{\"t\":1760000000000,\"T\":1760000059999,\"s\":\"BTCUSDT\",\"i\":\"1m\",\"o\":\"100.0\",\"c\":\"100.9\","
                + "\"h\":\"101.2\",\"l\":\"99.5\",\"v\":\"99.5\",\"n\":42,\"x\":true,\"q\":\"10000.0\"}}}";
        KlineWsClient.KlineEvent ev = KlineWsClient.parse(closed);
        assertNotNull(ev);
        assertTrue(ev.closed);
        assertEquals("BTCUSDT", ev.symbol);
        assertEquals(1760000000000L, ev.openTime);
        assertTrue(KlineIngestCore.sameBits(FINAL, ev.k));
        assertFalse(KlineWsClient.parse(closed.replace("\"x\":true", "\"x\":false")).closed);
        assertNull(KlineWsClient.parse("{\"result\":null,\"id\":1}"));
        assertNull(KlineWsClient.parse("not json"));
    }

    @Test
    public void wsChunkRespectsStreamCap() {
        List<String> syms = new ArrayList<>();
        for (int i = 0; i < 734; i++) syms.add("S" + i + "USDT");
        List<List<String>> c = KlineWsClient.chunk(syms, 150);
        assertEquals(5, c.size());
        int n = 0;
        for (List<String> x : c) {
            assertTrue(x.size() <= 150);
            n += x.size();
        }
        assertEquals(734, n);
    }

    @Test
    public void restParseMatchesWsParse() {
        String body = "[[1760000000000,\"100.0\",\"101.2\",\"99.5\",\"100.9\",\"99.5\",1760000059999,\"10000.0\",42,\"1\",\"1\",\"0\"],"
                + "[1760000060000,\"100.9\",\"100.9\",\"100.8\",\"100.85\",\"1.2\",1760000119999,\"120.0\",3,\"1\",\"1\",\"0\"]]";
        List<KlineIngestCore.Bar> b = TickerIngestor2AerospikeNew.parseRestKlines(body);
        assertEquals(2, b.size());
        assertEquals(1760000000000L, b.get(0).openTime);
        assertTrue(KlineIngestCore.sameBits(FINAL, b.get(0).k));
        assertTrue(KlineIngestCore.sameBits(OPEN, b.get(1).k));
    }
}
