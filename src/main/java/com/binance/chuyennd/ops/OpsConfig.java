package com.binance.chuyennd.ops;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * [V11D OPS 2026-10-21] Co VAN HANH cua ban v11d (ADDENDUM d PREREG_SHADOW2_PROMOTION). Khong co key nao o day cham
 * logic quyet dinh (feature, sizing, entry/exit, gate, selector, TS_MKT_EXT). Mac dinh = hanh vi v11c y het.
 *
 * <ul>
 *   <li>{@code LIVE_PERIODIC_RESET_HOURS} (mac dinh 12 = nhu cu; 0 = TAT reset dinh ky cua
 *       {@code ThreadAutoRestartProgram}). Duong reset cua {@code Reporter} (market check tre &gt;15') KHONG doi.</li>
 *   <li>{@code LIVE_HEARTBEAT} (mac dinh 0): 1 = cham mtime file {@code LIVE_HEARTBEAT_FILE} (mac dinh
 *       {@code run/heartbeat}) moi tick — xem {@link OpsHeartbeat}.</li>
 *   <li>{@code LIVE_KILLSW_MODE} off|log|act (mac dinh off) — xem {@link KillSwitchEngine}.</li>
 * </ul>
 * Doc qua {@link Cfg} (khong goi System.getenv truc tiep). Luu y: key tien to {@code LIVE_} bi Cfg coi la tham so giao
 * dich khi dat TRADING_PROFILE — 242 KHONG dung TRADING_PROFILE (env.sh), nen doc tu env nhu moi key LIVE_* khac.
 */
public final class OpsConfig {

    private static final Logger LOG = LoggerFactory.getLogger(OpsConfig.class);

    public static final String KEY_RESET_HOURS = "LIVE_PERIODIC_RESET_HOURS";
    public static final String KEY_HEARTBEAT = "LIVE_HEARTBEAT";
    public static final String KEY_HEARTBEAT_FILE = "LIVE_HEARTBEAT_FILE";
    public static final String KEY_KILLSW_MODE = "LIVE_KILLSW_MODE";
    public static final String KEY_KILLSW_STATE_FILE = "LIVE_KILLSW_STATE_FILE";

    /** Chu ky reset v11c (BinanceOrderTradingManager: Thread.sleep(Utils.TIME_HOUR * 12)). */
    public static final int DEFAULT_RESET_HOURS = 12;
    /** Gioi han tren hop ly (tranh go nham 1200). Ngoai [0, MAX] => ve mac dinh + WARN. */
    public static final int MAX_RESET_HOURS = 24 * 30;
    public static final String DEFAULT_HEARTBEAT_FILE = "run/heartbeat";
    public static final String DEFAULT_KILLSW_STATE_FILE = "run/killsw_peak";
    private static final long HOUR_MS = 3_600_000L;

    private static final int RESET_HOURS;

    static {
        String raw = Cfg.get(KEY_RESET_HOURS);
        int h = parseResetHours(raw);
        if (raw != null && !raw.trim().isEmpty() && !isValidResetHours(raw)) {
            LOG.warn("[OPS-RESET] {}='{}' khong hop le (can so nguyen 0..{}) => dung mac dinh {}h",
                    KEY_RESET_HOURS, raw, MAX_RESET_HOURS, DEFAULT_RESET_HOURS);
        }
        RESET_HOURS = h;
    }

    private OpsConfig() {
    }

    /** Gia tri thuan: null/rong/sai/am/qua lon => {@link #DEFAULT_RESET_HOURS}; 0 = tat. */
    static int parseResetHours(String raw) {
        if (!isValidResetHours(raw)) return DEFAULT_RESET_HOURS;
        return Integer.parseInt(raw.trim());
    }

    static boolean isValidResetHours(String raw) {
        if (raw == null || raw.trim().isEmpty()) return false;
        try {
            int v = Integer.parseInt(raw.trim());
            return v >= 0 && v <= MAX_RESET_HOURS;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    /** ms ngu giua 2 lan reset dinh ky; 0 = tat. Mac dinh 12h = 43 200 000 ms (y het v11c). */
    static long resetPeriodMs(int hours) {
        return hours <= 0 ? 0L : hours * HOUR_MS;
    }

    public static int periodicResetHours() {
        return RESET_HOURS;
    }

    /** ms ngu cua {@code BinanceOrderTradingManager.startThreadAutoRestartProgram}; 0 = tat reset dinh ky. */
    public static long periodicResetMs() {
        return resetPeriodMs(RESET_HOURS);
    }

    /** "1"/"true" (khong phan biet hoa thuong, bo khoang trang) => true; con lai false. */
    static boolean parseOn(String raw) {
        if (raw == null) return false;
        String s = raw.trim();
        return "1".equals(s) || "true".equalsIgnoreCase(s);
    }
}
