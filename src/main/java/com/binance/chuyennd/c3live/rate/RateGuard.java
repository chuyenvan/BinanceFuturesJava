package com.binance.chuyennd.c3live.rate;

import com.binance.chuyennd.c3live.api.ErrorKind;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.GatewayException;
import com.binance.chuyennd.c3live.api.RateLimitSpec;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayDeque;
import java.util.Optional;

/**
 * [V12 C13] Ngan sach REST ky cho MOI call c3_live (dung chung 1 instance cho C3LiveClient):
 * weight/1 phut (IP, chung voi LEGACY ingest tren 242), lenh/10 s, lenh/1 phut (tai khoan con).
 * <ul>
 *   <li>Ngan sach = floor(gioi han san * fraction), fraction mac dinh 0.5 va bi kep &lt;= 0.5.</li>
 *   <li>Gioi han lay tu exchangeInfo.rateLimits ({@link Limits#fromExchangeInfo}); thieu -> mac dinh Binance 2400/300/1200
 *       (CHUA XAC MINH tai thoi diem code, se ghi de khi nap exchangeInfo).</li>
 *   <li>Cua so truot (bao thu hon cua so phut co dinh cua san). Header X-MBX-USED-WEIGHT-1M / X-MBX-ORDER-COUNT-10S/-1M:
 *       dung max(dem noi bo, so san bao trong cung cua so co dinh) -> khi LEGACY dung nhieu weight IP, c3_live tu nhuong.</li>
 *   <li>Het ngan sach -> cho toi da maxWaitMs, qua -> GatewayException(RATE_LIMIT, notExecuted=true).</li>
 *   <li>429 -> back-off (Retry-After hoac 2s*2^n, tran 120s); 418 (ban IP) -> Retry-After hoac 300s*2^n; chan moi call toi het han.</li>
 * </ul>
 */
public final class RateGuard {
    private static final Logger LOG = LoggerFactory.getLogger(RateGuard.class);

    public static final double MAX_FRACTION = 0.5;
    public static final long WEIGHT_WINDOW_MS = 60_000L;
    public static final long ORDER10_WINDOW_MS = 10_000L;
    public static final long ORDER60_WINDOW_MS = 60_000L;
    static final long BACKOFF_429_BASE_MS = 2_000L;
    static final long BACKOFF_429_MAX_MS = 120_000L;
    static final long BAN_418_DEFAULT_MS = 300_000L;
    static final long BAN_418_MAX_MS = 3L * 86_400_000L;

    /** Dong ho tiem duoc (test). */
    public interface Clock {
        long nowMs();

        void sleepMs(long ms) throws InterruptedException;
    }

    public static final Clock SYSTEM = new Clock() {
        @Override public long nowMs() { return System.currentTimeMillis(); }
        @Override public void sleepMs(long ms) throws InterruptedException { Thread.sleep(ms); }
    };

    /** Gioi han CUA SAN (100 %), chua nhan fraction. */
    public static final class Limits {
        public final int weight1m;
        public final int orders10s;
        public final int orders1m;
        public final boolean fromExchange;

        public Limits(int weight1m, int orders10s, int orders1m, boolean fromExchange) {
            this.weight1m = weight1m;
            this.orders10s = orders10s;
            this.orders1m = orders1m;
            this.fromExchange = fromExchange;
        }

        /** Gia tri cong bo cua Binance USDT-M (CHUA XAC MINH tai thoi diem code). */
        public static Limits binanceDefault() { return new Limits(2400, 300, 1200, false); }

        /** Doc REQUEST_WEIGHT/1m, ORDERS/10s, ORDERS/1m; muc thieu -> mac dinh + WARN. */
        public static Limits fromExchangeInfo(ExchangeInfo ei) {
            Limits d = binanceDefault();
            if (ei == null) return d;
            Optional<RateLimitSpec> w = ei.rateLimit("REQUEST_WEIGHT", 60_000L);
            Optional<RateLimitSpec> o10 = ei.rateLimit("ORDERS", 10_000L);
            Optional<RateLimitSpec> o60 = ei.rateLimit("ORDERS", 60_000L);
            if (!w.isPresent() || !o10.isPresent() || !o60.isPresent()) {
                LOG.warn("[C3-RATE] exchangeInfo.rateLimits thieu muc (w={} o10={} o60={}) -> dung mac dinh cho muc thieu",
                        w.isPresent(), o10.isPresent(), o60.isPresent());
            }
            return new Limits(w.map(RateLimitSpec::getLimit).orElse(d.weight1m),
                    o10.map(RateLimitSpec::getLimit).orElse(d.orders10s),
                    o60.map(RateLimitSpec::getLimit).orElse(d.orders1m),
                    w.isPresent() && o10.isPresent() && o60.isPresent());
        }

        @Override
        public String toString() { return "w1m=" + weight1m + " o10s=" + orders10s + " o1m=" + orders1m + (fromExchange ? " (exchangeInfo)" : " (default)"); }
    }

    private final double fraction;
    private final long maxWaitMs;
    private final Clock clock;

    private int budgetWeight1m;
    private int budgetOrders10s;
    private int budgetOrders1m;
    private Limits limits;

