package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.junit.Before;
import org.junit.Test;

import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Predicate;

import static org.junit.Assert.*;

/**
 * [FIN 2026-11-14, phuong an A] Guard theo bin fin (CHI live). Kho gia mo phong record Aerospike: symbol i co ban NAN (gia lech)
 * cho toi khi "chot" (vao fin + data = ban final). Cac kich ban: du fin ngay, thieu roi bu trong han (+45 s), thieu qua han,
 * thieu bin (ingestor cu), loc universe, nguong 99 %, va "replay tham so" 2 su co that 11-10 21:03 (397/752 luc chot) va
 * 11-13 10:55 (535/752) voi nen chot ve deu trong +4..+30 s.
 */
public class MinuteFinGuardTest {

    static final long MIN = Utils.TIME_MINUTE;
    static final long T = 1_794_000_000_000L - (1_794_000_000_000L % MIN);
    static final int FULL = 752;

    /** Kho: so symbol; so symbol DA CHOT theo thoi gian (ham cua clock); co/khong bin fin. */
    final class Store implements LiveTickerWindow.MinuteReader, LiveTickerWindow.FinReader {
        final Map<Long, Integer> count = new HashMap<>();
        /** phut -> ham (ms sau khi phut dong) -> so symbol da chot (0..count); vang = chot het. */
        final Map<Long, java.util.function.LongToIntFunction> finAt = new HashMap<>();
        final Set<Long> noBin = new HashSet<>();
        final AtomicInteger finReads = new AtomicInteger();

        int finalized(long m) {
            java.util.function.LongToIntFunction f = finAt.get(m);
            int c = count.getOrDefault(m, 0);
            return f == null ? c : Math.min(c, f.applyAsInt(now.get() - (m + MIN)));
        }

        Map<String, KlineObjectSimple> data(long m) {
            Integer c = count.get(m);
            if (c == null) return null;
            int k = finalized(m);
            Map<String, KlineObjectSimple> mm = new HashMap<>();
            for (int s = 0; s < c; s++) mm.put("S" + s + "USDT", kl(m, s, s < k));
            return mm;
        }

        @Override
        public TreeMap<Long, Map<String, KlineObjectSimple>> read(long from, int n) {
            TreeMap<Long, Map<String, KlineObjectSimple>> out = new TreeMap<>();
            for (int i = 0; i < n; i++) {
                long m = from + i * MIN;
                Map<String, KlineObjectSimple> d = data(m);
                if (d != null) out.put(m, d);
            }
            return out;
        }

        @Override
        public MinuteFin.Read read(long m) {
            finReads.incrementAndGet();
            Map<String, KlineObjectSimple> d = data(m);
            if (d == null) return MinuteFin.Read.missing();
            Set<String> fin = null;
            if (!noBin.contains(m)) {
                fin = new HashSet<>();
                int k = finalized(m);
                for (int s = 0; s < k; s++) fin.add("S" + s + "USDT");
            }
            return new MinuteFin.Read(d, fin, true, false);
        }
    }

