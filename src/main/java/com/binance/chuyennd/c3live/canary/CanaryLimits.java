package com.binance.chuyennd.c3live.canary;

import java.math.BigDecimal;

/**
 * [V12 3] Gioi han CUNG cua cong cu canary (prereg GCANARY §3 + Quyet dinh MASTER 10-25). Hang so — KHONG doc tu config /
 * bien moi truong / file trang thai. Doi gia tri = doi code = A1 audit lai.
 */
public final class CanaryLimits {

    /** Notional lenh mo chuan (USDT). */
    public static final BigDecimal ORDER_NOTIONAL_USDT = new BigDecimal("20");
    /** Tran notional 1 lenh mo (USDT) — kiem lai trong CanaryGateway voi gia moi doc. */
    public static final BigDecimal MAX_ORDER_NOTIONAL_USDT = new BigDecimal("25");
    /** Tran tong notional dang mo (moi symbol canary) SAU khi lenh khop (USDT). */
    public static final BigDecimal MAX_OPEN_NOTIONAL_USDT = new BigDecimal("40");
    /** Tran lo cua phien (USDT): lo da chot + phi, hoac tmb0 - tmb hien tai; cham => flatten roi dung phien. */
    public static final double LOSS_CAP_USDT = 2.0d;
    /** [3g MIN-3] tran lo cong don moi phien (prereg MIN-C2): tran phien = min(2, 4 - lo cac phien truoc). */
    public static final double CUM_LOSS_CAP_USDT = 4.0d;
    /** [3g MIN-3] tran phien <= muc nay => TU CHOI mo lenh. */
    public static final double MIN_SESSION_CAP_USDT = 0.10d;
    /** So symbol canary (chinh + phu cho K7b). */
    public static final int SYMBOLS = 2;
    /** Leverage duy nhat duoc dat. */
    public static final int LEVERAGE = 1;
    /**
     * [V12 3c MAJ-C1, prereg §ADD-2] Khoang cach TOI DA cua stop SELL so gia vao (entry): moi vi the canary vua mo co NGAY stop
     * bao ve closePosition MARK_PRICE o -4,5 % (40 USDT x 4,5 % = 1,8 USDT) => tran lo giu duoc ca khi khong JVM nao canh.
     * CanaryGateway tu choi moi stop SELL thap hon entry x (1 - 4,5 % - dung sai lam tron).
     */
    public static final double MAX_STOP_DIST = 0.045d;
    /** Dung sai lam tron gia stop (FLOOR theo tick; luat §3: tick/gia <= 0,01 %) — 2 bp. */
    public static final double STOP_ROUND_TOL = 0.0002d;
    /** Khoang cach stop bao ve TOI THIEU; ngan sach lo con lai khong cho du khoang nay => KHONG mo (hoac dong ngay). */
    public static final double MIN_STOP_DIST = 0.01d;
    /** Du phong phi dong + truot khi stop kich (USDT), tru vao ngan sach khi tinh stop bao ve. */
    public static final double STOP_FEE_RESERVE_USDT = 0.10d;

    private CanaryLimits() {
    }
}
