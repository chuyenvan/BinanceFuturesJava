package com.binance.chuyennd.ops;

import com.binance.chuyennd.c3live.recon.Reconciler;
import org.junit.Before;
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
 * [V12 2c CRIT-1] c3_live: C6 tinh tren totalMarginBalance THAT so voi dinh RIENG (run/c3live_killsw_peak), KHONG san
 * PAPER_EQUITY, KHONG doc/ghi run/killsw_peak cua c3_shadow; reset_peak=1 dat lai dinh rieng. Dung engine qua DUNG duong
 * {@link OpsHooks#build} (nhu OpsHooks.newEngine). Gom ban hoi quy cua ProofKs (A1_AUDIT_V12 §4).
 */
public class KillSwitchC3LivePeakTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_793_000_000_000L;
    File shadowPeak;
    File ownPeak;
    long shadowMtime;
    final List<String> lines = new ArrayList<>();
    final List<String> alerts = new ArrayList<>();
    final KillSwitchEngine.Sink sink = new KillSwitchEngine.Sink() {
        public void info(String m) { lines.add("I " + m); }
        public void warn(String m) { lines.add("W " + m); }
    };

    @Before
    public void setUp() throws Exception {
        File run = new File(tmp.getRoot(), "run");
        assertTrue(run.mkdirs());
        shadowPeak = new File(run, "killsw_peak");                 // = run/killsw_peak tren 242 (c3_shadow da ghi)
        Files.write(shadowPeak.toPath(), "35015.29\n".getBytes(StandardCharsets.UTF_8));
        assertTrue(shadowPeak.setLastModified(1_700_000_000_000L));
        shadowMtime = shadowPeak.lastModified();
        ownPeak = new File(run, "c3live_killsw_peak");
    }

    /** Tham so y nhu OpsConfig.killSwitchParams(act=true). */
    private KillSwitchEngine.Params actParams() {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.latchFile = new File(tmp.getRoot(), "run/killsw_latch.json");
        p.resetFile = new File(tmp.getRoot(), "run/killsw_reset.req");
        p.autoReleaseMs = 30 * 60_000L;
        p.autoReleaseCodes.add("C3");
        p.c4Capacity = true;
        return p;
    }

    /** Duong that c3_live: PAPER_EQUITY=35000 + file dinh shadow 35015.29 co san. */
    private KillSwitchEngine c3live(long now) {
        KillSwitchEngine e = OpsHooks.build(KillSwitchEngine.Mode.ACT, "act", sink, true, shadowPeak, ownPeak, () -> 35_000d,
                () -> 0.6f, now, actParams());
        e.setAlert(alerts::add);
        return e;
    }

    private void writeReset(int resetPeak) throws Exception {
        // dung dinh dang ops/killsw_reset.sh ghi
        Files.write(new File(tmp.getRoot(), "run/killsw_reset.req").toPath(),
                ("{\"reset_at_ms\":" + T0 + ",\"reset_by\":\"owner\",\"reset_peak\":" + resetPeak + "}\n")
                        .getBytes(StandardCharsets.UTF_8));
    }

    /** File dinh c3_live: "<dinh> adapter=<nhan>" (2d MIN-19). */
    private double ownPeakValue() throws Exception {
        String s = new String(Files.readAllBytes(ownPeak.toPath()), StandardCharsets.UTF_8).trim();
        assertTrue("file dinh c3_live phai co nhan adapter: " + s, s.contains(" adapter="));
        return Double.parseDouble(s.split("\\s+")[0]);
    }

    private KillSwitchEngine c3liveTagged(long now, String adapter, KillSwitchEngine.Params p) {
        p.peakTag = adapter;
        return OpsHooks.build(KillSwitchEngine.Mode.ACT, "act", sink, true, shadowPeak, ownPeak, () -> 35_000d, () -> 0.6f,
                now, p);
    }

    // ------------------------------------------------------------------ [2d MIN-19] dinh dry KHONG dung cho tien that
    @Test
    public void dryPeaksIgnoredWhenAdapterChangesToLive() throws Exception {
        KillSwitchEngine dry = c3liveTagged(T0, "dry", actParams());
        dry.onPaper(T0, 0, 0f, 12_000f);          // dinh C6 dry = 12 000 (tmb gia lap)
        dry.onAccountEquity(T0, 12_000d);         // acct_peak A40 dry = 12 000 (ghi vao file latch)
        assertEquals(12_000d, ownPeakValue(), 1e-9);
        String ownTxt = new String(Files.readAllBytes(ownPeak.toPath()), StandardCharsets.UTF_8);
        assertTrue(ownTxt, ownTxt.trim().endsWith("adapter=dry"));
        String latchTxt = new String(Files.readAllBytes(new File(tmp.getRoot(), "run/killsw_latch.json").toPath()),
                StandardCharsets.UTF_8);
        assertTrue(latchTxt, latchTxt.contains("\"acct_peak_adapter\":\"dry\""));
        // cung adapter => nap lai
        KillSwitchEngine dry2 = c3liveTagged(T0 + 1_000L, "dry", actParams());
        assertEquals(12_000d, dry2.peak(), 1e-9);
        assertEquals(12_000d, dry2.acctPeak(), 1e-9);
        // chuyen sang live (tmb that 10 000): dinh dry BO QUA + WARN => KHONG latch C6/A40
        lines.clear();
        KillSwitchEngine live = c3liveTagged(T0 + 2_000L, "live", actParams());
        assertTrue(Double.isNaN(live.peak()));
        assertTrue(Double.isNaN(live.acctPeak()));
        assertTrue(lines.toString(), lines.stream().anyMatch(l -> l.startsWith("W") && l.contains("adapter=dry")
                && l.contains("adapter hien tai live") && l.contains("BO QUA")));
        live.onPaper(T0 + 3_000L, 0, 0f, 10_000f);
        live.onAccountEquity(T0 + 3_000L, 10_000d);
        assertEquals(KillSwitchEngine.Action.NONE, live.requiredAction());
        assertEquals(10_000d, live.peak(), 1e-9);
        assertEquals(10_000d, live.acctPeak(), 1e-9);
        assertTrue(new String(Files.readAllBytes(ownPeak.toPath()), StandardCharsets.UTF_8).trim().endsWith("adapter=live"));
    }

    @Test
    public void untaggedOldPeakFileIgnoredForC3Live() throws Exception {
        Files.write(ownPeak.toPath(), "35015.29\n".getBytes(StandardCharsets.UTF_8));   // dinh dang cu khong nhan
        KillSwitchEngine e = c3liveTagged(T0, "live", actParams());
        assertTrue(Double.isNaN(e.peak()));
        e.onPaper(T0, 0, 0f, 10_000f);
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
    }

    private void assertShadowFileUntouched() throws Exception {
        assertEquals("35015.29\n", new String(Files.readAllBytes(shadowPeak.toPath()), StandardCharsets.UTF_8));
        assertEquals(shadowMtime, shadowPeak.lastModified());
        for (String l : lines) assertFalse("khong duoc dung file dinh shadow: " + l, l.contains(shadowPeak.getAbsolutePath()));
    }

    // ------------------------------------------------------------------ (a)
    @Test
    public void c3LiveWithShadowPeak35015AndPaperEquity35000NeverLatchesOnTmb10000() throws Exception {
        KillSwitchEngine e = c3live(T0);
        for (int i = 0; i < 20; i++) e.onPaper(T0 + i * 5_000L, 0, 0f, 10_000f);
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        assertTrue(e.latchCodes().isEmpty());
        assertTrue(e.allowNewEntry("BTCUSDT"));
        assertEquals("dinh rieng = tmb dau tien (khong san PAPER_EQUITY)", 10_000d, e.peak(), 1e-9);
        assertTrue(alerts.isEmpty());
        assertTrue("dinh rieng duoc ghi", ownPeak.exists());
        assertEquals(10_000d, ownPeakValue(),
                1e-9);
        assertShadowFileUntouched();
    }

    /** Hoi quy ProofKs (A1): onBook -> reset_peak=1 -> onBook: truoc sua FLATTEN 2 lan; sau sua NONE ca 3 moc. */
    @Test
    public void proofKsRegression() throws Exception {
        KillSwitchEngine ks = c3live(T0);
        ks.onTickStart(T0);
        ks.onPaper(T0 + 15_000L, 0, 0f, 10_000f);
        assertEquals(KillSwitchEngine.Action.NONE, ks.requiredAction());
        assertTrue(ks.allowNewEntry("BTCUSDT"));
        assertTrue(ks.latchCodes().isEmpty());
        writeReset(1);
        ks.onTickStart(T0 + 20_000L);
        ks.periodic(T0 + 20_000L);
        assertEquals(KillSwitchEngine.Action.NONE, ks.requiredAction());
        ks.onPaper(T0 + 30_000L, 0, 0f, 10_000f);
        assertEquals(KillSwitchEngine.Action.NONE, ks.requiredAction());
        assertTrue(ks.latchCodes().isEmpty());
        assertShadowFileUntouched();
        // phan Reconciler cua ProofKs (MAJ-1): truoc startup() => CHAN
        Reconciler r = new Reconciler(null, null, null, null, null, null, () -> 0L, 0.01, 2, null);
        assertFalse(r.allowsEntry("BTCUSDT"));
        assertTrue(r.blocks().containsKey(Reconciler.BLOCK_STARTUP));
    }

    /** Doi chung: day noi CU (dinh so giay + san PAPER_EQUITY) o ACT => FLATTEN ngay (dung loi A1 bat duoc). */
    @Test
    public void oldPaperPeakWiringWouldLatchFlattenAsA1Showed() {
        KillSwitchEngine old = OpsHooks.build(KillSwitchEngine.Mode.ACT, "act", sink, false, shadowPeak, ownPeak, () -> 35_000d,
                () -> 0.6f, T0, actParams());
        old.onPaper(T0 + 15_000L, 0, 0f, 10_000f);
        assertEquals(KillSwitchEngine.Action.FLATTEN, old.requiredAction());
        assertTrue(old.latchCodes().contains("C6"));
    }

    // ------------------------------------------------------------------ (b)
    @Test
    public void c6LatchesExactlyAtThresholdAgainstOwnPeak() throws Exception {
        KillSwitchEngine e = c3live(T0);
        e.onPaper(T0, 0, 0f, 10_000f);
        e.onPaper(T0 + 5_000L, 0, 0f, 7_500f);   // -25 %: nguong C6 la -40 % => CHUA latch
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        e.onPaper(T0 + 10_000L, 0, 0f, 6_001f);  // -39,99 %
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        e.onPaper(T0 + 15_000L, 0, 0f, 6_000f);  // -40 % = KillSwitchEngine.C6_DD
        assertEquals(KillSwitchEngine.Action.FLATTEN, e.requiredAction());
        assertTrue(e.latchCodes().contains("C6"));
        assertEquals(1, alerts.size());
        // dinh tang theo tmb that
        KillSwitchEngine e2 = OpsHooks.build(KillSwitchEngine.Mode.ACT, "act", sink, true, shadowPeak,
                new File(tmp.getRoot(), "run/other_peak"), () -> 35_000d, () -> 0.6f, T0, actParams2());
        e2.onPaper(T0, 0, 0f, 10_000f);
        e2.onPaper(T0 + 5_000L, 0, 0f, 12_000f);
        e2.onPaper(T0 + 10_000L, 0, 0f, 7_201f);
        assertEquals(KillSwitchEngine.Action.NONE, e2.requiredAction());
        e2.onPaper(T0 + 15_000L, 0, 0f, 7_200f);   // 12 000 * 0,6
        assertEquals(KillSwitchEngine.Action.FLATTEN, e2.requiredAction());
        assertShadowFileUntouched();
    }

    private KillSwitchEngine.Params actParams2() {
        KillSwitchEngine.Params p = actParams();
        p.latchFile = new File(tmp.getRoot(), "run/killsw_latch2.json");
        p.resetFile = new File(tmp.getRoot(), "run/killsw_reset2.req");
        return p;
    }

    @Test
    public void invalidEquityKeepsC6StateAndPeak() throws Exception {
        KillSwitchEngine e = c3live(T0);
        e.onPaper(T0, 0, 0f, 10_000f);
        e.onPaper(T0 + 5_000L, 0, 0f, 0f);
        e.onPaper(T0 + 10_000L, 0, 0f, Float.NaN);
        e.onPaper(T0 + 15_000L, 0, 0f, -5f);
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        assertEquals(10_000d, e.peak(), 1e-9);
    }

    // ------------------------------------------------------------------ (c)
    @Test
    public void resetPeakResetsOwnPeakAndFile() throws Exception {
        KillSwitchEngine e = c3live(T0);
        e.onPaper(T0, 0, 0f, 10_000f);
        e.onPaper(T0 + 5_000L, 0, 0f, 5_000f);
        assertEquals(KillSwitchEngine.Action.FLATTEN, e.requiredAction());
        // reset_peak=0: latch mo nhung dinh giu => latch lai o onBook ke
        writeReset(0);
        e.onTickStart(T0 + 10_000L);
        e.periodic(T0 + 10_000L);
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        e.onPaper(T0 + 15_000L, 0, 0f, 5_000f);
        assertEquals(KillSwitchEngine.Action.FLATTEN, e.requiredAction());
        assertEquals(10_000d, e.peak(), 1e-9);
        // reset_peak=1 (owner nap/rut von co chu dich): dinh rieng dat lai + file xoa => khong latch lai
        writeReset(1);
        e.onTickStart(T0 + 20_000L);
        e.periodic(T0 + 20_000L);
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        assertTrue(Double.isNaN(e.peak()));
        assertFalse("file dinh rieng da xoa", ownPeak.exists());
        e.onPaper(T0 + 90_000L, 0, 0f, 5_000f);
        assertEquals(KillSwitchEngine.Action.NONE, e.requiredAction());
        assertEquals(5_000d, e.peak(), 1e-9);
        assertTrue(ownPeak.exists());
        assertEquals(5_000d, ownPeakValue(),
                1e-9);
        // restart: nap dinh rieng tu file rieng, KHONG tu file shadow
        KillSwitchEngine r = c3live(T0 + 100_000L);
        assertEquals(5_000d, r.peak(), 1e-9);
        assertShadowFileUntouched();
    }

    // ------------------------------------------------------------------ cau hinh + duong c3_shadow khong doi
    @Test
    public void c3LivePeakFileNeverSharesShadowFile() {
        assertEquals(OpsConfig.DEFAULT_C3LIVE_KILLSW_PEAK_FILE, OpsConfig.c3LivePeakFile(null, null).getPath());
        assertNotEquals(OpsConfig.DEFAULT_KILLSW_STATE_FILE, OpsConfig.DEFAULT_C3LIVE_KILLSW_PEAK_FILE);
        assertEquals(OpsConfig.DEFAULT_C3LIVE_KILLSW_PEAK_FILE, OpsConfig.c3LivePeakFile("run/killsw_peak", null).getPath());
        assertEquals(OpsConfig.DEFAULT_C3LIVE_KILLSW_PEAK_FILE, OpsConfig.c3LivePeakFile("x/p", "x/p").getPath());
        assertEquals("y/q", OpsConfig.c3LivePeakFile("y/q", "x/p").getPath());
    }

    @Test
    public void shadowPathIdenticalToV11Construction() throws Exception {
        List<String> l1 = new ArrayList<>();
        List<String> l2 = new ArrayList<>();
        KillSwitchEngine.Sink s1 = new KillSwitchEngine.Sink() {
            public void info(String m) { l1.add("I " + m); }
            public void warn(String m) { l1.add("W " + m); }
        };
        KillSwitchEngine.Sink s2 = new KillSwitchEngine.Sink() {
            public void info(String m) { l2.add("I " + m); }
            public void warn(String m) { l2.add("W " + m); }
        };
        KillSwitchEngine viaBuild = OpsHooks.build(KillSwitchEngine.Mode.LOG, "log", s1, false, shadowPeak, ownPeak,
                () -> 35_000d, () -> 0.6f, T0, new KillSwitchEngine.Params());
        KillSwitchEngine direct = new KillSwitchEngine(KillSwitchEngine.Mode.LOG, "log", s2, shadowPeak, () -> 35_000d,
                () -> 0.6f, T0, new KillSwitchEngine.Params());
        float[] eq = {34_000f, 36_000f, 20_000f, 10_000f, 36_500f};
        for (int i = 0; i < eq.length; i++) {
            viaBuild.onPaper(T0 + i * 5_000L, i, 100f, eq[i]);
            direct.onPaper(T0 + i * 5_000L, i, 100f, eq[i]);
        }
        assertEquals(l2, l1);
        assertEquals(direct.peak(), viaBuild.peak(), 0d);
        assertEquals(KillSwitchEngine.Action.NONE, viaBuild.requiredAction());
        assertFalse("duong shadow khong tao file dinh c3_live", ownPeak.exists());
    }
}
