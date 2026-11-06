package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.junit.Before;
import org.junit.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.*;

/**
 * [V12 R4r] Guard do du phut (CHI live). Tai hien phut 11-04 23:46Z (627/752), ngay sap nhieu ket noi rot, chung minh khong phut
 * nao bi tre qua giay +20 sau khi dong, va du lieu du =&gt; 0 doc them / khong doi gi (byte-identical r4q).
 */
public class MinuteCompletenessGuardTest {

    static final long MIN = Utils.TIME_MINUTE;
    static final long T = 1_793_835_960_000L - (1_793_835_960_000L % MIN);   // phut 11-04 23:46Z (can phut)
    static final int FULL = 752;

    /** Kho gia: phut -> so symbol co nen; "fill" phut sau N lan doc lai. */
    static final class Store implements LiveTickerWindow.MinuteReader {
        final Map<Long, Integer> count = new HashMap<>();
        final Map<Long, int[]> fillAfter = new HashMap<>();   // phut -> {sau_lan_doc_thu, so_moi}
        final AtomicInteger reads = new AtomicInteger();
        final Map<Long, AtomicInteger> readsOf = new HashMap<>();

        @Override
        public TreeMap<Long, Map<String, KlineObjectSimple>> read(long from, int n) {
            reads.incrementAndGet();
            TreeMap<Long, Map<String, KlineObjectSimple>> out = new TreeMap<>();
            for (int i = 0; i < n; i++) {
                long m = from + i * MIN;
                int k = readsOf.computeIfAbsent(m, x -> new AtomicInteger()).incrementAndGet();
                int[] f = fillAfter.get(m);
                if (f != null && k > f[0]) count.put(m, f[1]);
                Integer c = count.get(m);
                if (c == null) continue;
                Map<String, KlineObjectSimple> mm = new HashMap<>();
                for (int s = 0; s < c; s++) mm.put("S" + s + "USDT", kl(m, s));
                out.put(m, mm);
            }
            return out;
        }
    }

