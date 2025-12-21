package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.util.*;

public class DcaDataCollectionManager {
    private static final Logger LOG = LoggerFactory.getLogger(DcaDataCollectionManager.class);
    private final String outputDir;
    private final List<String> buffer = new ArrayList<>();
    private int collectedCount = 0;
    private final DcaFeatureExtractor featureExtractor = new DcaFeatureExtractor();

    // Caching Basket
    private long lastBasketTimestamp = -1;
    private List<String> cachedBasket = new ArrayList<>();

    public DcaDataCollectionManager(String outputDir) {
        this.outputDir = outputDir;
        new File(outputDir).mkdirs();
        writeHeader();
    }

    private void writeHeader() {
        String header = "currentDrawdown,lossVelocity1H,dcaImpactRatio," +
                "instantAlpha,recoveryElasticity,dangerIndex," +
                "crashVelocity,globalRateDownAvg," +
                "btcMomentum1H,btcMomentum24H," +
                "rsi1H,volumeAnomaly,distFromLow24H,maxRateChange60M,volumeSpike,volatilityShock," +
                "basketMomentum15M,basketMomentum1H,basketRsi14,basketVolSpike," +
                "fundingRateRaw,fundingRateAvg24H,fundingRateTrend," +
                "hourOfDay,dayOfWeek,weekOfMonth,monthOfYear," +
                "labelMaxDropFromNow";
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputDir + "/header.csv"))) {
            writer.write(header); writer.newLine();
        } catch (Exception e) { e.printStackTrace(); }
    }

    public void updateHistory(Map<String, KlineObjectSimple> snapshot) {
        featureExtractor.updateMarketHistory(snapshot);
    }

    public void processSimulatedOrder(long currentTimestamp, OrderTargetInfoTest order,
                                      MarketRateChange marketRate,
                                      Map<String, KlineObjectSimple> currentSnapshot,
                                      TreeMap<Long, Map<String, KlineObjectSimple>> futureLookupData) {
        try {
            // 1. Funding (Giữ nguyên)
            Map<String, Double> fundingMap = new HashMap<>();
            Double realFunding = FundingFeeManager.getInstance().getNearestFundingFee(order.symbol, currentTimestamp);
            if (realFunding != null) fundingMap.put(order.symbol, realFunding);

            // 2. Basket (Giữ nguyên logic Cache)
            if (currentTimestamp != lastBasketTimestamp) {
                cachedBasket = featureExtractor.identifyTargetBasket(currentTimestamp);
                lastBasketTimestamp = currentTimestamp;
            }
            List<String> targetBasket = cachedBasket;
            if (targetBasket == null || targetBasket.isEmpty()) targetBasket = Collections.singletonList(order.symbol);

            // 3. 🔥 THAY ĐỔI: CHỌN 1 KỊCH BẢN BƠM VỐN NGẪU NHIÊN
            // Thay vì loop qua mảng, ta random chọn 1 loại hành vi
            double volumeMultiplier;
            double r = Math.random();

            if (r < 0.4) {
                // 40% cơ hội là "Rải đinh" (Hết tiền/Sợ)
                volumeMultiplier = 0.05 + Math.random() * 0.15;
            } else if (r < 0.7) {
                // 30% cơ hội là "Cầm cự"
                volumeMultiplier = 0.20 + Math.random() * 0.20;
            } else if (r < 0.9) {
                // 20% cơ hội là "Tiêu chuẩn"
                volumeMultiplier = 0.40 + Math.random() * 0.30;
            } else {
                // 10% cơ hội là "All-in"
                volumeMultiplier = 0.70 + Math.random() * 0.30;
            }

            // Xử lý logic 1 lần duy nhất
            KlineObjectSimple k = currentSnapshot.get(order.symbol);
            if (k != null) {
                double dcaRatio = volumeMultiplier;

                DcaMarketFeatures features = featureExtractor.extractFeatures(
                        currentTimestamp, order, marketRate, currentSnapshot, dcaRatio, targetBasket);

                if (features != null) {
                    String csvLine = calculateLabelsAndFormat(features, order, futureLookupData);
                    if (csvLine != null) {
                        buffer.add(csvLine);
                        collectedCount++;
                    }
                }
            }
        } catch (Exception e) {
            LOG.error("Error processing sample", e);
        }
    }

    private String calculateLabelsAndFormat(DcaMarketFeatures f, OrderTargetInfoTest order,
                                            TreeMap<Long, Map<String, KlineObjectSimple>> futureLookupData) {
        double minPriceInFuture = Double.MAX_VALUE;
        long endTime = order.timeStart + 3 * Utils.TIME_DAY;
        Map<Long, Map<String, KlineObjectSimple>> subMap = futureLookupData.subMap(order.timeStart, false, endTime, true);

        boolean found = false;
        double currentPrice = order.priceEntry * (1.0 - f.currentDrawdown);

        for (Map<String, KlineObjectSimple> m : subMap.values()) {
            KlineObjectSimple k = m.get(order.symbol);
            if (k != null) {
                if (k.minPrice < minPriceInFuture) minPriceInFuture = k.minPrice;
                found = true;
            }
        }
        if (!found) return null;

        double labelMaxDrop = (minPriceInFuture - currentPrice) / currentPrice;

        StringBuilder sb = new StringBuilder();
        sb.append(String.format("%.6f,%.6f,%.4f,", f.currentDrawdown, f.lossVelocity1H, f.dcaImpactRatio));
        sb.append(String.format("%.6f,%.6f,%.6f,", f.instantAlpha, f.recoveryElasticity, f.dangerIndex));
        sb.append(String.format("%.6f,%.6f,", f.crashVelocity, f.globalRateDownAvg));
        sb.append(String.format("%.6f,%.6f,", f.btcMomentum1H, f.btcMomentum24H));
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.rsi1H, f.volumeAnomaly, f.distFromLow24H, f.maxRateChange60M, f.volumeSpike, f.volatilityShock));
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,", f.basketMomentum15M, f.basketMomentum1H, f.basketRsi14, f.basketVolSpike));
        sb.append(String.format("%.8f,%.8f,%.8f,", f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend));
        sb.append(String.format("%d,%d,%d,%d,", f.hourOfDay, f.dayOfWeek, f.weekOfMonth, f.monthOfYear));
        sb.append(String.format("%.6f", labelMaxDrop));
        return sb.toString();
    }

    public void exportData() {
        if (buffer.isEmpty()) return;
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputDir + "/data_" + System.currentTimeMillis() + ".csv"))) {
            for (String line : buffer) { writer.write(line); writer.newLine(); }
            buffer.clear();
        } catch (Exception e) { e.printStackTrace(); }
    }
    public int getCollectedCount() { return collectedCount; }
}