    private final ArrayDeque<long[]> weightEv = new ArrayDeque<>();
    private final ArrayDeque<long[]> order10Ev = new ArrayDeque<>();
    private final ArrayDeque<long[]> order60Ev = new ArrayDeque<>();
    private long weightSum, order10Sum, order60Sum;

    private int serverWeight = -1;
    private long serverWeightBucket = -1;
    private int serverOrder10 = -1;
    private long serverOrder10Bucket = -1;
    private int serverOrder60 = -1;
    private long serverOrder60Bucket = -1;

    private long blockedUntilMs;
    private int consecutive429;
    private int consecutive418;

    private long peakWeight1m, peakOrders10s, peakOrders1m, waitsTotalMs, rejects;

    public RateGuard(Limits limits, double fraction, long maxWaitMs, Clock clock) {
        double f = fraction <= 0 || Double.isNaN(fraction) ? MAX_FRACTION : Math.min(MAX_FRACTION, fraction);
        this.fraction = f;
        this.maxWaitMs = Math.max(0L, maxWaitMs);
        this.clock = clock == null ? SYSTEM : clock;
        updateLimits(limits == null ? Limits.binanceDefault() : limits);
    }

    /** Mac dinh: Binance default, 50 %, cho toi da 2 s, dong ho he thong. */
    public static RateGuard defaults() { return new RateGuard(Limits.binanceDefault(), MAX_FRACTION, 2_000L, SYSTEM); }

    public synchronized void updateLimits(Limits l) {
        this.limits = l;
        this.budgetWeight1m = Math.max(1, (int) Math.floor(l.weight1m * fraction));
        this.budgetOrders10s = Math.max(1, (int) Math.floor(l.orders10s * fraction));
        this.budgetOrders1m = Math.max(1, (int) Math.floor(l.orders1m * fraction));
        LOG.info("[C3-RATE] limits {} fraction={} -> budget w1m={} o10s={} o1m={}", l, fraction, budgetWeight1m,
                budgetOrders10s, budgetOrders1m);
    }

    public synchronized Limits getLimits() { return limits; }
    public synchronized int budgetWeight1m() { return budgetWeight1m; }
    public synchronized int budgetOrders10s() { return budgetOrders10s; }
    public synchronized int budgetOrders1m() { return budgetOrders1m; }
    public long getMaxWaitMs() { return maxWaitMs; }

    /** Xin quota voi maxWait mac dinh. */
    public void acquire(int weight, int orders) {
        acquire(weight, orders, maxWaitMs);
    }

    /**
     * Cho toi khi du ngan sach (toi da maxWait) roi GHI NHAN su dung. Khong du trong han -> RATE_LIMIT (request CHUA gui).
     */
    public void acquire(int weight, int orders, long maxWait) {
        if (weight < 0 || orders < 0) throw new IllegalArgumentException("weight/orders am");
        long start = clock.nowMs();
        long deadline = start + Math.max(0L, maxWait);
        while (true) {
            long wait;
            long now;
            synchronized (this) {
                now = clock.nowMs();
                if (weight > budgetWeight1m || orders > budgetOrders10s || orders > budgetOrders1m) {
                    rejects++;
                    throw new GatewayException(ErrorKind.RATE_LIMIT, 0, 0, "rate guard: 1 request vuot ngan sach (w=" + weight
                            + " o=" + orders + ")", true, 0L, null);
                }
                wait = waitNeeded(now, weight, orders);
                if (wait <= 0) {
                    record(now, weight, orders);
                    waitsTotalMs += Math.max(0L, now - start);
                    return;
                }
                if (now + wait > deadline) {
                    rejects++;
                    throw new GatewayException(ErrorKind.RATE_LIMIT, 0, 0, "rate guard: het ngan sach, can cho " + wait
                            + " ms > han " + maxWait + " ms", true, wait, null);
                }
            }
            try {
                clock.sleepMs(wait);
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                throw new GatewayException(ErrorKind.RATE_LIMIT, 0, 0, "rate guard: bi interrupt khi cho", true, 0L, ie);
            }
        }
    }

    private long waitNeeded(long now, int weight, int orders) {
        if (now < blockedUntilMs) return blockedUntilMs - now;
        prune(now);
        long w = 0;
        // weight / 1m
        int srvW = serverWeightBucket == now / WEIGHT_WINDOW_MS ? serverWeight : -1;
        if (weightSum + weight > budgetWeight1m) w = Math.max(w, expiryWait(weightEv, weightSum, weight, budgetWeight1m, WEIGHT_WINDOW_MS, now));
        if (srvW >= 0 && srvW + weight > budgetWeight1m) w = Math.max(w, WEIGHT_WINDOW_MS - (now % WEIGHT_WINDOW_MS) + 1);
        if (orders > 0) {
            int s10 = serverOrder10Bucket == now / ORDER10_WINDOW_MS ? serverOrder10 : -1;
            int s60 = serverOrder60Bucket == now / ORDER60_WINDOW_MS ? serverOrder60 : -1;
            if (order10Sum + orders > budgetOrders10s) w = Math.max(w, expiryWait(order10Ev, order10Sum, orders, budgetOrders10s, ORDER10_WINDOW_MS, now));
            if (order60Sum + orders > budgetOrders1m) w = Math.max(w, expiryWait(order60Ev, order60Sum, orders, budgetOrders1m, ORDER60_WINDOW_MS, now));
            if (s10 >= 0 && s10 + orders > budgetOrders10s) w = Math.max(w, ORDER10_WINDOW_MS - (now % ORDER10_WINDOW_MS) + 1);
            if (s60 >= 0 && s60 + orders > budgetOrders1m) w = Math.max(w, ORDER60_WINDOW_MS - (now % ORDER60_WINDOW_MS) + 1);
        }
        return w;
    }

