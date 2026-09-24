package com.binance.chuyennd.tradecore;

/**
 * PRE-ARM HARD STOP-LOSS (2026-09-05, X2) — cong cat lo cho cum CHUA arm trailing.
 *
 * <p>Nguong do tren {@code firstEntryPrice} (gia vao leg DAU cua cum) chu KHONG phai
 * {@code priceEntry} (gia binh quan) => muc cat khong noi long khi cum bi nhoi DCA.
 *
 * <p>Mac dinh {@code SIM_PRE_ARM_SL = 0} => {@link #enabled()} false => byte-identical voi truoc X2.
 *
 * <p>[SL-ADAPTIVE 2026-09-12] Them ban {@code *Val(...)} nhan {@code preArmSl} tuong minh de lever A
 * (SL_ADAPT_HARDSL) chon muc cat theo selRank cua cum. Ban khong tham so goi {@code *Val} voi
 * {@code Configs.PRE_ARM_SL} => arithmetic IEEE-identical hanh vi cu. Xem docs/prereg/PREREG_SL_ADAPTIVE_SWEEP.md.
 */
public final class PreArmSlUtils {

    private PreArmSlUtils() {
    }

    /** Gia tri AM moi co nghia (vd -0.20 = cat khi lo 20%); 0 hoac duong = TAT. */
    public static boolean enabledVal(float preArmSl) {
        return preArmSl < 0f;
    }

    /** Muc gia kich hoat, do tren gia vao leg DAU (BAT BIEN qua DCA). */
    public static float stopLevelVal(float firstEntryPrice, float preArmSl) {
        return firstEntryPrice * (1f + preArmSl);
    }

    /** Nen hien tai co cham nguong khong. Dung {@code bar.minPrice} (doi xung cong arm dung maxPrice). */
    public static boolean hitVal(Float firstEntryPrice, float barLow, float preArmSl) {
        if (!enabledVal(preArmSl) || firstEntryPrice == null || firstEntryPrice <= 0f) {
            return false;
        }
        return barLow <= stopLevelVal(firstEntryPrice, preArmSl);
    }

    /** Gia dong: KHONG BAO GIO tot hon muc stop (chan look-ahead), XAU HON neu nen dong duoi (chiu gap). */
    public static float exitPriceVal(float firstEntryPrice, float barOpen, float barClose, float preArmSl) {
        return Math.min(stopLevelVal(firstEntryPrice, preArmSl), Math.min(barOpen, barClose));
    }

    // --- Ban khong tham so: uy quyen sang *Val voi Configs.PRE_ARM_SL (byte-identical hanh vi cu) ---

    public static boolean enabled() {
        return enabledVal(Configs.PRE_ARM_SL);
    }

    public static float stopLevel(float firstEntryPrice) {
        return stopLevelVal(firstEntryPrice, Configs.PRE_ARM_SL);
    }

    public static boolean hit(Float firstEntryPrice, float barLow) {
        return hitVal(firstEntryPrice, barLow, Configs.PRE_ARM_SL);
    }

    public static float exitPrice(float firstEntryPrice, float barOpen, float barClose) {
        return exitPriceVal(firstEntryPrice, barOpen, barClose, Configs.PRE_ARM_SL);
    }
}
