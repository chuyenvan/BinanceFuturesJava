package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
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
import java.util.TreeMap;

/**
 * C1 — Chặn NaN/Inf trong feature/pred: đếm số ô NaN/Infinity mỗi cột feature phải = 0.
 *
 * <p>WRAP {@code ai_ml/validation/data/FeatureQualityAnalyzer} (cùng cách gom file {@code .features}
 * + reflection trên {@link MarketFeatures}), nhưng ĐỔI tiêu chí từ "đếm zero" sang "đếm NaN/Inf" theo
 * đúng spec §2 C1 ({@code DATA_VALIDATION_FRAMEWORK.md}). Mọi cột kiểu float/double được soi;
 * cột int/long/String bỏ qua (không thể NaN/Inf).</p>
 *
 * <p>Bài học nền: NaN/Inf lọt vào feature/label làm HPO/WFO cho ra SỐ SAI trông hợp lý (lỗi im lặng §5).
 * Vì vậy ngưỡng cứng: tổng NaN/Inf &gt; 0 = FAIL (BLOCK).</p>
 *
 * <p>Nguồn dữ liệu: thư mục feature cục bộ (đường dẫn {@link PreflightContext#wfoDataDir()} nếu có,
 * mặc định {@link #DEFAULT_FEATURE_DIR}). Chỉ ĐỌC. Đây là check RẺ (full-scan cột), chạy inline.</p>
 *
 * <p>TODO-verify: (1) xác nhận layout thư mục feature thật trên 226 (hiện mirror
 * {@code FeatureQualityAnalyzer}: {@code <dir>/<YYYYMMDD>/*.features}); (2) xác nhận pred (gate/selector)
 * cũng lưu dạng {@link MarketFeatures} hay format riêng — nếu format khác thì cần validator NaN/Inf riêng
 * cho pred (hiện mới phủ feature market-level).</p>
 */
