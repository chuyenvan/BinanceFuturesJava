package com.binance.chuyennd.ops;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.Locale;

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

    // ------------------------------------------------------------------ [V12 SAFE 2026-10-25] kill-switch ACT + C2 co dau
    public static final String KEY_KILLSW_C2_SIGNED = "LIVE_KILLSW_C2_SIGNED";
    public static final String KEY_KILLSW_C2_WARN = "LIVE_KILLSW_C2_WARN";
    public static final String KEY_KILLSW_C2_SLIP = "LIVE_KILLSW_C2_SLIP";
    public static final String KEY_KILLSW_C2_COUNT = "LIVE_KILLSW_C2_COUNT";
    public static final String KEY_KILLSW_C2_WINDOW_H = "LIVE_KILLSW_C2_WINDOW_H";
    public static final String KEY_KILLSW_LATCH_FILE = "LIVE_KILLSW_LATCH_FILE";
    public static final String KEY_KILLSW_RESET_FILE = "LIVE_KILLSW_RESET_FILE";
    public static final String DEFAULT_KILLSW_LATCH_FILE = "run/killsw_latch.json";
    public static final String DEFAULT_KILLSW_RESET_FILE = "run/killsw_reset.req";
    /** Nguong owner 10-25 (Q1c) — tam, chot lai sau exec-probe ~100 leg. */
    /** [V12 MASTER 10-25] c3_live: C1/C5 tu go latch sau N phut lien tuc sach (0 = tat). */
    public static final String KEY_KILLSW_AUTORELEASE_MIN = "LIVE_KILLSW_AUTORELEASE_MIN";
    public static final int DEFAULT_AUTORELEASE_MIN = 30;
    public static final double DEFAULT_C2_WARN = 0.017;
    public static final double DEFAULT_C2_SLIP = 0.025;
    public static final int DEFAULT_C2_COUNT = 3;
    public static final int DEFAULT_C2_WINDOW_H = 24;

    static boolean isC3Live(String profile) {
        return profile != null && "c3_live".equals(profile.trim().toLowerCase(Locale.ROOT));
    }

    public static String c2SignedRaw() {
        String r = Cfg.get(KEY_KILLSW_C2_SIGNED);
        return r == null ? "0" : r.trim();
    }

    public static File latchFile() {
        return new File(Cfg.getOr(KEY_KILLSW_LATCH_FILE, DEFAULT_KILLSW_LATCH_FILE).trim());
    }

    public static File resetFile() {
        return new File(Cfg.getOr(KEY_KILLSW_RESET_FILE, DEFAULT_KILLSW_RESET_FILE).trim());
    }

    /** So thuc trong [lo, hi]; vang => def; sai => def + WARN. */
    static double parseDouble(String key, String raw, double def, double lo, double hi) {
        if (raw == null || raw.trim().isEmpty()) return def;
        try {
            double v = Double.parseDouble(raw.trim());
            if (Double.isFinite(v) && v >= lo && v <= hi) return v;
        } catch (NumberFormatException ignore) {
            // roi xuong WARN
        }
        LOG.warn("[KILLSW] {}='{}' khong hop le (can [{}, {}]) => dung mac dinh {}", key, raw, lo, hi, def);
        return def;
    }

    static int parseInt(String key, String raw, int def, int lo, int hi) {
        if (raw == null || raw.trim().isEmpty()) return def;
        try {
            int v = Integer.parseInt(raw.trim());
            if (v >= lo && v <= hi) return v;
        } catch (NumberFormatException ignore) {
            // roi xuong WARN
        }
        LOG.warn("[KILLSW] {}='{}' khong hop le (can so nguyen [{}, {}]) => dung mac dinh {}", key, raw, lo, hi, def);
        return def;
    }

    /**
     * Tham so kill-switch v1.2. {@code act=false} (c3_shadow mode log): KHONG co file latch/reset (khong I/O moi);
     * C2 co dau chi khi {@code LIVE_KILLSW_C2_SIGNED=1} (mac dinh 0 = cong thuc v1.1).
     */
    public static KillSwitchEngine.Params killSwitchParams(boolean act) {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.c2Signed = parseOn(Cfg.get(KEY_KILLSW_C2_SIGNED));
        p.c2Warn = parseDouble(KEY_KILLSW_C2_WARN, Cfg.get(KEY_KILLSW_C2_WARN), DEFAULT_C2_WARN, 0d, 0.5d);
        p.c2Slip = parseDouble(KEY_KILLSW_C2_SLIP, Cfg.get(KEY_KILLSW_C2_SLIP), DEFAULT_C2_SLIP, 0d, 0.5d);
        p.c2Count = parseInt(KEY_KILLSW_C2_COUNT, Cfg.get(KEY_KILLSW_C2_COUNT), DEFAULT_C2_COUNT, 1, 1000);
        p.c2WindowMs = parseInt(KEY_KILLSW_C2_WINDOW_H, Cfg.get(KEY_KILLSW_C2_WINDOW_H), DEFAULT_C2_WINDOW_H, 1, 24 * 30)
                * HOUR_MS;
        if (act) {
            p.latchFile = latchFile();
            p.resetFile = resetFile();
            p.autoReleaseMs = parseInt(KEY_KILLSW_AUTORELEASE_MIN, Cfg.get(KEY_KILLSW_AUTORELEASE_MIN),
                    DEFAULT_AUTORELEASE_MIN, 0, 24 * 60) * 60_000L;
            p.autoReleaseCodes.add("C3");   // [V12 2b MASTER 10-25] C3 tu go: 30' sach + >= 3 call API OK lien tiep
            p.c4Capacity = true;            // [V12 2b MASTER 10-25] C4 = cong suat: chi chan mo cum moi, tu go co tre
        }
        return p;
    }

    /** "1"/"true" (khong phan biet hoa thuong, bo khoang trang) => true; con lai false. */
    static boolean parseOn(String raw) {
        if (raw == null) return false;
        String s = raw.trim();
        return "1".equals(s) || "true".equalsIgnoreCase(s);
    }
}
