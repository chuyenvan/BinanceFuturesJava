package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Test;

import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/** [V11] LiveTickerWindow: snapshot day du, cho du symbol (await/timeout), ghi de tai cho khi doc lai. */
public class LiveTickerWindowSettleTest {
    static final long MIN = LiveTickerWindowRereadTest.MIN;
    static final long E0 = LiveTickerWindowRereadTest.E0;

    @Test
    public void snapshotIsUnfilteredAndAwaitReturnsImmediatelyWhenComplete() {
        LiveTickerWindowRereadTest.FakeReader r = LiveTickerWindowRereadTest.seeded();
        r.put(E0, "FLATUSDT", 100f, 0f);   // nen phang khong volume: legacy loc, snapshot GIU
        LiveTickerWindow w = new LiveTickerWindow(r, 3);
        w.read(LiveTickerWindowRereadTest.tickFor(E0), 30);
        assertEquals(E0, w.lastEndMinute());
        Map<String, KlineObjectSimple> s = w.minuteSnapshot(E0);
        assertEquals(3, s.size());
        assertTrue(s.containsKey("FLATUSDT"));
        int before = r.minutesRead.get();
        long[] res = w.awaitMinuteComplete(E0, 3, 3000L, 250L, ms -> fail("khong duoc ngu"), () -> 0L);
        assertEquals(3, res[0]);
        assertEquals(0, res[1]);
        assertEquals(before, r.minutesRead.get());
    }

    @Test
    public void awaitPollsUntilLateSymbolArrives() {
        LiveTickerWindowRereadTest.FakeReader r = LiveTickerWindowRereadTest.seeded();
        LiveTickerWindow w = new LiveTickerWindow(r, 3);
        w.read(LiveTickerWindowRereadTest.tickFor(E0), 30);
        AtomicLong clock = new AtomicLong(0L);
        long[] res = w.awaitMinuteComplete(E0, 3, 3000L, 250L, ms -> {
            clock.addAndGet(ms);
            if (clock.get() >= 500L) r.put(E0, "LATEUSDT", 100f, 5f);   // toi sau 2 nhip
        }, clock::get);
        assertEquals(3, res[0]);
        assertEquals(2, res[1]);
        assertEquals(500L, res[2]);
        assertTrue(w.minuteSnapshot(E0).containsKey("LATEUSDT"));
    }

    @Test
    public void awaitTimesOutAndReportsPartial() {
        LiveTickerWindowRereadTest.FakeReader r = LiveTickerWindowRereadTest.seeded();
        LiveTickerWindow w = new LiveTickerWindow(r, 3);
        w.read(LiveTickerWindowRereadTest.tickFor(E0), 30);
        AtomicLong clock = new AtomicLong(0L);
        long[] res = w.awaitMinuteComplete(E0, 5, 1000L, 250L, clock::addAndGet, clock::get);
        assertEquals(2, res[0]);
        assertEquals(4, res[1]);
        assertEquals(1000L, res[2]);
    }

    @Test
    public void inPlaceRereadMutatesSameObjectAndAuditStillCountsUnsettled() {
        LiveTickerWindowRereadTest.FakeReader r = LiveTickerWindowRereadTest.seeded();
        LiveTickerWindow w = new LiveTickerWindow(r, 3);
        w.setInPlaceReread(true);
        Map<String, List<KlineObjectSimple>> out = w.read(LiveTickerWindowRereadTest.tickFor(E0), 30);
        KlineObjectSimple held = null;
        for (KlineObjectSimple k : out.get("BTCUSDT")) if (k.startTime == E0) held = k;   // vd ring HistoryManager giu
        assertNotNull(held);
        assertEquals(101f, held.priceClose, 0f);
        r.put(E0, "BTCUSDT", 105f, 1000f);   // settle ghi de sau quyet dinh
        for (long m = E0 + MIN; m <= E0 + 3 * MIN; m += MIN) w.read(LiveTickerWindowRereadTest.tickFor(m), 30);
        assertEquals(105f, held.priceClose, 0f);              // CUNG object da duoc sua
        assertSame(held, w.minuteSnapshot(E0).get("BTCUSDT"));
        assertEquals(1L, w.audit().unsettled[0].get());       // thuoc van bat duoc nen quyet dinh luc chua chot
    }

    @Test
    public void legacyRereadReplacesObject() {
        LiveTickerWindowRereadTest.FakeReader r = LiveTickerWindowRereadTest.seeded();
        LiveTickerWindow w = new LiveTickerWindow(r, 3);
        Map<String, List<KlineObjectSimple>> out = w.read(LiveTickerWindowRereadTest.tickFor(E0), 30);
        KlineObjectSimple held = null;
        for (KlineObjectSimple k : out.get("BTCUSDT")) if (k.startTime == E0) held = k;
        r.put(E0, "BTCUSDT", 105f, 1000f);
        w.read(LiveTickerWindowRereadTest.tickFor(E0 + MIN), 30);
        assertEquals(101f, held.priceClose, 0f);              // legacy: object cu giu nguyen
        assertEquals(105f, w.minuteSnapshot(E0).get("BTCUSDT").priceClose, 0f);
    }
}
