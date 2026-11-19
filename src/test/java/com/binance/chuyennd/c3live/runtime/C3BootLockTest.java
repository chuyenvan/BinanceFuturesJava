package com.binance.chuyennd.c3live.runtime;

import com.binance.chuyennd.tradecore.selector.LiveProfileC3;
import org.junit.After;
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
 * [W3A muc 6 B-09] bang trang thai khoi dong:
 * start do script (KILL_SWITCH token script co san) => EXISTING, khong dung file;
 * start sau crash/watchdog/reboot/restart tay (khong KILL_SWITCH) => LOCKED (JVM dat token c3live_boot);
 * adapter dry/off => NOT_LIVE; env tat => DISABLED; khong ghi duoc => khoa RAM; 1 lan / JVM.
 */
public class C3BootLockTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    final List<String> alerts = new ArrayList<>();
    static final long NOW = 1_795_000_000_000L;

    @After
    public void resetMem() {
        LiveProfileC3.setBootLockMem(false);
    }

    private File ks() throws Exception {
        File run = new File(tmp.getRoot(), "run_w3a");
        if (!run.exists()) assertTrue(run.mkdirs());
        return new File(run, "KILL_SWITCH");
    }

    @Test
    public void startSauCrash_khongKillSwitch_jvmTuKhoa() throws Exception {
        File f = ks();
        C3BootLock b = new C3BootLock(f, null, alerts::add);
        assertEquals(C3BootLock.Outcome.LOCKED, b.applyOnce(true, NOW));
        assertTrue(f.exists());
        String s = new String(Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8);
        assertTrue(s, s.startsWith("c3live_boot "));
        assertTrue(s.contains("MODE=undrain"));
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0).startsWith("[C3-BOOT] KHOA KHOI DONG"));
        assertFalse(LiveProfileC3.bootLockMem());
    }

    @Test
    public void startDoScript_tokenScript_khongDung() throws Exception {
        File f = ks();
        byte[] tok = "golive_micro_on 20261119_101500 hau_kiem: dung mo moi toi khi hau kiem DAT\n".getBytes(StandardCharsets.UTF_8);
        Files.write(f.toPath(), tok);
        long mt = f.lastModified();
        C3BootLock b = new C3BootLock(f, null, alerts::add);
        assertEquals(C3BootLock.Outcome.EXISTING, b.applyOnce(true, NOW));
        assertArrayEquals("token script giu nguyen byte (hau kiem micro_on grep '^golive_micro_on <TS> ')", tok,
                Files.readAllBytes(f.toPath()));
        assertEquals(mt, f.lastModified());
        assertTrue(alerts.isEmpty());
    }

    @Test
    public void startKhiDangDrain_giuNguyen() throws Exception {
        File f = ks();
        Files.write(f.toPath(), "golive_live_off drain 20261119_120000\n".getBytes(StandardCharsets.UTF_8));
        assertEquals(C3BootLock.Outcome.EXISTING, new C3BootLock(f, "true", alerts::add).applyOnce(true, NOW));
        assertTrue(new String(Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8).startsWith("golive_live_off drain "));
    }

    @Test
    public void dryHoacOff_khongLamGi() throws Exception {
        File f = ks();
        assertEquals(C3BootLock.Outcome.NOT_LIVE, new C3BootLock(f, null, alerts::add).applyOnce(false, NOW));
        assertFalse(f.exists());
    }

    @Test
    public void envTat_yNhuCu() throws Exception {
        File f = ks();
        assertEquals(C3BootLock.Outcome.DISABLED, new C3BootLock(f, " FALSE ", alerts::add).applyOnce(true, NOW));
        assertFalse(f.exists());
        assertTrue(C3BootLock.enabled(null));
        assertTrue(C3BootLock.enabled("true"));
        assertTrue(C3BootLock.enabled("0"));
        assertFalse(C3BootLock.enabled("false"));
    }

    @Test
    public void motLanMoiJvm_undrainXongKhongKhoaLai() throws Exception {
        File f = ks();
        C3BootLock b = new C3BootLock(f, null, alerts::add);
        assertEquals(C3BootLock.Outcome.LOCKED, b.applyOnce(true, NOW));
        assertTrue(f.renameTo(new File(f.getPath() + ".off_w3a")));   // = golive_live_off MODE=undrain
        assertEquals(C3BootLock.Outcome.ALREADY_DONE, b.applyOnce(true, NOW + 60_000L));   // create() thu lai sau 60 s
        assertFalse(f.exists());
    }

    @Test
    public void khongGhiDuoc_khoaRam() throws Exception {
        File f = new File(new File(tmp.getRoot(), "khong_ton_tai_w3a"), "KILL_SWITCH");
        assertEquals(C3BootLock.Outcome.FAILED_MEM_LOCK, new C3BootLock(f, null, alerts::add).applyOnce(true, NOW));
        assertTrue(LiveProfileC3.bootLockMem());
        assertEquals(1, alerts.size());
        assertTrue(alerts.get(0).startsWith("[C3-BOOT] KHAN"));
    }

    /** Khoa RAM duoc OR vao kill-switch trong forceNoPush; runtime ap khoa TRUOC khi tao gateway. */
    @Test
    public void nguon_wiring() throws Exception {
        String lp = new String(Files.readAllBytes(new File(
                "src/main/java/com/binance/chuyennd/tradecore/selector/LiveProfileC3.java").toPath()), StandardCharsets.UTF_8);
        assertTrue(lp.contains("boolean kill = killSwitchPresent(KILL_FILE) || BOOT_LOCK_MEM;"));
        String rt = new String(Files.readAllBytes(new File(
                "src/main/java/com/binance/chuyennd/c3live/runtime/C3LiveRuntime.java").toPath()), StandardCharsets.UTF_8);
        int a = rt.indexOf("BOOT_LOCK.applyOnce(mode == GatewayFactory.Mode.LIVE");
        int g = rt.indexOf("GatewayFactory.Result gr = GatewayFactory.create(");
        assertTrue(a > 0 && g > a);
    }
}
