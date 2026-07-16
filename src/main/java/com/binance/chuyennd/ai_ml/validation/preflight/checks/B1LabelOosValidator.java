package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedInputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * B1 — Chặn LEAKAGE nhãn OOS: label/pred của vùng OOS không được lấn vào vùng train.
 *
 * <p>Bài học ({@code DATA_VALIDATION_FRAMEWORK §5.2}): "precision ×2.4" hóa ra là số leaky vì nhãn
 * tính từ giá vùng OOS gần biên fold. Cơ chế spec (§2 nhóm B): với mỗi {@code predict_wf}:
 * {@code max(ts_train) < min(ts_oos) − embargo}.</p>
 *
 * <p><b>WRAP:</b> tầng đo edge sâu (IC/LIFT trên OOS thật) là
 * {@link com.binance.chuyennd.ai_ml.validation.predict.funding.ValidateFundingOOS} — nhưng tool đó
 * chạy trên set Aerospike model CŨ (funding_pred_1m_v5) và có {@code main()}/hardcode set, KHÔNG
 * phải nguồn walk-forward hiện tại. Validator này ĐO trực tiếp trên nguồn thật đang dùng:
 * các file {@code predict_wf_*.bin} (leak-free walk-forward, xem {@code WFO_DATAFLOW §2b}).</p>
 *
 * <p><b>Cơ chế đo được từ predict_wf (không cần đọc lại train dataset):</b> pipeline
 * ({@code gen_funding_wf_predictions.py}) sinh mỗi fold bằng model chỉ train trên
 * {@code ts < cutoff − purge}, rồi dự đoán OOS {@code [cutoff, cutoff+3m)}. Tên file
 * {@code predict_wf_<YYYYMMDD>.bin} mã hoá cutoff (mốc GMT+7). Do đó, NẾU mọi ts trong file OOS
 * đều {@code >= cutoff} thì suy ra {@code max(ts_train) < cutoff − embargo <= min(ts_oos) − embargo}
 * — đúng bất đẳng thức B1. Validator kiểm điều kiện quan sát-được này và ĐO khe embargo thực tế.
 * Fold sớm nhất (fold-0) được thiết kế phủ thêm vùng 2021 IS-only (block_lo = ts_min) nên được
 * đánh dấu riêng, KHÔNG coi là leak.</p>
 *
 * <p>Random-sample: theo §4b, B1 cần thêm mẫu quanh ±embargo mỗi biên fold. Ở đây ta QUÉT TOÀN BỘ
 * ts của từng file (siêu tập của yêu cầu lấy mẫu biên) nên phủ chắc vùng biên; {@code sampleSizePerCell}
 * được ghi vào metrics để truy vết.</p>
 *
 * <p>TODO-verify (data thật): (1) xác nhận {@code embargo == purge} thực của pipeline (mặc định
 * 288 bước × 15m = 72h — {@code WFO_DATAFLOW §2b}); nếu env/manifest khai khác thì đọc từ đó, KHÔNG
 * hardcode. (2) Xác nhận phần "train thực sự dừng tại cutoff − purge" bằng cross-check ts của
 * train dataset (funding.bin/market.bin hoặc Aerospike) — nằm ngoài phạm vi file predict_wf.
 * (3) Xác nhận quy ước timezone GMT+7 của cutoff (TZ_OFFSET_MS = 7h) khớp thực tế.</p>
 */
