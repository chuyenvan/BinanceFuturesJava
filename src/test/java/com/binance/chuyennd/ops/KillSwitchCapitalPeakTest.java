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
 * [W3A muc 7 A-02] dinh C6/A40 c3_live gan voi C3_CAPITAL: pilot 10 000 -> rollback 1 000 KHONG tao DD gia -90 % =>
 * khong FLATTEN; file dinh cua jar truoc (nhan khong co von) van nap duoc (khong mat dinh khi doi jar) va duoc ghi lai.
 */
public class KillSwitchCapitalPeakTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long T0 = 1_795_000_000_000L;
    File shadowPeak;
    File ownPeak;
    File latch;
    final List<String> lines = new ArrayList<>();
    final KillSwitchEngine.Sink sink = new KillSwitchEngine.Sink() {
        public void info(String m) { lines.add("I " + m); }
        public void warn(String m) { lines.add("W " + m); }
    };

    @Before
    public void setUp() {
        File run = new File(tmp.getRoot(), "run_w3a");
        assertTrue(run.mkdirs());
        shadowPeak = new File(run, "killsw_peak");
        ownPeak = new File(run, "c3live_killsw_peak");
        latch = new File(run, "killsw_latch.json");
    }

    private KillSwitchEngine.Params params(String tag, String legacy) {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.latchFile = latch;
        p.resetFile = new File(tmp.getRoot(), "run_w3a/killsw_reset.req");
        p.autoReleaseMs = 30 * 60_000L;
        p.autoReleaseCodes.add("C3");
        p.c4Capacity = true;
        p.peakTag = tag;
        p.peakTagLegacy = legacy;
        return p;
    }

    private KillSwitchEngine eng(long now, String tag, String legacy) {
        return OpsHooks.build(KillSwitchEngine.Mode.ACT, "act", sink, true, shadowPeak, ownPeak, () -> 35_000d, () -> 0.6f,
                now, params(tag, legacy));
    }

    private String own() throws Exception {
        return new String(Files.readAllBytes(ownPeak.toPath()), StandardCharsets.UTF_8).trim();
    }

    @Test
    public void capTag_thuTuNguonVaDinhDang() {
        assertEquals("_cap10000", OpsHooks.capTag("10000", null, null));
        assertEquals("_cap1000", OpsHooks.capTag(" 1000.0 ", "4000", null));
        assertEquals("_cap4000", OpsHooks.capTag(null, "4000", null));
        assertEquals("_cap10000", OpsHooks.capTag(null, null, null));
        assertEquals("_cap10000", OpsHooks.capTag("abc", "-5", null));
        assertEquals("_cap1000p5", OpsHooks.capTag("1000.5", null, "true"));
        assertNull(OpsHooks.capTag("1000", null, "FALSE"));
    }

    /** Kich ban audit A-02: pilot_on 1000 -> 10000 (dinh ~10 000), hau kiem TRUOT => rollback C3_CAPITAL=1000. */
    @Test
    public void pilotRollback_khongFlatten() throws Exception {
        KillSwitchEngine pilot = eng(T0, "live_c3eq_cap10000", "live_c3eq");
        pilot.onPaper(T0, 0, 0f, 10_000f);
        pilot.onAccountEquity(T0, 10_000d);
        assertTrue(own(), own().endsWith("adapter=live_c3eq_cap10000"));
        lines.clear();
        KillSwitchEngine back = eng(T0 + 60_000L, "live_c3eq_cap1000", "live_c3eq");
        assertTrue("dinh von khac => bo qua", Double.isNaN(back.peak()));
        assertTrue(Double.isNaN(back.acctPeak()));
        back.onPaper(T0 + 61_000L, 0, 0f, 1_000f);
        back.onAccountEquity(T0 + 61_000L, 1_000d);
        assertEquals(KillSwitchEngine.Action.NONE, back.requiredAction());
        assertEquals(1_000d, back.peak(), 1e-9);
    }

    /** Hoi quy: nhan KHONG gan von (C3_PEAK_TAG_CAPITAL=false = jar cu) => van tai hien loi A-02 (FLATTEN). */
    @Test
    public void coTat_taiHienLoiCu() throws Exception {
        KillSwitchEngine pilot = eng(T0, "live_c3eq", null);
        pilot.onPaper(T0, 0, 0f, 10_000f);
        pilot.onAccountEquity(T0, 10_000d);
        KillSwitchEngine back = eng(T0 + 60_000L, "live_c3eq", null);
        assertEquals(10_000d, back.peak(), 1e-9);
        back.onPaper(T0 + 61_000L, 0, 0f, 1_000f);
        back.onAccountEquity(T0 + 61_000L, 1_000d);
        assertEquals(KillSwitchEngine.Action.FLATTEN, back.requiredAction());
    }

    /** Doi jar (cung von): dinh do jar cu ghi (nhan live_c3eq) duoc nap => khong mat DD dang co; ghi lai nhan moi. */
    @Test
    public void doiJar_napDinhNhanCu_roiGhiLaiNhanMoi() throws Exception {
        KillSwitchEngine old = eng(T0, "live_c3eq", null);
        old.onPaper(T0, 0, 0f, 1_200f);
        old.onAccountEquity(T0, 1_200d);
        assertTrue(own().endsWith("adapter=live_c3eq"));
        KillSwitchEngine nw = eng(T0 + 60_000L, "live_c3eq_cap1000", "live_c3eq");
        assertEquals(1_200d, nw.peak(), 1e-9);
        assertEquals(1_200d, nw.acctPeak(), 1e-9);
        assertTrue(lines.toString(), lines.stream().anyMatch(l -> l.contains("nhan cu adapter=live_c3eq")));
        nw.onPaper(T0 + 400_000L, 0, 0f, 1_100f);
        nw.onAccountEquity(T0 + 400_000L, 1_100d);
        assertEquals(KillSwitchEngine.Action.NONE, nw.requiredAction());
        assertTrue("ghi lai nhan moi: " + own(), own().endsWith("adapter=live_c3eq_cap1000"));
        String lt = new String(Files.readAllBytes(latch.toPath()), StandardCharsets.UTF_8);
        assertTrue(lt, lt.contains("\"acct_peak_adapter\":\"live_c3eq_cap1000\""));
        // sau khi ghi lai, ha von => dinh bi bo qua (lo A-02 dong)
        KillSwitchEngine down = eng(T0 + 500_000L, "live_c3eq_cap500", "live_c3eq");
        assertTrue(Double.isNaN(down.peak()));
    }
}
