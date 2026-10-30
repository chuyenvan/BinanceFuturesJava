package com.binance.chuyennd.c3live.rate;

import com.binance.chuyennd.c3live.canary.CanaryLimits;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.function.Function;

/**
 * [V12 R4 R5] Chinh sach rate cua c3_live PRODUCTION tren tai khoan chinh (IP 242 chung LEGACY) = CHINH SACH CANARY 3i, dung
 * chung hang so {@link CanaryLimits} (khong nhan ban): call thuong nhan khi header IP + cost &lt;= 1800 (env
 * {@code LIVE_C3_IP_WEIGHT_CAP}, kep &lt;= 1920), weight c3 tu goi (cua so truot 60 s) &lt;= 600, call doc thuong tranh giay
 * [27, 40], doc bi tu choi cho &lt;= 2 x 61 s. Lan khan cap / {@link RateGuard.Urgent} giu nguyen; 429/418 van ton trong.
 */
public final class ProductionRatePolicy {

    private static final Logger LOG = LoggerFactory.getLogger(ProductionRatePolicy.class);
    public static final String KEY_IP_CAP = "LIVE_C3_IP_WEIGHT_CAP";
    /** cho toi da 1 call (lenh ghi) truoc khi guard tu choi — nhu canary. */
    public static final long WRITE_MAX_WAIT_MS = 2_000L;
    /** moi lan cho cua call doc / thu lai lenh ghi (het phut + 1 s). */
    public static final long READ_WAIT_MAX_MS = 61_000L;

    private ProductionRatePolicy() {
    }

    public static RateGuard.CanaryPolicy policy(String ipCapRaw) {
        int ipCap = CanaryLimits.ipWeightCap(ipCapRaw);
        if (ipCapRaw != null && !ipCapRaw.trim().isEmpty() && !String.valueOf(ipCap).equals(ipCapRaw.trim())) {
            LOG.warn("[C3-RATE] {}='{}' khong hop le / vuot tran {} => dung {}", KEY_IP_CAP, ipCapRaw.trim(),
                    CanaryLimits.IP_WEIGHT_ADMIT_MAX, ipCap);
        }
        return new RateGuard.CanaryPolicy(ipCap, CanaryLimits.OWN_WEIGHT_1M_CAP, CanaryLimits.BURST_FROM_SEC,
                CanaryLimits.BURST_TO_SEC, CanaryLimits.BURST_RESUME_SEC, CanaryLimits.READ_GUARD_MAX_WAITS, READ_WAIT_MAX_MS);
    }

    public static RateGuard.CanaryPolicy policy(Function<String, String> env) {
        return policy(env == null ? null : env.apply(KEY_IP_CAP));
    }

    /** RateGuard production (gioi han san mac dinh, ghi de khi nap exchangeInfo). */
    public static RateGuard guard(Function<String, String> env, RateGuard.Clock clock) {
        RateGuard.CanaryPolicy p = policy(env);
        LOG.info("[C3-RATE] production c3_live (tai khoan chinh): chinh sach 3i {}", p);
        return new RateGuard(RateGuard.Limits.binanceDefault(), RateGuard.MAX_FRACTION, WRITE_MAX_WAIT_MS,
                clock == null ? RateGuard.SYSTEM : clock, p);
    }
}
