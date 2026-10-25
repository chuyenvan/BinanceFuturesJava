package com.binance.chuyennd.c3live.runtime;

import com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.HttpRequest;
import org.junit.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.function.Predicate;

import static org.junit.Assert.*;

/**
 * [V12 vong 2b MASTER 10-25] Loai TradFi khoi feature cat ngang/thi truong CHI o c3_live (co
 * LIVE_C3_EXCLUDE_TRADFI_FEATURES, c3_live mac dinh 1; ngoai c3_live = 0 => cung map, byte-identical) + che token log.
 */
public class TradFiFeatureFilterTest {

    static KlineObjectSimple k(long t, float c) {
        KlineObjectSimple x = new KlineObjectSimple();
        x.startTime = t;
        x.priceOpen = c;
        x.priceClose = c;
        x.maxPrice = c * 1.01f;
        x.minPrice = c * 0.99f;
        x.totalUsdt = 1000;
        return x;
    }

    @Test
    public void flagOnlyOnC3Live() {
        assertFalse("ngoai c3_live (hook tat) => luon 0", C3LiveHook.decideExcludeTradFi(false, "1"));
        assertFalse(C3LiveHook.decideExcludeTradFi(false, null));
        assertTrue("c3_live mac dinh 1", C3LiveHook.decideExcludeTradFi(true, null));
        assertTrue(C3LiveHook.decideExcludeTradFi(true, "1"));
        assertFalse(C3LiveHook.decideExcludeTradFi(true, "0"));
        assertFalse(C3LiveHook.decideExcludeTradFi(true, "false"));
        // JVM test: khong co LIVE_PROFILE=c3_live => tat => dropTradFi tra CHINH map dau vao
        assertFalse(C3LiveHook.excludeTradFiFeatures());
        Map<String, KlineObjectSimple> m = new HashMap<>();
        m.put("TSLAUSDT", k(0, 1f));
        assertSame(m, C3LiveHook.dropTradFi(m));
        assertNull(C3LiveHook.tradFiFeatureFilterOrNull());
    }

    @Test
    public void filterCopiesWithoutTradFiAndKeepsOriginal() {
        Predicate<String> tf = s -> s.startsWith("TSLA") || s.startsWith("AAPL");
        Map<String, Integer> m = new LinkedHashMap<>();
        m.put("BTCUSDT", 1);
        m.put("TSLAUSDT", 2);
        m.put("ETHUSDT", 3);
        Map<String, Integer> out = C3LiveHook.filter(m, tf);
        assertNotSame(m, out);
        assertEquals(new ArrayList<>(java.util.Arrays.asList("BTCUSDT", "ETHUSDT")), new ArrayList<>(out.keySet()));
        assertEquals(3, m.size());
        Map<String, Integer> clean = new HashMap<>();
        clean.put("BTCUSDT", 1);
        assertSame("khong co TradFi => cung map", clean, C3LiveHook.filter(clean, tf));
        assertSame(m, C3LiveHook.filter(m, null));
    }

    @Test
    public void pipelineFeedsFilteredSnapshotsOnlyWhenFilterSet() {
        final long M = 60_000L;
        final long t0 = 1_792_900_000_000L - (1_792_900_000_000L % M);
        final Map<Long, Map<String, KlineObjectSimple>> data = new TreeMap<>();
        for (int i = 0; i < 5; i++) {
            Map<String, KlineObjectSimple> s = new HashMap<>();
            s.put("BTCUSDT", k(t0 + i * M, 100f));
            s.put("ALTUSDT", k(t0 + i * M, 1f));
            s.put("TSLAUSDT", k(t0 + i * M, 200f));
            data.put(t0 + i * M, s);
        }
        for (boolean filtered : new boolean[]{false, true}) {
            final List<TreeSet<String>> fed = new ArrayList<>();
            final List<TreeSet<String>> md = new ArrayList<>();
            final List<TreeSet<String>> extracted = new ArrayList<>();
            LiveFeaturePipeline.Sink sink = new LiveFeaturePipeline.Sink() {
                public void feed(long minute, Map<String, KlineObjectSimple> snap) { fed.add(new TreeSet<>(snap.keySet())); }
                public MarketFeatures extract(long minute, Map<String, KlineObjectSimple> snap, MarketDataObject m) {
                    extracted.add(new TreeSet<>(snap.keySet()));
                    return null;
                }
            };
            LiveFeaturePipeline p = new LiveFeaturePipeline(sink, snap -> {
                md.add(new TreeSet<>(snap.keySet()));
                return null;
            }, false, 3);
            if (filtered) p.setSnapshotFilter(s -> C3LiveHook.filter(s, x -> x.startsWith("TSLA")));
            TreeMap<Long, Map<String, KlineObjectSimple>> seed = new TreeMap<>();
            seed.put(t0, data.get(t0));
            seed.put(t0 + M, data.get(t0 + M));
            p.seed(seed);
            LiveFeaturePipeline.Result r = p.onTick(new LiveFeaturePipeline.MinuteSource() {
                public Map<String, KlineObjectSimple> snapshot(long minute) { return data.get(minute); }
                public LiveFeaturePipeline.SettleInfo await(long minute, int expected) {
                    return new LiveFeaturePipeline.SettleInfo(3, expected, 0L, 0);
                }
            }, t0 + 4 * M, null);
            assertEquals(4 + 1, md.size());   // 2 seed + 2 catch-up + 1 quyet dinh
            for (TreeSet<String> s : md) assertEquals(filtered ? 2 : 3, s.size());
            for (TreeSet<String> s : fed) assertEquals(!filtered, s.contains("TSLAUSDT"));
            assertEquals(!filtered, extracted.get(0).contains("TSLAUSDT"));
            assertEquals(!filtered, r.snapshot.containsKey("TSLAUSDT"));
            if (!filtered) assertSame("khong loc => snapshot goc (cung object)", data.get(t0 + 4 * M), r.snapshot);
        }
    }

    @Test
    public void telegramTokenRedactedInLogs() {
        String url = "https://api.telegram.org/bot6158000000:AAHfakeTOKENfakeTOKEN_x-1/sendMessage?chat_id=1&text=hi";
        String r = HttpRequest.redactSecrets("java.io.IOException: Server returned HTTP response code: 400 for URL: " + url);
        assertFalse(r, r.contains("AAHfake"));
        assertFalse(r, r.contains("6158000000"));
        assertTrue(r, r.contains("api.telegram.org/bot***/sendMessage"));
        assertEquals("null", HttpRequest.redactSecrets(null));
        assertTrue(HttpRequest.redactSecrets("bot123456:ABCDEFGHIJKLMNOP").contains("bot***"));
        assertEquals("https://fapi.binance.com/fapi/v1/time", HttpRequest.redactSecrets("https://fapi.binance.com/fapi/v1/time"));
    }
}
