package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.TreeMap;

/**
 * [BD-SIZE-ADAPT 2026-09-16] docs/prereg/PREREG_BD_SIZE_ADAPT.md — size leg BIG_DOWN theo severity
 * causal (rolling N-ngay), KHONG doi trigger BIG_DOWN.
 *
 * <p>Severity:
 * <pre>
 *   thr   = MS_DOWN_BIG_AVG = -0.03157
 *   x(t)  = rateDownAvg tai phut trigger
 *   qmin(D) = min(rateDownAvg) tren [D-N, D)   # N ngay lich TRUOC D, causal, KHONG gom D
 *   sev(t)  = clamp( (thr - x) / (thr - qmin(D) + eps), 0, 1 )
 * </pre>
 *
 * <p>Lich day-&gt;qmin duoc build MOT LAN tu chinh {@code time2MarketData} cua sim (khong CSV,
 * khong Python). Day key = {@code floorDiv(ms, 86400000)} (cung quy uoc RegimeSchedule.scaleForTime).
 * Khi mode = off => {@link #ACTIVE}=false, build() la no-op => khong cap phat => byte-identical.
 */
public final class BdSizeAdapt {
    private static final Logger LOG = LoggerFactory.getLogger(BdSizeAdapt.class);
    private static final long DAY_MS = 86400000L;
    private static final float EPS = 1e-6f;

    /** Che do da chuan hoa (off|down50|down25|up50). */
    public static final String MODE = Configs.BD_SIZE_ADAPT.trim().toLowerCase();
    /** true khi mode != off. */
    public static final boolean ACTIVE = !"off".equals(MODE);

    private static TreeMap<Long, Float> dayMin = new TreeMap<>();
    private static TreeMap<Long, Float> qminMap = new TreeMap<>();
    private static boolean built = false;
    private static long scaledLegs = 0L;

    private BdSizeAdapt() {
    }

    /**
     * Build lich day-&gt;qmin 1 lan tu market TreeMap. off => no-op (khong cap phat).
     */
    public static void build(TreeMap<Long, MarketDataObject> time2MarketData) {
        dayMin = new TreeMap<>();
        qminMap = new TreeMap<>();
        built = false;
        scaledLegs = 0L;
        if (!ACTIVE) return;
        if (time2MarketData == null || time2MarketData.isEmpty()) return;
        int n = Configs.BD_SIZE_ADAPT_N;
        if (n <= 0) n = 120;

        for (Map.Entry<Long, MarketDataObject> e : time2MarketData.entrySet()) {
            MarketDataObject md = e.getValue();
            if (md == null) continue;
            long day = Math.floorDiv(e.getKey(), DAY_MS);
            float v = md.rateDownAvg;
            Float cur = dayMin.get(day);
            if (cur == null || v < cur) dayMin.put(day, v);
        }
        for (Long day : dayMin.keySet()) {
            Map<Long, Float> sub = dayMin.subMap(day - (long) n, true, day, false);
            float best = Float.MAX_VALUE;
            for (float v : sub.values()) {
                if (v < best) best = v;
            }
            if (best != Float.MAX_VALUE) qminMap.put(day, best);
        }
        built = true;
        LOG.info("[BD-SIZE-ADAPT] mode={} N={} dayMinRows={} qminRows={} thr={}",
                MODE, n, dayMin.size(), qminMap.size(), Configs.MS_DOWN_BIG_AVG);
    }

    /**
     * He so nhan budget cho 1 leg BIG_DOWN. Tra 1f khi off/chua build/khong co baseline.
     *
     * @param levelChange luon la BIG_DOWN tai call-site (giu tham so de ro y doan, tuong lai).
     * @param dayKey      {@code floorDiv(ms, DAY_MS)} cua phut trigger.
     * @param rateDownAvg rateDownAvg cua phut trigger (= marketData.rateDownAvg).
     */
    public static float mult(MarketLevelChange levelChange, long dayKey, float rateDownAvg) {
        if (!ACTIVE || !built) return 1f;
        float qmin = qminFor(dayKey);
        if (qmin == Float.MAX_VALUE) return 1f;
        float thr = Configs.MS_DOWN_BIG_AVG;
        float denom = thr - qmin + EPS;
        float sev = (thr - rateDownAvg) / denom;
        if (sev < 0f) sev = 0f;
        else if (sev > 1f) sev = 1f;

        float m;
        if ("down50".equals(MODE)) m = clamp(1f - 0.50f * sev, 0.50f, 1.00f);
        else if ("down25".equals(MODE)) m = clamp(1f - 0.25f * sev, 0.75f, 1.00f);
        else if ("up50".equals(MODE)) m = clamp(1f + 0.50f * sev, 1.00f, 1.50f);
        else m = 1f;

        if (m != 1f) scaledLegs++;
        return m;
    }

    /** So leg da bi scale (m != 1f) — dung de bao 1 dong o cuoi sim. */
    public static long scaledLegs() {
        return scaledLegs;
    }

    private static float qminFor(long dayKey) {
        Float v = qminMap.get(dayKey);
        if (v != null) return v;
        Map.Entry<Long, Float> fe = qminMap.floorEntry(dayKey);
        return fe != null ? fe.getValue() : Float.MAX_VALUE;
    }

    private static float clamp(float v, float lo, float hi) {
        if (v < lo) return lo;
        if (v > hi) return hi;
        return v;
    }
}
