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

    /**
     * Thuật toán: Inventory-based Dynamic Threshold (Hệ số Khát lệnh theo Sức chứa)
     *
     * @param runningOrders Map chứa các lệnh ĐANG CHẠY (Giống đầu vào của is50PercentOrderLoss)
     * @param currentTime   Thời gian của nến hiện tại
     * @return Hệ số Multiplier dao động từ 0.5 (Rất đói/dễ dãi) đến 1.3 (Đang kẹp hàng/khó tính)
     */
    public static float getHungerMultiplier(Map<String, OrderTargetInfoTest> runningOrders, long currentTime) {
        // --- 1. CẤU HÌNH (Bạn có thể chuyển 3 biến này sang Configs.java để HPO tối ưu) ---
        float HUNGER_MAX_RELAX = 0.5f;   // Sàn: Rương trống trơn -> Nới lỏng tiêu chuẩn 50%
        float HUNGER_MAX_STRICT = 1.3f;  // Trần: Đang kẹp nhiều hàng -> Siết chặt tiêu chuẩn thêm 30%
        int HUNGER_TARGET_TRADES = 6;    // Mốc cân bằng: Đang ôm 6 lệnh thì tiêu chuẩn bình thường (x1.0)
        long LOOKBACK_MINS = 1440;       // (Tùy chọn) Chỉ tính các lệnh kẹp trong 24h qua

        if (runningOrders == null || runningOrders.isEmpty()) {
            return HUNGER_MAX_RELAX; // Rương trống -> Xả láng đi tìm mồi
        }

        // --- 2. ĐẾM SỐ LỆNH ĐANG ÔM (Có tính thời gian) ---
        int activeCount = 0;
        for (OrderTargetInfoTest order : runningOrders.values()) {
            if (order == null) continue;

            long diffMins = (currentTime - order.timeStart) / 60000L;
            if (diffMins <= LOOKBACK_MINS) {
                activeCount++;
            }
        }

        // --- 3. TÍNH TOÁN ĐƯỜNG CONG "ĐỘ KHÁT" ---
        float fillRatio = (float) activeCount / HUNGER_TARGET_TRADES;
        float multiplier;

        if (fillRatio < 1.0f) {
            // ĐANG ĐÓI (Ôm < 6 lệnh): Nội suy tuyến tính từ 0.5 lên 1.0
            // VD: 0 lệnh -> 0.5 | 3 lệnh -> 0.75 | 6 lệnh -> 1.0
            multiplier = HUNGER_MAX_RELAX + fillRatio * (1.0f - HUNGER_MAX_RELAX);
        } else {
            // ĐANG KẸP HÀNG (Ôm >= 6 lệnh): Phạt thêm 10% độ khó cho mỗi lệnh vượt mốc
            // VD: 6 lệnh -> 1.0 | 8 lệnh -> 1.0 + (1.33-1)*0.1 ~ 1.03
            multiplier = 1.0f + (fillRatio - 1.0f) * 0.10f;
        }

        // --- 4. CHỐT CHẶN AN TOÀN ---
        return Math.max(HUNGER_MAX_RELAX, Math.min(multiplier, HUNGER_MAX_STRICT));
    }
}
