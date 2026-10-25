package com.binance.chuyennd.ops;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.*;

/**
 * [V12 SAFE C8] kill-switch ACT (c3_live): moi C1–C6 + A40 mot kich ban mock => dung hanh dong; c3_shadow (mode log)
 * => 0 hanh dong; latch song qua restart; reset chi qua file yeu cau owner; C2 co dau sau co.
 */
public class KillSwitchActTest {

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

    private static final long T0 = ZonedDateTime.of(2026, 10, 25, 14, 10, 0, 0, ZoneId.of("Asia/Ho_Chi_Minh"))
            .toInstant().toEpochMilli();
    private static final long H = 3_600_000L;

    private File latchF() {
        return new File(tmp.getRoot(), "run/killsw_latch.json");
    }

    private File resetF() {
        return new File(tmp.getRoot(), "run/killsw_reset.req");
    }

    private KillSwitchEngine.Params prm(boolean signed) {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.c2Signed = signed;
        p.latchFile = latchF();
        p.resetFile = resetF();
        return p;
    }

    private KillSwitchEngine act(ListSink s, boolean signed, long now) {
        return new KillSwitchEngine(KillSwitchEngine.Mode.ACT, "act", s, null, () -> 10000d, () -> 0.60f, now, prm(signed));
    }

    /** Mode HIEU LUC cua c3_shadow khi owner go act (bi tu choi => LOG), CUNG file latch de chung minh khong I/O. */
    private KillSwitchEngine shadow(ListSink s, boolean signed, long now) {
        KillSwitchEngine.Resolved r = KillSwitchEngine.resolve("act", "c3_shadow");
        assertEquals(KillSwitchEngine.Mode.LOG, r.effective);
        return new KillSwitchEngine(r.effective, "log(act_tu_choi)", s, null, () -> 10000d, () -> 0.60f, now, prm(signed));
    }

    private static Map<String, List<KlineObjectSimple>> window(long btcStart) {
        Map<String, List<KlineObjectSimple>> w = new HashMap<>();
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = btcStart;
        w.put("BTCUSDT", new ArrayList<>(Collections.singletonList(k)));
        return w;
    }

    private static void assertAction(KillSwitchEngine e, KillSwitchEngine.Action a) {
        assertEquals(a, e.requiredAction());
        assertEquals(a == KillSwitchEngine.Action.NONE, e.allowNewEntry("XUSDT"));
    }

    // ------------------------------------------------------------ chinh sach mode
    @Test
    public void actOnlyOnC3Live() {
        assertTrue(KillSwitchEngine.ACT_IMPLEMENTED);
        KillSwitchEngine.Resolved live = KillSwitchEngine.resolve("act", "c3_live");
        assertEquals(KillSwitchEngine.Mode.ACT, live.effective);
        assertNull(live.warn);
        assertEquals(KillSwitchEngine.Mode.LOG, KillSwitchEngine.resolve("act", "c3_shadow").effective);
        assertEquals(KillSwitchEngine.Mode.LOG, KillSwitchEngine.resolve("act", null).effective);
        assertEquals(KillSwitchEngine.Mode.LOG, KillSwitchEngine.resolve("log", "c3_live").effective);
    }

