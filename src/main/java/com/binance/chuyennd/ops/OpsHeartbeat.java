package com.binance.chuyennd.ops;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileOutputStream;

/**
 * [V11D OPS 2026-10-21] Heartbeat cho watchdog {@code ops/h242_watchdog.sh}: moi tick quyet dinh (dau
 * {@code DetectEntrySignal2TradeNormal.checkMarketLevelChange2Trade}, ~1 lan/phut tren 242) cham mtime cua file
 * {@code LIVE_HEARTBEAT_FILE} (mac dinh {@code run/heartbeat}, tuong doi cwd app). File RONG — khong ghi noi dung.
 * Co {@code LIVE_HEARTBEAT} tat (mac dinh) => khong I/O nao.
 */
public final class OpsHeartbeat {

    private static final Logger LOG = LoggerFactory.getLogger(OpsHeartbeat.class);
    private static final long WARN_EVERY_MS = 3_600_000L;

    private static final boolean ON = OpsConfig.parseOn(Cfg.get(OpsConfig.KEY_HEARTBEAT));
    private static final File FILE = new File(Cfg.getOr(OpsConfig.KEY_HEARTBEAT_FILE, OpsConfig.DEFAULT_HEARTBEAT_FILE));
    private static volatile boolean firstOkLogged = false;
    private static volatile long lastWarnMs = 0L;

    private OpsHeartbeat() {
    }

    public static boolean on() {
        return ON;
    }

    public static File file() {
        return FILE;
    }

    /**
     * Tao file rong neu chua co, roi dat mtime = {@code nowMs}. Tra false neu loi (khong nem). Thuan I/O tren 1 file
     * — de unit test voi file tam.
     */
    static boolean touch(File f, long nowMs) {
        try {
            if (!f.exists()) {
                File p = f.getAbsoluteFile().getParentFile();
                if (p != null && !p.exists() && !p.mkdirs()) return false;
                new FileOutputStream(f, true).close();
            }
            return f.setLastModified(nowMs);
        } catch (Exception e) {
            return false;
        }
    }

    /** Goi moi tick. Tat => return ngay. Loi => WARN toi da 1 lan/gio, khong bao gio nem. */
    static void beat(long nowMs) {
        if (!ON) return;
        boolean ok = touch(FILE, nowMs);
        if (ok && !firstOkLogged) {
            firstOkLogged = true;
            LOG.info("[HEARTBEAT] BAT file={} (mtime cham moi tick; watchdog xet tuoi file)", FILE.getAbsolutePath());
        } else if (!ok && nowMs - lastWarnMs >= WARN_EVERY_MS) {
            lastWarnMs = nowMs;
            LOG.warn("[HEARTBEAT] khong cham duoc {} (watchdog se thay heartbeat cu)", FILE.getAbsolutePath());
        }
    }
}
