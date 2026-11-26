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

/** A1 audit QF4b (chi a1_wt4b, KHONG commit). */
public class A1Qf4bTest {
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

    KlinePassController ctl() {
        return new KlinePassController(core, new SettlePlanner(0, 30), () -> 200, () -> M + MIN + 4_000L,
                60, 3, M - 10 * MIN, 20_000L, 600);
    }

    /** Rot giua +2..+4 s: +4 s REST khong tran 60 => 125/125, thieu_ws=0 (MIN-1 da dong). */
    @Test
    public void b1_dropBetween2and4() {
        KlinePassController c = ctl();
        c.gap(M, uni, Collections.<String>emptySet(), null, true);
        KlinePassController.EarlyOut e = c.early(M, uni, new HashSet<>(uni), true);
        System.out.println("A1-B4b1 lostClosed=" + e.lostClosed + " thieu=" + e.thieuLucChot + " ws=" + e.thieuWs + " tre=" + e.thieuTre);
        assertEquals(125, e.lostClosed);
        assertEquals(0, e.thieuLucChot);
    }

    /** Ket noi song nhung stream cua 125 symbol mat x=true (loi phia minh, khong co dau hieu muc ket noi) => bi xep "tre" (khong gate). */
    @Test
    public void b2_streamLossOnLiveConnClassifiedAsTre() {
        KlinePassController c = ctl();
        c.gap(M, uni, Collections.<String>emptySet(), null, true);
        KlinePassController.EarlyOut e = c.early(M, uni, Collections.<String>emptySet(), true);
        System.out.println("A1-B4b2 thieu=" + e.thieuLucChot + " ws=" + e.thieuWs + " tre=" + e.thieuTre + " (mat stream tren ket noi song => tre)");
        assertEquals(125, e.thieuTre);
        assertEquals(0, e.thieuWs);
    }
}