    // ------------------------------------------------------------ C1..C6 + A40: dung hanh dong
    @Test
    public void c1DataLagLatchesNoNewEntry() {
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, false, T0);
        assertAction(e, KillSwitchEngine.Action.NONE);
        e.onMarketData(T0, window(T0 - 5 * 60_000L));   // tuoi nen 240 s > 180
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
        assertEquals(Collections.singleton("C1"), e.latchCodes());
        assertEquals(1, s.count("LATCH action=NO_NEW_ENTRY"));
        assertEquals(1, s.count("TRIGGER code=C1"));
        assertEquals(0, s.count("WOULD_TRIGGER"));
        // dieu kien het => latch VAN GIU (chi owner mo)
        e.onMarketData(T0 + 60_000L, window(T0));
        assertFalse(e.active("C1"));
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
    }

    @Test
    public void c2SignedThreeAdverseIn24hLatches() {
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, true, T0);
        e.onFill(T0, "AUSDT", true, 103.0, 100.0);          // +3 % bat loi
        e.onFill(T0 + H, "BUSDT", true, 102.6, 100.0);      // +2,6 %
        assertAction(e, KillSwitchEngine.Action.NONE);
        assertEquals(2, e.c2EventCount());
        e.onFill(T0 + 2 * H, "CUSDT", true, 102.0, 100.0);  // +2 %: chi canh bao
        assertAction(e, KillSwitchEngine.Action.NONE);
        assertEquals(3, s.count("C2_WARN"));
        e.onFill(T0 + 3 * H, "DUSDT", false, 97.0, 100.0);  // BAN 1 - 0,97 = +3 % bat loi
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
        assertEquals(Collections.singleton("C2"), e.latchCodes());
    }

    @Test
    public void c2SignedIgnoresFavorableAndWindowExpires() {
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, true, T0);
        for (int i = 0; i < 5; i++) e.onFill(T0 + i * 60_000L, "AUSDT", true, 95.0, 100.0);   // -5 %: CO LOI
        assertEquals(0, e.c2EventCount());
        assertEquals(0, s.count("C2_WARN"));
        assertAction(e, KillSwitchEngine.Action.NONE);
        e.onFill(T0, "AUSDT", true, 103.0, 100.0);
        e.onFill(T0 + H, "AUSDT", true, 103.0, 100.0);
        e.onFill(T0 + 24 * H + 30 * 60_000L, "AUSDT", true, 103.0, 100.0);   // su kien dau (T0) het cua so 24h
        assertEquals(2, e.c2EventCount());
        assertAction(e, KillSwitchEngine.Action.NONE);
        assertEquals(0.025, KillSwitchEngine.c2Adverse(true, 102.5, 100.0), 1e-12);
        assertTrue(KillSwitchEngine.c2Adverse(false, 103.0, 100.0) < 0);
        assertNull(KillSwitchEngine.c2Adverse(true, Double.NaN, 100.0));
        assertNull(KillSwitchEngine.c2Adverse(true, 1.0, null));
    }

    @Test
    public void c2FlagOffKeepsV11AbsFormula() {
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, false, T0);
        e.onFill(T0, "AUSDT", true, 97.0, 100.0);   // |-3 %| > 2,5 % => C2 dat ngay (cong thuc v1.1), du co loi
        assertTrue(e.active("C2"));
        assertEquals(0, s.count("C2_WARN"));
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
        // 4 tham so (duong v1.1) == 5 tham so khi co tat
        KillSwitchEngine a = new KillSwitchEngine(KillSwitchEngine.Mode.LOG, "log", new ListSink(), null, () -> 0d, () -> 0.6f, T0);
        a.onFill(T0, "A", 102.4, 100.0);
        assertFalse(a.active("C2"));
        a.onFill(T0, "A", 102.6, 100.0);
        assertTrue(a.active("C2"));
    }

    @Test
    public void c3ApiErrorsLatch() {
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, false, T0);
        for (int i = 0; i < 4; i++) e.onApiResult(T0 + i, "order", false);
        assertAction(e, KillSwitchEngine.Action.NONE);
        e.onApiResult(T0 + 5, "order", false);
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
        assertEquals(Collections.singleton("C3"), e.latchCodes());
    }

    @Test
    public void c4ExposureLatch() {
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, false, T0);
        e.onPaper(T0, 90, 100f, 10000f);
        assertAction(e, KillSwitchEngine.Action.NONE);
        e.onPaper(T0 + 1000L, 91, 100f, 10000f);
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
        assertEquals(Collections.singleton("C4"), e.latchCodes());
    }

    @Test
    public void c5NoTickLatch() {
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, false, T0);
        e.onMarketData(T0 + 299_000L, window(T0 + 239_000L - 60_000L));   // giu C1 sach
        e.periodic(T0 + 299_000L);
        assertAction(e, KillSwitchEngine.Action.NONE);
        e.onMarketData(T0 + 301_000L, window(T0 + 240_000L - 60_000L));
        e.periodic(T0 + 301_000L);
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
        assertEquals(Collections.singleton("C5"), e.latchCodes());
    }

    @Test
    public void c6BookDrawdownFlattens() {
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, false, T0);
        e.onPaper(T0, 3, 100f, 10000f);
        e.onPaper(T0 + 1000L, 3, 100f, 6001f);
        assertAction(e, KillSwitchEngine.Action.NONE);
        e.onPaper(T0 + 2000L, 3, 100f, 5999f);
        assertAction(e, KillSwitchEngine.Action.FLATTEN);
        assertEquals(Collections.singleton("C6"), e.latchCodes());
        assertEquals(1, s.count("LATCH action=FLATTEN"));
    }

    @Test
    public void a40AccountEquityFlattens() {
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, false, T0);
        AtomicReference<Double> eq = new AtomicReference<>(9977.89);
        e.attachEquitySource(eq::get);
        e.periodic(T0 + 1000L);
        eq.set(12000.0);
        e.periodic(T0 + 2000L);
        assertEquals(12000.0, e.acctPeak(), 1e-9);
        eq.set(7201.0);                                   // -39,99 %
        e.periodic(T0 + 3000L);
        assertAction(e, KillSwitchEngine.Action.NONE);
        eq.set(null);                                     // loi API: giu trang thai, khong latch
        e.periodic(T0 + 4000L);
        assertAction(e, KillSwitchEngine.Action.NONE);
        assertEquals(1, s.count("A40 equity khong co"));
        eq.set(7199.0);                                   // -40,01 %
        e.periodic(T0 + 5000L);
        assertAction(e, KillSwitchEngine.Action.FLATTEN);
        assertEquals(Collections.singleton("A40"), e.latchCodes());
        assertTrue(s.lines.stream().anyMatch(l -> l.contains("TRIGGER code=A40") && l.contains("CLOSE_ALL+HALT")));
    }

    @Test
    public void escalationNoNewEntryToFlattenAndNeverDowngrades() {
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, false, T0);
        for (int i = 0; i < 5; i++) e.onApiResult(T0 + i, "order", false);
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
        e.onPaper(T0 + 10L, 1, 1f, 10000f);
        e.onPaper(T0 + 20L, 1, 1f, 5000f);
        assertAction(e, KillSwitchEngine.Action.FLATTEN);
        assertEquals(new LinkedHashSet<>(Arrays.asList("C3", "C6")), e.latchCodes());
        for (int i = 0; i < 5; i++) e.onApiResult(T0 + 30 + i, "order", false);
        assertAction(e, KillSwitchEngine.Action.FLATTEN);
    }

    // ------------------------------------------------------------ c3_shadow: 0 hanh dong, 0 I/O latch
    @Test
    public void shadowNeverActsAndWritesNoLatchFile() {
        ListSink s = new ListSink();
        KillSwitchEngine e = shadow(s, true, T0);
        AtomicReference<Double> eq = new AtomicReference<>(10000.0);
        e.attachEquitySource(eq::get);
        e.periodic(T0 + 1L);                                                  // dinh equity that 10000
        e.onMarketData(T0, window(T0 - 10 * 60_000L));                        // C1
        for (int i = 0; i < 3; i++) e.onFill(T0 + i, "A", true, 110.0, 100.0);    // C2
        for (int i = 0; i < 6; i++) e.onApiResult(T0 + i, "x", false);         // C3
        e.onPaper(T0, 95, 100f, 10000f);                                      // C4
        e.onPaper(T0 + 1, 95, 100f, 1000f);                                   // C6
        eq.set(10.0);
        e.periodic(T0 + 400_000L);                                            // C5 + A40
        for (String c : new String[]{"C1", "C2", "C3", "C4", "C5", "C6", "A40"}) assertTrue(c, e.active(c));
        assertAction(e, KillSwitchEngine.Action.NONE);
        assertTrue(e.latchCodes().isEmpty());
        assertFalse(latchF().exists());
        assertEquals(0, s.count("LATCH"));
        for (String l : s.lines) {
            if (l.contains("TRIGGER")) assertTrue(l, l.contains("WOULD_TRIGGER"));
        }
    }

    // ------------------------------------------------------------ persist / restart / reset owner
    @Test
    public void latchSurvivesRestart() {
        KillSwitchEngine e1 = act(new ListSink(), false, T0);
        for (int i = 0; i < 5; i++) e1.onApiResult(T0 + i, "order", false);
        assertTrue(latchF().exists());
        ListSink s2 = new ListSink();
        KillSwitchEngine e2 = act(s2, false, T0 + H);   // JVM moi
        assertAction(e2, KillSwitchEngine.Action.NO_NEW_ENTRY);
        assertEquals(Collections.singleton("C3"), e2.latchCodes());
        assertEquals(1, s2.count("NAP LATCH"));
        // A40/FLATTEN cung song qua restart
        KillSwitchEngine e3 = act(new ListSink(), false, T0 + 2 * H);
        e3.onPaper(T0 + 2 * H, 1, 1f, 10000f);
        e3.onPaper(T0 + 2 * H + 1, 1, 1f, 100f);
        KillSwitchEngine e4 = act(new ListSink(), false, T0 + 3 * H);
        assertAction(e4, KillSwitchEngine.Action.FLATTEN);
    }

    @Test
    public void c2EventsAndAccountPeakSurviveRestart() {
        KillSwitchEngine e1 = act(new ListSink(), true, T0);
        e1.attachEquitySource(() -> 12000.0);
        e1.periodic(T0 + 1000L);
        e1.onFill(T0 + 2000L, "A", true, 103.0, 100.0);
        e1.onFill(T0 + 3000L, "B", true, 103.0, 100.0);
        KillSwitchEngine e2 = act(new ListSink(), true, T0 + H);
        assertEquals(2, e2.c2EventCount());
        assertEquals(12000.0, e2.acctPeak(), 1e-9);
        e2.onFill(T0 + H + 1, "C", true, 103.0, 100.0);
        assertAction(e2, KillSwitchEngine.Action.NO_NEW_ENTRY);
        KillSwitchEngine e3 = act(new ListSink(), true, T0 + 2 * H);
        e3.attachEquitySource(() -> 7100.0);   // 7100/12000-1 = -40,8 % so dinh DA LUU
        e3.periodic(T0 + 2 * H + 1000L);
        assertAction(e3, KillSwitchEngine.Action.FLATTEN);
    }

    private void writeReset(long at, int resetPeak) throws Exception {
        Files.write(resetF().toPath(), ("{\"reset_at_ms\":" + at + ",\"reset_by\":\"owner\",\"reset_peak\":" + resetPeak + "}\n")
                .getBytes(StandardCharsets.UTF_8));
    }

    @Test
    public void ownerResetClearsLatchWithoutRestartAndConditionRelatches() throws Exception {
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, true, T0);
        for (int i = 0; i < 3; i++) e.onFill(T0 + i, "A", true, 103.0, 100.0);
        for (int i = 0; i < 5; i++) e.onApiResult(T0 + i, "order", false);
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
        // xoa file latch tay KHONG mo latch (engine ghi lai)
        assertTrue(latchF().delete());
        e.periodic(T0 + 10_000L);
        assertTrue(latchF().exists());
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
        writeReset(T0 + 20_000L, 0);
        e.periodic(T0 + 30_000L);
        assertAction(e, KillSwitchEngine.Action.NONE);
        assertEquals(0, e.c2EventCount());
        assertFalse(resetF().exists());
        assertEquals(1, s.count("RESET boi owner"));
        String js = new String(Files.readAllBytes(latchF().toPath()), StandardCharsets.UTF_8);
        assertTrue(js, js.contains("\"latch\":\"NONE\""));
        assertEquals(KillSwitchEngine.Action.NONE, act(new ListSink(), true, T0 + H).requiredAction());
        // dieu kien con dat (loi API tiep) => latch lai ngay
        e.onApiResult(T0 + 40_000L, "order", false);
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
    }

    @Test
    public void resetPeakRebaselinesAccountPeak() throws Exception {
        KillSwitchEngine e = act(new ListSink(), false, T0);
        AtomicReference<Double> eq = new AtomicReference<>(10000.0);
        e.attachEquitySource(eq::get);
        e.periodic(T0 + 1000L);
        eq.set(5000.0);
        e.periodic(T0 + 2000L);
        assertAction(e, KillSwitchEngine.Action.FLATTEN);
        writeReset(T0 + 3000L, 0);                       // giu dinh => van -50 % => latch lai
        e.periodic(T0 + 4000L);
        assertAction(e, KillSwitchEngine.Action.FLATTEN);
        writeReset(T0 + 5000L, 1);                       // owner chu dich dat lai dinh
        e.periodic(T0 + 6000L);
        assertAction(e, KillSwitchEngine.Action.NONE);
        assertEquals(5000.0, e.acctPeak(), 1e-9);
    }

    @Test
    public void resetRequestAppliedAtStartupWhenJvmWasDown() throws Exception {
        KillSwitchEngine e1 = act(new ListSink(), false, T0);
        for (int i = 0; i < 5; i++) e1.onApiResult(T0 + i, "order", false);
        writeReset(T0 + H, 0);
        KillSwitchEngine e2 = act(new ListSink(), false, T0 + 2 * H);
        assertAction(e2, KillSwitchEngine.Action.NONE);
    }

    @Test
    public void corruptLatchFileFailsClosed() throws Exception {
        assertTrue(latchF().getParentFile().mkdirs());
        Files.write(latchF().toPath(), "{latch: ???".getBytes(StandardCharsets.UTF_8));
        ListSink s = new ListSink();
        KillSwitchEngine e = act(s, false, T0);
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
        assertEquals(Collections.singleton(KillSwitchEngine.CODE_STATE), e.latchCodes());
        assertEquals(1, s.count("FAIL-CLOSED file latch"));
        File[] bak = latchF().getParentFile().listFiles((d, n) -> n.startsWith("killsw_latch.json.corrupt_"));
        assertNotNull(bak);
        assertEquals(1, bak.length);
        // file hop le da duoc ghi lai => restart van latch STATE
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, act(new ListSink(), false, T0 + 1).requiredAction());
    }

    @Test
    public void invalidResetRequestIsIgnored() throws Exception {
        KillSwitchEngine e = act(new ListSink(), false, T0);
        for (int i = 0; i < 5; i++) e.onApiResult(T0 + i, "order", false);
        Files.write(resetF().toPath(), "khong phai json".getBytes(StandardCharsets.UTF_8));
        e.periodic(T0 + 1000L);
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
        assertFalse(resetF().exists());
    }

    @Test
    public void alertCalledOnLatchAndExceptionIsSwallowed() {
        KillSwitchEngine e = act(new ListSink(), false, T0);
        List<String> got = new ArrayList<>();
        e.setAlert(m -> {
            got.add(m);
            throw new RuntimeException("telegram down");
        });
        for (int i = 0; i < 5; i++) e.onApiResult(T0 + i, "order", false);
        assertEquals(1, got.size());
        assertTrue(got.get(0).contains("LATCH action=NO_NEW_ENTRY"));
        assertAction(e, KillSwitchEngine.Action.NO_NEW_ENTRY);
    }

    @Test
    public void hourlyLineUnchangedWithoutEquitySourceInLogMode() {
        ListSink s = new ListSink();
        KillSwitchEngine e = new KillSwitchEngine(KillSwitchEngine.Mode.LOG, "log", s, null, () -> 0d, () -> 0.6f, T0,
                new KillSwitchEngine.Params());
        String h = e.hourlyLine("2026-10-25T14+07");
        assertFalse(h, h.contains("A40"));
        assertFalse(h, h.contains("latch"));
        assertFalse(h, h.contains("acct_"));
        KillSwitchEngine old = new KillSwitchEngine(KillSwitchEngine.Mode.LOG, "log", s, null, () -> 0d, () -> 0.6f, T0);
        assertEquals(old.hourlyLine("x"), e.hourlyLine("x"));
    }
}
