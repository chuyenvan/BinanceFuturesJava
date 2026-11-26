package com.binance.chuyennd.websocket;

import org.junit.Test;

import java.util.Collections;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static com.binance.chuyennd.websocket.KlineIngestCoreTest.*;
import static org.junit.Assert.*;

/** A1 AUDIT (khong commit vao nhanh implementer): WS gui nen KHONG x=true. */
public class A1QfWsAdversarialTest {

    static String msg(long t, String x) {
        return "{\"stream\":\"btcusdt@kline_1m\",\"data\":{\"e\":\"kline\",\"k\":{\"t\":" + t
                + ",\"s\":\"BTCUSDT\",\"i\":\"1m\",\"o\":\"100\",\"h\":\"101\",\"l\":\"99.5\",\"c\":\"100.4\",\"q\":\"9000\"" + x + "}}}";
    }

    @Test
    public void t3a_parseNonFinal() {
        assertFalse(KlineWsClient.parse(msg(M, ",\"x\":false")).closed);
        assertTrue(KlineWsClient.parse(msg(M, ",\"x\":true")).closed);
        assertNull("thieu x => bo su kien (khong coi la final)", KlineWsClient.parse(msg(M, "")));
    }

    /** Phut M chi co x=false tu WS: +4 s REST som (chua settle) duoc danh dau suspect; +30 s pass suspects sua ve FINAL. */
    @Test
    public void t3b_nonFinalOnlyMinuteRepairedBySuspectPass() {
        FakeStore store = new FakeStore();
        FakeRest rest = new FakeRest();
        ExecutorService pool = Executors.newFixedThreadPool(4);
        try {
            KlineIngestCore core = new KlineIngestCore(store, rest, pool, 2, 0L, AGE, 5_000L);
            SettlePlanner planner = new SettlePlanner(25, 30);
            KlineWsClient.KlineEvent ev = KlineWsClient.parse(msg(M, ",\"x\":false"));
            if (ev.closed) core.onWsFinal(ev.symbol, ev.openTime, ev.k);   // dung nhu KlineWsClient: x=false khong vao final
            List<String> uni = Collections.singletonList("BTCUSDT");
            List<String> need = core.missingFinals(M, uni);
            assertEquals(uni, need);
            planner.markSuspects(need, M);
            rest.on("BTCUSDT", bars(bar(M, UNSETTLED), bar(M + MIN, OPEN)),
                    bars(bar(M, FINAL), bar(M + MIN, OPEN)));
            core.earlyRest(M, need);
            assertTrue(KlineIngestCore.sameBits(UNSETTLED, store.get(M, "BTC")));
            long cur = M + MIN;
            SettlePlanner.Plan p = planner.plan(cur, uni);
            assertEquals(uni, p.suspects);
            KlineIngestCore.SettleResult r = core.settle(cur + 30_000L, p.suspects, p.suspectLimit);
            planner.onSuspectsSettled(p.suspects, r.failedSymbols, cur, p.suspectLimit);
            assertTrue("o REST-som phai duoc sua ve FINAL", KlineIngestCore.sameBits(FINAL, store.get(M, "BTC")));
            assertEquals(0, planner.suspectCount());
        } finally {
            pool.shutdownNow();
        }
    }

    /** REST loi lien tuc 30 pass => planner bo kiem: o REST-som chua settle o lai VINH VIEN (ghi nhan hanh vi). */
    @Test
    public void t3c_persistentRestFailureLeavesUnsettledCell() {
        FakeStore store = new FakeStore();
        FakeRest rest = new FakeRest();
        ExecutorService pool = Executors.newFixedThreadPool(4);
        try {
            KlineIngestCore core = new KlineIngestCore(store, rest, pool, 1, 0L, AGE, 5_000L);
            SettlePlanner planner = new SettlePlanner(0, 30);
            List<String> uni = Collections.singletonList("BTCUSDT");
            planner.markSuspects(uni, M);
            rest.on("BTCUSDT", bars(bar(M, UNSETTLED), bar(M + MIN, OPEN)), new IllegalStateException("budget denied"));
            core.earlyRest(M, uni);
            int passes = 0;
            for (long cur = M + MIN; planner.suspectCount() > 0 && passes < 100; cur += MIN, passes++) {
                SettlePlanner.Plan p = planner.plan(cur, uni);
                KlineIngestCore.SettleResult r = core.settle(cur + 30_000L, p.suspects, p.suspectLimit);
                planner.onSuspectsSettled(p.suspects, r.failedSymbols, cur, p.suspectLimit);
            }
            System.out.println("A1-T3c passes_truoc_khi_bo=" + passes);
            assertEquals(30, passes);
            assertTrue(KlineIngestCore.sameBits(UNSETTLED, store.get(M, "BTC")));
        } finally {
            pool.shutdownNow();
        }
    }
}
