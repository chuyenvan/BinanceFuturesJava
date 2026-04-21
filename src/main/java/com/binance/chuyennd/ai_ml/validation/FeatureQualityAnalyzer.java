package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.utils.StorageSnappy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.lang.reflect.Field;
import java.util.*;

public class FeatureQualityAnalyzer {
    private static final Logger LOG = LoggerFactory.getLogger(FeatureQualityAnalyzer.class);
    private static final String PROD_DIR = "storage/data/predict/";
    private static final int MAX_FILES = 10000; // Tăng số lượng file để thống kê chính xác hơn

    public static void main(String[] args) {
        new FeatureQualityAnalyzer().analyzeZeroValues();
    }

    public void analyzeZeroValues() {
        List<File> files = collectFiles(PROD_DIR);
        if (files.isEmpty()) return;

        Map<String, Integer> zeroCounts = new HashMap<>();
        int totalProcessed = 0;

        for (File f : files) {
            try {
                MarketFeatures feat = (MarketFeatures) StorageSnappy.readObjectFromFile(f.getPath());
                if (feat == null) continue;

                for (Field field : MarketFeatures.class.getFields()) {
                    String name = field.getName();
                    Object val = field.get(feat);

                    // Kiểm tra nếu giá trị là 0.0 hoặc 0
                    if (isZero(val)) {
                        zeroCounts.put(name, zeroCounts.getOrDefault(name, 0) + 1);
                    }
                }
                totalProcessed++;
            } catch (Exception e) {
                LOG.error("Error reading {}", f.getName());
            }
        }

        printReport(zeroCounts, totalProcessed);
    }

    private boolean isZero(Object val) {
        if (val == null) return true;
        if (val instanceof Number) {
            return ((Number) val).doubleValue() == 0.0;
        }
        return false;
    }

    private void printReport(Map<String, Integer> counts, int total) {
        System.out.println("\n=== FEATURE ZERO-VALUE REPORT ===");
        System.out.println(String.format("%-25s | %-10s | %-10s", "Feature Name", "Zero Count", "Zero Rate"));
        System.out.println("-----------------------------------------------------------");

        // Sắp xếp theo số lượng zero giảm dần
        counts.entrySet().stream()
                .sorted((a, b) -> b.getValue().compareTo(a.getValue()))
                .forEach(e -> {
                    float rate = (float) e.getValue() / total * 100;
                    System.out.println(String.format("%-25s | %-10d | %.2f%%",
                            e.getKey(), e.getValue(), rate));
                });
        System.out.println("Total Samples Processed: " + total);
    }

    private List<File> collectFiles(String path) {
        List<File> all = new ArrayList<>();
        File root = new File(path);
        File[] dates = root.listFiles(File::isDirectory);
        if (dates != null) {
            Arrays.sort(dates, Collections.reverseOrder());
            for (File d : dates) {
                File[] fs = d.listFiles((dir, name) -> name.endsWith(".features"));
                if (fs != null) all.addAll(Arrays.asList(fs));
                if (all.size() >= MAX_FILES) break;
            }
        }
        return all;
    }
}