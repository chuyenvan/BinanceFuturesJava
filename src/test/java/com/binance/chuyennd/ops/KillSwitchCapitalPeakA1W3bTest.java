package com.binance.chuyennd.ops;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

import static org.junit.Assert.*;

/** [W3B v2] Test doi khang A1_W3B muc 7 (a1_w3b/A1W3bPeakAdvTest) dua vao bo chinh. Sua ky vong co giai thich: t05/t06/t08 (dinh TAM), t14 (co tat van ghi cap=). */
public class KillSwitchCapitalPeakA1W3bTest {
    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();
    static final long T0 = 1_795_000_000_000L;
    static final long H = 3_600_000L;
    final List<String> warns = new CopyOnWriteArrayList<>();
    final KillSwitchEngine.Sink sink = new KillSwitchEngine.Sink() {
        public void info(String m) { }
        public void warn(String m) { warns.add(m); }
    };
    File dir, ownPeak, latch, eqState;

    @Before
    public void setUp() throws Exception {
        dir = tmp.newFolder();
        ownPeak = new File(dir, "c3live_killsw_peak");
        latch = new File(dir, "killsw_latch.json");
        eqState = new File(dir, "c3live_equity_c3.json");
    }

    KillSwitchEngine.Params params() {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.latchFile = latch;
        p.resetFile = new File(dir, "killsw_reset.req");
        p.autoReleaseMs = 30 * 60_000L;
        p.autoReleaseCodes.add("C3");
        p.c4Capacity = true;
        return p;
    }

    KillSwitchEngine newJar(long now, String cap, String flag) {
        KillSwitchEngine.Params p = params();
        OpsHooks.applyC3PeakTag(p, "live", cap, null, flag, eqState);
        return OpsHooks.build(KillSwitchEngine.Mode.ACT, "act", sink, true, new File(dir, "killsw_peak"), ownPeak,
                () -> 35_000d, () -> 0.6f, now, p);
    }

    KillSwitchEngine oldJar(long now) {
        KillSwitchEngine.Params p = params();
        p.peakTag = "live_c3eq";
        return OpsHooks.build(KillSwitchEngine.Mode.ACT, "act", sink, true, new File(dir, "killsw_peak"), ownPeak,
                () -> 35_000d, () -> 0.6f, now, p);
    }

    void eqState(String adapter, double cap) throws Exception {
        Files.write(eqState.toPath(), ("{\"adapter\":\"" + adapter + "\",\"start_ms\":1,\"capital\":" + cap
                + ",\"funding_cum\":0.0,\"income_last_ms\":1,\"income_last_ids\":[]}").getBytes(StandardCharsets.UTF_8));
    }

    static void eq(KillSwitchEngine e, long t, double v) {
        e.onPaper(t, 0, 0f, (float) v);
        e.onAccountEquity(t, v);
    }

    long capWarns() {
        return warns.stream().filter(w -> w.contains("BO QUA vi von")).count();
    }

    long quarantined() {
        File[] fs = dir.listFiles((d, n) -> n.startsWith("c3live_killsw_peak.bo_qua_"));
        return fs == null ? 0 : fs.length;
    }

    String read(File f) throws Exception {
        return new String(Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8);
    }

    // ---------- 1(b): sau khi jar moi da ghi cap=, file equity mat/hong KHONG duoc lam mat moc DD
    @Test
    public void t01_steady_eqFileMissing_ddThat_flatten() throws Exception {
        KillSwitchEngine a = newJar(T0, "1000", null);
        eq(a, T0, 1_200d);
        assertTrue(read(ownPeak), read(ownPeak).contains("cap=1000"));
        assertFalse(eqState.exists());
        KillSwitchEngine b = newJar(T0 + H, "1000", null);
        assertEquals(1_200d, b.peak(), 1e-9);
        eq(b, T0 + H + 1_000L, 600d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, b.requiredAction());
        assertEquals(0, capWarns());
    }

    @Test
    public void t02_steady_eqFileCorrupt_ddThat_flatten() throws Exception {
        KillSwitchEngine a = newJar(T0, "1000", null);
        eq(a, T0, 1_200d);
        Files.write(eqState.toPath(), "{hong".getBytes(StandardCharsets.UTF_8));
        KillSwitchEngine b = newJar(T0 + H, "1000", null);
        eq(b, T0 + H + 1_000L, 600d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, b.requiredAction());
    }

