package com.binance.chuyennd.c3live.adapter;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.attribute.FileTime;
import java.util.function.Supplier;

import static org.junit.Assert.*;

/** [A1 R4n ADV] KHONG commit. Ke ho: file cu bi coi la tuoi? */
public class A1R4nAdvFreshTest {

    static final long MIN = 60_000L;
    static final long NOW = 1_793_586_523_000L;
    static final long MAX = 45 * MIN;

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static byte[] json(long st, int n) {
        StringBuilder b = new StringBuilder("{\"serverTime\":" + st + ",\"symbols\":[");
        for (int i = 0; i < n; i++) b.append(i == 0 ? "" : ",").append("{\"symbol\":\"S").append(i).append("USDT\",\"status\":\"TRADING\"}");
        return b.append("]}").toString().getBytes(StandardCharsets.UTF_8);
    }

    static void write(File f, byte[] b, long mtime) throws Exception {
        Files.write(f.toPath(), b);
        Files.setLastModifiedTime(f.toPath(), FileTime.fromMillis(mtime));
    }

    static void meta(File f, long fetched, String sha, int n) throws Exception {
        Files.write(new File(f.getPath() + GatewayFactory.META_SUFFIX).toPath(),
                ("{\"fetchedAtMs\":" + fetched + ",\"sha256\":\"" + sha + "\",\"n_symbols\":" + n + "}").getBytes(StandardCharsets.UTF_8));
    }

    static boolean ok(Supplier<ExchangeInfo> s) {
        try {
            s.get();
            return true;
        } catch (IllegalStateException e) {
            return false;
        }
    }

    Supplier<ExchangeInfo> src(File f, long[] now) {
        return GatewayFactory.freshFileSource(f, () -> now[0], MAX);
    }

    /** File cu 60' + sidecar dung, mtime bi touch => van CU (sidecar thang mtime). */
    @Test
    public void touchedOldFile_withSidecar_staysStale() throws Exception {
        File f = tmp.newFile("x.json");
        byte[] b = json(NOW - 150 * MIN, 3);
        write(f, b, NOW);
        meta(f, NOW - 60 * MIN, GatewayFactory.sha256Hex(b), 3);
        assertFalse(ok(src(f, new long[]{NOW})));
    }

    /** KE HO (fallback mtime): sidecar mat + file cu bi touch => coi la tuoi. */
    @Test
    public void touchedOldFile_noSidecar_mustNotBeFresh() throws Exception {
        File f = tmp.newFile("y.json");
        write(f, json(NOW - 150 * MIN, 3), NOW);
        assertFalse("khong sidecar + mtime bi cham => file cu thanh tuoi", ok(src(f, new long[]{NOW})));
    }

    /** Sidecar cua file khac (sha lech) => tu choi; n_symbols lech => tu choi. */
    @Test
    public void sidecarFromOtherFile_rejected() throws Exception {
        File f = tmp.newFile("z.json");
        byte[] b = json(NOW, 3);
        write(f, b, NOW);
        meta(f, NOW, GatewayFactory.sha256Hex(json(NOW - 1, 3)), 3);
        assertFalse(ok(src(f, new long[]{NOW})));
        meta(f, NOW, GatewayFactory.sha256Hex(b), 4);
        assertFalse(ok(src(f, new long[]{NOW})));
    }

    /** Dong ho: fetchedAt tuong lai > 5' => tu choi; 3' => nhan; dong ho JVM nhay lui 50' => tuoi am => nhan (cung may). */
    @Test
    public void clockSkew() throws Exception {
        File f = tmp.newFile("w.json");
        byte[] b = json(NOW - 88 * MIN, 3);
        write(f, b, NOW);
        meta(f, NOW + 10 * MIN, GatewayFactory.sha256Hex(b), 3);
        assertFalse(ok(src(f, new long[]{NOW})));
        meta(f, NOW + 3 * MIN, GatewayFactory.sha256Hex(b), 3);
        assertTrue(ok(src(f, new long[]{NOW})));
    }

    /** Refresh dut giua chung: file moi da mv, sidecar con cu => tu choi (fail-closed) cho toi khi sidecar moi toi. */
    @Test
    public void refreshInterruptedBetweenMoves() throws Exception {
        File f = tmp.newFile("v.json");
        byte[] old = json(NOW - 100 * MIN, 3);
        write(f, old, NOW - 20 * MIN);
        meta(f, NOW - 20 * MIN, GatewayFactory.sha256Hex(old), 3);
        long[] now = {NOW};
        Supplier<ExchangeInfo> s = src(f, now);
        assertTrue(ok(s));
        byte[] nw = json(NOW - 99 * MIN, 3);
        write(f, nw, NOW);
        assertFalse("file moi + sidecar cu => tu choi", ok(s));
        meta(f, NOW, GatewayFactory.sha256Hex(nw), 3);
        assertTrue(ok(s));
    }

    /** Rollback / cp -p khoi phuc file cu + sidecar cu (nhat quan) => van CU. */
    @Test
    public void restoredOldPair_staysStale() throws Exception {
        File f = tmp.newFile("u.json");
        byte[] b = json(NOW - 200 * MIN, 3);
        write(f, b, NOW - 120 * MIN);
        meta(f, NOW - 120 * MIN, GatewayFactory.sha256Hex(b), 3);
        assertFalse(ok(src(f, new long[]{NOW})));
    }
}
