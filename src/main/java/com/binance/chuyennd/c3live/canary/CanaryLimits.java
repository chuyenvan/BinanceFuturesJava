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
    /** So symbol canary (chinh + phu cho K7b). */
    public static final int SYMBOLS = 2;
    /** Leverage duy nhat duoc dat. */
    public static final int LEVERAGE = 1;

    private CanaryLimits() {
    }
}
