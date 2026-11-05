package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.junit.After;
import org.junit.Assume;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.FileTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.zip.GZIPInputStream;

import static org.junit.Assert.*;

/**
 * [V12 R4d] Universe A1: bo phan loai chung, point-in-time (MDT), fail-fast (loi init nem lai MOI lan goi), reload giu snapshot
 * cu khi file moi hong, parity live (diem loc sau tickerWindow.read + LiveFeaturePipeline) == replay (filterMinutes) o S1/ung
 * vien, breadth, ALT_EW, gate; co TAT = y nguyen (cung object).
 */
public class UniverseA1FilterTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    static final long S0 = 1793072475507L;          // serverTime snapshot that 2026-10-27
    static final long MDT_OB = 1792574400000L;      // onboardDate MDTUSDT (TF Medtronic) 2026-10-21
    static final long MIN = 60_000L;
    static final String[] CRYPTO = {"BTCUSDT", "ETHUSDT", "AAAUSDT", "BBBUSDT", "UNKUSDT"};   // [PREMARKET-b] PREUSDT bi loai
    static final String[] BANNED = {"AAPLUSDT", "GOLDUSDT", "EURUSDT", "ALLUSDT", "DEFIUSDT", "TF000USDT"};

    @After
    public void tearDown() {
        UniverseA1Filter.resetForTest();
    }

    // ------------------------------------------------------------------ fixture

    private static JsonObject sym(String s, String ct, String ut, long ob) {
        JsonObject o = new JsonObject();
        o.addProperty("symbol", s);
        if (ct != null) o.addProperty("contractType", ct);
        if (ut != null) o.addProperty("underlyingType", ut);
        o.addProperty("onboardDate", ob);
        o.addProperty("status", "TRADING");
        o.addProperty("quoteAsset", "USDT");
        return o;
    }

    /** nTf hop dong TRADIFI_PERPETUAL TF000..; cong them AAPL (TRADIFI), GOLD/EUR (PERPETUAL + COMMODITY/FX), MDT, INDEX, crypto. */
    private Path exinfo(String name, int nTf, boolean serverTime) throws Exception {
        JsonArray a = new JsonArray();
        for (String c : new String[]{"BTCUSDT", "ETHUSDT", "AAAUSDT", "BBBUSDT"}) a.add(sym(c, "PERPETUAL", "COIN", 1569398400000L));
        a.add(sym("PREUSDT", "PERPETUAL", "PREMARKET", 1792916100000L));
        a.add(sym("UNKUSDT", "PERPETUAL", null, 1600000000000L));
        a.add(sym("ALLUSDT", "PERPETUAL", "INDEX", 1600000000000L));
        a.add(sym("DEFIUSDT", "PERPETUAL", "INDEX", 1600000000000L));
        a.add(sym("AAPLUSDT", "TRADIFI_PERPETUAL", "EQUITY", 1780000000000L));
        a.add(sym("GOLDUSDT", "PERPETUAL", "COMMODITY", 1780000000000L));
        a.add(sym("EURUSDT", "PERPETUAL", "FX", 1780000000000L));
        a.add(sym("MDTUSDT", "TRADIFI_PERPETUAL", "EQUITY", MDT_OB));
        for (int i = 0; i < nTf; i++) a.add(sym(String.format("TF%03dUSDT", i), "TRADIFI_PERPETUAL", "EQUITY", 1780000000000L));
        JsonObject root = new JsonObject();
        if (serverTime) root.addProperty("serverTime", S0);
        root.add("symbols", a);
        Path p = tmp.getRoot().toPath().resolve(name);
        Files.write(p, root.toString().getBytes(StandardCharsets.UTF_8));
        return p;
    }

    /** 48 TF + AAPL + MDT = 50 hop dong TRADIFI (dung nguong R4b). */
    private Path ok() throws Exception {
        return exinfo("ok.json", 48, true);
    }

    private static KlineObjectSimple bar(float open, float close, long t) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.priceOpen = open;
        k.priceClose = close;
        k.maxPrice = Math.max(open, close);
        k.minPrice = Math.min(open, close);
        k.totalUsdt = 1000f;
        k.startTime = t;
        return k;
    }

    /** 1 phut: crypto +-nho, TF/INDEX/MDT roi manh (de breadth/ALT_EW lech neu lot vao). */
    private static Map<String, KlineObjectSimple> minute(long t, int i) {
        Map<String, KlineObjectSimple> m = new LinkedHashMap<>();
        float c = 100f + (i % 7);
        for (String s : CRYPTO) m.put(s, bar(100f, c * (s.hashCode() % 3 == 0 ? 1.001f : 0.999f), t));
        for (String s : BANNED) m.put(s, bar(100f, 90f - (i % 5), t));
        m.put("MDTUSDT", bar(100f, 92f + (i % 3), t));
        m.put("NEWUSDT", bar(100f, 95f, t));   // khong co trong snapshot
        return m;
    }

    private static Set<String> notAllowed(long t) {
        Set<String> s = new HashSet<>();
        for (String b : BANNED) s.add(b);
        if (t >= MDT_OB) s.add("MDTUSDT");
        if (t > S0) s.add("NEWUSDT");
        return s;
    }

    // ------------------------------------------------------------------ dinh nghia

    @Test
    public void classifier_definition() {
        assertEquals(UniverseA1Classifier.Kind.TRADFI, UniverseA1Classifier.classify("TRADIFI_PERPETUAL", "EQUITY"));
        assertEquals(UniverseA1Classifier.Kind.TRADFI, UniverseA1Classifier.classify("TRADIFI_PERPETUAL", null));
        for (String ut : new String[]{"EQUITY", "HK_EQUITY", "KR_EQUITY", "CN_EQUITY", "COMMODITY", "FX"}) {
            assertEquals(ut, UniverseA1Classifier.Kind.TRADFI, UniverseA1Classifier.classify("PERPETUAL", ut));
        }
        assertEquals(UniverseA1Classifier.Kind.INDEX, UniverseA1Classifier.classify("PERPETUAL", "INDEX"));
        assertEquals(UniverseA1Classifier.Kind.CRYPTO, UniverseA1Classifier.classify("PERPETUAL", "COIN"));
        assertEquals(UniverseA1Classifier.Kind.PREMARKET, UniverseA1Classifier.classify("PERPETUAL", "PREMARKET"));
        assertTrue("[PREMARKET-b]", UniverseA1Classifier.excluded(UniverseA1Classifier.Kind.PREMARKET));
        assertEquals(UniverseA1Classifier.Kind.UNCLASSIFIED, UniverseA1Classifier.classify("PERPETUAL", null));
        assertTrue(UniverseA1Classifier.excluded(UniverseA1Classifier.Kind.TRADFI));
        assertTrue(UniverseA1Classifier.excluded(UniverseA1Classifier.Kind.INDEX));
        assertFalse(UniverseA1Classifier.excluded(UniverseA1Classifier.Kind.UNCLASSIFIED));
        assertNull(UniverseA1Classifier.sourceProblem(900, 900, 900, 50));
        assertNotNull(UniverseA1Classifier.sourceProblem(900, 900, 900, 49));
        assertTrue(UniverseA1Classifier.tradFiDropped(229, 160));
        assertFalse(UniverseA1Classifier.tradFiDropped(229, 161));
    }

    /** Snapshot that 10-27: 229 TF, 3 INDEX; dinh nghia MASTER == luat bu TradFiClassifier (0 khac biet); filter loai dung tap do. */
    @Test
    public void realSnapshot_1027() throws Exception {
        Path gz = Paths.get("/home/ubuntu/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz");
        Assume.assumeTrue(Files.isRegularFile(gz));
        Path raw = tmp.getRoot().toPath().resolve("ex1027.json");
        JsonObject root;
        try (InputStreamReader r = new InputStreamReader(new GZIPInputStream(Files.newInputStream(gz)), StandardCharsets.UTF_8)) {
            root = JsonParser.parseReader(r).getAsJsonObject();
        }
        Files.write(raw, root.toString().getBytes(StandardCharsets.UTF_8));
        Set<String> tf = new HashSet<>();
        Set<String> idx = new HashSet<>();
        Set<String> pre = new HashSet<>();
        for (com.google.gson.JsonElement e : root.getAsJsonArray("symbols")) {
            JsonObject o = e.getAsJsonObject();
            String ct = o.has("contractType") ? o.get("contractType").getAsString() : null;
            String ut = o.has("underlyingType") ? o.get("underlyingType").getAsString() : null;
            UniverseA1Classifier.Kind k = UniverseA1Classifier.classify(ct, ut);
            boolean complement = (ct != null && ct.toUpperCase().contains("TRADIFI"))
                    || (ut != null && !"COIN".equals(ut) && !"INDEX".equals(ut) && !"PREMARKET".equals(ut));
            assertEquals(o.get("symbol").getAsString(), complement, k == UniverseA1Classifier.Kind.TRADFI);
            if (k == UniverseA1Classifier.Kind.TRADFI) tf.add(o.get("symbol").getAsString());
            if (k == UniverseA1Classifier.Kind.INDEX) idx.add(o.get("symbol").getAsString());
            if (k == UniverseA1Classifier.Kind.PREMARKET) pre.add(o.get("symbol").getAsString());
        }
        assertEquals("[PREMARKET-b] snapshot 10-27: 1 PREMARKET", java.util.Collections.singleton("PREDICTUSDT"), pre);
        assertEquals(229, tf.size());
        assertEquals(new HashSet<>(java.util.Arrays.asList("ALLUSDT", "BTCDOMUSDT", "DEFIUSDT")), idx);
        UniverseA1Filter.setConfigForTest(true, raw, true);
        UniverseA1Filter.initEager();
        Set<String> exp = new HashSet<>(tf);
        exp.addAll(idx);
        exp.addAll(pre);
        assertEquals(exp, UniverseA1Filter.excludedSymbols());
        long t = S0 + 86_400_000L;
        assertFalse("crypto co trong snapshot KHONG bi loai sau serverTime", UniverseA1Filter.isExcluded("BTCUSDT", t));
        assertFalse(UniverseA1Filter.isExcluded("SPXUSDT", t));
        assertTrue("[PREMARKET-b] PREMARKET bi loai", UniverseA1Filter.isExcluded("PREDICTUSDT", t));
        assertTrue(UniverseA1Filter.isExcluded("MDTUSDT", t));
        assertFalse("MDT truoc onboard TF = crypto", UniverseA1Filter.isExcluded("MDTUSDT", MDT_OB - 1));
        assertTrue(UniverseA1Filter.isExcluded("BTCDOMUSDT", t));
    }

    // ------------------------------------------------------------------ co TAT

    @Test
    public void flagOff_identityEverywhere() throws Exception {
        UniverseA1Filter.resetForTest();   // doc env: UNIVERSE_A1 khong dat => TAT
        assertFalse(UniverseA1Filter.isActive());
        Map<String, KlineObjectSimple> m = minute(S0 + MIN, 1);
        assertSame(m, UniverseA1Filter.filter(m, S0 + MIN));
        TreeMap<Long, Map<String, KlineObjectSimple>> d = new TreeMap<>();
        d.put(S0 + MIN, m);
        assertSame(d, UniverseA1Filter.filterMinutes(d));
        assertFalse(UniverseA1Filter.isExcluded("AAPLUSDT", S0 + MIN));
        // tat qua cau hinh test cung vay
        UniverseA1Filter.setConfigForTest(false, ok(), true);
        assertSame(m, UniverseA1Filter.filter(m, S0 + MIN));
        assertEquals("off", UniverseA1Filter.source());
        // gate (LiveFeaturePipeline): co tat => CUNG object vao md/sink
        Cap c = new Cap();
        LiveFeaturePipeline p = new LiveFeaturePipeline(c, c, true, 3);
        p.seed(d);
        assertSame(m, c.fed.get(0));
    }

    // ------------------------------------------------------------------ co BAT

    @Test
    public void flagOn_excludesTfIndexPointInTime_keepsCrypto() throws Exception {
        UniverseA1Filter.setConfigForTest(true, ok(), true);
        UniverseA1Filter.initEager();
        assertTrue(UniverseA1Filter.isActive());
        long late = S0 + 3 * 86_400_000L;
        for (String s : CRYPTO) assertFalse(s, UniverseA1Filter.isExcluded(s, late));   // UNK (thieu underlyingType) + PREMARKET giu
        for (String s : BANNED) assertTrue(s, UniverseA1Filter.isExcluded(s, late));
        assertTrue("[PREMARKET-b] PREMARKET loai khoi A1", UniverseA1Filter.isExcluded("PREUSDT", late));
        // MDT point-in-time
        assertFalse(UniverseA1Filter.isExcluded("MDTUSDT", MDT_OB - MIN));
        assertTrue(UniverseA1Filter.isExcluded("MDTUSDT", MDT_OB));
        // symbol niem yet sau snapshot: truoc serverTime giu, sau => loai (fail-closed)
        assertFalse(UniverseA1Filter.isExcluded("NEWUSDT", S0));
        assertTrue(UniverseA1Filter.isExcluded("NEWUSDT", S0 + 1));
        assertEquals(52, (int) UniverseA1Filter.stats().get("tradfi"));   // 48 TF + AAPL + MDT + GOLD + EUR
        assertEquals(2, (int) UniverseA1Filter.stats().get("index"));
    }

    @Test
    public void initFailure_rethrownOnEveryCall() throws Exception {
        Path[] bad = {tmp.getRoot().toPath().resolve("missing.json"), exinfo("noserver.json", 48, false),
                exinfo("few.json", 47, true), Files.write(tmp.getRoot().toPath().resolve("broken.json"), "{not json".getBytes())};
        for (Path p : bad) {
            UniverseA1Filter.setConfigForTest(true, p, true);
            RuntimeException first = null;
            try {
                UniverseA1Filter.initEager();
                fail("phai nem: " + p);
            } catch (IllegalStateException e) {
                first = e;
            }
            for (int i = 0; i < 3; i++) {
                try {
                    if (i == 0) UniverseA1Filter.isExcluded("BTCUSDT", S0);
                    else if (i == 1) UniverseA1Filter.filter(minute(S0, 0), S0);
                    else UniverseA1Filter.isActive();
                    fail("lan goi " + i + " phai nem lai loi init: " + p);
                } catch (IllegalStateException e) {
                    assertSame(first, e);
                }
            }
        }
        // dung nguong 50 TRADIFI => hop le
        UniverseA1Filter.setConfigForTest(true, exinfo("fifty.json", 48, true), true);
        UniverseA1Filter.initEager();
        assertTrue(UniverseA1Filter.isActive());
    }

    @Test
    public void reload_newValidAccepted_newBrokenKeepsOld() throws Exception {
        Path p = ok();
        UniverseA1Filter.setConfigForTest(true, p, true);
        UniverseA1Filter.initEager();
        long late = S0 + 86_400_000L;
        assertTrue(UniverseA1Filter.isExcluded("NEWUSDT", late));
        // file moi hong (JSON vo) => GIU snapshot cu, KHONG nem
        Files.write(p, "{broken".getBytes());
        Files.setLastModifiedTime(p, FileTime.fromMillis(System.currentTimeMillis() + 5_000L));
        UniverseA1Filter.resetStatForTest();
        assertTrue(UniverseA1Filter.isExcluded("AAPLUSDT", late));
        assertFalse(UniverseA1Filter.isExcluded("BTCUSDT", late));
        // file moi hop le, co them NEWUSDT (crypto) => nhan
        JsonObject root = JsonParser.parseString(new String(Files.readAllBytes(exinfo("v2.json", 48, true)))).getAsJsonObject();
        root.getAsJsonArray("symbols").add(sym("NEWUSDT", "PERPETUAL", "COIN", S0 - MIN));
        Files.write(p, root.toString().getBytes(StandardCharsets.UTF_8));
        Files.setLastModifiedTime(p, FileTime.fromMillis(System.currentTimeMillis() + 10_000L));
        UniverseA1Filter.resetStatForTest();
        assertFalse(UniverseA1Filter.isExcluded("NEWUSDT", late));
        assertTrue(UniverseA1Filter.isExcluded("AAPLUSDT", late));
    }

    // ------------------------------------------------------------------ parity live == replay

    /** 240 phut quanh moc onboard MDT: tap live (diem loc sau tickerWindow.read) == replay (filterMinutes) == gate (pipeline). */
    @Test
    public void liveReplayGate_identicalSets_noTfIndex() throws Exception {
        UniverseA1Filter.setConfigForTest(true, ok(), true);
        UniverseA1Filter.initEager();
        TreeMap<Long, Map<String, KlineObjectSimple>> day = new TreeMap<>();
        long t0 = MDT_OB - 120 * MIN;
        for (int i = 0; i < 240; i++) day.put(t0 + i * MIN, minute(t0 + i * MIN, i));
        TreeMap<Long, Map<String, KlineObjectSimple>> replay = UniverseA1Filter.filterMinutes(day);
        Cap c = new Cap();
        LiveFeaturePipeline p = new LiveFeaturePipeline(c, c, true, 3);
        TreeMap<Long, Map<String, KlineObjectSimple>> seed = new TreeMap<>(day.headMap(t0 + 200 * MIN));
        p.seed(seed);
        Src src = new Src(day);
        for (long t = t0 + 200 * MIN; t < t0 + 240 * MIN; t += 2 * MIN) p.onTick(src, t, null);   // decision + catch-up
        assertEquals(239, c.byMinute.size());   // seed 0..199 + tick/catch-up 200..238 (phut 239 chua toi luot quyet dinh)
        assertFalse("prod path luon goi md.update(snap, ts)", c.mdTs.contains(Long.MIN_VALUE));
        for (int i = 0; i < 239; i++) {
            long t = t0 + i * MIN;
            Set<String> live = UniverseA1Filter.filter(day.get(t), t).keySet();   // = symbol2FinalTicker / S1 / ung vien / funding-OI
            assertEquals("phut " + i, live, replay.get(t).keySet());
            assertEquals("gate phut " + i, live, c.byMinute.get(t));
            assertTrue("md ts phut " + i, c.mdTs.contains(t));
            for (String b : notAllowed(t)) assertFalse(b + " phut " + i, live.contains(b));
            assertEquals("MDT crypto truoc onboard", t < MDT_OB, live.contains("MDTUSDT"));
        }
        for (Map<String, KlineObjectSimple> x : c.extracted) for (String b : BANNED) assertFalse(x.containsKey(b));
    }

    /** breadth (calMarketData) va ALT_EW: co BAT tren map tho == co TAT tren map chi con universe A1. */
    @Test
    public void breadthAndAltEw_equalCryptoOnly() throws Exception {
        long t0 = MDT_OB - 30 * MIN;
        List<Map<String, KlineObjectSimple>> raw = new ArrayList<>();
        for (int i = 0; i < 60; i++) raw.add(minute(t0 + i * MIN, i));
        UniverseA1Filter.setConfigForTest(true, ok(), true);
        UniverseA1Filter.initEager();
        List<Map<String, KlineObjectSimple>> a1 = new ArrayList<>();
        for (int i = 0; i < 60; i++) a1.add(new LinkedHashMap<>(UniverseA1Filter.filter(raw.get(i), t0 + i * MIN)));
        double[] ewOn = new double[60];
        MarketDataObject[] mdOn = new MarketDataObject[60];
        AltEwIndex x = new AltEwIndex();
        for (int i = 0; i < 60; i++) {
            ewOn[i] = x.feed(t0 + i * MIN, raw.get(i));
            mdOn[i] = MarketBigChangeDetector.calMarketData(raw.get(i), mx(raw.get(i)), mn(raw.get(i)),
                    com.binance.client.constant.Constants.diedSymbol, t0 + i * MIN);
        }
        UniverseA1Filter.setConfigForTest(false, null, true);
        AltEwIndex y = new AltEwIndex();
        AltEwIndex z = new AltEwIndex();
        boolean differs = false;
        for (int i = 0; i < 60; i++) {
            long t = t0 + i * MIN;
            assertEquals("ALT_EW phut " + i, ewOn[i], y.feed(t, a1.get(i)), 1e-12);
            MarketDataObject off = MarketBigChangeDetector.calMarketData(a1.get(i), mx(a1.get(i)), mn(a1.get(i)),
                    com.binance.client.constant.Constants.diedSymbol, t);
            assertEquals(off.rateDownAvg, mdOn[i].rateDownAvg, 0f);
            assertEquals(off.rateUpAvg, mdOn[i].rateUpAvg, 0f);
            assertEquals(off.rateDown15MAvg, mdOn[i].rateDown15MAvg, 0f);
            double ew0 = z.feed(t, raw.get(i));   // co TAT tren map tho: TF lot vao
            if (i > 0 && Math.abs(ew0 - ewOn[i]) > 1e-9) differs = true;
        }
        assertTrue("co TAT phai khac (TF/INDEX lot vao ALT_EW)", differs);
    }

    /** S1/ung vien/funding-OI deu sinh tu symbol2LastTickers: diem loc A1 PHAI ngay sau tickerWindow.read; init SOM; seed loc. */
    @Test
    public void liveSource_singleFilterPointAfterTickerRead() throws Exception {
        String src = new String(Files.readAllBytes(Paths.get(
                "src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java")), StandardCharsets.UTF_8);
        int read = src.indexOf("symbol2LastTickers = tickerWindow.read(");
        int filt = src.indexOf("symbol2LastTickers = com.binance.chuyennd.tradecore.selector.UniverseA1Filter.filter(symbol2LastTickers");
        assertTrue(read > 0 && filt > read);
        assertEquals("khong dung symbol2LastTickers giua read va diem loc", -1,
                src.substring(src.indexOf('\n', read), filt).indexOf("symbol2LastTickers.get"));
        int st = src.indexOf("public void start()");
        assertTrue(src.indexOf("UniverseA1Filter.initEager()", st) < src.indexOf("initData();", st));
        int seed = src.indexOf("time2Tickers = com.binance.chuyennd.tradecore.selector.UniverseA1Filter.filterMinutes(time2Tickers)");
        assertTrue(seed > 0 && seed < src.indexOf("featPipeline.seed(time2Tickers)"));
    }

    private static Map<String, Float> mx(Map<String, KlineObjectSimple> m) {
        Map<String, Float> r = new HashMap<>();
        for (Map.Entry<String, KlineObjectSimple> e : m.entrySet()) r.put(e.getKey(), e.getValue().maxPrice);
        return r;
    }

    private static Map<String, Float> mn(Map<String, KlineObjectSimple> m) {
        Map<String, Float> r = new HashMap<>();
        for (Map.Entry<String, KlineObjectSimple> e : m.entrySet()) r.put(e.getKey(), e.getValue().minPrice);
        return r;
    }

    /** Sink + MdGen ghi lai moi snapshot duoc nuoi (theo thu tu) va ts md. */
    static final class Cap implements LiveFeaturePipeline.Sink, LiveFeaturePipeline.MdGen {
        final List<Map<String, KlineObjectSimple>> fed = new ArrayList<>();
        final Map<Long, Set<String>> byMinute = new TreeMap<>();
        final List<Map<String, KlineObjectSimple>> extracted = new ArrayList<>();
        final List<Long> mdTs = new ArrayList<>();

        public void feed(long minute, Map<String, KlineObjectSimple> snap) {
            fed.add(snap);
            byMinute.put(minute, new HashSet<>(snap.keySet()));
        }

        public MarketFeatures extract(long minute, Map<String, KlineObjectSimple> snap, MarketDataObject md) {
            byMinute.put(minute, new HashSet<>(snap.keySet()));
            extracted.add(snap);
            return null;
        }

        public MarketDataObject update(Map<String, KlineObjectSimple> snap) {
            mdTs.add(Long.MIN_VALUE);
            return null;
        }

        public MarketDataObject update(Map<String, KlineObjectSimple> snap, long tsMs) {
            mdTs.add(tsMs);
            return null;
        }
    }

    static final class Src implements LiveFeaturePipeline.MinuteSource {
        final TreeMap<Long, Map<String, KlineObjectSimple>> d;

        Src(TreeMap<Long, Map<String, KlineObjectSimple>> d) {
            this.d = d;
        }

        public Map<String, KlineObjectSimple> snapshot(long minute) {
            return d.get(minute);
        }

        public LiveFeaturePipeline.SettleInfo await(long minute, int expected) {
            return new LiveFeaturePipeline.SettleInfo(expected, expected, 0L, 0);
        }
    }
}
