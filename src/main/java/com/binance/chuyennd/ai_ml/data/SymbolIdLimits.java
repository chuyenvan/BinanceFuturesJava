package com.binance.chuyennd.ai_ml.data;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * [LIVEFIX2 2026-10-11] Tran CHUNG cho moi mang danh chi so theo symbolId (truoc day hardcode 1000 rai rac:
 * HistoryManager.MAX_COINS, klineArray[1000] x3, sim symbol2Order*, PumpDumpFilter, TickWeakBlock...).
 * Id hop le: 0..CAPACITY-1. Max id 242 ngay 2026-10-11 = 933 (sau repair 949), tang ~1 id/ngay ⇒ 4096 du ~8 nam.
 * <ul>
 *   <li>Live (HistoryManager): id &gt;= CAPACITY ⇒ {@link #recordOverCap} — log ERROR (lan dau moi symbol + moi
 *       1000 lan) + dem tong {@link #overCapCount()}; KHONG bo im lang.</li>
 *   <li>Sim/loader: id &gt;= CAPACITY ⇒ {@link #requireInRange} nem IllegalStateException ro rang (thay AIOOBE).</li>
 * </ul>
 * Voi id &lt; 1000 moi mang chi DAI them (o thua = null/0), thu tu duyet tang dan theo id khong doi.
 */
public final class SymbolIdLimits {

    private static final Logger LOG = LoggerFactory.getLogger(SymbolIdLimits.class);

    /** Kich thuoc mang theo id. Id hop le 0..CAPACITY-1. (&lt; Short.MAX_VALUE vi id la short.) */
    public static final int CAPACITY = 4096;
    /** Tran cu (truoc 2026-10-11) — chi de tai lieu/test. */
    public static final int LEGACY_CAPACITY = 1000;

    private static final AtomicLong OVER_CAP = new AtomicLong();
    private static final Set<String> LOGGED = ConcurrentHashMap.newKeySet();

    private SymbolIdLimits() {}

    public static boolean inRange(int id) {
        return id >= 0 && id < CAPACITY;
    }

    /**
     * Live: ghi nhan 1 lan bo qua symbol vi id vuot tran. Tra ve tong so lan (tich luy tu luc start JVM).
     */
    public static long recordOverCap(String where, String symbol, int id) {
        long n = OVER_CAP.incrementAndGet();
        if (LOGGED.add(symbol) || n % 1000 == 0) {
            LOG.error("⛔ [ID-CAP] {}: {} -> id {} >= CAPACITY {} — BO QUA (khong co lich su/feature). tong={} "
                    + "Nang SymbolIdLimits.CAPACITY.", where, symbol, id, CAPACITY, n);
        }
        return n;
    }

    public static long overCapCount() {
        return OVER_CAP.get();
    }

    /** Sim/loader: id ngoai [0, CAPACITY) ⇒ IllegalStateException (fail-fast, thong diep ro). */
    public static int requireInRange(String where, String symbol, int id) {
        if (id < 0 || id >= CAPACITY) {
            throw new IllegalStateException("[ID-CAP] " + where + ": " + symbol + " -> id " + id
                    + " ngoai [0," + CAPACITY + ") — nang SymbolIdLimits.CAPACITY");
        }
        return id;
    }

    /** Chi cho test. */
    public static void resetForTest() {
        OVER_CAP.set(0);
        LOGGED.clear();
    }
}
