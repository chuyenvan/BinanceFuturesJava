package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

/** [KFIX-B] LiveTickerWindow doc lai 3 phut da nap + thuoc LiveKlineAudit (reader gia, khong Aerospike). */
public class LiveTickerWindowRereadTest {
    static final long MIN = 60_000L;
    static final long E0 = 1_760_000_000_000L / MIN * MIN;

    /** Kho phut gia: minute -> (symbol -> nen); moi lan doc tra object MOI (nhu parse lai). */
    static final class FakeReader implements LiveTickerWindow.MinuteReader {
        final Map<Long, Map<String, KlineObjectSimple>> db = new HashMap<>();
        final AtomicInteger minutesRead = new AtomicInteger();

        public TreeMap<Long, Map<String, KlineObjectSimple>> read(long from, int count) {
            TreeMap<Long, Map<String, KlineObjectSimple>> out = new TreeMap<>();
            for (int i = 0; i < count; i++) {
                long m = from + i * MIN;
                Map<String, KlineObjectSimple> src = db.get(m);
                if (src == null) continue;
                Map<String, KlineObjectSimple> cp = new HashMap<>();
                for (Map.Entry<String, KlineObjectSimple> e : src.entrySet()) cp.put(e.getKey(), copy(e.getValue()));
                out.put(m, cp);
                minutesRead.incrementAndGet();
            }
            return out;
        }

        void put(long m, String sym, float close, float q) {
            db.computeIfAbsent(m, k -> new HashMap<>()).put(sym, k(m, close, q));
        }
    }

    static KlineObjectSimple k(long t, float close, float q) {
        KlineObjectSimple x = new KlineObjectSimple();
        x.startTime = t;
        x.priceOpen = 100f;
        x.maxPrice = Math.max(100f, close);
        x.minPrice = Math.min(100f, close);
        x.priceClose = close;
        x.totalUsdt = q;
        return x;
    }

    static KlineObjectSimple copy(KlineObjectSimple a) {
        KlineObjectSimple x = k(a.startTime, a.priceClose, a.totalUsdt);
        x.priceOpen = a.priceOpen;
        x.maxPrice = a.maxPrice;
        x.minPrice = a.minPrice;
        return x;
    }

    /** now cua tick quyet dinh phut M (giay 6 cua M+1). */
    static long tickFor(long m) {
        return m + MIN + 6_000L;
    }

    static float lastClose(Map<String, List<KlineObjectSimple>> out, String sym, long m) {
        for (KlineObjectSimple x : out.get(sym)) if (x.startTime == m) return x.priceClose;
        return Float.NaN;
    }

    /** Du lieu nen cho moi phut [E0-20', E0+20'] voi 2 symbol, gia tri final. */
    static FakeReader seeded() {
        FakeReader r = new FakeReader();
        for (long m = E0 - 20 * MIN; m <= E0 + 20 * MIN; m += MIN) {
            r.put(m, "BTCUSDT", 101f, 1000f);
            r.put(m, "ETHUSDT", 99f, 500f);
        }
        return r;
    }

    @Test
    public void rereadOverwritesUnsettledAndMeasuresDecisionCorrectness() {
        FakeReader r = seeded();
        LiveTickerWindow w = new LiveTickerWindow(r, 3);
        w.read(tickFor(E0), 10);                                   // full reload, quyet dinh phut E0
        long m = E0 + MIN;
        r.put(m, "BTCUSDT", 100.5f, 900f);                         // nen M chua chot luc quyet dinh
        Map<String, List<KlineObjectSimple>> o1 = w.read(tickFor(m), 10);
        assertEquals(100.5f, lastClose(o1, "BTCUSDT", m), 0f);
        w.audit().markTopK("BTCUSDT");
        w.audit().markPass("BTCUSDT");
        w.audit().markTopK("ETHUSDT");
        r.put(m, "BTCUSDT", 101f, 1000f);                          // ingest chot (WS/settle)
        Map<String, List<KlineObjectSimple>> o2 = w.read(tickFor(m + MIN), 10);
        assertEquals(101f, lastClose(o2, "BTCUSDT", m), 0f);       // cache da ghi de bang ban chot
        w.read(tickFor(m + 2 * MIN), 10);
        assertTrue(w.audit().tracking(m));                         // van trong cua so doc lai
        w.read(tickFor(m + 3 * MIN), 10);                          // M roi cua so => chot thuoc
        assertFalse(w.audit().tracking(m));
        String s = w.audit().statsLine();
        assertTrue(s, s.contains("cum{decided_on_unsettled=1/"));
        assertTrue(s, s.contains("topK 1/2 correct=50.000%"));
        assertTrue(s, s.contains("pass 1/1 correct=0.000%"));
        assertTrue(s, s.contains("reread_overwritten=1"));
    }

