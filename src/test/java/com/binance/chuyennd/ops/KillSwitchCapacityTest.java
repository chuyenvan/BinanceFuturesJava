package com.binance.chuyennd.ops;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

/**
 * [V12 vong 2b MASTER 10-25] C4 = dieu kien CONG SUAT (khong latch; chan MO CUM MOI, DCA van chay; tu go khi vi the <= 85
 * va U <= U_MAX - 0,05) + C3 tu go sau 30' sach + >= 3 call API OK lien tiep; C2/C6/A40 van giu latch.
 * Mac dinh Params (c4Capacity=false) = hanh vi v1.2 vong 2a (C4 latch) — khong doi test cu.
 */
public class KillSwitchCapacityTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_792_900_000_000L;
    static final long MIN = 60_000L;

    static final class Sink implements KillSwitchEngine.Sink {
        final List<String> lines = new ArrayList<>();
        public void info(String m) { lines.add("I " + m); }
        public void warn(String m) { lines.add("W " + m); }
    }

    private KillSwitchEngine.Params params(boolean capacity) {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.latchFile = new File(tmp.getRoot(), "run/killsw_latch.json");
        p.resetFile = new File(tmp.getRoot(), "run/killsw_reset.req");
        p.autoReleaseMs = 30 * MIN;
        if (capacity) {
            p.c4Capacity = true;
            p.autoReleaseCodes.add("C3");
        }
        return p;
    }

    private KillSwitchEngine engine(KillSwitchEngine.Params p, Sink s, List<String> alerts) {
        KillSwitchEngine e = new KillSwitchEngine(KillSwitchEngine.Mode.ACT, "act", s, null, () -> 10_000d, () -> 0.60f, T0, p);
        e.setAlert(alerts::add);
        return e;
    }

    @Test
    public void c4CapacityBlocksNewClustersNotDcaWithHysteresis() {
        Sink s = new Sink();
        List<String> alerts = new ArrayList<>();
        KillSwitchEngine e = engine(params(true), s, alerts);
        e.onPaper(T0, 91, 1000f, 10_000f);
        assertFalse("vi the > 90 => chan mo cum moi", e.allowNewEntry("AUSDT"));
        assertTrue("DCA cum dang co van chay", e.allowDca("AUSDT"));
        assertEquals("C4 KHONG latch", KillSwitchEngine.Action.NONE, e.requiredAction());
        assertTrue(e.latchCodes().isEmpty());
        assertTrue(e.capacityBlocked());
        assertEquals(1, alerts.size());
        e.onPaper(T0 + MIN, 88, 1000f, 10_000f);
        assertFalse("tre: 88 > 85 => van chan", e.allowNewEntry("AUSDT"));
        e.onPaper(T0 + 2 * MIN, 85, 1000f, 10_000f);
        assertTrue("<= 85 va U thap => go", e.allowNewEntry("AUSDT"));
        assertEquals(2, alerts.size());
        // theo U: 0,60 => chan; 0,57 => van chan (tre 0,05); 0,55 => go
        e.onPaper(T0 + 3 * MIN, 10, 6000f, 10_000f);
        assertFalse(e.allowNewEntry("AUSDT"));
        assertTrue(e.allowDca("AUSDT"));
        e.onPaper(T0 + 4 * MIN, 10, 5700f, 10_000f);
        assertFalse(e.allowNewEntry("AUSDT"));
        e.onPaper(T0 + 5 * MIN, 10, 5500f, 10_000f);
        assertTrue(e.allowNewEntry("AUSDT"));
        assertFalse("khong co file latch C4", new File(tmp.getRoot(), "run/killsw_latch.json").exists()
                && new String(read(new File(tmp.getRoot(), "run/killsw_latch.json"))).contains("C4"));
    }

    @Test
    public void latchStillBlocksDca() {
        Sink s = new Sink();
        List<String> alerts = new ArrayList<>();
        KillSwitchEngine e = engine(params(true), s, alerts);
        for (int i = 0; i < 5; i++) e.onApiResult(T0, "newMarketOrder", false);
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, e.requiredAction());
        assertFalse(e.allowNewEntry("AUSDT"));
        assertFalse("latch (C3) chan ca DCA", e.allowDca("AUSDT"));
    }

    @Test
    public void c3AutoReleaseNeeds30minCleanAnd3ConsecutiveOk() {
        Sink s = new Sink();
        List<String> alerts = new ArrayList<>();
        KillSwitchEngine e = engine(params(true), s, alerts);
        for (int i = 0; i < 5; i++) e.onApiResult(T0, "newMarketOrder", false);
        assertTrue(e.latchCodes().contains("C3"));
        e.onApiResult(T0 + MIN, "positions", true);   // het dat C3, 1 OK
        periodicHealthy(e, T0 + MIN);
        periodicHealthy(e, T0 + 32 * MIN);
        assertTrue("30' sach nhung moi 1 call OK => giu", e.latchCodes().contains("C3"));
        e.onApiResult(T0 + 33 * MIN, "positions", true);
        e.onApiResult(T0 + 33 * MIN, "positions", true);
        periodicHealthy(e, T0 + 33 * MIN);
        assertFalse("30' sach + 3 OK lien tiep => go", e.latchCodes().contains("C3"));
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        assertTrue(alerts.stream().anyMatch(a -> a.contains("AUTO_RELEASE")));
    }

    @Test
    public void c3ErrorBetweenOksResetsCounter() {
        Sink s = new Sink();
        KillSwitchEngine e = engine(params(true), s, new ArrayList<>());
        for (int i = 0; i < 5; i++) e.onApiResult(T0, "newMarketOrder", false);
        e.onApiResult(T0 + MIN, "a", true);
        periodicHealthy(e, T0 + MIN);
        e.onApiResult(T0 + 40 * MIN, "a", true);
        e.onApiResult(T0 + 40 * MIN, "a", false);   // loi le (chua du 5) => dem OK ve 0
        e.onApiResult(T0 + 40 * MIN, "a", true);
        e.onApiResult(T0 + 40 * MIN, "a", true);
        periodicHealthy(e, T0 + 40 * MIN);
        assertTrue(e.latchCodes().contains("C3"));
        e.onApiResult(T0 + 41 * MIN, "a", true);
        periodicHealthy(e, T0 + 41 * MIN);
        assertFalse(e.latchCodes().contains("C3"));
    }

    @Test
    public void c2c6a40StillLatchUntilOwner() {
        Sink s = new Sink();
        KillSwitchEngine.Params p = params(true);
        p.c2Signed = true;
        KillSwitchEngine e = engine(p, s, new ArrayList<>());
        for (int i = 0; i < 3; i++) e.onFill(T0 + i, "AUSDT", true, 1.03, 1.0);
        assertTrue(e.latchCodes().contains("C2"));
        periodicHealthy(e, T0 + 120 * MIN);
        assertTrue("C2 khong tu go", e.latchCodes().contains("C2"));
        e.onPaper(T0 + 121 * MIN, 1, 100f, 5_000f);   // DD -50 % tu dinh 10 000
        assertEquals(KillSwitchEngine.Action.FLATTEN, e.requiredAction());
        periodicHealthy(e, T0 + 300 * MIN);
        assertEquals(KillSwitchEngine.Action.FLATTEN, e.requiredAction());
    }

    @Test
    public void legacyLatchFileWithC4IsDroppedInCapacityMode() throws Exception {
        File f = new File(tmp.getRoot(), "run/killsw_latch.json");
        f.getParentFile().mkdirs();
        Files.write(f.toPath(), "{\"version\":1,\"latch\":\"NO_NEW_ENTRY\",\"codes\":[\"C4\"],\"since_ms\":1,\"detail\":\"x\"}"
                .getBytes(StandardCharsets.UTF_8));
        KillSwitchEngine e = engine(params(true), new Sink(), new ArrayList<>());
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        assertTrue(e.allowNewEntry("AUSDT"));
    }

    @Test
    public void defaultParamsKeepC4Latch() {
        KillSwitchEngine e = engine(params(false), new Sink(), new ArrayList<>());
        e.onPaper(T0, 91, 1000f, 10_000f);
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, e.requiredAction());
        assertTrue(e.latchCodes().contains("C4"));
        assertFalse(e.allowDca("AUSDT"));
    }

    @Test
    public void logModeUnchanged() {
        KillSwitchEngine e = new KillSwitchEngine(KillSwitchEngine.Mode.LOG, "log", new Sink(), null, () -> 10_000d,
                () -> 0.60f, T0, params(true));
        e.onPaper(T0, 95, 9000f, 10_000f);
        assertTrue(e.allowNewEntry("AUSDT"));
        assertTrue(e.allowDca("AUSDT"));
        assertFalse(e.capacityBlocked());
    }

    @Test
    public void opsConfigActEnablesCapacityAndC3Release() {
        KillSwitchEngine.Params act = OpsConfig.killSwitchParams(true);
        assertTrue(act.c4Capacity);
        assertTrue(act.autoReleaseCodes.contains("C3"));
        assertTrue(act.autoReleaseCodes.contains("C1") && act.autoReleaseCodes.contains("C5"));
        assertFalse(act.autoReleaseCodes.contains("C2") || act.autoReleaseCodes.contains("C6")
                || act.autoReleaseCodes.contains("A40"));
        assertEquals(3, act.c3ReleaseOkConsec);
        KillSwitchEngine.Params log = OpsConfig.killSwitchParams(false);
        assertFalse(log.c4Capacity);
        assertFalse(log.autoReleaseCodes.contains("C3"));
    }


    /** periodic sau 1 tick + 1 cua so du lieu BTC tuoi (C1/C5 sach) — nhu luong that. */
    static void periodicHealthy(KillSwitchEngine e, long t) {
        e.onTickStart(t);
        java.util.Map<String, java.util.List<com.binance.chuyennd.object.sw.KlineObjectSimple>> w = new java.util.HashMap<>();
        com.binance.chuyennd.object.sw.KlineObjectSimple k = new com.binance.chuyennd.object.sw.KlineObjectSimple();
        k.startTime = t - 60_000L;
        k.priceOpen = 1f;
        k.priceClose = 1f;
        k.maxPrice = 1f;
        k.minPrice = 1f;
        w.put("BTCUSDT", java.util.Collections.singletonList(k));
        e.onMarketData(t, w);
        e.periodic(t);
    }

    private static byte[] read(File f) {
        try {
            return Files.readAllBytes(f.toPath());
        } catch (Exception e) {
            return new byte[0];
        }
    }
}
