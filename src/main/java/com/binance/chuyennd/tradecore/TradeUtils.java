package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;
import java.util.Set;

public class TradeUtils {
    public static final Logger LOG = LoggerFactory.getLogger(TradeUtils.class);

    public static void main(String[] args) {
//        for (int i = 0; i < 100; i++) {
//            Float rate = 0.01 + i * 0.001;
//            LOG.info("{} {}", rate, TradeUtils.calRateLossDynamicBuy(rate));
//        }
//        System.out.println(TradeUtils.calRateMinWithMaxChange60MForTradingStop(0d, null));
    }

    public static Float calRateLossDynamicBuy(Float unProfit, Float maxChange90M) {
        Float rateLoss = unProfit * 200;
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
        rateLoss = rateLoss.longValue() - tradingStopRate.floatValue();
        return rateLoss / 200;
    }

    public static Float calRateMinWithMaxChange60MForTradingStop(Float maxChange90M) {
        // Sử dụng biến từ Configs thay vì số cứng
        Float rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;

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

    public static Float managerBudget(Float budget, Float marginRunning, Float balanceBasic,
                                      MarketLevelChange levelChange) {


        final Set<MarketLevelChange> dcaOrBigLevels = Set.of(
                MarketLevelChange.DCA_LEVEL1,
                MarketLevelChange.DCA_LEVEL2
        );
        boolean isNormalLevel = !dcaOrBigLevels.contains(levelChange)
                && !StringUtils.containsIgnoreCase(levelChange.toString(), "big")
                && !StringUtils.containsIgnoreCase(levelChange.toString(), "medium");
        float marginRatio = marginRunning / balanceBasic;

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
            case MEDIUM_UP:
                budget /= 2;
                break;

            case DCA_LEVEL1:
            case SMALL_DOWN:
            case MEDIUM_DOWN_15M:
            case DCA_LEVEL2:
            case BTC_TREND_REVERSE:
            case PREDICT_SYMBOL_TRADE:
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
