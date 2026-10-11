package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.Test;

import java.util.TreeMap;

import static org.junit.Assert.*;

/** [LIVEFIX2] cache nen ngay giu id >= 1000 va dung shape CAPACITY (truoc: mac dinh 1000). */
public class CompactFileDayIdCapTest {

    private static KlineObjectSimple k(long t, float c) {
        KlineObjectSimple x = new KlineObjectSimple();
        x.startTime = t; x.priceOpen = c; x.maxPrice = c; x.minPrice = c; x.priceClose = c; x.totalUsdt = 1f;
        return x;
    }

    @Test
    public void ids999_1000_1500_roundTrip() {
        long t = 1_700_000_000_000L;
        KlineObjectSimple[] a = new KlineObjectSimple[SymbolIdLimits.CAPACITY];
        a[999] = k(t, 1f); a[1000] = k(t, 2f); a[1500] = k(t, 3f);
        TreeMap<Long, KlineObjectSimple[]> day = new TreeMap<>();
        day.put(t, a);
        KlineObjectSimple[] r = CompactFileDay.compress(day).reconstruct().get(t);
        assertEquals(SymbolIdLimits.CAPACITY, r.length);
        assertEquals(1f, r[999].priceClose, 0f);
        assertEquals(2f, r[1000].priceClose, 0f);
        assertEquals(3f, r[1500].priceClose, 0f);
        int nonNull = 0;
        for (KlineObjectSimple x : r) if (x != null) nonNull++;
        assertEquals(3, nonNull);
    }

    @Test
    public void legacy1000Array_valuesUnchanged_shapeWidened() {
        long t = 1_700_000_000_000L;
        KlineObjectSimple[] a = new KlineObjectSimple[SymbolIdLimits.LEGACY_CAPACITY];
        a[7] = k(t, 5f);
        TreeMap<Long, KlineObjectSimple[]> day = new TreeMap<>();
        day.put(t, a);
        KlineObjectSimple[] r = CompactFileDay.compress(day).reconstruct().get(t);
        assertEquals(SymbolIdLimits.CAPACITY, r.length);
        assertEquals(5f, r[7].priceClose, 0f);
    }
}
