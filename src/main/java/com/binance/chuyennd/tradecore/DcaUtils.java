package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.utils.Utils;

public final class DcaUtils {

    // Private constructor để ngăn việc khởi tạo đối tượng từ lớp tiện ích
    private DcaUtils() {
    }

    /**
     * Phương thức chính, chỉ nhận vào các tham số đơn để kiểm tra.
     * Đây là hàm duy nhất bạn cần gọi từ bên ngoài.
     */
    public static boolean shouldDca(float margin, float currentRateLoss, MarketLevelChange orderMarketLevel, long orderTimeStart,
                                    MarketLevelChange marketLevelChange, long currentTime, float budget) {
            DcaConfig config = getDcaConfig(marketLevelChange);
            if (config == null) {
                return false;
            }
//            if (!isTrendBuyWithETH) {
//                config.rateLoss2Dca = config.rateLoss2Dca * 1.5;
////            if (marketLevelChange != null){
////                config.rateLoss2Dca = config.rateLoss2Dca * 1.5;
////            }
//                if (config.rateLoss2Dca < -0.9) {
//                    config.rateLoss2Dca = -0.9;
//                }
//            }
            float adjustedRateLoss = calculateAdjustedRateLoss(margin, budget, config.getRateLoss2Dca(), config.isAll());

            if (currentRateLoss >= adjustedRateLoss) {
                return false;
            }

            return isTimeConditionMet(orderMarketLevel, orderTimeStart, currentTime, config.getDurationDca());

    }

    // --- CÁC PHƯƠNG THỨC HỖ TRỢ (PRIVATE) ---

    private static DcaConfig getDcaConfig(MarketLevelChange levelChange) {
        if (levelChange == null) {
            return new DcaConfig(1, -0.4f, false);
        }
        switch (levelChange) {
            case BIG_DOWN:
                return new DcaConfig(8, -0.15f, true);
            case MEDIUM_DOWN:
            case BIG_UP:
                return new DcaConfig(15, -0.28f, false);
//            case MEDIUM_UP:
//            case MEDIUM_DOWN_15M:
//                return new DcaConfig(15, -0.15, false);
//            case SMALL_DOWN:
//                return new DcaConfig(15, -0.20, false);
            default:
                return null;
        }
    }

    private static float calculateAdjustedRateLoss(float margin, float budget, float baseRateLoss, boolean isAll) {
        if (isAll || margin < budget) {
            return baseRateLoss;
        }
        float marginRatio = margin / budget;
        if (marginRatio >= 3.0) return -0.99f;
        if (marginRatio >= 2.5) return -0.9f;
        if (marginRatio >= 2.0) return -0.7f;
        if (marginRatio >= 1.5) return -0.6f;
        return -0.4f;
    }

    private static boolean isTimeConditionMet(MarketLevelChange orderMarketLevel, long orderTimeStart, long currentTime, int durationDca) {
        boolean isSpecialDcaLevel = orderMarketLevel.equals(MarketLevelChange.DCA_LEVEL2)
                || orderMarketLevel.equals(MarketLevelChange.DCA_LEVEL1);
        if (isSpecialDcaLevel) {
            return currentTime > orderTimeStart + (long) durationDca * Utils.TIME_MINUTE;
        }
        return true;
    }

    /**
     * Lớp private tĩnh để chứa dữ liệu cấu hình, tương thích với Java 11.
     */
    private static final class DcaConfig {
        private final int durationDca;
        private float rateLoss2Dca;
        private final boolean isAll;

        public DcaConfig(int durationDca, float rateLoss2Dca, boolean isAll) {
            this.durationDca = durationDca;
            this.rateLoss2Dca = rateLoss2Dca;
            this.isAll = isAll;
        }

        public int getDurationDca() {
            return durationDca;
        }

        public float getRateLoss2Dca() {
            return rateLoss2Dca;
        }

        public boolean isAll() {
            return isAll;
        }
    }
}