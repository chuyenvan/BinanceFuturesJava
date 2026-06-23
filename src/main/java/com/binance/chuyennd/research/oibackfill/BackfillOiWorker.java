package com.binance.chuyennd.research.oibackfill;

import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.GenerationPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * TASK-013 BƯỚC 2 — WORKER phân tán backfill OI/LS/taker history (≤5 Kaggle CPU).
 * Tái dùng pattern {@code RunWorkerKaggle}: {@code while(true)} fetchTask race-safe (generation lock) +
 * cướp task RUNNING quá hạn (worker chết). Mỗi task = 1 symbol → tải metrics daily 2020→nay từ
 * data.binance.vision ({@link VisionMetricsClient}) → dedup + chuẩn-mốc-5m → ghi <b>226</b> 5 set
 * ({@link OiMetricSets#ALL}) bằng {@link DataManagerAerospikeFloatSim#writeMetricMap226} (merge-guard,
 * không ghi đè rỗng) → mark {@link OiMetricSets#DONE_SET} + xoá queue. Queue rỗng → {@code System.exit(0)} (#6).
 *
 * <p>KHÔNG đụng Redis/BinanceRestGuard/live — chỉ HttpURLConnection (vision) + Aerospike 226.
 */
public class BackfillOiWorker {

    private static final Logger LOG = LoggerFactory.getLogger(BackfillOiWorker.class);

    private static final String QUEUE_SET = OiMetricSets.QUEUE_SET;
    private static final String DONE_SET = OiMetricSets.DONE_SET;

    /** Task RUNNING quá ngưỡng này coi worker giữ nó đã chết → cho cướp. 1 symbol BTC ~2100 file → cho rộng 45'. */
    private static final long STALE_RUNNING_MS = 45 * 60_000L;
    /** Số luồng tải song song trong 1 symbol. */
    private static final int DOWNLOAD_THREADS = 8;
    /** Số lần liên tiếp thấy queue rỗng trước khi worker tự thoát (tránh thoát giữa lúc master còn đang bơm). */
    private static final int EMPTY_EXIT_CHECKS = 3;

    private final VisionMetricsClient vision = new VisionMetricsClient();
    /** TASK-013 backfill-lai: gioi han ngay-file [startMs,endMs] (env OI_START_DATE/OI_END_DATE yyyyMMdd UTC). */
    private final long startMs = parseEnvDate("OI_START_DATE", Long.MIN_VALUE);
    private final long endMs = parseEnvDate("OI_END_DATE", Long.MAX_VALUE);

    public static void main(String[] args) {
        Configs.IS_KAGGLE_MODE = true;
        new BackfillOiWorker().run();
    }

    private static long parseEnvDate(String env, long def) {
        String v = System.getenv(env);
        if (v == null || v.trim().isEmpty()) return def;
        try {
            java.text.SimpleDateFormat df = new java.text.SimpleDateFormat("yyyyMMdd");
            df.setTimeZone(java.util.TimeZone.getTimeZone("UTC"));
            return df.parse(v.trim()).getTime();
        } catch (Exception e) {
            LOG.warn("⚠️ {} khong parse duoc '{}' -> bo qua: {}", env, v, e.getMessage());
            return def;
        }
    }

    public void run() {
        LOG.info("👷 BACKFILL-OI WORKER khởi động | queue={} | done={} | threads={} | range=[{}..{}]",
                QUEUE_SET, DONE_SET, DOWNLOAD_THREADS,
                startMs == Long.MIN_VALUE ? "ALL" : startMs, endMs == Long.MAX_VALUE ? "ALL" : endMs);
        int emptyChecks = 0;
        while (true) {
            try {
                String symbol = fetchTask();
                if (symbol == null) {
                    // không cướp được task: queue rỗng thật sự?
                    if (queueIsEmpty()) {
                        emptyChecks++;
                        LOG.info("☕ Queue trống ({}/{}). Chờ xác nhận trước khi thoát...", emptyChecks, EMPTY_EXIT_CHECKS);
                        if (emptyChecks >= EMPTY_EXIT_CHECKS) {
                            LOG.info("✅ Queue rỗng ổn định → worker thoát (System.exit 0).");
                            System.exit(0);
                        }
                    } else {
                        emptyChecks = 0; // còn RUNNING của worker khác → chờ, đừng thoát
                        LOG.info("⏳ Queue còn task (RUNNING worker khác). Đi dạo 15s...");
                    }
                    Thread.sleep(15_000L);
                    continue;
                }
                emptyChecks = 0;
                processSymbol(symbol);
            } catch (Exception e) {
                LOG.error("❌ Lỗi worker loop: ", e);
                try {
                    Thread.sleep(5_000L);
                } catch (InterruptedException ignored) {
                    Thread.currentThread().interrupt();
                }
            }
        }
    }

    /** Tải + ghi 5 set cho 1 symbol, mark done, xoá queue. */
    private void processSymbol(String symbol) {
        long t1 = System.currentTimeMillis();
        Key queueKey = new Key(Configs.AEROSPIKE_NAMESPACE, QUEUE_SET, symbol);

        // Phòng race: symbol đã DONE (worker khác vừa xong) → chỉ dọn queue.
        if (isDone(symbol)) {
            safeDelete(queueKey);
            LOG.info("↩️ {} đã DONE từ trước → bỏ qua, dọn queue.", symbol);
            return;
        }

        LOG.info("🔨 Backfill {} ...", symbol);
        VisionMetricsClient.SymbolMetrics m;
        try {
            m = vision.fetchSymbol(symbol, DOWNLOAD_THREADS, startMs, endMs);
        } catch (Exception e) {
            // Lỗi tải/parse cả symbol: KHÔNG mark done, KHÔNG xoá queue → để task tự về PENDING (stale) cho lần sau.
            LOG.error("❌ {} tải/parse lỗi (giữ task trong queue để retry): {}", symbol, e.getMessage(), e);
            return;
        }

        int totalTs = VisionMetricsClient.totalTs(m);
        if (totalTs == 0) {
            LOG.warn("⚠️ {} không có dữ liệu metrics (0 record). Vẫn mark DONE để khỏi treo queue.", symbol);
            markDoneAndClear(symbol, queueKey, m, 0);
            return;
        }

        // Ghi 5 set lên 226 (chunk-tháng SYMBOL_yyyyMM, merge-guard chống mất lịch sử).
        int writeFails = 0;
        for (int i = 0; i < OiMetricSets.ALL.length; i++) {
            OiMetricSets.Metric metric = OiMetricSets.ALL[i];
            TreeMap<Long, Float> map = m.maps[i];
            if (map.isEmpty()) continue;
            writeFails += DataManagerAerospikeFloatSim.writeMetricMap226(metric.set, metric.bin, symbol, map);
        }
        if (writeFails > 0) {
            LOG.error("❌ {} có {} chunk-tháng GHI LỖI → KHÔNG mark DONE (giữ queue để retry).", symbol, writeFails);
            return;
        }

        // 🔎 SELF-VERIFY end-to-end CẢ 5 SET (không chỉ OI — vá lỗ hổng để sót LS/taker bị bắt ngay):
        // đọc lại từng set trên 226, đếm trong [startMs,endMs] phải ≥ kỳ vọng trước khi mark DONE.
        for (int i = 0; i < OiMetricSets.ALL.length; i++) {
            int expected = m.maps[i].size();
            if (expected == 0) continue;
            OiMetricSets.Metric mm = OiMetricSets.ALL[i];
            java.util.TreeMap<Long, Float> stored =
                    DataManagerAerospikeFloatSim.getMetricMap226(mm.set, mm.bin, symbol);
            int storedInRange = (startMs == Long.MIN_VALUE && endMs == Long.MAX_VALUE)
                    ? stored.size()
                    : stored.subMap(startMs, true, endMs, true).size();
            if (storedInRange < expected) {
                LOG.error("❌ {} SELF-VERIFY {} thất bại: stored(range)={} < kỳ vọng={} → KHÔNG mark DONE (retry).",
                        symbol, mm.set, storedInRange, expected);
                return;
            }
        }
        LOG.info("🔎 {} self-verify 5 set 226 (range) ✓", symbol);

        markDoneAndClear(symbol, queueKey, m, totalTs);
        LOG.info("✅ {} xong trong {}ms | filesOk={} filesEmpty={} rawRows={} | ts(OI)={} | ts-range[{}..{}]",
                symbol, System.currentTimeMillis() - t1, m.filesOk, m.filesEmpty, m.rawRows,
                m.maps[0].size(),
                m.maps[0].isEmpty() ? "-" : m.maps[0].firstKey(),
                m.maps[0].isEmpty() ? "-" : m.maps[0].lastKey());
    }

    /** Ghi record DONE (kèm vài counter để soát) rồi xoá khỏi queue (ghi DONE TRƯỚC, xoá SAU → không mất task). */
    private void markDoneAndClear(String symbol, Key queueKey, VisionMetricsClient.SymbolMetrics m, int totalTs) {
        WritePolicy wp = new WritePolicy();
        wp.sendKey = true;
        wp.expiration = 0;
        Key doneKey = new Key(Configs.AEROSPIKE_NAMESPACE, DONE_SET, symbol);
        try {
            DataManagerAerospikeFloatSim.getClient226().put(wp, doneKey,
                    new Bin("symbol", symbol),
                    new Bin("totalTs", totalTs),
                    new Bin("oiTs", m.maps[0].size()),
                    new Bin("filesOk", m.filesOk),
                    new Bin("rawRows", m.rawRows),
                    new Bin("finishedAt", System.currentTimeMillis()));
        } catch (Exception e) {
            LOG.error("❌ {} ghi DONE thất bại (giữ queue để retry): {}", symbol, e.getMessage(), e);
            return;
        }
        safeDelete(queueKey);
    }

    private boolean isDone(String symbol) {
        Key doneKey = new Key(Configs.AEROSPIKE_NAMESPACE, DONE_SET, symbol);
        Record r = DataManagerAerospikeFloatSim.getClient226().get(null, doneKey);
        return r != null;
    }

    /**
     * Scan QUEUE_SET, chiếm 1 task PENDING (hoặc RUNNING quá STALE) bằng optimistic lock (generation).
     * Trả symbol đã chiếm, hoặc null nếu không có gì grabbable.
     */
    private String fetchTask() {
        final String[] found = {null};
        try {
            DataManagerAerospikeFloatSim.getClient226().scanAll(null, Configs.AEROSPIKE_NAMESPACE, QUEUE_SET,
                    (key, record) -> {
                        if (found[0] != null) return;
                        String status = record.getString("status");
                        long startTime = record.getLong("startTime");
                        boolean grabbable = "PENDING".equals(status)
                                || ("RUNNING".equals(status) && (System.currentTimeMillis() - startTime) > STALE_RUNNING_MS);
                        if (!grabbable) return;

                        WritePolicy lockPolicy = new WritePolicy();
                        lockPolicy.sendKey = true;
                        lockPolicy.expiration = 0;
                        lockPolicy.generationPolicy = GenerationPolicy.EXPECT_GEN_EQUAL;
                        lockPolicy.generation = record.generation;
                        try {
                            DataManagerAerospikeFloatSim.getClient226().put(lockPolicy, key,
                                    new Bin("status", "RUNNING"),
                                    new Bin("startTime", System.currentTimeMillis()));
                            found[0] = record.getString("symbol");
                            if (found[0] == null) found[0] = key.userKey != null ? key.userKey.toString() : null;
                        } catch (com.aerospike.client.AerospikeException e) {
                            // Generation lệch: worker khác vừa chiếm → bỏ qua, scan tiếp.
                        }
                    }, "status", "startTime", "symbol");
        } catch (Exception e) {
            LOG.error("❌ Lỗi scan QUEUE (worker tưởng nhầm trống): ", e);
        }
        return found[0];
    }

    /** Queue thật sự rỗng (0 record)? */
    private boolean queueIsEmpty() {
        AtomicInteger c = new AtomicInteger();
        try {
            DataManagerAerospikeFloatSim.getClient226().scanAll(null, Configs.AEROSPIKE_NAMESPACE, QUEUE_SET,
                    (key, record) -> c.incrementAndGet(), "status");
        } catch (Exception e) {
            LOG.warn("⚠️ scan queue (check rỗng) lỗi → coi như KHÔNG rỗng: {}", e.getMessage());
            return false;
        }
        return c.get() == 0;
    }

    private void safeDelete(Key queueKey) {
        try {
            DataManagerAerospikeFloatSim.getClient226().delete(new WritePolicy(), queueKey);
        } catch (Exception e) {
            LOG.warn("⚠️ Không xoá được task khỏi queue {}: {}", queueKey, e.getMessage());
        }
    }
}