    @Test
    public void t03_steady_eqFileOtherAdapterStaleCap_ddThat_flatten() throws Exception {
        KillSwitchEngine a = newJar(T0, "1000", null);
        eq(a, T0, 1_200d);
        eqState("dry", 10_000d);
        KillSwitchEngine b = newJar(T0 + H, "1000", null);
        eq(b, T0 + H + 1_000L, 600d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, b.requiredAction());
    }

    /** crash-loop 10 lan (1/gio), file equity mat: dinh + acct_peak giu, khong canh bao lap, DD that cuoi => FLATTEN. */
    @Test
    public void t04_crashLoop10_eqMissing_peakKept_noSpam() throws Exception {
        KillSwitchEngine a = newJar(T0, "1000", null);
        eq(a, T0, 1_200d);
        for (int i = 1; i <= 10; i++) {
            KillSwitchEngine k = newJar(T0 + i * H, "1000", null);
            assertEquals("restart " + i, 1_200d, k.peak(), 1e-9);
            assertEquals("restart " + i, 1_200d, k.acctPeak(), 1e-9);
            eq(k, T0 + i * H + 1_000L, 1_000d);
            assertEquals(KillSwitchEngine.Action.NONE, k.requiredAction());
        }
        KillSwitchEngine z = newJar(T0 + 11 * H, "1000", null);
        eq(z, T0 + 11 * H + 1_000L, 600d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, z.requiredAction());
        assertEquals(0, capWarns());
    }

