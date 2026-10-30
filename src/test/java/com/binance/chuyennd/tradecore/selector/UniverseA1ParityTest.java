package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import org.junit.After;
import org.junit.Test;

import java.net.URISyntaxException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import static org.junit.Assert.*;

/**
 * Parity cua universe A1 tren cac "feature thi truong" dung chung live/replay:
 * - tap S1 / breadth (calMarketData) / candidates / funding-OI deu sinh tu MOT map da loc;
 * - ALT_EW (X14) loai TF/INDEX theo point-in-time;
 * - co TAT: gia tri y nguyen (khong doi hanh vi).
 */
public class UniverseA1ParityTest {

    private static final long T = 1793000000000L;   // 2026-10-26, sau moi onboardDate trong fixture
    private static final String IDX = "DEFIUSDT";

    private static Path fixture() throws URISyntaxException {
        return Paths.get(UniverseA1ParityTest.class.getResource("/universe_a1_exchange_info.json").toURI());
    }

    @After
    public void tearDown() {
        UniverseA1Filter.resetForTest();
    }

    // ------------------------------------------------------------------ tap live sinh tu 1 map

    @Test
    public void liveDerivedSets_khongCoTradFiIndex() throws Exception {
        UniverseA1Filter.installForTest(fixture(), IDX, true);
        Map<String, KlineObjectSimple> raw = new LinkedHashMap<>();
        raw.put("BTCUSDT", bar(100, 101));
        raw.put("C1USDT", bar(100, 100));
        raw.put("C2USDT", bar(100, 100));
        raw.put("C3USDT", bar(100, 100));
        raw.put("AAPLUSDT", bar(100, 90));
        raw.put("ALLUSDT", bar(100, 90));

        // DIEM LOC DUY NHAT (giong DetectEntrySignal2TradeNormal sau tickerWindow.read)
        Map<String, KlineObjectSimple> symbol2FinalTicker = UniverseA1Filter.filter(raw, T);

        // calRateChangeAvg: 2 cay rate am/duong nhu live (:273-276)
        TreeMap<Float, String> rateDown2 = new TreeMap<>();
        TreeMap<Float, String> rateUp2 = new TreeMap<>();
        for (Map.Entry<String, KlineObjectSimple> e : symbol2FinalTicker.entrySet()) {
            float r = (e.getValue().priceClose - e.getValue().priceOpen) / e.getValue().priceOpen;
            rateDown2.put(r, e.getKey());
            rateUp2.put(-r, e.getKey());
        }
        // breadth/market features
        Map<String, Float> max = new HashMap<>();
        Map<String, Float> min = new HashMap<>();
        for (String s : raw.keySet()) {
            max.put(s, raw.get(s).maxPrice);
            min.put(s, raw.get(s).minPrice);
        }
        MarketDataObject md = MarketBigChangeDetector.calMarketData(raw, max, min,
                com.binance.client.constant.Constants.diedSymbol, T);
        // candidates (cascade/predict) + funding/OI snapshot + S1 pool deu lay tu symbol2FinalTicker
        Set<String> candidates = symbol2FinalTicker.keySet();
        Map<String, KlineObjectSimple> fundingSnap = symbol2FinalTicker;
        Set<String> s1Pool = symbol2FinalTicker.keySet();

        for (String banned : new String[]{"AAPLUSDT", "ALLUSDT"}) {
            assertFalse("S1", s1Pool.contains(banned));
            assertFalse("candidates/funding-OI", candidates.contains(banned));
            assertFalse("funding snapshot", fundingSnap.containsKey(banned));
            assertFalse("rateDown", rateDown2.containsValue(banned));
            assertFalse("rateUp", rateUp2.containsValue(banned));
        }
        // breadth: TF/INDEX roi -10% KHONG duoc keo rateDownAvg (chi con 0% cua crypto flat)
        assertEquals(0.0f, md.rateDownAvg, 1e-6f);
        // co TAT: map giu nguyen (ke ca TF) -> hanh vi cu
        UniverseA1Filter.installForTest(fixture(), IDX, false);
        MarketDataObject md0 = MarketBigChangeDetector.calMarketData(raw, max, min,
                com.binance.client.constant.Constants.diedSymbol, T);
        assertEquals(-0.05f, md0.rateDownAvg, 1e-6f);
    }

    // ------------------------------------------------------------------ ALT_EW

    @Test
    public void altEw_loaiTfIndexPointInTime() throws Exception {
        long t0 = T;
        long t1 = T + 60_000L;

        UniverseA1Filter.installForTest(fixture(), IDX, true);
        AltEwIndex a1 = new AltEwIndex();
        Map<String, KlineObjectSimple> m0 = new LinkedHashMap<>();
        m0.put("AAAUSDT", bar(100, 100));
        m0.put("AAPLUSDT", bar(100, 100));
        m0.put("ALLUSDT", bar(100, 100));
        a1.feed(t0, m0);
        Map<String, KlineObjectSimple> m1 = new LinkedHashMap<>();
        m1.put("AAAUSDT", bar(101, 101));
        m1.put("AAPLUSDT", bar(120, 120));
        m1.put("ALLUSDT", bar(130, 130));
        double ewA1 = a1.feed(t1, m1);
        assertEquals(Math.log(101.0 / 100.0), ewA1, 1e-12);   // chi AAAUSDT

        UniverseA1Filter.installForTest(fixture(), IDX, false);
        AltEwIndex a0 = new AltEwIndex();
        a0.feed(t0, m0);
        double ewA0 = a0.feed(t1, m1);
        double exp = (Math.log(1.01) + Math.log(1.2) + Math.log(1.3)) / 3.0;
        assertEquals(exp, ewA0, 1e-12);                       // co TAT: ca 3
    }

    @Test
    public void altEw_mdtCryptoTruocOnboardVanTinh() throws Exception {
        UniverseA1Filter.installForTest(fixture(), IDX, true);
        long mdtBefore = 1792574400000L - 2 * 60_000L;   // truoc onboard 2 phut
        AltEwIndex a = new AltEwIndex();
        a.feed(mdtBefore, Map.of("MDTUSDT", bar(100, 100)));
        double ew = a.feed(mdtBefore + 60_000L, Map.of("MDTUSDT", bar(102, 102)));
        assertEquals(Math.log(1.02), ew, 1e-12);         // truoc onboard: MDT la crypto, van tinh
    }

    private static KlineObjectSimple bar(float open, float close) {
        KlineObjectSimple k = new KlineObjectSimple();
        k.priceOpen = open;
        k.priceClose = close;
        k.maxPrice = Math.max(open, close);
        k.minPrice = Math.min(open, close);
        k.totalUsdt = 1f;
        k.startTime = T;
        return k;
    }
}