    /** final: gia 1+s; ban nan: gia lech 1 % (close truoc trade cuoi). */
    static KlineObjectSimple kl(long m, int s, boolean fin) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = m;
        float p = 1f + s;
        k.priceOpen = p;
        k.priceClose = fin ? p : p * 0.99f;
        k.maxPrice = p;
        k.minPrice = fin ? p : p * 0.99f;
        k.totalUsdt = fin ? 100f : 90f;
        return k;
    }

    Store st;
    AtomicLong now;
    LiveTickerWindow w;
    List<String> alerts;
    MinuteCompletenessGuard.State gs;

    @Before
    public void setUp() {
        now = new AtomicLong();
        st = new Store();
        w = new LiveTickerWindow(st, 3, st);
        MinuteCompletenessGuard.N_FIN_INCOMPLETE.set(0);
        MinuteCompletenessGuard.N_FIN_NOBIN.set(0);
        MinuteCompletenessGuard.N_FIN_WAITED.set(0);
        MinuteCompletenessGuard.N_FIN_RECOVERED.set(0);
        alerts = new ArrayList<>();
        gs = new MinuteCompletenessGuard.State(alerts::add);
        for (long m = T - 119 * MIN; m <= T + 10 * MIN; m += MIN) st.count.put(m, FULL);
    }

    /** tick live nhu production: doc cua so luc giay :06 cua phut sau, roi guard fin. */
    private MinuteCompletenessGuard.FinVerdict tick(long endMinute, Predicate<String> u) {
        now.set(endMinute + MIN + 6_000L);
        w.read(now.get(), 120);
        return MinuteCompletenessGuard.checkFin(gs, w, endMinute, u, now::get, ms -> now.addAndGet(ms));
    }

    private int finalInCache(long m) {
        int n = 0;
        for (Map.Entry<String, KlineObjectSimple> e : w.minuteSnapshot(m).entrySet()) {
            int s = Integer.parseInt(e.getKey().substring(1, e.getKey().length() - 4));
            if (LiveKlineAudit.same(e.getValue(), kl(m, s, true))) n++;
        }
        return n;
    }

    @Test
    public void allFinal_noWait_noChange() {
        MinuteCompletenessGuard.FinVerdict v = tick(T, null);
        assertTrue(v.complete);
        assertEquals("DU", v.reason);
        assertFalse(v.waited);
        assertFalse(v.changed);
        assertEquals(0, v.polls);
        assertEquals("khong ngu", T + MIN + 6_000L, now.get());
        assertEquals(FULL, v.have);
        assertEquals(745, v.need);   // ceil(0.99 x 752)
        assertEquals(1, st.finReads.get());
    }

    @Test
    public void missingThenHealedWithinDeadline_decisionDataIsFinal() {
        // luc +6 s chi 397/752 chot (11-10 21:03); toi +14 s chot het
        st.finAt.put(T, ms -> ms < 14_000L ? 397 : FULL);
        MinuteCompletenessGuard.FinVerdict v = tick(T, null);
        assertTrue(v.complete);
        assertEquals("DU_SAU_CHO", v.reason);
        assertTrue(v.waited);
        assertTrue("cache da duoc thay ban chot", v.changed);
        assertEquals(4, v.polls);   // +8, +10, +12, +14
        assertEquals(T + MIN + 14_000L, now.get());
        assertEquals("quyet dinh tren nen DA CHOT", FULL, finalInCache(T));
        assertEquals(1, MinuteCompletenessGuard.N_FIN_RECOVERED.get());
        assertEquals(0, MinuteCompletenessGuard.N_FIN_INCOMPLETE.get());
    }

    @Test
    public void missingPastDeadline_failClosedAt45s() {
        st.finAt.put(T, ms -> 397);
        MinuteCompletenessGuard.FinVerdict v = tick(T, null);
        assertFalse(v.complete);
        assertEquals("FIN_THIEU", v.reason);
        assertEquals("khong bao gio cho qua +45 s", T + MIN + 45_000L, now.get());
        assertEquals(397, v.have);
        assertEquals(745, v.need);
        assertEquals(1, MinuteCompletenessGuard.N_FIN_INCOMPLETE.get());
        assertEquals(1, gs.consecutive);
    }

    @Test
    public void noBin_oldIngestor_failClosedImmediately_thenAfterSeenWaits_thenResets() {
        st.noBin.add(T);
        MinuteCompletenessGuard.FinVerdict v = tick(T, null);
        assertFalse(v.complete);
        assertEquals("FIN_KHONG_BIN", v.reason);
        assertEquals("chua tung thay bin => khong cho", T + MIN + 6_000L, now.get());
        assertEquals(1, MinuteCompletenessGuard.N_FIN_NOBIN.get());
        // phut sau co bin (ingestor moi) => finSeen; phut sau nua mat bin => cho toi han roi fail-closed
        assertTrue(tick(T + MIN, null).complete);
        st.noBin.add(T + 2 * MIN);
        st.noBin.add(T + 3 * MIN);
        st.noBin.add(T + 4 * MIN);
        st.noBin.add(T + 5 * MIN);
        MinuteCompletenessGuard.FinVerdict v2 = tick(T + 2 * MIN, null);
        assertEquals("FIN_KHONG_BIN", v2.reason);
        assertEquals(T + 3 * MIN + 45_000L, now.get());
        tick(T + 3 * MIN, null);
        MinuteCompletenessGuard.FinVerdict v4 = tick(T + 4 * MIN, null);   // phut thu 3 lien tiep khong bin => reset finSeen
        assertEquals("FIN_KHONG_BIN", v4.reason);
        MinuteCompletenessGuard.FinVerdict v5 = tick(T + 5 * MIN, null);
        assertEquals("sau reset: fail-closed ngay, khong chan tick", T + 6 * MIN + 6_000L, now.get());
        assertFalse(v5.complete);
        assertFalse("KHAN Telegram khi MI lien tiep >= 3", alerts.isEmpty());
    }

    @Test
    public void universeFilter_unfinalOutsideUniverseIgnored() {
        st.finAt.put(T, ms -> 600);   // S600..S751 chua chot nhung ngoai universe (vd TradFi/A1)
        Predicate<String> u = s -> Integer.parseInt(s.substring(1, s.length() - 4)) < 600;
        MinuteCompletenessGuard.FinVerdict v = tick(T, u);
        assertTrue(v.complete);
        assertEquals(600, v.universe);
        assertEquals(600, v.have);
        assertEquals(0, v.polls);
    }

    @Test
    public void threshold99pct_edge() {
        st.finAt.put(T, ms -> 745);
        assertTrue(tick(T, null).complete);
        st.finAt.put(T + MIN, ms -> 744);
        assertFalse(tick(T + MIN, null).complete);
        assertEquals(745, MinuteCompletenessGuard.finNeed(752));
        assertEquals(507, MinuteCompletenessGuard.finNeed(512));
    }

    /** Replay tham so 2 su co that: nen chot ve deu tu +4 s toi +30 s (do 11-06/11-10/11-13). */
    @Test
    public void replayIncidents_1110_2103_and_1113_1055() {
        int[] atChot = {397, 535};
        for (int i = 0; i < atChot.length; i++) {
            long m = T + i * 3 * MIN;
            final int a = atChot[i];
            st.finAt.put(m, ms -> ms <= 4_000L ? a : (int) Math.min(FULL, a + (FULL - a) * (ms - 4_000L) / 26_000L));
            MinuteCompletenessGuard.FinVerdict v = tick(m, null);
            assertTrue("su co " + i + " bu trong han", v.complete);
            assertTrue(v.waited);
            assertTrue("xong truoc +30 s", now.get() <= m + MIN + 30_000L);
            assertTrue(">= 99 % nen quyet dinh la ban chot", finalInCache(m) >= 745);
        }
        assertEquals(0, MinuteCompletenessGuard.N_FIN_INCOMPLETE.get());
    }

    @Test
    public void flagParse() {
        assertTrue(MinuteCompletenessGuard.parseFinFlag(null));
        assertTrue(MinuteCompletenessGuard.parseFinFlag(""));
        assertTrue(MinuteCompletenessGuard.parseFinFlag("1"));
        assertFalse(MinuteCompletenessGuard.parseFinFlag("0"));
        assertFalse(MinuteCompletenessGuard.parseFinFlag(" FALSE "));
        // [A1-M5] khop script: no/off (moi kieu hoa) cung la TAT
        assertFalse(MinuteCompletenessGuard.parseFinFlag("no"));
        assertFalse(MinuteCompletenessGuard.parseFinFlag("Off"));
        assertFalse(MinuteCompletenessGuard.parseFinFlag(" NO "));
        assertTrue(MinuteCompletenessGuard.parseFinFlag("on"));
    }

    /** [A1-M2] phut DU (>= 99 %) nhung 5 coin chua chot: 5 coin bi loai THEO COIN (finAllows false), coin chot van duoc. */
    @Test
    public void perCoinExclusion_unfinalCoinsBlockedEvenWhenTotalPasses() {
        MinuteCompletenessGuard.N_FIN_EXCL_MINUTES.set(0);
        MinuteCompletenessGuard.N_FIN_EXCL_SYMS.set(0);
        st.finAt.put(T, ms -> FULL - 5);   // S747..S751 khong bao gio chot; 747 >= 745 => DU ngay
        MinuteCompletenessGuard.FinVerdict v = tick(T, null);
        assertTrue(v.complete);
        assertEquals("DU", v.reason);
        assertEquals(Arrays.asList("S747USDT", "S748USDT", "S749USDT", "S750USDT", "S751USDT"), v.excluded);
        assertNotNull(v.finSyms);
        assertEquals(FULL - 5, v.finSyms.size());
        for (int s = 747; s < FULL; s++) assertFalse(MinuteCompletenessGuard.finAllows(v.finSyms, "S" + s + "USDT"));
        assertTrue(MinuteCompletenessGuard.finAllows(v.finSyms, "S0USDT"));
        assertTrue(MinuteCompletenessGuard.finAllows(v.finSyms, "S746USDT"));
        assertFalse("coin khong co nen phut nay cung khong co trong fin", MinuteCompletenessGuard.finAllows(v.finSyms, "NEWUSDT"));
        assertEquals(1, MinuteCompletenessGuard.N_FIN_EXCL_MINUTES.get());
        assertEquals(5, MinuteCompletenessGuard.N_FIN_EXCL_SYMS.get());
        assertTrue(v.line().contains("loai_coin=5"));
        // phut sau du het => khong loai coin nao
        MinuteCompletenessGuard.FinVerdict v2 = tick(T + MIN, null);
        assertTrue(v2.excluded.isEmpty());
        assertTrue(MinuteCompletenessGuard.finAllows(v2.finSyms, "S751USDT"));
        assertEquals(1, MinuteCompletenessGuard.N_FIN_EXCL_MINUTES.get());
    }

    /** [A1-M2] coin ngoai universe khong tinh vao danh sach loai; guard fin tat (finSyms null) => khong loc. */
    @Test
    public void perCoinExclusion_universeOnly_andNullMeansNoFilter() {
        st.finAt.put(T, ms -> 600);
        Predicate<String> u = s -> Integer.parseInt(s.substring(1, s.length() - 4)) < 600;
        MinuteCompletenessGuard.FinVerdict v = tick(T, u);
        assertTrue(v.complete);
        assertTrue(v.excluded.isEmpty());
        assertTrue(MinuteCompletenessGuard.finAllows(null, "S700USDT"));
        assertFalse(MinuteCompletenessGuard.finAllows(Collections.<String>emptySet(), "S0USDT"));
    }

    /** [A1-M3] tre quyet dinh: DU ngay ~+6 s; phai cho => tre_sau_dong = luc DU; fail-closed => khong co finSyms. */
    @Test
    public void lateMs_recorded() {
        MinuteCompletenessGuard.FinVerdict v = tick(T, null);
        assertEquals(6_000L, v.lateMs);
        st.finAt.put(T + MIN, ms -> ms < 14_000L ? 397 : FULL);
        MinuteCompletenessGuard.FinVerdict v2 = tick(T + MIN, null);
        assertEquals("DU_SAU_CHO", v2.reason);
        assertEquals(14_000L, v2.lateMs);
        assertTrue(v2.line().contains("tre_sau_dong=14000ms"));
        st.finAt.put(T + 2 * MIN, ms -> 397);
        MinuteCompletenessGuard.FinVerdict v3 = tick(T + 2 * MIN, null);
        assertFalse(v3.complete);
        assertEquals(45_000L, v3.lateMs);
        assertNull(v3.finSyms);
        assertTrue(v3.excluded.isEmpty());
    }
}
