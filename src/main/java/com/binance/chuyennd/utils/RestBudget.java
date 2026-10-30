package com.binance.chuyennd.utils;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayDeque;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.LongSupplier;

/**
 * [INGEST-QF 2026-10-30] Ngân sách REST CỨNG cho mọi call tới {@code https://fapi.binance.com/} của MỘT JVM
 * (bật bởi {@code BinanceDataIngestor.main}; JVM khác không gọi {@link #enable} ⇒ không đổi hành vi).
 * Prereg: docs/prereg/PREREG_INGEST_QUICKFIX.md.
 * <ul>
 *   <li>Cửa sổ trượt 60 s theo weight TỰ ĐẾM (bảng {@link #weightOf}); tổng ≤ {@code cap} (mặc định & trần 300).</li>
 *   <li>Lane HIGH (klines, ticker/price — nến/giá LEGACY đọc) dùng tới {@code cap}; lane LOW (OI/LS/taker, premiumIndex,
 *       24hr, exchangeInfo, repair...) chỉ tới {@code cap - LOW_RESERVE} ⇒ HIGH luôn còn ≥ {@code LOW_RESERVE}.</li>
 *   <li>Header {@code X-MBX-USED-WEIGHT-1M} (cả IP, gồm LEGACY): ≥ {@code hdrSoft} trong phút hiện tại ⇒ LOW chờ sang
 *       phút sau; ≥ {@code hdrHard} ⇒ mọi lane chờ sang phút sau.</li>
 *   <li>HTTP 429/418 ⇒ cooldown GLOBAL ngay ({@link BinanceRestGuard#cooldownUntil}) theo {@code Retry-After}.</li>
 * </ul>
 * Hết hạn chờ ⇒ {@link #beforeRequest} trả {@code false}: caller coi như call lỗi (KHÔNG gọi sàn), đếm {@code denied}.
 */
public final class RestBudget {
    private static final Logger LOG = LoggerFactory.getLogger(RestBudget.class);
    public static final String FAPI = "https://fapi.binance.com/";
    public static final int MAX_CAP = 300;
    public static final int LOW_RESERVE = 100;
    static final long WINDOW_MS = 60_000L;

    public enum Lane { HIGH, LOW }

    private static volatile RestBudget INSTANCE = null;

    /** Bật ngân sách cho JVM này (gọi 1 lần ở main của ingestor). */
    public static synchronized RestBudget enable(int cap, int hdrSoft, int hdrHard) {
        INSTANCE = new RestBudget(cap, hdrSoft, hdrHard, System::currentTimeMillis);
        LOG.info("[REST-BUDGET] bat: cap={} weight/60s (LOW toi {}), hdrSoft={} hdrHard={}", INSTANCE.cap,
                INSTANCE.cap - LOW_RESERVE, hdrSoft, hdrHard);
        return INSTANCE;
    }

    public static RestBudget get() {
        return INSTANCE;
    }

    /** Chỉ cho test. */
    static void reset(RestBudget b) {
        INSTANCE = b;
    }

    public static boolean isFapi(String url) {
        return url != null && url.startsWith(FAPI);
    }

    /** Hook trước MỖI lần mở kết nối trong HttpRequest. Không bật / không phải fapi ⇒ true ngay. */
    public static boolean beforeRequest(String url) {
        RestBudget b = INSTANCE;
        if (b == null || !isFapi(url)) return true;
        Lane lane = laneOf(url);
        return b.acquire(weightOf(url), lane, lane == Lane.HIGH ? 5_000L : 30_000L);
    }

    /** Hook sau khi có status code. */
    public static void afterResponse(String url, int code, String usedWeightHdr, String retryAfterHdr) {
        RestBudget b = INSTANCE;
        if (b == null || !isFapi(url)) return;
        b.observe(code, usedWeightHdr, retryAfterHdr);
    }

    // ------------------------------------------------------------------ bảng weight (Binance UM, 2026)
    static String path(String url) {
        String p = url.substring(FAPI.length() - 1);
        int q = p.indexOf('?');
        return q < 0 ? p : p.substring(0, q);
    }

    static String param(String url, String key) {
        int q = url.indexOf('?');
        if (q < 0) return null;
        for (String kv : url.substring(q + 1).split("&")) {
            int e = kv.indexOf('=');
            if (e > 0 && kv.substring(0, e).equals(key)) return kv.substring(e + 1);
        }
        return null;
    }

    /** Weight theo tài liệu Binance UM; endpoint lạ ⇒ 5 (bảo thủ). */
    public static int weightOf(String url) {
        String p = path(url);
        boolean sym = param(url, "symbol") != null;
        switch (p) {
            case "/fapi/v1/klines":
            case "/fapi/v1/continuousKlines":
            case "/fapi/v1/markPriceKlines":
            case "/fapi/v1/indexPriceKlines": {
                int lim = 500;
                try {
                    String l = param(url, "limit");
                    if (l != null) lim = Integer.parseInt(l);
                } catch (NumberFormatException e) {
                    lim = 1500;   // khong doc duoc limit => tinh muc cao nhat (bao thu)
                }
                return lim < 100 ? 1 : lim < 500 ? 2 : lim <= 1000 ? 5 : 10;
            }
            case "/fapi/v1/ticker/price":
            case "/fapi/v2/ticker/price":
            case "/fapi/v1/ticker/bookTicker":
                return sym ? 1 : 2;
            case "/fapi/v1/ticker/24hr":
                return sym ? 1 : 40;
            case "/fapi/v1/premiumIndex":
                return sym ? 1 : 10;
            case "/fapi/v1/exchangeInfo":
            case "/fapi/v1/time":
            case "/fapi/v1/ping":
            case "/fapi/v1/fundingRate":
            case "/fapi/v1/openInterest":
                return 1;
            default:
                if (p.startsWith("/futures/data/")) return 1;   // han muc rieng 1000 req/5'; dem 1 cho bao thu
                return 5;
        }
    }

