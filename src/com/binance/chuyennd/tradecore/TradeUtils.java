package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

public class TradeUtils {
    public static final Logger LOG = LoggerFactory.getLogger(TradeUtils.class);

    public static void main(String[] args) {
        for (int i = 0; i < 100; i++) {
            Double rate = 0.01 + i * 0.001;
            LOG.info("{} {}", rate, TradeUtils.calRateLossDynamicBuy(rate));
        }
    }

    public static Double calRateLossDynamicBuy(Double unProfit) {
        Double rateLoss = unProfit * 200;
        Long tradingStopRate;
        Long maxRateTradingStop = 10l;
        if (rateLoss < maxRateTradingStop * 2) {
            tradingStopRate = rateLoss.longValue() / 2;
        } else {
            tradingStopRate = maxRateTradingStop;
        }
        rateLoss = rateLoss.longValue() - tradingStopRate.doubleValue();
        return rateLoss / 200;
    }

    public static Double calRateMinWithMaxChange60M(Double maxChange15M) {
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
                        if (rateMin2MoveSl < 0.05) {
                            rateMin2MoveSl = 0.05;
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
        // 3. Tham số cho bộ lọc "Thị trường ảm đạm"
        double MIN_MOVEMENT_RANGE_THRESHOLD = 0.03;
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


    public static Double managerBudget(Double budget, Double marginRunning, Double balanceBasic, MarketLevelChange levelChange, Boolean isTrendBuyWithBtc) {
        if (marginRunning >= balanceBasic * 0.25
                && !levelChange.equals(MarketLevelChange.DCA_LEVEL1)
                && !levelChange.equals(MarketLevelChange.DCA_LEVEL2)
                && !StringUtils.containsIgnoreCase(levelChange.toString(), "big")
        ) {
            budget = budget / 2;
        }
        if (marginRunning >= balanceBasic * 0.35
                && !levelChange.equals(MarketLevelChange.DCA_LEVEL1)
                && !levelChange.equals(MarketLevelChange.DCA_LEVEL2)
                && !StringUtils.containsIgnoreCase(levelChange.toString(), "big")
        ) {
            return null;
        }
        if (marginRunning >= balanceBasic * 0.45) {
            budget = budget / 2;
        }
        if (marginRunning >= balanceBasic * 0.6) {
            return null;
        }
        if (levelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_UP)
                || levelChange.equals(MarketLevelChange.DCA_LEVEL1)
        ) {
            budget = budget / 2;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                || levelChange.equals(MarketLevelChange.FUNDING_FEE_BUY)
                || levelChange.equals(MarketLevelChange.FUNDING_FEE_BUY_SPECIAL)
                || levelChange.equals(MarketLevelChange.DCA_LEVEL2)
                || levelChange.equals(MarketLevelChange.BTC_TREND_REVERSE)
        ) {
            budget = budget / 3;
        }
        if (levelChange.equals(MarketLevelChange.SMALL_UP)
                || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
        ) {
            if (isTrendBuyWithBtc) {
                budget = budget / 4;
            } else {
                return null;
            }
        }
        return budget;
    }
}
