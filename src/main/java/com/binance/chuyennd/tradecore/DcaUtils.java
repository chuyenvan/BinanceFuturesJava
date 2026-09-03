package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class DcaUtils {
    public static final Logger LOG = LoggerFactory.getLogger(DcaUtils.class);
    // Private constructor để ngăn việc khởi tạo đối tượng từ lớp tiện ích
    private DcaUtils() {
    }

    /**
     * DCA GRID (2026-08-01) — thay logic phan xa bang GRID CO KE HOACH.
     *
     * <p>Khac DCA cu o 3 diem, moi diem sua mot loi da do duoc:
     * <ol>
     *   <li>Do muc lo tren {@code firstEntryPrice} (BAT BIEN qua DCA) thay vi {@code avgEntry}.
     *       Cu: avgEntry tut sau moi lan nhoi => muc lo reset => khoang cach nhoi CO LAI DAN
     *       (15% -> 8.1% -> 5.5% -> 4.4%), tuc cang lo sau cang nhoi day. Moi: khoang cach GIAN
     *       dung nhu thiet ke.</li>
     *   <li>TRAN so leg = do dai grid. Cu khong co tran nao.</li>
     *   <li>KHONG phu thuoc market level => bo duoc {@code isAll=true} cua BIG_DOWN (cai tat thang
     *       chan margin dung luc thi truong sap manh nhat).</li>
     * </ol>
     *
     * @param firstEntryPrice gia vao leg DAU cua cum (khong phai avgEntry)
     * @param lastPrice       gia hien tai
     * @param legCount        so leg da khop (1 = chua nhoi)
     */
    public static boolean shouldDcaGrid(Float firstEntryPrice, Float lastPrice, int legCount) {
        if (firstEntryPrice == null || lastPrice == null || firstEntryPrice <= 0) return false;
        // 2026-08-01 (HPO-ready): doc qua Configs.dcaGridLevel()/dcaGridLegs() thay vi cham thang mang
        // DCA_GRID_LEVELS. Ly do: HPO/WFO ap gene bang reflection len FIELD SCALAR — neu ham nay doc
        // mang thi gene DCA_GRID_L1/STEP/LEGS set xong KHONG co tac dung nao (loi im lang, rat kho thay).
        // Khi DCA_GRID_SCALAR=false, accessor tra dung phan tu mang cu => byte-identical.
        if (legCount < 1 || legCount > Configs.dcaGridLegs()) return false;   // het bac grid -> khong nhoi nua
        float level = Configs.dcaGridLevel(legCount - 1);
        if (level >= 0f) return false;                                  // 0f = het bac (guard kep)
        float drop = lastPrice / firstEntryPrice - 1f;                  // am khi lo
        return drop <= level;
    }

    /** Ti trong cho leg sap khop (0-based theo legCount hien tai), quy ve ti le tren TONG, x SCALE.
     *  SCALE bu lai phan du tru hiem khi dung (chi 0.34% cum cham day) — xem Configs.DCA_GRID_SCALE. */
    public static float gridLegWeightRatio(int legCount) {
        if (legCount < 0 || legCount > Configs.dcaGridLegs()) return 0f;
        float w = Configs.dcaGridWeight(legCount);
        if (w <= 0f) return 0f;
        float total = Configs.dcaGridTotalWeight();
        if (total <= 0f) return 0f;
        return (w / total) * Configs.DCA_GRID_SCALE;
    }

    /**
     * Phương thức chính, chỉ nhận vào các tham số đơn để kiểm tra.
     * Đây là hàm duy nhất bạn cần gọi từ bên ngoài.
     */
    public static boolean shouldDca(Float margin, float currentRateLoss, MarketLevelChange orderMarketLevel, long orderTimeStart,
                                    MarketLevelChange marketLevelChange, long currentTime, float budget) {
        DcaConfig config = getDcaConfig(marketLevelChange);
        if (config == null) {
            return false;
        }
        if (margin == null) {
            LOG.info("DCA SKIP - margin is null. orderMarketLevel={}, orderTimeStart={}, marketLevelChange={}, currentTime={}, budget={}",
                    orderMarketLevel, orderTimeStart, marketLevelChange, currentTime, budget);
            return false;
        }

        float adjustedRateLoss = calculateAdjustedRateLoss(margin, budget, config.getRateLoss2Dca(), config.isAll());

        if (currentRateLoss >= adjustedRateLoss) {
            return false;
        }

        return isTimeConditionMet(orderMarketLevel, orderTimeStart, currentTime, config.getDurationDca());

    }

    // --- CÁC PHƯƠNG THỨC HỖ TRỢ (PRIVATE) ---

    private static DcaConfig getDcaConfig(MarketLevelChange levelChange) {
        if (levelChange == null) return new DcaConfig(1, -0.4f, false);
        switch (levelChange) {
            case BIG_DOWN:
                return new DcaConfig(Configs.DCA_TIME_BIG_DOWN, Configs.DCA_LOSS_BIG_DOWN, true);
//            case MEDIUM_DOWN:
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

        boolean isSpecialDcaLevel = true;
        if (orderMarketLevel != null) isSpecialDcaLevel = orderMarketLevel.equals(MarketLevelChange.DCA_LEVEL1);
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