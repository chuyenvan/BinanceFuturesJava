package com.binance.chuyennd.c3live.runtime;

import com.binance.chuyennd.c3live.adapter.GatewayFactory;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.nio.file.Files;

import static org.junit.Assert.*;

/** [W3A muc 2] nhan tai khoan trong dong "[C3-LIVE] khoi dong adapter=" ? khong con "CHINH" cung, khong in key/duong dan. */
public class C3LiveAccountLabelTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void live_keysSub_laSUB_coSha8() throws Exception {
        File dir = tmp.newFolder("cfg_w3a");
        File sub = new File(dir, "keys_sub.env");
        assertTrue(sub.createNewFile());
        String l = C3LiveRuntime.accountLabel(GatewayFactory.Mode.LIVE, sub.getPath(), "43820b5b",
                C3LiveRuntime::canonicalPath, null);
        assertEquals("tai_khoan=SUB key_file=keys_sub.env key_sha8=43820b5b recon=QTY(pham vi c3)", l);
        assertFalse("khong in thu muc", l.contains(dir.getPath()));
    }

    @Test
    public void live_keysChinh_vaVang_laCHINH() {
        assertEquals("tai_khoan=CHINH key_file=keys.env key_sha8=3ef771e0 recon=QTY(pham vi c3)",
                C3LiveRuntime.accountLabel(GatewayFactory.Mode.LIVE, "/root/.config/c3live/keys.env", "3ef771e0", p -> p, null));
        assertEquals("tai_khoan=CHINH key_file=keys.env key_sha8=? recon=QTY(pham vi c3)",
                C3LiveRuntime.accountLabel(GatewayFactory.Mode.LIVE, null, null, p -> p, null));
        assertEquals("tai_khoan=CHINH key_file=keys.env key_sha8=? recon=QTY(pham vi c3)",
                C3LiveRuntime.accountLabel(GatewayFactory.Mode.LIVE, "  ", "", p -> p, ""));
    }

    @Test
    public void live_symlinkTenSubTroSangKeysChinh_laCHINH() throws Exception {
        File dir = tmp.newFolder("cfg2_w3a");
        File main = new File(dir, "keys.env");
        assertTrue(main.createNewFile());
        File link = new File(dir, "keys_sub.env");
        Files.createSymbolicLink(link.toPath(), main.toPath());
        String l = C3LiveRuntime.accountLabel(GatewayFactory.Mode.LIVE, link.getPath(), "3ef771e0",
                C3LiveRuntime::canonicalPath, null);
        assertEquals("tai_khoan=CHINH key_file=keys_sub.env key_file_that=keys.env key_sha8=3ef771e0 recon=QTY(pham vi c3)", l);
    }

    @Test
    public void dry_khongDungKey() {
        assertEquals("tai_khoan=DRY(khong dung key) recon=QTY(pham vi c3)",
                C3LiveRuntime.accountLabel(GatewayFactory.Mode.DRY, "/x/keys_sub.env", null, p -> p, null));
    }

    @Test
    public void rollbackV1_inChuoiCu() {
        assertEquals("tai_khoan=CHINH(pham vi c3)",
                C3LiveRuntime.accountLabel(GatewayFactory.Mode.LIVE, "/x/keys_sub.env", "43820b5b", p -> p, "true"));
        assertEquals("tai_khoan=CHINH(pham vi c3)",
                C3LiveRuntime.accountLabel(GatewayFactory.Mode.DRY, null, null, p -> p, " TRUE "));
        assertNotEquals("tai_khoan=CHINH(pham vi c3)",
                C3LiveRuntime.accountLabel(GatewayFactory.Mode.LIVE, "/x/keys_sub.env", "43820b5b", p -> p, "false"));
    }

    @Test
    public void nguonDongKhoiDong_dungAccountLabel_khongConChuoiCung() throws Exception {
        String s = new String(Files.readAllBytes(new File(
                "src/main/java/com/binance/chuyennd/c3live/runtime/C3LiveRuntime.java").toPath()), "UTF-8");
        int i = s.indexOf("\"[C3-LIVE] khoi dong adapter=\"");
        assertTrue(i > 0);
        String line = s.substring(i, s.indexOf("LOG.warn(", i));
        assertTrue(line.contains("accountLabel(mode, Cfg.get(LegacySymbols.KEY_KEYS_FILE)"));
        assertFalse(line.contains("tai_khoan=CHINH(pham vi c3)"));
    }
}
