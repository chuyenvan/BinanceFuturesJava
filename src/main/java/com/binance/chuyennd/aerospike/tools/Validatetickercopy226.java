package com.binance.chuyennd.aerospike.tools;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.BatchPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;

/**
 * VALIDATE BẢN SAO TICKER 226 vs 242 — lấy mẫu PHỦ ĐỀU, không check all.
 *
 * Hai tầng kiểm, bắt hai kiểu hỏng khác nhau:
 *  (A) BYTE-COMPARE PHÂN TẦNG THEO THÁNG: mỗi tháng bốc MINUTES_PER_MONTH phút ngẫu nhiên,
 *      đọc cả hai cluster, so bytes. Phân tầng đảm bảo KHÔNG tháng nào lọt lưới
 *      (random thuần dễ bỏ sót cụm hỏng cục bộ — vd vài ngày copy lỗi trong một tháng).
 *  (B) EXISTS-SCAN THEO NGÀY: bốc DAYS_RANDOM ngày ngẫu nhiên, batch-exists đủ 1440 key
 *      trên CẢ HAI cluster, so bitmap. Rẻ (không kéo data) nên quét được rộng — bắt kiểu
 *      hỏng "thiếu record" mà byte-compare mẫu thưa có thể trượt.
 *
 * Quy ước đếm:
 *  - match        : cả hai có, bytes giống hệt.
 *  - MISMATCH     : cả hai có, bytes KHÁC -> copy hỏng, phải chép đè lại (FORCE_OVERWRITE).
 *  - MISSING_226  : 242 có, 226 không -> copy thiếu, chạy lại CopyTicker242To226 (tự resume).
 *  - both-empty   : cả hai không có (gap gốc của collector) -> NHẤT QUÁN, tính là OK.
 *  - EXTRA_226    : 226 có, 242 không -> lạ, cần soi tay (không được phép xảy ra với copy thuần).
 *
 * Kết luận: PASS khi MISMATCH = 0 và MISSING_226 = 0 và EXTRA_226 = 0 trên toàn bộ mẫu.
 * In bảng theo tháng để biết tháng nào hỏng mà chép lại đúng chỗ.
 *
 * CHẠY TRÊN 226 (với được cả hai cluster). Read-only tuyệt đối.
 */
public class Validatetickercopy226 {

    private static final Logger LOG = LoggerFactory.getLogger(Validatetickercopy226.class);

    // ⚙️ CẤU HÌNH MẪU
    private static final String START_DATE = "20210101";
    private static final int MINUTES_PER_MONTH = 60;   // tầng A: ~60 phút/tháng x ~65 tháng ≈ 4000 record so bytes
    private static final int DAYS_RANDOM = 40;         // tầng B: 40 ngày x 1440 key exists-scan ≈ 57k key
    private static final long SEED = 42;               // cố định để chạy lại tái lập được

    private static final String SET_TICKER = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER;
    private static final String BIN_DATA = "data";

    private final BatchPolicy batchPolicy = new BatchPolicy();
    private final SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");
    private final Random rnd = new Random(SEED);

    private static class MonthStat {
        int sampled, match, mismatch, missing226, extra226, bothEmpty;
    }

    public static void main(String[] args) {
        try { new Validatetickercopy226().run(); }
        catch (Exception e) { LOG.error("ValidateTickerCopy error", e); }
        System.exit(0);
    }

    public void run() throws Exception {
        long start = Utils.sdfFile.parse(START_DATE).getTime();
        long end = System.currentTimeMillis();
        AerospikeClient src = DataManagerAerospikeFloatSim.getClient242();
        AerospikeClient dst = DataManagerAerospikeFloatSim.getClientOracle();

        LOG.info("🔎 VALIDATE TICKER 226 vs 242 | {} -> nay | tầng A: {} phút/tháng | tầng B: {} ngày exists-scan",
                START_DATE, MINUTES_PER_MONTH, DAYS_RANDOM);

        TreeMap<String, MonthStat> monthStats = new TreeMap<>();

        // ===== TẦNG A: byte-compare phân tầng theo tháng =====
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(start);
        cal.set(Calendar.DAY_OF_MONTH, 1);
        cal.set(Calendar.HOUR_OF_DAY, 0); cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0); cal.set(Calendar.MILLISECOND, 0);

        while (cal.getTimeInMillis() < end) {
            long monthStart = cal.getTimeInMillis();
            cal.add(Calendar.MONTH, 1);
            long monthEnd = Math.min(cal.getTimeInMillis(), end);
            String monthLabel = new SimpleDateFormat("yyyyMM").format(new Date(monthStart));

            // bốc MINUTES_PER_MONTH phút ngẫu nhiên trong tháng (làm tròn về phút)
            Set<Long> picked = new LinkedHashSet<>();
            long spanMin = (monthEnd - monthStart) / Utils.TIME_MINUTE;
            if (spanMin <= 0) continue;
            while (picked.size() < Math.min(MINUTES_PER_MONTH, spanMin)) {
                picked.add(monthStart + (long) (rnd.nextDouble() * spanMin) * Utils.TIME_MINUTE);
            }

            MonthStat st = monthStats.computeIfAbsent(monthLabel, k -> new MonthStat());
            List<Long> times = new ArrayList<>(picked);
            Key[] keys = new Key[times.size()];
            for (int i = 0; i < times.size(); i++) {
                keys[i] = new Key(Configs.AEROSPIKE_NAMESPACE, SET_TICKER, keyFmt.format(new Date(times.get(i))));
            }

            Record[] recSrc = src.get(batchPolicy, keys);
            Record[] recDst = dst.get(batchPolicy, keys);

            for (int i = 0; i < keys.length; i++) {
                st.sampled++;
                byte[] a = (recSrc != null && recSrc[i] != null) ? (byte[]) recSrc[i].getValue(BIN_DATA) : null;
                byte[] b = (recDst != null && recDst[i] != null) ? (byte[]) recDst[i].getValue(BIN_DATA) : null;
                if (a == null && b == null) st.bothEmpty++;
                else if (a != null && b == null) st.missing226++;
                else if (a == null) st.extra226++;
                else if (Arrays.equals(a, b)) st.match++;
                else st.mismatch++;
            }
        }
        LOG.info("✅ Tầng A xong: {} tháng đã lấy mẫu byte-compare.", monthStats.size());

