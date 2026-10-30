package com.binance.chuyennd.utils;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayDeque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;

/**
 * [INGEST-QF2/QF3] Giám sát loop chính trong JVM (thay "restart JVM" làm đường tự cứu, MAJ-1 A1_QF_REPORT):
 * thân loop thoát vì {@link Throwable} (Error/OOM/RuntimeException lọt) hoặc tự return ⇒ log ERROR, đếm, ngủ backoff
 * (1 s → 30 s, reset sau 10′ chạy ổn) rồi chạy LẠI thân loop trên CÙNG thread. Thread bị interrupt ⇒ dừng hẳn.
 * <p>[QF3, ADD2, A1_QF2 MIN-C] Leo thang: một loop chết &gt; {@link #ESCALATE_PER_HOUR} lần trong 1 giờ ⇒ ERROR + cảnh báo KHẨN qua
 * {@link #setAlertSink} (Telegram), tối đa 1 tin/{@link #ALERT_EVERY_MS}/loop; vẫn dựng lại. Loop hỏng vĩnh viễn ở backoff trần
 * 30 s = 2 880 lần/ngày (trần lý thuyết, không phải lỗi quan sát được) ⇒ nay có cảnh báo trong ≤ ~6′ thay vì chỉ log.
 */
public final class LoopSupervisor {
    private static final Logger LOG = LoggerFactory.getLogger(LoopSupervisor.class);
    /** Tổng số lần dựng lại loop từ khi JVM start (metric loop_restarts, prereg Q10). */
    public static final AtomicLong RESTARTS = new AtomicLong();
    /** Tổng số lần đã leo thang (gửi cảnh báo KHẨN). */
    public static final AtomicLong ESCALATIONS = new AtomicLong();
    public static final int ESCALATE_PER_HOUR = 10;
    public static final long ALERT_EVERY_MS = 30 * 60_000L;
    static volatile long minBackoffMs = 1_000L, maxBackoffMs = 30_000L;
    private static volatile Consumer<String> alertSink = null;
    private static final Map<String, ArrayDeque<Long>> DEATHS = new ConcurrentHashMap<>();
    private static final Map<String, Long> LAST_ALERT = new ConcurrentHashMap<>();

    private LoopSupervisor() {
    }

    /** Kênh cảnh báo KHẨN (vd Telegram). null ⇒ chỉ log. */
    public static void setAlertSink(Consumer<String> sink) {
        alertSink = sink;
    }

    /** Ghi nhận một lần chết; trả true nếu lần này phải leo thang (đã gửi cảnh báo). Thuần theo {@code now}, test được. */
    static boolean recordDeath(String name, String why, long now) {
        ArrayDeque<Long> q = DEATHS.computeIfAbsent(name, k -> new ArrayDeque<>());
        int n;
        synchronized (q) {
            q.addLast(now);
            while (!q.isEmpty() && q.peekFirst() <= now - 3_600_000L) q.pollFirst();
            n = q.size();
        }
        if (n <= ESCALATE_PER_HOUR) return false;
        Long last = LAST_ALERT.get(name);
        if (last != null && now - last < ALERT_EVERY_MS) return false;
        LAST_ALERT.put(name, now);
        ESCALATIONS.incrementAndGet();
        String msg = "KHAN collectData 242: loop " + name + " chet " + n + " lan/1h (>" + ESCALATE_PER_HOUR + "), van dung lai — can nguoi xem. Loi: " + why;
        LOG.error("[SUPERVISOR] LEO THANG: {}", msg);
        Consumer<String> s = alertSink;
        if (s != null) {
            try {
                s.accept(msg);
            } catch (Exception e) {
                LOG.warn("[SUPERVISOR] gui canh bao loi: {}", e.toString());
            }
        }
        return true;
    }

    /** Bọc thân loop: dùng {@code new Thread(LoopSupervisor.wrap("ten", () -> {...}))}. */
    public static Runnable wrap(String name, Runnable body) {
        return () -> {
            long backoff = minBackoffMs;
            while (!Thread.currentThread().isInterrupted()) {
                long t0 = System.currentTimeMillis();
                String why;
                try {
                    body.run();
                    why = "thoat binh thuong (khong mong doi)";
                } catch (Throwable t) {
                    why = t.toString();
                    LOG.error("[SUPERVISOR] loop {} chet: {}", name, why, t);
                }
                if (Thread.currentThread().isInterrupted()) return;
                if (System.currentTimeMillis() - t0 > 600_000L) backoff = minBackoffMs;
                long n = RESTARTS.incrementAndGet();
                recordDeath(name, why, System.currentTimeMillis());
                LOG.error("[SUPERVISOR] dung lai loop {} sau {} ms (lan thu {} toan JVM): {}", name, backoff, n, why);
                try {
                    Thread.sleep(backoff);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return;
                }
                backoff = Math.min(maxBackoffMs, backoff * 2);
            }
        };
    }

    /** Tạo + start thread được giám sát. */
    public static Thread start(String name, Runnable body, boolean daemon) {
        Thread t = new Thread(wrap(name, body), name);
        t.setDaemon(daemon);
        t.start();
        return t;
    }
}
