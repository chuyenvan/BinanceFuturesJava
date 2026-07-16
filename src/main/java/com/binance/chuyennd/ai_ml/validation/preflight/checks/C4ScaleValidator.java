package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.ExpectedRanges;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.utils.StorageSnappy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * C4 — Chặn SCALE SAI (vd 0.03 vs 3%): min/max/median mỗi feature phải nằm trong khoảng pre-register
 * {@link ExpectedRanges#feature(String)}. Mức WARN ({@code DATA_VALIDATION_FRAMEWORK.md} §2/§4b).
 *
 * <p>WRAP {@code ai_ml/validation/data/ProductionFeatureStabilityChecker} (cùng cách gom file
 * {@code .features} + reflection gom lịch sử giá trị từng field), nhưng ĐỔI phân tích từ
 * "phát hiện feature tĩnh" sang "so min/max/median với bound khai báo trước". Chỉ ĐỌC.</p>
 *
 * <p>Nguyên tắc "đo không đoán": KHÔNG hard-code magic number; bound đến từ
 * {@link ExpectedRanges} (nạp ngoài từ {@code validate_criteria.md} — việc nạp là task riêng).
 * Feature CHƯA khai báo bound → BỎ QUA + đếm (không võ đoán ngưỡng). Nếu KHÔNG feature nào có bound
 * → trả WARN "chưa pre-register" (không thể đo scale).</p>
 *
 * <p>Đây là check ĐẮT ({@link CheckId#C4} expensive=true) — theo §3 nên chạy random-sample phân tầng.
 * Bản này lấy tối đa {@link #MAX_FILES} file mới nhất làm mẫu (mirror tool cũ).</p>
 *
 * <p>TODO-verify: (1) thay lấy-N-file-mới-nhất bằng sample phân tầng (tháng × tier) theo §4b Q2;
 * (2) xác nhận đơn vị mỗi feature khi nạp bound (rate ở dạng thập phân hay %) — chính là lỗi C4 muốn bắt.</p>
 */
public final class C4ScaleValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(C4ScaleValidator.class);

    private static final String DEFAULT_FEATURE_DIR = "storage/data/predict/";
    private static final String FEATURE_SUFFIX = ".features";
    private static final int MAX_FILES = 10_000;

    @Override
    public CheckId id() {
        return CheckId.C4;
    }

    /**
     * Gom giá trị từng feature số, tính min/max/median, so với bound pre-register.
     *
     * @param ctx ngữ cảnh (thư mục feature + {@link PreflightContext#expected()})
     * @return WARN nếu có feature lệch bound HOẶC chưa khai báo bound nào; PASS nếu mọi feature-có-bound đều trong khoảng
     * @throws IllegalStateException nếu thư mục feature không tồn tại / không đọc được file nào (NEEDS_HUMAN)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        String dir = ctx.wfoDataDir() != null && !ctx.wfoDataDir().trim().isEmpty()
                ? ctx.wfoDataDir() : DEFAULT_FEATURE_DIR;
        File root = new File(dir);
        if (!root.exists() || !root.isDirectory()) {
            throw new IllegalStateException("C4: thư mục feature không tồn tại: " + root.getAbsolutePath());
        }
        List<File> files = collectFeatureFiles(root);
        if (files.isEmpty()) {
            throw new IllegalStateException("C4: không có file " + FEATURE_SUFFIX + " dưới " + root.getAbsolutePath());
        }

        List<Field> numericFields = new ArrayList<>();
        for (Field f : MarketFeatures.class.getFields()) {
            Class<?> t = f.getType();
            if (t == float.class || t == double.class || t == Float.class || t == Double.class) {
                numericFields.add(f);
            }
        }

        // Gom lịch sử giá trị mỗi field (bỏ NaN/Inf — C1 phụ trách NaN/Inf, ở đây tránh làm hỏng min/max/median).
        Map<String, List<Double>> history = new LinkedHashMap<>();
        for (Field f : numericFields) {
            history.put(f.getName(), new ArrayList<>());
        }
        long processed = 0;
        long readErrors = 0;
        for (File file : files) {
            MarketFeatures feat;
            try {
                Object obj = StorageSnappy.readObjectFromFile(file.getPath());
                if (!(obj instanceof MarketFeatures)) {
                    readErrors++;
                    continue;
                }
                feat = (MarketFeatures) obj;
            } catch (Exception e) {
                readErrors++;
                LOG.warn("C4: đọc lỗi file {}: {}", file.getName(), e.toString());
                continue;
            }
            processed++;
            for (Field field : numericFields) {
                try {
                    Object v = field.get(feat);
                    if (v == null) {
                        continue;
                    }
                    double d = ((Number) v).doubleValue();
                    if (!Double.isNaN(d) && !Double.isInfinite(d)) {
                        history.get(field.getName()).add(d);
                    }
                } catch (IllegalAccessException e) {
                    throw new IllegalStateException("C4: không đọc được field " + field.getName(), e);
                }
            }
        }
        if (processed == 0) {
            throw new IllegalStateException("C4: 0 file hợp lệ (" + readErrors + " lỗi đọc) dưới "
                    + root.getAbsolutePath() + " — NEEDS_HUMAN.");
        }

        ExpectedRanges expected = ctx.expected();
        List<String> violations = new ArrayList<>();
        long featuresWithBound = 0;
        long featuresNoBound = 0;
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("dir", root.getAbsolutePath());
        metrics.put("filesProcessed", processed);
        metrics.put("readErrors", readErrors);

        for (Map.Entry<String, List<Double>> e : history.entrySet()) {
            String name = e.getKey();
            List<Double> values = e.getValue();
            if (values.isEmpty()) {
                continue;
            }
            ExpectedRanges.FeatureBound bound = expected.feature(name);
            if (bound == null) {
                featuresNoBound++;
                continue; // chưa khai báo → không võ đoán
            }
            featuresWithBound++;
            Collections.sort(values);
            double min = values.get(0);
            double max = values.get(values.size() - 1);
            double median = median(values);
            metrics.put("min." + name, min);
            metrics.put("max." + name, max);
            metrics.put("median." + name, median);
            // Lệch scale: min/max/median rơi ngoài [bound.min, bound.max].
            if (min < bound.min || max > bound.max
                    || median < bound.min || median > bound.max) {
                violations.add(String.format("%s: min=%.6g max=%.6g median=%.6g NGOÀI [%.6g, %.6g]",
                        name, min, max, median, bound.min, bound.max));
            }
        }
        metrics.put("featuresWithBound", featuresWithBound);
        metrics.put("featuresNoBound", featuresNoBound);
        metrics.put("violations", (long) violations.size());

        if (featuresWithBound == 0) {
            return ValidationResult.warn(id(),
                    "Chưa pre-register bound feature nào (ExpectedRanges rỗng) → KHÔNG đo được scale. "
                            + "TODO: nạp validate_criteria.md.", metrics);
        }
        if (!violations.isEmpty()) {
            return ValidationResult.warn(id(),
                    "Nghi SCALE SAI ở " + violations.size() + "/" + featuresWithBound + " feature: " + violations,
                    metrics);
        }
        return ValidationResult.pass(id(),
                "Scale OK: " + featuresWithBound + " feature-có-bound đều trong khoảng (bỏ qua "
                        + featuresNoBound + " feature chưa khai báo).", metrics);
    }

    /**
     * Median của list ĐÃ SẮP XẾP tăng dần.
     *
     * @param sorted list đã sort (không rỗng)
     * @return trung vị
     */
    private static double median(List<Double> sorted) {
        int n = sorted.size();
        if (n % 2 == 1) {
            return sorted.get(n / 2);
        }
        return (sorted.get(n / 2 - 1) + sorted.get(n / 2)) / 2.0;
    }

    /**
     * Gom file {@code .features} (mới nhất trước), trần {@link #MAX_FILES}.
     *
     * @param root thư mục gốc chứa thư mục con YYYYMMDD
     * @return danh sách file (có thể rỗng)
     */
    private List<File> collectFeatureFiles(File root) {
        List<File> all = new ArrayList<>();
        File[] dateDirs = root.listFiles(File::isDirectory);
        if (dateDirs == null) {
            return all;
        }
        Arrays.sort(dateDirs, Collections.reverseOrder());
        for (File d : dateDirs) {
            File[] fs = d.listFiles((dir, name) -> name.endsWith(FEATURE_SUFFIX));
            if (fs != null) {
                all.addAll(Arrays.asList(fs));
            }
            if (all.size() >= MAX_FILES) {
                break;
            }
        }
        return all;
    }
}
