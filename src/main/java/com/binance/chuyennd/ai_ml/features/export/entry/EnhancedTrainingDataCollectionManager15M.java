package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.NavigableMap;

public class EnhancedTrainingDataCollectionManager15M {
    private static final Logger LOG = LoggerFactory.getLogger(EnhancedTrainingDataCollectionManager15M.class);
    private final ComprehensiveMarketFeatureExtractor15M featureExtractor;
    private final List<MarketFeatures15M> collectedFeatures;
    private final String outputPath;
    private int triggeredCollections = 0;

    public EnhancedTrainingDataCollectionManager15M(String outputPath) {
        this.featureExtractor = new ComprehensiveMarketFeatureExtractor15M();
        this.collectedFeatures = Collections.synchronizedList(new ArrayList<>());
        this.outputPath = outputPath;
        new File(outputPath).mkdirs();
    }

    public void clearBuffer() {
        collectedFeatures.clear();
    }

    /**
     * 🔥 Xử lý Market Data với đầu vào là mảng Short (O(1)).
     */
    public void processMarketData(long timestamp,
                                  NavigableMap<Long, Map<Short, KlineObjectSimple>> historyWindow,
                                  MarketDataObject15M marketRate,
                                  List<Short> basket,
                                  float ret4H, float ret24H, float maxDD12H) {

        if (!shouldCollectData(marketRate)) return;

        try {
            // Lấy snapshot của cây nến hiện tại
            Map<Short, KlineObjectSimple> currentMarketData = historyWindow.get(timestamp);
            if (currentMarketData == null) return;

            // Gọi Extractor xử lý (Tất cả đều thuần Short)
            MarketFeatures15M features = featureExtractor.extractAllFeatures(timestamp, currentMarketData, marketRate, basket);

            if (features != null) {
                // 🔥 Gán 3 nhãn hệ 15M
                features.futureReturn4H = ret4H;
                features.futureReturn24H = ret24H;
                features.maxDrawdownNext12H = maxDD12H;

                collectedFeatures.add(features);
                triggeredCollections++;

                if (triggeredCollections % 1000 == 0) {
                    LOG.info("Collected {}. Label: 4H: {}% | 24H: {}% | DD12H: {}%",
                            triggeredCollections,
                            String.format("%.2f", ret4H * 100),
                            String.format("%.2f", ret24H * 100),
                            String.format("%.2f", maxDD12H * 100));
                }
            }

        } catch (Exception e) {
            LOG.error("Error processing data: {}", e.getMessage());
        }
    }

    /**
     * 🚀 ĐIỀU CHỈNH BỘ LỌC DATA TRAIN CHO NẾN 15M
     * Bỏ qua các giai đoạn Sideway đi ngang. Chỉ thu thập mẫu khi có biến động.
     */
    private boolean shouldCollectData(MarketDataObject15M rate) {
        if (rate == null) return false;

        // Đã đổi từ rateDown15MAvg (Hệ cũ) sang rateDown4HAvg (Hệ mới)
        return Math.abs(rate.rateDown4HAvg) > 0.005f  // Trong 4H vừa qua giật quá 0.5%
                || Math.abs(rate.rateUpAvg) > 0.002f
                || rate.rateDownAvg < -0.005f;
    }

    public void exportCollectedData() {
        if (collectedFeatures.isEmpty()) return;
        try {
            String filename = outputPath + "/features_15m_" + System.currentTimeMillis() + ".csv";
            try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
                writer.println(collectedFeatures.get(0).toCSVHeader());
                for (MarketFeatures15M f : collectedFeatures) {
                    writer.println(f.toCSVRow());
                }
            }
            LOG.info("✅ Exported {} 15M samples.", collectedFeatures.size());
            collectedFeatures.clear();
        } catch (Exception e) {
            LOG.error("Export failed", e);
        }
    }

    public int getCollectedCount() {
        return triggeredCollections;
    }
}