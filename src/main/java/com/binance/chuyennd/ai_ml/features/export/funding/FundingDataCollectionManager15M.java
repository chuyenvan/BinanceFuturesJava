package com.binance.chuyennd.ai_ml.features.export.funding;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager15M;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Utils;
import org.jetbrains.annotations.NotNull;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.util.*;

public class FundingDataCollectionManager15M {
    private static final Logger LOG = LoggerFactory.getLogger(FundingDataCollectionManager15M.class);
    private final String outputDir;
    private final List<String> buffer = new ArrayList<>();
    private int collectedCount = 0;
    private final FundingFeatureExtractorV2_15M featureExtractor = new FundingFeatureExtractorV2_15M();

    private final int[] label6Counts = new int[5];
    private final int[] label40Counts = new int[5];

    public FundingDataCollectionManager15M(String outputDir) {
        this.outputDir = outputDir;
        new File(outputDir).mkdirs();
        writeHeader();
    }

    private void writeHeader() {
        String header =
                "btcMomentum1H,btcMomentum4H,btcMomentum24H,btcDominance,marketBreadthStrength," +
                        "momentum15M,momentum1H,momentum4H,momentum24H,rsi1H,distFromLow24H,volatilityShock," +
                        "basketMomentum15M,basketMomentum1H,basketMomentum24H,basketRsi14,basketVolSpike," +
                        "coinFundingRate,fundingRateRaw,fundingRateAvg24H,fundingRateTrend," +
                        "label6,label40";

        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputDir + "/header_funding_15m.csv"))) {
            writer.write(header);
            writer.newLine();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void updateHistory(Map<Short, KlineObjectSimple> snapshot) {
        featureExtractor.updateMarketHistory(snapshot);
    }

    public void processSample(long currentTimestamp, OrderTargetInfoTest order,
                              Map<Short, KlineObjectSimple> currentSnapshot,
                              TreeMap<Long, Map<Short, KlineObjectSimple>> futureLookupData,
                              MarketDataObject15M marketData) {
        try {
            // Lấy rổ Coin bằng ID Short
            List<Short> basket = HistoryManager15M.getInstance().findPotentialLosersShort(currentTimestamp);

            FundingMarketFeatures15M features = featureExtractor.extractFeatures(
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

    private String calculateLabelsAndFormat(FundingMarketFeatures15M f, OrderTargetInfoTest order,
                                            TreeMap<Long, Map<Short, KlineObjectSimple>> futureLookupData) {
        float entryPrice = order.lastPrice;
        if (entryPrice <= 0) return null;

        short symId = com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper.getInstance().getId(order.symbol);

        // Target 6%
        float targetPrice6 = entryPrice * 1.06f;
        f.label6 = calculateLabelType(symId, targetPrice6, order.timeStart, futureLookupData);
        if (f.label6 >= 0 && f.label6 <= 4) label6Counts[f.label6]++;

        // Target 40%
        float targetPrice40 = entryPrice * 1.40f;
        f.label40 = calculateLabelType(symId, targetPrice40, order.timeStart, futureLookupData);
        if (f.label40 >= 0 && f.label40 <= 4) label40Counts[f.label40]++;

        return getStringBuilder(f).toString();
    }

    @NotNull
    private static StringBuilder getStringBuilder(FundingMarketFeatures15M f) {
        StringBuilder sb = new StringBuilder();
        sb.append(String.format(Locale.US, "%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.btcMomentum1H, f.btcMomentum4H, f.btcMomentum24H, f.btcDominance, f.marketBreadthStrength));
        sb.append(String.format(Locale.US, "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.momentum15M, f.momentum1H, f.momentum4H, f.momentum24H, f.rsi1H, f.distFromLow24H, f.volatilityShock));
        sb.append(String.format(Locale.US, "%.6f,%.6f,%.6f,%.6f,%.6f,",
                f.basketMomentum15M, f.basketMomentum1H, f.basketMomentum24H, f.basketRsi14, f.basketVolSpike));
        sb.append(String.format(Locale.US, "%.8f,%.8f,%.8f,%.8f,",
                f.coinFundingRate, f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend));
        sb.append(String.format(Locale.US, "%d,%d", f.label6, f.label40));
        return sb;
    }

    private int calculateLabelType(short symId, float targetPrice, long startTime,
                                   TreeMap<Long, Map<Short, KlineObjectSimple>> futureData) {
        if (checkProfit(symId, targetPrice, startTime, 15 * Utils.TIME_MINUTE, futureData)) return 4;
        else if (checkProfit(symId, targetPrice, startTime, 4 * Utils.TIME_HOUR, futureData)) return 3;
        else if (checkProfit(symId, targetPrice, startTime, 24 * Utils.TIME_HOUR, futureData)) return 2;
        else if (checkProfit(symId, targetPrice, startTime, 72 * Utils.TIME_HOUR, futureData)) return 1;
        else return 0;
    }

    private boolean checkProfit(short symId, float targetPrice, long startTime, long duration,
                                TreeMap<Long, Map<Short, KlineObjectSimple>> futureData) {
        long endTime = startTime + duration;
        // Quét tương lai theo khung 15m
        for (Map<Short, KlineObjectSimple> snapshot : futureData.subMap(startTime, false, endTime, true).values()) {
            KlineObjectSimple k = snapshot.get(symId);
            if (k != null && k.maxPrice >= targetPrice) return true;
        }
        return false;
    }

    public void exportData() {
        if (buffer.isEmpty()) return;
        try (BufferedWriter writer = new BufferedWriter(new FileWriter(outputDir + "/data_funding_15m_" + System.currentTimeMillis() + ".csv"))) {
            for (String line : buffer) {
                writer.write(line); writer.newLine();
            }
            buffer.clear();
        } catch (Exception e) { e.printStackTrace(); }
    }

    public int getCollectedCount() { return collectedCount; }
    public String getLabelReport() {
        return String.format("L6:[%d,%d,%d,%d,F:%d] | L40:[%d,%d,%d,%d,F:%d]",
                label6Counts[4], label6Counts[3], label6Counts[2], label6Counts[1], label6Counts[0],
                label40Counts[4], label40Counts[3], label40Counts[2], label40Counts[1], label40Counts[0]);
    }
}
