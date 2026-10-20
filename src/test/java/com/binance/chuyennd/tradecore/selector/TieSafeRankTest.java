package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/** [V11] TieSafeRank: khong mat coin trung score, thu tu (score, symbol), khoa tang ngat. */
public class TieSafeRankTest {

    private static Map<String, Float> m(Object... kv) {
        Map<String, Float> o = new HashMap<>();
        for (int i = 0; i < kv.length; i += 2) o.put((String) kv[i], (Float) kv[i + 1]);
        return o;
    }

    @Test
    public void tiesKeptOrderedBySymbol() {
        Map<String, Float> s = m("ZEC", -0.5f, "ADA", -0.5f, "BTC", -0.7f, "ETH", -0.5f, "XRP", 0.1f);
        TreeMap<Float, String> p = TieSafeRank.build(s);
        assertEquals(5, p.size());
        assertEquals(Arrays.asList("BTC", "ADA", "ETH", "ZEC", "XRP"), new ArrayList<>(p.values()));
        assertEquals(2, TieSafeRank.lostInLegacy(s));
        // legacy TreeMap mat 2 coin
        TreeMap<Float, String> legacy = new TreeMap<>();
        for (Map.Entry<String, Float> e : s.entrySet()) legacy.put(e.getValue(), e.getKey());
        assertEquals(3, legacy.size());
    }

    @Test
    public void keysStrictlyIncreasingAndCloseToScore() {
        Map<String, Float> s = m("A", 1f, "B", 1f, "C", Math.nextUp(1f), "D", 2f);
        TreeMap<Float, String> p = TieSafeRank.build(s);
        assertEquals(Arrays.asList("A", "B", "C", "D"), new ArrayList<>(p.values()));
        List<Float> k = new ArrayList<>(p.keySet());
        for (int i = 1; i < k.size(); i++) assertTrue(k.get(i) > k.get(i - 1));
        assertEquals(1f, k.get(0), 0f);
        assertTrue(Math.abs(k.get(2) - 1f) < 1e-6f);   // day day chuyen nextUp chi vai ulp
        assertEquals(2f, k.get(3), 0f);
    }

    @Test
    public void nanAndNullSkipped() {
        Map<String, Float> s = m("A", Float.NaN, "B", null, "C", 0.3f);
        TreeMap<Float, String> p = TieSafeRank.build(s);
        assertEquals(1, p.size());
        assertEquals("C", p.firstEntry().getValue());
        assertEquals(0, TieSafeRank.lostInLegacy(s));
    }

    @Test
    public void deterministicRegardlessOfInsertionOrder() {
        Map<String, Float> a = new java.util.LinkedHashMap<>();
        Map<String, Float> b = new java.util.LinkedHashMap<>();
        String[] syms = {"S1", "S2", "S3", "S4", "S5", "S6"};
        float[] v = {0.2f, 0.1f, 0.2f, 0.1f, 0.2f, 0.3f};
        for (int i = 0; i < syms.length; i++) a.put(syms[i], v[i]);
        for (int i = syms.length - 1; i >= 0; i--) b.put(syms[i], v[i]);
        assertEquals(new ArrayList<>(TieSafeRank.build(a).values()), new ArrayList<>(TieSafeRank.build(b).values()));
        assertEquals(Arrays.asList("S2", "S4", "S1", "S3", "S5", "S6"), new ArrayList<>(TieSafeRank.build(a).values()));
    }
}
