package com.binance.chuyennd.ai_ml.onnx.funding;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

/**
 * TASK-109 bước 4 — Validate Java SelectorOnnxInferenceManager == Python Booster.
 * Đọc cùng file vector (45 feat × N) mà Python đã predict, chạy ONNX Java, in P(win) 4 horizon.
 * So tay với D:/claudedata/sel_validate_python.json (Python ref). Mục tiêu diff ~0.
 *
 * Chạy: java -cp <jar> com.binance.chuyennd.ai_ml.onnx.funding.SelectorValidateTool <modelDir> <vectorsCsv>
 */
public class SelectorValidateTool {
    private static final Logger LOG = LoggerFactory.getLogger(SelectorValidateTool.class);

    public static void main(String[] args) throws Exception {
        String modelDir = args.length > 0 ? args[0] : "ml/funding_selector/models_v1";
        String vectorsCsv = args.length > 1 ? args[1] : "sel_validate_vectors.csv";

        List<float[]> batch = new ArrayList<>();
        for (String line : Files.readAllLines(Paths.get(vectorsCsv))) {
            if (line.isBlank()) continue;
            String[] p = line.split(",");
            float[] x = new float[p.length];
            for (int i = 0; i < p.length; i++) x[i] = Float.parseFloat(p[i].trim());
            batch.add(x);
        }
        LOG.info("Đọc {} vector × {} feat từ {}", batch.size(), batch.get(0).length, vectorsCsv);

        try (SelectorOnnxInferenceManager mgr = new SelectorOnnxInferenceManager(modelDir)) {
            float[][] out = mgr.predictAll4(batch);   // [N][4] theo HORIZONS 4h/12h/24h/72h
            for (int h = 0; h < SelectorOnnxInferenceManager.HORIZONS.length; h++) {
                StringBuilder sb = new StringBuilder();
                for (int i = 0; i < Math.min(3, out.length); i++) {
                    if (i > 0) sb.append(", ");
                    sb.append(String.format("%.6f", out[i][h]));
                }
                LOG.info("Java {} first3: [{}]", SelectorOnnxInferenceManager.HORIZONS[h], sb);
            }
            // in full để so script ngoài nếu cần
            StringBuilder full = new StringBuilder("JAVA_FULL ");
            for (int h = 0; h < 4; h++) {
                full.append(SelectorOnnxInferenceManager.HORIZONS[h]).append("=[");
                for (int i = 0; i < out.length; i++) {
                    if (i > 0) full.append(",");
                    full.append(String.format("%.6f", out[i][h]));
                }
                full.append("] ");
            }
            LOG.info(full.toString());
        }
        System.exit(0);
    }
}
