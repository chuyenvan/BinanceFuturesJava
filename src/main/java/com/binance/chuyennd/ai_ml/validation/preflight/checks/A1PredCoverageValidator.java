package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.ExpectedRanges;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * A1 — Chặn "pred thiếu cả GIAI ĐOẠN" (bug gate trống 2021-2022 → 8/17 cửa sổ WFO ZERO_TRADES →
 * verdict FAIL GIẢ; {@code DATA_VALIDATION_FRAMEWORK §5.1}).
 *
 * <p><b>Cơ chế (§2 A1):</b> đếm số record MỖI THÁNG cho từng nguồn pred, tính median tháng-có-data,
 * rồi cờ mọi tháng trong SPAN mong đợi có count &lt; {@value #COVERAGE_MIN_FRACTION_DEFAULT}×median
 * (bao gồm tháng = 0). Bất kỳ tháng nào bị cờ ⇒ FAIL (A1 = BLOCK). Tháng gate 2021-2022 = 0 record
 * nằm trong span mong đợi ⇒ chắc chắn bị bắt (regression task 156).</p>
 *
 * <p><b>Nguồn quét (WRAP {@code CheckGapPredictMarket}/{@code CheckGapPredictSymbol} — đổi từ
 * "đếm phút THIẾU bằng exists()" sang "đếm record CÓ mỗi tháng bằng scanAll", đúng mechanism §2):</b>
 * <ul>
 *   <li><b>GATE</b> (Aerospike set, mặc định {@code ai_pred_market_gate_wfo}, override env {@code WFO_SET_PRED}):
 *       scanAll, lấy tháng từ {@code key.userKey} dạng {@code yyyyMMdd-HHmm} (writer bật {@code sendKey=true},
 *       xem {@code LoadWfoGatePredTool}). 1 record = 1 phút.</li>
 *   <li><b>FUNDING/SELECTOR</b> (file {@code predict_wf_*.bin} trong {@code ctx.fundingPredDir()}): đọc ts
 *       (8 byte đầu big-endian mỗi record 26B, mirror {@code WfoDataset.buildFundingFromWfFiles}). Bỏ qua nếu
 *       không có dir (không phải lỗi hạ tầng — gate vẫn bắt được regression chính là GATE).</li>
 * </ul></p>
 *
 * <p><b>SPAN mong đợi:</b> ưu tiên {@link ExpectedRanges#source(String)} khai báo pre-register; nếu CHƯA khai
 * báo thì dùng mặc định 2021-01 → tháng hiện tại (đủ phủ 2021-2022 để bắt regression) và ghi cờ
 * {@code defaultedSpan=true} vào metrics.</p>
 *
 * <p><b>TODO-verify-trên-data-thật:</b> (1) xác nhận {@code key.userKey} không null khi scanAll set gate
 * (phụ thuộc sendKey đã ghi) — nếu null hết, chuyển sang giải nén bin "data" lấy {@code AiPredictionData.timestamp};
 * (2) chốt {@link #COVERAGE_MIN_FRACTION_DEFAULT} và span mong đợi vào {@code validate_criteria.md}/{@code ExpectedRanges}
 * thay cho default; (3) tên nguồn tra {@code ExpectedRanges}: dùng {@code "gate"} và {@code "funding"} — khớp khi khai báo.</p>
 */
public final class A1PredCoverageValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(A1PredCoverageValidator.class);

    private static final String DEFAULT_GATE_SET = "ai_pred_market_gate_wfo";
    private static final int FUNDING_REC_BYTES = 26; // >q h 4f (WfoDataset.buildFundingFromWfFiles)
    /** Ngưỡng đề xuất: tháng có count &lt; 20% median = coverage gap (chờ Uni chốt vào ExpectedRanges). */
    private static final double COVERAGE_MIN_FRACTION_DEFAULT = 0.20;
    /** Múi giờ project (key Aerospike ghi theo GMT+7) — dùng để gom tháng nhất quán 2 nguồn. */
    private static final TimeZone TZ = TimeZone.getTimeZone("GMT+7");
    private static final int MAX_LIST = 30;

    @Override
    public CheckId id() {
        return CheckId.A1;
    }

    /**
     * Đếm record/tháng gate (+funding nếu có dir), cờ tháng dưới ngưỡng median trong span mong đợi.
     *
     * @param ctx cần {@link PreflightContext#client()} != null (quét gate set)
     * @return FAIL (BLOCK) nếu bất kỳ nguồn nào có tháng coverage gap; PASS kèm metrics số
     * @throws IllegalStateException nếu thiếu Aerospike client (lỗi hạ tầng → gate xử NEEDS_HUMAN)
     * @throws Exception nếu lỗi đọc file funding
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) throws Exception {
        AerospikeClient client = ctx.client();
        if (client == null) {
            throw new IllegalStateException("A1: thiếu Aerospike client trong PreflightContext (226/Oracle).");
        }
        Map<String, Object> metrics = new LinkedHashMap<>();
        List<String> failReasons = new ArrayList<>();

        // ---- Nguồn 1: GATE (Aerospike) ----
        String gateSet = firstNonEmpty(ctx.env("WFO_SET_PRED"), DEFAULT_GATE_SET);
        TreeMap<String, Long> gateByMonth = countGateByMonth(client, gateSet);
        evalSource("gate", gateSet, gateByMonth, ctx.expected(), metrics, failReasons);

        // ---- Nguồn 2: FUNDING/SELECTOR (file bin) ----
        String fundingDir = ctx.fundingPredDir();
        if (fundingDir != null && !fundingDir.trim().isEmpty()) {
            TreeMap<String, Long> fundByMonth = countFundingByMonth(fundingDir);
            evalSource("funding", fundingDir, fundByMonth, ctx.expected(), metrics, failReasons);
        } else {
            metrics.put("funding.skipped", "khong co WFO_FUNDING_PRED_DIR (bo qua nguon funding)");
            LOG.warn("A1: bo qua nguon funding (fundingPredDir rong).");
        }

        if (!failReasons.isEmpty()) {
            return ValidationResult.fail(id(),
                    "Pred thieu giai doan (coverage gap): " + failReasons, metrics);
        }
        return ValidationResult.pass(id(),
                "Moi nguon pred phu du cac thang trong span mong doi (khong co coverage gap).", metrics);
    }

    /** Quét gate set, gom tháng {@code yyyyMM} từ {@code key.userKey}. Trả map tháng→count (sắp xếp). */
    private TreeMap<String, Long> countGateByMonth(AerospikeClient client, String setName) {
        Map<String, Long> byMonth = new ConcurrentHashMap<>();
        AtomicLong total = new AtomicLong();
        AtomicLong noKey = new AtomicLong();
        ScanPolicy sp = new ScanPolicy();
        sp.concurrentNodes = true;
        client.scanAll(sp, Configs.AEROSPIKE_NAMESPACE, setName, (key, rec) -> {
            total.incrementAndGet();
            if (key.userKey == null) {
                noKey.incrementAndGet();
                return;
            }
            String uk = key.userKey.toString(); // yyyyMMdd-HHmm
            if (uk.length() >= 6) {
                byMonth.merge(uk.substring(0, 6), 1L, Long::sum);
            } else {
                noKey.incrementAndGet();
            }
        });
        if (total.get() > 0 && noKey.get() == total.get()) {
            throw new IllegalStateException("A1: gate set " + setName + " khong tra userKey (sendKey?) — "
                    + "khong xac dinh duoc thang. Can chuyen sang giai nen bin data.timestamp.");
        }
        return new TreeMap<>(byMonth);
    }

    /** Đọc ts từ mọi {@code predict_wf_*.bin}, gom tháng {@code yyyyMM}. Trả map tháng→count. */
    private TreeMap<String, Long> countFundingByMonth(String predDir) throws Exception {
        File d = new File(predDir);
        File[] files = d.listFiles((dir, name) -> name.startsWith("predict_wf_") && name.endsWith(".bin"));
        if (files == null || files.length == 0) {
            throw new IllegalStateException("A1: khong thay predict_wf_*.bin trong " + predDir);
        }
        SimpleDateFormat monthFmt = new SimpleDateFormat("yyyyMM");
        monthFmt.setTimeZone(TZ);
        TreeMap<String, Long> byMonth = new TreeMap<>();
        for (File f : files) {
            byte[] all = Files.readAllBytes(f.toPath());
            if (all.length % FUNDING_REC_BYTES != 0) {
                throw new IllegalStateException("A1: " + f.getName() + " (" + all.length
                        + " byte) khong chia het " + FUNDING_REC_BYTES);
            }
            ByteBuffer buf = ByteBuffer.wrap(all); // big-endian mac dinh
            int nrec = all.length / FUNDING_REC_BYTES;
            for (int i = 0; i < nrec; i++) {
                long ts = buf.getLong();
                buf.position(buf.position() + (FUNDING_REC_BYTES - 8)); // bo symId + 4 float
                byMonth.merge(monthFmt.format(new java.util.Date(ts)), 1L, Long::sum);
            }
        }
        return byMonth;
    }

    /**
     * So từng tháng trong span mong đợi với ngưỡng median; ghi metrics + fail reasons nếu có gap.
     */
    private void evalSource(String srcName, String srcRef, TreeMap<String, Long> byMonth,
                            ExpectedRanges expected, Map<String, Object> metrics, List<String> failReasons) {
        long totalRec = byMonth.values().stream().mapToLong(Long::longValue).sum();

        // Median trên các tháng CÓ data (mức "bình thường").
        List<Long> counts = new ArrayList<>(byMonth.values());
        Collections.sort(counts);
        long median = counts.isEmpty() ? 0 : counts.get(counts.size() / 2);
        long threshold = (long) Math.floor(median * COVERAGE_MIN_FRACTION_DEFAULT);

        // Span mong đợi: ExpectedRanges nếu khai báo, else default 2021-01..thang hien tai.
        ExpectedRanges.SourceRange sr = expected.source(srcName);
        boolean defaulted = (sr == null);
        List<String> expectedMonths = defaulted
                ? defaultSpanMonths()
                : enumerateMonths(sr.expectedStartMs, sr.expectedEndMs);

        List<String> gapMonths = new ArrayList<>();
        int zeroMonths = 0;
        for (String ym : expectedMonths) {
            long c = byMonth.getOrDefault(ym, 0L);
            if (c == 0) zeroMonths++;
            if (c < threshold || c == 0) {
                if (gapMonths.size() < MAX_LIST) gapMonths.add(ym + "=" + c);
            }
        }

        metrics.put(srcName + ".ref", srcRef);
        metrics.put(srcName + ".totalRecords", totalRec);
        metrics.put(srcName + ".monthsWithData", byMonth.size());
        metrics.put(srcName + ".monthsExpected", expectedMonths.size());
        metrics.put(srcName + ".monthsZeroInSpan", zeroMonths);
        metrics.put(srcName + ".median", median);
        metrics.put(srcName + ".threshold", threshold);
        metrics.put(srcName + ".defaultedSpan", defaulted);
        metrics.put(srcName + ".gapMonths", gapMonths);

        if (!gapMonths.isEmpty()) {
            failReasons.add(srcName + ": " + gapMonths.size() + " thang < nguong " + threshold
                    + " (median=" + median + ", span" + (defaulted ? "=DEFAULT" : "") + "): " + gapMonths);
        }
    }

    /** Liệt kê tháng {@code yyyyMM} trong [startMs, endMs] theo GMT+7. */
    private List<String> enumerateMonths(long startMs, long endMs) {
        List<String> out = new ArrayList<>();
        SimpleDateFormat monthFmt = new SimpleDateFormat("yyyyMM");
        monthFmt.setTimeZone(TZ);
        Calendar cal = Calendar.getInstance(TZ);
        cal.setTimeInMillis(startMs);
        cal.set(Calendar.DAY_OF_MONTH, 1);
        cal.set(Calendar.HOUR_OF_DAY, 0);
        cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0);
        cal.set(Calendar.MILLISECOND, 0);
        while (cal.getTimeInMillis() <= endMs) {
            out.add(monthFmt.format(cal.getTime()));
            cal.add(Calendar.MONTH, 1);
        }
        return out;
    }

    /** Span mặc định 2021-01 → tháng hiện tại (phủ 2021-2022 để bắt regression gate). */
    private List<String> defaultSpanMonths() {
        Calendar start = Calendar.getInstance(TZ);
        start.set(2021, Calendar.JANUARY, 1, 0, 0, 0);
        return enumerateMonths(start.getTimeInMillis(), System.currentTimeMillis());
    }

    private static String firstNonEmpty(String a, String b) {
        return (a != null && !a.trim().isEmpty()) ? a.trim() : b;
    }
}
