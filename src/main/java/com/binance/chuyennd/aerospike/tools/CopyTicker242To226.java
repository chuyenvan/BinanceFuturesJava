package com.binance.chuyennd.aerospike.tools;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.BatchPolicy;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

/**
 * COPY TICKER 1M TỪ 242 (live, đã khóa firewall) SANG 226 (public cho Kaggle).
 *
 * MỤC ĐÍCH: Kaggle worker không với được 242 => copy ticker (dữ liệu lịch sử, read-only)
 * sang 226 MỘT LẦN, từ đó mọi job Kaggle (gen funding, validate, WFO...) đọc 226.
 * 242 không bao giờ phải mở firewall.
 *
 * THIẾT KẾ:
 *  - Chép NGUYÊN byte[] bin "data" (snappy/proto) — không giải nén/parse => nhanh và
 *    đảm bảo bản sao giống hệt từng byte.
 *  - IDEMPOTENT + RESUME: mặc định batch-exists trên 226 trước, chỉ copy key còn thiếu.
 *    Chết giữa chừng chạy lại là tiếp tục, không tốn lại từ đầu. FORCE_OVERWRITE=true để chép đè.
 *  - VERIFY: sau khi xong, lấy mẫu ngẫu nhiên N key so bytes 242 vs 226.
 *
 * CHẠY Ở ĐÂU: máy 226 (nằm trong whitelist của 242, và ghi local vào chính nó).
 * Khoảng 2.8M records => ước ~15-30 phút tùy mạng nội bộ.
 */
public class CopyTicker242To226 {

    private static final Logger LOG = LoggerFactory.getLogger(CopyTicker242To226.class);

    // ⚙️ CẤU HÌNH
    private static String START_DATE = "20210101";          // override qua args[0] yyyyMMdd
    private static String END_DATE = null;                   // null = tới hôm nay; override qua args[1] yyyyMMdd (loại trừ)
    private static final boolean FORCE_OVERWRITE = false;   // true = chép đè kể cả key đã có trên 226
    private static final int PUT_THREADS = 4;                // luồng ghi song song vào 226
    private static final int VERIFY_SAMPLES = 200;           // số key lấy mẫu so bytes cuối cùng

    private static final String SET_TICKER = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER; // kline_1m_opt
    private static final String BIN_DATA = "data";

    private final BatchPolicy batchPolicy = new BatchPolicy();
    private final WritePolicy writePolicy = new WritePolicy();
    private final ExecutorService putPool = Executors.newFixedThreadPool(PUT_THREADS);

    private final AtomicLong copied = new AtomicLong();
    private final AtomicLong skippedExisting = new AtomicLong();
    private final AtomicLong missingOn242 = new AtomicLong();
    private final List<String> sampleKeys = Collections.synchronizedList(new ArrayList<>());
    private final Random rnd = new Random(42);

    public CopyTicker242To226() {
        writePolicy.sendKey = true;
        writePolicy.expiration = 0;                          // vĩnh viễn, giống bản gốc
        writePolicy.recordExistsAction = RecordExistsAction.UPDATE;
    }

    public static void main(String[] args) {
        try {
            if (args.length >= 1 && args[0] != null && !args[0].isBlank()) START_DATE = args[0].trim();
            if (args.length >= 2 && args[1] != null && !args[1].isBlank()) END_DATE = args[1].trim();
            LOG.info("ARGS range: START_DATE={} END_DATE={}", START_DATE, END_DATE);
            new CopyTicker242To226().run();
        } catch (Exception e) {
            LOG.error("CopyTicker error", e);
        }
        System.exit(0);
    }

