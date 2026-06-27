package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.object.MarketLevelChange;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

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


    public static float calRateLossDynamicBuy(float maxProfitRate, Float predReturn15M) {
        // Khoảng trailing tối đa: siết chặt khi momentum dự đoán yếu
        float maxGap = (predReturn15M != null && predReturn15M < Configs.TS_WEAK_MOMENTUM_THRES)
                ? Configs.TS_MAX_GAP_WEAK    // 0.03f  (= 6 đơn vị cũ)
                : Configs.TS_MAX_GAP;        // 0.08f  (= 16 đơn vị cũ)

        // Nhả lại tối đa nửa lợi nhuận, nhưng không vượt maxGap
        float gap = Math.min(maxProfitRate * 0.5f, maxGap);

        // Lãi còn lại sau khi trừ gap chính là mức stop mới
        float rate = maxProfitRate - gap;
        float step = 0.005f;
        rate = Math.round(rate / step) * step;
        return rate;
    }

    public static Float calRateMinWithPredReturn15MForTradingStop(Float predReturn15M) {
        Float rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;

        // 🔥 LOGIC MỚI: Dùng hệ số nhân K tuyến tính theo biên độ nến
        if (predReturn15M != null && predReturn15M > 0) {
            float dynamicRate = predReturn15M * Configs.TS_DYNAMIC_K;
            if (dynamicRate > rateMin2MoveSl) {
                rateMin2MoveSl = dynamicRate;
            }
        }
        return rateMin2MoveSl;
    }

    public static Float managerBudget(Float budget, Float marginRunning, Float balanceBasic,
                                      MarketLevelChange levelChange) {


        final Set<MarketLevelChange> dcaOrBigLevels = Set.of(
                MarketLevelChange.DCA_LEVEL1
        );
        boolean isNormalLevel = !dcaOrBigLevels.contains(levelChange)
                && !StringUtils.containsIgnoreCase(levelChange.toString(), "big")
                && !StringUtils.containsIgnoreCase(levelChange.toString(), "medium");
        float marginRatio = marginRunning / balanceBasic;

        // === THAY ĐỔI 1: SỬ DỤNG BIẾN CONFIGS ===
        // [OFF-CỨNG] BUDGET_DIVIDER_1 thuộc cụm phẳng → bỏ tầng chia vốn này.
        if (!Configs.OFF_FLAT_HARD && isNormalLevel && marginRatio >= Configs.BUDGET_MARGIN_RATIO_1) {
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
//            case MEDIUM_DOWN:
//                budget /= 2;
//                break;

            case DCA_LEVEL1:
            case PREDICT_SYMBOL_TRADE:
            case SMALL_UP:
            case SMALL_DOWN_15M:
                budget /= 3;
                break;

//                budget /= 4;
//                break;
        }

        return budget;
    }
}
