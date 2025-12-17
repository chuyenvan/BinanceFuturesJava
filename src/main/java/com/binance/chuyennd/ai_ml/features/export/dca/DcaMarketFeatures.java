package com.binance.chuyennd.ai_ml.features.export.dca;

import java.io.Serializable;
import java.util.Locale;

public class DcaMarketFeatures implements Serializable {
    private static final long serialVersionUID = 1L;

    public long timestamp;
    public String dateKey;

    // === GROUPS 1-5 GIỮ NGUYÊN ===
    public double currentDrawdown;
    public double lossVelocity1H;
    public double dcaImpactRatio;
    public double instantAlpha;
    public double recoveryElasticity;
    public double dangerIndex;
    public double crashVelocity;
    public double globalRateDownAvg;
    public double fundingRate;
    public double btcMomentum15M;
    public double btcMomentum1H;
    public double btcMomentum4H;
    public double btcMomentum24H;
    public double btcMomentumAcceleration;
    public double ethTrendStrength;
    public double rsi1H;
    public double volumeAnomaly;
    public double distFromLow24H;
    public double maxRateChange60M;

    // === LABELS (UPDATED to 3D) ===
    public int labelIsRecoverable3D;   // 1: Về bờ trong 3 ngày (72h)
    public double labelMaxDrawdown3D;  // Max lỗ thêm trong 3 ngày

    public String toCSVHeader() {
        return "timestamp,currentDrawdown,lossVelocity1H," +
                "dcaImpactRatio," +
                "instantAlpha,recoveryElasticity,dangerIndex," +
                "crashVelocity,globalRateDownAvg,fundingRate," +
                "btcMomentum15M,btcMomentum1H,btcMomentum4H,btcMomentum24H,btcMomentumAcceleration,ethTrendStrength," +
                "rsi1H,volumeAnomaly,distFromLow24H,maxRateChange60M," +
                "labelIsRecoverable3D,labelMaxDrawdown3D"; // Updated Header
    }

    public String toCSVRow() {
        StringBuilder sb = new StringBuilder();
        sb.append(timestamp).append(",");

        // Các Features giữ nguyên
        sb.append(formatDouble(currentDrawdown)).append(",");
        sb.append(formatDouble(lossVelocity1H)).append(",");
        sb.append(formatDouble(dcaImpactRatio)).append(",");
        sb.append(formatDouble(instantAlpha)).append(",");
        sb.append(formatDouble(recoveryElasticity)).append(",");
        sb.append(formatDouble(dangerIndex)).append(",");
        sb.append(formatDouble(crashVelocity)).append(",");
        sb.append(formatDouble(globalRateDownAvg)).append(",");
        sb.append(formatDouble(fundingRate)).append(",");
        sb.append(formatDouble(btcMomentum15M)).append(",");
        sb.append(formatDouble(btcMomentum1H)).append(",");
        sb.append(formatDouble(btcMomentum4H)).append(",");
        sb.append(formatDouble(btcMomentum24H)).append(",");
        sb.append(formatDouble(btcMomentumAcceleration)).append(",");
        sb.append(formatDouble(ethTrendStrength)).append(",");
        sb.append(formatDouble(rsi1H)).append(",");
        sb.append(formatDouble(volumeAnomaly)).append(",");
        sb.append(formatDouble(distFromLow24H)).append(",");
        sb.append(formatDouble(maxRateChange60M)).append(",");

        // Updated Labels
        sb.append(labelIsRecoverable3D).append(",");
        sb.append(formatDouble(labelMaxDrawdown3D));

        return sb.toString();
    }

    private String formatDouble(double value) {
        if (Double.isNaN(value) || Double.isInfinite(value)) return "0.000000";
        return String.format(Locale.US, "%.8f", value);
    }
}