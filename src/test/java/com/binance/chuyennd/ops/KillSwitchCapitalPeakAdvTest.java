package com.binance.chuyennd.ops;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

/**
 * [W3B muc 7] Test doi khang cua A1_W3A (a1_w3a/A1W3aPeakCapAdvTest, 4 ca FAIL tren dd8547d9) dua vao bo chinh thuc theo
 * API moi + MA TRAN {jar cu->moi, moi->cu, moi->moi (+ doi co)} x {von giu, tang, giam} x {co bat/tat} x {file dinh
 * co/khong/hong} x {A: khong lo that, B: lo that 50 %}. "Jar cu" = Params dung y nhu OpsHooks b9e661db (peakTag
 * "live_c3eq", khong von). Moi JVM ghi file trang thai equity c3 (gia lap C3MainEquity.saveState, ca 2 jar deu ghi "capital").
 */
public class KillSwitchCapitalPeakAdvTest {

    private static final Logger LOG = LoggerFactory.getLogger(KillSwitchCapitalPeakAdvTest.class);

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_795_000_000_000L;
    final KillSwitchEngine.Sink sink = new KillSwitchEngine.Sink() {
        public void info(String m) { }
        public void warn(String m) { }
    };

    /** 1 thu muc run/ rieng. */
    final class Run {
        final File dir;
        final File ownPeak;
        final File latch;
        final File eqState;

        Run() throws Exception {
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

        /** jar moi: co BAT (flag null) / TAT ("false"). */
        KillSwitchEngine newJar(long now, double cap, String flag) {
            KillSwitchEngine.Params p = params();
            OpsHooks.applyC3PeakTag(p, "live", Double.toString(cap), null, flag, eqState);
            return OpsHooks.build(KillSwitchEngine.Mode.ACT, "act", sink, true, new File(dir, "killsw_peak"), ownPeak,
                    () -> 35_000d, () -> 0.6f, now, p);
        }

        /** jar cu b9e661db: peakTag = adapter + "_c3eq", khong von. */
        KillSwitchEngine oldJar(long now) {
            KillSwitchEngine.Params p = params();
            p.peakTag = "live_c3eq";
            return OpsHooks.build(KillSwitchEngine.Mode.ACT, "act", sink, true, new File(dir, "killsw_peak"), ownPeak,
                    () -> 35_000d, () -> 0.6f, now, p);
        }

        void eqState(double cap) throws Exception {
            Files.write(eqState.toPath(), ("{\"adapter\":\"live\",\"start_ms\":1,\"capital\":" + cap
                    + ",\"funding_cum\":0.0,\"income_last_ms\":1,\"income_last_ids\":[]}").getBytes(StandardCharsets.UTF_8));
        }
    }

    private static void eq(KillSwitchEngine e, long t, double v) {
        e.onPaper(t, 0, 0f, (float) v);
        e.onAccountEquity(t, v);
    }

    Run r;

    @Before
    public void setUp() throws Exception {
        r = new Run();
    }

    // ------------------------------------------------------------------ 6 ca A1 (a1_w3a/A1W3aPeakCapAdvTest)

    /** A1 doi chung: DD that -50 % cung von => FLATTEN. */
    @Test
    public void a1_doiChung_ddThat_cungVon_flatten() throws Exception {
        KillSwitchEngine a = r.newJar(T0, 1_000d, null);
        eq(a, T0, 1_200d);
        r.eqState(1_000d);
        KillSwitchEngine b = r.newJar(T0 + 60_000L, 1_000d, null);
        eq(b, T0 + 61_000L, 600d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, b.requiredAction());
    }

    /** A1 R3 (FAIL tren dd8547d9): doi jar CUNG LUC ha von 10000 -> 1000 => KHONG FLATTEN gia. */
    @Test
    public void a1_r3_doiJarCungLucHaVon_khongFlattenGia() throws Exception {
        KillSwitchEngine old = r.oldJar(T0);
        eq(old, T0, 10_000d);
        r.eqState(10_000d);
        KillSwitchEngine nw = r.newJar(T0 + 60_000L, 1_000d, null);
        eq(nw, T0 + 61_000L, 1_000d);
        assertEquals(KillSwitchEngine.Action.NONE, nw.requiredAction());
    }

