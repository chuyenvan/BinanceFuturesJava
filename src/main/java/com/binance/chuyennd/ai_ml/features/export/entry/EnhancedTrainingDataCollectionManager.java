package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.object.MarketDataObject;
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

public class EnhancedTrainingDataCollectionManager {
    private static final Logger LOG = LoggerFactory.getLogger(EnhancedTrainingDataCollectionManager.class);
    private final ComprehensiveMarketFeatureExtractor featureExtractor;
    private final List<MarketFeatures> collectedFeatures;
    private final String outputPath;
    private int triggeredCollections = 0;

    public EnhancedTrainingDataCollectionManager(String outputPath) {
        this.featureExtractor = new ComprehensiveMarketFeatureExtractor();
        this.collectedFeatures = Collections.synchronizedList(new ArrayList<>());
        this.outputPath = outputPath;
        new File(outputPath).mkdirs();
    }

    public void clearBuffer() {
        collectedFeatures.clear();
    }

    /**
     * Chỉ nhận và gán 3 nhãn quan trọng: Return 15m, Return 24h và Max Drawdown 4h
     */
    public void processMarketData(long timestamp,
                                  Map<String, KlineObjectSimple> marketData,
                                  MarketDataObject marketRate,
                                  float ret15M, float ret24H, float maxDD4H) {

        if (!shouldCollectData(marketRate)) return;

        try {
            MarketFeatures features = featureExtractor.extractAllFeatures(timestamp, marketData, marketRate);

            // 🔥 Gán 3 nhãn duy nhất (Khớp với MarketFeatures mới)
            features.futureReturn15M = ret15M;
            features.futureReturn24H = ret24H;
            features.maxDrawdownNext4H = maxDD4H;

            collectedFeatures.add(features);
            triggeredCollections++;

            if (triggeredCollections % 1000 == 0) {
                // Log thông tin 3 nhãn để bác theo dõi tiến độ
                LOG.info("Collected {}. Label: 15M: {}% | 24H: {}% | DD4H: {}%",
                        triggeredCollections,
                        String.format("%.2f", ret15M * 100),
                        String.format("%.2f", ret24H * 100),
                        String.format("%.2f", maxDD4H * 100));
            }

        } catch (Exception e) {
            LOG.error("Error processing data: {}", e.getMessage());
        }
    }

    /**
     * Giữ nguyên logic lọc điểm dữ liệu có biến động mạnh để train hiệu quả hơn
     */
    private boolean shouldCollectData(MarketDataObject rate) {
        if (rate == null) return false;
        return Math.abs(rate.rateDown15MAvg) > 0.0018
                || Math.abs(rate.rateUpAvg) > 0.002
                || rate.rateDownAvg < -0.005;
    }

    public void exportCollectedData() {
        if (collectedFeatures.isEmpty()) return;
        try {
            String filename = outputPath + "/features_" + System.currentTimeMillis() + ".csv";
            try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
                // Header và Row lúc này chỉ chứa 3 cột label cuối cùng
                writer.println(collectedFeatures.get(0).toCSVHeader());
                for (MarketFeatures f : collectedFeatures) {
                    writer.println(f.toCSVRow());
                }
            }
            LOG.info("✅ Exported {} samples.", collectedFeatures.size());
            collectedFeatures.clear();
        } catch (Exception e) {
            LOG.error("Export failed", e);
        }
    }

    public int getCollectedCount() {
        return triggeredCollections;
    }
}