package com.binance.chuyennd.websocket;

import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.utils.BinanceRestGuard;
import com.binance.chuyennd.utils.RestBudget;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.IntBinaryOperator;
import java.util.function.LongSupplier;

import static org.junit.Assert.*;

/**
 * [INGEST-QF2] Kịch bản đối kháng chạy ĐÚNG mã production (KlineIngestCore + SettlePlanner + KlinePassController + RestBudget),
 * thời gian mô phỏng nhanh ×10 (1 phút = 6 s thật). Đo: khoảng giá lớn nhất (Rest-Price-Loop mô phỏng, lane PRICE),
 * đỉnh weight IP & futures/data, thời gian lành lỗ (mọi ô = FINAL và planner hết suspect) so với prereg ADD-1b.
 * Nền xấu nhất: lane LOW bị repair chiếm đầy, OI chạy liên tục ở lane FDATA, premiumIndex 10 weight/30 s.
 */
public class IngestScenarioTest {
    static final long MIN = 60_000L;
    static final long M0 = 1_760_000_040_000L / MIN * MIN;
    static final int N = 752;
    static final double SPEED = 10.0;

    final List<String> uni = new ArrayList<>();
    ExecutorService pool;

    @Before
    public void setUp() {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        for (int i = 0; i < N; i++) uni.add(String.format("S%03dUSDT", i));
        pool = Executors.newFixedThreadPool(30);
    }

    @After
    public void tearDown() {
        pool.shutdownNow();
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
    }

    static KlineObjectOptimized fin(String s, long m) {
        float b = 1 + (s.hashCode() & 0xff) + (float) ((m / MIN) % 97);
        return KlineObjectOptimized.newBuilder().setPriceOpen(b).setMaxPrice(b + 2).setMinPrice(b - 1).setPriceClose(b + 1).setTotalUsdt(1000 + b).build();
    }

    static KlineObjectOptimized unsettled(String s, long m) {
        KlineObjectOptimized f = fin(s, m);
        return f.toBuilder().setPriceClose(f.getPriceClose() - 0.5f).setTotalUsdt(f.getTotalUsdt() - 7).build();
    }

    static final class Result {
        long priceMaxGapMs, priceDenied, oiOk;
        int peakWeight, peakFdata;
        Map<Long, Long> healMs = new HashMap<>();      // phut -> ms sau khi dong (sim) toi khi lanh
        Map<Long, Integer> missingAt4s = new HashMap<>();
        int maxEarlyRequested;
        long droppedCells;
        String log = "";
        /** [QF4] pass +2 s / thieu luc chot (+4 s) / so o lost co ban REST trong store luc pass +2 s xong. */
        Map<Long, KlinePassController.GapOut> gap = new HashMap<>();
        Map<Long, Integer> thieuLucChot = new HashMap<>();
        Map<Long, Integer> lostWithRestAt4s = new HashMap<>();
        int maxGapRequested;
    }

    /** [QF4] 6 kết nối như prod (KlineWsClient.chunk, 150/kết nối ⇒ 126,126,125,125,125,125). */
    List<List<String>> groups() {
        return KlineWsClient.chunk(uni, 150);
    }

    Result run(int minutes, IntBinaryOperator wsDelay, int extraHealMinutes) throws Exception {
        return run(minutes, wsDelay, extraHealMinutes, mi -> Collections.<Integer>emptySet());
    }

