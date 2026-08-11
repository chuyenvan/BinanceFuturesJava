package com.binance.chuyennd.aerospike.tools;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.ScanPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.atomic.AtomicLong;

/**
 * COPY các set PHỤ TRỢ từ 242 (live, khóa firewall) -> 226 (public cho Kaggle/HPO). Bổ trợ
 * CopyTicker242To226 — đây là 2 set CÒN LẠI mà đường Kaggle/HPO đọc từ 242:
 *   - funding_data : funding fee, key=symbol, bin "f_data" (Snappy) / "f_map" (legacy CDT).
 *                    Cần cho GenerateFundingPredictionsTool (FundingFeatureExtractorV2).
 *   - symbol_mapper: 1 record key=global_id_map, bin CDT map String->Long. Cần cho MỌI chạy.
 *
 * THIẾT KẾ: chép NGUYÊN bins (byte[]/CDT map) — không parse => bản sao giống hệt. sendKey=true để 226
 * giữ userKey (getAllFundingMap scan 226 đọc key.userKey=symbol). funding_data IDEMPOTENT (skip key đã
 * có; FORCE_OVERWRITE=true để làm tươi vì funding fee tăng theo ngày). symbol_mapper LUÔN ghi đè (1
 * record, lấy bản mới nhất). VERIFY: đếm + so bytes mẫu.
 *
 * CHẠY TRÊN 226 (whitelist 242 + ghi local). READ-ONLY với 242.
 */
public class CopyAuxSets242To226 {

    private static final Logger LOG = LoggerFactory.getLogger(CopyAuxSets242To226.class);

    private static final boolean FORCE_OVERWRITE = false;  // true = chép đè funding_data đã có (làm tươi)
    private static final int VERIFY_SAMPLES = 50;

    private static final String NS = Configs.AEROSPIKE_NAMESPACE;          // Oracle/226 (đích)
    // [TASK-251, 2026-08-05] 242 (nguồn, đọc-only) dùng namespace THẬT "ticker" (đo trực tiếp),
    // KHÁC NS ở trên (Oracle="test"). Trước đây dùng CHUNG NS cho cả đọc-242 và đọc/ghi-Oracle
    // => mọi src.get()/src.scanAll() luôn fail AerospikeException$InvalidNamespace. Chỉ dùng
    // NS_242 khi gọi trên client `src`; dst (Oracle) vẫn dùng NS như cũ, KHÔNG đổi.
    private static final String NS_242 = Configs.AEROSPIKE_NAMESPACE_242;
    private static final String SET_FUNDINGFEE = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_FUNDINGFEE; // funding_data
    private static final String SET_MAPPER = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_MAPPER;         // symbol_mapper
    private static final String MAPPER_KEY = DataManagerAerospikeFloatSim.MAPPER_KEY_GLOBAL;                 // global_id_map

    private final WritePolicy writePolicy = new WritePolicy();
    private final AtomicLong copied = new AtomicLong();
    private final AtomicLong skipped = new AtomicLong();
    private final AtomicLong noKey = new AtomicLong();
    private final List<String> sampleSymbols = Collections.synchronizedList(new ArrayList<>());
    private final Random rnd = new Random(42);

    public CopyAuxSets242To226() {
        writePolicy.sendKey = true;          // 226 giữ userKey để scan theo symbol
        writePolicy.expiration = 0;          // vĩnh viễn, giống gốc
        writePolicy.recordExistsAction = RecordExistsAction.UPDATE;
    }

    public static void main(String[] args) {
        try { new CopyAuxSets242To226().run(); }
        catch (Exception e) { LOG.error("CopyAuxSets error", e); }
        System.exit(0);
    }

    public void run() {
        AerospikeClient src = DataManagerAerospikeFloatSim.getClient242();
        AerospikeClient dst = DataManagerAerospikeFloatSim.getClientOracle();

        LOG.info("🚚 COPY AUX 242 -> 226 | sets: {} (idempotent, force={}) + {} (overwrite) | namespace={}",
                SET_FUNDINGFEE, FORCE_OVERWRITE, SET_MAPPER, NS);

        copyMapper(src, dst);
        copyFundingData(src, dst);
        verify(src, dst);
    }

    /** symbol_mapper: 1 record (key cố định global_id_map) — đọc thẳng, ghi đè 226 lấy bản mới nhất. */
    private void copyMapper(AerospikeClient src, AerospikeClient dst) {
        try {
            Key k = new Key(NS_242, SET_MAPPER, MAPPER_KEY);
            Record rec = src.get(null, k);
            if (rec == null || rec.bins == null || rec.bins.isEmpty()) {
                LOG.error("⛔ symbol_mapper trên 242 RỖNG/không có — DỪNG (mọi job cần mapper). Kiểm tra 242.");
                return;
            }
            dst.put(writePolicy, new Key(NS, SET_MAPPER, MAPPER_KEY), binsOf(rec));
            LOG.info("✅ symbol_mapper copied: {} bin(s) | map size = {}", rec.bins.size(), mapSizeOf(rec));
        } catch (Exception e) {
            LOG.error("❌ Lỗi copy symbol_mapper: {}", e.getMessage());
        }
    }

