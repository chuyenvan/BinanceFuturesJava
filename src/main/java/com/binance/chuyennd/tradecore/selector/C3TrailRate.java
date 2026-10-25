package com.binance.chuyennd.tradecore.selector;

/**
 * [V12 C6 vong 2b] Cau noi PUBLIC toi cong thuc trailing cua so giay {@code ShadowBookC3.trailRate} (package-private) cho
 * duong lenh THAT c3_live ({@code c3live.exit.TrailingStopManager}). KHONG viet lai cong thuc: goi thang ham cua so giay
 * (=> {@code TradeUtils.calRateLossDynamicBuyPNoPump} + TRAIL_HINGE_NET015 neu bat) => cum that va cum giay cung dinh/
 * cung symbolPred cho ra CUNG gia tri float.
 */
public final class C3TrailRate {

    private C3TrailRate() {
    }

    /** {@code rate = peak - min(peak*giveback, gap(symbolPred))} — xem {@code ShadowBookC3.trailRate(float, Float, String)}. */
    public static float trailRate(float peakRate, Float symbolPred, String symbol) {
        return ShadowBookC3.trailRate(peakRate, symbolPred, symbol);
    }

    /** Nguong arm cua C3 (0.07, {@link LiveProfileC3#ARM_RATE}). */
    public static float armRate() {
        return LiveProfileC3.ARM_RATE;
    }

    /** Time-stop goc (gio) cua cum chua arm ({@link LiveProfileC3#TIME_STOP_HOURS}). */
    public static int timeStopHours() {
        return LiveProfileC3.TIME_STOP_HOURS;
    }
}
