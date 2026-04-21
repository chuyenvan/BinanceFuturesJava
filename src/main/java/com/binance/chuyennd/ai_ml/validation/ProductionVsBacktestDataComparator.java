package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.OnnxInferenceManager;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.*;

/**
 * Công cụ Đối soát Dữ liệu (Data Reconciliation Tool).
 * So sánh giá trị dự đoán AI sinh ra lúc Live (ghi ở Local File)
 * với giá trị mà Backtest đang dùng (lấy từ Aerospike).
 */
public class ProductionVsBacktestDataComparator {
    private static final Logger LOG = LoggerFactory.getLogger(ProductionVsBacktestDataComparator.class);

    // Thư mục mà Bot Live ghi log
    private static final String PROD_PREDICT_DIR = "storage/data/prediction/";

    public static void main(String[] args) {
        new ProductionVsBacktestDataComparator().runCompare();
    }

    public void runCompare() {
        LOG.info("🚀 Đang khởi động tiến trình đối soát Live vs Backtest...");

        List<File> predictFiles = collectPredictionFiles(PROD_PREDICT_DIR);
        if (predictFiles.isEmpty()) {
            LOG.error("❌ Không tìm thấy file log Production nào tại {}", PROD_PREDICT_DIR);
            return;
        }

        int matchCount = 0;
        int mismatchCount = 0;
        int missingInAerospike = 0;

        // List chứa các mẫu log để in random
        List<String> sampleLogs = new ArrayList<>();

        for (File file : predictFiles) {
            try {
                long timestamp = Long.parseLong(file.getName());

                OnnxInferenceManager.PredictionResult prodData =
                        (OnnxInferenceManager.PredictionResult) StorageSnappy.readObjectFromFile(file.getPath());

                if (prodData == null) continue;

                AiPredictionData backtestData = DataManagerAerospikeFloatSim.getAiPredictionMarketAtTime(timestamp);

                if (backtestData == null) {
                    missingInAerospike++;
                    continue;
                }

                // Lưu lại log mẫu để lát nữa in random (In chi tiết cả 3 biến)
                String sample = String.format("Time: %s | PROD [15M:%8.5f, 24H:%8.5f, Risk4H:%8.5f] vs BT [15M:%8.5f, 24H:%8.5f, Risk4H:%8.5f]",
                        Utils.normalizeDateYYYYMMDDHHmm(timestamp),
                        prodData.return15M, prodData.return24H, prodData.riskDrawdown4H,
                        backtestData.predReturn15M, backtestData.predReturn24H, backtestData.predRisk4H);
                sampleLogs.add(sample);

                boolean isMatch = compareData(prodData, backtestData, timestamp);

                if (isMatch) {
                    matchCount++;
                } else {
                    mismatchCount++;
                }

            } catch (NumberFormatException e) {
                // Bỏ qua các file không phải là số
            } catch (Exception e) {
                LOG.error("Lỗi khi đọc file: {}", file.getName(), e);
            }
        }

        // ==========================================
        // IN RANDOM 10 MẪU ĐỂ NGƯỜI DÙNG TỰ KIỂM CHỨNG
        // ==========================================
        LOG.info("\n==========================================");
        LOG.info("=== 🔍 KIỂM TRA CHÉO 10 MẪU NGẪU NHIÊN ===");
        if (!sampleLogs.isEmpty()) {
            Collections.shuffle(sampleLogs); // Xáo trộn danh sách
            int limit = Math.min(10, sampleLogs.size());
            for (int i = 0; i < limit; i++) {
                LOG.info("Mẫu {}: {}", i + 1, sampleLogs.get(i));
            }
        }
        LOG.info("==========================================\n");

        LOG.info("=== BÁO CÁO ĐỐI SOÁT (RECONCILIATION) ===");
        LOG.info("✅ Khớp hoàn hảo (Perfect Match) : {}", matchCount);
        LOG.info("❌ Bị lệch pha (Mismatched)      : {}", mismatchCount);
        LOG.info("⚠️ Không có trong DB Aerospike   : {}", missingInAerospike);
        LOG.info("==========================================");

        if (mismatchCount == 0 && missingInAerospike == 0) {
            LOG.info("🎉 TUYỆT VỜI! Dữ liệu Production và Backtest đồng bộ 100%.");
        }
    }

    private boolean compareData(OnnxInferenceManager.PredictionResult prod, AiPredictionData backtest, long time) {
        float epsilon = 0.00001f;
        boolean isMatch = true;

        if (Math.abs(prod.return15M - backtest.predReturn15M) > epsilon) isMatch = false;
        if (Math.abs(prod.return24H - backtest.predReturn24H) > epsilon) isMatch = false;
        if (Math.abs(prod.riskDrawdown4H - backtest.predRisk4H) > epsilon) isMatch = false;

        return isMatch;
    }

    private List<File> collectPredictionFiles(String path) {
        List<File> allFiles = new ArrayList<>();
        File root = new File(path);
        if (!root.exists() || !root.isDirectory()) return allFiles;

        File[] dateDirs = root.listFiles(File::isDirectory);
        if (dateDirs != null) {
            for (File dateDir : dateDirs) {
                File[] files = dateDir.listFiles((dir, name) -> !name.endsWith(".features"));
                if (files != null) {
                    allFiles.addAll(Arrays.asList(files));
                }
            }
        }
        return allFiles;
    }
}