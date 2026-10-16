package com.binance.chuyennd.tradecore.selector;

import org.junit.Test;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertSame;

public class TtlPriceCacheTest {
    private final AtomicLong now = new AtomicLong(1_000_000L);
    private final AtomicInteger calls = new AtomicInteger();

    private TtlPriceCache cache(long ttl) {
        return new TtlPriceCache(ttl, syms -> {
            calls.incrementAndGet();
            Map<String, Float> m = new HashMap<>();
            for (String s : syms) m.put(s, (float) calls.get());
            return m;
        }, now::get);
    }

    private static Set<String> set(String... s) {
        return new HashSet<>(Arrays.asList(s));
    }

    @Test
    public void reuseWithinTtl() {
        TtlPriceCache c = cache(3000);
        Map<String, Float> a = c.get(set("BTC", "ETH"));
        now.addAndGet(2999);
        assertSame(a, c.get(set("BTC")));
        assertEquals(1, calls.get());
        assertEquals(1, c.hits());
    }

    @Test
    public void refetchAfterTtl() {
        TtlPriceCache c = cache(3000);
        c.get(set("BTC"));
        now.addAndGet(3000);
        c.get(set("BTC"));
        assertEquals(2, calls.get());
    }

    @Test
    public void refetchWhenNewSymbol() {
        TtlPriceCache c = cache(3000);
        c.get(set("BTC"));
        Map<String, Float> b = c.get(set("BTC", "SOL"));
        assertEquals(2, calls.get());
        assertEquals(2f, b.get("SOL"), 0f);
    }

    @Test
    public void ttlZeroAlwaysFetches() {
        TtlPriceCache c = cache(0);
        c.get(set("BTC"));
        c.get(set("BTC"));
        assertEquals(2, calls.get());
    }

    @Test
    public void clockBackwardsRefetches() {
        TtlPriceCache c = cache(3000);
        c.get(set("BTC"));
        now.addAndGet(-10);
        c.get(set("BTC"));
        assertEquals(2, calls.get());
    }
}
