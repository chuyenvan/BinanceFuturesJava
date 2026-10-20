package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import org.junit.After;
import org.junit.Test;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.junit.Assert.*;

/**
 * [TS-MKT-EXT v1.1] Luat keo dai time-stop cua SO GIAY + co lap LEGACY + co TAT ⇒ v11b + restart.
 */
public class TsMktExtTest {

    private static final long H = TsMktExt.HOUR;
    private static final long DAY = AltEwIndex.DAY;
    /** 2026-02-01 00:00 UTC. */
    private static final long D0 = LocalDate.of(2026, 2, 1).toEpochDay();

    @After
    public void reset() {
        TsMktExt.enabledForTest = null;
        TsMktExt.legacyCheck = LegacySymbols::isLegacySymbol;
        TsMktExt.setInstanceForTest(null);
    }

    private static Map<String, Float> px(String s, float v) {
        Map<String, Float> m = new HashMap<>();
        m.put(s, v);
        return m;
    }

    private ShadowBookC3 freshBook() {
        ShadowBookC3.resetForTest();
        new File(System.getProperty("user.dir"), "open_positions.csv").delete();
        Configs.properties.putIfAbsent("CAPITAL_START", "35000");
        return ShadowBookC3.getInstance();
    }

    /** Instance khong doc store (reader null), co dat tay theo ngay; startedAt xa => khong co an han khoi dong. */
    private TsMktExt ext(boolean enabled, AltEwIndex.State... perDay) {
        TsMktExt.enabledForTest = enabled;
        TsMktExt x = new TsMktExt(null, null, 0L, 0L);
        for (int i = 0; i < perDay.length; i++) if (perDay[i] != null) x.setFlagForTest(D0 + i, perDay[i]);
        TsMktExt.setInstanceForTest(x);
        return x;
    }

    // ------------------------------------------------------------------ decide
    @Test
    public void decideBoundariesMatchSim() {
        TsMktExt.Flag on = TsMktExt.Flag.ON;
        assertEquals(TsMktExt.Decision.NOT_DUE, TsMktExt.decide(true, false, 168 * H, on));      // sim: age > 168h
        assertEquals(TsMktExt.Decision.DEFER, TsMktExt.decide(true, false, 168 * H + 1, on));
        assertEquals(TsMktExt.Decision.DEFER, TsMktExt.decide(true, false, 504 * H, on));        // sim: age <= 168+336
        assertEquals(TsMktExt.Decision.CUT, TsMktExt.decide(true, false, 504 * H + 1, on));
        assertEquals(TsMktExt.Decision.CUT, TsMktExt.decide(true, false, 200 * H, TsMktExt.Flag.OFF));
        assertEquals(TsMktExt.Decision.DEFER, TsMktExt.decide(true, false, 200 * H, TsMktExt.Flag.PENDING));
        assertEquals(TsMktExt.Decision.CUT, TsMktExt.decide(false, false, 200 * H, on));        // co TAT = v11b
        assertEquals(TsMktExt.Decision.CUT, TsMktExt.decide(true, true, 200 * H, on));          // LEGACY
        assertEquals(TsMktExt.Decision.CUT, TsMktExt.decide(true, true, 200 * H, TsMktExt.Flag.PENDING));
    }

    @Test
    public void enableGateOnlyC3Shadow() {
        assertTrue(TsMktExt.decideEnabled("1", true, false));
        assertTrue(TsMktExt.decideEnabled(" 1 ", true, false));
        assertFalse(TsMktExt.decideEnabled("1", true, true));     // c3_live: khong bat
        assertFalse(TsMktExt.decideEnabled("1", false, false));   // profile tat
        assertFalse(TsMktExt.decideEnabled("0", true, false));
        assertFalse(TsMktExt.decideEnabled(null, true, false));
        assertFalse(TsMktExt.decideEnabled("true", true, false));
        // mac dinh test JVM (khong co env) => TAT
        assertFalse(TsMktExt.enabled());
        assertFalse(TsMktExt.deferTimeStop("AAAUSDT", 0L, 300 * H));
    }