public final class C1NanInfValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(C1NanInfValidator.class);

    /** Thư mục feature mặc định (mirror {@code FeatureQualityAnalyzer.PROD_DIR}). */
    private static final String DEFAULT_FEATURE_DIR = "storage/data/predict/";

    /** Đuôi file feature (mirror tool cũ). */
    private static final String FEATURE_SUFFIX = ".features";

    /** Trần số file quét (chống OOM khi lịch sử quá lớn) — mirror {@code FeatureQualityAnalyzer.MAX_FILES}. */
    private static final int MAX_FILES = 10_000;

    /** Số cột lỗi tối đa liệt kê trong message (tránh log phình). */
    private static final int MAX_LISTED_COLS = 20;

    @Override
    public CheckId id() {
        return CheckId.C1;
    }

    /**
     * Quét file feature, đếm NaN/Inf từng cột float/double.
     *
     * @param ctx ngữ cảnh (đọc {@link PreflightContext#wfoDataDir()} làm thư mục feature nếu có)
     * @return FAIL (BLOCK) nếu tổng NaN/Inf &gt; 0; PASS kèm metrics (số file, số cột, tổng NaN/Inf)
     * @throws IllegalStateException nếu thư mục feature không tồn tại (lỗi hạ tầng → gate xử NEEDS_HUMAN)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        String dir = ctx.wfoDataDir() != null && !ctx.wfoDataDir().trim().isEmpty()
                ? ctx.wfoDataDir() : DEFAULT_FEATURE_DIR;
        File root = new File(dir);
        if (!root.exists() || !root.isDirectory()) {
            throw new IllegalStateException("C1: thư mục feature không tồn tại: " + root.getAbsolutePath()
                    + " (lỗi hạ tầng — cấu hình sai đường dẫn feature).");
        }

        List<File> files = collectFeatureFiles(root);
        if (files.isEmpty()) {
            throw new IllegalStateException("C1: không tìm thấy file " + FEATURE_SUFFIX + " nào dưới "
                    + root.getAbsolutePath() + " (không thể đo — coi là NEEDS_HUMAN, KHÔNG suy PASS suông).");
        }

        // Chỉ soi các cột float/double (int/long/String không thể NaN/Inf).
        List<Field> numericFields = new ArrayList<>();
        for (Field f : MarketFeatures.class.getFields()) {
            Class<?> t = f.getType();
            if (t == float.class || t == double.class || t == Float.class || t == Double.class) {
                numericFields.add(f);
            }
        }

        Map<String, Long> nanInfPerCol = new TreeMap<>();
        long totalProcessed = 0;
        long totalReadErrors = 0;
        long totalNanInf = 0;

        for (File f : files) {
            MarketFeatures feat;
            try {
                Object obj = StorageSnappy.readObjectFromFile(f.getPath());
                if (!(obj instanceof MarketFeatures)) {
                    totalReadErrors++;
                    continue;
                }
                feat = (MarketFeatures) obj;
            } catch (Exception e) {
                // Lỗi ĐỌC 1 file = data corrupt, KHÔNG câm: đếm + log rồi tiếp (không làm gãy cả scan).
                totalReadErrors++;
                LOG.warn("C1: đọc lỗi file {}: {}", f.getName(), e.toString());
                continue;
            }
            totalProcessed++;
            for (Field field : numericFields) {
                double val;
                try {
                    Object v = field.get(feat);
                    if (v == null) {
                        continue;
                    }
                    val = ((Number) v).doubleValue();
                } catch (IllegalAccessException e) {
                    // Reflection lỗi cấu trúc code (không phải data) → hạ tầng.
                    throw new IllegalStateException("C1: không đọc được field " + field.getName(), e);
                }
                if (Double.isNaN(val) || Double.isInfinite(val)) {
                    nanInfPerCol.merge(field.getName(), 1L, Long::sum);
                    totalNanInf++;
                }
            }
        }

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("dir", root.getAbsolutePath());
        metrics.put("filesFound", (long) files.size());
        metrics.put("filesProcessed", totalProcessed);
        metrics.put("readErrors", totalReadErrors);
        metrics.put("numericColumns", (long) numericFields.size());
        metrics.put("totalNanInf", totalNanInf);
        metrics.put("columnsWithNanInf", (long) nanInfPerCol.size());
        // Đưa top cột lỗi vào metrics để đối chiếu (giữ gọn).
        int listed = 0;
        for (Map.Entry<String, Long> e : nanInfPerCol.entrySet()) {
            if (listed++ >= MAX_LISTED_COLS) {
                break;
            }
            metrics.put("col." + e.getKey(), e.getValue());
        }

        if (totalReadErrors > 0 && totalProcessed == 0) {
            // Đọc được 0 file hợp lệ dù có file → dữ liệu/hạ tầng hỏng, không tự PASS.
            throw new IllegalStateException("C1: " + totalReadErrors + " file lỗi đọc, 0 file hợp lệ dưới "
                    + root.getAbsolutePath() + " — NEEDS_HUMAN.");
        }
        if (totalNanInf > 0) {
            List<String> cols = new ArrayList<>(nanInfPerCol.keySet());
            return ValidationResult.fail(id(),
                    "Phát hiện " + totalNanInf + " ô NaN/Inf ở " + nanInfPerCol.size() + " cột: "
                            + cols.subList(0, Math.min(cols.size(), MAX_LISTED_COLS)), metrics);
        }
        return ValidationResult.pass(id(),
                "0 NaN/Inf trên " + totalProcessed + " file × " + numericFields.size() + " cột số"
                        + (totalReadErrors > 0 ? " (bỏ qua " + totalReadErrors + " file lỗi đọc)" : "") + ".",
                metrics);
    }

    /**
     * Gom file {@code .features} theo thư mục ngày (mới nhất trước), trần {@link #MAX_FILES}.
     * Mirror {@code FeatureQualityAnalyzer.collectFiles}.
     *
     * @param root thư mục gốc chứa các thư mục con dạng YYYYMMDD
     * @return danh sách file feature (có thể rỗng)
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