    static KlineObjectSimple kl(long m, int s) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = m;
        k.priceOpen = 1f + s;
        k.priceClose = 1f + s;
        k.maxPrice = 1f + s;
        k.minPrice = 1f + s;
        k.totalUsdt = 100f;
        return k;
    }

    Store st;
    AtomicLong now;
    LiveTickerWindow w;
    List<String> alerts;
    MinuteCompletenessGuard.State gs;

    @Before
    public void setUp() {
        st = new Store();
        now = new AtomicLong();
        w = new LiveTickerWindow(st, 3);
        MinuteCompletenessGuard.N_INCOMPLETE.set(0);
        MinuteCompletenessGuard.N_WAITED.set(0);
        MinuteCompletenessGuard.N_RECOVERED.set(0);
        MinuteCompletenessGuard.N_ALERTS.set(0);
        alerts = new ArrayList<>();
        gs = new MinuteCompletenessGuard.State(alerts::add);   // KHONG gui Telegram that trong test
    }

    private void fill(long from, long to, int c) {
        for (long m = from; m <= to; m += MIN) st.count.put(m, c);
    }

    /** tick live nhu production: doc cua so luc giay :06 cua phut sau, roi guard. */
    private MinuteCompletenessGuard.Verdict tick(long endMinute, long atMsAfterClose) {
        now.set(endMinute + MIN + atMsAfterClose);
        w.read(now.get(), 120);
        return MinuteCompletenessGuard.check(gs, w, endMinute, now::get, ms -> now.addAndGet(ms));
    }

    @Test
    public void normalMinute_noExtraRead_noChange_byteIdentical() {
        fill(T - 119 * MIN, T, FULL);
        now.set(T + MIN + 6_000L);
        Map<String, List<KlineObjectSimple>> before = w.read(now.get(), 120);
        int r0 = st.reads.get();
        MinuteCompletenessGuard.Verdict v = MinuteCompletenessGuard.check(gs, w, T, now::get, ms -> now.addAndGet(ms));
        assertTrue(v.complete);
        assertFalse(v.waited);
        assertEquals("du => 0 lan doc them", r0, st.reads.get());
        assertEquals("khong ngu", T + MIN + 6_000L, now.get());
        assertEquals(FULL, v.have);
        assertEquals(745, v.need);   // ceil(0.99 x 752)
        assertEquals(FULL, w.minuteSnapshot(T).size());
        assertEquals(0, MinuteCompletenessGuard.N_INCOMPLETE.get());
    }

    @Test
    public void incident_2346Z_627of752_waitsTo20s_thenFailClosed() {
        fill(T - 119 * MIN, T - MIN, FULL);
        st.count.put(T, 627);
        MinuteCompletenessGuard.Verdict v = tick(T, 6_000L);
        assertFalse("627/752 => thieu", v.complete);
        assertTrue(v.waited);
        assertEquals(627, v.have);
        assertEquals(745, v.need);
        assertEquals(1504, v.median2);
        assertTrue("khong qua giay +20: " + (now.get() - (T + MIN)), now.get() - (T + MIN) <= 20_000L);
        assertTrue("cho toi sat han", now.get() - (T + MIN) >= 18_000L);
        assertTrue(v.polls >= 5);
        assertEquals(1, MinuteCompletenessGuard.N_INCOMPLETE.get());
    }

    @Test
    public void lateFill_recoversWithinDeadline_andWindowSeesFullMinute() {
        fill(T - 119 * MIN, T - MIN, FULL);
        st.count.put(T, 627);
        st.fillAfter.put(T, new int[]{3, FULL});   // lan doc thu 4 (sau 2 lan doc lai) co du
        MinuteCompletenessGuard.Verdict v = tick(T, 6_000L);
        assertTrue(v.complete);
        assertTrue(v.waited);
        assertEquals(FULL, v.have);
        assertTrue(now.get() - (T + MIN) < 20_000L);
        Map<String, List<KlineObjectSimple>> again = w.read(now.get(), 120);
        int n = 0;
        for (List<KlineObjectSimple> l : again.values()) if (l.get(l.size() - 1).startTime == T) n++;
        assertEquals("doc lai cua so sau khi cho => du 752", FULL, n);
        assertEquals(1, MinuteCompletenessGuard.N_RECOVERED.get());
        assertEquals(0, MinuteCompletenessGuard.N_INCOMPLETE.get());
    }

    @Test
    public void threshold_744incomplete_745complete() {
        fill(T - 119 * MIN, T - MIN, FULL);
        st.count.put(T, 745);
        assertTrue(tick(T, 6_000L).complete);
        setUp();
        fill(T - 119 * MIN, T - MIN, FULL);
        st.count.put(T, 744);
        assertFalse(tick(T, 6_000L).complete);
    }

    @Test
    public void tickAfterDeadline_noWait() {
        fill(T - 119 * MIN, T - MIN, FULL);
        st.count.put(T, 600);
        MinuteCompletenessGuard.Verdict v = tick(T, 25_000L);
        assertFalse(v.complete);
        assertEquals(0, v.polls);
        assertEquals(T + MIN + 25_000L, now.get());
    }

    @Test
    public void insufficientHistory_skips() {
        fill(T - 10 * MIN, T - MIN, FULL);
        st.count.put(T, 100);
        MinuteCompletenessGuard.Verdict v = tick(T, 6_000L);
        assertTrue("< 30 phut lich su => khong kiem", v.complete);
        assertEquals(-1, v.median2);
    }

    /** Ngay sap: nhieu ket noi rot (le + chuoi 3 phut lien), moi phut tick luc :06; khong phut nao tre qua +20 s. */
    @Test
    public void crashDay_manyDrops_noMinuteLatePast20s_allDropsFlagged() {
        long start = T - 300 * MIN;
        fill(start - 119 * MIN, T, FULL);
        Random rnd = new Random(1030);
        Set<Long> dropped = new HashSet<>();
        for (long m = start; m <= T; m += MIN) {
            int r = rnd.nextInt(10);
            if (r == 0) { st.count.put(m, 627); dropped.add(m); }                         // 1 ket noi (125 symbol) rot
            else if (r == 1) { st.count.put(m, 502); dropped.add(m); }                    // 2 ket noi rot
            else if (r == 2) { st.count.put(m, 627); st.fillAfter.put(m, new int[]{2, FULL}); }   // REST bu kip
        }
        for (long b = start + 100 * MIN; b < start + 103 * MIN; b += MIN) { st.count.put(b, 520); st.fillAfter.remove(b); dropped.add(b); }
        long worst = 0;
        int incomplete = 0;
        for (long m = start; m <= T; m += MIN) {
            MinuteCompletenessGuard.Verdict v = tick(m, 6_000L);
            worst = Math.max(worst, now.get() - (m + MIN));
            if (!v.complete) {
                incomplete++;
                assertTrue("phut thieu duoc gan co: " + v.line(), dropped.contains(m));
            } else {
                assertFalse("phut rot ma bao du: " + v.line(), dropped.contains(m));
            }
        }
        assertTrue("phut tre nhat " + worst + " ms <= +20 s", worst <= 20_000L);
        assertEquals(dropped.size(), incomplete);
        assertEquals(incomplete, MinuteCompletenessGuard.N_INCOMPLETE.get());
        assertTrue("co phut REST bu kip", MinuteCompletenessGuard.N_RECOVERED.get() > 0);
        assertFalse("ngay sap => co KHAN", alerts.isEmpty());
        assertTrue("chong spam: <= 1 tin/30' (" + alerts.size() + ")", alerts.size() <= 300 / 30 + 1);
    }

    @Test
    public void median2AndNeed() {
        for (int i = 0; i < 29; i++) gs.addGood(T + i * MIN, 752);
        assertEquals(-1, gs.median2());
        for (int i = 29; i < 80; i++) gs.addGood(T + i * MIN, 752);
        assertEquals("giu 60 phut DU gan nhat", 60, gs.good.size());
        assertEquals(1504, gs.median2());
        assertEquals(745, MinuteCompletenessGuard.need(1504));
        assertEquals(693, MinuteCompletenessGuard.need(1400));   // 0.99 x 700 = 693 dung (khong loi dau phay dong)
    }

    /** [R4s A1 MIN-3] Su co keo dai 35' (627/752): nguong KHONG tu ha — moi phut MI; trung vi 60' cache (cach cu) da ha sau 31'. */
    @Test
    public void longOutage35min_thresholdStays_allMinutesFailClosed() {
        long start = T - 34 * MIN;
        fill(start - 120 * MIN, start - MIN, FULL);
        for (long m = start - 60 * MIN; m < start; m += MIN) assertTrue(tick(m, 6_000L).complete);
        fill(start, T, 627);
        for (long m = start; m <= T; m += MIN) {
            MinuteCompletenessGuard.Verdict v = tick(m, 6_000L);
            assertFalse("phut thu " + ((m - start) / MIN) + " phai MI: " + v.line(), v.complete);
            assertEquals("nguong co dinh 745", 745, v.need);
            assertTrue(now.get() - (m + MIN) <= 20_000L);
        }
        assertEquals(35, MinuteCompletenessGuard.N_INCOMPLETE.get());
        int[] c = w.countsRange(T - 60 * MIN, 60);
        int[] v = Arrays.stream(c).filter(x -> x > 0).sorted().toArray();
        assertEquals("cach cu (trung vi 60' cache) da ha ve 627 => mu", 627, v[v.length / 2]);
        assertEquals("tham chieu chi gom phut DU", 1504, gs.median2());
        // KHAN: phut MI thu 3 (lien tiep) + lan 2 sau 30' (chong spam) = 2 tin
        assertEquals(alerts.toString(), 2, alerts.size());
        assertTrue(alerts.get(0).contains("KHAN") && alerts.get(0).contains("3 phut lien tiep"));
        assertTrue(alerts.get(1).contains("33 phut lien tiep"));
        // het su co => du lai, lien tiep ve 0
        st.count.put(T + MIN, FULL);
        assertTrue(tick(T + MIN, 6_000L).complete);
        assertEquals(0, gs.consecutive);
    }

    /** [R4s MIN-2] 5 phut MI KHONG lien tiep trong 60' => KHAN o phut thu 5; them MI trong 30' => khong spam. */
    @Test
    public void alert_fiveIn60_nonConsecutive_thenCooldown() {
        long start = T - 70 * MIN;
        fill(start - 120 * MIN, T + 30 * MIN, FULL);
        for (int k = 0; k < 8; k++) st.count.put(start + k * 9 * MIN, 600);   // MI cach 9' => lien tiep toi da 1
        int miSeen = 0;
        for (long m = start; m <= start + 70 * MIN; m += MIN) {
            MinuteCompletenessGuard.Verdict v = tick(m, 6_000L);
            if (!v.complete) {
                miSeen++;
                assertEquals("MI thu " + miSeen, miSeen < 5 ? 0 : 1, alerts.size());
            }
        }
        assertEquals(8, miSeen);
        assertEquals("trong 30' sau tin dau: khong gui them", 1, alerts.size());
        assertTrue(alerts.get(0).contains("5 phut/60'"));
    }

    /** 2 phut MI lien tiep roi du => khong KHAN, dem lien tiep ve 0. */
    @Test
    public void twoConsecutive_noAlert() {
        fill(T - 120 * MIN, T + 5 * MIN, FULL);
        st.count.put(T, 600);
        st.count.put(T + MIN, 600);
        for (long m = T - 60 * MIN; m <= T + 3 * MIN; m += MIN) tick(m, 6_000L);
        assertEquals(2, MinuteCompletenessGuard.N_INCOMPLETE.get());
        assertTrue(alerts.isEmpty());
        assertEquals(0, gs.consecutive);
    }

    /** Noi day production: guard ngay sau doc cua so, TRUOC loc A1/feature; chan lenh moi o DAU createOrderBuyRequest0. */
    @Test
    public void wiring_guardBeforeFeatures_blockAtOrderChokePoint() throws Exception {
        String s = new String(Files.readAllBytes(Paths.get(
                "src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java")), StandardCharsets.UTF_8);
        int read = s.indexOf("tickerWindow.read(System.currentTimeMillis(), 1000);");
        int guard = s.indexOf("MinuteCompletenessGuard.check(tickerWindow");
        int a1 = s.indexOf("UniverseA1Filter.filter(symbol2LastTickers");
        assertTrue(read > 0 && guard > read && a1 > guard);
        int m0 = s.indexOf("private void createOrderBuyRequest0(");
        int blk = s.indexOf("if (minuteIncomplete)", m0);
        int hook = s.indexOf("C3LiveHook.onLeg(", m0);
        int pred = s.indexOf("if (prediction == null)", m0);
        assertTrue("chan o dau ham, truoc moi duong vao lenh", blk > m0 && blk < pred && blk < hook);
    }
}
