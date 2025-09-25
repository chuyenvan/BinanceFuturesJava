package com.binance.chuyennd.research;

import com.binance.chuyennd.object.sw.KlineObjectSimple;

import java.util.List;
import java.util.Map;

/**
 * Lớp này chứa các hàm logic cho các chiến lược vào lệnh khác nhau.
 * Nó bao gồm các hàm tín hiệu "thô" (raw) và các hàm đã được thêm bộ lọc
 * (lọc xu hướng, kết hợp chỉ báo) để tăng chất lượng và giảm nhiễu.
 * <p>
 * Tác giả: Gemini & [Tên của bạn]
 * Ngày cập nhật: 25 tháng 9 năm 2025
 */
public class BacktestEntryStrategies {

    /**
     * Enum để định nghĩa tín hiệu trả về: Mua, Bán, hoặc Không làm gì.
     */
    public enum Signal {
        BUY,
        SELL,
        NONE
    }

    // =================================================================================
    // == CÁC HÀM TÍN HIỆU GỐC (RAW SIGNALS) - Chỉ mang tính tham khảo, độ nhiễu cao ==
    // =================================================================================

    /**
     * Tín hiệu gốc từ Giao cắt đường trung bình động (Moving Average Crossover).
     * Private vì chỉ nên được sử dụng bên trong lớp này.
     */
    private static Signal getRawSignal_MovingAverageCrossover(List<KlineObjectSimple> klines) {
        int fastPeriod = 9;
        int slowPeriod = 21;
        if (klines == null || klines.size() < slowPeriod + 1) return Signal.NONE;

        // Dữ liệu cho nến hiện tại
        double fastSMA_current = TechnicalAnalysisUtils.calculateSMA(klines, fastPeriod);
        double slowSMA_current = TechnicalAnalysisUtils.calculateSMA(klines, slowPeriod);

        // Dữ liệu cho nến trước đó
        List<KlineObjectSimple> previousKlines = klines.subList(0, klines.size() - 1);
        double fastSMA_previous = TechnicalAnalysisUtils.calculateSMA(previousKlines, fastPeriod);
        double slowSMA_previous = TechnicalAnalysisUtils.calculateSMA(previousKlines, slowPeriod);

        if (fastSMA_current < 0 || slowSMA_current < 0 || fastSMA_previous < 0 || slowSMA_previous < 0)
            return Signal.NONE;

        // Tín hiệu MUA: đường nhanh cắt lên trên đường chậm
        if (fastSMA_previous <= slowSMA_previous && fastSMA_current > slowSMA_current) return Signal.BUY;

        // Tín hiệu BÁN: đường nhanh cắt xuống dưới đường chậm
        if (fastSMA_previous >= slowSMA_previous && fastSMA_current < slowSMA_current) return Signal.SELL;

        return Signal.NONE;
    }

    /**
     * Tín hiệu gốc từ RSI quá mua/quá bán.
     * Private vì chỉ nên được sử dụng bên trong lớp này.
     */
    private static Signal getRawSignal_Rsi(List<KlineObjectSimple> klines) {
        int rsiPeriod = 14;
        double overbought = 70.0;
        double oversold = 30.0;
        if (klines == null || klines.size() < rsiPeriod + 2) return Signal.NONE;

        // RSI của nến hiện tại
        double currentRSI = TechnicalAnalysisUtils.calculateRSI(klines, rsiPeriod);

        // RSI của nến trước đó
        List<KlineObjectSimple> previousKlines = klines.subList(0, klines.size() - 1);
        double previousRSI = TechnicalAnalysisUtils.calculateRSI(previousKlines, rsiPeriod);

        if (previousRSI < 0 || currentRSI < 0) return Signal.NONE;

        // Tín hiệu MUA: RSI vừa cắt lên khỏi vùng quá bán
        if (previousRSI <= oversold && currentRSI > oversold) return Signal.BUY;

        // Tín hiệu BÁN: RSI vừa cắt xuống khỏi vùng quá mua
        if (previousRSI >= overbought && currentRSI < overbought) return Signal.SELL;

        return Signal.NONE;
    }


    // =================================================================================
    // == CÁC CHIẾN LƯỢC CHẤT LƯỢNG CAO (HIGH-QUALITY STRATEGIES)                  ==
    // == Đây là những hàm bạn nên gọi từ bên ngoài                                  ==
    // =================================================================================

    /**
     * CHIẾN LƯỢC 1: Tín hiệu RSI được lọc bởi XU HƯỚỚNG DÀI HẠN.
     *
     * @param klines Dữ liệu nến 1 phút.
     * @return Tín hiệu đã được lọc.
     */
    public static Signal getSignal_RsiWithTrendFilter(List<KlineObjectSimple> klines) {
        int trendPeriod = 200; // Dùng SMA200 để xác định xu hướng
        if (klines == null || klines.size() < trendPeriod) return Signal.NONE;

        double longTermSMA = TechnicalAnalysisUtils.calculateSMA(klines, trendPeriod);
        double currentPrice = klines.get(klines.size() - 1).priceClose;

        // Lấy tín hiệu RSI gốc
        Signal rsiSignal = getRawSignal_Rsi(klines);

        // Áp dụng bộ lọc xu hướng
        if (currentPrice > longTermSMA) { // Đang trong xu hướng TĂNG
            if (rsiSignal == Signal.BUY) {
                return Signal.BUY; // Chỉ chấp nhận tín hiệu MUA
            }
        } else if (currentPrice < longTermSMA) { // Đang trong xu hướng GIẢM
            if (rsiSignal == Signal.SELL) {
                return Signal.SELL; // Chỉ chấp nhận tín hiệu BÁN
            }
        }

        // Bỏ qua tất cả các tín hiệu khác
        return Signal.NONE;
    }

    /**
     * CHIẾN LƯỢC NÂNG CAO 2: Tín hiệu RSI được xác nhận bởi Bollinger Bands và lọc bởi XU HƯỚNG.
     * Đây là chiến lược cho tín hiệu chất lượng cao và chọn lọc nhất.
     *
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
        if (klines == null || klines.size() < trendPeriod) {
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
     * CHIẾN LƯỢC 2: Kết hợp tín hiệu MA Crossover và RSI, đồng thời lọc bởi XU HƯỚNG.
     *
     * @param klines Dữ liệu nến 1 phút.
     * @return Tín hiệu đã được xác nhận bởi nhiều yếu tố.
     */
    public static Signal getSignal_CombinedWithTrendFilter(List<KlineObjectSimple> klines) {
        int trendPeriod = 200;
        if (klines.size() < trendPeriod) return Signal.NONE;

        // Lấy các tín hiệu gốc
        Signal maSignal = getRawSignal_MovingAverageCrossover(klines);
        Signal rsiSignal = getRawSignal_Rsi(klines);

        // Lọc theo xu hướng
        double longTermSMA = TechnicalAnalysisUtils.calculateSMA(klines, trendPeriod);
        double currentPrice = klines.get(klines.size() - 1).priceClose;

        if (currentPrice > longTermSMA) { // Xu hướng TĂNG
            // Yêu cầu cả hai chỉ báo đều cho tín hiệu MUA
            if (maSignal == Signal.BUY && rsiSignal == Signal.BUY) {
                return Signal.BUY;
            }
        } else if (currentPrice < longTermSMA) { // Xu hướng GIẢM
            // Yêu cầu cả hai chỉ báo đều cho tín hiệu BÁN
            if (maSignal == Signal.SELL && rsiSignal == Signal.SELL) {
                return Signal.SELL;
            }
        }

        return Signal.NONE;
    }
}