    // ------------------------------------------------------------------ so giay
    /** Lo, co ON tu ngay 169h: khong cat; ngay co tat: cat o nhip DAU TIEN cua ngay do. */
    @Test
    public void loserDeferredWhileFlagOnThenCutWhenOff() {
        AltEwIndex.State[] st = new AltEwIndex.State[20];
        for (int i = 0; i < 20; i++) st[i] = AltEwIndex.State.OFF;
        for (int i = 7; i <= 10; i++) st[i] = AltEwIndex.State.ON;
        ext(true, st);
        ShadowBookC3 b = freshBook();
        long t0 = D0 * DAY + 12 * H;                     // mo 02-01 12:00 UTC
        b.openPos("AAAUSDT", t0, 100f, 1f, 1, 0.1f);
        b.tick(px("AAAUSDT", 80f), t0 + 169 * H);       // 02-08 13:00 (ngay 7: ON) -> hoan
        assertEquals(1, b.openCount());
        b.tick(px("AAAUSDT", 80f), D0 * DAY + 11 * DAY - 1); // 02-11 23:59:59 (ngay 10: ON) -> van hoan
        assertEquals(1, b.openCount());
        b.tick(px("AAAUSDT", 80f), D0 * DAY + 11 * DAY);     // 02-12 00:00 (ngay 11: OFF) -> cat
        assertEquals(0, b.openCount());
    }

    /** "Lo" = CHUA arm (sim khong xet gia): cum dang lai +5 % (< 0.07) cung duoc hoan nhu nhau. */
    @Test
    public void unarmedInProfitAlsoDeferred() {
        AltEwIndex.State[] st = new AltEwIndex.State[30];
        java.util.Arrays.fill(st, AltEwIndex.State.ON);
        ext(true, st);
        ShadowBookC3 b = freshBook();
        long t0 = D0 * DAY;
        b.openPos("BBBUSDT", t0, 100f, 1f, 1, 0.1f);
        b.tick(px("BBBUSDT", 105f), t0 + 200 * H);
        assertEquals(1, b.openCount());
        b.tick(px("BBBUSDT", 105f), t0 + 504 * H);      // dung 504h: con hoan (<=)
        assertEquals(1, b.openCount());
        b.tick(px("BBBUSDT", 105f), t0 + 504 * H + 1000); // qua 504h: cat du co ON
        assertEquals(0, b.openCount());
    }

    /** Co TAT (mac dinh) ⇒ y het v11b: cat o 169h du co ngay do ON. */
    @Test
    public void flagOffEqualsV11b() {
        AltEwIndex.State[] st = new AltEwIndex.State[30];
        java.util.Arrays.fill(st, AltEwIndex.State.ON);
        ext(false, st);
        ShadowBookC3 b = freshBook();
        b.openPos("CCCUSDT", D0 * DAY, 100f, 1f, 1, 0.1f);
        b.tick(px("CCCUSDT", 90f), D0 * DAY + 167 * H);
        assertEquals(1, b.openCount());
        b.tick(px("CCCUSDT", 90f), D0 * DAY + 169 * H);
        assertEquals(0, b.openCount());
    }

    /** LEGACY: ke ca neu lot vao so giay, KHONG bao gio duoc keo dai (cat 169h nhu v11b). */
    @Test
    public void legacyNeverExtended() {
        AltEwIndex.State[] st = new AltEwIndex.State[30];
        java.util.Arrays.fill(st, AltEwIndex.State.ON);
        ext(true, st);
        TsMktExt.legacyCheck = s -> "LEGUSDT".equals(s);
        assertFalse(TsMktExt.deferTimeStop("LEGUSDT", D0 * DAY, D0 * DAY + 200 * H));
        assertTrue(TsMktExt.deferTimeStop("PAPUSDT", D0 * DAY, D0 * DAY + 200 * H));
        ShadowBookC3 b = freshBook();
        b.openPos("LEGUSDT", D0 * DAY, 100f, 1f, 1, 0.1f);
        b.openPos("PAPUSDT", D0 * DAY, 100f, 1f, 1, 0.1f);
        Map<String, Float> p = px("LEGUSDT", 90f);
        p.put("PAPUSDT", 90f);
        b.tick(p, D0 * DAY + 169 * H);
        assertFalse(b.isHolding("LEGUSDT"));
        assertTrue(b.isHolding("PAPUSDT"));
    }

