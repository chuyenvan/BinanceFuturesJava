package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.*;

public class DcaDataCollectionManager {
    private static final Logger LOG = LoggerFactory.getLogger(DcaDataCollectionManager.class);
    private final DcaFeatureExtractor featureExtractor;
    private final List<DcaMarketFeatures> buffer;
    private final String outputPath;
    private int collectedCount = 0;
    private final Random rand = new Random();

    public DcaDataCollectionManager(String outputPath) {
        this.featureExtractor = new DcaFeatureExtractor();
        this.buffer = Collections.synchronizedList(new ArrayList<>());
        this.outputPath = outputPath;
        new File(outputPath).mkdirs();
    }

    public void updateHistory(Map<String, KlineObjectSimple> marketData) {
        featureExtractor.updateMarketHistory(marketData);
    }

    public void processSimulatedOrder(long currentTimestamp,
                                      OrderTargetInfoTest order,
                                      MarketRateChange marketRate,
                                      Map<String, KlineObjectSimple> currentSnapshot,
                                      TreeMap<Long, Map<String, KlineObjectSimple>> futureLookupData) {

        double currentPrice = currentSnapshot.get(order.symbol).priceClose;
        double drawdown = (currentPrice - order.priceEntry) / order.priceEntry;
        if (drawdown > -0.02) return;

        try {
            // Random ratio: 0.1 -> 1.3
            double dcaRatio = 0.1 + (1.2) * rand.nextDouble();

            DcaMarketFeatures features = featureExtractor.extractFeatures(
                    currentTimestamp, order, marketRate, currentSnapshot, dcaRatio);

            if (features != null) {
                calculateLabels(features, order, currentPrice, futureLookupData, 4320);
                buffer.add(features);
                collectedCount++;
            }

        } catch (Exception e) {
            LOG.error("Error processing DCA sample", e);
        }

    }

    private void calculateLabels(DcaMarketFeatures f, OrderTargetInfoTest order, double currentPrice,
                                 TreeMap<Long, Map<String, KlineObjectSimple>> futureData, int lookAheadMinutes) {

        double oldVol = order.quantity;
        double newVol = oldVol * f.dcaImpactRatio;

        double newAvgPrice = (order.priceEntry * oldVol + currentPrice * newVol) / (oldVol + newVol);
        double targetPrice = newAvgPrice * 1.005; // TP +0.5%

        boolean recovered = false;
        double maxDrawdown = 0.0;

        long endTime = f.timestamp + (lookAheadMinutes * 60000L);
        // Lấy dữ liệu từ hiện tại đến 3 ngày sau
        NavigableMap<Long, Map<String, KlineObjectSimple>> future = futureData.subMap(f.timestamp, false, endTime, true);

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : future.entrySet()) {
            KlineObjectSimple kline = entry.getValue().get(order.symbol);
            if (kline == null) continue;

            if (!recovered && kline.maxPrice >= targetPrice) {
                recovered = true;
            }

            // Tính Max DD tiếp diễn (so với giá Avg mới)
            double dd = (kline.minPrice - newAvgPrice) / newAvgPrice;
            if (dd < maxDrawdown) maxDrawdown = dd;
        }

        // Gán Label (Tên biến đã đổi sang 3D ở class DcaMarketFeatures)
        f.labelIsRecoverable3D = recovered ? 1 : 0;
        f.labelMaxDrawdown3D = maxDrawdown;
    }

    public void exportData() {
        if (buffer.isEmpty()) return;
        try {
            String filename = outputPath + "/dca_features_" + System.currentTimeMillis() + ".csv";
            try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
                writer.println(buffer.get(0).toCSVHeader());
                for (DcaMarketFeatures f : buffer) {
                    writer.println(f.toCSVRow());
                }
            }
            LOG.info("✅ Exported {} DCA samples.", buffer.size());
            buffer.clear();
        } catch (Exception e) {
            LOG.error("Export failed", e);
        }
    }

    public int getCollectedCount() {
        return collectedCount;
    }
}