package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
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
    private long lastBasketTimestamp = -1;
    private List<String> cachedBasket = new ArrayList<>();

    public DcaDataCollectionManager(String outputDir) {
        this.outputDir = outputDir;
        new File(outputDir).mkdirs();
        writeHeader();
    }

    private void writeHeader() {
        // 🔥 HEADER ĐÃ CẬP NHẬT FULL
        String header = "distFromHigh24H,distMA20," +
                "instantAlpha,recoveryElasticity," +
                "crashVelocity,globalRateDownAvg,advanceDeclineRatio,btcDominance,marketBreadthStrength," +
                "btcMomentum15M,btcMomentum1H,btcMomentum4H,btcMomentum24H,btcMomentumAcceleration," +
                "ethMomentum15M,ethMomentum4H," +
                "momentum15M,momentum1H,momentum4H,momentum24H," + // Coin specific
                "rsi1H,rsiChange,volumeAnomaly,volumeRatio15M_24H,distFromLow24H,maxRateChange60M,volatilityShock,volatilityTermStructure," +
                "basketMomentum15M,basketMomentum1H,basketMomentum24H,basketRsi14,basketVolSpike," +
                "coinFundingRate,fundingRateRaw,fundingRateAvg24H,fundingRateTrend," + // Added coinFundingRate
                "hourOfDay,dayOfWeek,weekOfMonth,monthOfYear," +
                "labelMaxDropFromNow,labelMaxRiseFromNow," +
                "isDump30Pct3D,isPump20Pct3D";
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
            if (currentTimestamp != lastBasketTimestamp) {
                cachedBasket = featureExtractor.identifyTargetBasket(currentTimestamp);
                lastBasketTimestamp = currentTimestamp;
            }
            List<String> targetBasket = cachedBasket;
            if (targetBasket == null || targetBasket.isEmpty()) targetBasket = Collections.singletonList(order.symbol);

            KlineObjectSimple k = currentSnapshot.get(order.symbol);
            if (k != null) {
                DcaMarketFeatures features = featureExtractor.extractFeatures(
                        currentTimestamp, order, marketRate, currentSnapshot, targetBasket);

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
        double maxPriceInFuture = -1.0;

        long endTime = order.timeStart + 3 * Utils.TIME_DAY;
        Map<Long, Map<String, KlineObjectSimple>> subMap = futureLookupData.subMap(order.timeStart, false, endTime, true);

        boolean found = false;
        double basePrice = order.lastPrice;
        if (basePrice <= 0) return null;

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : subMap.entrySet()) {
            KlineObjectSimple k = entry.getValue().get(order.symbol);
            if (k != null) {
                if (k.minPrice < minPriceInFuture) minPriceInFuture = k.minPrice;
                if (k.maxPrice > maxPriceInFuture) maxPriceInFuture = k.maxPrice;
                found = true;
            }
        }
        if (!found) return null;

        double labelMaxDrop = (minPriceInFuture - basePrice) / basePrice;
        double labelMaxRise = (maxPriceInFuture - basePrice) / basePrice;

        int isDump30Pct3D = (labelMaxDrop <= -0.30) ? 1 : 0;
        int isPump20Pct3D = (labelMaxRise >= 0.20) ? 1 : 0;

        StringBuilder sb = new StringBuilder();
        // 1. Market Position
        sb.append(String.format("%.6f,%.6f,", f.distFromHigh24H, f.distMA20));
        // 2. Rel Strength
        sb.append(String.format("%.6f,%.6f,", f.instantAlpha, f.recoveryElasticity));
        // 3. Market Context
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.crashVelocity, f.globalRateDownAvg, f.advanceDeclineRatio, f.btcDominance, f.marketBreadthStrength));
        // 4. Macro (Updated BTC & ETH)
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.btcMomentum15M, f.btcMomentum1H, f.btcMomentum4H, f.btcMomentum24H, f.btcMomentumAcceleration,
                f.ethMomentum15M, f.ethMomentum4H));

        // 5. Technicals (Updated Momentum, RSI Change, Vol Ratio)
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,",
                f.momentum15M, f.momentum1H, f.momentum4H, f.momentum24H));
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.rsi1H, f.rsiChange, f.volumeAnomaly, f.volumeRatio15M_24H,
                f.distFromLow24H, f.maxRateChange60M, f.volatilityShock, f.volatilityTermStructure));

        // 6. Basket
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.basketMomentum15M, f.basketMomentum1H, f.basketMomentum24H, f.basketRsi14, f.basketVolSpike));

        // 7. Funding (Updated Coin Funding)
        sb.append(String.format("%.8f,%.8f,%.8f,%.8f,",
                f.coinFundingRate, f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend));

        // 8. Time
        sb.append(String.format("%d,%d,%d,%d,", f.hourOfDay, f.dayOfWeek, f.weekOfMonth, f.monthOfYear));

        // Labels
        sb.append(String.format("%.6f,%.6f,%d,%d", labelMaxDrop, labelMaxRise, isDump30Pct3D, isPump20Pct3D));

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