    public void run() throws Exception {
        long start = Utils.sdfFile.parse(START_DATE).getTime();
        long end = (END_DATE != null) ? Utils.sdfFile.parse(END_DATE).getTime() + Utils.TIME_DAY
                : System.currentTimeMillis();

        AerospikeClient src = DataManagerAerospikeFloatSim.getClient242();
        AerospikeClient dst = DataManagerAerospikeFloatSim.getClientOracle();

        LOG.info("🚚 COPY TICKER 242 -> 226 | set={} | {} -> {} | force={}",
                SET_TICKER, START_DATE, Utils.normalizeDateYYYYMMDD(end), FORCE_OVERWRITE);

        SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");
        long day = Utils.getDate(start);
        int dayCount = 0;

        while (day < end) {
            try {
                // 1. Dựng 1440 key của ngày
                Key[] srcKeys = new Key[1440];
                String[] keyStrings = new String[1440];
                for (int m = 0; m < 1440; m++) {
                    keyStrings[m] = keyFmt.format(new Date(day + m * Utils.TIME_MINUTE));
                    srcKeys[m] = new Key(Configs.AEROSPIKE_NAMESPACE, SET_TICKER, keyStrings[m]);
                }

                // 2. Xác định key cần copy (resume: bỏ qua key đã có trên 226)
                boolean[] need = new boolean[1440];
                if (FORCE_OVERWRITE) {
                    Arrays.fill(need, true);
                } else {
                    boolean[] existsOn226 = dst.exists(batchPolicy, srcKeys);
                    for (int m = 0; m < 1440; m++) {
                        need[m] = !existsOn226[m];
                        if (existsOn226[m]) skippedExisting.incrementAndGet();
                    }
                }

                // 3. Batch read từ 242 cho các key cần
                List<Integer> idxNeed = new ArrayList<>();
                for (int m = 0; m < 1440; m++) if (need[m]) idxNeed.add(m);
                if (!idxNeed.isEmpty()) {
                    Key[] readKeys = new Key[idxNeed.size()];
                    for (int i = 0; i < idxNeed.size(); i++) readKeys[i] = srcKeys[idxNeed.get(i)];
                    Record[] records = src.get(batchPolicy, readKeys);

                    // 4. Ghi song song vào 226 — chép NGUYÊN bytes
                    List<Future<?>> futures = new ArrayList<>();
                    for (int i = 0; i < records.length; i++) {
                        Record r = records[i];
                        int idx = idxNeed.get(i);
                        if (r == null) { missingOn242.incrementAndGet(); continue; }
                        byte[] bytes = (byte[]) r.getValue(BIN_DATA);
                        if (bytes == null) { missingOn242.incrementAndGet(); continue; }

                        final String ks = keyStrings[idx];
                        futures.add(putPool.submit(() -> {
                            dst.put(writePolicy, new Key(Configs.AEROSPIKE_NAMESPACE, SET_TICKER, ks),
                                    new Bin(BIN_DATA, bytes));
                            copied.incrementAndGet();
                        }));
                        if (rnd.nextInt(20000) == 0) sampleKeys.add(ks);   // gom mẫu verify
                    }
                    for (Future<?> f : futures) f.get();
                }
            } catch (Exception e) {
                LOG.error("❌ Lỗi ngày {} — chạy lại tool là tự resume ngày này.", Utils.normalizeDateYYYYMMDD(day), e);
            }

            day += Utils.TIME_DAY;
            if (++dayCount % 30 == 0) {
                LOG.info("... {} ngày | copied={} | skipped(đã có)={} | missing(242 không có)={}",
                        dayCount, copied.get(), skippedExisting.get(), missingOn242.get());
            }
        }

        putPool.shutdown();
        putPool.awaitTermination(10, TimeUnit.MINUTES);
        LOG.info("✅ XONG COPY: copied={} | skipped={} | missing242={}",
                copied.get(), skippedExisting.get(), missingOn242.get());

        verifySample(src, dst);
    }

    /** So bytes ngẫu nhiên giữa 242 và 226 — bắt copy hỏng trước khi tin dữ liệu. */
    private void verifySample(AerospikeClient src, AerospikeClient dst) {
        List<String> keys = new ArrayList<>(sampleKeys);
        // nếu mẫu gom được ít (vd toàn skip vì resume), bốc thêm key ngẫu nhiên trong range
        SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");
        try {
            long start = Utils.sdfFile.parse(START_DATE).getTime();
            long span = System.currentTimeMillis() - start;
            while (keys.size() < VERIFY_SAMPLES) {
                long t = start + (long) (rnd.nextDouble() * span);
                keys.add(keyFmt.format(new Date((t / Utils.TIME_MINUTE) * Utils.TIME_MINUTE)));
            }
        } catch (Exception ignored) { }

        int ok = 0, mismatch = 0, bothMissing = 0, onlySrc = 0;
        for (String ks : keys) {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, SET_TICKER, ks);
            Record a = src.get(null, key);
            Record b = dst.get(null, key);
            byte[] ba = a != null ? (byte[]) a.getValue(BIN_DATA) : null;
            byte[] bb = b != null ? (byte[]) b.getValue(BIN_DATA) : null;
            if (ba == null && bb == null) { bothMissing++; continue; }
            if (ba != null && bb == null) { onlySrc++; continue; }
            if (Arrays.equals(ba, bb)) ok++; else mismatch++;
        }
        LOG.info("🔎 VERIFY {} mẫu: khớp bytes={} | LỆCH={} | thiếu trên 226={} | cả hai không có={}",
                keys.size(), ok, mismatch, onlySrc, bothMissing);
        if (mismatch > 0 || onlySrc > 0) {
            LOG.error("⛔ CÓ LỆCH/THIẾU — đừng cho Kaggle dùng vội. Chạy lại tool (resume tự vá phần thiếu);"
                    + " nếu LỆCH bytes thì chạy lại với FORCE_OVERWRITE=true cho các ngày liên quan.");
        } else {
            LOG.info("✅ Bản sao 226 khớp 242. Kaggle dùng được.");
        }
    }
}