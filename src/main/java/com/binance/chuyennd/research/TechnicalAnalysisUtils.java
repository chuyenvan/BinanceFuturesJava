package com.binance.chuyennd.research;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class TechnicalAnalysisUtils {


    public enum Signal {
        BUY,
        SELL,
        NONE
    }

    public static double calculateATR(List<KlineObjectSimple> tickers, int period) {
        if (tickers == null || tickers.size() < period + 1) {
            return -1;
        }

        double totalTrueRange = 0;

        // Bắt đầu từ nến thứ hai của chu kỳ cần tính
        // Vị trí bắt đầu là (tổng số nến - chu kỳ)
        int startIndex = tickers.size() - period;

        for (int i = startIndex; i < tickers.size(); i++) {
            KlineObjectSimple currentCandle = tickers.get(i);
            KlineObjectSimple previousCandle = tickers.get(i - 1);

            // Tính 3 giá trị để tìm ra True Range (TR)
            double highMinusLow = currentCandle.maxPrice - currentCandle.minPrice;
            double highMinusPrevClose = Math.abs(currentCandle.maxPrice - previousCandle.priceClose);
            double lowMinusPrevClose = Math.abs(currentCandle.minPrice - previousCandle.priceClose);

            // True Range là giá trị lớn nhất trong 3 giá trị trên
            double trueRange = Math.max(highMinusLow, Math.max(highMinusPrevClose, lowMinusPrevClose));

            totalTrueRange += trueRange;
        }

        // ATR là trung bình của các True Range
        return totalTrueRange / period;
    }
    /**
     * HÀM MỚI: Tính toán Đường trung bình động đơn giản (SMA).
     * @param tickers Danh sách các nến.
     * @param period Chu kỳ tính toán.
     * @return Giá trị SMA, hoặc -1 nếu không đủ dữ liệu.
     */
    public static double calculateSMA(List<KlineObjectSimple> tickers, int period) {
        if (tickers == null || tickers.size() < period) {
            return -1; // Không đủ dữ liệu
        }
        double sum = 0;
        // Chỉ lấy 'period' phần tử cuối cùng của list để tính toán
        for (int i = tickers.size() - period; i < tickers.size(); i++) {
            sum += tickers.get(i).priceClose;
        }
        return sum / period;
    }
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
    // =================================================================================
    // == CHIẾN LƯỢC NÂNG CAO: RSI + Bollinger Bands + Lọc Xu Hướng                  ==
    // =================================================================================

    /**
     * CHIẾN LƯỢC NÂNG CAO: Tín hiệu RSI được xác nhận bởi Bollinger Bands và lọc bởi XU HƯỚNG.
     * Đây là chiến lược cho tín hiệu chất lượng cao nhất.
     * @param klines Dữ liệu nến 1 phút.
     * @return Tín hiệu đã được lọc và xác nhận.
     */
    public static Signal getSignal_RsiWithBBandAndTrendFilter(List<KlineObjectSimple> klines) {
        // --- Các tham số có thể tùy chỉnh ---
        int trendPeriod = 200;      // Chu kỳ SMA để xác định xu hướng
        int rsiPeriod = 14;         // Chu kỳ RSI
        double rsiOverbought = 70.0; // Ngưỡng quá mua
        double rsiOversold = 30.0;   // Ngưỡng quá bán
        int bbPeriod = 20;          // Chu kỳ Bollinger Bands
        double bbStdDev = 2.0;       // Độ lệch chuẩn cho Bollinger Bands

        // --- Kiểm tra dữ liệu đầu vào ---
        if (klines.size() < trendPeriod) {
            return Signal.NONE;
        }

        // --- Lớp lọc 1: Xác định xu hướng ---
        double longTermSMA = TechnicalAnalysisUtils.calculateSMA(klines, trendPeriod);
        KlineObjectSimple lastCandle = klines.get(klines.size() - 1);
        double currentPrice = lastCandle.priceClose;

        // --- Tính toán các chỉ báo cần thiết ---
        double currentRSI = TechnicalAnalysisUtils.calculateRSI(klines, rsiPeriod);
        Map<String, Double> bollingerBands = TechnicalAnalysisUtils.calculateBollingerBands(klines, bbPeriod, bbStdDev);

        if (currentRSI < 0 || bollingerBands == null) {
            return Signal.NONE; // Không đủ dữ liệu để tính toán
        }

        // --- Áp dụng logic vào lệnh ---
        if (currentPrice > longTermSMA) { // Chỉ xem xét tín hiệu MUA trong xu hướng TĂNG
            Double lowerBand = bollingerBands.get("LOWER");
            // Điều kiện MUA: Giá chạm hoặc xuống dưới dải BB dưới VÀ RSI đang quá bán
            if (currentPrice <= lowerBand && currentRSI <= rsiOversold) {
                return Signal.BUY;
            }
        } else if (currentPrice < longTermSMA) { // Chỉ xem xét tín hiệu BÁN trong xu hướng GIẢM
            Double upperBand = bollingerBands.get("UPPER");
            // Điều kiện BÁN: Giá chạm hoặc vượt lên trên dải BB trên VÀ RSI đang quá mua
            if (currentPrice >= upperBand && currentRSI >= rsiOverbought) {
                return Signal.SELL;
            }
        }

        return Signal.NONE;
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