package com.binance.chuyennd.ai_ml.features.export.entry;

import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.util.*;

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

    // Thêm vào class EnhancedTrainingDataCollectionManager
    public void clearBuffer() {
        collectedFeatures.clear();
        // LOG.info("Buffer cleared (Warm-up complete)");
    }
    public List<String> identifyTargetBasket(long timestamp, Map<String, KlineObjectSimple> marketData) {
        // 1. Cập nhật History trước
        featureExtractor.updateMarketHistory(marketData);
        // 2. Lấy danh sách từ logic nội tại của Extractor
        return featureExtractor.findPotentialLosers(timestamp);
    }
    public void processMarketData(long timestamp,
                                  Map<String, KlineObjectSimple> marketData,
                                  MarketRateChange marketRateChange, List<String> targetBasket,
                                  double ret15M, double ret1H, double ret4H, double ret24H,
                                  double maxDD4H, double maxDD24H) {

        if (!shouldCollectData(marketRateChange)) return;

        try {
            MarketFeatures features = featureExtractor.extractAllFeatures(timestamp, marketData, marketRateChange, targetBasket);

            // Gán Labels (Output)
            features.futureReturn15M = ret15M;
            features.futureReturn1H = ret1H;
            features.futureReturn4H = ret4H;
            features.futureReturn24H = ret24H;

            features.maxDrawdownNext4H = maxDD4H;
            features.maxDrawdownNext24H = maxDD24H; // Đã gán vào Object để ghi CSV

            // Gán nhãn tham khảo
            assignRegimeLabel(features, ret15M, ret1H, ret4H, maxDD4H);

            collectedFeatures.add(features);
            triggeredCollections++;

            if (triggeredCollections % 1000 == 0) {
                LOG.info("Collected {}. Label: {} | 15M: {}% | DD24H: {}%",
                        triggeredCollections, features.regimeLabel,
                        String.format("%.2f", ret15M * 100),
                        String.format("%.2f", maxDD24H * 100));
            }

        } catch (Exception e) {
            LOG.error("Error processing data: {}", e.getMessage());
        }
    }

    // ... (Các hàm private khác giữ nguyên như cũ) ...
    private void assignRegimeLabel(MarketFeatures f, double r15m, double r1h, double r4h, double dd4h) {
        if (r15m > 0.008 && dd4h > -0.03) f.regimeLabel = "SCALP_WIN";
        else if (r4h > 0.01 && r1h < 0.0) f.regimeLabel = "BUY_DIP";
        else if (r4h < -0.02 && r1h < -0.01) f.regimeLabel = "CATCH_BOTTOM";
        else if (dd4h < -0.05) f.regimeLabel = "DONT_CATCH";
        else f.regimeLabel = "WAIT";
    }

    private boolean shouldCollectData(MarketRateChange rate) {
        if (rate == null) return false;
        return Math.abs(rate.rateDown15MAvg) > 0.002 || Math.abs(rate.rateUpAvg) > 0.002;
    }

    public void exportCollectedData() {
        if (collectedFeatures.isEmpty()) return;
        try {
            String filename = outputPath + "/features_" + System.currentTimeMillis() + ".csv";
            try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
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