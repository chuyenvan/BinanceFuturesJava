package com.binance.chuyennd.ai_ml.features.export.entry;

import java.io.Serializable;
import java.util.Locale;

public class MarketFeatures15M implements Serializable {
    private static final long serialVersionUID = 1L;

    public long timestamp;
    public String dateKey;

    // === GROUP 1: BTC MACRO (Bỏ 1M, 5M) ===
    public float momentum15M;
    public float momentum1H;
    public float momentum4H;
    public float momentum24H;
    public float momentumAcceleration; // Gia tốc giữa 1H và 15M
    public float trendStrengthETH;
    public float trendConsistency;

    public float volatility1H;
    public float volatility4H;
    public float volatility24H;
    public float volatilityTermStructure;
    public String volatilityRegime;

    public float rsi14;
    public float volumeSpike;
    public float distMA20;

    // === GROUP 2: MARKET BREADTH ===
    public float advanceDeclineRatio;
    public float percentAboveMA20;
    public float volumeRatioUpDown;
    public float marketBreadthStrength;
    public float btcDominance;

    // === GROUP 3: BASKET SPECIFIC ===
    public float basketMomentum1H;
    public float basketMomentum4H;
    public float basketRsi14;
    public float basketVolSpike;

    // === GROUP 4: FUNDING ===
    public float fundingRateRaw;
    public float fundingRateAvg24H;
    public float fundingRateTrend;

    // === GROUP 5: TIME ===
    public int hourOfDay;
    public int dayOfWeek;
    public int weekOfMonth;
    public int monthOfYear;

    // === LABELS (Đã nâng cấp tầm nhìn xa hơn) ===
    public float futureReturn4H;   // Đổi từ 15m -> 4H (16 nến)
    public float futureReturn24H;  // 24H (96 nến)
    public float maxDrawdownNext12H; // Đổi từ 4H -> 12H

    public String toCSVHeader() {
        return "timestamp,momentum15M,momentum1H,momentum4H,momentum24H," +
                "momentumAcceleration,trendStrengthETH,trendConsistency," +
                "volatility1H,volatility4H,volatility24H,volatilityTermStructure," +
                "volatilityRegime," +
                "advanceDeclineRatio,percentAboveMA20,volumeRatioUpDown,marketBreadthStrength,btcDominance," +
                "rsi14,volumeSpike,distMA20," +
                "basketMomentum1H,basketMomentum4H,basketRsi14,basketVolSpike," +
                "fundingRateRaw,fundingRateAvg24H,fundingRateTrend," +
                "hourOfDay,dayOfWeek,weekOfMonth,monthOfYear," +
                "futureReturn4H,futureReturn24H,maxDrawdownNext12H";
    }

    public String toCSVRow() {
        StringBuilder sb = new StringBuilder();
        sb.append(timestamp).append(",");

        sb.append(formatDouble(momentum15M)).append(",");
        sb.append(formatDouble(momentum1H)).append(",");
        sb.append(formatDouble(momentum4H)).append(",");
        sb.append(formatDouble(momentum24H)).append(",");
        sb.append(formatDouble(momentumAcceleration)).append(",");
        sb.append(formatDouble(trendStrengthETH)).append(",");
        sb.append(formatDouble(trendConsistency)).append(",");

        sb.append(formatDouble(volatility1H)).append(",");
        sb.append(formatDouble(volatility4H)).append(",");
        sb.append(formatDouble(volatility24H)).append(",");
        sb.append(formatDouble(volatilityTermStructure)).append(",");
        sb.append(escapeCSV(volatilityRegime)).append(",");

        sb.append(formatDouble(advanceDeclineRatio)).append(",");
        sb.append(formatDouble(percentAboveMA20)).append(",");
        sb.append(formatDouble(volumeRatioUpDown)).append(",");
        sb.append(formatDouble(marketBreadthStrength)).append(",");
        sb.append(formatDouble(btcDominance)).append(",");

        sb.append(formatDouble(rsi14)).append(",");
        sb.append(formatDouble(volumeSpike)).append(",");
        sb.append(formatDouble(distMA20)).append(",");

        sb.append(formatDouble(basketMomentum1H)).append(",");
        sb.append(formatDouble(basketMomentum4H)).append(",");
        sb.append(formatDouble(basketRsi14)).append(",");
        sb.append(formatDouble(basketVolSpike)).append(",");

        sb.append(formatDouble(fundingRateRaw)).append(",");
        sb.append(formatDouble(fundingRateAvg24H)).append(",");
        sb.append(formatDouble(fundingRateTrend)).append(",");

        sb.append(hourOfDay).append(",");
        sb.append(dayOfWeek).append(",");
        sb.append(weekOfMonth).append(",");
        sb.append(monthOfYear).append(",");

        // Labels
        sb.append(formatDouble(futureReturn4H)).append(",");
        sb.append(formatDouble(futureReturn24H)).append(",");
        sb.append(formatDouble(maxDrawdownNext12H));

        return sb.toString();
    }

    private String formatDouble(float value) {
        if (Float.isNaN(value) || Float.isInfinite(value)) return "0.000000";
        return String.format(Locale.US, "%.8f", value);
    }

    private String escapeCSV(String value) {
        if (value == null) return "NULL";
        return value;
    }
}