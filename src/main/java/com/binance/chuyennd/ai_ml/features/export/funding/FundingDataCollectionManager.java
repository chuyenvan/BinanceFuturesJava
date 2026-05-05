package com.binance.chuyennd.ai_ml.features.export.funding;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.utils.Utils;
import org.jetbrains.annotations.NotNull;
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


    // Counter cho 2 loại label
    private final int[] label6Counts = new int[5];
    private final int[] label40Counts = new int[5];

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
                        "momentum1M,momentum15M,momentum1H,momentum4H,momentum24H,rsi1H,distFromLow24H,volatilityShock," +
                        // Basket
                        "basketMomentum15M,basketMomentum1H,basketMomentum24H,basketRsi14,basketVolSpike," +
                        // Funding
                        "coinFundingRate,fundingRateRaw,fundingRateAvg24H,fundingRateTrend," +
                        // LABELS (2 columns)
                        "label6,label40";

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

    public float getReturn(String symbol, int minutes) {
        return featureExtractor.calculateReturn(symbol, minutes);
    }

    public void processSample(long currentTimestamp, OrderTargetInfoTest order,
                              Map<String, KlineObjectSimple> currentSnapshot,
                              TreeMap<Long, Map<String, KlineObjectSimple>> futureLookupData,
                              MarketDataObject marketData) {
        try {
            final List<String> basket = HistoryManager.getInstance().findPotentialLosers(currentTimestamp);

            FundingMarketFeatures features = featureExtractor.extractFeatures(
                    currentTimestamp, order, currentSnapshot, marketData, basket);

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
        float entryPrice = order.lastPrice;
        if (entryPrice <= 0) return null;

        // 1. Tính toán Label 6 (Target 6%)
        float targetPrice6 = entryPrice * 1.06f;
        f.label6 = calculateLabelType(order.symbol, targetPrice6, order.timeStart, futureLookupData);
        if (f.label6 >= 0 && f.label6 <= 4) label6Counts[f.label6]++;

        // 2. Tính toán Label 40 (Target 40%)
        float targetPrice40 = entryPrice * 1.40f;
        f.label40 = calculateLabelType(order.symbol, targetPrice40, order.timeStart, futureLookupData);
        if (f.label40 >= 0 && f.label40 <= 4) label40Counts[f.label40]++;

        // 3. Format CSV
        StringBuilder sb = getStringBuilder(f);

        return sb.toString();
    }

    @NotNull
    private static StringBuilder getStringBuilder(FundingMarketFeatures f) {
        StringBuilder sb = new StringBuilder();

        // Context
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.btcMomentum1H, f.btcMomentum4H, f.btcMomentum24H, f.btcDominance, f.marketBreadthStrength));

        // Coin
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.momentum1M, f.momentum15M, f.momentum1H, f.momentum4H, f.momentum24H, f.rsi1H, f.distFromLow24H, f.volatilityShock));

        // Basket
        sb.append(String.format("%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.basketMomentum15M, f.basketMomentum1H, f.basketMomentum24H, f.basketRsi14, f.basketVolSpike));

        // Funding
        sb.append(String.format("%.8f,%.8f,%.8f,%.8f,",
                f.coinFundingRate, f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend));

        // Labels
        sb.append(String.format("%d,%d", f.label6, f.label40));
        return sb;
    }

    // Hàm chung để tính loại Label (0-4) dựa trên Target Price
    private int calculateLabelType(String symbol, float targetPrice, long startTime,
                                   TreeMap<Long, Map<String, KlineObjectSimple>> futureLookupData) {
        if (checkProfit(symbol, targetPrice, startTime, 15 * Utils.TIME_MINUTE, futureLookupData)) {
            return 4;
        } else if (checkProfit(symbol, targetPrice, startTime, 4 * Utils.TIME_HOUR, futureLookupData)) {
            return 3;
        } else if (checkProfit(symbol, targetPrice, startTime, 24 * Utils.TIME_HOUR, futureLookupData)) {
            return 2;
        } else if (checkProfit(symbol, targetPrice, startTime, 72 * Utils.TIME_HOUR, futureLookupData)) {
            return 1;
        } else {
            return 0;
        }
    }

    private boolean checkProfit(String symbol, float targetPrice, long startTime, long duration,
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

    public String getLabelReport() {
        return String.format("L6:[%d,%d,%d,%d,F:%d] | L40:[%d,%d,%d,%d,F:%d]",
                label6Counts[4], label6Counts[3], label6Counts[2], label6Counts[1], label6Counts[0],
                label40Counts[4], label40Counts[3], label40Counts[2], label40Counts[1], label40Counts[0]);
    }
}