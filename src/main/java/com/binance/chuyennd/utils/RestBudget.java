package com.binance.chuyennd.utils;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayDeque;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.LongSupplier;

/**
 * [INGEST-QF2 2026-10-31] Ngân sách REST CỨNG cho mọi call {@code https://fapi.binance.com/} của MỘT JVM (bật bởi
 * {@code BinanceDataIngestor.main}; JVM khác không gọi {@link #enable} ⇒ không đổi hành vi).
 * Prereg: docs/prereg/PREREG_INGEST_QUICKFIX.md ADDENDUM 1 + ADD-1b + ADD-1c.
 * <ul>
 *   <li>Weight IP tự đếm, cửa sổ trượt 60 s, tổng ≤ {@code cap} (≤300), HẠN MỨC RIÊNG từng lane (không lồng nhau):
 *     <b>PRICE</b> ({@code ticker/price}) {@link #PRICE_QUOTA} — chỉ giá dùng, kline/LOW không chạm được;
 *     <b>KLINE</b> ({@code klines} limit&lt;100) {@link #KLINE_QUOTA}, KHÔNG chờ (hết chỗ ⇒ false ngay, để phút sau);
 *     <b>LOW</b> (premiumIndex, exchangeInfo, klines limit≥100 = repair/roller, ...) {@code cap-PRICE_QUOTA-KLINE_QUOTA}.</li>
 *   <li><b>FDATA</b> ({@code /futures/data/*} OI/LS/taker): KHÔNG vào weight IP; bucket riêng ≤ {@code fdataCap} request/60 s
 *       (hạn mức sàn 1 000/5′).</li>
 *   <li>Header {@code X-MBX-USED-WEIGHT-1M} gán theo phút GIỜ SÀN (header {@code Date}): ≥ hdrSoft ⇒ LOW chờ sang phút sau;
 *       ≥ hdrHard ⇒ KLINE + LOW chờ; PRICE chỉ dừng khi ≥ {@link #HDR_PRICE_STOP}.</li>
 *   <li>HTTP 429/418 ⇒ cooldown GLOBAL ngay ({@link BinanceRestGuard#cooldownUntil}) theo {@code Retry-After}; mọi lane dừng.</li>
 * </ul>
 */
public final class RestBudget {
    private static final Logger LOG = LoggerFactory.getLogger(RestBudget.class);
    public static final String FAPI = "https://fapi.binance.com/";
    public static final int MAX_CAP = 300;
    /** [ADD-1c] Hạn mức RIÊNG từng lane (không lồng nhau ⇒ lane này không bỏ đói lane kia): PRICE 60, KLINE 200, LOW = cap−260. */
    public static final int PRICE_QUOTA = 60;
    public static final int KLINE_QUOTA = 200;
    public static final int HDR_PRICE_STOP = 2300;
    public static final int DEFAULT_FDATA_CAP = 150;
    static final long WINDOW_MS = 60_000L;

    public enum Lane { PRICE, KLINE, LOW, FDATA }

    private static volatile RestBudget INSTANCE = null;