    /**
     * Chạy mô phỏng {@code minutes} phút đóng (từ M0). {@code wsDelay.applyAsInt(idx, minuteIdx)} = ms sau đóng nến WS final tới,
     * hoặc -1 nếu không bao giờ tới. Phút được kiểm lành: mọi phút có symbol thiếu ở +4 s.
     */
    Result run(int minutes, IntBinaryOperator wsDelay, int extraHealMinutes,
               java.util.function.IntFunction<Set<Integer>> gapConnsAt) throws Exception {
        final List<List<String>> groups = groups();
        final long realStart = System.currentTimeMillis();
        final LongSupplier sim = () -> M0 + (long) ((System.currentTimeMillis() - realStart) * SPEED);
        final RestBudget budget = RestBudget.create(300, 1600, 2000, 150, sim);
        final KlineIngestCoreTest.FakeStore store = new KlineIngestCoreTest.FakeStore();
        final AtomicInteger restCalls = new AtomicInteger();
        KlineIngestCore.RestFetcher rest = (sym, limit) -> {
            if (!budget.acquire(1, RestBudget.Lane.KLINE, RestBudget.maxWaitMs(RestBudget.Lane.KLINE)))
                throw new IllegalStateException("budget KLINE het cho");
            restCalls.incrementAndGet();
            Thread.sleep(8);   // ~80 ms mo phong
            long now = sim.getAsLong();
            long cur = now / MIN * MIN;
            List<KlineIngestCore.Bar> out = new ArrayList<>();
            for (long m = cur - (long) (limit - 1) * MIN; m <= cur; m += MIN) {
                boolean settled = now - (m + MIN) >= 8_000L;   // REST chua settle truoc +8 s (do 10-10)
                out.add(new KlineIngestCore.Bar(m, settled ? fin(sym, m) : unsettled(sym, m)));
            }
            return out;
        };
        KlineIngestCore core = new KlineIngestCore(store, rest, pool, 2, 30L, 20_000L, 15_000L);
        SettlePlanner planner = new SettlePlanner(25, 30);
        KlinePassController ctl = new KlinePassController(core, planner, () -> budget.available(RestBudget.Lane.KLINE), sim,
                60, 3, M0 - 10 * MIN, 20_000L);
        Result res = new Result();
        AtomicBoolean stop = new AtomicBoolean();
        List<Long> priceOk = Collections.synchronizedList(new ArrayList<>());
        AtomicLong priceDenied = new AtomicLong(), oiOk = new AtomicLong();
        Thread price = new Thread(() -> {
            while (!stop.get()) {
                if (budget.acquire(2, RestBudget.Lane.PRICE, RestBudget.maxWaitMs(RestBudget.Lane.PRICE))) priceOk.add(sim.getAsLong());
                else priceDenied.incrementAndGet();
                try { Thread.sleep((long) (3000 / SPEED)); } catch (InterruptedException e) { return; }
            }
        });
        Thread oi = new Thread(() -> {
            while (!stop.get()) {
                if (budget.acquire(1, RestBudget.Lane.FDATA, RestBudget.maxWaitMs(RestBudget.Lane.FDATA))) oiOk.incrementAndGet();
                try { Thread.sleep((long) (250 / SPEED)); } catch (InterruptedException e) { return; }
            }
        });
        Thread low = new Thread(() -> {   // repair khoi dong + premiumIndex: chiem LOW toi tran
            long nextPrem = 0;
            while (!stop.get()) {
                long t = sim.getAsLong();
                if (t >= nextPrem) { budget.acquire(10, RestBudget.Lane.LOW, 30_000L); nextPrem = t + 30_000L; }
                budget.acquire(5, RestBudget.Lane.LOW, 3_000L);
                try { Thread.sleep(5); } catch (InterruptedException e) { return; }
            }
        });
        price.start(); oi.start(); low.start();
        Map<Long, Set<Integer>> delivered = new HashMap<>();
        Set<Long> flushed = new HashSet<>(), early = new HashSet<>(), settled = new HashSet<>(), caught = new HashSet<>(), gapped = new HashSet<>();
        long endSim = M0 + (long) (minutes + 1 + extraHealMinutes) * MIN + 35_000L;
        int peakW = 0, peakF = 0;
        while (sim.getAsLong() < endSim) {
            long now = sim.getAsLong();
            long curMin = now / MIN * MIN;
            for (long m = M0; m < curMin && m < M0 + (long) minutes * MIN; m += MIN) {   // giao WS final cua phut da dong
                int mi = (int) ((m - M0) / MIN);
                Set<Integer> d = delivered.computeIfAbsent(m, k -> new HashSet<>());
                for (int i = 0; i < N; i++) {
                    if (d.contains(i)) continue;
                    int dl = wsDelay.applyAsInt(i, mi);
                    if (dl >= 0 && now >= m + MIN + dl) { core.onWsFinal(uni.get(i), m, fin(uni.get(i), m)); d.add(i); }
                }
            }
            long m = curMin - MIN;
            long inMin = now - curMin;
            if (m >= M0) {
                if (!flushed.contains(m) && inMin >= 1_500L) { core.flushWsFinals(m); flushed.add(m); }
                core.flushLateFinals();
                if (!gapped.contains(m) && inMin >= 2_000L && flushed.contains(m) && m < M0 + (long) minutes * MIN) {   // [QF4] pass +2 s nhu Finalizer
                    gapped.add(m);
                    int mi = (int) ((m - M0) / MIN);
                    Set<String> gs = new HashSet<>();
                    for (int ci : gapConnsAt.apply(mi)) gs.addAll(groups.get(ci));
                    KlinePassController.GapOut g = ctl.gap(m, uni, gs, null, true);
                    res.gap.put(m, g);
                    res.maxGapRequested = Math.max(res.maxGapRequested, g.requested);
                    int have = 0;
                    if (g.doneAtMs > 0 && g.doneAtMs - (m + MIN) <= 4_000L) {
                        for (String s : g.lostSample.isEmpty() ? Collections.<String>emptyList() : uni) {
                            if (gs.contains(s) && store.get(m, KlineIngestCore.shortSym(s)) != null) have++;
                        }
                    }
                    res.lostWithRestAt4s.put(m, have);
                }
                if (!early.contains(m) && inMin >= 4_000L && flushed.contains(m) && m < M0 + (long) minutes * MIN) {
                    early.add(m);
                    KlinePassController.EarlyOut o = ctl.early(m, uni, true);
                    res.missingAt4s.put(m, o.missingWs);
                    res.thieuLucChot.put(m, o.thieuLucChot);
                    res.maxEarlyRequested = Math.max(res.maxEarlyRequested, o.requested);
                }
                if (!settled.contains(m) && inMin >= 30_000L) {
                    settled.add(m);
                    ctl.settle(curMin, uni);
                }
                if (early.contains(m) || m >= M0 + (long) minutes * MIN) ctl.maybeCatchUp(curMin, inMin, uni);   // nhu Kline-Finalizer
            }
            for (Map.Entry<Long, Integer> e : res.missingAt4s.entrySet()) {   // lanh: moi o = FINAL va het suspect
                long mm = e.getKey();
                if (e.getValue() == 0 || res.healMs.containsKey(mm) || planner.pendingAt(mm) > 0) continue;
                boolean ok = true;
                for (String s : uni) if (!KlineIngestCore.sameBits(fin(s, mm), store.get(mm, KlineIngestCore.shortSym(s)))) { ok = false; break; }
                if (ok) res.healMs.put(mm, now - (mm + MIN));
            }
            peakW = Math.max(peakW, budget.usedNow());
            peakF = Math.max(peakF, budget.fdataNow());
            Thread.sleep(10);
        }
        stop.set(true);
        price.interrupt(); oi.interrupt(); low.interrupt();
        List<Long> p = new ArrayList<>(priceOk);
        p.add(endSim);
        long prev = M0, gap = 0;
        for (long t : p) { gap = Math.max(gap, t - prev); prev = t; }
        res.priceMaxGapMs = gap;
        res.priceDenied = priceDenied.get();
        res.oiOk = oiOk.get();
        res.peakWeight = peakW;
        res.peakFdata = peakF;
        res.droppedCells = planner.droppedCells();
        StringBuilder gl = new StringBuilder();
        for (Map.Entry<Long, KlinePassController.GapOut> e : new java.util.TreeMap<>(res.gap).entrySet()) {
            KlinePassController.GapOut g = e.getValue();
            gl.append(String.format("[lost=%d req=%d ok=%d xong_ms=%d co_rest_4s=%d thieu_luc_chot=%s]", g.lost, g.requested, g.closed,
                    g.doneAtMs == 0 ? -1 : g.doneAtMs - (e.getKey() + MIN), res.lostWithRestAt4s.get(e.getKey()), res.thieuLucChot.get(e.getKey())));
        }
        res.log = String.format("price_max_gap_ms=%d price_denied=%d peak_weight=%d peak_fdata=%d oi_ok=%d rest_kline_calls=%d missing_at_4s=%s heal_ms=%s max_early_requested=%d dropped=%d gap=%s",
                gap, res.priceDenied, peakW, peakF, res.oiOk, restCalls.get(), new java.util.TreeMap<>(res.missingAt4s).values(),
                new java.util.TreeMap<>(res.healMs).values(), res.maxEarlyRequested, res.droppedCells, gl);
        return res;
    }

