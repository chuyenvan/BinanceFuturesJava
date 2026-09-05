package com.binance.chuyennd.tradecore;

/**
 * PRE-ARM HARD STOP-LOSS (2026-09-05, X2) — cong cat lo cho cum CHUA arm trailing.
 *
 * <p>Boi canh: truoc X2 he KHONG co stop-loss nao truoc khi arm (+7%). Loi ra duy nhat la
 * {@code SIM_LOSER_TIME_STOP_HOURS} (cat PHANG theo gio, mac dinh 168h) — nghia la mot cum co the
 * roi 50-95% ma van duoc giu du 7 ngay ({@code docs/C2B_SPEC.md} muc 5.1, {@code docs/X1_EXTEND.md}
 * muc 10.3). Key cu {@code SIM_HARD_SL_PCT} KHONG con doc duoc o HEAD; day la ban VIET LAI.
 *
 * <p>Bat bien quan trong: nguong do tren {@code firstEntryPrice} (gia vao leg DAU cua cum) chu
 * KHONG phai {@code priceEntry} (gia binh quan, DICH moi lan DCA). Nho vay muc cat khong tu noi
 * long ra khi cum bi nhoi them.
 *
 * <p>Mac dinh {@code SIM_PRE_ARM_SL = 0} => {@link #enabled()} false => moi diem chen la
 * {@code if(false)} => byte-identical voi truoc X2. Xem {@code docs/PREREG_X2.md} muc 2.2.
 */
public final class PreArmSlUtils {

    private PreArmSlUtils() {
    }

    /** Co bat khong. Gia tri AM moi co nghia (vd -0.20 = cat khi lo 20%); 0 hoac duong = TAT. */
    public static boolean enabled() {
        return Configs.PRE_ARM_SL < 0f;
    }

    /** Muc gia kich hoat, do tren gia vao leg DAU (BAT BIEN qua DCA). */
    public static float stopLevel(float firstEntryPrice) {
        return firstEntryPrice * (1f + Configs.PRE_ARM_SL);
    }

    /**
     * Nen hien tai co cham nguong khong. Dung {@code bar.minPrice} — doi xung voi cong arm da dung
     * {@code bar.maxPrice}, tuc KHONG phai mot quy uoc intrabar moi.
     */
    public static boolean hit(Float firstEntryPrice, float barLow) {
        if (!enabled() || firstEntryPrice == null || firstEntryPrice <= 0f) {
            return false;
        }
        return barLow <= stopLevel(firstEntryPrice);
    }

    /**
     * Gia dong. KHONG BAO GIO tot hon muc stop (chan look-ahead co loi khi nen thung xuong roi bat
     * len trong cung 1 phut), va XAU HON muc stop neu nen dong duoi do (chiu gap) — dung tinh than
     * haircut {@code min(open, close)} ma {@code LOSER_TIME_STOP} dang dung.
     */
    public static float exitPrice(float firstEntryPrice, float barOpen, float barClose) {
        return Math.min(stopLevel(firstEntryPrice), Math.min(barOpen, barClose));
    }
}
