package com.binance.chuyennd.ai_ml.features.export.entry;

import java.io.Serializable;
import java.util.Locale;

public class MarketFeatures implements Serializable {
    private static final long serialVersionUID = 1L;

    public long timestamp;
    public String dateKey;

    // === GROUP 1: BTC MACRO ===
    public float momentum1M;
    public float momentum5M;
    public float momentum15M;
    public float momentum1H;
    public float momentum4H;
    public float momentum24H;
    public float momentumAcceleration;
    public float trendStrengthETH;
    public float trendConsistency;

    public float volatility1M;
    public float volatility15M;
    public float volatility1H;
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
    public float basketMomentum15M;
    public float basketMomentum1H;
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

    // === LABELS (đã BỎ futureReturn24H — model 24H không còn dùng) ===
    public float futureReturn15M;  //
    public float maxDrawdownNext4H; //

    public String toCSVHeader() {
        return "timestamp,momentum1M,momentum5M,momentum15M,momentum1H,momentum4H,momentum24H," +
                "momentumAcceleration,trendStrengthETH,trendConsistency," +
                "volatility1M,volatility15M,volatility1H,volatility24H,volatilityTermStructure," +
                "volatilityRegime," +
                "advanceDeclineRatio,percentAboveMA20,volumeRatioUpDown,marketBreadthStrength,btcDominance," +
                "rsi14,volumeSpike,distMA20," +
                "basketMomentum15M,basketMomentum1H,basketRsi14,basketVolSpike," +
                "fundingRateRaw,fundingRateAvg24H,fundingRateTrend," +
                "hourOfDay,dayOfWeek,weekOfMonth,monthOfYear," +
                "futureReturn15M,maxDrawdownNext4H"; // đã bỏ futureReturn24H
    }

    public String toCSVRow() {
        StringBuilder sb = new StringBuilder();
        sb.append(timestamp).append(",");

        // BTC Momentum & Volatility & Breadth & Indicators & Basket & Funding & Time ...
        // (Giữ nguyên các append cũ cho tới phần Labels)
        sb.append(formatDouble(momentum1M)).append(",");
        sb.append(formatDouble(momentum5M)).append(",");
        sb.append(formatDouble(momentum15M)).append(",");
        sb.append(formatDouble(momentum1H)).append(",");
        sb.append(formatDouble(momentum4H)).append(",");
        sb.append(formatDouble(momentum24H)).append(",");
        sb.append(formatDouble(momentumAcceleration)).append(",");
        sb.append(formatDouble(trendStrengthETH)).append(",");
        sb.append(formatDouble(trendConsistency)).append(",");
        sb.append(formatDouble(volatility1M)).append(",");
        sb.append(formatDouble(volatility15M)).append(",");
        sb.append(formatDouble(volatility1H)).append(",");
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
        sb.append(formatDouble(basketMomentum15M)).append(",");
        sb.append(formatDouble(basketMomentum1H)).append(",");
        sb.append(formatDouble(basketRsi14)).append(",");
        sb.append(formatDouble(basketVolSpike)).append(",");
        sb.append(formatDouble(fundingRateRaw)).append(",");
        sb.append(formatDouble(fundingRateAvg24H)).append(",");
        sb.append(formatDouble(fundingRateTrend)).append(",");
        sb.append(hourOfDay).append(",");
        sb.append(dayOfWeek).append(",");
        sb.append(weekOfMonth).append(",");
        sb.append(monthOfYear).append(",");

        // Labels (2 cột: 15M + DD4H)
        sb.append(formatDouble(futureReturn15M)).append(","); //
        sb.append(formatDouble(maxDrawdownNext4H));           //

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