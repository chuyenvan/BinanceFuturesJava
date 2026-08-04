package com.binance.chuyennd.ai_ml.validation.data;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.ScanPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

/**
 * TASK-034 — Replicate set Aerospike **242 → 226** theo setname (ĐỌC-ONLY 242, GHI 226). Hai mục đích:
 * (1) đưa market data 242 sang 226 cho train/backtest (Kaggle/dev chỉ tới 226); (2) BACKUP set chỉ-sống-242
 * (242 repl-factor=1 → mất ổ = mất data).
 *
 * <p><b>Cách dùng:</b> {@code java ... ReplicateSet242To226 <set1> [set2] ...} (vd
 * {@code open_interest price_realtime funding_data}). Không tham số → in hướng dẫn + danh sách gợi ý, KHÔNG làm gì.
 *
 * <p><b>An toàn:</b> chỉ {@code scanAll} (đọc) trên 242, chỉ {@code put} trên 226 — TUYỆT ĐỐI không ghi/xoá 242.
 * Idempotent: ghi 226 theo CHÍNH digest+key+bin của record 242 ({@code RecordExistsAction.UPDATE}) → chạy lại
 * không nhân đôi, record nguyên vẹn (per-symbol map ghi đè = tự cập nhật điểm mới). Set lớn {@code kline_1m_opt}
 * (22GB) BỊ CHẶN trừ khi truyền cờ {@code --allow-large} (tránh copy nhầm 22GB; incremental cho set này là
 * việc riêng — xem task). Verify: đếm #record 226 sau copy + so 242.
 */
public class ReplicateSet242To226 {
    private static final Logger LOG = LoggerFactory.getLogger(ReplicateSet242To226.class);
    private static final String NS = Configs.AEROSPIKE_NAMESPACE;
    private static final String LARGE_GUARD = "kline_1m_opt";

    public static void main(String[] args) {
        List<String> sets = new ArrayList<>();
        boolean allowLarge = false;
        for (String a : args) {
            if ("--allow-large".equals(a)) allowLarge = true;
            else if (!a.startsWith("--")) sets.add(a);
        }
        if (sets.isEmpty()) {
            LOG.info("Cách dùng: ReplicateSet242To226 <set1> [set2] ... [--allow-large]");
            LOG.info("Gợi ý backup chỉ-242 (nhẹ): open_interest price_realtime funding_data");
            LOG.info("(KHÔNG truyền set → không làm gì. ĐỌC-ONLY 242, GHI 226.)");
            System.exit(0);
        }

        AerospikeClient src = DataManagerAerospikeFloatSim.getClient242(); // ĐỌC-ONLY
        AerospikeClient dst = DataManagerAerospikeFloatSim.getClientOracle(); // GHI
        LOG.info("🔁 REPLICATE 242→226 | sets={} | allowLarge={}", sets, allowLarge);

        for (String set : sets) {
            if (LARGE_GUARD.equals(set) && !allowLarge) {
                LOG.warn("⛔ BỎ QUA '{}' (set lớn ~22GB) — cần cờ --allow-large nếu CỐ Ý copy toàn bộ. " +
                        "Incremental cho set này là việc riêng (TASK-034 ghi chú).", set);
                continue;
            }
            replicateOne(src, dst, set);
        }
        LOG.info("✅ REPLICATE xong.");
        System.exit(0);
    }

    private static void replicateOne(AerospikeClient src, AerospikeClient dst, String set) {
        long t0 = System.currentTimeMillis();
        AtomicLong copied = new AtomicLong(), skippedNoBin = new AtomicLong(), errors = new AtomicLong();
        // 2 policy: record có userKey (vd funding/OI key=symbol) → sendKey=true giữ userKey; record KHÔNG
        // có userKey (vd price_realtime ghi digest-only) → sendKey=false (sendKey=true + userKey null = NPE).
        // Cả hai ghi THEO digest gốc nên record vẫn nằm đúng chỗ, trung thực với nguồn.
        WritePolicy wpKey = new WritePolicy();
        wpKey.expiration = 0; wpKey.sendKey = true; wpKey.recordExistsAction = RecordExistsAction.UPDATE;
        WritePolicy wpNoKey = new WritePolicy();
        wpNoKey.expiration = 0; wpNoKey.sendKey = false; wpNoKey.recordExistsAction = RecordExistsAction.UPDATE;

        ScanPolicy sp = new ScanPolicy();
        sp.includeBinData = true;
        try {
            src.scanAll(sp, NS, set, (key, record) -> {
                try {
                    if (record == null || record.bins == null || record.bins.isEmpty()) {
                        skippedNoBin.incrementAndGet();
                        return;
                    }
                    Bin[] bins = new Bin[record.bins.size()];
                    int i = 0;
                    for (Map.Entry<String, Object> e : record.bins.entrySet()) {
                        bins[i++] = new Bin(e.getKey(), e.getValue());
                    }
                    // Ghi 226 GIỮ NGUYÊN digest + setName + userKey của record gốc 242 (idempotent theo key).
                    Key dstKey = new Key(key.namespace, key.digest, key.setName, key.userKey);
                    dst.put(key.userKey != null ? wpKey : wpNoKey, dstKey, bins);
                    long n = copied.incrementAndGet();
                    if (n % 50_000 == 0) LOG.info("   {} … {} record copied", set, n);
                } catch (Exception ex) {
                    errors.incrementAndGet();
                    LOG.warn("⚠️ {} copy 1 record lỗi (userKey={}): {}", set,
                            key.userKey == null ? "?" : key.userKey, ex.getMessage());
                }
            });
        } catch (Exception e) {
            LOG.error("❌ scanAll 242 set {} lỗi: {}", set, e.getMessage(), e);
            return;
        }

        long dst226 = countSet(dst, set);
        LOG.info("💾 {}: copied={} · skip(no-bin)={} · errors={} · 226-now #record={} · {}ms",
                set, copied.get(), skippedNoBin.get(), errors.get(), dst226, System.currentTimeMillis() - t0);
    }

    private static long countSet(AerospikeClient client, String set) {
        AtomicLong c = new AtomicLong();
        ScanPolicy sp = new ScanPolicy();
        sp.includeBinData = false;
        try {
            client.scanAll(sp, NS, set, (key, record) -> c.incrementAndGet());
        } catch (Exception e) {
            LOG.warn("countSet {} lỗi: {}", set, e.getMessage());
            return -1;
        }
        return c.get();
    }
}