    void assertCommon(String name, Result r, Map<Long, Integer> expectMissing) {
        System.out.println("[QF2-SCENARIO] " + name + " " + r.log);
        assertTrue(name + " gia dung > 5 s: " + r.log, r.priceMaxGapMs <= 5_000L);
        assertEquals(name + " gia bi tu choi", 0, r.priceDenied);
        assertTrue(name + " weight IP > 300: " + r.log, r.peakWeight <= 300);
        assertTrue(name + " futures/data > 150: " + r.log, r.peakFdata <= 150);
        assertTrue(name + " REST som vuot 60: " + r.log, r.maxEarlyRequested <= 60);
        assertEquals(name + " bo kiem", 0, r.droppedCells);
        for (Map.Entry<Long, Integer> e : expectMissing.entrySet()) {
            int n = e.getValue();
            long limitMs = n <= 200 ? 3 * MIN : (long) (Math.ceil(n / 200.0) + 1) * MIN;   // prereg ADD-1b
            Long h = r.healMs.get(e.getKey());
            assertNotNull(name + " phut " + e.getKey() + " khong lanh: " + r.log, h);
            assertTrue(name + " lanh cham " + h + " ms > " + limitMs + ": " + r.log, h <= limitMs);
        }
    }

    /** QF2-T1 (A1-T1 trên mã thật): WS chết đúng 1 phút (phút thứ 2), OI + LOW nền. */
    @Test(timeout = 120_000)
    public void wsDeadOneMinute() throws Exception {
        Result r = run(3, (i, mi) -> mi == 1 ? -1 : 500, 5);
        Map<Long, Integer> exp = new HashMap<>();
        exp.put(M0 + MIN, N);
        assertEquals(Integer.valueOf(N), r.missingAt4s.get(M0 + MIN));
        assertCommon("ws_dead_1min", r, exp);
    }

