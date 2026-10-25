package com.binance.chuyennd.ops;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.util.*;

import static org.junit.Assert.*;

/**
 * [V12 MASTER 10-25] c3_live (ACT): C1/C5 tu go latch sau 30' LIEN TUC sach + Telegram; C2/C3/C4/C6/A40 giu latch toi khi
 * owner reset; autoReleaseMs=0 (mac dinh Params) = hanh vi v1.2/safe; mode LOG khong doi.
 */
public class KillSwitchAutoReleaseTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_792_900_000_000L;
    static final long M = 60_000L;

    static final class ListSink implements KillSwitchEngine.Sink {
        final List<String> lines = new ArrayList<>();
        public void info(String m) { lines.add("I " + m); }
        public void warn(String m) { lines.add("W " + m); }
    }

    private KillSwitchEngine.Params prm(long autoMs) {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.latchFile = new File(tmp.getRoot(), "run/killsw_latch.json");
        p.resetFile = new File(tmp.getRoot(), "run/killsw_reset.req");
        p.autoReleaseMs = autoMs;
        return p;
    }

    private KillSwitchEngine act(ListSink s, long autoMs, List<String> alerts, long now) {
        KillSwitchEngine e = new KillSwitchEngine(KillSwitchEngine.Mode.ACT, "act", s, null, () -> 10000d, () -> 0.60f, now,
                prm(autoMs));
        e.setAlert(alerts::add);
        return e;
    }

    private static Map<String, List<KlineObjectSimple>> window(long btcStart) {
        Map<String, List<KlineObjectSimple>> w = new HashMap<>();
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = btcStart;
        w.put("BTCUSDT", new ArrayList<>(Collections.singletonList(k)));
        return w;
    }

    /** 1 phut sach: tick + du lieu tuoi + periodic. */
    private static void cleanMinute(KillSwitchEngine e, long t) {
        e.onTickStart(t);
        e.onMarketData(t, window(t - M));
        e.periodic(t);
    }

    @Test
    public void c1AutoReleasesAfter30CleanMinutesAndTimerResetsOnRecurrence() {
        ListSink s = new ListSink();
        List<String> alerts = new ArrayList<>();
        KillSwitchEngine e = act(s, 30 * M, alerts, T0);
        e.onTickStart(T0);
        e.onMarketData(T0, window(T0 - 5 * M));   // lag 240 s > 180 => C1
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, e.requiredAction());
        long t = T0;
        for (int i = 1; i <= 20; i++) cleanMinute(e, t = T0 + i * M);
        // tai phat C1 o phut 20 => dong ho dem lai
        e.onMarketData(t, window(t - 5 * M));
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, e.requiredAction());
        long t1 = t;
        for (int i = 1; i <= 29; i++) cleanMinute(e, t1 + i * M);
        assertEquals("29' sach => chua go", KillSwitchEngine.Action.NO_NEW_ENTRY, e.requiredAction());
        cleanMinute(e, t1 + 31 * M);
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        assertTrue(e.allowNewEntry("XUSDT"));
        assertTrue(alerts.stream().anyMatch(m -> m.contains("AUTO_RELEASE codes=[C1]")));
        // persist: restart => khong latch
        KillSwitchEngine r = act(new ListSink(), 30 * M, new ArrayList<>(), t1 + 32 * M);
        assertEquals(KillSwitchEngine.Action.NONE, r.requiredAction());
    }

    @Test
    public void c5AutoReleasesButC3Stays() {
        ListSink s = new ListSink();
        List<String> alerts = new ArrayList<>();
        KillSwitchEngine e = act(s, 30 * M, alerts, T0);
        e.onMarketData(T0, window(T0 - M));
        e.periodic(T0 + 6 * M);   // khong tick > 300 s => C5 (C1 no_data cung dat)
        assertTrue(e.latchCodes().contains("C5"));
        for (int i = 0; i < 5; i++) e.onApiResult(T0 + 6 * M, "positions", false);   // C3
        assertTrue(e.latchCodes().contains("C3"));
        for (int i = 7; i <= 50; i++) {
            cleanMinute(e, T0 + i * M);
            e.onApiResult(T0 + i * M, "positions", true);
        }
        assertEquals(Collections.singleton("C3"), e.latchCodes());
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, e.requiredAction());
        assertTrue(alerts.stream().anyMatch(m -> m.contains("AUTO_RELEASE") && m.contains("C5") && m.contains("con [C3]")));
    }

    @Test
    public void flattenCodesNeverAutoRelease() {
        KillSwitchEngine e = act(new ListSink(), 30 * M, new ArrayList<>(), T0);
        e.onAccountEquity(T0, 10_000d);
        e.onAccountEquity(T0, 5_000d);   // A40
        assertEquals(KillSwitchEngine.Action.FLATTEN, e.requiredAction());
        e.onAccountEquity(T0 + M, 10_000d);
        for (int i = 2; i <= 90; i++) cleanMinute(e, T0 + i * M);
        assertEquals(KillSwitchEngine.Action.FLATTEN, e.requiredAction());
    }

    @Test
    public void autoReleaseOffKeepsV12SafeBehaviour() {
        KillSwitchEngine e = act(new ListSink(), 0L, new ArrayList<>(), T0);
        e.onMarketData(T0, window(T0 - 5 * M));
        for (int i = 1; i <= 90; i++) cleanMinute(e, T0 + i * M);
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, e.requiredAction());
        assertEquals(Collections.singleton("C1"), e.latchCodes());
    }

    @Test
    public void latchLoadedFromFileAutoReleasesAfter30MinFromStart() {
        KillSwitchEngine e = act(new ListSink(), 30 * M, new ArrayList<>(), T0);
        e.onMarketData(T0, window(T0 - 5 * M));
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, e.requiredAction());
        long t = T0 + 10 * M;
        KillSwitchEngine r = act(new ListSink(), 30 * M, new ArrayList<>(), t);   // restart
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, r.requiredAction());
        for (int i = 1; i <= 30; i++) cleanMinute(r, t + i * M);
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, r.requiredAction());   // dem tu periodic dau tien
        cleanMinute(r, t + 32 * M);
        assertEquals(KillSwitchEngine.Action.NONE, r.requiredAction());
    }

    @Test
    public void opsConfigActSets30MinDefaultOnlyForAct() {
        assertEquals(30 * M, OpsConfig.killSwitchParams(true).autoReleaseMs);
        assertEquals(0L, OpsConfig.killSwitchParams(false).autoReleaseMs);
    }
}
