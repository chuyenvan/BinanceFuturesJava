package com.binance.chuyennd.c3live.alert;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * [W3A muc 3 A-06] Chong spam canh bao: toi da 1 lan / khoa (symbol) / cua so; dem so lan bi nen de bao kem lan sau.
 */
public final class C3AlertThrottle {

    private final long windowMs;
    private final Map<String, long[]> state = new ConcurrentHashMap<>();   // [lastSentMs, suppressed]

    /**
     * @param windowMs cua so toi thieu giua 2 canh bao cung khoa (ms, &gt;= 0)
     */
    public C3AlertThrottle(long windowMs) {
        this.windowMs = Math.max(0L, windowMs);
    }

    /**
     * Thu xin gui canh bao cho khoa.
     *
     * @param key   khoa (symbol)
     * @param nowMs thoi diem
     * @return -1 neu bi nen; nguoc lai = so lan da bi nen tu lan gui truoc (&gt;= 0)
     */
    public synchronized long tryAcquire(String key, long nowMs) {
        long[] s = state.get(key);
        if (s == null) {
            state.put(key, new long[]{nowMs, 0L});
            return 0L;
        }
        if (nowMs - s[0] < windowMs) {
            s[1]++;
            return -1L;
        }
        long sup = s[1];
        s[0] = nowMs;
        s[1] = 0L;
        return sup;
    }

    /** @return cua so (ms) */
    public long windowMs() {
        return windowMs;
    }

    /**
     * Doc cua so tu env (phut); sai/thieu => mac dinh.
     *
     * @param raw    gia tri env (phut)
     * @param defMin mac dinh (phut)
     * @return cua so ms
     */
    public static long windowFromMinutes(String raw, long defMin) {
        try {
            long m = raw == null || raw.trim().isEmpty() ? defMin : Long.parseLong(raw.trim());
            return (m < 1 ? defMin : m) * 60_000L;
        } catch (NumberFormatException e) {
            return defMin * 60_000L;
        }
    }

    /**
     * Thuan: co bat canh bao (chi "false" moi tat).
     *
     * @param flag gia tri env
     * @return true neu bat
     */
    public static boolean enabled(String flag) {
        return !(flag != null && "false".equalsIgnoreCase(flag.trim()));
    }
}