    /**
     * Duong vi the THAT (LEGACY 44) khong tham chieu lop moi: chi ShadowBookC3 (so giay) goi deferTimeStop;
     * BinanceOrderTradingManager khong nhac TsMktExt.
     */
    @Test
    public void realPositionPathDoesNotReferenceTsExt() throws Exception {
        Path root = Paths.get(System.getProperty("user.dir"), "src", "main", "java");
        assertTrue(Files.isDirectory(root));
        List<String> callers;
        try (Stream<Path> s = Files.walk(root)) {
            callers = s.filter(f -> f.toString().endsWith(".java"))
                    .filter(f -> {
                        try {
                            return new String(Files.readAllBytes(f), StandardCharsets.UTF_8).contains("TsMktExt.");
                        } catch (Exception e) {
                            throw new RuntimeException(e);
                        }
                    })
                    .map(f -> f.getFileName().toString()).sorted().collect(Collectors.toList());
        }
        List<String> want = new ArrayList<>();
        want.add("ShadowBookC3.java");
        want.add("TsMktExt.java");
        assertEquals(want, callers);
        String botm = new String(Files.readAllBytes(root.resolve(
                "com/binance/chuyennd/trading/BinanceOrderTradingManager.java")), StandardCharsets.UTF_8);
        assertFalse(botm.contains("TsMktExt"));
        assertFalse(botm.contains("AltEwIndex"));
    }

    /** Da arm trong luc hoan ⇒ ra khoi time-stop, trailing binh thuong; DCA khong doi moc leg dau. */
    @Test
    public void armDuringDeferAndDcaKeepsAnchor() {
        AltEwIndex.State[] st = new AltEwIndex.State[30];
        java.util.Arrays.fill(st, AltEwIndex.State.ON);
        st[12] = AltEwIndex.State.OFF;
        ext(true, st);
        ShadowBookC3 b = freshBook();
        long t0 = D0 * DAY;
        b.openPos("DDDUSDT", t0, 100f, 1f, 1, 0.1f);
        b.tick(px("DDDUSDT", 70f), t0 + 170 * H);
        b.openPos("DDDUSDT", t0 + 180 * H, 50f, 1f, 1, 0.1f);   // DCA: VWAP 75, moc leg dau giu t0
        assertEquals(t0, b.cluster("DDDUSDT").tsFirstLeg);
        b.tick(px("DDDUSDT", 70f), t0 + 12 * DAY);              // ngay 12 OFF: tuoi 288h > 168h -> cat
        assertEquals(0, b.openCount());

        ShadowBookC3 b2 = freshBook();
        b2.openPos("EEEUSDT", t0, 100f, 1f, 1, 0.1f);
        b2.tick(px("EEEUSDT", 95f), t0 + 170 * H);              // hoan
        b2.tick(px("EEEUSDT", 110f), t0 + 171 * H);             // arm
        b2.tick(px("EEEUSDT", 109f), t0 + 12 * DAY + H);        // ngay OFF nhung da arm: khong time-stop
        assertEquals(1, b2.openCount());
    }

    /** PENDING: chua co co hom nay ⇒ giu toi han 00:22 UTC, sau do OFF ⇒ cat. */
    @Test
    public void pendingHoldsUntilDeadline() {
        TsMktExt.enabledForTest = true;
        TsMktExt x = new TsMktExt(null, null, 0L, 0L);
        TsMktExt.setInstanceForTest(x);
        long day = D0 + 8;
        assertEquals(TsMktExt.Flag.PENDING, x.flagFor(day, day * DAY + 5 * 60_000L));
        assertEquals(TsMktExt.Flag.PENDING, x.flagFor(day, day * DAY + TsMktExt.PENDING_MAX_MS - 1));
        assertEquals(TsMktExt.Flag.OFF, x.flagFor(day, day * DAY + TsMktExt.PENDING_MAX_MS));
        ShadowBookC3 b = freshBook();
        b.openPos("FFFUSDT", day * DAY - 170 * H, 100f, 1f, 1, 0.1f);
        b.tick(px("FFFUSDT", 90f), day * DAY + 60_000L);
        assertEquals(1, b.openCount());
        b.tick(px("FFFUSDT", 90f), day * DAY + 30 * 60_000L);
        assertEquals(0, b.openCount());
        // an han khoi dong 20 phut
        TsMktExt y = new TsMktExt(null, null, day * DAY + 5 * H, 0L);
        assertEquals(TsMktExt.Flag.PENDING, y.flagFor(day, day * DAY + 5 * H + 60_000L));
        assertEquals(TsMktExt.Flag.OFF, y.flagFor(day, day * DAY + 5 * H + TsMktExt.START_GRACE_MS));
    }

