package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;

public final class DcaUtils {

    // Private constructor để ngăn việc khởi tạo đối tượng từ lớp tiện ích
    private DcaUtils() {
    }

    /**
     * Phương thức chính, chỉ nhận vào các tham số đơn để kiểm tra.
     * Đây là hàm duy nhất bạn cần gọi từ bên ngoài.
     */
    public static boolean shouldDca(double margin, double currentRateLoss, MarketLevelChange orderMarketLevel, long orderTimeStart,
                                    MarketLevelChange marketLevelChange, long currentTime, double budget) {


        DcaConfig config = getDcaConfig(marketLevelChange);
        if (config == null) {
            return false;
        }

        double adjustedRateLoss = calculateAdjustedRateLoss(margin, budget, config.getRateLoss2Dca(), config.isAll());

        if (currentRateLoss >= adjustedRateLoss) {
            return false;
        }

        return isTimeConditionMet(orderMarketLevel, orderTimeStart, currentTime, config.getDurationDca());
    }

    // --- CÁC PHƯƠNG THỨC HỖ TRỢ (PRIVATE) ---

    private static DcaConfig getDcaConfig(MarketLevelChange levelChange) {
        if (levelChange == null) {
            return new DcaConfig(1, -0.25, false);
        }
        switch (levelChange) {
            case BIG_DOWN:
                return new DcaConfig(8, -0.05, true);
            case MEDIUM_DOWN:
            case BIG_UP:
                return new DcaConfig(15, -0.08, false);
            case MEDIUM_UP:
            case MEDIUM_DOWN_15M:
                return new DcaConfig(15, -0.15, false);
            case SMALL_DOWN:
                return new DcaConfig(15, -0.20, false);
            default:
                return null;
        }
    }

    private static double calculateAdjustedRateLoss(double margin, double budget, double baseRateLoss, boolean isAll) {
        if (isAll || margin < budget) {
            return baseRateLoss;
        }
        double marginRatio = margin / budget;
        if (marginRatio >= 4.0) return -0.99;
        if (marginRatio >= 3.0) return -0.9;
        if (marginRatio >= 2.0) return -0.7;
        if (marginRatio >= 1.5) return -0.6;
        return -0.4;
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
        private final double rateLoss2Dca;
        private final boolean isAll;

        public DcaConfig(int durationDca, double rateLoss2Dca, boolean isAll) {
            this.durationDca = durationDca;
            this.rateLoss2Dca = rateLoss2Dca;
            this.isAll = isAll;
        }

        public int getDurationDca() {
            return durationDca;
        }

        public double getRateLoss2Dca() {
            return rateLoss2Dca;
        }

        public boolean isAll() {
            return isAll;
        }
    }
}