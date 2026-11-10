package com.binance.chuyennd.tradecore.selector;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;

/** [V12 R4u3] C3-EXCL-FORCE: dry/live x true/false/vang x keys.env/keys_sub.env/thieu env (+ symlink). */
public class C3ExclForceTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void matrix() throws Exception {
        File d = tmp.newFolder("c3live");
        String main = new File(d, "keys.env").getAbsolutePath();
        String sub = new File(d, "keys_sub.env").getAbsolutePath();
        Files.write(new File(main).toPath(), new byte[0]);
        Files.write(new File(sub).toPath(), new byte[0]);
        String[] envs = {"true", "false", null};
        String[] keys = {null, main, sub};
        for (boolean live : new boolean[]{false, true}) {
            for (String env : envs) {
                for (String k : keys) {
                    boolean envVal = LegacySymbols.parseExclude(env);
                    boolean expect = envVal || (live && !sub.equals(k));
                    String tag = "live=" + live + " env=" + env + " key=" + k;
                    assertEquals(tag, expect, LegacySymbols.effectiveExclude(env, live, k, LegacySymbols::canonical));
                    String why = LegacySymbols.forceReason(envVal, live, k, LegacySymbols::canonical);
                    if (!envVal && live && !sub.equals(k)) assertNotNull(tag, why);
                    else assertNull(tag, why);
                }
            }
        }
    }

    @Test
    public void dryKeepsFalseWhateverKey() {
        assertEquals(false, LegacySymbols.effectiveExclude("false", false, null, LegacySymbols::canonical));
        assertEquals(false, LegacySymbols.effectiveExclude("false", false, "/root/.config/c3live/keys.env",
                LegacySymbols::canonical));
    }

    @Test
    public void symlinkNamedSubToMainIsForced() throws Exception {
        File d = tmp.newFolder("c3l");
        Path main = new File(d, "keys.env").toPath();
        Files.write(main, new byte[0]);
        File sd = tmp.newFolder("lnk");
        Path link = new File(sd, "keys_sub.env").toPath();
        Files.createSymbolicLink(link, main);
        assertEquals(true, LegacySymbols.effectiveExclude("false", true, link.toString(), LegacySymbols::canonical));
    }

    @Test
    public void blankAndOtherNamesForced() {
        assertEquals(true, LegacySymbols.effectiveExclude("false", true, "  ", LegacySymbols::canonical));
        assertEquals(true, LegacySymbols.effectiveExclude("false", true, "/x/keys_sub.env.bak", LegacySymbols::canonical));
        assertEquals(true, LegacySymbols.effectiveExclude("0", true, "/x/keys_main.env", LegacySymbols::canonical));
        // file chua ton tai nhung DUNG ten keys_sub.env => khong ep (jar se fail nap key rieng)
        assertEquals(false, LegacySymbols.effectiveExclude("false", true, "/nonexist/keys_sub.env",
                LegacySymbols::canonical));
    }
}