    // ------------------------------------------------------------------ du lieu / restart
    /** Store gia: AAA/BBB giam deu 2 %/ngay tu D0 (=> ~ −45 % sau 30 ngay), BTC di ngang. */
    private static final class FakeStore implements TsMktExt.MinuteReader {
        int calls = 0;
        boolean missingLast = false;
        long missingTs = -1;

        @Override
        public TreeMap<Long, Map<String, KlineObjectSimple>> read(long startMs, int minutes) {
            calls++;
            TreeMap<Long, Map<String, KlineObjectSimple>> out = new TreeMap<>();
            for (int i = 0; i < minutes; i++) {
                long ts = startMs + i * AltEwIndex.MIN;
                if (missingLast && ts == missingTs) continue;
                Map<String, KlineObjectSimple> m = new HashMap<>();
                double f = Math.exp(-0.02 * (ts - D0 * DAY) / (double) DAY);
                m.put("AAAUSDT", k(ts, 100 * f));
                m.put("BBBUSDT", k(ts, 3 * f));
                m.put("BTCUSDT", k(ts, 60000));
                out.put(ts, m);
            }
            return out;
        }

        private static KlineObjectSimple k(long ts, double c) {
            KlineObjectSimple o = new KlineObjectSimple();
            o.startTime = ts;
            o.priceClose = (float) c;
            o.totalUsdt = 1000f;
            return o;
        }
    }

    @Test
    public void refreshScheduleFileAndRestart() throws Exception {
        File f = File.createTempFile("ts_ext_daily", ".csv");
        f.delete();
        FakeStore st = new FakeStore();
        long today = D0 + 32;
        TsMktExt x = new TsMktExt(st, f, 0L, 0L);
        x.refresh(today * DAY + 2 * 60_000L);                       // truoc 00:03 => chua tinh
        assertNull(x.flagResult(today));
        assertEquals(0, st.calls);
        st.missingLast = true;
        st.missingTs = today * DAY - AltEwIndex.MIN;
        x.refresh(today * DAY + 4 * 60_000L);                       // thieu nen 23:59 => cho
        assertNull(x.flagResult(today));
        assertEquals(1, st.calls);
        st.missingLast = false;
        x.refresh(today * DAY + 5 * 60_000L);                       // du => doc 30 ngay
        AltEwIndex.FlagResult r = x.flagResult(today);
        assertNotNull(r);
        assertEquals(AltEwIndex.State.ON, r.state);
        assertEquals(Math.exp(-0.02 * 30) - 1, r.dd, 2e-3);       // float32 + 1 phut dau thang mat
        assertEquals(31, Files.readAllLines(f.toPath()).size());   // header + 30 ngay

        // RESTART giua ngay: nap file, KHONG doc store, cung co + cung dd (bit-exact)
        TsMktExt.MinuteReader boom = (s, m) -> {
            throw new IllegalStateException("khong duoc doc store sau restart");
        };
        TsMktExt y = new TsMktExt(boom, f, today * DAY + 10 * H, 0L);
        y.refresh(today * DAY + 10 * H + 1000L);
        AltEwIndex.FlagResult r2 = y.flagResult(today);
        assertNotNull(r2);
        assertEquals(r.state, r2.state);
        assertEquals(Double.doubleToLongBits(r.dd), Double.doubleToLongBits(r2.dd));
        assertEquals(0, y.readCalls);
        f.delete();
    }

    /** Qua han 00:20 ma van thieu nen 23:59 => tinh voi phan co (ngay van >= 1296 phut). */
    @Test
    public void finalPassComputesWithoutLastMinute() throws Exception {
        File f = File.createTempFile("ts_ext_daily2", ".csv");
        f.delete();
        FakeStore st = new FakeStore();
        long today = D0 + 32;
        st.missingLast = true;
        st.missingTs = today * DAY - AltEwIndex.MIN;
        TsMktExt x = new TsMktExt(st, f, 0L, 0L);
        x.refresh(today * DAY + 21 * 60_000L);
        AltEwIndex.FlagResult r = x.flagResult(today);
        assertNotNull(r);
        assertEquals(AltEwIndex.State.ON, r.state);
        assertEquals(1439, x.days.get(today - 1).n);
        f.delete();
    }
}