    /** funding_data: scan 242, chép nguyên bins từng symbol sang 226 (resume: bỏ qua key đã có). */
    private void copyFundingData(AerospikeClient src, AerospikeClient dst) {
        ScanPolicy sp = new ScanPolicy();
        sp.concurrentNodes = true;
        sp.includeBinData = true;
        try {
            src.scanAll(sp, NS_242, SET_FUNDINGFEE, (key, rec) -> {
                if (key.userKey == null) { noKey.incrementAndGet(); return; }  // không có userKey => không copy được
                String symbol = key.userKey.toString();
                Key k226 = new Key(NS, SET_FUNDINGFEE, symbol);
                try {
                    if (!FORCE_OVERWRITE && dst.exists(null, k226)) { skipped.incrementAndGet(); return; }
                    if (rec.bins == null || rec.bins.isEmpty()) return;
                    dst.put(writePolicy, k226, binsOf(rec));
                    long c = copied.incrementAndGet();
                    if (rnd.nextInt(15) == 0 && sampleSymbols.size() < VERIFY_SAMPLES) sampleSymbols.add(symbol);
                    if (c % 100 == 0) LOG.info("... funding_data copied={} skipped={}", c, skipped.get());
                } catch (Exception e) {
                    LOG.error("❌ Lỗi copy funding {}: {}", symbol, e.getMessage());
                }
            });
            LOG.info("✅ XONG funding_data: copied={} | skipped(đã có)={} | noKey={}",
                    copied.get(), skipped.get(), noKey.get());
            if (noKey.get() > 0)
                LOG.warn("⚠️ {} record funding_data trên 242 KHÔNG có userKey — không copy được (ghi thiếu sendKey?).", noKey.get());
        } catch (Exception e) {
            LOG.error("❌ Lỗi scan funding_data: {}", e.getMessage());
        }
    }

    /** So bytes mẫu funding_data + xác nhận mapper size khớp 242<->226. */
    private void verify(AerospikeClient src, AerospikeClient dst) {
        // mapper
        try {
            Record a = src.get(null, new Key(NS_242, SET_MAPPER, MAPPER_KEY));
            Record b = dst.get(null, new Key(NS, SET_MAPPER, MAPPER_KEY));
            LOG.info("🔎 VERIFY mapper: 242 size={} | 226 size={} | {}",
                    mapSizeOf(a), mapSizeOf(b),
                    (a != null && b != null && mapSizeOf(a) == mapSizeOf(b) && mapSizeOf(a) > 0) ? "KHỚP ✅" : "LỆCH 🔴");
        } catch (Exception e) {
            LOG.error("❌ Verify mapper lỗi: {}", e.getMessage());
        }

        // funding_data: so bytes f_data của mẫu
        List<String> keys = new ArrayList<>(sampleSymbols);
        int ok = 0, mismatch = 0, missing226 = 0;
        for (String sym : keys) {
            Key k242 = new Key(NS_242, SET_FUNDINGFEE, sym);
            Key kOracle = new Key(NS, SET_FUNDINGFEE, sym);
            Record a = src.get(null, k242);
            Record b = dst.get(null, kOracle);
            byte[] ba = (a != null) ? (byte[]) a.getValue("f_data") : null;
            byte[] bb = (b != null) ? (byte[]) b.getValue("f_data") : null;
            if (bb == null && a != null) { missing226++; continue; }
            if (Arrays.equals(ba, bb)) ok++; else mismatch++;
        }
        LOG.info("🔎 VERIFY funding_data {} mẫu: khớp bytes={} | LỆCH={} | thiếu 226={}", keys.size(), ok, mismatch, missing226);

        if (mismatch > 0 || missing226 > 0)
            LOG.error("⛔ funding_data CÓ LỆCH/THIẾU — chạy lại (resume vá thiếu); LỆCH thì FORCE_OVERWRITE=true.");
        else
            LOG.info("✅ AUX sync OK — Kaggle/HPO đọc symbol_mapper + funding_data từ 226 được rồi.");
    }

    private static Bin[] binsOf(Record rec) {
        List<Bin> bins = new ArrayList<>(rec.bins.size());
        for (Map.Entry<String, Object> e : rec.bins.entrySet()) bins.add(new Bin(e.getKey(), e.getValue()));
        return bins.toArray(new Bin[0]);
    }

    /** Kích thước bin map đầu tiên (symbol_mapper chỉ có 1 bin CDT map). 0 nếu không có. */
    private static int mapSizeOf(Record rec) {
        if (rec == null || rec.bins == null) return 0;
        for (Object v : rec.bins.values()) if (v instanceof Map) return ((Map<?, ?>) v).size();
        return 0;
    }
}
