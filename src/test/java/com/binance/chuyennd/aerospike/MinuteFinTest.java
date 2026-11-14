package com.binance.chuyennd.aerospike;

import org.junit.Test;
import org.xerial.snappy.Snappy;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.TreeSet;

import static org.junit.Assert.*;

/** [FIN 2026-11-14] Ma hoa bin fin + luat gop (thuan). File nay giong het o 2 nhanh qf/fin-bin va v1.2/fin-guard. */
public class MinuteFinTest {

    static Set<String> set(String... s) {
        return new TreeSet<>(Arrays.asList(s));
    }

    @Test
    public void roundTripSortedAndEmpty() throws IOException {
        assertEquals(set("BTC", "ETH", "1000PEPE"), MinuteFin.decode(MinuteFin.encode(Arrays.asList("ETH", "BTC", "1000PEPE", "BTC"))));
        Set<String> empty = MinuteFin.decode(MinuteFin.encode(Collections.<String>emptyList()));
        assertNotNull("tap rong != vang bin", empty);
        assertTrue(empty.isEmpty());
        assertNull("bin vang => null", MinuteFin.decode(null));
    }

    @Test(expected = IOException.class)
    public void wrongVersionRejected() throws IOException {
        MinuteFin.decode(Snappy.compress("v9:BTC".getBytes("UTF-8")));
    }

    @Test
    public void fullSymMatchesReaderConvention() {
        assertEquals("BTCUSDT", MinuteFin.fullSym("BTC"));
        assertEquals("BTCUSDT", MinuteFin.fullSym("BTCUSDT"));
    }

    @Test
    public void mergeRules() {
        Set<String> data = set("A", "B", "C", "D");
        // WS final A,B lan dau (record chi co ban nan)
        assertEquals(set("A", "B"), MinuteFin.merge(null, set("A", "B"), set("A", "B"), data));
        // REST som C (chua settle) => khong vao fin; fin cu giu
        assertEquals(set("A", "B"), MinuteFin.merge(set("A", "B"), set("C"), Collections.<String>emptySet(), data));
        // ghi de A bang ban chua chot => go A
        assertEquals(set("B"), MinuteFin.merge(set("A", "B"), set("A"), Collections.<String>emptySet(), data));
        // settle "same" (khong doi data) => danh dau D
        assertEquals(set("A", "B", "D"), MinuteFin.merge(set("A", "B"), null, set("D"), data));
        // finalSyms khong co trong data => khong vao fin
        assertEquals(set("A"), MinuteFin.merge(set("A"), null, set("Z"), data));
        // dong dau rong
        assertEquals(new HashSet<String>(), MinuteFin.merge(null, null, null, data));
    }
}
