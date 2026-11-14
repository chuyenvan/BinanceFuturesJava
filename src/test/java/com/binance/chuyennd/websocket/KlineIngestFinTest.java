package com.binance.chuyennd.websocket;

import com.binance.chuyennd.aerospike.MinuteFin;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static com.binance.chuyennd.websocket.KlineIngestCoreTest.*;
import static org.junit.Assert.*;

/**
 * [FIN 2026-11-14, phuong an A] Bin fin do KlineIngestCore ghi: chi nen DA CHOT (WS final / REST settle) vao fin; REST som va
 * ban nan khong vao; fin lon dan khi WS final ve muon; settle "same" danh dau; phut 0 WS final duoc dong dau {} (record da co).
 * Store gia mo phong DUNG luat writeMinuteBatchFin (MinuteFin.merge, nguyen tu data+fin).
 */
public class KlineIngestFinTest {

    /** Store gia: data + fin nhu record Aerospike (merge theo symbol; fin theo MinuteFin.merge). */
    static final class FinStore implements KlineIngestCore.MinuteStore {
        final Map<Long, Map<String, KlineObjectOptimized>> db = new ConcurrentHashMap<>();
        final Map<Long, Set<String>> fin = new ConcurrentHashMap<>();

        public Map<String, KlineObjectOptimized> read(long minute) {
            return new HashMap<>(db.getOrDefault(minute, Collections.<String, KlineObjectOptimized>emptyMap()));
        }

        /** ban nan / ghi cu: chi bin data (nhu writeMinuteBatch). */
        public void write(long minute, Map<String, KlineObjectOptimized> c) {
            db.computeIfAbsent(minute, k -> new ConcurrentHashMap<>()).putAll(c);
        }

        public void writeFinal(long minute, Map<String, KlineObjectOptimized> c, Set<String> finalSyms) {
            boolean exists = db.containsKey(minute);
            if (!exists && c.isEmpty()) return;
            Map<String, KlineObjectOptimized> d = db.computeIfAbsent(minute, k -> new ConcurrentHashMap<>());
            d.putAll(c);
            fin.put(minute, MinuteFin.merge(fin.get(minute), c.isEmpty() ? null : c.keySet(), finalSyms, d.keySet()));
        }

        Set<String> finOf(long m) {
            return fin.get(m);
        }
    }

    static Set<String> set(String... s) {
        return new TreeSet<>(Arrays.asList(s));
    }

    FinStore store;
    FakeRest rest;
    ExecutorService pool;
    KlineIngestCore core;

    @Before
    public void setUp() {
        store = new FinStore();
        rest = new FakeRest();
        pool = Executors.newFixedThreadPool(4);
        core = new KlineIngestCore(store, rest, pool, 2, 0L, AGE, 5_000L);
    }

    @After
    public void tearDown() {
        pool.shutdownNow();
    }

    /** Ban nan cua phut M (ticker loop truoc khi dong) cho 3 symbol. */
    private void nan() {
        Map<String, KlineObjectOptimized> n = new HashMap<>();
        n.put("BTC", UNSETTLED);
        n.put("ETH", UNSETTLED);
        n.put("SOL", UNSETTLED);
        assertTrue(core.writeOpenMinute(M, n));
        assertNull("ban nan khong tao fin", store.finOf(M));
    }

    @Test
    public void wsFinalAtFlushGoesToFin_restEarlyDoesNot_lateWsGrowsFin() {
        nan();
        core.onWsFinal("BTCUSDT", M, FINAL);
        core.flushWsFinals(M);
        assertEquals(set("BTC"), store.finOf(M));
        // REST som cho ETH (co the chua settle) => ghi data nhung KHONG vao fin
        rest.on("ETHUSDT", bars(bar(M, UNSETTLED), bar(M + MIN, OPEN)));
        core.earlyRest(M, Collections.singletonList("ETHUSDT"));
        assertEquals(set("BTC"), store.finOf(M));
        // WS final ETH, SOL toi muon (+10 s) => fin lon dan, data = ban final
        core.onWsFinal("ETHUSDT", M, FINAL);
        core.onWsFinal("SOLUSDT", M, FINAL);
        assertEquals(2, core.flushLateFinals());
        assertEquals(set("BTC", "ETH", "SOL"), store.finOf(M));
        assertTrue(KlineIngestCore.sameBits(FINAL, store.read(M).get("ETH")));
        // ban nan tre qua ranh phut bi chan (phut da chot) => fin khong doi
        assertFalse(core.writeOpenMinute(M, Collections.singletonMap("BTC", UNSETTLED)));
        assertEquals(set("BTC", "ETH", "SOL"), store.finOf(M));
    }

    @Test
    public void settleMarksFinal_diffSameAndFilled() {
        nan();
        core.onWsFinal("BTCUSDT", M, FINAL);
        core.flushWsFinals(M);
        store.db.get(M).put("SOL", FINAL);   // SOL: store da dung ban settle (same)
        rest.on("ETHUSDT", bars(bar(M, FINAL)));
        rest.on("SOLUSDT", bars(bar(M, FINAL)));
        rest.on("XRPUSDT", bars(bar(M, FINAL)));   // XRP chua co trong store (filled)
        KlineIngestCore.SettleResult r = core.settle(M + MIN + 30_000L, Arrays.asList("ETHUSDT", "SOLUSDT", "XRPUSDT"), 3);
        assertEquals(1, r.rewrittenDiff);
        assertEquals(1, r.same);
        assertEquals(1, r.filledMissing);
        assertEquals(set("BTC", "ETH", "SOL", "XRP"), store.finOf(M));
    }

    @Test
    public void immatureSettleDoesNotMark() {
        nan();
        rest.on("ETHUSDT", bars(bar(M, FINAL)));
        core.settle(M + MIN + 5_000L, Collections.singletonList("ETHUSDT"), 3);   // 5 s < 20 s
        assertNull(store.finOf(M));
    }

    @Test
    public void zeroWsFinalStampsEmptyFin_onlyIfRecordExists() {
        assertEquals(0, core.flushWsFinals(M - MIN));   // khong co record => khong tao
        assertNull(store.finOf(M - MIN));
        assertFalse(store.db.containsKey(M - MIN));
        nan();
        assertEquals(0, core.flushWsFinals(M));
        assertNotNull("dong dau {} de live phan biet ingestor cu", store.finOf(M));
        assertTrue(store.finOf(M).isEmpty());
        assertEquals("dong dau khong doi data", 3, store.read(M).size());
    }
}