    /** A1 (FAIL tren dd8547d9): rollback JAR ve b9e661db sau khi jar moi ghi dinh => dinh GIU, DD that -50 % FLATTEN. */
    @Test
    public void a1_rollbackJar_dinhGiu_ddThatFlatten() throws Exception {
        KillSwitchEngine nw = r.newJar(T0, 1_000d, null);
        eq(nw, T0, 1_200d);
        r.eqState(1_000d);
        KillSwitchEngine old = r.oldJar(T0 + 60_000L);
        assertEquals(1_200d, old.peak(), 1e-9);
        assertEquals(1_200d, old.acctPeak(), 1e-9);
        eq(old, T0 + 61_000L, 600d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, old.requiredAction());
    }

    /** A1 (FAIL tren dd8547d9): rollback CO (C3_PEAK_TAG_CAPITAL=false) sau khi da ghi von => dinh GIU, FLATTEN. */
    @Test
    public void a1_rollbackCo_dinhGiu_ddThatFlatten() throws Exception {
        KillSwitchEngine nw = r.newJar(T0, 1_000d, null);
        eq(nw, T0, 1_200d);
        r.eqState(1_000d);
        KillSwitchEngine off = r.newJar(T0 + 60_000L, 1_000d, "false");
        assertEquals(1_200d, off.peak(), 1e-9);
        eq(off, T0 + 61_000L, 600d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, off.requiredAction());
    }

    /** A1: latch FLATTEN dang giu + doi von => latch GIU. */
    @Test
    public void a1_latchFlatten_doiVon_giuLatch() throws Exception {
        KillSwitchEngine a = r.newJar(T0, 1_000d, null);
        eq(a, T0, 1_200d);
        eq(a, T0 + 1_000L, 600d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, a.requiredAction());
        r.eqState(1_000d);
        KillSwitchEngine b = r.newJar(T0 + 60_000L, 10_000d, null);
        assertEquals(KillSwitchEngine.Action.FLATTEN, b.requiredAction());
    }

    /** A1 (FAIL tren dd8547d9): dinh thieu von KHONG duoc nap o restart thu 2 voi von khac. */
    @Test
    public void a1_nhanCu_khongNapLaiKhiVonDoi() throws Exception {
        KillSwitchEngine old = r.oldJar(T0);
        eq(old, T0, 10_000d);
        r.eqState(10_000d);
        KillSwitchEngine n1 = r.newJar(T0 + 60_000L, 10_000d, null);
        assertEquals(10_000d, n1.peak(), 1e-9);
        // n1 chet truoc khi ghi lai file dinh; C3MainEquity cua n1 ghi von 10000
        KillSwitchEngine n2 = r.newJar(T0 + 120_000L, 1_000d, null);
        assertTrue("restart lan 2 voi von khac: peak=" + n2.peak(), Double.isNaN(n2.peak()));
        assertTrue(Double.isNaN(n2.acctPeak()));
        // n2 cung chet som; C3MainEquity n2 da ghi von 1000 => restart lan 3 (von 1000) van KHONG nap dinh 10000
        r.eqState(1_000d);
        KillSwitchEngine n3 = r.newJar(T0 + 180_000L, 1_000d, null);
        assertTrue(Double.isNaN(n3.peak()));
        assertTrue(Double.isNaN(n3.acctPeak()));
        eq(n3, T0 + 181_000L, 1_000d);
        assertEquals(KillSwitchEngine.Action.NONE, n3.requiredAction());
    }

    // ------------------------------------------------------------------ ma tran

    enum Trans { CU_MOI, MOI_CU, MOI_MOI, MOI_MOI_BAT_TAT, MOI_MOI_TAT_BAT }

    enum Von { GIU, TANG, GIAM }

    enum FileDinh { CO, KHONG, HONG }

    /** Ket cuc 1 o: JVM1 len equity = C1 (dinh C1), JVM2 nhan equity = eq2. */
    private KillSwitchEngine.Action cell(Trans t, Von v, boolean flagOn, FileDinh fd, boolean lossB) throws Exception {
        Run x = new Run();
        double c1 = v == Von.GIAM ? 10_000d : 1_000d;
        double c2 = v == Von.TANG ? 10_000d : v == Von.GIAM ? 1_000d : 1_000d;
        String f1 = flagOf(t, flagOn, true);
        String f2 = flagOf(t, flagOn, false);
        KillSwitchEngine j1 = t == Trans.CU_MOI ? x.oldJar(T0) : x.newJar(T0, c1, f1);
        eq(j1, T0, c1);
        x.eqState(c1);
        if (fd == FileDinh.KHONG) {
            Files.deleteIfExists(x.ownPeak.toPath());
            Files.deleteIfExists(x.latch.toPath());
        } else if (fd == FileDinh.HONG) {
            Files.write(x.ownPeak.toPath(), "#!x hong\n".getBytes(StandardCharsets.UTF_8));
            Files.write(x.latch.toPath(), "{hong".getBytes(StandardCharsets.UTF_8));
        }
        KillSwitchEngine j2 = t == Trans.MOI_CU ? x.oldJar(T0 + 60_000L) : x.newJar(T0 + 60_000L, c2, f2);
        eq(j2, T0 + 61_000L, lossB ? 0.5d * c2 : c2);
        return j2.requiredAction();
    }

