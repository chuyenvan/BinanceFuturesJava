package com.binance.chuyennd.tradecore.selector;

import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.function.LongSupplier;

/**
 * [PXCACHE 2026-10-16] Cache gia realtime cho {@code liveBookFull} (skipFull): truoc day MOI ung vien PREDICT
 * goi {@code getAllPriceRealtimeLegacy} (scan TOAN BO set gia Aerospike) => K24 = 24 scan/tick, tick 7-14 s
 * (docs/result/SHADOW_PARITY_FEAT_1016.md §6). Nay dung lai ket qua trong {@code ttlMs} neu tap symbol yeu cau
 * nam trong tap da lay. Chi dung o duong LIVE; sim khong goi.
 */
public final class TtlPriceCache {
    private final long ttlMs;
    private final Function<Set<String>, Map<String, Float>> fetch;
    private final LongSupplier clock;
    private long atMs = Long.MIN_VALUE;
    private Set<String> keys = Collections.emptySet();
    private Map<String, Float> value;
    private long hits;
    private long misses;

    public TtlPriceCache(long ttlMs, Function<Set<String>, Map<String, Float>> fetch, LongSupplier clock) {
        this.ttlMs = ttlMs;
        this.fetch = fetch;
        this.clock = clock;
    }

    public synchronized Map<String, Float> get(Set<String> symbols) {
        long now = clock.getAsLong();
        if (ttlMs > 0 && value != null && now >= atMs && now - atMs < ttlMs && keys.containsAll(symbols)) {
            hits++;
            return value;
        }
        Set<String> req = new HashSet<>(symbols);
        Map<String, Float> v = fetch.apply(req);
        value = v;
        keys = req;
        atMs = now;
        misses++;
        return v;
    }

    public synchronized long hits() {
        return hits;
    }

    public synchronized long misses() {
        return misses;
    }
}
