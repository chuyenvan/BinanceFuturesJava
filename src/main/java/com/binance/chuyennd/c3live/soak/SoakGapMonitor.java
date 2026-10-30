package com.binance.chuyennd.c3live.soak;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * [V12 R4h] Theo doi khe ho ket noi user-data stream (lay mau ~1 s): moi lan CONNECTED -> mat -> CONNECTED ghi 1 {@link Gap}
 * (luc mat, luc co lai, da ket noi bao lau truoc khi mat). "Cat 24 h" = mat sau &gt;= {@link #CUT_24H_MIN_MS} ket noi lien tuc.
 */
public final class SoakGapMonitor {

    public static final long CUT_24H_MIN_MS = 23L * 3_600_000L + 30L * 60_000L;

    public static final class Gap {
        public final long downAtMs;
        public final long upAtMs;
        public final long connectedForMs;

        Gap(long downAtMs, long upAtMs, long connectedForMs) {
            this.downAtMs = downAtMs;
            this.upAtMs = upAtMs;
            this.connectedForMs = connectedForMs;
        }

        public long gapMs() {
            return upAtMs - downAtMs;
        }

        public boolean is24hCut() {
            return connectedForMs >= CUT_24H_MIN_MS;
        }
    }

    private Boolean last;
    private long connectedSince = -1L;
    private long downSince = -1L;
    private long lastConnectedFor;
    private final List<Gap> gaps = new ArrayList<>();
    private long maxConnectedMs;

    /** @return Gap vua dong (ket noi lai) hoac null. */
    public synchronized Gap sample(long now, boolean connected) {
        Gap done = null;
        if (last == null) {
            last = connected;
            if (connected) connectedSince = now;
            else downSince = now;
            return null;
        }
        if (connected && !last) {
            if (downSince >= 0 && lastConnectedFor > 0) {   // mat SAU khi da tung ket noi (khong tinh luc khoi dong)
                done = new Gap(downSince, now, lastConnectedFor);
                gaps.add(done);
            }
            connectedSince = now;
            downSince = -1L;
        } else if (!connected && last) {
            lastConnectedFor = now - connectedSince;
            maxConnectedMs = Math.max(maxConnectedMs, lastConnectedFor);
            downSince = now;
            connectedSince = -1L;
        } else if (connected) {
            maxConnectedMs = Math.max(maxConnectedMs, now - connectedSince);
        }
        last = connected;
        return done;
    }

    public synchronized List<Gap> gaps() {
        return Collections.unmodifiableList(new ArrayList<>(gaps));
    }

    public synchronized long maxConnectedMs() {
        return maxConnectedMs;
    }

    public synchronized boolean cut24hSeen() {
        for (Gap g : gaps) if (g.is24hCut()) return true;
        return false;
    }

    public synchronized long maxGapMs() {
        long m = 0;
        for (Gap g : gaps) m = Math.max(m, g.gapMs());
        return m;
    }

    /** Dang mat ket noi tu bao gio (-1 = dang ket noi / chua lay mau). */
    public synchronized long downSinceMs() {
        return downSince;
    }
}