    static Lane laneOf(String url) {
        String p = path(url);
        return ("/fapi/v1/klines".equals(p) || p.endsWith("/ticker/price")) ? Lane.HIGH : Lane.LOW;
    }

    // ------------------------------------------------------------------ trạng thái
    final int cap, hdrSoft, hdrHard;
    private final LongSupplier clock;
    private final ArrayDeque<long[]> window = new ArrayDeque<>();   // {ts, weight}
    private int used = 0;
    private long hdrMinute = -1;
    private int hdrLast = 0;

    final AtomicLong calls = new AtomicLong(), weight = new AtomicLong(), denied = new AtomicLong();
    final AtomicLong http429 = new AtomicLong(), http418 = new AtomicLong(), http4xx = new AtomicLong();
    private int peakUsed = 0, hdrMax = 0;
    private long lastCalls = 0, lastWeight = 0, lastDenied = 0, last429 = 0, last418 = 0, last4xx = 0;

    RestBudget(int cap, int hdrSoft, int hdrHard, LongSupplier clock) {
        this.cap = Math.max(LOW_RESERVE + 10, Math.min(MAX_CAP, cap));
        this.hdrSoft = hdrSoft;
        this.hdrHard = hdrHard;
        this.clock = clock;
    }

    private void evict(long now) {
        while (!window.isEmpty() && window.peekFirst()[0] <= now - WINDOW_MS) used -= (int) window.pollFirst()[1];
    }

    /** Thử lấy {@code w} weight ngay; trả 0 nếu được, ngược lại số ms nên chờ. */
    synchronized long tryAcquire(int w, Lane lane) {
        long now = clock.getAsLong();
        evict(now);
        long minute = now / WINDOW_MS;
        long toNextMin = (minute + 1) * WINDOW_MS - now + 50;
        if (BinanceRestGuard.isBanned()) return Math.max(200, BinanceRestGuard.BANNED_UNTIL_MS.get() - now);
        if (hdrMinute == minute) {
            if (hdrLast >= hdrHard) return toNextMin;
            if (lane == Lane.LOW && hdrLast >= hdrSoft) return toNextMin;
        }
        int limit = lane == Lane.HIGH ? cap : cap - LOW_RESERVE;
        if (used + w <= limit) {
            window.addLast(new long[]{now, w});
            used += w;
            if (used > peakUsed) peakUsed = used;
            calls.incrementAndGet();
            weight.addAndGet(w);
            return 0;
        }
        long[] first = window.peekFirst();
        return first == null ? 100 : Math.max(20, first[0] + WINDOW_MS - now + 5);
    }

    /** Chờ tối đa {@code maxWaitMs}; false ⇒ không gọi sàn. */
    public boolean acquire(int w, Lane lane, long maxWaitMs) {
        long deadline = clock.getAsLong() + maxWaitMs;
        while (true) {
            long wait = tryAcquire(w, lane);
            if (wait == 0) return true;
            long left = deadline - clock.getAsLong();
            if (left <= 0) {
                denied.incrementAndGet();
                return false;
            }
            try {
                Thread.sleep(Math.max(1, Math.min(Math.min(wait, left), 500)));
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                denied.incrementAndGet();
                return false;
            }
        }
    }

    void observe(int code, String usedWeightHdr, String retryAfterHdr) {
        long now = clock.getAsLong();
        if (usedWeightHdr != null) {
            try {
                int h = Integer.parseInt(usedWeightHdr.trim());
                synchronized (this) {
                    long minute = now / WINDOW_MS;
                    if (minute != hdrMinute || h > hdrLast) {
                        hdrMinute = minute;
                        hdrLast = h;
                    }
                    if (h > hdrMax) hdrMax = h;
                }
            } catch (NumberFormatException e) {
                LOG.debug("[REST-BUDGET] header weight khong phai so: {}", usedWeightHdr);
            }
        }
        if (code == 429 || code == 418) {
            if (code == 429) http429.incrementAndGet();
            else http418.incrementAndGet();
            long sec = code == 418 ? 120 : 60;
            if (retryAfterHdr != null) {
                try {
                    sec = Math.max(1, Long.parseLong(retryAfterHdr.trim()));
                } catch (NumberFormatException e) {
                    LOG.debug("[REST-BUDGET] Retry-After khong phai so: {}", retryAfterHdr);
                }
            }
            BinanceRestGuard.cooldownUntil(now + sec * 1000L, "HTTP " + code + " Retry-After=" + retryAfterHdr);
        } else if (code >= 400) {
            http4xx.incrementAndGet();
        }
    }

    /** Dòng thống kê (delta kể từ lần gọi trước) — 1 lần/phút từ BinanceDataIngestor. */
    public synchronized String statsLine() {
        evict(clock.getAsLong());
        long c = calls.get(), w = weight.get(), d = denied.get(), a = http429.get(), b = http418.get(), x = http4xx.get();
        String s = String.format("calls=%d weight=%d peak60s=%d now60s=%d denied=%d http429=%d http418=%d http4xx=%d hdr_max=%d cap=%d",
                c - lastCalls, w - lastWeight, peakUsed, used, d - lastDenied, a - last429, b - last418, x - last4xx, hdrMax, cap);
        lastCalls = c;
        lastWeight = w;
        lastDenied = d;
        last429 = a;
        last418 = b;
        last4xx = x;
        peakUsed = used;
        hdrMax = 0;
        return s;
    }

    synchronized int usedNow() {
        evict(clock.getAsLong());
        return used;
    }

    synchronized int headerLast() {
        return hdrLast;
    }
}
