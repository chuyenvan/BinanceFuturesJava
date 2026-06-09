package com.binance.chuyennd.ai_ml.onnx.funding;

import com.aerospike.client.*;
import com.aerospike.client.policy.GenerationPolicy;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.ScanPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

/**
 * Điều phối task gen funding theo THÁNG, có TRẠNG THÁI (không còn xóa-khi-claim).
 *
 * VÌ SAO ĐỔI: cơ chế cũ claim = ATOMIC DELETE → claim xong task biến mất, worker chết giữa chừng là
 * MẤT task vĩnh viễn, và không biết tháng nào đã xong. Nay mỗi task có bin:
 *   status   : PENDING | RUNNING | DONE   (thiếu bin => coi như PENDING — tương thích queue v2 cũ)
 *   worker   : id worker đang giữ
 *   claim_ts : mốc claim (ms)             -> RUNNING quá STALE_MS (3h) coi như CHẾT, cho claim lại
 *   done_ts  : mốc hoàn tất
 *
 * Claim = CAS theo generation (EXPECT_GEN_EQUAL): 2 worker cùng nhắm 1 task thì chỉ 1 ghi được RUNNING,
 * thằng kia gen mismatch -> thử task khác. Worker xong gọi markDone(); lỗi-bắt-được gọi releaseTask()
 * (về PENDING retry ngay); worker CHẾT cứng thì task RUNNING sẽ stale sau 3h và được nhặt lại.
 */
public class AerospikeTaskCoordinator {
    private static final Logger LOG = LoggerFactory.getLogger(AerospikeTaskCoordinator.class);

    private static final String TASK_SET_NAME = "funding_tasks_monthly_v2";

    private static final String B_START = "start", B_END = "end", B_STATUS = "status",
            B_WORKER = "worker", B_CLAIM = "claim_ts", B_DONE = "done_ts";
    private static final String ST_PENDING = "PENDING", ST_RUNNING = "RUNNING", ST_DONE = "DONE";

    // RUNNING quá ngưỡng này coi như worker chết -> cho claim lại. (1 task tháng ~2-3h; nới nếu cần.)
    private static final long STALE_MS = 3 * 60 * 60 * 1000L;

    private static final String WORKER_ID = buildWorkerId();

    private static String buildWorkerId() {
        String host;
        try { host = java.net.InetAddress.getLocalHost().getHostName(); }
        catch (Exception e) { host = "host"; }
        return host + "-" + Long.toHexString(System.nanoTime() & 0xFFFFFFL);
    }

    private static AerospikeClient client() { return DataManagerAerospikeFloatSim.getClient226(); }

    // =========================================================================
    // WORKER API: claim / done / release
    // =========================================================================

    /**
     * Nhận 1 task: scan các task CLAIM ĐƯỢC (PENDING/legacy, hoặc RUNNING đã stale >3h), giành quyền
     * bằng CAS generation (đánh dấu RUNNING). Trả null nếu không còn task nào claim được.
     */
    public static TaskRange claimNextTask() {
        AerospikeClient client = client();
        ScanPolicy policy = new ScanPolicy();
        policy.concurrentNodes = true;   // KHÔNG giới hạn maxRecords: task không bị xóa nữa nên set luôn đầy

        long now = System.currentTimeMillis();
        final List<TaskRange> pending = new ArrayList<>();
        final List<TaskRange> stale = new ArrayList<>();

        try {
            client.scanAll(policy, Configs.AEROSPIKE_NAMESPACE, TASK_SET_NAME, (key, rec) -> {
                String st = rec.getString(B_STATUS);
                if (st == null) st = ST_PENDING;                 // legacy record (chỉ có start/end)
                if (ST_DONE.equals(st)) return;                  // xong rồi, bỏ qua
                TaskRange t = new TaskRange(key, rec.getLong(B_START), rec.getLong(B_END), rec.generation);
                if (ST_RUNNING.equals(st)) {
                    if (now - rec.getLong(B_CLAIM) > STALE_MS) stale.add(t);   // chết >3h -> nhặt lại
                } else {
                    pending.add(t);
                }
            }, B_START, B_END, B_STATUS, B_CLAIM);
        } catch (AerospikeException e) {
            LOG.warn("⚠️ scan task lỗi: {}", e.getMessage());
        }

        Collections.shuffle(pending);                                   // giảm tranh chấp giữa worker
        stale.sort(Comparator.comparingLong(t -> t.start));             // reclaim cái cũ trước
        List<TaskRange> order = new ArrayList<>(pending);
        order.addAll(stale);

        for (TaskRange t : order) {
            if (tryClaim(client, t, now)) return t;                     // gen mismatch -> thử task khác
        }
        return null;
    }

