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

    // 🔥 Thêm biến quản lý file ghi nối tiếp
    private final String singleFileName;
    private boolean isFirstWrite = true;

    public EnhancedTrainingDataCollectionManager15M(String outputPath) {
        this.featureExtractor = new ComprehensiveMarketFeatureExtractor15M();
        this.collectedFeatures = Collections.synchronizedList(new ArrayList<>());
        this.outputPath = outputPath;
        new File(outputPath).mkdirs();

        // 🔥 Định nghĩa đúng 1 file duy nhất
        this.singleFileName = outputPath + "/final_combined_market_15m.csv";

        // Xóa file cũ nếu đã tồn tại để tránh ghi đè lặp data
        File oldFile = new File(singleFileName);
        if (oldFile.exists()) {
            oldFile.delete();
        }
    }

    public void clearBuffer() {
        collectedFeatures.clear();
    }

    public void processMarketData(long timestamp,
                                  NavigableMap<Long, Map<Short, KlineObjectSimple>> historyWindow,
                                  MarketDataObject15M marketRate,
                                  List<Short> basket,
                                  float ret1H, float ret4H, float maxDD4H) {

        if (!shouldCollectData(marketRate)) return;

        try {
            Map<Short, KlineObjectSimple> currentMarketData = historyWindow.get(timestamp);
            if (currentMarketData == null) return;

            MarketFeatures15M features = featureExtractor.extractAllFeatures(timestamp, currentMarketData, marketRate, basket);

            if (features != null) {
                features.futureReturn1H = ret1H;
                features.futureReturn4H = ret4H;
                features.maxDrawdownNext4H = maxDD4H;

                collectedFeatures.add(features);
                triggeredCollections++;

                if (triggeredCollections % 1000 == 0) {
                    LOG.info("Collected {}. Label: 1H: {}% | 4H: {}% | DD4H: {}%",
                            triggeredCollections,
                            String.format("%.2f", ret1H * 100),
                            String.format("%.2f", ret4H * 100),
                            String.format("%.2f", maxDD4H * 100));
                }
            }

        } catch (Exception e) {
            LOG.error("Error processing data: {}", e.getMessage());
        }
    }

    private boolean shouldCollectData(MarketDataObject15M rate) {
        if (rate == null) return false;
        return Math.abs(rate.rateDown4HAvg) > 0.005f
                || Math.abs(rate.rateUpAvg) > 0.002f
                || rate.rateDownAvg < -0.005f;
    }

    // 🔥 GHI NỐI TIẾP VÀO 1 FILE DUY NHẤT
    public void exportCollectedData() {
        if (collectedFeatures.isEmpty()) return;
        try {
            // Tham số 'true' trong FileWriter để bật chế độ Append (Ghi nối thêm ở cuối)
            try (PrintWriter writer = new PrintWriter(new FileWriter(singleFileName, true))) {
                // Chỉ in Header ở lần ghi đầu tiên
                if (isFirstWrite) {
                    writer.println(collectedFeatures.get(0).toCSVHeader());
                    isFirstWrite = false;
                }

                for (MarketFeatures15M f : collectedFeatures) {
                    writer.println(f.toCSVRow());
                }
            }
            LOG.info("✅ Appended {} 15M samples. File size so far: {} bytes",
                    collectedFeatures.size(), new File(singleFileName).length());

            // Giải phóng RAM sau khi ghi xong
            collectedFeatures.clear();
        } catch (Exception e) {
            LOG.error("Export failed", e);
        }
    }

    public int getCollectedCount() {
        return triggeredCollections;
    }
}