    @Test
    public void rereadOffKeepsLegacyBehaviour() {
        FakeReader r = seeded();
        LiveTickerWindow w = new LiveTickerWindow(r, 0);
        w.read(tickFor(E0), 10);
        long m = E0 + MIN;
        r.put(m, "BTCUSDT", 100.5f, 900f);
        w.read(tickFor(m), 10);
        r.put(m, "BTCUSDT", 101f, 1000f);
        int before = r.minutesRead.get();
        Map<String, List<KlineObjectSimple>> o = w.read(tickFor(m + MIN), 10);
        assertEquals(1, r.minutesRead.get() - before);             // chi doc phut moi
        assertEquals(100.5f, lastClose(o, "BTCUSDT", m), 0f);      // giu ban cu nhu truoc KFIX
    }

    @Test
    public void fifteenMinuteCadenceStillRereadsAndFinalizes() {
        FakeReader r = seeded();
        LiveTickerWindow w = new LiveTickerWindow(r, 3);
        long m = E0 - 15 * MIN;
        r.put(m, "ETHUSDT", 98.5f, 400f);                          // phut quyet dinh chua chot
        w.read(tickFor(m), 60);
        w.audit().markPass("ETHUSDT");
        r.put(m, "ETHUSDT", 99f, 500f);
        Map<String, List<KlineObjectSimple>> o = w.read(tickFor(m + 15 * MIN), 60);   // tick 15' sau
        assertEquals(99f, lastClose(o, "ETHUSDT", m), 0f);         // doc lai 3 phut da nap truoc do (gom m)
        assertFalse(w.audit().tracking(m));                        // m roi cua so doc lai => da chot
        assertTrue(w.audit().statsLine().contains("pass 1/1 correct=0.000%"));
    }

    @Test
    public void auditSkipsMissingSymbolAndCountsAll() {
        LiveKlineAudit a = new LiveKlineAudit();
        Map<String, KlineObjectSimple> d = new HashMap<>();
        d.put("A", k(E0, 1f, 1f));
        d.put("B", k(E0, 2f, 2f));
        d.put("C", k(E0, 3f, 3f));
        a.onDecisionRead(E0, d);
        a.markTopK("A");
        Map<String, KlineObjectSimple> latest = new HashMap<>();
        latest.put("A", k(E0, 1f, 1.5f));                         // Q doi => quyet dinh tren nen chua chot
        latest.put("B", k(E0, 2f, 2f));                           // giu nguyen; C thieu => bo qua
        assertEquals(1, a.finalizeMinute(E0, latest));
        String s = a.statsLine();
        assertTrue(s, s.contains("win{minutes=1 decided_on_unsettled=1/2 correct=50.000%"));
        assertTrue(s, s.contains("topK 1/1"));
        assertTrue(s, s.contains("pass 0/0 correct=n/a"));
        assertTrue(a.statsLine().contains("win{minutes=0 decided_on_unsettled=0/0"));   // cua so reset
        assertTrue(LiveKlineAudit.same(k(E0, 1f, 1f), k(E0, 1f, 1f)));
        assertFalse(LiveKlineAudit.same(k(E0, 1f, 1f), null));
    }
}
