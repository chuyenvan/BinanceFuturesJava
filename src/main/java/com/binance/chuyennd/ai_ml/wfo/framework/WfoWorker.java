package com.binance.chuyennd.ai_ml.wfo.framework;

import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.management.ManagementFactory;
import java.net.InetAddress;
import java.util.List;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/**
 * WFO FRAMEWORK — WORKER chung (entrypoint chạy MỌI node trừ 242). Vòng đời:
 * <pre>
 * load dataset offline 1 lần → loop:
 *   tìm job claim được (PENDING / RUNNING-hết-lease) → claim CAS
 *   → heartbeat nền (gia hạn lease) → chạy task.runJob → reportDone | reportFail
 *   hết job claimable → nghỉ rồi quét lại; quá maxIdle vòng rỗng → thoát.
 * </pre>
 *
 * <p>Mọi node coi NHƯ NHAU (Uni chốt) — chỉ khác nguồn dataset (env WFO_DATA_DIR: VPS file tĩnh /
 * Kaggle Dataset). Cân tải tự nhiên: node rảnh tự giành job kế. Worker chết → lease hết → job về
 * PENDING, node khác steal.
 *
 * <p>Env: WFO_DATA_DIR (bắt buộc cho phân tán; thiếu → fallback Aerospike, chỉ test đơn máy).
 *        WFO_LEASE_MIN (mặc định 30), WFO_MAX_IDLE_LOOPS (mặc định 3). Cluster đọc theo config AEROSPIKE_READ_CLUSTER (TASK-112).
 *        WFO_N_SAMPLES (truyền xuống task qua buildJobs — chỉ coordinator dùng).
 * Arg: [type=strategy_window]
 */
public class WfoWorker {

    private static final Logger LOG = LoggerFactory.getLogger(WfoWorker.class);

    public static void main(String[] args) {
        try {
            // TASK (2026-07-11): mac dinh A, cho phep env ABLATION_MODE override de test gate-off (B).
            // WFO_SMART_CACHE=1 → bật cache nén kline RAM (HPOSmartCache.getDataShort) trong simulator.
            // Cluster đọc theo config box AEROSPIKE_READ_CLUSTER=226 (Oracle: AEROSPIKE_HOST_ORACLE=127.0.0.1 local).
            if ("1".equals(System.getenv("WFO_SMART_CACHE"))) Configs.USE_SMART_CACHE = true;
            // WFO_STATIC_RANK=1 → CoinRank đọc tier TĨNH từ file (env WFO_COINTIER_FILE), backtest KHÔNG bật
            // HistoryManager. Nạp 1 lần vào singleton trước khi chạy job.
            if ("1".equals(System.getenv("WFO_STATIC_RANK"))) {
                Configs.WFO_STATIC_RANK = true;
                String tierFile = System.getenv("WFO_COINTIER_FILE");
                if (tierFile == null || tierFile.isBlank()) {
                    throw new IllegalStateException("WFO_STATIC_RANK=1 nhưng thiếu WFO_COINTIER_FILE");
                }
                com.binance.chuyennd.tradecore.CoinRankManager.getInstance()
                        .loadStaticTier(ExportCoinTierStatic.load(tierFile));
            }
            String type = args.length > 0 ? args[0] : "strategy_window";
            new WfoWorker().run(type);
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("WfoWorker FAIL", e);
            System.exit(1);
        }
    }

    private long leaseMs;
    private int maxIdleLoops;

    void run(String type) throws Exception {
        leaseMs = envLong("WFO_LEASE_MIN", 30) * 60_000L;
        maxIdleLoops = (int) envLong("WFO_MAX_IDLE_LOOPS", 3);
        String workerId = workerId();
        LOG.info("WfoWorker start: type={} workerId={} leaseMin={} maxIdleLoops={}",
                type, workerId, leaseMs / 60000, maxIdleLoops);

        WfoTask task = WfoTaskRegistry.get(type);
        WfoJobStore store = new WfoJobStore();

        // load dataset offline 1 LẦN (tái dùng mọi job)
        WfoDataset ds = WfoDataset.loadAuto();
        WfoContext ctx = new WfoContext(ds, workerId);

        ScheduledExecutorService hb = new ScheduledThreadPoolExecutor(1);
        int idleLoops = 0;
        int doneCount = 0;
        while (true) {
            WfoJob claimed = findAndClaim(store, task.type(), workerId);
            if (claimed == null) {
                idleLoops++;
                if (idleLoops >= maxIdleLoops) {
                    LOG.info("Khong con job claimable sau {} vong rong -> worker thoat. (done {} job)", idleLoops, doneCount);
                    break;
                }
                LOG.info("Khong co job claimable, nghi 10s (idle {}/{})", idleLoops, maxIdleLoops);
                Thread.sleep(10_000);
                continue;
            }
            idleLoops = 0;
            final String jobId = claimed.id;
            // heartbeat nền: gia hạn lease mỗi 1/3 lease
            java.util.concurrent.ScheduledFuture<?> hbTask = hb.scheduleAtFixedRate(() -> {
                try { store.heartbeat(jobId, workerId, leaseMs); }
                catch (Exception e) { LOG.warn("heartbeat loi {}: {}", jobId, e.getMessage()); }
            }, leaseMs / 3, leaseMs / 3, TimeUnit.MILLISECONDS);

            try {
                LOG.info("RUN job {} ...", jobId);
                long t0 = System.currentTimeMillis();
                String result = task.runJob(claimed, ctx);
                hbTask.cancel(false);
                boolean ok = store.reportDone(jobId, workerId, result);
                long sec = (System.currentTimeMillis() - t0) / 1000;
                if (ok) { doneCount++; LOG.info("DONE job {} ({}s)", jobId, sec); }
                else LOG.warn("job {} chay xong nhung reportDone FAIL (mat lease?) -> se duoc lam lai", jobId);
            } catch (Throwable e) {
                hbTask.cancel(false);
                LOG.error("job {} FAIL: {}", jobId, e.toString());
                store.reportFail(jobId, workerId, e.toString());
            }
        }
        hb.shutdownNow();
    }

    /** Quét toàn bộ job cùng type, thử claim job đầu tiên claimable (PENDING hoặc RUNNING hết lease). */
    private WfoJob findAndClaim(WfoJobStore store, String type, String workerId) {
        List<WfoJob> all = store.listAll();
        long now = System.currentTimeMillis();
        // ưu tiên PENDING trước, rồi mới tới stale (steal)
        for (WfoJob j : all) {
            if (!type.equals(j.type)) continue;
            if (j.state == WfoJob.State.PENDING) {
                WfoJob c = store.tryClaim(j.id, workerId, leaseMs);
                if (c != null) return c;
            }
        }
        for (WfoJob j : all) {
            if (!type.equals(j.type)) continue;
            if (j.leaseExpired(now)) {
                WfoJob c = store.tryClaim(j.id, workerId, leaseMs);
                if (c != null) return c;
            }
        }
        return null;
    }

    private static String workerId() {
        String host;
        try { host = InetAddress.getLocalHost().getHostName(); }
        catch (Exception e) { host = "unknown"; }
        String pid = ManagementFactory.getRuntimeMXBean().getName();
        return host + "/" + pid;
    }
    private static long envLong(String k, long def) {
        String v = System.getenv(k);
        if (v == null || v.isEmpty()) return def;
        try { return Long.parseLong(v.trim()); } catch (Exception e) { return def; }
    }
}
