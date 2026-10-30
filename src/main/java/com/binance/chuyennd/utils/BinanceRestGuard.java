package com.binance.chuyennd.utils;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Cooldown GLOBAL theo IP cho MỌI REST caller tới Binance (ticker price/kline/repair + funding + OI).
 * <p>Binance ban theo IP, nên cooldown phải DÙNG CHUNG một chỗ — KHÔNG mỗi class một biến, nếu không
 * một ingester hết-ban-cục-bộ vẫn gọi tiếp trong khi sàn còn ban → GIA HẠN ban. Mọi luồng đọc/ghi
 * cùng {@link #BANNED_UNTIL_MS}.
 * <p>Cách phát hiện ban: {@code HttpRequest.getContentFromUrl} nuốt status code và TRẢ BODY (đọc
 * {@code getErrorStream()} khi HTTP≥400), nên chỉ nhận biết ban qua parse body {@code -1003 / "banned until <ms>"}.
 */
public class BinanceRestGuard {
    private static final Logger LOG = LoggerFactory.getLogger(BinanceRestGuard.class);

    /** Mốc ms-epoch UTC mà REST được phép gọi lại. 0 = không ban. */
    public static final AtomicLong BANNED_UNTIL_MS = new AtomicLong(0);
    /** Cooldown fallback khi body có chữ "banned until" nhưng KHÔNG parse được số. */
    public static final long DEFAULT_COOLDOWN_MS = 5 * 60_000L;
    /** TASK-016: -1003 RATE (chưa "banned until") → backoff NGẮN để hạ nhịp NGAY, tránh leo IP-ban. */
    public static final long RATE_BACKOFF_MS = 8_000L;
    /** Đệm thêm sau mốc ban của sàn cho chắc (lệch đồng hồ / phòng gọi sát giờ). */
    public static final long SAFETY_BUFFER_MS = 10_000L;
    /** Anchor "banned until " để KHÔNG bắt nhầm số trong IP (vd 103.157...). */
    private static final Pattern BAN_UNTIL_PATTERN = Pattern.compile("banned until (\\d+)");

    /**
     * Parse mốc hết-ban (ms-epoch UTC) từ body lỗi của Binance.
     *
     * @param body body trả về từ REST call (có thể null/blank/JSON mảng giá bình thường).
     * @return mốc ms-epoch được phép gọi lại; {@code 0} nếu KHÔNG phải lỗi ban. Có dấu hiệu ban
     *         nhưng KHÔNG match số → {@code now + DEFAULT_COOLDOWN_MS} (fallback, không để lọt).
     */
    public static long parseBanUntilMs(String body) {
        if (body == null || body.isBlank()) return 0;
        // 1) BAN THẬT có mốc "banned until <ms>" → cooldown tới đúng mốc đó.
        Matcher m = BAN_UNTIL_PATTERN.matcher(body);
        if (m.find()) {
            try {
                return Long.parseLong(m.group(1));
            } catch (NumberFormatException e) {
                return System.currentTimeMillis() + DEFAULT_COOLDOWN_MS;
            }
        }
        // 2) -1003 RATE (chưa banned-until) → backoff NGẮN (hạ nhịp ngay, tránh leo thành IP-ban).
        if (body.contains("-1003")) {
            return System.currentTimeMillis() + RATE_BACKOFF_MS;
        }
        // 3) có chữ "banned until" nhưng không parse được số → fallback dài cho chắc.
        if (body.contains("banned until")) {
            return System.currentTimeMillis() + DEFAULT_COOLDOWN_MS;
        }
        // 4) -1130 (param) / -1121 / -4xxx (delist) / lỗi khác → KHÔNG cooldown.
        return 0;
    }

    /**
     * @return {@code true} nếu hiện đang trong cửa sổ ban (mọi REST call phải dừng).
     *         Body cũ có mốc {@code < now} sẽ tự cho {@code false}.
     */
    public static boolean isBanned() {
        return System.currentTimeMillis() < BANNED_UNTIL_MS.get();
    }

    /**
     * Nếu {@code body} là lỗi ban → đặt cooldown GLOBAL theo nguyên tắc atomic-max (nhiều luồng/nhiều
     * response không ghi đè nhau bằng giá trị gần hơn). Chỉ {@code LOG.warn} MỘT lần khi mốc mới đẩy
     * xa hơn mốc cũ (tránh spam mỗi 3s).
     *
     * @param body body trả về từ REST call.
     */
    public static void cooldownUntil(long untilMs, String why) {
        // [INGEST-QF 2026-10-30] HTTP 429/418 doc tu status + Retry-After (RestBudget) — atomic-max nhu reportBan.
        long target = untilMs + SAFETY_BUFFER_MS;
        long prev = BANNED_UNTIL_MS.getAndUpdate(p -> Math.max(p, target));
        if (target > prev) {
            LOG.warn("🔒 REST cooldown ({}) đến {}", why, new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date(target)));
            persist(target);
        }
    }

    // ===== [INGEST-QF3 2026-10-31] ban BEN qua restart JVM (A1_QF2 MAJ-A, prereg ADD2/Q11) — chi bat o JVM goi enablePersistence =====
    private static volatile java.nio.file.Path persistFile = null;

    /** Bật lưu mốc hết ban ra file + NẠP mốc cũ (JVM mới không gọi fapi trước mốc đó). Gọi ĐẦU main, trước mọi call. */
    public static synchronized long enablePersistence(java.nio.file.Path file) {
        persistFile = file;
        long loaded = readPersisted(file);
        long now = System.currentTimeMillis();
        if (loaded > now) {
            BANNED_UNTIL_MS.getAndUpdate(p -> Math.max(p, loaded));
            LOG.warn("🔒 [REST-BAN] nap moc ban tu {}: con ban {} s (toi {}) — KHONG goi fapi truoc moc nay", file, (loaded - now) / 1000,
                    new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date(loaded)));
        } else {
            LOG.info("[REST-BAN] file {}: khong con ban (moc={})", file, loaded);
        }
        return loaded;
    }

    static long readPersisted(java.nio.file.Path file) {
        try {
            return Long.parseLong(new String(java.nio.file.Files.readAllBytes(file), java.nio.charset.StandardCharsets.US_ASCII).trim());
        } catch (Exception e) {
            return 0L;
        }
    }

    private static void persist(long until) {
        java.nio.file.Path f = persistFile;
        if (f == null) return;
        try {
            java.nio.file.Path tmp = f.resolveSibling(f.getFileName() + ".tmp");
            java.nio.file.Files.write(tmp, Long.toString(Math.max(until, BANNED_UNTIL_MS.get())).getBytes(java.nio.charset.StandardCharsets.US_ASCII));
            java.nio.file.Files.move(tmp, f, java.nio.file.StandardCopyOption.REPLACE_EXISTING, java.nio.file.StandardCopyOption.ATOMIC_MOVE);
        } catch (Exception e) {
            LOG.error("[REST-BAN] khong ghi duoc moc ban {}: {}", f, e.toString());
        }
    }

    /** Chỉ cho test: tắt lưu file. */
    static void disablePersistence() {
        persistFile = null;
    }

    public static void reportBan(String body) {
        long banUntil = parseBanUntilMs(body);
        if (banUntil <= 0) return;
        long target = banUntil + SAFETY_BUFFER_MS;
        long prev = BANNED_UNTIL_MS.getAndUpdate(p -> Math.max(p, target));
        if (target > prev) {
            LOG.warn("🔒 REST banned, cooldown đến {}",
                    new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date(target)));
            persist(target);   // [INGEST-QF3]
        }
    }

    /**
     * Nếu đang ban → chờ tối đa {@code capMs} (cap mỗi nhịp để thread không kẹt quá lâu + cho phép
     * tái kiểm khi hết hạn) rồi trả {@code true} (đã chờ). Ngược lại trả {@code false} ngay.
     * <p>Caller nên gọi trong vòng lặp: {@code while (awaitIfBanned(60_000)) continue;} hoặc dùng
     * cờ riêng để log "resume" đúng một lần.
     *
     * @param capMs trần thời gian ngủ mỗi nhịp (ms).
     * @return {@code true} nếu đã chờ vì đang ban; {@code false} nếu không ban.
     */
    public static boolean awaitIfBanned(long capMs) {
        long now = System.currentTimeMillis();
        long until = BANNED_UNTIL_MS.get();
        if (now < until) {
            Utils.sleep(Math.min(until - now, capMs));
            return true;
        }
        return false;
    }
}
