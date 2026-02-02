package com.binance.chuyennd.ai_ml.features.export.funding;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.util.*;

public class FundingDataCollectionManager {
    private static final Logger LOG = LoggerFactory.getLogger(FundingDataCollectionManager.class);
    private final String outputDir;
    private final List<String> buffer = new ArrayList<>();
    private int collectedCount = 0;
    private final FundingFeatureExtractor featureExtractor = new FundingFeatureExtractor();

    private long lastBasketTimestamp = -1;
    private List<String> cachedBasket = new ArrayList<>();
    private final int[] labelCounts = new int[5];

    public FundingDataCollectionManager(String outputDir) {
        this.outputDir = outputDir;
        new File(outputDir).mkdirs();
        writeHeader();
    }

    private void writeHeader() {
        String header =
                // Context
                "btcMomentum1H,btcMomentum4H,btcMomentum24H,btcDominance,marketBreadthStrength," +
                        // Coin
                        "momentum15M,momentum1H,momentum4H,momentum24H,rsi1H,distFromLow24H,volatilityShock," +
                        // Basket
                        "basketMomentum15M,basketMomentum1H,basketMomentum24H,basketRsi14,basketVolSpike," +
                        // Funding
                        "coinFundingRate,fundingRateRaw,fundingRateAvg24H,fundingRateTrend," +
                        // LABEL (Single column)
                        "label";

        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputDir + "/header_funding.csv"))) {
            writer.write(header);
            writer.newLine();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void updateHistory(Map<String, KlineObjectSimple> snapshot) {
        featureExtractor.updateMarketHistory(snapshot);
    }

    // 🔥 HÀM MỚI: Dùng để check rate15m trong Runner
    public double getReturn(String symbol, int minutes) {
        return featureExtractor.calculateReturn(symbol, minutes);
    }

    public void processSample(long currentTimestamp, OrderTargetInfoTest order,
                              Map<String, KlineObjectSimple> currentSnapshot,
                              TreeMap<Long, Map<String, KlineObjectSimple>> futureLookupData) {
        try {
            if (currentTimestamp != lastBasketTimestamp) {
                cachedBasket = featureExtractor.identifyTargetBasket(currentSnapshot);
                lastBasketTimestamp = currentTimestamp;
            }

            FundingMarketFeatures features = featureExtractor.extractFeatures(
                    currentTimestamp, order, currentSnapshot, cachedBasket);

            if (features != null) {
                String csvLine = calculateLabelsAndFormat(features, order, futureLookupData);
                if (csvLine != null) {
                    buffer.add(csvLine);
                    collectedCount++;
                }
            }
        } catch (Exception e) {
            LOG.error("Error processing funding sample", e);
        }
    }

    private String calculateLabelsAndFormat(FundingMarketFeatures f, OrderTargetInfoTest order,
                                            TreeMap<Long, Map<String, KlineObjectSimple>> futureLookupData) {
        double entryPrice = order.lastPrice;
        if (entryPrice <= 0) return null;

        double targetPrice = entryPrice * 1.06; // Mục tiêu lãi 6%

        // Tính Label theo thứ tự ưu tiên (Nhanh nhất -> Chậm nhất)
        // 4: 15M, 3: 4H, 2: 24H, 1: 72H, 0: Fail
        int label = 0;

        if (checkProfit(order.symbol, targetPrice, order.timeStart, 15 * Utils.TIME_MINUTE, futureLookupData)) {
            label = 4;
        } else if (checkProfit(order.symbol, targetPrice, order.timeStart, 4 * Utils.TIME_HOUR, futureLookupData)) {
            label = 3;
        } else if (checkProfit(order.symbol, targetPrice, order.timeStart, 24 * Utils.TIME_HOUR, futureLookupData)) {
            label = 2;
        } else if (checkProfit(order.symbol, targetPrice, order.timeStart, 72 * Utils.TIME_HOUR, futureLookupData)) {
            label = 1;
        } else {
            label = 0;
        }
// 🔥 CẬP NHẬT COUNTER
        if (label >= 0 && label <= 4) {
            labelCounts[label]++;
        }
        StringBuilder sb = new StringBuilder();

        // 1. Context
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.btcMomentum1H, f.btcMomentum4H, f.btcMomentum24H, f.btcDominance, f.marketBreadthStrength));

        // 2. Coin (Đã thêm momentum15M)
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.momentum15M, f.momentum1H, f.momentum4H, f.momentum24H, f.rsi1H, f.distFromLow24H, f.volatilityShock));

        // 3. Basket
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.basketMomentum15M, f.basketMomentum1H, f.basketMomentum24H, f.basketRsi14, f.basketVolSpike));

        // 4. Funding
        sb.append(String.format("%.8f,%.8f,%.8f,%.8f,",
                f.coinFundingRate, f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend));

        // 5. Label
        sb.append(String.format("%d", label));

        return sb.toString();
    }

    private boolean checkProfit(String symbol, double targetPrice, long startTime, long duration,
                                TreeMap<Long, Map<String, KlineObjectSimple>> futureData) {
        long endTime = startTime + duration;
        Map<Long, Map<String, KlineObjectSimple>> periodData = futureData.subMap(startTime, false, endTime, true);

        for (Map<String, KlineObjectSimple> snapshot : periodData.values()) {
            KlineObjectSimple k = snapshot.get(symbol);
            if (k != null && k.maxPrice >= targetPrice) {
                return true;
            }
        }
        return false;
    }

    public void exportData() {
        if (buffer.isEmpty()) return;
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputDir + "/data_funding_" + System.currentTimeMillis() + ".csv"))) {
            for (String line : buffer) {
                writer.write(line);
                writer.newLine();
            }
            buffer.clear();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public int getCollectedCount() {
        return collectedCount;
    }
    // 🔥 HÀM MỚI ĐỂ LẤY REPORT
    public String getLabelReport() {
        return String.format("[L4(15m):%d, L3(4h):%d, L2(24h):%d, L1(72h):%d, L0(Fail):%d]",
                labelCounts[4], labelCounts[3], labelCounts[2], labelCounts[1], labelCounts[0]);
    }

}