    /** Giành quyền bằng CAS: chỉ ghi RUNNING nếu generation chưa đổi (không ai claim chen vào). */
    private static boolean tryClaim(AerospikeClient client, TaskRange t, long now) {
        WritePolicy wp = new WritePolicy();
        wp.generationPolicy = GenerationPolicy.EXPECT_GEN_EQUAL;
        wp.generation = t.generation;
        wp.recordExistsAction = RecordExistsAction.UPDATE;
        try {
            client.put(wp, t.key,
                    new Bin(B_STATUS, ST_RUNNING),
                    new Bin(B_WORKER, WORKER_ID),
                    new Bin(B_CLAIM, now));
            LOG.info("🎯 Claimed {} (worker={}) {} -> {}", t.key.userKey, WORKER_ID,
                    Utils.normalizeDateYYYYMMDD(t.start), Utils.normalizeDateYYYYMMDD(t.end));
            return true;
        } catch (AerospikeException e) {
            return false;   // generation đổi (worker khác giành mất) hoặc lỗi tạm -> bỏ qua task này
        }
    }

    /** Worker gọi khi đã gen XONG task: đánh dấu DONE (sẽ không bị claim lại). */
    public static void markDone(TaskRange task) {
        try {
            client().put(null, task.key,
                    new Bin(B_STATUS, ST_DONE),
                    new Bin(B_DONE, System.currentTimeMillis()));
            LOG.info("✅ DONE {} (worker={})", task.key.userKey, WORKER_ID);
        } catch (Exception e) {
            LOG.error("❌ markDone lỗi {} — task có thể bị nhặt lại sau 3h: {}", task.key.userKey, e.getMessage());
        }
    }

    /** Worker gọi khi task LỖI (bắt được): trả về PENDING để retry NGAY (không phải chờ 3h stale). */
    public static void releaseTask(TaskRange task) {
        try {
            client().put(null, task.key, new Bin(B_STATUS, ST_PENDING), new Bin(B_CLAIM, 0L));
            LOG.warn("↩️ Release {} về PENDING (lỗi/retry).", task.key.userKey);
        } catch (Exception e) {
            LOG.error("❌ releaseTask lỗi {}: {}", task.key.userKey, e.getMessage());
        }
    }

    /** In trạng thái toàn bộ queue: đếm PENDING/RUNNING/DONE, liệt kê RUNNING (active + stale>3h). */
    public static void checkStatus() {
        AerospikeClient client = client();
        ScanPolicy policy = new ScanPolicy();
        policy.concurrentNodes = true;
        long now = System.currentTimeMillis();
        final int[] cnt = new int[3];   // [0]=pending [1]=running [2]=done
        final int[] staleCnt = {0};
        final List<String> staleList = new ArrayList<>();
        final List<String> activeList = new ArrayList<>();

        try {
            client.scanAll(policy, Configs.AEROSPIKE_NAMESPACE, TASK_SET_NAME, (key, rec) -> {
                String st = rec.getString(B_STATUS);
                if (st == null) st = ST_PENDING;
                if (ST_DONE.equals(st)) {
                    cnt[2]++;
                } else if (ST_RUNNING.equals(st)) {
                    cnt[1]++;
                    long ageMin = (now - rec.getLong(B_CLAIM)) / 60000;
                    String w = rec.getString(B_WORKER);
                    String entry = key.userKey + "(" + w + "," + ageMin + "m)";
                    if (now - rec.getLong(B_CLAIM) > STALE_MS) { staleCnt[0]++; staleList.add(entry); }
                    else activeList.add(entry);
                } else {
                    cnt[0]++;
                }
            });
        } catch (AerospikeException e) {
            LOG.error("❌ checkStatus scan lỗi: {}", e.getMessage());
            return;
        }

        int total = cnt[0] + cnt[1] + cnt[2];
        LOG.info("📊 TASK STATUS [{}]: PENDING={} | RUNNING={} (trong đó stale>3h={}) | DONE={} | TỔNG={}",
                TASK_SET_NAME, cnt[0], cnt[1], staleCnt[0], cnt[2], total);
        if (!activeList.isEmpty()) LOG.info("▶️ Đang chạy: {}", activeList);
        if (!staleList.isEmpty()) LOG.warn("⏳ RUNNING quá 3h (sẽ bị nhặt lại): {}", staleList);
        if (cnt[0] == 0 && cnt[1] == 0 && total > 0) LOG.info("🏁 TẤT CẢ {} task ĐÃ DONE.", total);
    }

