package com.binance.chuyennd.ops;

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
 * [W3A/W3B muc 7 A-02] dinh C6/A40 c3_live gan voi C3_CAPITAL (token cap= rieng, nhan adapter= giu nhu jar cu):
 * pilot 10 000 -> rollback 1 000 KHONG tao DD gia -90 % => khong FLATTEN; dinh jar cu (thieu cap) chi nap khi von JVM truoc
 * (file trang thai equity c3) = von hien tai; rollback jar / tat co van nap duoc dinh cua jar moi.
 */
public class KillSwitchCapitalPeakTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_795_000_000_000L;
    File shadowPeak;
    File ownPeak;
    File latch;
    File eqState;
    final List<String> lines = new ArrayList<>();
    final List<String> alerts = new ArrayList<>();
    final KillSwitchEngine.Sink sink = new KillSwitchEngine.Sink() {
        public void info(String m) { lines.add("I " + m); }
        public void warn(String m) { lines.add("W " + m); }
    };

    @Before
    public void setUp() {
        File run = new File(tmp.getRoot(), "run_w3b");
        assertTrue(run.mkdirs());
        shadowPeak = new File(run, "killsw_peak");
        ownPeak = new File(run, "c3live_killsw_peak");
        latch = new File(run, "killsw_latch.json");
        eqState = new File(run, "c3live_equity_c3.json");
    }

    private KillSwitchEngine.Params params() {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.latchFile = latch;
        p.resetFile = new File(tmp.getRoot(), "run_w3b/killsw_reset.req");
        p.autoReleaseMs = 30 * 60_000L;
        p.autoReleaseCodes.add("C3");
        p.c4Capacity = true;
        return p;
    }

    /** JVM moi (co BAT) von cap / co tat ("false") = hanh vi jar cu. */
    private KillSwitchEngine eng(long now, String cap, String flag) {
        KillSwitchEngine.Params p = params();
        OpsHooks.applyC3PeakTag(p, "live", cap, null, flag, eqState);
        KillSwitchEngine e = OpsHooks.build(KillSwitchEngine.Mode.ACT, "act", sink, true, shadowPeak, ownPeak, () -> 35_000d,
                () -> 0.6f, now, p);
        e.setAlert(alerts::add);
        return e;
    }

    /** jar cu b9e661db: peakTag "live_c3eq", khong von (khong doc, khong ghi cap=). */
    private KillSwitchEngine oldJar(long now) {
        KillSwitchEngine.Params p = params();
        p.peakTag = "live_c3eq";
        KillSwitchEngine e = OpsHooks.build(KillSwitchEngine.Mode.ACT, "act", sink, true, shadowPeak, ownPeak, () -> 35_000d,
                () -> 0.6f, now, p);
        e.setAlert(alerts::add);
        return e;
    }

    /** gia lap C3MainEquity.saveState (jar cu va moi deu ghi "capital"). */
    private void eqStateCap(String adapter, double cap) throws Exception {
        Files.write(eqState.toPath(), ("{\"adapter\":\"" + adapter + "\",\"start_ms\":1,\"capital\":" + cap
                + ",\"funding_cum\":0.0,\"income_last_ms\":1,\"income_last_ids\":[]}").getBytes(StandardCharsets.UTF_8));
    }

    private static void eq(KillSwitchEngine e, long t, double v) {
        e.onPaper(t, 0, 0f, (float) v);
        e.onAccountEquity(t, v);
    }

    private String own() throws Exception {
        return new String(Files.readAllBytes(ownPeak.toPath()), StandardCharsets.UTF_8).trim();
    }

    private String latchTxt() throws Exception {
        return new String(Files.readAllBytes(latch.toPath()), StandardCharsets.UTF_8);
    }

    @Test
    public void capValue_thuTuNguonVaDinhDang() {
        assertEquals("10000", OpsHooks.capValue("10000", null, null));
        assertEquals("1000", OpsHooks.capValue(" 1000.0 ", "4000", null));
        assertEquals("4000", OpsHooks.capValue(null, "4000", null));
        assertEquals("10000", OpsHooks.capValue(null, null, null));
        assertEquals("10000", OpsHooks.capValue("abc", "-5", null));
        assertEquals("1000.5", OpsHooks.capValue("1000.5", null, "true"));
        assertNull(OpsHooks.capValue("1000", null, "FALSE"));
        assertNull("[v2] 0 cung tat", OpsHooks.capValue("1000", null, " 0 "));
    }

    @Test
    public void applyTag_nhanGiuNhuJarCu_vonJvmTruocTuFileEquity() throws Exception {
        KillSwitchEngine.Params p = params();
        OpsHooks.applyC3PeakTag(p, "LIVE", "1000", null, null, eqState);
        assertEquals("live_c3eq", p.peakTag);
        assertEquals("1000", p.peakCap);
        assertNull("chua co file equity", p.peakCapPrev);
        eqStateCap("live", 10_000d);
        OpsHooks.applyC3PeakTag(p, "live", "1000", null, null, eqState);
        assertEquals(10_000d, p.peakCapPrev, 1e-9);
        eqStateCap("dry", 10_000d);
        OpsHooks.applyC3PeakTag(p, "live", "1000", null, null, eqState);
        assertNull("file equity cua adapter khac => khong tin", p.peakCapPrev);
        Files.write(eqState.toPath(), "{hong".getBytes(StandardCharsets.UTF_8));
        OpsHooks.applyC3PeakTag(p, "live", "1000", null, null, eqState);
        assertNull(p.peakCapPrev);
        Files.write(eqState.toPath(), "{\"adapter\":\"live\",\"capital\":-3}".getBytes(StandardCharsets.UTF_8));
        OpsHooks.applyC3PeakTag(p, "live", "1000", null, null, eqState);
        assertNull(p.peakCapPrev);
        OpsHooks.applyC3PeakTag(p, "live", "1000", null, "false", eqState);
        assertEquals("live_c3eq", p.peakTag);
        assertNull(p.peakCap);
        assertNull(p.peakCapPrev);
        assertEquals("[v2] co tat van ghi von", "1000", p.peakCapWrite);
    }

    /** Kich ban audit A-02: pilot_on 1000 -> 10000 (dinh ~10 000), hau kiem TRUOT => rollback C3_CAPITAL=1000. */
    @Test
    public void pilotRollback_khongFlatten() throws Exception {
        KillSwitchEngine pilot = eng(T0, "10000", null);
        eq(pilot, T0, 10_000d);
        assertEquals("10000.0 adapter=live_c3eq cap=10000", own());
        assertTrue(latchTxt(), latchTxt().contains("\"acct_peak_adapter\":\"live_c3eq\"") && latchTxt().contains("\"acct_peak_cap\":\"10000\""));
        eqStateCap("live", 10_000d);
        lines.clear();
        KillSwitchEngine back = eng(T0 + 60_000L, "1000", null);
        assertTrue("dinh von khac => bo qua", Double.isNaN(back.peak()));
        assertTrue(Double.isNaN(back.acctPeak()));
        eq(back, T0 + 61_000L, 1_000d);
        assertEquals(KillSwitchEngine.Action.NONE, back.requiredAction());
        assertEquals(1_000d, back.peak(), 1e-9);
        assertTrue(alerts.toString(), alerts.stream().anyMatch(a -> a.contains("BO QUA vi von")));
    }

    /** Hoi quy: C3_PEAK_TAG_CAPITAL=false (= jar cu) => van tai hien loi A-02 (FLATTEN). */
    @Test
    public void coTat_taiHienLoiCu() throws Exception {
        KillSwitchEngine pilot = eng(T0, "10000", "false");
        eq(pilot, T0, 10_000d);
        assertEquals("[v2] co tat: dinh dang tuong thich jar cu + VAN ghi cap=", "10000.0 adapter=live_c3eq cap=10000", own());
        assertTrue(latchTxt().contains("\"acct_peak_cap\":\"10000\""));
        KillSwitchEngine back = eng(T0 + 60_000L, "1000", "false");
        assertEquals(10_000d, back.peak(), 1e-9);
        eq(back, T0 + 61_000L, 1_000d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, back.requiredAction());
    }

    /** Doi jar (cung von): dinh jar cu (thieu cap) + von JVM truoc = von hien tai => nap, roi ghi lai kem cap=. */
    @Test
    public void doiJar_cungVon_napDinhCu_roiGhiLaiKemCap() throws Exception {
        KillSwitchEngine old = oldJar(T0);
        eq(old, T0, 1_200d);
        eqStateCap("live", 1_000d);
        assertEquals("1200.0 adapter=live_c3eq", own());
        KillSwitchEngine nw = eng(T0 + 60_000L, "1000", null);
        assertEquals(1_200d, nw.peak(), 1e-9);
        assertEquals(1_200d, nw.acctPeak(), 1e-9);
        assertTrue(lines.toString(), lines.stream().anyMatch(l -> l.contains("dinh dang cu (thieu cap=) => nap dinh TAM")));
        eq(nw, T0 + 400_000L, 1_100d);
        assertEquals(KillSwitchEngine.Action.NONE, nw.requiredAction());
        assertEquals("ghi lai kem cap", "1200.0 adapter=live_c3eq cap=1000", own());
        assertTrue(latchTxt(), latchTxt().contains("\"acct_peak_cap\":\"1000\""));
        // sau khi ghi lai, ha von => dinh bi bo qua
        KillSwitchEngine down = eng(T0 + 500_000L, "500", null);
        assertTrue(Double.isNaN(down.peak()));
        assertTrue(Double.isNaN(down.acctPeak()));
    }

    /**
     * [v2] File thieu cap + KHONG co moc von (file equity mat): dinh TAM giu qua moi restart (von khong doi khong mat dinh);
     * lan danh gia dau DD du nguong FLATTEN (von that su da ha 10000 -> 1000) => KHONG FLATTEN, dat lai moc, latch
     * NO_NEW_ENTRY STATE + 1 canh bao; file ghi lai kem cap => restart sau khong canh bao lai.
     */
    @Test
    public void thieuCap_khongMocVon_dinhTam_khongFlatten_failClosed() throws Exception {
        KillSwitchEngine old = oldJar(T0);
        eq(old, T0, 10_000d);
        assertFalse(eqState.exists());
        for (int i = 1; i <= 3; i++) {   // chet truoc equity dau 3 lan
            KillSwitchEngine k = eng(T0 + i * 60_000L, "1000", null);
            assertEquals(10_000d, k.peak(), 1e-9);
            assertEquals(10_000d, k.acctPeak(), 1e-9);
        }
        assertTrue(alerts.toString(), alerts.isEmpty());
        KillSwitchEngine nw = eng(T0 + 300_000L, "1000", null);
        eq(nw, T0 + 301_000L, 1_000d);
        assertEquals(KillSwitchEngine.Action.NO_NEW_ENTRY, nw.requiredAction());
        assertTrue(nw.latchCodes().contains(KillSwitchEngine.CODE_STATE));
        assertEquals(1_000d, nw.peak(), 1e-9);
        assertEquals(1_000d, nw.acctPeak(), 1e-9);
        assertEquals(alerts.toString(), 1, alerts.stream().filter(x -> x.contains("KHONG phan biet duoc lo that")).count());
        assertEquals("1000.0 adapter=live_c3eq cap=1000", own());
        assertTrue(latchTxt(), latchTxt().contains("\"acct_peak_cap\":\"1000\""));
        eqStateCap("live", 1_000d);
        alerts.clear();
        KillSwitchEngine again = eng(T0 + 400_000L, "1000", null);
        assertEquals(1_000d, again.peak(), 1e-9);
        eq(again, T0 + 401_000L, 1_000d);
        assertEquals("latch STATE giu toi khi owner reset", KillSwitchEngine.Action.NO_NEW_ENTRY, again.requiredAction());
        assertTrue(alerts.toString(), alerts.stream().noneMatch(x -> x.contains("KHONG phan biet")));
        eq(again, T0 + 402_000L, 550d);
        assertEquals("sau khi xac nhan: lo that => FLATTEN", KillSwitchEngine.Action.FLATTEN, again.requiredAction());
    }

    /** [v2] File thieu cap + moc von JVM truoc KHAC => bo qua + cach ly + 1 canh bao gop (dinh + latch). */
    @Test
    public void thieuCap_vonDoiTheoMoc_boQua_cachLy_motCanhBao() throws Exception {
        KillSwitchEngine old = oldJar(T0);
        eq(old, T0, 10_000d);
        eqStateCap("live", 10_000d);
        KillSwitchEngine nw = eng(T0 + 60_000L, "1000", null);
        assertTrue(Double.isNaN(nw.peak()));
        assertTrue(Double.isNaN(nw.acctPeak()));
        assertFalse(ownPeak.exists());
        assertEquals(alerts.toString(), 1, alerts.stream().filter(x -> x.contains("BO QUA vi von")).count());
        eqStateCap("live", 1_000d);
        KillSwitchEngine again = eng(T0 + 120_000L, "1000", null);
        assertTrue(Double.isNaN(again.peak()));
        assertTrue(Double.isNaN(again.acctPeak()));
        assertEquals("khong canh bao lai", 1, alerts.stream().filter(x -> x.contains("BO QUA vi von")).count());
    }

    /** [v2] dinh TAM, lan danh gia dau DD nho (von khong doi) => xac nhan, ghi lai cap; restart file equity mat => DD that FLATTEN. */
    @Test
    public void dinhTam_xacNhan_roiCrash_eqMat_ddThatFlatten() throws Exception {
        KillSwitchEngine old = oldJar(T0);
        eq(old, T0, 1_200d);
        KillSwitchEngine nw = eng(T0 + 60_000L, "1000", null);
        eq(nw, T0 + 61_000L, 1_150d);
        assertEquals(KillSwitchEngine.Action.NONE, nw.requiredAction());
        assertEquals("1200.0 adapter=live_c3eq cap=1000", own());
        assertTrue(latchTxt().contains("\"acct_peak_cap\":\"1000\""));
        for (int i = 2; i <= 5; i++) {
            if (eqState.exists()) assertTrue(eqState.delete());
            KillSwitchEngine k = eng(T0 + i * 60_000L, "1000", null);
            assertEquals(1_200d, k.peak(), 1e-9);
            assertEquals(1_200d, k.acctPeak(), 1e-9);
        }
        KillSwitchEngine z = eng(T0 + 600_000L, "1000", null);
        eq(z, T0 + 601_000L, 700d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, z.requiredAction());
    }

    /** [v2] acct_peak TAM KHONG duoc ghi kem cap truoc lan danh gia A40 cua chinh no (C6 latch truoc => persistLatch). */
    @Test
    public void acctPeakTam_khongDuocChungNhanSom() throws Exception {
        KillSwitchEngine old = oldJar(T0);
        eq(old, T0, 10_000d);
        KillSwitchEngine nw = eng(T0 + 60_000L, "1000", null);
        nw.onPaper(T0 + 61_000L, 0, 0f, 1_000f);   // C6 trip => persistLatch (acct_peak con TAM)
        assertFalse("acct_peak TAM chua duoc gan von: " + latchTxt(), latchTxt().contains("acct_peak_cap"));
        // JVM chet o day; restart: acct_peak van TAM => khong FLATTEN gia
        KillSwitchEngine again = eng(T0 + 120_000L, "1000", null);
        eq(again, T0 + 121_000L, 1_000d);
        assertNotEquals(KillSwitchEngine.Action.FLATTEN, again.requiredAction());
    }

    /** Dinh dang nhan cua ban w3a (dd8547d9, "live_c3eq_cap1000") van doc duoc: cung von nap + ghi lai; von khac bo qua. */
    @Test
    public void nhanW3a_docDuoc() throws Exception {
        Files.write(ownPeak.toPath(), "1200.0 adapter=live_c3eq_cap1000\n".getBytes(StandardCharsets.UTF_8));
        KillSwitchEngine a = eng(T0, "1000", null);
        assertEquals(1_200d, a.peak(), 1e-9);
        eq(a, T0 + 1_000L, 1_150d);
        assertEquals("1200.0 adapter=live_c3eq cap=1000", own());
        Files.write(ownPeak.toPath(), "1200.0 adapter=live_c3eq_cap1000\n".getBytes(StandardCharsets.UTF_8));
        KillSwitchEngine b = eng(T0 + 60_000L, "500", null);
        assertTrue(Double.isNaN(b.peak()));
        Files.write(ownPeak.toPath(), "1200.0 adapter=live_c3eq_cap1000p5\n".getBytes(StandardCharsets.UTF_8));
        KillSwitchEngine c = eng(T0 + 70_000L, "1000.5", null);
        assertEquals(1_200d, c.peak(), 1e-9);
    }

    /** Nhan adapter khac (dry) van bo qua nhu 2d MIN-19 (ke ca co cap trung). */
    @Test
    public void adapterKhac_boQua() throws Exception {
        Files.write(ownPeak.toPath(), "1200.0 adapter=dry_c3eq cap=1000\n".getBytes(StandardCharsets.UTF_8));
        KillSwitchEngine a = eng(T0, "1000", null);
        assertTrue(Double.isNaN(a.peak()));
        assertTrue(lines.toString(), lines.stream().anyMatch(l -> l.contains("!= adapter hien tai live_c3eq => BO QUA")));
        assertTrue("khong cach ly file adapter khac", ownPeak.exists());
    }

    /**
     * Tuong thich nguoc: chep NGUYEN logic loadPeak cua jar b9e661db (tag = token adapter= cuoi; so = token dau) => file
     * jar moi ghi phai duoc jar cu chap nhan (khong mat dinh khi rollback).
     */
    @Test
    public void jarCu_docDuocFileJarMoi() throws Exception {
        KillSwitchEngine nw = eng(T0, "1000", null);
        eq(nw, T0, 1_234.5d);
        String s = own();
        String[] tok = s.split("\\s+");
        String tag = null;
        for (String x : tok) if (x.startsWith("adapter=")) tag = x.substring("adapter=".length());
        assertEquals("live_c3eq", tag);
        assertEquals(1_234.5d, Double.parseDouble(tok[0]), 1e-9);
        com.google.gson.JsonObject o = com.google.gson.JsonParser.parseString(latchTxt()).getAsJsonObject();
        assertEquals("live_c3eq", o.get("acct_peak_adapter").getAsString());
        assertEquals("live_c3eq", o.get("adapter").getAsString());
        assertEquals(1_234.5d, o.get("acct_peak").getAsDouble(), 1e-9);
    }
}
