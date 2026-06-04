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
    private final String outputFile; // 1 file DUY NHẤT (append) để tiện đẩy Kaggle
    private int triggeredCollections = 0;

    public EnhancedTrainingDataCollectionManager(String outputPath) {
        this.featureExtractor = new ComprehensiveMarketFeatureExtractor();
        this.collectedFeatures = Collections.synchronizedList(new ArrayList<>());
        this.outputPath = outputPath;
        this.outputFile = outputPath + "/features_all.csv";
        new File(outputPath).mkdirs();

        // Tạo MỚI file (truncate) + ghi header 1 lần. Mỗi lần chạy lại export là làm sạch file.
        try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile, false))) {
            writer.println(new MarketFeatures().toCSVHeader());
        } catch (Exception e) {
            LOG.error("Init output file failed", e);
        }
    }

    public void clearBuffer() {
        collectedFeatures.clear();
    }

    /**
     * Nuôi ring history (LIÊN TỤC, mỗi phút) — phải gọi cho MỌI phút, KỂ CẢ phút không thu thập,
     * để RSI/MA/return/volatility (đếm theo SỐ NẾN) có cửa sổ đúng. Không gọi = ring thưa = indicator sai.
     */
    public void updateHistory(Map<String, KlineObjectSimple> snapshot) {
        featureExtractor.updateMarketHistory(snapshot);
    }

    /**
     * Nhận và gán 2 nhãn: Return 15m và Max Drawdown 4h (đã bỏ Return 24h).
     */
    public void processMarketData(long timestamp,
                                  Map<String, KlineObjectSimple> marketData,
                                  MarketDataObject marketRate,
                                  float ret15M, float maxDD4H) {

        if (!shouldCollectData(marketRate)) return;

        try {
            MarketFeatures features = featureExtractor.extractAllFeatures(timestamp, marketData, marketRate);

            // Gán 2 nhãn (khớp MarketFeatures mới)
            features.futureReturn15M = ret15M;
            features.maxDrawdownNext4H = maxDD4H;

            collectedFeatures.add(features);
            triggeredCollections++;

            if (triggeredCollections % 1000 == 0) {
                LOG.info("Collected {}. Label: 15M: {}% | DD4H: {}%",
                        triggeredCollections,
                        String.format("%.2f", ret15M * 100),
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
            // APPEND vào 1 file duy nhất (header đã ghi ở constructor).
            try (PrintWriter writer = new PrintWriter(new FileWriter(outputFile, true))) {
                for (MarketFeatures f : collectedFeatures) {
                    writer.println(f.toCSVRow());
                }
            }
            LOG.info("✅ Appended {} samples -> {}", collectedFeatures.size(), outputFile);
            collectedFeatures.clear();
        } catch (Exception e) {
            LOG.error("Export failed", e);
        }
    }

    public int getCollectedCount() {
        return triggeredCollections;
    }
}