    /** Cả 6 kết nối rơi cùng lúc (mốc 24h không xoay / mạng): mất 2 phút liền (phát hiện + backoff mở lại). */
    @Test(timeout = 150_000)
    public void allSixConnectionsDropTwoMinutes() throws Exception {
        Result r = run(4, (i, mi) -> (mi == 1 || mi == 2) ? -1 : 500, 6);
        Map<Long, Integer> exp = new HashMap<>();
        exp.put(M0 + MIN, N);
        exp.put(M0 + 2 * MIN, N);
        assertCommon("all6_drop_2min", r, exp);
    }

    /** Phút biến động: 376 symbol WS final tới trễ 3–6,6 s, 94 trong số đó không bao giờ tới. */
    @Test(timeout = 120_000)
    public void volatileMinute376Late() throws Exception {
        Result r = run(3, (i, mi) -> {
            if (mi != 1 || i >= 376) return 500;
            if (i % 4 == 0) return -1;
            return 3_000 + (i % 10) * 400;
        }, 4);
        int miss = r.missingAt4s.get(M0 + MIN);
        assertTrue("phai co thieu luc +4 s: " + miss, miss >= 94 && miss <= 376);
        Map<Long, Integer> exp = new HashMap<>();
        exp.put(M0 + MIN, miss);
        assertCommon("volatile_376", r, exp);
    }

    // ===================== [QF4, ADDENDUM 3 / ADD-3b] REST bù mất WS ở +2 s — ngưỡng pre-reg, KHÔNG chỉnh sau khi xem kết quả =====================

    /** Chỉ số symbol (trong uni) của kết nối {@code ci}. */
    Set<Integer> idxOf(int... cis) {
        Set<Integer> out = new HashSet<>();
        List<List<String>> g = groups();
        for (int ci : cis) for (String s : g.get(ci)) out.add(uni.indexOf(s));
        return out;
    }

