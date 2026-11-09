package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import org.junit.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.TreeMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * [V12 R4u BIG_DOWN-SEL] cung input => top-n leg market-signal cua live ({@link BigDownSelect}) == sim
 * ({@code MarketBigChangeDetector.getTopSymbolArray} tren TreeMap symbolPred -> symId nhu
 * {@code extractPredict2Symbol}).
 */
public class BigDownSelectTest {

    /** Dung input sim tu cung map symbol->symbolPred; id = vi tri trong danh sach symbol sap xep. */
    private static Set<String> sim(Map<String, Float> mapPred, int n, Set<String> locked, Set<String> noTicker) {
        List<String> syms = new ArrayList<>(mapPred.keySet());
        Collections.sort(syms);
        KlineObjectSimple[] tk = new KlineObjectSimple[syms.size() + 1];
        TreeMap<Float, Short> p2s = new TreeMap<>();
        Set<Short> lk = new HashSet<>();
        for (int i = 0; i < syms.size(); i++) {
            String s = syms.get(i);
            short id = (short) (i + 1);
            Float v = mapPred.get(s);
            if (v != null && !v.isNaN()) p2s.put(v, id);          // extractPredict2Symbol: put(pred, id)
            if (!noTicker.contains(s)) tk[id] = new KlineObjectSimple();
            if (locked.contains(s)) lk.add(id);
        }
        Set<String> out = new HashSet<>();
        for (Short id : MarketBigChangeDetector.getTopSymbolArray(n, tk, lk, p2s)) out.add(syms.get(id - 1));
        return out;
    }

    private static Set<String> live(Map<String, Float> mapPred, int n, Set<String> locked, Set<String> noTicker) {
        return new HashSet<>(BigDownSelect.select(mapPred, n, locked::contains, s -> !noTicker.contains(s)));
    }

    private static Map<String, Float> m(Object... kv) {
        Map<String, Float> o = new HashMap<>();
        for (int i = 0; i < kv.length; i += 2) o.put((String) kv[i], (Float) kv[i + 1]);
        return o;
    }

    private static Set<String> set(String... s) {
        return new HashSet<>(Arrays.asList(s));
    }

    @Test
    public void top2SkipsHeldAndNoTickerLikeSim() {
        Map<String, Float> mp = m("AAA", 0.31f, "BBB", 0.12f, "CCC", 0.20f, "DDD", 0.05f, "EEE", 0.44f, "FFF", 0.08f);
        Set<String> locked = set("DDD");
        Set<String> noTk = set("FFF");
        assertEquals(sim(mp, 2, locked, noTk), live(mp, 2, locked, noTk));
        assertEquals(Arrays.asList("BBB", "CCC"), BigDownSelect.select(mp, 2, locked::contains, s -> !noTk.contains(s)));
    }

    @Test
    public void noMaxThresFilterLikeSim() {
        // ca hai coin > maxThres 0.3212 van duoc chon (sim khong loc)
        Map<String, Float> mp = m("AAA", 0.90f, "BBB", 0.80f);
        assertEquals(set("AAA", "BBB"), live(mp, 2, set(), set()));
        assertEquals(sim(mp, 2, set(), set()), live(mp, 2, set(), set()));
    }

    @Test
    public void missingS1GivesNothing() {
        assertTrue(BigDownSelect.select(null, 2, s -> false, s -> true).isEmpty());
        assertTrue(BigDownSelect.select(new HashMap<>(), 2, s -> false, s -> true).isEmpty());
        assertEquals(sim(new HashMap<>(), 2, set(), set()), live(new HashMap<>(), 2, set(), set()));
    }

    @Test
    public void nanAndNullDropped() {
        Map<String, Float> mp = m("AAA", Float.NaN, "BBB", 0.30f, "CCC", null, "DDD", 0.10f);
        assertEquals(Arrays.asList("DDD", "BBB"), BigDownSelect.select(mp, 2, s -> false, s -> true));
        assertEquals(sim(mp, 2, set(), set()), live(mp, 2, set(), set()));
    }

    @Test
    public void fewerThanNCandidates() {
        Map<String, Float> mp = m("AAA", 0.10f, "BBB", 0.20f, "CCC", 0.30f);
        Set<String> locked = set("AAA", "CCC");
        assertEquals(set("BBB"), live(mp, 2, locked, set()));
        assertEquals(sim(mp, 2, locked, set()), live(mp, 2, locked, set()));
        assertEquals(sim(mp, 2, set("AAA", "BBB", "CCC"), set()), live(mp, 2, set("AAA", "BBB", "CCC"), set()));
    }

    @Test
    public void smallLevelsN1AndN0QuirkLikeSim() {
        Map<String, Float> mp = m("AAA", 0.10f, "BBB", 0.20f, "CCC", 0.30f);
        assertEquals(sim(mp, 1, set(), set()), live(mp, 1, set(), set()));
        // n = 0: sim van lay 1 coin (kiem size>=n SAU khi them) — chep nguyen
        assertEquals(set("AAA"), live(mp, 0, set(), set()));
        assertEquals(sim(mp, 0, set(), set()), live(mp, 0, set(), set()));
        // n = 0 va coin dau khong co ticker: sim tra rong
        assertEquals(sim(mp, 0, set(), set("AAA")), live(mp, 0, set(), set("AAA")));
    }

    @Test
    public void tiesDeterministicDocumentedDeviation() {
        // sim TreeMap<Float,Short> giu 1 coin cho moi gia tri trung; live giu ca hai theo symbol tang
        Map<String, Float> mp = m("ZZZ", 0.10f, "AAA", 0.10f, "MMM", 0.20f);
        assertEquals(Arrays.asList("AAA", "ZZZ"), BigDownSelect.select(mp, 2, s -> false, s -> true));
        Set<String> s = sim(mp, 2, set(), set());
        assertEquals(2, s.size());
        assertTrue(s.contains("MMM"));     // sim mat 1 coin trung => lay xuong MMM
    }

    @Test
    public void randomNoTiesEqualsSim() {
        Random r = new Random(20261109L);
        for (int t = 0; t < 2000; t++) {
            int k = 1 + r.nextInt(40);
            Map<String, Float> mp = new HashMap<>();
            Set<Float> used = new HashSet<>();
            Set<String> locked = new HashSet<>();
            Set<String> noTk = new HashSet<>();
            for (int i = 0; i < k; i++) {
                String s = "S" + i + "USDT";
                float v;
                do {
                    v = r.nextFloat();
                } while (!used.add(v));
                mp.put(s, r.nextInt(25) == 0 ? Float.NaN : v);
                if (r.nextInt(4) == 0) locked.add(s);
                if (r.nextInt(10) == 0) noTk.add(s);
            }
            int n = r.nextInt(4);
            assertEquals("trial " + t, sim(mp, n, locked, noTk), live(mp, n, locked, noTk));
        }
    }

    @Test
    public void describeFormat() {
        Map<String, Float> mp = m("AAA", 0.1f, "BBB", 0.25f);
        assertEquals("AAA=0.100000,BBB=0.250000", BigDownSelect.describe(Arrays.asList("AAA", "BBB"), mp));
        assertEquals("-", BigDownSelect.describe(new ArrayList<>(), mp));
    }
}
