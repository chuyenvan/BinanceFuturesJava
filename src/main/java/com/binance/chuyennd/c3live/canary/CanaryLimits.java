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

    // ------------------------------------------------------------------ [3i] rate guard JVM canary (IP chung LEGACY)
    /**
     * [3i] Call thuong cua canary chi duoc gui khi header X-MBX-USED-WEIGHT-1M (CA IP, chung LEGACY) + cost &lt;= muc nay (75 % x 2400).
     * Mac dinh; script co the ha / nang qua env CANARY_IP_WEIGHT_CAP (khong can file gate) — NGOAI LE duy nhat doc tu env, kep
     * &lt;= {@link #IP_WEIGHT_ADMIT_MAX}.
     */
    public static final int IP_WEIGHT_ADMIT_DEFAULT = 1800;
    /** [3i] tran CUNG cua nguong IP (80 % x 2400): env lon hon bi kep ve day. */
    public static final int IP_WEIGHT_ADMIT_MAX = 1920;
    /** [3i] weight canary TU GOI trong 60 s (tieu chi 5 §ADD-4 I) + cost &gt; muc nay => cho. */
    public static final int OWN_WEIGHT_1M_CAP = 600;
    /**
     * [3i] Heuristic tranh burst LEGACY: v_t_m TickerIngestor2AerospikeNew chot nen 1 phut quanh giay :30 roi LEGACY goi REST
     * don dap (~1300 weight/phut) => call thuong (khong khan cap, khong stop bao ve) trong giay [27, 40] ngu toi giay 41.
     */
    public static final int BURST_FROM_SEC = 27;
    public static final int BURST_TO_SEC = 40;
    public static final int BURST_RESUME_SEC = 41;
    /** [3i] call DOC bi guard tu choi: cho sang phut moi (&lt;= 61 s) toi da so lan nay roi moi loi. */
    public static final int READ_GUARD_MAX_WAITS = 2;
    /** [3i] tu luc gui lenh mo (khop) toi luc stop bao ve duoc XAC NHAN tren san: qua han => dong vi the canary (lan khan cap), TRUOT. */
    public static final long PROTECT_MAX_MS = 61_000L;

    /** [3i] nguong IP tu env CANARY_IP_WEIGHT_CAP: rong / sai / &lt;= 0 => mac dinh 1800; &gt; 1920 => 1920. */
    public static int ipWeightCap(String raw) {
        if (raw == null || raw.trim().isEmpty()) return IP_WEIGHT_ADMIT_DEFAULT;
        int v;
        try {
            v = Integer.parseInt(raw.trim());
        } catch (NumberFormatException e) {
            return IP_WEIGHT_ADMIT_DEFAULT;
        }
        if (v <= 0) return IP_WEIGHT_ADMIT_DEFAULT;
        return Math.min(v, IP_WEIGHT_ADMIT_MAX);
    }

    private CanaryLimits() {
    }
}
