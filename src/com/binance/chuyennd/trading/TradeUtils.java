package com.binance.chuyennd.trading;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

public class TradeUtils {
    public static final Logger LOG = LoggerFactory.getLogger(TradeUtils.class);

    public static Double calRateMinWithMaxChange15M(Double maxChange15M) {
        Double rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;
        if (maxChange15M != null && maxChange15M > 0.006) {
            if (maxChange15M < 0.01) {
                if (rateMin2MoveSl < 0.02) {
                    rateMin2MoveSl = 0.02;
                }
            } else {
                if (maxChange15M < 0.02) {
                    if (rateMin2MoveSl < 0.025) {
                        rateMin2MoveSl = 0.025;
                    }
                } else {
                    if (maxChange15M < 0.03) {
                        if (rateMin2MoveSl < 0.04) {
                            rateMin2MoveSl = 0.04;
                        }
                    } else {
                        if (rateMin2MoveSl < 0.06) {
                            rateMin2MoveSl = 0.06;
                        }
                    }
                }
            }
        } else {
            if (maxChange15M != null && maxChange15M > 0.004) {
                if (rateMin2MoveSl < 0.015) {
                    rateMin2MoveSl = 0.015;
                }
            }
        }
        return rateMin2MoveSl;
    }

    public static boolean shouldAvoidEntry(String symbol, List<KlineObjectSimple> recentTickers) {
        // ================== CÁC THAM SỐ CÓ THỂ TÙY CHỈNH ==================
        // 1. Chu kỳ xem xét để tính toán đỉnh/đáy (ví dụ: 15 phút)
        final int PRICE_LOOKBACK_PERIOD = 15;

        // 2. Tham số cho bộ lọc "Vòng xoáy tử thần"
        final double MIN_DOW_THRESHOLD = -0.05;
        final double MIN_BOUNCE_RATIO_THRESHOLD = 0.35;

        // 3. Tham số cho bộ lọc "Thị trường ảm đạm"
        final double MIN_MOVEMENT_RANGE_THRESHOLD = 0.045;
        // =================================================================

        // --- Bước 1: Kiểm tra dữ liệu đầu vào ---
        if (recentTickers == null || recentTickers.size() < PRICE_LOOKBACK_PERIOD) {
            return false; // Không đủ dữ liệu, tạm thời cho phép
        }

        // --- Bước 2: Tính toán các chỉ số dow (rateFromMax) và up (rateFromMin) ---
        double currentClose = recentTickers.get(recentTickers.size() - 1).priceClose;
        double periodHigh = 0;
        double periodMin = Double.MAX_VALUE;
        int startIndex = recentTickers.size() - PRICE_LOOKBACK_PERIOD;

        for (int i = startIndex; i < recentTickers.size(); i++) {
            KlineObjectSimple candle = recentTickers.get(i);
            if (candle.maxPrice > periodHigh) {
                periodHigh = candle.maxPrice;
            }
            if (candle.minPrice < periodMin) {
                periodMin = candle.minPrice;
            }
        }

        if (periodHigh == 0 || periodMin == 0) return false; // Dữ liệu bất thường, bỏ qua

        double dow = (currentClose - periodHigh) / periodHigh;
        double up = (currentClose - periodMin) / periodMin;

        // --- Bước 3: Áp dụng các bộ lọc ---

        // Lọc 1: "Vòng xoáy tử thần"
//        if (dow < MIN_DOW_THRESHOLD) {
//            double bounceRatio = up / Math.abs(dow);
//            if (bounceRatio < MIN_BOUNCE_RATIO_THRESHOLD) {
//                LOG.warn("!!! TRÁNH VÀO LỆNH (Vòng xoáy tử thần): {} | Giảm {}%, Phục hồi {}%",
//                        symbol, String.format("%.2f", dow * 100), String.format("%.2f", up * 100));
//                return true;
//            }
//        }

        // Lọc 2: "Thị trường ảm đạm"
        double movementRange = Math.abs(dow) + up;
        if (movementRange < MIN_MOVEMENT_RANGE_THRESHOLD) {
            LOG.warn("!!! TRÁNH VÀO LỆNH (Thị trường ảm đạm): {} | Biến động chỉ {}%",
                    symbol, String.format("%.2f", movementRange * 100));
            return true;
        }

        // Nếu không rơi vào trường hợp nào, có thể vào lệnh
        return false;
    }
    public static boolean shouldAvoidEntryProduction(String symbol, List<KlineObjectNumber> recentTickers) {
        // ================== CÁC THAM SỐ CÓ THỂ TÙY CHỈNH ==================
        // 1. Chu kỳ xem xét để tính toán đỉnh/đáy (ví dụ: 15 phút)
        final int PRICE_LOOKBACK_PERIOD = 15;

        // 2. Tham số cho bộ lọc "Vòng xoáy tử thần"
        final double MIN_DOW_THRESHOLD = -0.05;
        final double MIN_BOUNCE_RATIO_THRESHOLD = 0.35;

        // 3. Tham số cho bộ lọc "Thị trường ảm đạm"
        final double MIN_MOVEMENT_RANGE_THRESHOLD = 0.045;
        // =================================================================

        // --- Bước 1: Kiểm tra dữ liệu đầu vào ---
        if (recentTickers == null || recentTickers.size() < PRICE_LOOKBACK_PERIOD) {
            return false; // Không đủ dữ liệu, tạm thời cho phép
        }

        // --- Bước 2: Tính toán các chỉ số dow (rateFromMax) và up (rateFromMin) ---
        double currentClose = recentTickers.get(recentTickers.size() - 1).priceClose;
        double periodHigh = 0;
        double periodMin = Double.MAX_VALUE;
        int startIndex = recentTickers.size() - PRICE_LOOKBACK_PERIOD;

        for (int i = startIndex; i < recentTickers.size(); i++) {
            KlineObjectNumber candle = recentTickers.get(i);
            if (candle.maxPrice > periodHigh) {
                periodHigh = candle.maxPrice;
            }
            if (candle.minPrice < periodMin) {
                periodMin = candle.minPrice;
            }
        }

        if (periodHigh == 0 || periodMin == 0) return false; // Dữ liệu bất thường, bỏ qua

        double dow = (currentClose - periodHigh) / periodHigh;
        double up = (currentClose - periodMin) / periodMin;

        // --- Bước 3: Áp dụng các bộ lọc ---

        // Lọc 1: "Vòng xoáy tử thần"
//        if (dow < MIN_DOW_THRESHOLD) {
//            double bounceRatio = up / Math.abs(dow);
//            if (bounceRatio < MIN_BOUNCE_RATIO_THRESHOLD) {
//                LOG.warn("!!! TRÁNH VÀO LỆNH (Vòng xoáy tử thần): {} | Giảm {}%, Phục hồi {}%",
//                        symbol, String.format("%.2f", dow * 100), String.format("%.2f", up * 100));
//                return true;
//            }
//        }

        // Lọc 2: "Thị trường ảm đạm"
        double movementRange = Math.abs(dow) + up;
        if (movementRange < MIN_MOVEMENT_RANGE_THRESHOLD) {
            LOG.warn("!!! TRÁNH VÀO LỆNH (Thị trường ảm đạm): {} | Biến động chỉ {}%",
                    symbol, String.format("%.2f", movementRange * 100));
            return true;
        }

        // Nếu không rơi vào trường hợp nào, có thể vào lệnh
        return false;
    }
}