    // ---------- 1(b): lan DOI JAR (file dinh dang cu, thieu cap)
    /**
     * [v2 SUA KY VONG] A1 ghi nhan fail-open (NONE + cach ly). W3B v2: dinh dang cu = dinh TAM (KHONG mat dinh khi von khong
     * doi), lan danh gia dau DD -50 % => KHONG FLATTEN (khong phan biet lo that vs doi von, xem t08) nhung FAIL-CLOSED:
     * latch NO_NEW_ENTRY code=STATE + canh bao; khong cach ly.
     */
    @Test
    public void t05_transition_eqMissing_failClosedNoNewEntry() throws Exception {
        KillSwitchEngine old = oldJar(T0);
        eq(old, T0, 1_200d);
        assertFalse(read(ownPeak).contains("cap="));
        KillSwitchEngine n = newJar(T0 + H, "1000", null);
        assertEquals("dinh TAM giu", 1_200d, n.peak(), 1e-9);
        eq(n, T0 + H + 1_000L, 600d);
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, n.requiredAction());
        assertTrue(n.latchCodes().toString(), n.latchCodes().contains(KillSwitchEngine.CODE_STATE));
        assertTrue("phai canh bao", warns.stream().anyMatch(w -> w.contains("KHONG phan biet duoc lo that")));
        assertEquals(0, quarantined());
    }

    /** [v2 SUA KY VONG] restart 6 lan (chet truoc equity dau, file equity mat) => dinh TAM GIU moi lan, 0 canh bao, 0 cach ly. */
    @Test
    public void t06_transition_restarts_peakKept_noSpam() throws Exception {
        KillSwitchEngine old = oldJar(T0);
        eq(old, T0, 1_200d);
        for (int i = 1; i <= 6; i++) {
            KillSwitchEngine k = newJar(T0 + i * H, "1000", null);
            assertEquals("restart " + i, 1_200d, k.peak(), 1e-9);
            assertEquals("restart " + i, 1_200d, k.acctPeak(), 1e-9);
        }
        assertEquals(0, capWarns());
        assertEquals(0, warns.size());
        assertEquals(0, quarantined());
    }

    /** doi jar OK (von chung minh), JVM moi chet TRUOC equity dau tien, roi file equity mat => dinh van phai giu. */
    @Test
    public void t07_transitionAccepted_dieBeforeRewrite_thenEqMissing_peakKept() throws Exception {
        KillSwitchEngine old = oldJar(T0);
        eq(old, T0, 1_200d);
        eqState("live", 1_000d);
        KillSwitchEngine n1 = newJar(T0 + H, "1000", null);
        assertEquals(1_200d, n1.peak(), 1e-9);
        Files.delete(eqState.toPath());
        KillSwitchEngine n2 = newJar(T0 + 2 * H, "1000", null);
        assertEquals("cua so: dinh mat neu JVM chet truoc lan ghi lai", 1_200d, n2.peak(), 1e-9);
    }

    /**
     * [v2 SUA KY VONG] file equity CU (capital = von moi) + dinh dang cu do JVM von KHAC ghi => KHONG FLATTEN gia (yeu cau
     * cot loi cua A1 dat). Ky vong A1 "NONE" doi thanh NO_NEW_ENTRY (code STATE + canh bao): du lieu nay GIONG HET t05 (lo
     * that -50 % luc doi jar, von khong doi) - khong the vua NONE o t08 vua chan o t05; chon fail-closed chan mo moi.
     */
    @Test
    public void t08_staleEqCapital_giam_noFalseFlatten() throws Exception {
        KillSwitchEngine old = oldJar(T0);
        eq(old, T0, 10_000d);
        eqState("live", 1_000d);
        KillSwitchEngine n = newJar(T0 + H, "1000", null);
        eq(n, T0 + H + 1_000L, 1_000d);
        assertNotEquals(KillSwitchEngine.Action.FLATTEN, n.requiredAction());
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, n.requiredAction());
        assertEquals("moc DD dat lai = equity", 1_000d, n.peak(), 1e-9);
        // restart sau: file da ghi lai kem cap => khong canh bao lai, khong FLATTEN
        long w = warns.size();
        KillSwitchEngine n2 = newJar(T0 + 2 * H, "1000", null);
        eq(n2, T0 + 2 * H + 1_000L, 1_000d);
        assertNotEquals(KillSwitchEngine.Action.FLATTEN, n2.requiredAction());
        assertTrue(warns.subList((int) w, warns.size()).stream().noneMatch(x -> x.contains("KHONG phan biet")));
    }

    @Test
    public void t09_capFormat_equivalence() throws Exception {
        KillSwitchEngine a = newJar(T0, "1000.0", null);
        eq(a, T0, 1_200d);
        assertTrue(read(ownPeak), read(ownPeak).trim().endsWith("cap=1000"));
        KillSwitchEngine b = newJar(T0 + H, "1e3", null);
        assertEquals(1_200d, b.peak(), 1e-9);
        KillSwitchEngine c = newJar(T0 + 2 * H, " 1000 ", null);
        assertEquals(1_200d, c.peak(), 1e-9);
    }

    @Test
    public void t10_w3aTagForm() throws Exception {
        Files.write(ownPeak.toPath(), "1200.0 adapter=live_c3eq_cap1000\n".getBytes(StandardCharsets.UTF_8));
        KillSwitchEngine a = newJar(T0, "1000", null);
        assertEquals(1_200d, a.peak(), 1e-9);
        eq(a, T0 + 1_000L, 600d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, a.requiredAction());
        setUp();
        Files.write(ownPeak.toPath(), "1200.0 adapter=live_c3eq_cap1000\n".getBytes(StandardCharsets.UTF_8));
        KillSwitchEngine b = newJar(T0, "10000", null);
        assertTrue(Double.isNaN(b.peak()));
    }

    @Test
    public void t11_crlfAndExtraTokens() throws Exception {
        Files.write(ownPeak.toPath(), "1200.0 adapter=live_c3eq cap=1000\r\n".getBytes(StandardCharsets.UTF_8));
        KillSwitchEngine a = newJar(T0, "1000", null);
        assertEquals(1_200d, a.peak(), 1e-9);
    }

    /** doi von 1000->10000, JVM chet truoc equity dau tien 3 lan => so canh bao (moi restart 1 lan / file) - ky vong <=2 tong. */
    @Test
    public void t12_capChanged_restartsBeforeFirstEquity_alertCount() throws Exception {
        KillSwitchEngine a = newJar(T0, "1000", null);
        eq(a, T0, 1_200d);
        for (int i = 1; i <= 3; i++) newJar(T0 + i * H, "10000", null);
        assertTrue("canh bao lap moi restart: " + capWarns(), capWarns() <= 2);
    }

    @Test
    public void t13_tang_thenRestart_loadsNewPeak_ddFlatten() throws Exception {
        KillSwitchEngine a = newJar(T0, "1000", null);
        eq(a, T0, 1_200d);
        KillSwitchEngine b = newJar(T0 + H, "10000", null);
        eq(b, T0 + H + 1_000L, 10_000d);
        KillSwitchEngine c = newJar(T0 + 2 * H, "10000", null);
        assertEquals(10_000d, c.peak(), 1e-9);
        assertEquals(10_000d, c.acctPeak(), 1e-9);
        eq(c, T0 + 2 * H + 1_000L, 5_000d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, c.requiredAction());
    }

    /** co tat roi bat lai, file equity con => dinh giu; file equity mat => (ghi nhan) */
    @Test
    public void t14_flagOffThenOn_eqPresent_peakKept() throws Exception {
        KillSwitchEngine a = newJar(T0, "1000", null);
        eq(a, T0, 1_200d);
        KillSwitchEngine off = newJar(T0 + H, "1000", "false");
        eq(off, T0 + H + 1_000L, 1_300d);
        // [v2 SUA] co tat van GHI cap= (jar cu bo qua token) => bat lai co khong gap dinh thieu von
        assertTrue(read(ownPeak), read(ownPeak).contains("cap=1000"));
        eqState("live", 1_000d);
        KillSwitchEngine on = newJar(T0 + 2 * H, "1000", null);
        assertEquals(1_300d, on.peak(), 1e-9);
        eq(on, T0 + 2 * H + 1_000L, 700d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, on.requiredAction());
    }

    /** dinh co cap nhung latch acct_peak chua (chet giua 2 lan ghi), file equity mat => van FLATTEN (C6). */
    @Test
    public void t15_peakHasCap_latchNoCap_eqMissing_stillFlatten() throws Exception {
        KillSwitchEngine old = oldJar(T0);
        eq(old, T0, 1_200d);
        Files.write(ownPeak.toPath(), "1200.0 adapter=live_c3eq cap=1000\n".getBytes(StandardCharsets.UTF_8));
        assertFalse(read(latch).contains("acct_peak_cap"));
        KillSwitchEngine n = newJar(T0 + H, "1000", null);
        eq(n, T0 + H + 1_000L, 600d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, n.requiredAction());
    }

    @Test
    public void t16_flagOff_readsCapFile() throws Exception {
        KillSwitchEngine a = newJar(T0, "1000", null);
        eq(a, T0, 1_200d);
        KillSwitchEngine off = newJar(T0 + H, "1000", "false");
        assertEquals(1_200d, off.peak(), 1e-9);
        assertEquals(1_200d, off.acctPeak(), 1e-9);
    }

    /** latch FLATTEN dang giu + acct_peak dinh dang cu bi bo qua (CAP_UNPROVEN) => ghi lai latch KHONG duoc lam mat FLATTEN. */
    @Test
    public void t17_latchFlatten_survivesUnprovenRewrite() throws Exception {
        KillSwitchEngine old = oldJar(T0);
        eq(old, T0, 1_200d);
        eq(old, T0 + 1_000L, 600d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, old.requiredAction());
        KillSwitchEngine n = newJar(T0 + H, "1000", null);
        assertEquals(KillSwitchEngine.Action.FLATTEN, n.requiredAction());
        KillSwitchEngine n2 = newJar(T0 + 2 * H, "1000", null);
        assertEquals(KillSwitchEngine.Action.FLATTEN, n2.requiredAction());
        assertTrue(read(latch), read(latch).contains("FLATTEN"));
    }

    /** rollback tu jar moi ve co tat + GIAM von cung luc (M7-Q3) => ghi nhan FLATTEN gia (luat van hanh). */
    @Test
    public void t18_doc_flagOff_plusGiam_flattenGia() throws Exception {
        KillSwitchEngine a = newJar(T0, "10000", null);
        eq(a, T0, 10_000d);
        KillSwitchEngine off = newJar(T0 + H, "1000", "false");
        eq(off, T0 + H + 1_000L, 1_000d);
        assertEquals("M7-Q3 xac nhan", KillSwitchEngine.Action.FLATTEN, off.requiredAction());
    }
}