    /** Thoi gian toi luc du su kien cu het han de sum + need <= budget. */
    private static long expiryWait(ArrayDeque<long[]> ev, long sum, long need, long budget, long window, long now) {
        long s = sum;
        for (long[] e : ev) {
            s -= e[1];
            if (s + need <= budget) return Math.max(1L, e[0] + window - now);
        }
        return window;
    }

    private void record(long now, int weight, int orders) {
        if (weight > 0) { weightEv.addLast(new long[]{now, weight}); weightSum += weight; }
        if (orders > 0) {
            order10Ev.addLast(new long[]{now, orders}); order10Sum += orders;
            order60Ev.addLast(new long[]{now, orders}); order60Sum += orders;
        }
        peakWeight1m = Math.max(peakWeight1m, weightSum);
        peakOrders10s = Math.max(peakOrders10s, order10Sum);
        peakOrders1m = Math.max(peakOrders1m, order60Sum);
    }

    private void prune(long now) {
        weightSum -= pruneQ(weightEv, now - WEIGHT_WINDOW_MS);
        order10Sum -= pruneQ(order10Ev, now - ORDER10_WINDOW_MS);
        order60Sum -= pruneQ(order60Ev, now - ORDER60_WINDOW_MS);
    }

    private static long pruneQ(ArrayDeque<long[]> q, long cutoffExclusive) {
        long removed = 0;
        while (!q.isEmpty() && q.peekFirst()[0] <= cutoffExclusive) removed += q.pollFirst()[1];
        return removed;
    }

    /** Header response (null = khong co). Goi cho MOI response co header, ke ca loi. */
    public synchronized void onHeaders(Integer usedWeight1m, Integer orderCount10s, Integer orderCount1m) {
        long now = clock.nowMs();
        if (usedWeight1m != null) { serverWeight = usedWeight1m; serverWeightBucket = now / WEIGHT_WINDOW_MS; }
        if (orderCount10s != null) { serverOrder10 = orderCount10s; serverOrder10Bucket = now / ORDER10_WINDOW_MS; }
        if (orderCount1m != null) { serverOrder60 = orderCount1m; serverOrder60Bucket = now / ORDER60_WINDOW_MS; }
        if (usedWeight1m != null && usedWeight1m > budgetWeight1m) {
            LOG.warn("[C3-RATE] san bao used weight 1m = {} > ngan sach {} (IP chung LEGACY?) -> c3_live cho het phut", usedWeight1m, budgetWeight1m);
        }
    }

    /** Response thanh cong (2xx): reset bo dem back-off. */
    public synchronized void onSuccess() {
        consecutive429 = 0;
        consecutive418 = 0;
    }

    /** HTTP 429 / 418. retryAfterMs <= 0 -> back-off mac dinh. Tra ve thoi diem het chan. */
    public synchronized long onRateLimited(int httpStatus, long retryAfterMs) {
        long now = clock.nowMs();
        long backoff;
        if (httpStatus == 418) {
            consecutive418++;
            backoff = retryAfterMs > 0 ? retryAfterMs : Math.min(BAN_418_MAX_MS, BAN_418_DEFAULT_MS << Math.min(10, consecutive418 - 1));
        } else {
            consecutive429++;
            long exp = Math.min(BACKOFF_429_MAX_MS, BACKOFF_429_BASE_MS << Math.min(10, consecutive429 - 1));
            backoff = retryAfterMs > 0 ? Math.max(retryAfterMs, exp) : exp;
        }
        blockedUntilMs = Math.max(blockedUntilMs, now + backoff);
        LOG.warn("[C3-RATE] HTTP {} -> chan moi call c3_live {} ms (toi {})", httpStatus, backoff, blockedUntilMs);
        return blockedUntilMs;
    }

    public synchronized long blockedUntilMs() { return blockedUntilMs; }

    public synchronized long usedWeight1m() { prune(clock.nowMs()); return weightSum; }
    public synchronized long usedOrders10s() { prune(clock.nowMs()); return order10Sum; }
    public synchronized long usedOrders1m() { prune(clock.nowMs()); return order60Sum; }
    public synchronized int lastServerWeight1m() { return serverWeight; }
    public synchronized long peakWeight1m() { return peakWeight1m; }
    public synchronized long peakOrders10s() { return peakOrders10s; }
    public synchronized long peakOrders1m() { return peakOrders1m; }
    public synchronized long rejects() { return rejects; }
}
