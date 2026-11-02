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

/**
 * [V12 R4n MAJ-X A1 R4M] tuoi exchangeInfo theo LUC TAI (sidecar / mtime), KHONG theo serverTime (anh chup cache cua san:
 * do 11-02 09:28 cu 88', lui 6 ms giua 2 lan tai).
 */
public class GatewayFactoryFreshR4nTest {

    private static final long MIN = 60_000L;
    private static final long NOW = 1_793_581_261_893L + 88 * MIN;   // 11-02 09:29 +07
    private static final long MAX = 45 * MIN;
    private static final String A64 = new String(new char[64]).replace('\0', 'a');

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    private static String json(long serverTime) {
        return "{\"serverTime\":" + serverTime + ",\"symbols\":[{\"symbol\":\"AAAUSDT\",\"status\":\"TRADING\"},"
                + "{\"symbol\":\"BBBUSDT\",\"status\":\"TRADING\"},{\"symbol\":\"CCCUSDT\",\"status\":\"TRADING\"}]}";
    }

    /** ghi file + sidecar (nhu cron); mtime khac moi lan de cache fileSource nap lai. */
    private File put(File f, long serverTime, long fetchedAt, String metaOverride, long mtime) throws Exception {
        byte[] b = json(serverTime).getBytes(StandardCharsets.UTF_8);
        Files.write(f.toPath(), b);
        Files.setLastModifiedTime(f.toPath(), FileTime.fromMillis(mtime));
        File m = new File(f.getPath() + GatewayFactory.META_SUFFIX);
        if (metaOverride == null) {
            Files.write(m.toPath(), ("{\"fetchedAtMs\":" + fetchedAt + ",\"sha256\":\"" + GatewayFactory.sha256Hex(b)
                    + "\",\"n_symbols\":3}").getBytes(StandardCharsets.UTF_8));
        } else {
            Files.write(m.toPath(), metaOverride.getBytes(StandardCharsets.UTF_8));
        }
        return f;
    }

    private static void rejects(Supplier<ExchangeInfo> s, String part) {
        try {
            s.get();
            fail("phai tu choi: " + part);
        } catch (IllegalStateException e) {
            assertTrue(e.getMessage(), e.getMessage().contains(part));
        }
    }

    @Test
    public void serverTime88mOld_justFetched_ok_and_regress6ms_ok() throws Exception {
        File f = tmp.newFile("c3live_exchangeInfo.json");
        long st = NOW - 88 * MIN;
        put(f, st, NOW - 5_000L, null, NOW - 5_000L);
        Supplier<ExchangeInfo> s = GatewayFactory.freshFileSource(f, () -> NOW, MAX);
        assertEquals("serverTime cu 88' nhung vua tai => DAT", st, s.get().getServerTime());
        put(f, st - 6, NOW, null, NOW);                     // lan tai sau: serverTime LUI 6 ms
        assertEquals("serverTime lui 6 ms => DAT", st - 6, s.get().getServerTime());
        put(f, NOW - 30 * 60 * MIN, NOW, null, NOW + 1);    // serverTime lech 30 h => chi canh bao
        assertNotNull(s.get());
    }

    @Test
    public void fetchedOver45m_stale() throws Exception {
        File f = tmp.newFile("c3live_exchangeInfo.json");
        put(f, NOW, NOW - 46 * MIN, null, NOW);            // serverTime "moi" nhung tai 46' truoc (sidecar) => CU
        rejects(GatewayFactory.freshFileSource(f, () -> NOW, MAX), "CU");
        put(f, NOW, NOW + 6 * MIN, null, NOW + 1);          // fetchedAt o tuong lai > 5'
        rejects(GatewayFactory.freshFileSource(f, () -> NOW, MAX), "CU");
    }

    @Test
    public void noSidecar_usesMtime() throws Exception {
        File f = tmp.newFile("c3live_exchangeInfo.json");
        put(f, NOW - 88 * MIN, 0L, null, NOW - MIN);
        assertTrue(new File(f.getPath() + GatewayFactory.META_SUFFIX).delete());
        assertNotNull(GatewayFactory.freshFileSource(f, () -> NOW, MAX).get());
        Files.setLastModifiedTime(f.toPath(), FileTime.fromMillis(NOW - 46 * MIN));
        rejects(GatewayFactory.freshFileSource(f, () -> NOW, MAX), "CU");
    }

    @Test
    public void corruptSidecar_failClosed() throws Exception {
        File f = tmp.newFile("c3live_exchangeInfo.json");
        put(f, NOW, 0L, "{khong phai json", NOW);
        rejects(GatewayFactory.freshFileSource(f, () -> NOW, MAX), "HONG");
        put(f, NOW, 0L, "{\"sha256\":\"" + A64 + "\",\"n_symbols\":3}", NOW + 1);
        rejects(GatewayFactory.freshFileSource(f, () -> NOW, MAX), "thieu/sai truong");
        put(f, NOW, 0L, "{\"fetchedAtMs\":" + NOW + ",\"sha256\":\"" + A64 + "\",\"n_symbols\":3}", NOW + 2);
        rejects(GatewayFactory.freshFileSource(f, () -> NOW, MAX), "sha256 KHONG khop");
        String sha = GatewayFactory.sha256Hex(json(NOW).getBytes(StandardCharsets.UTF_8));
        put(f, NOW, 0L, "{\"fetchedAtMs\":" + NOW + ",\"sha256\":\"" + sha + "\",\"n_symbols\":4}", NOW + 3);
        rejects(GatewayFactory.freshFileSource(f, () -> NOW, MAX), "n_symbols");
        put(f, NOW, 0L, "{\"fetchedAtMs\":0,\"sha256\":\"" + sha + "\",\"n_symbols\":3}", NOW + 4);
        rejects(GatewayFactory.freshFileSource(f, () -> NOW, MAX), "khong hop le");
    }
}
