package com.binance.chuyennd.ai_ml.features.export.entry;

import java.io.Serializable;
import java.util.Locale;

public class MarketFeatures implements Serializable {
    private static final long serialVersionUID = 1L;

    public long timestamp;
    public String dateKey;

    // === GROUP 1: BTC MACRO (Thị trường chung) ===
    public double momentum1M;      // BTC
    public double momentum5M;      // BTC
    public double momentum15M;     // BTC
    public double momentum1H;      // BTC
    public double momentum4H;      // BTC
    public double momentum24H;     // BTC
    public double momentumAcceleration; // BTC
    public double trendStrengthETH;
    public double trendConsistency;

    public double volatility1M;    // BTC
    public double volatility15M;   // BTC
    public double volatility1H;    // BTC
    public double volatility24H;   // BTC
    public double volatilityTermStructure;
    public String volatilityRegime;

    public double rsi14;           // BTC RSI
    public double volumeSpike;     // BTC Volume
    public double distMA20;        // BTC MA

    // === GROUP 2: MARKET BREADTH (Độ rộng) ===
    public double advanceDeclineRatio;
    public double percentAboveMA20;
    public double volumeRatioUpDown;
    public double marketBreadthStrength;
    public double btcDominance;

    // === GROUP 3: 🔥 BASKET SPECIFIC (Của chính rổ coin định mua) ===
    public double basketMomentum15M; // TB Momentum 15M của rổ
    public double basketMomentum1H;  // TB Momentum 1H của rổ
    public double basketRsi14;       // TB RSI 14 của rổ (Quan trọng nhất để bắt đáy)
    public double basketVolSpike;    // TB Volume Spike của rổ (Tiền vào hay chưa)

    // === GROUP 4: FUNDING (Của rổ) ===
    public double fundingRateRaw;
    public double fundingRateAvg24H;
    public double fundingRateTrend;

    // === GROUP 5: TIME ===
    public int hourOfDay;
    public int dayOfWeek;
    public int weekOfMonth;
    public int monthOfYear;

    // === LABELS ===
    public String regimeLabel;
    public double futureReturn15M;
    public double futureReturn1H;
    public double futureReturn4H;
    public double futureReturn24H;
    public double maxDrawdownNext4H;
    public double maxDrawdownNext24H;



    public String toCSVHeader() {
        return "timestamp,momentum1M,momentum5M,momentum15M,momentum1H,momentum4H,momentum24H," +
                "momentumAcceleration,trendStrengthETH,trendConsistency," +
                "volatility1M,volatility15M,volatility1H,volatility24H,volatilityTermStructure," +
                "volatilityRegime," +
                "advanceDeclineRatio,percentAboveMA20,volumeRatioUpDown,marketBreadthStrength,btcDominance," +
                "rsi14,volumeSpike,distMA20," + // BTC Features
                "basketMomentum15M,basketMomentum1H,basketRsi14,basketVolSpike," + // 🔥 BASKET Features
                "fundingRateRaw,fundingRateAvg24H,fundingRateTrend," +
                "hourOfDay,dayOfWeek,weekOfMonth,monthOfYear," +
                "regimeLabel,futureReturn15M,futureReturn1H,futureReturn4H,futureReturn24H," +
                "maxDrawdownNext4H,maxDrawdownNext24H";
    }

    public String toCSVRow() {
        StringBuilder sb = new StringBuilder();
        sb.append(timestamp).append(",");

        // BTC Momentum
        sb.append(formatDouble(momentum1M)).append(",");
        sb.append(formatDouble(momentum5M)).append(",");
        sb.append(formatDouble(momentum15M)).append(",");
        sb.append(formatDouble(momentum1H)).append(",");
        sb.append(formatDouble(momentum4H)).append(",");
        sb.append(formatDouble(momentum24H)).append(",");
        sb.append(formatDouble(momentumAcceleration)).append(",");
        sb.append(formatDouble(trendStrengthETH)).append(",");
        sb.append(formatDouble(trendConsistency)).append(",");

        // BTC Volatility
        sb.append(formatDouble(volatility1M)).append(",");
        sb.append(formatDouble(volatility15M)).append(",");
        sb.append(formatDouble(volatility1H)).append(",");
        sb.append(formatDouble(volatility24H)).append(",");
        sb.append(formatDouble(volatilityTermStructure)).append(",");
        sb.append(escapeCSV(volatilityRegime)).append(",");

        // Breadth
        sb.append(formatDouble(advanceDeclineRatio)).append(",");
        sb.append(formatDouble(percentAboveMA20)).append(",");
        sb.append(formatDouble(volumeRatioUpDown)).append(",");
        sb.append(formatDouble(marketBreadthStrength)).append(",");
        sb.append(formatDouble(btcDominance)).append(",");

        // BTC Indicators
        sb.append(formatDouble(rsi14)).append(",");
        sb.append(formatDouble(volumeSpike)).append(",");
        sb.append(formatDouble(distMA20)).append(",");

        // 🔥 BASKET Indicators
        sb.append(formatDouble(basketMomentum15M)).append(",");
        sb.append(formatDouble(basketMomentum1H)).append(",");
        sb.append(formatDouble(basketRsi14)).append(",");
        sb.append(formatDouble(basketVolSpike)).append(",");

        // Funding
        sb.append(formatDouble(fundingRateRaw)).append(",");
        sb.append(formatDouble(fundingRateAvg24H)).append(",");
        sb.append(formatDouble(fundingRateTrend)).append(",");

        // Time
        sb.append(hourOfDay).append(",");
        sb.append(dayOfWeek).append(",");
        sb.append(weekOfMonth).append(",");
        sb.append(monthOfYear).append(",");

        // Labels
        sb.append(escapeCSV(regimeLabel)).append(",");
        sb.append(formatDouble(futureReturn15M)).append(",");
        sb.append(formatDouble(futureReturn1H)).append(",");
        sb.append(formatDouble(futureReturn4H)).append(",");
        sb.append(formatDouble(futureReturn24H)).append(",");
        sb.append(formatDouble(maxDrawdownNext4H)).append(",");
        sb.append(formatDouble(maxDrawdownNext24H));

        return sb.toString();
    }

    private String formatDouble(double value) {
        if (Double.isNaN(value) || Double.isInfinite(value)) return "0.000000";
        return String.format(Locale.US, "%.8f", value);
    }

    private String escapeCSV(String value) {
        if (value == null) return "NULL";
        return value;
    }
}