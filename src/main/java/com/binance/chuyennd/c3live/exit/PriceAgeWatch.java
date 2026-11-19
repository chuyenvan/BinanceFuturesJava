package com.binance.chuyennd.c3live.exit;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collection;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeSet;
import java.util.function.Function;
import java.util.function.LongSupplier;

/**
 * [W3A muc 5 ? AUDIT_GOLIVE_1116_D D-03] Theo doi TUOI gia price_realtime ma nhip exit c3 dung (CHI log + bo dem).
 * KHONG chan ARM/MOVE/time-stop (audit de xuat bo qua ARM/MOVE khi gia cu = DOI quyet dinh exit => can prereg, MASTER quyet).
 * Gia cu &gt; nguong ({@code C3_PRICE_AGE_STALE_MS}, mac dinh 15 000) => WARN {@code [C3-LIVE] PRICE-AGE} toi da 1 dong/phut.
 */
public final class PriceAgeWatch {

    private static final Logger LOG = LoggerFactory.getLogger(PriceAgeWatch.class);
    /** Env tat (chi "false" moi tat). */
    public static final String KEY_FLAG = "C3_PRICE_AGE_WATCH";
    /** Env nguong gia cu (ms). */
    public static final String KEY_STALE_MS = "C3_PRICE_AGE_STALE_MS";
    public static final long DEFAULT_STALE_MS = 15_000L;
    static final long LOG_EVERY_MS = 60_000L;

    private final long staleMs;
    /** [W3B muc 3b] doc ts theo LO (1 lenh / nhip); loi => nem (dem thieu + ghi vao dong WARN 1/phut). */
    private final Function<Collection<String>, Map<String, Long>> batchReader;
    private String lastErr;
    private final LongSupplier clock;
    private long lastLogMs = Long.MIN_VALUE / 2;
    private long nTicks;
    private long nStaleTicks;
    private long nStaleObs;
    private long nMissingObs;
    private long maxAgeMs;

    /**
     * @param staleMs  nguong tuoi gia (ms)
     * @param tsReader doc ts (ms) cua price_realtime theo symbol (null = khong co)
     * @param clock    dong ho
     */
    public PriceAgeWatch(long staleMs, Function<String, Long> tsReader, LongSupplier clock) {
        this(staleMs, clock, syms -> {
            Map<String, Long> m = new HashMap<>();
            for (String s : syms) {
                try {
                    Long t = tsReader.apply(s);
                    if (t != null) m.put(s, t);
                } catch (RuntimeException e) {
                    // tinh la thieu ts
                }
            }
            return m;
        });
    }

    private PriceAgeWatch(long staleMs, LongSupplier clock, Function<Collection<String>, Map<String, Long>> batchReader) {
        this.staleMs = staleMs > 0 ? staleMs : DEFAULT_STALE_MS;
        this.batchReader = batchReader;
        this.clock = clock;
    }

    /**
     * [W3B muc 3b] Ban doc ts theo LO (Aerospike batch get 1 lan / nhip thay vi N get tuan tu).
     *
     * @param staleMs     nguong tuoi gia (ms)
     * @param batchReader doc ts nhieu symbol (thieu = vang mat); nem = ca nhip tinh thieu
     * @param clock       dong ho
     * @return watcher
     */
    public static PriceAgeWatch batch(long staleMs, Function<Collection<String>, Map<String, Long>> batchReader, LongSupplier clock) {
        return new PriceAgeWatch(staleMs, clock, batchReader);
    }

    /**
     * Thuan: co bat khong.
     *
     * @param flag env {@code C3_PRICE_AGE_WATCH}
     * @return false chi khi "false"
     */
    public static boolean enabled(String flag) {
        return !(flag != null && "false".equalsIgnoreCase(flag.trim()));
    }

    /**
     * Doc nguong tu env (ms); thieu/sai/&lt;= 0 => mac dinh.
     *
     * @param raw gia tri env
     * @return nguong ms
     */
    public static long staleFrom(String raw) {
        try {
            long v = raw == null || raw.trim().isEmpty() ? DEFAULT_STALE_MS : Long.parseLong(raw.trim());
            return v > 0 ? v : DEFAULT_STALE_MS;
        } catch (NumberFormatException e) {
            return DEFAULT_STALE_MS;
        }
    }

    /**
     * Quan sat 1 nhip exit (sau khi trailing.step da chay ? khong lam tre quyet dinh exit).
     *
     * @param syms symbol cum dang giu
     * @return so symbol co gia cu (&gt; nguong) trong nhip nay
     */
    public synchronized int observe(Collection<String> syms) {
        if (syms == null || syms.isEmpty()) return 0;
        long now = clock.getAsLong();
        nTicks++;
        int stale = 0;
        int missing = 0;
        long maxTick = 0L;
        TreeSet<String> staleSyms = new TreeSet<>();
        Map<String, Long> all;
        try {
            all = batchReader.apply(syms);
        } catch (RuntimeException e) {
            all = null;
            lastErr = e.getClass().getSimpleName() + ": " + e.getMessage();
        }
        for (String s : syms) {
            Long ts = all == null ? null : all.get(s);
            if (ts == null) {
                missing++;
                continue;
            }
            long age = now - ts;
            if (age > maxTick) maxTick = age;
            if (age > staleMs) {
                stale++;
                if (staleSyms.size() < 8) staleSyms.add(s + ":" + age);
            }
        }
        nStaleObs += stale;
        nMissingObs += missing;
        if (maxTick > maxAgeMs) maxAgeMs = maxTick;
        if (stale > 0) nStaleTicks++;
        if ((stale > 0 || missing > 0) && now - lastLogMs >= LOG_EVERY_MS) {
            lastLogMs = now;
            LOG.warn("[C3-LIVE] PRICE-AGE gia_cu={}/{} thieu_ts={} nguong_ms={} max_age_ms={} {} | tong: nhip={} nhip_cu={} obs_cu={}"
                            + " obs_thieu={} (CHI canh bao, KHONG doi exit ? D-03 can prereg)",
                    stale, syms.size(), missing, staleMs, maxTick, staleSyms, nTicks, nStaleTicks, nStaleObs, nMissingObs);
            if (lastErr != null) {   // [W3B muc 3b] loi doc gom vao nhip log 1/phut (khong ERROR moi nhip)
                LOG.warn("[C3-LIVE] PRICE-AGE loi doc ts gan nhat: {}", lastErr);
                lastErr = null;
            }
        }
        return stale;
    }

    /** @return so nhip co &gt;= 1 symbol gia cu */
    public synchronized long staleTicks() {
        return nStaleTicks;
    }

    /** @return tong so quan sat symbol gia cu */
    public synchronized long staleObs() {
        return nStaleObs;
    }

    /** @return tong so quan sat thieu ts */
    public synchronized long missingObs() {
        return nMissingObs;
    }

    /** @return tuoi lon nhat da thay (ms) */
    public synchronized long maxAgeMs() {
        return maxAgeMs;
    }
}