    // =========================================================================
    // ADMIN API: init / requeue
    // =========================================================================

    /** KHỞI TẠO queue theo THÁNG (chạy 1 lần ở admin). Mỗi task status=PENDING. */
    public static void initTasks(long startTime, long endTime) {
        LOG.info("🛠 Init Task Queue (MONTHLY) set '{}'...", TASK_SET_NAME);
        AerospikeClient client = client();
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startTime);
        int count = 0;
        while (cal.getTimeInMillis() < endTime) {
            long chunkStart = cal.getTimeInMillis();
            cal.add(Calendar.MONTH, 1);
            long chunkEnd = Math.min(cal.getTimeInMillis(), endTime);
            String keyString = "TASK_" + Utils.normalizeDateYYYYMMDD(chunkStart);
            writePending(client, keyString, chunkStart, chunkEnd);
            count++;
        }
        LOG.info("✅ Created {} task PENDING trong set '{}'", count, TASK_SET_NAME);
    }

    /** RE-QUEUE 1 task (về PENDING). resumeFromStr null = cả tháng; hoặc "yyyyMMdd" để chạy tiếp từ giữa. */
    public static void requeueTask(String monthStartStr, String resumeFromStr) {
        try {
            long monthStart = Utils.sdfFile.parse(monthStartStr).getTime();
            Calendar cal = Calendar.getInstance();
            cal.setTimeInMillis(monthStart);
            cal.add(Calendar.MONTH, 1);
            long chunkEnd = cal.getTimeInMillis();

            long chunkStart = monthStart;
            if (resumeFromStr != null) {
                long resume = Utils.sdfFile.parse(resumeFromStr).getTime();
                if (resume > monthStart && resume < chunkEnd) chunkStart = resume;
                else LOG.warn("⚠️ resumeFrom {} ngoài tháng {} -> chạy lại cả tháng.", resumeFromStr, monthStartStr);
            }
            writePending(client(), "TASK_" + monthStartStr, chunkStart, chunkEnd);
            LOG.info("✅ Re-queued PENDING {}: {} -> {}", monthStartStr,
                    Utils.normalizeDateYYYYMMDDHHmm(chunkStart), Utils.normalizeDateYYYYMMDDHHmm(chunkEnd));
        } catch (ParseException e) {
            LOG.error("❌ Sai định dạng ngày (yyyyMMdd): {} / {}", monthStartStr, resumeFromStr);
        }
    }

    /** Re-init nhiều task cụ thể (về PENDING). */
    public static void reInitSpecificTasks(List<String> specificDates) {
        LOG.info("🛠 Re-init {} task cụ thể (PENDING)...", specificDates.size());
        AerospikeClient client = client();   // 226 — CÙNG cluster với queue (sửa: trước nhầm 242)
        for (String dateStr : specificDates) {
            try {
                long chunkStart = Utils.sdfFile.parse(dateStr).getTime();
                Calendar cal = Calendar.getInstance();
                cal.setTimeInMillis(chunkStart);
                cal.add(Calendar.MONTH, 1);
                writePending(client, "TASK_" + dateStr, chunkStart, cal.getTimeInMillis());
                LOG.info("✅ Re-queued PENDING: TASK_{}", dateStr);
            } catch (ParseException e) {
                LOG.error("❌ Invalid date format: {}", dateStr);
            }
        }
    }

    /** Ghi 1 task ở trạng thái PENDING (reset claim_ts). */
    private static void writePending(AerospikeClient client, String keyString, long start, long end) {
        Key key = new Key(Configs.AEROSPIKE_NAMESPACE, TASK_SET_NAME, keyString);
        client.put(null, key,
                new Bin(B_START, start),
                new Bin(B_END, end),
                new Bin(B_STATUS, ST_PENDING),
                new Bin(B_CLAIM, 0L));
    }

    public static class TaskRange {
        public Key key;
        public long start;
        public long end;
        public int generation;   // dùng cho CAS claim

        public TaskRange(Key key, long start, long end, int generation) {
            this.key = key;
            this.start = start;
            this.end = end;
            this.generation = generation;
        }
    }

    public static void main(String[] args) throws ParseException {
        // CLI: "status" => in trạng thái; mặc định => init lại queue 2021->nay.
//        long globalStart = Utils.sdfFile.parse("20210101").getTime();
//        long globalEnd = System.currentTimeMillis();
//        initTasks(globalStart, globalEnd);
        checkStatus();
    }
}
