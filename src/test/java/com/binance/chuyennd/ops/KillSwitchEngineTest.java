package com.binance.chuyennd.ops;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.nio.file.Files;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.*;

import static org.junit.Assert.*;

/** [V11D OPS] kill-switch: chinh sach mode, moi detector o bien nguong, may trang thai log-only, luu dinh, dem gio. */
public class KillSwitchEngineTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final class ListSink implements KillSwitchEngine.Sink {
        final List<String> lines = new ArrayList<>();

        public void info(String m) {
            lines.add("I " + m);
        }

        public void warn(String m) {
            lines.add("W " + m);
        }

        long count(String s) {
            return lines.stream().filter(l -> l.contains(s)).count();
        }
    }

    private static final long T0 = ZonedDateTime.of(2026, 10, 21, 14, 10, 0, 0, ZoneId.of("Asia/Ho_Chi_Minh"))
            .toInstant().toEpochMilli();

    private KillSwitchEngine engine(ListSink s, File peak) {
        return new KillSwitchEngine(KillSwitchEngine.Mode.LOG, "log", s, peak, () -> 35000d, () -> 0.60f, T0);
    }

    // ------------------------------------------------------------ mode
    @Test
    public void modeOffByDefault() {
        assertEquals(KillSwitchEngine.Mode.OFF, KillSwitchEngine.resolve(null, "c3_shadow").effective);
        assertEquals(KillSwitchEngine.Mode.OFF, KillSwitchEngine.resolve("", "c3_shadow").effective);
        assertEquals(KillSwitchEngine.Mode.OFF, KillSwitchEngine.resolve(" off ", "c3_shadow").effective);
        assertNull(KillSwitchEngine.resolve(null, null).warn);
    }

    @Test
    public void modeLogAllowedOnShadow() {
        KillSwitchEngine.Resolved r = KillSwitchEngine.resolve(" LOG ", "c3_shadow");
        assertEquals(KillSwitchEngine.Mode.LOG, r.effective);
        assertNull(r.warn);
    }

    @Test
    public void modeActRejectedOnShadow() {
        KillSwitchEngine.Resolved r = KillSwitchEngine.resolve("act", "c3_shadow");
        assertEquals(KillSwitchEngine.Mode.ACT, r.requested);
        assertNotEquals(KillSwitchEngine.Mode.ACT, r.effective);
        assertEquals(KillSwitchEngine.Mode.LOG, r.effective);
        assertNotNull(r.warn);
        assertTrue(r.warn.contains("TU CHOI"));
        // profile tat / khac c3_live cung bi tu choi
        assertEquals(KillSwitchEngine.Mode.LOG, KillSwitchEngine.resolve("ACT", null).effective);
        assertEquals(KillSwitchEngine.Mode.LOG, KillSwitchEngine.resolve("act", "c3_shadowX").effective);
    }

    @Test
    public void modeActOnLiveNotImplementedInV11d() {
        assertFalse(KillSwitchEngine.ACT_IMPLEMENTED);
        KillSwitchEngine.Resolved r = KillSwitchEngine.resolve("act", "c3_live");
        assertEquals(KillSwitchEngine.Mode.LOG, r.effective);
        assertTrue(r.warn.contains("CHUA cai"));
    }

    @Test
    public void modeGarbageIsOffWithWarn() {
        KillSwitchEngine.Resolved r = KillSwitchEngine.resolve("on", "c3_shadow");
        assertEquals(KillSwitchEngine.Mode.OFF, r.effective);
        assertNotNull(r.warn);
    }

    // ------------------------------------------------------------ detector bien nguong
    @Test
    public void c1Bounds() {
        assertFalse(KillSwitchEngine.c1Lag(180));
        assertTrue(KillSwitchEngine.c1Lag(181));
        assertFalse(KillSwitchEngine.c1Missing(100, 10));
        assertTrue(KillSwitchEngine.c1Missing(100, 11));
        assertFalse(KillSwitchEngine.c1Missing(738, 73));   // 9,89 %
        assertTrue(KillSwitchEngine.c1Missing(738, 74));    // 10,03 %
        assertFalse(KillSwitchEngine.c1Missing(0, 0));
        assertFalse(KillSwitchEngine.c1NoData(240));
        assertTrue(KillSwitchEngine.c1NoData(241));
        long ref = 1_792_000_020_000L - (1_792_000_020_000L % 60_000L);
        assertEquals(180L, KillSwitchEngine.lagSec(ref + 60_000L + 180_000L, ref));
        assertEquals(6L, KillSwitchEngine.lagSec(ref + 66_000L, ref));
    }

    @Test
    public void c2Bounds() {
        assertNull(KillSwitchEngine.c2Slip(null, 100d));   // so giay: khong co fill that => N/A
        assertNull(KillSwitchEngine.c2Slip(100d, null));
        assertNull(KillSwitchEngine.c2Slip(100d, 0d));
        assertFalse(KillSwitchEngine.c2(null));
        assertFalse(KillSwitchEngine.c2(0.025));
        assertTrue(KillSwitchEngine.c2(0.0250001));
        assertTrue(KillSwitchEngine.c2(KillSwitchEngine.c2Slip(97.4, 100d)));
        assertFalse(KillSwitchEngine.c2(KillSwitchEngine.c2Slip(102.4, 100d)));
    }

    @Test
    public void c3Bounds() {
        assertFalse(KillSwitchEngine.c3(4));
        assertTrue(KillSwitchEngine.c3(5));
    }

    @Test
    public void c4Bounds() {
        assertFalse(KillSwitchEngine.c4(90, 0f, 35000f, 0.6f));
        assertTrue(KillSwitchEngine.c4(91, 0f, 35000f, 0.6f));
        assertTrue(KillSwitchEngine.c4(10, 6f, 10f, 0.6f));     // U = 0,6 = U_MAX
        assertFalse(KillSwitchEngine.c4(10, 5.9f, 10f, 0.6f));
        assertFalse(KillSwitchEngine.c4(10, 6f, 0f, 0.6f));     // equity <= 0 => khong tinh U
    }

    @Test
    public void c5Bounds() {
        assertFalse(KillSwitchEngine.c5(300));
        assertTrue(KillSwitchEngine.c5(301));
    }

    @Test
    public void c6Bounds() {
        assertTrue(KillSwitchEngine.c6(KillSwitchEngine.dd(60, 100)));      // dung -40 %
        assertTrue(KillSwitchEngine.c6(KillSwitchEngine.dd(6, 10)));
        assertFalse(KillSwitchEngine.c6(KillSwitchEngine.dd(60.01, 100)));
        assertTrue(KillSwitchEngine.c6(-0.41));
        assertFalse(KillSwitchEngine.c6(-0.3999));
        assertEquals(0.0, KillSwitchEngine.dd(10, 0), 0.0);
    }

    // ------------------------------------------------------------ C1 tren cua so ticker
    private static List<KlineObjectSimple> k(long startMs) {
        KlineObjectSimple o = new KlineObjectSimple();
        o.startTime = startMs;
        o.priceClose = 1f;
        return Collections.singletonList(o);
    }

    @Test
    public void c1ScanCountsUniverseAndMissingReadOnly() {
        long m = 29_866_666L * 60_000L;   // moc phut
        Map<String, List<KlineObjectSimple>> w = new HashMap<>();
        w.put("BTCUSDT", k(m + 347));      // startTime lech ms nhu live
        for (int i = 0; i < 9; i++) w.put("S" + i + "USDT", k(m + 120));
        w.put("STALEUSDT", k(m - 60_000L));          // thieu phut hien tai => missing
        w.put("DEADUSDT", k(m - 61 * 60_000L));      // ngoai universe 60'
        w.put("NULLUSDT", Collections.emptyList());
        Map<String, List<KlineObjectSimple>> ro = Collections.unmodifiableMap(w);
        long[] r = KillSwitchEngine.c1Scan(ro, "BTCUSDT");
        assertEquals(m, r[0]);
        assertEquals(11L, r[1]);
        assertEquals(1L, r[2]);
        assertEquals(13, w.size());
        assertArrayEquals(new long[]{-1, 0, 0}, KillSwitchEngine.c1Scan(Collections.emptyMap(), "BTCUSDT"));
        assertArrayEquals(new long[]{-1, 0, 0}, KillSwitchEngine.c1Scan(null, "BTCUSDT"));
    }

    // ------------------------------------------------------------ may trang thai (log-only)
    @Test
    public void c1LagEdgeRepeatClear() {
        ListSink s = new ListSink();
        KillSwitchEngine e = engine(s, null);
        long ref = T0 - (T0 % 60_000L);
        Map<String, List<KlineObjectSimple>> w = new HashMap<>();
        w.put("BTCUSDT", k(ref));
        e.onMarketData(ref + 66_000L, w);   // lag 6 s
        assertFalse(e.active("C1"));
        assertEquals(0, s.count("WOULD_TRIGGER"));
        e.onMarketData(ref + 60_000L + 181_000L, w);   // lag 181 s
        assertTrue(e.active("C1"));
        assertEquals(1, s.count("WOULD_TRIGGER code=C1"));
        assertEquals(1, s.count("edge=START"));
        e.onMarketData(ref + 60_000L + 200_000L, w);   // < 60 s sau => khong log them
        assertEquals(1, s.count("WOULD_TRIGGER code=C1"));
        assertEquals(2L, e.metTotal("C1"));
        e.onMarketData(ref + 60_000L + 242_000L, w);   // >= 60 s => CONT
        assertEquals(1, s.count("edge=CONT"));
        Map<String, List<KlineObjectSimple>> w2 = new HashMap<>();
        w2.put("BTCUSDT", k(ref + 240_000L));
        e.onMarketData(ref + 60_000L + 245_000L, w2);  // nen moi => lag 5 s
        assertFalse(e.active("C1"));
        assertEquals(1, s.count("CLEAR code=C1"));
        assertEquals(1L, e.edgesTotal("C1"));
        for (String l : s.lines) if (l.contains("WOULD_TRIGGER")) assertTrue(l.contains("mode=log"));
    }

    @Test
    public void c1NoDataWhenNoMarketTick() {
        ListSink s = new ListSink();
        KillSwitchEngine e = engine(s, null);
        e.periodic(T0 + 240_000L);
        assertFalse(e.active("C1"));
        e.periodic(T0 + 241_000L);
        assertTrue(e.active("C1"));
        assertEquals(1, s.count("NO_DATA"));
        // thieu BTC trong cua so cung khong lam moi du lieu
        e.onMarketData(T0 + 250_000L, new HashMap<>());
        assertTrue(e.active("C1"));
    }

    @Test
    public void c3ConsecutiveApiErrors() {
        ListSink s = new ListSink();
        KillSwitchEngine e = engine(s, null);
        for (int i = 0; i < 4; i++) e.onApiResult(T0 + i * 60_000L, "positionRisk", false);
        assertFalse(e.active("C3"));
        e.onApiResult(T0 + 4 * 60_000L, "positionRisk", false);
        assertTrue(e.active("C3"));
        e.onApiResult(T0 + 5 * 60_000L, "positionRisk", true);
        assertFalse(e.active("C3"));
        for (int i = 0; i < 4; i++) e.onApiResult(T0 + (6 + i) * 60_000L, "positionRisk", false);
        assertFalse("dem lien tiep reset sau 1 lan OK", e.active("C3"));
    }

    @Test
    public void c5NoTick() {
        ListSink s = new ListSink();
        KillSwitchEngine e = engine(s, null);
        e.onTickStart(T0);
        e.periodic(T0 + 300_000L);
        assertFalse(e.active("C5"));
        e.periodic(T0 + 301_000L);
        assertTrue(e.active("C5"));
        e.onTickStart(T0 + 310_000L);
        assertFalse(e.active("C5"));
        assertEquals(1, s.count("CLEAR code=C5"));
    }

    @Test
    public void c4AndC6OnPaperBook() {
        ListSink s = new ListSink();
        KillSwitchEngine e = engine(s, null);
        e.onPaper(T0, 4, 100f, 35088f);
        assertEquals(35088d, e.peak(), 1e-6);
        assertFalse(e.active("C4"));
        assertFalse(e.active("C6"));
        e.onPaper(T0 + 10_000L, 91, 100f, 35088f);
        assertTrue(e.active("C4"));
        e.onPaper(T0 + 20_000L, 10, 13000f, 21100f);   // U = 0,616 >= 0,6 => C4; dd -39,87 % => chua C6
        assertTrue(e.active("C4"));
        assertFalse(e.active("C6"));
        e.onPaper(T0 + 30_000L, 10, 100f, 21000f);            // dd -40,15 %
        assertTrue(e.active("C6"));
        assertFalse(e.active("C4"));
        assertTrue(s.count("WOULD_TRIGGER code=C6") >= 1);
        assertTrue(s.lines.stream().anyMatch(l -> l.contains("code=C6") && l.contains("CLOSE_ALL+HALT")));
    }

    @Test
    public void peakFloorIsPaperEquity() {
        ListSink s = new ListSink();
        KillSwitchEngine e = engine(s, null);
        e.onPaper(T0, 0, 0f, 30000f);
        assertEquals(35000d, e.peak(), 1e-9);
        assertFalse(e.active("C6"));
        e.onPaper(T0 + 1000L, 0, 0f, 20999f);   // 20999/35000-1 = -0,40003
        assertTrue(e.active("C6"));
    }

    @Test
    public void peakPersistsAcrossRestart() throws Exception {
        File f = new File(tmp.getRoot(), "run/killsw_peak");
        assertTrue(f.getParentFile().mkdirs());
        ListSink s1 = new ListSink();
        KillSwitchEngine e1 = engine(s1, f);
        e1.onPaper(T0, 2, 10f, 36000f);
        assertTrue(f.exists());
        assertEquals(36000d, Double.parseDouble(new String(Files.readAllBytes(f.toPath())).trim()), 1e-9);
        ListSink s2 = new ListSink();
        KillSwitchEngine e2 = engine(s2, f);
        assertEquals(36000d, e2.peak(), 1e-9);
        e2.onPaper(T0 + 1000L, 2, 10f, 21500f);   // 21500/36000-1 = -0,4028
        assertTrue(e2.active("C6"));
        assertEquals(1, s2.count("nap dinh equity"));
    }

    @Test
    public void hourlySummaryAndReset() {
        ListSink s = new ListSink();
        long t = ZonedDateTime.of(2026, 10, 21, 14, 59, 50, 0, ZoneId.of("Asia/Ho_Chi_Minh")).toInstant().toEpochMilli();
        KillSwitchEngine e = new KillSwitchEngine(KillSwitchEngine.Mode.LOG, "log", s, null, () -> 0d, () -> 0.6f, t);
        for (int i = 0; i < 5; i++) e.onApiResult(t + i, "positionRisk", false);
        assertEquals(1L, e.metHour("C3"));
        e.onApiResult(t + 15_000L, "positionRisk", false);   // 15:00:05 => lan gio
        assertEquals(1, s.count("HOURLY hour=2026-10-21T14+07"));
        String h = s.lines.stream().filter(l -> l.contains("HOURLY")).findFirst().get();
        assertTrue(h, h.contains("C3=1/1"));
        assertTrue(h, h.contains("C2=NA"));
        assertEquals(1L, e.metHour("C3"));   // lan dat o gio moi
    }

    @Test
    public void allLinesAreLogOnlyWording() {
        ListSink s = new ListSink();
        KillSwitchEngine e = engine(s, null);
        e.periodic(T0 + 400_000L);   // C1 no_data + C5
        for (String l : s.lines) {
            if (l.contains("[KILLSW]") && !l.contains("HOURLY") && !l.contains("CLEAR")) {
                assertTrue(l, l.contains("WOULD_TRIGGER"));
            }
        }
        assertTrue(e.active("C1"));
        assertTrue(e.active("C5"));
    }
}
