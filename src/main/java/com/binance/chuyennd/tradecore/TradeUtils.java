package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.utils.Configs;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Set;

public class TradeUtils {
    public static final Logger LOG = LoggerFactory.getLogger(TradeUtils.class);

    public static void main(String[] args) {
//        for (int i = 0; i < 100; i++) {
//            Double rate = 0.01 + i * 0.001;
//            LOG.info("{} {}", rate, TradeUtils.calRateLossDynamicBuy(rate));
//        }
//        System.out.println(TradeUtils.calRateMinWithMaxChange60MForTradingStop(0d, null));
    }

    public static Double calRateLossDynamicBuy(Double unProfit, Double maxChange90M) {
        Double rateLoss = unProfit * 200;
        Long tradingStopRate;
        Long maxRateTradingStop = 16l;
        if (maxChange90M < 0.004) {
            maxRateTradingStop = 6l;
        }
        if (rateLoss < maxRateTradingStop * 2) {
            tradingStopRate = rateLoss.longValue() / 2;
        } else {
            tradingStopRate = maxRateTradingStop;
        }
        rateLoss = rateLoss.longValue() - tradingStopRate.doubleValue();
        return rateLoss / 200;
    }

    public static Double calRateMinWithMaxChange60MForTradingStop(Double maxChange90M) {
        // Sử dụng biến từ Configs thay vì số cứng
        Double rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;

        if (maxChange90M != null) {
            // Logic cũ: 0.01 -> 0.03
            if (maxChange90M >= Configs.TS_VOL_HIGH_THRES) {
                rateMin2MoveSl = Configs.TS_RATE_HIGH;
            }
            // Logic cũ: 0.006 -> 0.02
            else if (maxChange90M >= Configs.TS_VOL_MED_THRES) {
                rateMin2MoveSl = Configs.TS_RATE_MED;
            }
            // Logic cũ: 0.004 -> 0.016
            else if (maxChange90M >= Configs.TS_VOL_LOW_THRES) {
                rateMin2MoveSl = Configs.TS_RATE_LOW;
            }
        }
        return rateMin2MoveSl;
    }

//    public static boolean shouldAvoidEntry(String symbol, List<KlineObjectSimple> recentTickers, Boolean isTrendBuyWithETH) {
//        // ================== CÁC THAM SỐ CÓ THỂ TÙY CHỈNH ==================
//        // 1. Chu kỳ xem xét để tính toán đỉnh/đáy (ví dụ: 15 phút)
//        final int PRICE_LOOKBACK_PERIOD = 15;
//        // 3. Tham số cho bộ lọc "Thị trường ảm đạm"
//        double MIN_MOVEMENT_RANGE_THRESHOLD = 0.02;
//        if (!isTrendBuyWithETH) {
//            MIN_MOVEMENT_RANGE_THRESHOLD = 0.03;
//        }
//        double MIN_VOLUME_TRADING = 50 * 1000;
//        // =================================================================
//
//        if (Constants.specialSymbol.contains(symbol) || Constants.stableSymbol.contains(symbol)) {
//            return false;
//        }
//        // --- Bước 1: Kiểm tra dữ liệu đầu vào ---
//        if (recentTickers == null || recentTickers.size() < PRICE_LOOKBACK_PERIOD) {
//            return false; // Không đủ dữ liệu, tạm thời cho phép
//        }
//
//        // --- Bước 2: Tính toán các chỉ số dow (rateFromMax) và up (rateFromMin) ---
//        double currentClose = recentTickers.get(recentTickers.size() - 1).priceClose;
//        double periodHigh = 0;
//        double periodMin = Double.MAX_VALUE;
//        double totalVolume = 0;
//        double maxChange = 0;
//        int startIndex = recentTickers.size() - PRICE_LOOKBACK_PERIOD;
//
//        for (int i = startIndex; i < recentTickers.size(); i++) {
//            KlineObjectSimple candle = recentTickers.get(i);
//            if (candle.maxPrice > periodHigh) {
//                periodHigh = candle.maxPrice;
//            }
//            if (candle.minPrice < periodMin) {
//                periodMin = candle.minPrice;
//            }
//            if (maxChange < Utils.rateOf2Double(candle.maxPrice, candle.minPrice)) {
//                maxChange = Utils.rateOf2Double(candle.maxPrice, candle.minPrice);
//            }
//            totalVolume += candle.totalUsdt;
//        }
//        if (periodHigh == 0 || periodMin == 0) return false; // Dữ liệu bất thường, bỏ qua
//
//        double dow = (currentClose - periodHigh) / periodHigh;
//        double up = (currentClose - periodMin) / periodMin;
//
//        // Lọc 2: "Thị trường ảm đạm"
//        double movementRange = Math.abs(dow) + up;
//        if (movementRange < MIN_MOVEMENT_RANGE_THRESHOLD
//                || totalVolume < MIN_VOLUME_TRADING
//                || maxChange < 0.01
//        ) {
////            LOG.warn("!!! TRÁNH VÀO LỆNH (Thị trường ảm đạm): {} | Biến động chỉ {}% ",
////                    symbol, String.format("%.2f", movementRange * 100));
//            return true;
//        }
//        // Nếu không rơi vào trường hợp nào, có thể vào lệnh
//        return false;
//    }

    public static Double managerBudget(Double budget, Double marginRunning, Double balanceBasic,
                                       MarketLevelChange levelChange) {


        final Set<MarketLevelChange> dcaOrBigLevels = Set.of(
                MarketLevelChange.DCA_LEVEL1,
                MarketLevelChange.DCA_LEVEL2
        );
        boolean isNormalLevel = !dcaOrBigLevels.contains(levelChange)
                && !StringUtils.containsIgnoreCase(levelChange.toString(), "big")
                && !StringUtils.containsIgnoreCase(levelChange.toString(), "medium");
        double marginRatio = marginRunning / balanceBasic;

        // === THAY ĐỔI 1: SỬ DỤNG BIẾN CONFIGS ===
        if (isNormalLevel && marginRatio >= Configs.BUDGET_MARGIN_RATIO_1) {
            budget /= Configs.BUDGET_DIVIDER_1;
        }
        if (marginRatio >= Configs.BUDGET_MARGIN_RATIO_2) {
            budget /= Configs.BUDGET_DIVIDER_2;
        }

        // (Tôi giữ lại các logic cũ của bạn)
        if (marginRatio >= 0.9) {
            budget /= 4;
        }
        if (marginRatio >= 0.99) {
            return null;
        }

        // ... (Switch case của bạn giữ nguyên) ...
        // (Bạn cũng có thể tham số hóa các giá trị chia 2, 3, 4 này
        //  nhưng chúng ta sẽ làm 6 tham số trên trước)
        switch (levelChange) {
            case MEDIUM_DOWN:
            case DCA_LEVEL1:
            case MEDIUM_UP:
                budget /= 2;
                break;

            case SMALL_DOWN:
            case MEDIUM_DOWN_15M:
            case DCA_LEVEL2:
            case BTC_TREND_REVERSE:
            case FUNDING_FEE_BUY:
            case FUNDING_FEE_BUY_SPECIAL:
            case SMA_SIGNAL:
            case RSI_SIGNAL:
                budget /= 3;
                break;

            case SMALL_UP:
            case SMALL_DOWN_15M:
                budget /= 4;
                break;
        }

        return budget;
    }
}
