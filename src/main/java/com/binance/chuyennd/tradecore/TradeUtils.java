package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Set;

public class TradeUtils {
    public static final Logger LOG = LoggerFactory.getLogger(TradeUtils.class);

    public static void main(String[] args) {
//        for (int i = 0; i < 100; i++) {
//            Double rate = 0.01 + i * 0.001;
//            LOG.info("{} {}", rate, TradeUtils.calRateLossDynamicBuy(rate));
//        }
        System.out.println(TradeUtils.calRateMinWithMaxChange60MForTradingStop(0d));
    }

    public static Double calRateLossDynamicBuy(Double unProfit) {
        Double rateLoss = unProfit * 200;
        Long tradingStopRate;
        Long maxRateTradingStop = 16l;
        if (rateLoss < maxRateTradingStop * 2) {
            tradingStopRate = rateLoss.longValue() / 2;
        } else {
            tradingStopRate = maxRateTradingStop;
        }
        rateLoss = rateLoss.longValue() - tradingStopRate.doubleValue();
        return rateLoss / 200;
    }

    public static Double calRateMinWithMaxChange60MForTradingStop(Double maxChange60M) {
        Double rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;
        if (maxChange60M != null) {
            if (maxChange60M >= 0.01) {
                rateMin2MoveSl = Math.max(rateMin2MoveSl, 0.03);
            } else if (maxChange60M >= 0.008) {
                rateMin2MoveSl = Math.max(rateMin2MoveSl, 0.024);
            } else if (maxChange60M >= 0.006) {
                rateMin2MoveSl = Math.max(rateMin2MoveSl, 0.018);
            } else if (maxChange60M >= 0.004) {
                rateMin2MoveSl = Math.max(rateMin2MoveSl, 0.016);
            }
        }
        return rateMin2MoveSl;
    }

    public static boolean shouldAvoidEntry(String symbol, List<KlineObjectSimple> recentTickers) {
        // ================== CÁC THAM SỐ CÓ THỂ TÙY CHỈNH ==================
        // 1. Chu kỳ xem xét để tính toán đỉnh/đáy (ví dụ: 15 phút)
        final int PRICE_LOOKBACK_PERIOD = 15;
        // 3. Tham số cho bộ lọc "Thị trường ảm đạm"
        double MIN_MOVEMENT_RANGE_THRESHOLD = 0.03;
        double MIN_VOLUME_TRADING = 200 * 1000;
        // =================================================================

        if (Constants.specialSymbol.contains(symbol) || Constants.stableSymbol.contains(symbol)) {
            return false;
        }
        // --- Bước 1: Kiểm tra dữ liệu đầu vào ---
        if (recentTickers == null || recentTickers.size() < PRICE_LOOKBACK_PERIOD) {
            return false; // Không đủ dữ liệu, tạm thời cho phép
        }

        // --- Bước 2: Tính toán các chỉ số dow (rateFromMax) và up (rateFromMin) ---
        double currentClose = recentTickers.get(recentTickers.size() - 1).priceClose;
        double periodHigh = 0;
        double periodMin = Double.MAX_VALUE;
        double totalVolume = 0;
        int startIndex = recentTickers.size() - PRICE_LOOKBACK_PERIOD;

        for (int i = startIndex; i < recentTickers.size(); i++) {
            KlineObjectSimple candle = recentTickers.get(i);
            if (candle.maxPrice > periodHigh) {
                periodHigh = candle.maxPrice;
            }
            if (candle.minPrice < periodMin) {
                periodMin = candle.minPrice;
            }
            totalVolume += candle.totalUsdt;
        }
        if (periodHigh == 0 || periodMin == 0) return false; // Dữ liệu bất thường, bỏ qua

        double dow = (currentClose - periodHigh) / periodHigh;
        double up = (currentClose - periodMin) / periodMin;

        // Lọc 2: "Thị trường ảm đạm"
        double movementRange = Math.abs(dow) + up;
        if (movementRange < MIN_MOVEMENT_RANGE_THRESHOLD || totalVolume < MIN_VOLUME_TRADING) {
            LOG.warn("!!! TRÁNH VÀO LỆNH (Thị trường ảm đạm): {} | Biến động chỉ {}% ",
                    symbol, String.format("%.2f", movementRange * 100));
            return true;
        }
        // Nếu không rơi vào trường hợp nào, có thể vào lệnh
        return false;
    }


    public static Double managerBudget(Double budget, Double marginRunning, Double balanceBasic,
                                       MarketLevelChange levelChange, Boolean isTrendBuyWithBtc) {

        final Set<MarketLevelChange> dcaOrBigLevels = Set.of(
                MarketLevelChange.DCA_LEVEL1,
                MarketLevelChange.DCA_LEVEL2
        );
        boolean isNormalLevel = !dcaOrBigLevels.contains(levelChange)
                && !StringUtils.containsIgnoreCase(levelChange.toString(), "big");
        double marginRatio = marginRunning / balanceBasic;

        if (marginRatio >= 0.5) {
            budget /= 4;
        }
        if (marginRatio >= 0.6) {
            return null;
        }
        if (isNormalLevel && marginRatio >= 0.25) {
            budget /= 3;
        }

        if (levelChange.equals(MarketLevelChange.SMALL_UP)
                || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)) {
            if (!isTrendBuyWithBtc) {
                return null;
            }
        }

        if (marginRatio >= 0.35) {
            budget /= 2;
        }
        if (isNormalLevel && marginRatio >= 0.2) {
            budget /= 2;
        }
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