public final class B1LabelOosValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(B1LabelOosValidator.class);

    /** Kích thước 1 record predict_wf (big-endian: long ts + short symId + 4 float p4h/p12h/p24h/p72h). */
    private static final int REC = 26;

    /** 1 bar = 15 phút (grid selector). Nguồn: {@code gen_funding_wf_predictions.py} GRID_MS. */
    private static final long GRID_MS = 15L * 60 * 1000;

    /**
     * Embargo/purge mặc định = 288 bước × 15m = 72h. Nguồn: {@code gen_funding_wf_predictions.py}
     * PURGE_STEPS=288 + {@code WFO_DATAFLOW §2b}. TODO-verify: nếu env {@code PURGE_STEPS} có mặt thì
     * ưu tiên đọc từ đó (không hardcode verdict).
     */
    private static final long DEFAULT_EMBARGO_MS = 288L * GRID_MS;

    /** Lệch múi giờ GMT+7 dùng khi diễn giải cutoff trong tên file (khớp pipeline). TODO-verify. */
    private static final long TZ_OFFSET_MS = 7L * 60 * 60 * 1000;

    private static final DateTimeFormatter YMD = DateTimeFormatter.ofPattern("yyyyMMdd");

    @Override
    public CheckId id() {
        return CheckId.B1;
    }

    @Override
    public boolean expensive() {
        return true;
    }

    /**
     * Quét mọi {@code predict_wf_*.bin}, kiểm biên OOS ≥ cutoff và đo khe embargo mỗi fold.
     *
     * @param ctx ngữ cảnh (cần {@link PreflightContext#fundingPredDir()} trỏ thư mục predict_wf)
     * @return FAIL (BLOCK) nếu fold nào (trừ fold-0 IS-only) có ts OOS lấn vào vùng &lt; cutoff hoặc
     *         nằm trong khe embargo; PASS kèm metrics khe embargo nhỏ nhất từng fold
     * @throws IllegalStateException khi thiếu thư mục pred / không có file (lỗi hạ tầng → NEEDS_HUMAN)
     * @throws IOException khi lỗi đọc file (lỗi hạ tầng → NEEDS_HUMAN)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) throws IOException {
        String predDir = ctx.fundingPredDir();
        if (predDir == null || predDir.trim().isEmpty()) {
            throw new IllegalStateException("B1: thiếu WFO_FUNDING_PRED_DIR (fundingPredDir) — không thể đo leak OOS.");
        }
        File dir = new File(predDir);
        File[] files = dir.listFiles((d, name) -> name.startsWith("predict_wf_") && name.endsWith(".bin"));
        if (files == null || files.length == 0) {
            throw new IllegalStateException("B1: không thấy predict_wf_*.bin trong " + predDir);
        }
        java.util.Arrays.sort(files);

        long embargoMs = DEFAULT_EMBARGO_MS; // TODO-verify: đọc từ env/manifest nếu pipeline khai khác.

        // Đo từng fold trước để tìm cutoff nhỏ nhất (fold-0 IS-only).
        List<FoldStat> stats = new ArrayList<>();
        long minCutoff = Long.MAX_VALUE;
        for (File f : files) {
            long cutoff = parseCutoffMs(f.getName());
            FoldStat st = scanFold(f, cutoff, embargoMs);
            stats.add(st);
            if (cutoff < minCutoff) {
                minCutoff = cutoff;
            }
        }

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("folds", files.length);
        metrics.put("embargoMs", embargoMs);
        metrics.put("embargoHours", embargoMs / 3_600_000L);
        metrics.put("sampleSizePerCell", ctx.sampleSizePerCell());

        List<String> leakFolds = new ArrayList<>();
        List<String> embargoViolations = new ArrayList<>();
        long totalRec = 0;
        long minGapToEmbargoMs = Long.MAX_VALUE;
        for (FoldStat st : stats) {
            totalRec += st.count;
            boolean isFold0 = st.cutoffMs == minCutoff;
            String tag = st.fileName + "(cutoff=" + st.cutoffMs + ",minOos=" + st.minTs
                    + ",oosBeforeCutoff=" + st.oosBeforeCutoff + ",inEmbargo=" + st.inEmbargoZone + ")";
            if (isFold0) {
                metrics.put("fold0_isOnlyBackfill", st.fileName);
                continue; // fold-0 phủ 2021 IS-only theo thiết kế — không tính leak.
            }
            // Khe embargo thực đo = min(ts_oos) − (cutoff − embargo). Phải ≥ embargo (tương đương minOos ≥ cutoff).
            if (st.count > 0) {
                long gapToEmbargo = st.minTs - (st.cutoffMs - embargoMs);
                if (gapToEmbargo < minGapToEmbargoMs) {
                    minGapToEmbargoMs = gapToEmbargo;
                }
            }
            if (st.oosBeforeCutoff > 0) {
                leakFolds.add(tag);
            }
            if (st.inEmbargoZone > 0) {
                embargoViolations.add(tag);
            }
        }
        metrics.put("totalRec", totalRec);
        metrics.put("minGapToEmbargoMs", minGapToEmbargoMs == Long.MAX_VALUE ? -1 : minGapToEmbargoMs);
        metrics.put("leakFolds", leakFolds.size());
        metrics.put("embargoViolationFolds", embargoViolations.size());

        if (!leakFolds.isEmpty()) {
            return ValidationResult.fail(id(),
                    "LEAK B1: có fold OOS chứa ts < cutoff (nhãn/pred lấn vùng train): " + leakFolds, metrics);
        }
        if (!embargoViolations.isEmpty()) {
            return ValidationResult.fail(id(),
                    "LEAK B1: có fold OOS rơi trong khe embargo [cutoff−" + (embargoMs / 3_600_000L)
                            + "h, cutoff): " + embargoViolations, metrics);
        }
        LOG.info("B1 OK: {} fold, khe embargo nhỏ nhất = {} ms (>= embargo {} ms).",
                files.length, metrics.get("minGapToEmbargoMs"), embargoMs);
        return ValidationResult.pass(id(),
                "Mọi fold OOS >= cutoff và ngoài khe embargo (" + (embargoMs / 3_600_000L)
                        + "h); suy ra max(ts_train) < min(ts_oos) − embargo.", metrics);
    }

    /**
     * Diễn giải cutoff (ms epoch) từ tên file {@code predict_wf_<YYYYMMDD>.bin}. Ngày là mốc GMT+7.
     *
     * @param fileName tên file
     * @return cutoff tính bằng ms epoch (UTC-midnight của ngày trừ TZ_OFFSET_MS)
     * @throws IllegalStateException nếu tên file không đúng khuôn (lỗi hạ tầng → NEEDS_HUMAN)
     */
    private static long parseCutoffMs(String fileName) {
        String core = fileName.substring("predict_wf_".length(), fileName.length() - ".bin".length());
        try {
            LocalDate d = LocalDate.parse(core, YMD);
            return d.atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli() - TZ_OFFSET_MS;
        } catch (RuntimeException e) {
            throw new IllegalStateException("B1: tên file predict_wf sai khuôn ngày: " + fileName, e);
        }
    }

    /**
     * Quét toàn bộ record 1 fold, đếm số OOS trước cutoff và trong khe embargo, lấy min ts.
     *
     * @param f         file predict_wf
     * @param cutoffMs  cutoff của fold (ms)
     * @param embargoMs khe embargo (ms)
     * @return thống kê fold
     * @throws IOException lỗi đọc (hạ tầng)
     */
    private static FoldStat scanFold(File f, long cutoffMs, long embargoMs) throws IOException {
        long len = f.length();
        if (len % REC != 0) {
            throw new IOException("B1: " + f.getName() + " kích thước " + len + " không chia hết " + REC);
        }
        FoldStat st = new FoldStat(f.getName(), cutoffMs);
        long embargoStart = cutoffMs - embargoMs;
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(new FileInputStream(f), 1 << 20))) {
            long nrec = len / REC;
            for (long i = 0; i < nrec; i++) {
                long ts = in.readLong();
                in.readShort();   // symId — không cần cho biên
                in.skipBytes(16); // 4 float p4h/p12h/p24h/p72h
                st.count++;
                if (ts < st.minTs) {
                    st.minTs = ts;
                }
                if (ts > st.maxTs) {
                    st.maxTs = ts;
                }
                if (ts < cutoffMs) {
                    st.oosBeforeCutoff++;
                    if (ts >= embargoStart) {
                        st.inEmbargoZone++;
                    }
                }
            }
        }
        return st;
    }

    /** Thống kê biên OOS của một fold predict_wf. */
    private static final class FoldStat {
        final String fileName;
        final long cutoffMs;
        long count = 0;
        long minTs = Long.MAX_VALUE;
        long maxTs = Long.MIN_VALUE;
        long oosBeforeCutoff = 0;
        long inEmbargoZone = 0;

        FoldStat(String fileName, long cutoffMs) {
            this.fileName = fileName;
            this.cutoffMs = cutoffMs;
        }
    }
}
