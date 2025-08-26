package com.binance.chuyennd.research;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class TechnicalAnalysisUtils {

    /**
     * Tính toán chỉ báo RSI (Relative Strength Index).
     * @param tickers Danh sách các nến.
     * @param period Chu kỳ tính toán (thường là 14).
     * @return Giá trị RSI cuối cùng, hoặc -1 nếu không đủ dữ liệu.
     */
    public static double calculateRSI(List<KlineObjectSimple> tickers, int period) {
        if (tickers == null || tickers.size() < period + 1) {
            return -1; // Không đủ dữ liệu
        }

        double totalGain = 0;
        double totalLoss = 0;

        // Tính gain/loss trung bình cho chu kỳ đầu tiên
        for (int i = tickers.size() - period - 1; i < tickers.size() - 1; i++) {
            double change = tickers.get(i + 1).priceClose - tickers.get(i).priceClose;
            if (change > 0) {
                totalGain += change;
            } else {
                totalLoss -= change; // loss là số dương
            }
        }

        double avgGain = totalGain / period;
        double avgLoss = totalLoss / period;

        if (avgLoss == 0) {
            return 100; // RSI = 100 nếu không có loss
        }

        double rs = avgGain / avgLoss;
        return 100 - (100 / (1 + rs));
    }

    /**
     * Tính toán dải Bollinger Bands.
     * @param tickers Danh sách các nến.
     * @param period Chu kỳ tính toán (thường là 20).
     * @param stdDevMultiplier Hệ số nhân cho độ lệch chuẩn (thường là 2.0).
     * @return Một Map chứa "UPPER", "MIDDLE", "LOWER" band, hoặc null nếu không đủ dữ liệu.
     */
    public static Map<String, Double> calculateBollingerBands(List<KlineObjectSimple> tickers, int period, double stdDevMultiplier) {
        if (tickers == null || tickers.size() < period) {
            return null;
        }

        List<Double> closes = new ArrayList<>();
        for (int i = tickers.size() - period; i < tickers.size(); i++) {
            closes.add(tickers.get(i).priceClose);
        }

        // Tính SMA (Middle Band)
        double sum = closes.stream().mapToDouble(Double::doubleValue).sum();
        double middleBand = sum / period;

        // Tính độ lệch chuẩn
        double stdDevSum = 0;
        for (double close : closes) {
            stdDevSum += Math.pow(close - middleBand, 2);
        }
        double stdDev = Math.sqrt(stdDevSum / period);

        // Tính Upper và Lower band
        double upperBand = middleBand + (stdDev * stdDevMultiplier);
        double lowerBand = middleBand - (stdDev * stdDevMultiplier);

        Map<String, Double> bands = new HashMap<>();
        bands.put("UPPER", upperBand);
        bands.put("MIDDLE", middleBand);
        bands.put("LOWER", lowerBand);
        return bands;
    }
}