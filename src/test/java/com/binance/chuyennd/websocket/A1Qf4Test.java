package com.binance.chuyennd.websocket;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static com.binance.chuyennd.websocket.KlineIngestCoreTest.*;
import static org.junit.Assert.*;

/** A1 audit QF4 (chi a1_wt4, KHONG commit). */
public class A1Qf4Test {
    ExecutorService pool;
    FakeStore store;
    FakeRest rest;
    KlineIngestCore core;
    List<String> uni = new ArrayList<>();

    @Before
    public void setUp() {
        pool = Executors.newFixedThreadPool(8);
        store = new FakeStore();
        rest = new FakeRest();
        core = new KlineIngestCore(store, rest, pool, 1, 0L, AGE, 5_000L);
        for (int i = 0; i < 125; i++) {
            String s = String.format("S%03dUSDT", i);
            uni.add(s);
            rest.on(s, bars(bar(M, UNSETTLED), bar(M + MIN, OPEN)));
        }
    }

    @After
    public void tearDown() {
        pool.shutdownNow();
    }

    KlinePassController ctl(int room) {
        return new KlinePassController(core, new SettlePlanner(0, 30), () -> room, () -> M + MIN + 2_000L,
                60, 3, M - 10 * MIN, 20_000L, 600);
    }

    /** Ket noi rot SAU pass +2 s (giua +2 va +4 s): luat a chi xet 1 lan o +2 s => +4 s bo qua (>60) => ca ket noi thieu luc chot. */
    @Test
    public void q4a_dropBetween2sAnd4s() {
        KlinePassController c = ctl(200);
        KlinePassController.GapOut g = c.gap(M, uni, Collections.<String>emptySet(), null, true);   // +2 s: ket noi con song
        assertEquals(0, g.lost);
        KlinePassController.EarlyOut e = c.early(M, uni, true);                                      // +4 s: 125 thieu
        System.out.println("A1-Q4a rot giua +2..+4 s: need=" + e.need + " restSkipped=" + e.restSkipped + " thieu_luc_chot=" + e.thieuLucChot);
        assertTrue(e.restSkipped);
        assertEquals(125, e.thieuLucChot);
    }

    /** Doi chung: rot truoc +2 s (luat a) => 125/125 REST, thieu_luc_chot 0. */
    @Test
    public void q4b_dropBefore2s() {
        KlinePassController c = ctl(200);
        KlinePassController.GapOut g = c.gap(M, uni, new HashSet<>(uni), null, true);
        assertEquals(125, g.closed);
        KlinePassController.EarlyOut e = c.early(M, uni, true);
        assertEquals(0, e.thieuLucChot);
    }

    /** Room KLINE con 40 (vd vua co pass bu lon) + 1 ket noi rot => 85 thieu luc chot; uu tien quote volume. */
    @Test
    public void q4c_lowRoomPriority() {
        KlinePassController c = ctl(40);
        KlinePassController.GapOut g = c.gap(M, uni, new HashSet<>(uni), s -> Integer.parseInt(s.substring(1, 4)), true);
        assertEquals(40, g.requested);
        assertTrue("uu tien volume cao nhat (S124 truoc)", store.get(M, "S124") != null && store.get(M, "S000") == null);
        KlinePassController.EarlyOut e = c.early(M, uni, true);
        System.out.println("A1-Q4c room 40: rest=" + g.closed + " thieu_luc_chot=" + e.thieuLucChot);
        assertEquals(85, e.thieuLucChot);
    }

    /** Xoay chu dong (pending -> ws) KHONG doi openedAtMs/lastDownMs => khong bao nham mat WS. */
    @Test
    public void q4d_rotationNotAGap() {
        long since = M + MIN - 1_000L;
        assertFalse(KlineWsClient.hadGapSince(true, 0L, since - 20 * 3_600_000L, since));
        assertFalse(KlineWsClient.silentNow(125, M + MIN + 1_000L, M + MIN + 2_000L));
    }
}