    /** co cua JVM1 (first) / JVM2; jar cu => "false" (khong gan von). */
    private static String flagOf(Trans t, boolean flagOn, boolean first) {
        switch (t) {
            case CU_MOI: return first ? "false" : (flagOn ? null : "false");
            case MOI_CU: return first ? (flagOn ? null : "false") : "false";
            case MOI_MOI_BAT_TAT: return first ? null : "false";
            case MOI_MOI_TAT_BAT: return first ? "false" : null;
            default: return flagOn ? null : "false";
        }
    }

    /** Ket cuc MONG MUON (quy tac thiet ke W3B). */
    private static KillSwitchEngine.Action expected(Trans t, Von v, boolean flagOn, FileDinh fd, boolean lossB) {
        double c1 = v == Von.GIAM ? 10_000d : 1_000d;
        double c2 = v == Von.TANG ? 10_000d : 1_000d;
        double eq2 = lossB ? 0.5d * c2 : c2;
        boolean binding2 = t != Trans.MOI_CU && flagOf(t, flagOn, false) == null;   // JVM2 xet von
        boolean accepted = fd == FileDinh.CO && (!binding2 || v == Von.GIU);
        boolean flatten = accepted && eq2 / c1 - 1d <= -0.40d;
        if (flatten) return KillSwitchEngine.Action.FLATTEN;
        return fd == FileDinh.HONG ? KillSwitchEngine.Action.NO_NEW_ENTRY : KillSwitchEngine.Action.NONE;
    }

    @Test
    public void maTran() throws Exception {
        List<String> bad = new ArrayList<>();
        int n = 0;
        StringBuilder tbl = new StringBuilder("\nMATRAN7|trans|von|co|file|A_khongLo|B_lo50%\n");
        for (Trans t : Trans.values()) {
            boolean[] flags = t == Trans.MOI_MOI_BAT_TAT || t == Trans.MOI_MOI_TAT_BAT ? new boolean[]{true} : new boolean[]{true, false};
            for (Von v : Von.values()) {
                for (boolean fl : flags) {
                    for (FileDinh fd : FileDinh.values()) {
                        String[] got = new String[2];
                        for (int k = 0; k < 2; k++) {
                            KillSwitchEngine.Action a = cell(t, v, fl, fd, k == 1);
                            KillSwitchEngine.Action e = expected(t, v, fl, fd, k == 1);
                            got[k] = a.name();
                            n++;
                            if (a != e) bad.add(t + "/" + v + "/" + (fl ? "BAT" : "TAT") + "/" + fd + "/" + (k == 1 ? "B" : "A") + " got=" + a + " exp=" + e);
                        }
                        tbl.append("MATRAN7|").append(t).append('|').append(v).append('|')
                                .append(t == Trans.MOI_MOI_BAT_TAT || t == Trans.MOI_MOI_TAT_BAT ? "-" : fl ? "BAT" : "TAT")
                                .append('|').append(fd).append('|').append(got[0]).append('|').append(got[1]).append('\n');
                    }
                }
            }
        }
        LOG.info("{}", tbl);
        assertTrue("o lech ky vong: " + bad, bad.isEmpty());
        assertEquals(2 * (3 * 3 * 3 * 2 + 2 * 3 * 3), n);
    }

    /** Bat bien an toan chinh: co BAT o JVM2 moi => KHONG BAO GIO FLATTEN khi khong lo that (moi o, moi von). */
    @Test
    public void batBien_coBat_khongFlattenGia() throws Exception {
        for (Trans t : new Trans[]{Trans.CU_MOI, Trans.MOI_MOI, Trans.MOI_MOI_TAT_BAT}) {
            for (Von v : Von.values()) {
                for (FileDinh fd : FileDinh.values()) {
                    assertNotEquals(t + "/" + v + "/" + fd, KillSwitchEngine.Action.FLATTEN, cell(t, v, true, fd, false));
                }
            }
        }
    }
}
