package com.binance.chuyennd.research.oibackfill;

import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.TreeSet;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * TASK-013 BƯỚC 2 — MASTER phân tán backfill OI/LS/taker history.
 * Tái dùng pattern {@code RunHpoMaster_Distributed}: master headless liệt kê universe symbol có metrics
 * (S3 listing data.binance.vision) → symbol CHƯA done thì ném task PENDING vào {@link OiMetricSets#QUEUE_SET}
 * trên Aerospike <b>226</b>; {@code BackfillOiWorker} (≤5 Kaggle) tiêu thụ. Queue Aerospike = checkpoint
 * phân tán (rerun chỉ làm symbol chưa DONE, KHÔNG lặp từ 0).
 *
 * <p>Args:
 * <ul>
 *   <li>không tham số → enumerate TOÀN BỘ symbol metrics (universe ~896 gồm delist — survivorship).</li>
 *   <li>danh sách symbol (vd {@code BTCUSDT,LUNAUSDT}) → CHỈ enqueue các symbol đó (dùng cho TEST NHỎ ở GATE).</li>
 * </ul>
 *
 * <p>Master KHÔNG tải/ghi metrics — chỉ điều phối + theo dõi. Hết việc (queue rỗng) → {@code System.exit(0)} (CLAUDE.md #6).
 */
public class BackfillOiMaster {

    private static final Logger LOG = LoggerFactory.getLogger(BackfillOiMaster.class);

    private static final String QUEUE_SET = OiMetricSets.QUEUE_SET;
    private static final String DONE_SET = OiMetricSets.DONE_SET;

    public static void main(String[] args) {
        LOG.info("👑 BACKFILL-OI MASTER khởi động | queue={} | done={}", QUEUE_SET, DONE_SET);

        // --reset: xoá sạch queue + done (dùng khi re-test hoặc dọn checkpoint cũ). KHÔNG đụng 5 set data.
        if (args != null && args.length > 0 && "--reset".equalsIgnoreCase(args[0])) {
            try {
                DataManagerAerospikeFloatSim.getClientOracle().truncate(null, Configs.AEROSPIKE_NAMESPACE, QUEUE_SET, null);
                DataManagerAerospikeFloatSim.getClientOracle().truncate(null, Configs.AEROSPIKE_NAMESPACE, DONE_SET, null);
                LOG.info("🧹 Đã truncate {} + {} (checkpoint reset). KHÔNG đụng set data OI/LS/taker.", QUEUE_SET, DONE_SET);
            } catch (Exception e) {
                LOG.error("❌ Reset truncate lỗi: ", e);
                System.exit(1);
            }
            System.exit(0);
        }

        // --reset-stale: reset task RUNNING qua han (kernel bi Kaggle kill) ve PENDING de worker moi cuop lai.
        // KHONG mat data da ghi. KHONG xoa DONE set. Chi dung khi tat ca kernel da COMPLETE/ERROR ma DONE < universe.
        if (args != null && args.length > 0 && "--reset-stale".equalsIgnoreCase(args[0])) {
            long staleMs = 45 * 60_000L;
            long now = System.currentTimeMillis();
            int[] counts = {0, 0}; // [reset, skip]
            try {
                DataManagerAerospikeFloatSim.getClientOracle().scanAll(null, Configs.AEROSPIKE_NAMESPACE, QUEUE_SET,
                        (key, record) -> {
                            String status = record.getString("status");
                            long startTime = record.getLong("startTime");
                            if ("RUNNING".equals(status) && (now - startTime) > staleMs) {
                                com.aerospike.client.policy.WritePolicy wp = new com.aerospike.client.policy.WritePolicy();
                                wp.sendKey = true;
                                try {
                                    DataManagerAerospikeFloatSim.getClientOracle().put(wp, key,
                                            new com.aerospike.client.Bin("status", "PENDING"),
                                            new com.aerospike.client.Bin("startTime", 0L));
                                    counts[0]++;
                                } catch (Exception e) {
                                    LOG.warn("reset-stale: khong update duoc {}: {}", key, e.getMessage());
                                }
                            } else {
                                counts[1]++;
                            }
                        }, "status", "startTime", "symbol");
                LOG.info("reset-stale XONG: reset={} RUNNING->PENDING, skip={} (PENDING/fresh RUNNING)", counts[0], counts[1]);
            } catch (Exception e) {
                LOG.error("reset-stale loi: ", e);
                System.exit(1);
            }
            System.exit(0);
        }

        try {
            List<String> universe = resolveUniverse(args);
            LOG.info("🌐 Universe = {} symbol cần backfill.", universe.size());

            int enqueued = 0, alreadyDone = 0, alreadyQueued = 0;
            for (String symbol : universe) {
                try {
                    if (isDone(symbol)) {
                        alreadyDone++;
                        continue;
                    }
                    if (enqueue(symbol)) enqueued++;
                    else alreadyQueued++;
                } catch (Exception e) {
                    LOG.warn("⚠️ Master bỏ qua enqueue {} (lỗi tạm thời): {}", symbol, e.getMessage());
                }
            }
            LOG.info("📤 Enqueue xong: mới={} | đã-done(skip)={} | đã-trong-queue={} | tổng universe={}",
                    enqueued, alreadyDone, alreadyQueued, universe.size());

            monitor(universe.size());
        } catch (Exception e) {
            LOG.error("❌ Master lỗi nghiêm trọng: ", e);
            System.exit(1);
        }
        System.exit(0);
    }

    /** Xác định universe theo args (test) hoặc S3 listing (full). */
    private static List<String> resolveUniverse(String[] args) throws Exception {
        if (args != null && args.length > 0) {
            TreeSet<String> set = new TreeSet<>();
            for (String a : args) {
                for (String s : a.split("[,\\s]+")) {
                    if (!s.trim().isEmpty()) set.add(s.trim().toUpperCase());
                }
            }
            LOG.info("🧪 TEST MODE — universe từ args: {}", set);
            return new ArrayList<>(set);
        }
        VisionMetricsClient client = new VisionMetricsClient();
        TreeSet<String> all = client.listSymbols();
        // breakdown log để soát (không lọc — backfill TOÀN BỘ theo user chốt B1.5).
        int usdt = 0, usdc = 0, other = 0;
        for (String s : all) {
            if (s.endsWith("USDT")) usdt++;
            else if (s.endsWith("USDC")) usdc++;
            else other++;
        }
        LOG.info("🌐 Metrics universe (S3): tổng={} | USDT={} | USDC={} | khác={}", all.size(), usdt, usdc, other);
        return new ArrayList<>(all);
    }

    private static boolean isDone(String symbol) {
        Key doneKey = new Key(Configs.AEROSPIKE_NAMESPACE, DONE_SET, symbol);
        Record r = DataManagerAerospikeFloatSim.getClientOracle().get(null, doneKey);
        return r != null;
    }

    /** Đẩy task PENDING vào queue (CREATE_ONLY chống ghi đè task đang RUNNING). true nếu vừa tạo mới. */
    private static boolean enqueue(String symbol) {
        Key queueKey = new Key(Configs.AEROSPIKE_NAMESPACE, QUEUE_SET, symbol);
        WritePolicy wp = new WritePolicy();
        wp.sendKey = true;
        wp.expiration = 0;
        wp.recordExistsAction = RecordExistsAction.CREATE_ONLY;
        try {
            DataManagerAerospikeFloatSim.getClientOracle().put(wp, queueKey,
                    new com.aerospike.client.Bin("symbol", symbol),
                    new com.aerospike.client.Bin("status", "PENDING"),
                    new com.aerospike.client.Bin("startTime", 0L));
            return true;
        } catch (com.aerospike.client.AerospikeException e) {
            // KEY_EXISTS_ERROR: task đã có trong queue (PENDING/RUNNING) → không tạo lại.
            return false;
        }
    }

    /** Theo dõi tiến độ: in dashboard mỗi 30s; queue cạn → trả về (main exit). */
    private static void monitor(int total) throws InterruptedException {
        LOG.info("📡 MONITOR — chờ worker rút cạn queue (tổng {} symbol)...", total);
        int idleTicks = 0;
        while (true) {
            int[] qc = queueCounts();
            int pending = qc[0], running = qc[1];
            int done = doneCount();
            LOG.info("📊 queue: PENDING={} RUNNING={} | DONE={}/{}", pending, running, done, total);

            if (pending + running == 0) {
                idleTicks++;
                // xác nhận 2 lần liên tiếp queue rỗng (tránh đọc giữa lúc worker đang chuyển trạng thái).
                if (idleTicks >= 2) {
                    LOG.info("✅ Queue rỗng. Backfill kết thúc (DONE={}/{}).", done, total);
                    return;
                }
            } else {
                idleTicks = 0;
            }
            Thread.sleep(30_000L);
        }
    }

    /** Đếm PENDING/RUNNING trong queue (scan set nhỏ). */
    private static int[] queueCounts() {
        AtomicInteger pending = new AtomicInteger();
        AtomicInteger running = new AtomicInteger();
        try {
            DataManagerAerospikeFloatSim.getClientOracle().scanAll(null, Configs.AEROSPIKE_NAMESPACE, QUEUE_SET,
                    (key, record) -> {
                        String st = record.getString("status");
                        if ("RUNNING".equals(st)) running.incrementAndGet();
                        else pending.incrementAndGet();
                    }, "status");
        } catch (Exception e) {
            LOG.warn("⚠️ scan queue lỗi (coi như chưa rỗng): {}", e.getMessage());
            pending.incrementAndGet(); // ép không-rỗng để monitor không exit nhầm
        }
        return new int[]{pending.get(), running.get()};
    }

    /** Đếm symbol DONE (scan set done). */
    private static int doneCount() {
        AtomicInteger c = new AtomicInteger();
        try {
            DataManagerAerospikeFloatSim.getClientOracle().scanAll(null, Configs.AEROSPIKE_NAMESPACE, DONE_SET,
                    (key, record) -> c.incrementAndGet());
        } catch (Exception e) {
            LOG.warn("⚠️ scan done lỗi: {}", e.getMessage());
        }
        return c.get();
    }
}
