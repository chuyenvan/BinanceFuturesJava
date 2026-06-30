package com.binance.chuyennd.ai_ml.wfo.framework;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.GenerationPolicy;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.BatchPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.aerospike.client.cdt.ListOperation;
import com.aerospike.client.cdt.ListOrder;
import com.aerospike.client.cdt.ListPolicy;
import com.aerospike.client.cdt.ListWriteFlags;
import com.aerospike.client.Value;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;

/**
 * WFO FRAMEWORK — STORE TRẠNG THÁI JOB trên Aerospike 226 (Uni chốt: state NHỎ + thay đổi NHIỀU → hợp
 * Aerospike; còn DATA lớn bất biến → file offline). Mọi node (Oracle/226/Kaggle) đọc-ghi qua 226.
 *
 * <p><b>Atomic claim (chống 2 worker giành 1 job):</b> dùng GenerationPolicy.EXPECT_GEN_EQUAL — đọc record
 * (kèm generation), CAS ghi với generation đã đọc; nếu worker khác ghi trước → generation đổi → ghi FAIL
 * → claim thất bại (worker này bỏ qua, thử job khác). Đây là tiền lệ GenerationPolicy đã dùng trong dự án.
 *
 * <p><b>Lease/TTL:</b> claim đặt leaseUntil = now + leaseMs. Worker heartbeat gia hạn định kỳ. Worker chết
 * → lease hết → job được coi là "stale", worker khác steal (CAS PENDING rồi claim lại). KHÔNG mất job.
 *
 * <p>Set Aerospike: {@code wfo_jobs}, namespace như project (ticker). 1 record / job, key = job.id.
 * Bins: type, state, payload, result, owner, lease(long), retry(int), maxRetry, created, updated, err.
 */
public class WfoJobStore {

    private static final Logger LOG = LoggerFactory.getLogger(WfoJobStore.class);
    public static final String SET = "wfo_jobs";
    /** Record chi muc giu danh sach job-id (thay scanAll — server 8 bo legacy scan, batch-get OK). */
    public static final String INDEX_KEY = "__job_index__";

    private final AerospikeClient client;
    private final String ns;

    public WfoJobStore() {
        String host = System.getenv("WFO_STATE_HOST");
        if (host != null && !host.isEmpty()) {
            // State-store RIENG cho WFO (vd Aerospike local tren Oracle) — tach khoi 226 (226 stop_writes do index-mem day)
            int port = Integer.parseInt(System.getenv().getOrDefault("WFO_STATE_PORT", "3000"));
            this.client = new AerospikeClient(host, port);
            this.ns = System.getenv().getOrDefault("WFO_STATE_NS", "test");
            LOG.info("WfoJobStore: state Aerospike RIENG {}:{} ns={}", host, port, ns);
        } else {
            this.client = DataManagerAerospikeFloatSim.getClient226();
            this.ns = Configs.AEROSPIKE_NAMESPACE;
            LOG.info("WfoJobStore: state Aerospike 226 ns={}", ns);
        }
    }

    private Key key(String id) { return new Key(ns, SET, id); }

    /** Them job-id vao record chi muc (ADD_UNIQUE + NO_FAIL: khong trung, khong loi neu da co). */
    private void addToIndex(String id) {
        try {
            client.operate(null, key(INDEX_KEY),
                    ListOperation.append(
                            new ListPolicy(ListOrder.UNORDERED, ListWriteFlags.ADD_UNIQUE | ListWriteFlags.NO_FAIL),
                            "ids", Value.get(id)));
        } catch (Exception e) {
            LOG.warn("addToIndex {} fail: {}", id, e.getMessage());
        }
    }