    public static synchronized RestBudget enable(int cap, int hdrSoft, int hdrHard, int fdataCap) {
        INSTANCE = new RestBudget(cap, hdrSoft, hdrHard, fdataCap, System::currentTimeMillis);
        LOG.info("[REST-BUDGET] bat: cap={} weight/60s (PRICE {}, KLINE {}, LOW {} — han muc rieng), futures/data {} req/60s, hdrSoft={} hdrHard={}",
                INSTANCE.cap, INSTANCE.limitOf(Lane.PRICE), INSTANCE.limitOf(Lane.KLINE), INSTANCE.limitOf(Lane.LOW), INSTANCE.fdataCap, hdrSoft, hdrHard);
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

    /** Thời gian chờ tối đa theo lane: KLINE KHÔNG chờ (không xếp hàng chặn), PRICE ≤5 s, LOW/FDATA ≤30 s. */
    public static long maxWaitMs(Lane lane) {
        switch (lane) {
            case KLINE: return 0L;
            case PRICE: return 5_000L;
            default: return 30_000L;
        }
    }

    /** Hook trước MỖI lần mở kết nối trong HttpRequest. Không bật / không phải fapi ⇒ true ngay. */
    public static boolean beforeRequest(String url) {
        RestBudget b = INSTANCE;
        if (b == null || !isFapi(url)) return true;
        Lane lane = laneOf(url);
        return b.acquire(weightOf(url), lane, maxWaitMs(lane));
    }

    /** Hook sau khi có status code. */
    public static void afterResponse(String url, int code, String usedWeightHdr, String retryAfterHdr, String dateHdr) {
        RestBudget b = INSTANCE;
        if (b == null || !isFapi(url)) return;
        b.observe(code, usedWeightHdr, retryAfterHdr, dateHdr);
    }

    // ------------------------------------------------------------------ bảng weight + lane (Binance UM)
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

    static int klineLimit(String url) {
        try {
            String l = param(url, "limit");
            return l == null ? 500 : Integer.parseInt(l);
        } catch (NumberFormatException e) {
            return 1500;   // khong doc duoc limit => tinh muc cao nhat (bao thu)
        }
    }

    /** Weight theo tài liệu Binance UM; endpoint lạ ⇒ 5 (bảo thủ); futures/data = 1 request (bucket riêng). */
    public static int weightOf(String url) {
        String p = path(url);
        boolean sym = param(url, "symbol") != null;
        switch (p) {
            case "/fapi/v1/klines":
            case "/fapi/v1/continuousKlines":
            case "/fapi/v1/markPriceKlines":
            case "/fapi/v1/indexPriceKlines": {
                int lim = klineLimit(url);
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
                if (p.startsWith("/futures/data/")) return 1;
                return 5;
        }
    }

    public static Lane laneOf(String url) {
        String p = path(url);
        if (p.startsWith("/futures/data/")) return Lane.FDATA;
        if (p.endsWith("/ticker/price")) return Lane.PRICE;
        if ("/fapi/v1/klines".equals(p) && klineLimit(url) < 100) return Lane.KLINE;
        return Lane.LOW;   // gom klines limit>=100 (repair khoi dong, roller)
    }

    // ------------------------------------------------------------------ trạng thái
    final int cap, hdrSoft, hdrHard, fdataCap;
    private final LongSupplier clock;
    private final ArrayDeque<long[]> window = new ArrayDeque<>();   // {ts, weight, lane.ordinal}
    private final ArrayDeque<Long> fwindow = new ArrayDeque<>();    // ts request futures/data
    private int used = 0;                                           // tong weight IP 60 s (moi lane)
    private final int[] usedLane = new int[3];                      // PRICE, KLINE, LOW
    private long hdrMinute = -1;      // phut GIO SAN cua header
    private int hdrLast = 0;
    private long skewMs = 0;          // gio san - gio local (tu header Date, do phan giai 1 s)

    final AtomicLong calls = new AtomicLong(), weight = new AtomicLong(), denied = new AtomicLong(), fcalls = new AtomicLong();
    final AtomicLong http429 = new AtomicLong(), http418 = new AtomicLong(), http4xx = new AtomicLong();
    private int peakUsed = 0, hdrMax = 0, fpeak = 0;
    private long lastCalls = 0, lastWeight = 0, lastDenied = 0, last429 = 0, last418 = 0, last4xx = 0, lastF = 0;

    RestBudget(int cap, int hdrSoft, int hdrHard, int fdataCap, LongSupplier clock) {
        this.cap = Math.max(PRICE_QUOTA + KLINE_QUOTA + 20, Math.min(MAX_CAP, cap));
        this.hdrSoft = hdrSoft;
        this.hdrHard = hdrHard;
        this.fdataCap = Math.max(10, Math.min(190, fdataCap));
        this.clock = clock;
    }

    int limitOf(Lane lane) {
        switch (lane) {
            case PRICE: return PRICE_QUOTA;
            case KLINE: return KLINE_QUOTA;
            case LOW: return cap - PRICE_QUOTA - KLINE_QUOTA;
            default: return fdataCap;
        }
    }

    private void evict(long now) {
        while (!window.isEmpty() && window.peekFirst()[0] <= now - WINDOW_MS) {
            long[] e = window.pollFirst();
            used -= (int) e[1];
            usedLane[(int) e[2]] -= (int) e[1];
        }
        while (!fwindow.isEmpty() && fwindow.peekFirst() <= now - WINDOW_MS) fwindow.pollFirst();
    }

    /** Lane có bị header/ban chặn ở thời điểm này không; trả số ms nên chờ (0 = không chặn). */
    private long blockedMs(Lane lane, long now) {
        if (BinanceRestGuard.isBanned()) return Math.max(200, BinanceRestGuard.BANNED_UNTIL_MS.get() - now);
        if (lane == Lane.FDATA) return 0;
        long srv = now + skewMs;
        long minute = srv / WINDOW_MS;
        if (hdrMinute != minute) return 0;
        long toNext = (minute + 1) * WINDOW_MS - srv + 50;
        if (lane == Lane.PRICE) return hdrLast >= HDR_PRICE_STOP ? toNext : 0;
        if (hdrLast >= hdrHard) return toNext;
        if (lane == Lane.LOW && hdrLast >= hdrSoft) return toNext;
        return 0;
    }

    /** Thử lấy {@code w} weight ngay; trả 0 nếu được, ngược lại số ms nên chờ. */
    synchronized long tryAcquire(int w, Lane lane) {
        long now = clock.getAsLong();
        evict(now);
        long b = blockedMs(lane, now);
        if (b > 0) return b;
        if (lane == Lane.FDATA) {
            if (fwindow.size() + 1 <= fdataCap) {
                fwindow.addLast(now);
                if (fwindow.size() > fpeak) fpeak = fwindow.size();
                fcalls.incrementAndGet();
                return 0;
            }
            Long first = fwindow.peekFirst();
            return first == null ? 100 : Math.max(20, first + WINDOW_MS - now + 5);
        }
        int o = lane.ordinal();
        if (usedLane[o] + w <= limitOf(lane)) {
            window.addLast(new long[]{now, w, o});
            used += w;
            usedLane[o] += w;
            if (used > peakUsed) peakUsed = used;
            calls.incrementAndGet();
            weight.addAndGet(w);
            return 0;
        }
        long[] first = window.peekFirst();
        return first == null ? 100 : Math.max(20, first[0] + WINDOW_MS - now + 5);
    }

    /** Weight còn lấy được NGAY cho lane (0 nếu bị header/ban chặn) — để pass kline chỉ lấy phần vừa chỗ, không xếp hàng. */
    public synchronized int available(Lane lane) {
        long now = clock.getAsLong();
        evict(now);
        if (blockedMs(lane, now) > 0) return 0;
        if (lane == Lane.FDATA) return Math.max(0, fdataCap - fwindow.size());
        return Math.max(0, limitOf(lane) - usedLane[lane.ordinal()]);
    }

    /** Chờ tối đa {@code maxWaitMs}; false ⇒ không gọi sàn (đếm denied). */
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
                Thread.sleep(Math.max(1, Math.min(Math.min(wait, left), 200)));
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                denied.incrementAndGet();
                return false;
            }
        }
    }

    static long parseHttpDate(String d) {
        try {
            return ZonedDateTime.parse(d.trim(), DateTimeFormatter.RFC_1123_DATE_TIME).toInstant().toEpochMilli();
        } catch (Exception e) {
            return -1;
        }
    }

    void observe(int code, String usedWeightHdr, String retryAfterHdr, String dateHdr) {
        long now = clock.getAsLong();
        long srvMs = dateHdr == null ? -1 : parseHttpDate(dateHdr);
        if (usedWeightHdr != null) {
            try {
                int h = Integer.parseInt(usedWeightHdr.trim());
                synchronized (this) {
                    if (srvMs > 0) skewMs = srvMs + 500 - now;   // Date lam tron xuong giay => +500 ms
                    long minute = (now + skewMs) / WINDOW_MS;
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
        long c = calls.get(), w = weight.get(), d = denied.get(), a = http429.get(), b = http418.get(), x = http4xx.get(), f = fcalls.get();
        String s = String.format("calls=%d weight=%d peak60s=%d now60s=%d fdata=%d fdata_peak60s=%d denied=%d http429=%d http418=%d http4xx=%d hdr_max=%d skew_ms=%d cap=%d",
                c - lastCalls, w - lastWeight, peakUsed, used, f - lastF, fpeak, d - lastDenied, a - last429, b - last418, x - last4xx,
                hdrMax, skewMs, cap);
        lastCalls = c;
        lastWeight = w;
        lastDenied = d;
        last429 = a;
        last418 = b;
        last4xx = x;
        lastF = f;
        peakUsed = used;
        fpeak = fwindow.size();
        hdrMax = 0;
        return s;
    }

    /** Tạo instance KHÔNG cài làm global (test / mô phỏng). */
    public static RestBudget create(int cap, int hdrSoft, int hdrHard, int fdataCap, LongSupplier clock) {
        return new RestBudget(cap, hdrSoft, hdrHard, fdataCap, clock);
    }

    public synchronized int usedNow() {
        evict(clock.getAsLong());
        return used;
    }

    public synchronized int fdataNow() {
        evict(clock.getAsLong());
        return fwindow.size();
    }
}
