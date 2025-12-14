package com.binance.chuyennd.ai_ml.features.export.dca;

import java.io.Serializable;
import java.util.Locale;

public class DcaMarketFeatures implements Serializable {
    private static final long serialVersionUID = 1L;

    public long timestamp;
    public String symbol;
    public String dateKey;

    // === GROUP 1: POSITION HEALTH (Bệnh án lệnh) ===
    public double currentDrawdown;      // % Lỗ hiện tại (< 0)
    public double lossVelocity;         // Tốc độ lỗ trong 15p qua
    public double orderAgeHours;        // Thời gian treo lệnh

    // === GROUP 2: FEASIBILITY (Tính khả thi) ===
    public double simulatedRecoveryDiff; // Cần hồi bao nhiêu % để về bờ nếu DCA x2
    public double dcaImpactRatio;       // Tỷ lệ Vol mới / Vol cũ (Set cứng hoặc biến thiên)

    // === GROUP 3: RELATIVE STRENGTH (Tương quan) ===
    public double instantAlpha;         // Coin_Return_15m - BTC_Return_15m
    public double recoveryElasticity;   // Độ nảy so với BTC trong 1H
    public double dangerIndex;          // Drawdown * Độ lệch pha (Cảnh báo đỏ)

    // === GROUP 4: MARKET CONTEXT (Bối cảnh) ===
    public int isPanicMode;             // 1 nếu sập mạnh, 0 nếu ko
    public double crashVelocity;        // Tốc độ sập thị trường chung
    public double globalRateDownAvg;    // Mức giảm TB top coin

    // === GROUP 5: TECHNICAL EXTREMES (Kỹ thuật) ===
    public double rsi14;
    public double volumeAnomaly;        // Vol / AvgVol4H
    public double distFromLow24H;       // Giá đang ở đâu so với đáy ngày

    // === LABELS (Target để Train) ===
    public int labelIsRecoverable24H;   // 1: Về bờ được trong 24h, 0: Không
    public double labelMaxDrawdown24H;  // Max lỗ thêm trong 24h tới (để lọc lệnh quá rủi ro)
    public double labelHoursToRecover;  // Mất bao lâu để về bờ

    public String toCSVHeader() {
        return "timestamp,symbol,currentDrawdown,lossVelocity,orderAgeHours," +
                "simulatedRecoveryDiff,dcaImpactRatio," +
                "instantAlpha,recoveryElasticity,dangerIndex," +
                "isPanicMode,crashVelocity,globalRateDownAvg," +
                "rsi14,volumeAnomaly,distFromLow24H," +
                "labelIsRecoverable24H,labelMaxDrawdown24H,labelHoursToRecover";
    }

    public String toCSVRow() {
        StringBuilder sb = new StringBuilder();
        sb.append(timestamp).append(",").append(symbol).append(",");

        // Group 1
        sb.append(formatDouble(currentDrawdown)).append(",");
        sb.append(formatDouble(lossVelocity)).append(",");
        sb.append(formatDouble(orderAgeHours)).append(",");

        // Group 2
        sb.append(formatDouble(simulatedRecoveryDiff)).append(",");
        sb.append(formatDouble(dcaImpactRatio)).append(",");

        // Group 3
        sb.append(formatDouble(instantAlpha)).append(",");
        sb.append(formatDouble(recoveryElasticity)).append(",");
        sb.append(formatDouble(dangerIndex)).append(",");

        // Group 4
        sb.append(isPanicMode).append(",");
        sb.append(formatDouble(crashVelocity)).append(",");
        sb.append(formatDouble(globalRateDownAvg)).append(",");

        // Group 5
        sb.append(formatDouble(rsi14)).append(",");
        sb.append(formatDouble(volumeAnomaly)).append(",");
        sb.append(formatDouble(distFromLow24H)).append(",");

        // Labels
        sb.append(labelIsRecoverable24H).append(",");
        sb.append(formatDouble(labelMaxDrawdown24H)).append(",");
        sb.append(formatDouble(labelHoursToRecover));

        return sb.toString();
    }

    private String formatDouble(double value) {
        if (Double.isNaN(value) || Double.isInfinite(value)) return "0.000000";
        return String.format(Locale.US, "%.6f", value);
    }
}