    // ---------- ghi mới (init) ----------
    /** Tạo/ghi đè job (dùng khi init danh sách job; CREATE_ONLY để không đè job đang chạy). */
    public void putNew(WfoJob j) {
        WritePolicy wp = new WritePolicy();
        wp.recordExistsAction = RecordExistsAction.CREATE_ONLY; // không đè nếu đã tồn tại
        try {
            client.put(wp, key(j.id), bins(j));
        } catch (com.aerospike.client.AerospikeException ae) {
            if (ae.getResultCode() == com.aerospike.client.ResultCode.KEY_EXISTS_ERROR) {
                LOG.debug("putNew skip (da ton tai) {}", j.id);   // idempotent init, dung
            } else {
                LOG.warn("putNew FAIL {} -> rc={} {}", j.id, ae.getResultCode(), ae.getMessage());
                throw ae;   // fail-fast: KHONG nuot loi ghi that
            }
        }
        addToIndex(j.id);
    }

    /** Ghi đè bắt buộc (reset). */
    public void putForce(WfoJob j) {
        WritePolicy wp = new WritePolicy();
        wp.recordExistsAction = RecordExistsAction.REPLACE;
        client.put(wp, key(j.id), bins(j));
        addToIndex(j.id);
    }

    private Bin[] bins(WfoJob j) {
        return new Bin[]{
                new Bin("type", j.type), new Bin("state", j.state.name()),
                new Bin("payload", j.payload), new Bin("result", j.result),
                new Bin("owner", j.owner), new Bin("lease", j.leaseUntil),
                new Bin("retry", j.retryCount), new Bin("maxRetry", j.maxRetry),
                new Bin("created", j.createdAt), new Bin("updated", j.updatedAt),
                new Bin("err", j.lastError == null ? "" : j.lastError),
                new Bin("id", j.id),
        };
    }

    private WfoJob fromRecord(String id, Record r) {
        if (r == null) return null;
        WfoJob j = new WfoJob();
        j.id = id;
        j.type = r.getString("type");
        j.state = WfoJob.State.valueOf(r.getString("state"));
        j.payload = nz(r.getString("payload"));
        j.result = nz(r.getString("result"));
        j.owner = nz(r.getString("owner"));
        j.leaseUntil = r.getLong("lease");
        j.retryCount = r.getInt("retry");
        j.maxRetry = r.getInt("maxRetry");
        j.createdAt = r.getLong("created");
        j.updatedAt = r.getLong("updated");
        j.lastError = nz(r.getString("err"));
        return j;
    }
    private static String nz(String s) { return s == null ? "" : s; }

    // ---------- đọc ----------
    public WfoJob get(String id) {
        Record r = client.get(null, key(id));
        return fromRecord(id, r);
    }

    public List<WfoJob> listAll() {
        List<WfoJob> out = new ArrayList<>();
        Record idx = client.get(null, key(INDEX_KEY));
        if (idx == null) return out;
        List<?> ids = idx.getList("ids");
        if (ids == null || ids.isEmpty()) return out;
        LinkedHashSet<String> uniq = new LinkedHashSet<>();
        for (Object o : ids) if (o != null) uniq.add(o.toString());
        if (uniq.isEmpty()) return out;
        Key[] keys = new Key[uniq.size()];
        int i = 0;
        for (String id : uniq) keys[i++] = key(id);
        Record[] recs = client.get(new BatchPolicy(), keys);   // batch-get thay scanAll (server 8 OK)
        i = 0;
        for (String id : uniq) {
            WfoJob j = fromRecord(id, recs[i++]);
            if (j != null) out.add(j);
        }
        return out;
    }

