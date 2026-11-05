package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.c3live.adapter.GatewayFactory;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import com.binance.chuyennd.c3live.universe.TradFiClassifier;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.junit.After;
import org.junit.Assume;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.FileTime;
import java.util.TreeSet;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Supplier;
import java.util.zip.GZIPInputStream;

import static org.junit.Assert.*;

/**
 * [V12 R4e MAJOR-1] Symbol niem yet SAU deploy: truoc khi file lam moi toi => bi loai o CA bo loc tin hieu (fail-closed) va R7
 * (khong niem yet); file lam moi (cron 242, serverTime moi hon) toi => vao CA HAI (A1 reload theo mtime, R7 doc CUNG file).
 * File qua tuoi => R7 tu choi snapshot (giu cu).
 */
public class UniverseA1ListingRefreshTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @After
    public void tearDown() {
        UniverseA1Filter.resetForTest();
    }

    @Test
    public void listingAfterDeployEntersA1AndR7AfterRefresh() throws Exception {
        File gz = new File("/home/ubuntu/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz");
        Assume.assumeTrue(gz.isFile());
        JsonObject full;
        try (InputStreamReader r = new InputStreamReader(new GZIPInputStream(Files.newInputStream(gz.toPath())), StandardCharsets.UTF_8)) {
            full = JsonParser.parseReader(r).getAsJsonObject();
        }
        long st0 = full.get("serverTime").getAsLong();
        // chon 1 symbol COIN mua duoc tren snapshot day du = "listing moi"
        Path pFull = tmp.getRoot().toPath().resolve("full.json");
        Files.write(pFull, full.toString().getBytes(StandardCharsets.UTF_8));
        ExchangeInfo eiFull = GatewayFactory.fileSource(pFull.toFile()).get();
        SymbolUniverseLive probe = new SymbolUniverseLive(SymbolUniverseLive.Config.defaults().strictCoin()
                .withClassifier(TradFiClassifier.universeA1()), () -> eiFull, m -> { });
        assertNotNull(probe.apply(eiFull, st0));
        String nw = new TreeSet<>(probe.tradableSymbols()).first();
        assertFalse(probe.whyNotBuyable(nw, st0).isPresent());

        // v1 = snapshot luc deploy KHONG co nw
        JsonObject v1 = full.deepCopy();
        JsonArray a1 = new JsonArray();
        for (JsonElement e : full.getAsJsonArray("symbols")) if (!nw.equals(e.getAsJsonObject().get("symbol").getAsString())) a1.add(e);
        v1.add("symbols", a1);
        Path f = tmp.getRoot().toPath().resolve("c3live_exchangeInfo.json");
        Files.write(f, v1.toString().getBytes(StandardCharsets.UTF_8));
        Files.setLastModifiedTime(f, FileTime.fromMillis(st0 + 60_000L - 120_000L));   // [R4n] tuoi theo LUC TAI (mtime, khong sidecar)
        AtomicLong clock = new AtomicLong(st0 + 60_000L);
        UniverseA1Filter.setConfigForTest(true, f, true);
        UniverseA1Filter.initEager();
        Supplier<ExchangeInfo> src = GatewayFactory.freshFileSource(f.toFile(), clock::get, 45L * 60_000L);
        SymbolUniverseLive r7 = new SymbolUniverseLive(SymbolUniverseLive.Config.defaults().strictCoin()
                .withClassifier(TradFiClassifier.universeA1()), src, m -> { });
        r7.refresh(clock.get());
        long t = clock.get();
        assertTrue("A1: listing sau snapshot => loai (fail-closed)", UniverseA1Filter.isExcluded(nw, t));
        assertTrue("R7: chua niem yet", r7.whyNotBuyable(nw, t).isPresent());

        // file lam moi (serverTime + 15') co nw => vao CA HAI
        JsonObject v2 = full.deepCopy();
        v2.addProperty("serverTime", st0 + 15 * 60_000L);
        Files.write(f, v2.toString().getBytes(StandardCharsets.UTF_8));
        Files.setLastModifiedTime(f, FileTime.fromMillis(st0 + 15 * 60_000L));
        clock.set(st0 + 16 * 60_000L);
        UniverseA1Filter.resetStatForTest();
        t = clock.get();
        assertFalse("A1: sau lam moi => vao universe", UniverseA1Filter.isExcluded(nw, t));
        r7.refresh(t);
        assertFalse("R7: sau lam moi => mua duoc", r7.whyNotBuyable(nw, t).isPresent());
        assertEquals(233, UniverseA1Filter.excludedSymbols().size());   // [PREMARKET-b] 229 TF + 3 INDEX + 1 PREMARKET

        // file qua tuoi (cron hong) => R7 tu choi snapshot moi (nem trong supplier), giu snapshot cu
        clock.set(st0 + 15 * 60_000L + 46 * 60_000L);
        try {
            src.get();
            fail("file qua 45' phai bi tu choi");
        } catch (IllegalStateException e) {
            assertTrue(e.getMessage(), e.getMessage().contains("CU"));
        }
    }
}
