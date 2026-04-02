package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.DataManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class TraceDynamicThresholdTool {
    private static final Logger LOG = LoggerFactory.getLogger(TraceDynamicThresholdTool.class);

    public static void main(String[] args) {
        LOG.info("🚀 BẮT ĐẦU TRACE DỮ LIỆU ĐỂ TÌM HỆ SỐ DYNAMIC (K_DOWN, K_UP)...");

        try {
            // Load Data từ Aerospike vào RAM (Sử dụng DataManager chuẩn của bạn)
            Configs.TIME_RUN = "20210101"; // Trace từ quá khứ xa để có đủ mẫu
            TreeMap<Long, MarketDataObject> time2MarketData = DataManager.getMarketData();
            TreeMap<Long, AiPredictionData> predictionMap = DataManager.getAiPredictionData();

            if (time2MarketData == null || predictionMap == null) {
                LOG.error("❌ Không load được dữ liệu từ DataManager!");
                return;
            }

            LOG.info("✅ Đã nạp {} records Market Data và {} records AI Pred.", time2MarketData.size(), predictionMap.size());

            List<Float> allPred15M = new ArrayList<>();
            List<Float> kDownSamples = new ArrayList<>();
            List<Float> kUpSamples = new ArrayList<>();

            // Quét dữ liệu đồng bộ theo thời gian
            for (Map.Entry<Long, AiPredictionData> entry : predictionMap.entrySet()) {
                long time = entry.getKey();
                AiPredictionData pred = entry.getValue();
                MarketDataObject market = time2MarketData.get(time);

                if (pred == null || market == null) continue;

                // 1. Thu thập độ lớn tuyệt đối của predReturn15M
                float absPred = Math.abs(pred.predReturn15M);
                allPred15M.add(absPred);

                // 2. Chỉ tính K khi AI dự báo có biến động rõ ràng (> 0.5%) để tránh lỗi chia số quá nhỏ (nhiễu)
                if (absPred > 0.005f) {

                    // MÔ PHỎNG CHIỀU DOWN: Chỉ xét khi thị trường thực sự giảm (Avg < -1%)
                    if (market.rateDownAvg < -0.01f) {
                        // K = Độ lớn Market / Độ lớn Predict
                        float k_down = Math.abs(market.rateDownAvg) / absPred;
                        kDownSamples.add(k_down);
                    }

                    // MÔ PHỎNG CHIỀU UP: Chỉ xét khi thị trường thực sự tăng (Avg > 1%)
                    if (market.rateUpAvg > 0.01f) {
                        float k_up = Math.abs(market.rateUpAvg) / absPred;
                        kUpSamples.add(k_up);
                    }
                }
            }

            // In Báo Cáo
            printReport("1. ĐỘ LỚN VOLATILITY CỦA AI (Math.abs(predReturn15M))", allPred15M);
            printReport("2. HỆ SỐ K_DOWN (Thị trường sập)", kDownSamples);
            printReport("3. HỆ SỐ K_UP (Thị trường bơm)", kUpSamples);

            LOG.info("\n=======================================================");
            LOG.info("🎯 KẾT LUẬN & GỢI Ý CHO HPO (Jenetics)");
            LOG.info("Dựa vào P10 (Min) và P90 (Max) của K_DOWN và K_UP ở trên, bạn hãy set:");
            LOG.info("DoubleChromosome.of(DoubleRange.of( [P10_của_K_DOWN], [P90_của_K_DOWN] )) // Cho k_down");
            LOG.info("DoubleChromosome.of(DoubleRange.of( [P10_của_K_UP], [P90_của_K_UP] ))     // Cho k_up");
            LOG.info("=======================================================");

        } catch (Exception e) {
            LOG.error("Lỗi khi Trace Data: ", e);
        }
    }

    // Hàm tiện ích để in thống kê phân phối (Percentile)
    private static void printReport(String title, List<Float> data) {
        if (data.isEmpty()) {
            LOG.warn("\n=== {} ===", title);
            LOG.warn("Không có đủ mẫu dữ liệu thỏa mãn điều kiện!");
            return;
        }

        Collections.sort(data);
        int size = data.size();

        float min = data.get(0);
        float max = data.get(size - 1);
        float p10 = data.get((int) (size * 0.10));
        float p50 = data.get((int) (size * 0.50)); // Median
        float p90 = data.get((int) (size * 0.90));
        float p99 = data.get((int) (size * 0.99));

        double sum = 0;
        for (float f : data) sum += f;
        float avg = (float) (sum / size);

        LOG.info("\n=== {} (Tổng mẫu: {}) ===", title, size);
        LOG.info("  - Trung bình (Mean): {}", String.format("%.4f", avg));
        LOG.info("  - Trung vị (P50)   : {}", String.format("%.4f", p50));
        LOG.info("  - Vùng phủ 80% (P10 -> P90): [ {}  ->  {} ] << DÙNG KHOẢNG NÀY CHO HPO",
                String.format("%.4f", p10), String.format("%.4f", p90));
        LOG.info("  - Đỉnh điểm (P99)  : {}", String.format("%.4f", p99));
    }
}