        // ===== TẦNG B: exists-scan theo ngày ngẫu nhiên =====
        long totalDays = (Utils.getDate(end) - Utils.getDate(start)) / Utils.TIME_DAY;
        Set<Long> pickedDays = new LinkedHashSet<>();
        while (pickedDays.size() < Math.min(DAYS_RANDOM, totalDays)) {
            pickedDays.add(Utils.getDate(start) + (long) (rnd.nextDouble() * totalDays) * Utils.TIME_DAY);
        }

        long bMissing = 0, bExtra = 0, bChecked = 0;
        List<String> badDays = new ArrayList<>();
        for (long day : pickedDays) {
            Key[] keys = new Key[1440];
            for (int m = 0; m < 1440; m++) {
                keys[m] = new Key(Configs.AEROSPIKE_NAMESPACE, SET_TICKER,
                        keyFmt.format(new Date(day + m * Utils.TIME_MINUTE)));
            }
            boolean[] exSrc = src.exists(batchPolicy, keys);
            boolean[] exDst = dst.exists(batchPolicy, keys);
            int dayMissing = 0, dayExtra = 0;
            for (int m = 0; m < 1440; m++) {
                bChecked++;
                if (exSrc[m] && !exDst[m]) { bMissing++; dayMissing++; }
                else if (!exSrc[m] && exDst[m]) { bExtra++; dayExtra++; }
            }
            if (dayMissing > 0 || dayExtra > 0) {
                badDays.add(String.format(Locale.US, "%s(missing=%d, extra=%d)",
                        Utils.normalizeDateYYYYMMDD(day), dayMissing, dayExtra));
            }
        }
        LOG.info("✅ Tầng B xong: {} key exists-scan trên {} ngày.", bChecked, pickedDays.size());

        // ===== BÁO CÁO =====
        long tSampled = 0, tMatch = 0, tMismatch = 0, tMissing = 0, tExtra = 0, tEmpty = 0;
        List<String> badMonths = new ArrayList<>();
        for (Map.Entry<String, MonthStat> e : monthStats.entrySet()) {
            MonthStat s = e.getValue();
            tSampled += s.sampled; tMatch += s.match; tMismatch += s.mismatch;
            tMissing += s.missing226; tExtra += s.extra226; tEmpty += s.bothEmpty;
            if (s.mismatch > 0 || s.missing226 > 0 || s.extra226 > 0) {
                badMonths.add(String.format(Locale.US, "%s(mismatch=%d, missing226=%d, extra226=%d / %d mẫu)",
                        e.getKey(), s.mismatch, s.missing226, s.extra226, s.sampled));
            }
        }

        LOG.info("\n================ KẾT QUẢ VALIDATE TICKER 226 vs 242 ================");
        LOG.info("Tầng A (byte-compare, {} mẫu): match={} | MISMATCH={} | MISSING_226={} | EXTRA_226={} | both-empty(OK)={}",
                tSampled, tMatch, tMismatch, tMissing, tExtra, tEmpty);
        LOG.info("Tầng B (exists-scan, {} key / {} ngày): MISSING_226={} | EXTRA_226={}",
                bChecked, pickedDays.size(), bMissing, bExtra);

        if (!badMonths.isEmpty()) LOG.warn("⚠️ Tháng có vấn đề (tầng A): {}", badMonths);
        if (!badDays.isEmpty()) LOG.warn("⚠️ Ngày có vấn đề (tầng B): {}", badDays);

        boolean pass = (tMismatch == 0 && tMissing == 0 && tExtra == 0 && bMissing == 0 && bExtra == 0);
        if (pass) {
            LOG.info("🟢 PASS — bản sao 226 nhất quán với 242 trên toàn bộ mẫu phủ đều. Kaggle dùng được.");
        } else {
            LOG.error("🔴 FAIL — xử lý theo loại lỗi:");
            LOG.error("   MISSING_226 -> chạy lại CopyTicker242To226 (tự resume, chỉ chép phần thiếu).");
            LOG.error("   MISMATCH    -> chạy lại CopyTicker242To226 với FORCE_OVERWRITE=true (giới hạn các tháng/ngày liệt kê trên).");
            LOG.error("   EXTRA_226   -> không được phép với copy thuần, soi tay xem ai ghi vào set ticker trên 226.");
            LOG.error("   Sửa xong CHẠY LẠI tool này tới khi PASS rồi mới thả Kaggle worker.");
        }
    }
}