    /** Kết nối {@code cis} rớt ĐÚNG ranh phút thứ 2 (mi=1): WS final của chúng không bao giờ tới; phút khác bình thường. */
    Result runDrop(int... cis) throws Exception {
        final Set<Integer> dead = idxOf(cis);
        final Set<Integer> conns = new HashSet<>();
        for (int ci : cis) conns.add(ci);
        return run(3, (i, mi) -> mi == 1 && dead.contains(i) ? -1 : 500, 4,
                mi -> mi == 1 ? conns : Collections.<Integer>emptySet());
    }

    void assertDropAt4s(String name, Result r, int lostExpect, int minWithRest) {
        long m = M0 + MIN;
        KlinePassController.GapOut g = r.gap.get(m);
        System.out.println("[QF4-SCENARIO] " + name + " " + r.log);
        assertNotNull(name + " khong chay pass +2 s", g);
        assertEquals(name + " tap mat WS", lostExpect, g.lost);
        assertTrue(name + " REST vuot room KLINE 200: " + g.requested, g.requested <= RestBudget.KLINE_QUOTA);
        assertTrue(name + " pass +2 s xong sau +4 s: " + (g.doneAtMs - (m + MIN)), g.doneAtMs - (m + MIN) <= 4_000L);
        int have = r.lostWithRestAt4s.get(m);
        assertTrue(name + " o co ban REST truoc +4 s = " + have + " < " + minWithRest, have >= minWithRest);
        assertEquals(name + " thieu_luc_chot = lost - co REST", lostExpect - have, (int) r.thieuLucChot.get(m));
        Map<Long, Integer> exp = new HashMap<>();
        exp.put(m, lostExpect);
        assertCommon(name, r, exp);
    }

    /** T-Q4-1: một kết nối (125) rớt đúng :00 ⇒ 125/125 có REST trước +4 s, thieu_luc_chot = 0. */
    @Test(timeout = 120_000)
    public void tq4_1_oneConnectionDropsAtMinute() throws Exception {
        assertDropAt4s("tq4_1_1conn", runDrop(3), 125, 125);
    }

    /** T-Q4-2: hai kết nối (250) cùng rớt ⇒ ≥150 có REST trước +4 s (vừa room KLINE), phần còn lại = thieu_luc_chot, lành ≤ 3′. */
    @Test(timeout = 120_000)
    public void tq4_2_twoConnectionsDropTogether() throws Exception {
        assertDropAt4s("tq4_2_2conn", runDrop(2, 3), 250, 150);
    }

    /** T-Q4-3: phút bình thường (đo ADD-3b: 75 % symbol final tới ở 3,05 s) ⇒ 0 REST mất WS, thieu_luc_chot = 0. */
    @Test(timeout = 120_000)
    public void tq4_3_normalMinutesNoFalseGap() throws Exception {
        Result r = run(3, (i, mi) -> i % 4 == 0 ? 500 : 3_050, 1);
        System.out.println("[QF4-SCENARIO] tq4_3_normal " + r.log);
        for (KlinePassController.GapOut g : r.gap.values()) {
            assertTrue("thieu o +2 s phai lon (phan bo do duoc): " + g.missing, g.missing >= 500);
            assertEquals("bao nham mat WS", 0, g.lost);
        }
        assertEquals(0, r.maxGapRequested);
        for (int t : r.thieuLucChot.values()) assertEquals(0, t);
        for (int miss : r.missingAt4s.values()) assertEquals(0, miss);
        assertCommon("tq4_3_normal", r, new HashMap<>());
    }

    /** T-Q4-4: kết nối im lặng không EOF (luật b: KlineWsClient.silentNow) ⇒ như T-Q4-1 (kết nối 0, 126 symbol). */
    @Test(timeout = 120_000)
    public void tq4_4_silentConnectionNoEof() throws Exception {
        long close = M0 + 2 * MIN;
        assertTrue("im lang 2,1 s tai +2 s => mat", KlineWsClient.silentNow(126, close - 100, close + 2_000));
        assertFalse("ket noi van song (EOF chua co) => luat a khong bat", KlineWsClient.hadGapSince(true, 0, close - 3_600_000L, close - 1_000));
        assertDropAt4s("tq4_4_silent", runDrop(0), 126, 126);
    }
}
