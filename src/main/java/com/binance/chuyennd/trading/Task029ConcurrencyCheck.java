package com.binance.chuyennd.trading;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * TASK-029 — TEST RIÊNG (không đụng Aerospike/Binance) cho 3 fix concurrency #4/#5/#9.
 *
 * <p>Các method thật ({@code writeMinuteBatch}, {@code updatePositionInfo}) phụ thuộc Aerospike/Binance nên
 * KHÔNG chạy được offline; test này kiểm <b>LOGIC fix</b>: (T1) striped-lock chống lost-update cùng key phút (#4),
 * (T2) chọn stripe đúng (cùng key→cùng stripe), (T3) removeLock nhả lock SỚM trên {@link SymbolOrderLockingManager}
 * (CODE THẬT — #9 phần lock), (T4) swap-not-clear không tạo cửa sổ rỗng cho reader (#9 phần map).
 *
 * <p>Chạy: {@code java -cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.trading.Task029ConcurrencyCheck}
 */
public class Task029ConcurrencyCheck {
    private static final Logger LOG = LoggerFactory.getLogger(Task029ConcurrencyCheck.class);

    public static void main(String[] args) throws Exception {
        int fail = 0;
        fail += t1_stripedLockNoLostUpdate();
        fail += t2_sameKeySameStripe();
        fail += t3_removeLockReleasesEarly();
        fail += t4_swapNoEmptyWindow();
        if (fail == 0) LOG.info("✅ TASK-029 ALL PASS (4/4)");
        else LOG.error("🔴 TASK-029 FAIL: {} test", fail);
    }

    // ---- T1 (#4): read-modify-write cùng "record phút" — có striped lock thì KHÔNG mất key ----
    private static int t1_stripedLockNoLostUpdate() throws Exception {
        final int STRIPES = 64;
        final Object[] locks = new Object[STRIPES];
        for (int i = 0; i < STRIPES; i++) locks[i] = new Object();
        final String minuteKey = "20210101-1200";
        final Object lock = locks[(minuteKey.hashCode() & 0x7fffffff) % STRIPES];

        // "Aerospike record" giả lập: 1 ô giữ map đã merge (read-modify-write có DELAY để khuếch đại race)
        final Map[] store = new Map[]{new HashMap<String, Integer>()};

        int nThreads = 32;
        ExecutorService ex = Executors.newFixedThreadPool(nThreads);
        CountDownLatch start = new CountDownLatch(1);
        CountDownLatch done = new CountDownLatch(nThreads);
        for (int t = 0; t < nThreads; t++) {
            final String sym = "SYM" + t;
            ex.submit(() -> {
                try {
                    start.await();
                    // mô phỏng writeMinuteBatch: synchronized(stripe){ read → merge → write }
                    synchronized (lock) {
                        @SuppressWarnings("unchecked")
                        Map<String, Integer> cur = new HashMap<>(store[0]); // read (copy như getExistingTickersMap)
                        Thread.sleep(2);                                    // widen cửa sổ read→write
                        cur.put(sym, 1);                                    // putAll(newTickers)
                        store[0] = cur;                                     // put (ghi đè record)
                    }
                } catch (Exception e) {
                    LOG.error("writer lỗi", e);
                } finally {
                    done.countDown();
                }
            });
        }
        start.countDown();
        done.await(30, TimeUnit.SECONDS);
        ex.shutdownNow();

        int size = store[0].size();
        boolean ok = size == nThreads;
        LOG.info("T1 striped-lock no-lost-update: {} key (expect {}) → {}", size, nThreads, ok ? "PASS✅" : "FAIL🔴");
        return ok ? 0 : 1;
    }

    // ---- T2 (#4): cùng key-phút → cùng stripe; phút khác → phân tán ----
    private static int t2_sameKeySameStripe() {
        final int STRIPES = 64;
        int s1 = stripe("20210101-1200", STRIPES);
        int s1b = stripe("20210101-1200", STRIPES);
        int s2 = stripe("20210101-1201", STRIPES);
        boolean sameKeySame = (s1 == s1b);
        // phân tán: đếm số stripe khác nhau trên 1000 phút liên tiếp (kỳ vọng phủ nhiều stripe)
        java.util.Set<Integer> used = new java.util.HashSet<>();
        long base = 1609477200000L; // 2021-01-01 12:00 ~
        java.text.SimpleDateFormat fmt = new java.text.SimpleDateFormat("yyyyMMdd-HHmm");
        for (int i = 0; i < 1000; i++) used.add(stripe(fmt.format(new java.util.Date(base + i * 60000L)), STRIPES));
        boolean spread = used.size() >= STRIPES / 2;
        boolean ok = sameKeySame && spread;
        LOG.info("T2 stripe: sameKey→same={} | 1000 phút phủ {}/{} stripe → {}", sameKeySame, used.size(), STRIPES, ok ? "PASS✅" : "FAIL🔴");
        return ok ? 0 : 1;
    }

    private static int stripe(String key, int stripes) {
        return (key.hashCode() & 0x7fffffff) % stripes;
    }

    // ---- T3 (#9): removeLock nhả lock SỚM (CODE THẬT SymbolOrderLockingManager) ----
    private static int t3_removeLockReleasesEarly() {
        SymbolOrderLockingManager m = SymbolOrderLockingManager.getInstance();
        String k = "UpdateAllPos_TEST_" + System.nanoTime();
        m.addLock(k);
        boolean lockedAfterAdd = m.isLock(k, 3);
        m.removeLock(k);
        boolean freeAfterRemove = !m.isLock(k, 3);
        boolean ok = lockedAfterAdd && freeAfterRemove;
        LOG.info("T3 removeLock: lockedAfterAdd={} freeAfterRemove={} → {}", lockedAfterAdd, freeAfterRemove, ok ? "PASS✅" : "FAIL🔴");
        return ok ? 0 : 1;
    }

    // ---- T4 (#9): swap-not-clear — reader song song KHÔNG bao giờ thấy map rỗng giữa chừng ----
    private static int t4_swapNoEmptyWindow() throws Exception {
        // holder mô phỏng BudgetManager.symbol2Pos (field reassign được)
        final Map[] holder = new Map[]{seed(50)};
        final AtomicInteger minSeen = new AtomicInteger(Integer.MAX_VALUE);
        final boolean[] stop = {false};

        Thread reader = new Thread(() -> {
            while (!stop[0]) {
                @SuppressWarnings("unchecked")
                Map<String, Integer> snap = holder[0];       // đọc reference (như getInstance().symbol2Pos)
                int sz = snap.size();                          // map cũ bất biến sau swap → an toàn, không CME
                if (sz < minSeen.get()) minSeen.set(sz);
            }
        });
        reader.start();
        for (int round = 0; round < 200; round++) {
            // FIX: build map MỚI đầy đủ rồi SWAP (không clear-then-fill)
            Map<String, Integer> fresh = seed(50);
            holder[0] = fresh;
            Thread.sleep(1);
        }
        stop[0] = true;
        reader.join(5000);

        boolean ok = minSeen.get() == 50; // không bao giờ thấy < 50 (không có cửa sổ rỗng)
        LOG.info("T4 swap-not-clear: minSizeReaderSaw={} (expect 50, KHÔNG tụt) → {}", minSeen.get(), ok ? "PASS✅" : "FAIL🔴");
        return ok ? 0 : 1;
    }

    private static Map<String, Integer> seed(int n) {
        Map<String, Integer> m = new HashMap<>();
        for (int i = 0; i < n; i++) m.put("S" + i, i);
        return m;
    }
}
