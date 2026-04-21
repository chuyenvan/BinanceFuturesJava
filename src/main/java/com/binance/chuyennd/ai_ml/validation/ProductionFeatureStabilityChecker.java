package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.lang.reflect.Field;
import java.util.*;

/**
 * Công cụ kiểm tra độ ổn định của Features trong Production.
 * Tìm các features không thay đổi theo thời gian (dấu hiệu lỗi logic/dữ liệu).
 */
public class ProductionFeatureStabilityChecker {
    private static final Logger LOG = LoggerFactory.getLogger(ProductionFeatureStabilityChecker.class);
    private static final String PROD_DIR = "storage/data/predict/";

    // Cấu hình số lượng file tối đa để kiểm tra (tránh quá tải)

    public static void main(String[] args) {
        new ProductionFeatureStabilityChecker().runCheck();
    }

    public void runCheck() {
        LOG.info("🚀 Starting Production Feature Stability Check...");

        List<File> featureFiles = collectFeatureFiles(PROD_DIR);
        if (featureFiles.isEmpty()) {
            LOG.error("❌ No feature files found in {}", PROD_DIR);
            return;
        }

        // Map lưu trữ: Tên Field -> Danh sách các giá trị thu thập được
        Map<String, List<Object>> featureHistory = new HashMap<>();
        int processedCount = 0;

        for (File file : featureFiles) {
            try {
                MarketFeatures feat = (MarketFeatures) StorageSnappy.readObjectFromFile(file.getPath());
                if (feat == null) continue;

                // Sử dụng Reflection để lấy tất cả các field
                for (Field field : MarketFeatures.class.getFields()) {
                    field.setAccessible(true);
                    String fieldName = field.getName();
                    Object value = field.get(feat);

                    featureHistory.computeIfAbsent(fieldName, k -> new ArrayList<>()).add(value);
                }

                processedCount++;


            } catch (Exception e) {
                LOG.error("Error reading file: {}", file.getName());
            }
        }

        analyzeStability(featureHistory, processedCount);
    }

    private void analyzeStability(Map<String, List<Object>> history, int totalSamples) {
        LOG.info("=== STABILITY REPORT (Samples: {}) ===", totalSamples);
        List<String> staticFeatures = new ArrayList<>();
        List<String> validFeatures = new ArrayList<>();

        for (Map.Entry<String, List<Object>> entry : history.entrySet()) {
            String fieldName = entry.getKey();
            List<Object> values = entry.getValue();

            if (values.isEmpty()) continue;

            // Kiểm tra xem tất cả các giá trị có giống nhau không
            boolean isStatic = true;
            Object firstValue = values.get(0);

            for (Object val : values) {
                if (!Objects.equals(val, firstValue)) {
                    isStatic = false;
                    break;
                }
            }

            if (isStatic) {
                staticFeatures.add(String.format("❌ STATIC: %-30s | Value: %s", fieldName, firstValue));
            } else {
                validFeatures.add(fieldName);
            }
        }

        // In kết quả
        if (!staticFeatures.isEmpty()) {
            LOG.warn("⚠️ FOUND {} STATIC FEATURES (POSSIBLE BUGS):", staticFeatures.size());
            staticFeatures.forEach(System.out::println);
        }

        LOG.info("✅ Valid Moving Features: {}", validFeatures.size());
        LOG.info("========================================");
    }

    private List<File> collectFeatureFiles(String path) {
        List<File> allFiles = new ArrayList<>();
        File root = new File(path);
        if (!root.exists() || !root.isDirectory()) return allFiles;

        // Quét thư mục theo ngày (YYYYMMDD)
        File[] dateDirs = root.listFiles(File::isDirectory);
        if (dateDirs != null) {
            // Sắp xếp ngày mới nhất lên trước
            Arrays.sort(dateDirs, Collections.reverseOrder());

            for (File dateDir : dateDirs) {
                File[] files = dateDir.listFiles((dir, name) -> name.endsWith(".features"));
                if (files != null) {
                    allFiles.addAll(Arrays.asList(files));
                }
            }
        }
        return allFiles;
    }
}