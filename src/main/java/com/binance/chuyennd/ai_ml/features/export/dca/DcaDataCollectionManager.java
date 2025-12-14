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

    public DcaDataCollectionManager(String outputPath) {
        this.featureExtractor = new DcaFeatureExtractor();
        this.buffer = Collections.synchronizedList(new ArrayList<>());
        this.outputPath = outputPath;
        new File(outputPath).mkdirs();
    }

    // 1. Cập nhật History cho Extractor
    public void updateHistory(Map<String, KlineObjectSimple> marketData) {
        featureExtractor.updateMarketHistory(marketData);
    }

    // 2. Hàm xử lý chính: Nhận vào lệnh giả lập và check Label tương lai
    public void processSimulatedOrder(long currentTimestamp,
                                      OrderTargetInfoTest order,
                                      MarketRateChange marketRate,
                                      Map<String, KlineObjectSimple> currentSnapshot,
                                      TreeMap<Long, Map<String, KlineObjectSimple>> futureLookupData) {

        // Chỉ thu thập dữ liệu khi lệnh đang lỗ đáng kể (Drawdown < -3%)
        // Để tránh rác data (lệnh lãi thì DCA làm gì?)
        double currentPrice = currentSnapshot.get(order.symbol).priceClose;
        double drawdown = (currentPrice - order.priceEntry) / order.priceEntry;

        if (drawdown > -0.02) return; // Lỗ ít quá bỏ qua

        try {
            // Trích xuất Features tại thời điểm hiện tại
            DcaMarketFeatures features = featureExtractor.extractFeatures(currentTimestamp, order, marketRate, currentSnapshot);
            if (features == null) return;

            // Tính Labels (Nhìn về tương lai 24H)
            calculateLabels(features, order, currentPrice, futureLookupData, 1440);

            // Logic lọc mẫu: Có thể thêm Sample Weight ở đây nếu cần
            buffer.add(features);
            collectedCount++;

            if (collectedCount % 1000 == 0) {
                LOG.info("Collected DCA Samples: {} | Sym: {} | DD: {}% | Recov: {}",
                        collectedCount, order.symbol,
                        String.format("%.2f", features.currentDrawdown * 100),
                        features.labelIsRecoverable24H);
            }

        } catch (Exception e) {
            LOG.error("Error processing DCA sample", e);
        }
    }

    private void calculateLabels(DcaMarketFeatures f, OrderTargetInfoTest order, double currentPrice,
                                 TreeMap<Long, Map<String, KlineObjectSimple>> futureData, int lookAheadMinutes) {

        // 1. Tính giá Target để về bờ (Giả sử DCA x2 Volume)
        double oldVol = order.quantity;
        double newVol = order.quantity;
        double newAvgPrice = (order.priceEntry * oldVol + currentPrice * newVol) / (oldVol + newVol);

        // Target TP: Hồi phục vượt qua giá Avg mới + 0.5% phí/lãi
        double targetPrice = newAvgPrice * 1.005;

        boolean recovered = false;
        double maxDrawdown = 0.0;
        double firstRecoverTime = -1;

        long endTime = f.timestamp + (lookAheadMinutes * 60000L);
        NavigableMap<Long, Map<String, KlineObjectSimple>> future = futureData.subMap(f.timestamp, false, endTime, true);

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : future.entrySet()) {
            KlineObjectSimple kline = entry.getValue().get(order.symbol);
            if (kline == null) continue;

            // Check TP
            if (!recovered && kline.maxPrice >= targetPrice) {
                recovered = true;
                firstRecoverTime = (double)(entry.getKey() - f.timestamp) / (3600 * 1000);
            }

            // Check Max Drawdown tiếp diễn
            // So sánh Low tương lai với giá Avg mới
            double dd = (kline.minPrice - newAvgPrice) / newAvgPrice;
            if (dd < maxDrawdown) maxDrawdown = dd;
        }

        f.labelIsRecoverable24H = recovered ? 1 : 0;
        f.labelHoursToRecover = (firstRecoverTime > 0) ? firstRecoverTime : 24.0;
        f.labelMaxDrawdown24H = maxDrawdown;
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

    public int getCollectedCount() { return collectedCount; }
}