    // ---------- claim atomic (CAS theo generation) ----------
    /**
     * Thử claim 1 job đang PENDING (hoặc RUNNING đã hết lease = steal). Trả job nếu thắng CAS, null nếu thua.
     * @param id job cần claim, owner định danh worker, leaseMs thời hạn lease
     */
    public WfoJob tryClaim(String id, String owner, long leaseMs) {
        Record r = client.get(null, key(id));
        if (r == null) return null;
        WfoJob j = fromRecord(id, r);
        long now = System.currentTimeMillis();
        boolean claimable = (j.state == WfoJob.State.PENDING) || j.leaseExpired(now);
        if (!claimable) return null;

        // CAS: chỉ ghi nếu generation chưa đổi kể từ lúc đọc
        WritePolicy wp = new WritePolicy();
        wp.generationPolicy = GenerationPolicy.EXPECT_GEN_EQUAL;
        wp.generation = r.generation;
        boolean wasSteal = j.leaseExpired(now) && j.state == WfoJob.State.RUNNING;
        j.state = WfoJob.State.RUNNING;
        j.owner = owner;
        j.leaseUntil = now + leaseMs;
        j.updatedAt = now;
        if (wasSteal) {
            j.retryCount += 1; // steal tính như 1 lần thử lại
            j.lastError = "stolen (lease expired from " + j.owner + ")";
        }
        try {
            client.put(wp, key(id), bins(j));
            if (wasSteal) LOG.info("STEAL job {} (lease het) -> owner {}", id, owner);
            return j;
        } catch (Exception e) {
            return null; // generation đổi → worker khác thắng
        }
    }

    /** Gia hạn lease (heartbeat). CAS theo owner: chỉ owner hiện tại mới gia hạn được. */
    public boolean heartbeat(String id, String owner, long leaseMs) {
        Record r = client.get(null, key(id));
        if (r == null) return false;
        WfoJob j = fromRecord(id, r);
        if (j.state != WfoJob.State.RUNNING || !owner.equals(j.owner)) return false;
        WritePolicy wp = new WritePolicy();
        wp.generationPolicy = GenerationPolicy.EXPECT_GEN_EQUAL;
        wp.generation = r.generation;
        j.leaseUntil = System.currentTimeMillis() + leaseMs;
        j.updatedAt = System.currentTimeMillis();
        try { client.put(wp, key(id), bins(j)); return true; }
        catch (Exception e) { return false; }
    }

    /** Báo DONE + ghi result. CAS theo owner. */
    public boolean reportDone(String id, String owner, String resultJson) {
        return finish(id, owner, WfoJob.State.DONE, resultJson, "");
    }

    /** Báo FAIL. Nếu retry < maxRetry → về PENDING (chạy lại); else FAILED (chờ người). */
    public void reportFail(String id, String owner, String error) {
        Record r = client.get(null, key(id));
        if (r == null) return;
        WfoJob j = fromRecord(id, r);
        if (!owner.equals(j.owner)) return; // không phải owner thì thôi
        WritePolicy wp = new WritePolicy();
        wp.generationPolicy = GenerationPolicy.EXPECT_GEN_EQUAL;
        wp.generation = r.generation;
        j.retryCount += 1;
        j.lastError = error == null ? "" : (error.length() > 500 ? error.substring(0, 500) : error);
        j.owner = "";
        j.leaseUntil = 0;
        j.updatedAt = System.currentTimeMillis();
        j.state = (j.retryCount > j.maxRetry) ? WfoJob.State.FAILED : WfoJob.State.PENDING;
        try { client.put(wp, key(id), bins(j)); } catch (Exception ignore) {}
    }

    private boolean finish(String id, String owner, WfoJob.State st, String result, String err) {
        Record r = client.get(null, key(id));
        if (r == null) return false;
        WfoJob j = fromRecord(id, r);
        if (!owner.equals(j.owner)) return false;
        WritePolicy wp = new WritePolicy();
        wp.generationPolicy = GenerationPolicy.EXPECT_GEN_EQUAL;
        wp.generation = r.generation;
        j.state = st;
        j.result = result == null ? "" : result;
        j.lastError = err == null ? "" : err;
        j.owner = "";
        j.leaseUntil = 0;
        j.updatedAt = System.currentTimeMillis();
        try { client.put(wp, key(id), bins(j)); return true; }
        catch (Exception e) { return false; }
    }
}
