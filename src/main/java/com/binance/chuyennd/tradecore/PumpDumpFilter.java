package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.MarketLevelChange;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedInputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;

/**
 * [D3D4-FILTER 2026-09-17] docs/PREREG_D3D4_FILTER_SIM.md — filter "pump xong chuan bi dump" ap cho
 * LENH MOI (selector Best-N + BIG_DOWN), KHONG ap DCA.
 *
 * <p>Hai detector POST-HOC (da nhin DEV truoc): D3 {@code oi_px_div = oiDelta24h - ret_24h}, D4
 * {@code stall = ret_6h - ret_15m}. Luat: bo qua lenh moi neu feature &gt; p90 cua no (feature cao =
 * de sup). p90 co dinh tinh tren DEV (920 leg entry moi). Khong toi uu nguon.
 *
 * <p>Feature tinh IN-SIM tai moc vao lenh (bar {@code startTime = T}, entry price = close(T)):
 * <pre>
 *   now      = close(T - 1m)         // trung ce = c[N-1] cua extractor screen
 *   ret_15m  = now / close(T - 15m)  - 1
 *   ret_6h   = now / close(T - 6h)   - 1
 *   ret_24h  = now / close(T - 24h)  - 1
 *   stall    = ret_6h - ret_15m
 *   oi_px_div = oiDelta24h(T) - ret_24h   (oiDelta24h = snapshot OI 5m gan nhat ts &lt;= T)
 * </pre>
 * close(.) doc tu {@link HistoryManager#getPriceAt(short, long)} (ring 1m). Thieu thanh phan
 * (history &lt; 24h / gap &gt; 30m / OI NaN) =&gt; feature NaN =&gt; KHONG filter (giu lenh).
 *
 * <p>Mode doc 1 lan tu {@link Configs#SIM_FILTER_D3D4} (off|d3|d4|both, default off). OFF =&gt;
 * {@link #shouldSkip} tra false ngay =&gt; byte-identical parity.
 *
 * <p>Bang tra cuu OI (chi cho D3): file nhi phan BE {@link #OI_TABLE_PATH} sinh offline tu
 * {@code oi_percoin_full.bin} (5m), cot {@code oiDelta24h} (field 0). Layout:
 * <pre>
 *   int32 numSlots (1001)
 *   for sid in 0..1000: int32 count, roi count x (int32 tsIdx5m BE, float32 oid BE)
 * </pre>
 * tsIdx5m = ts / 300000, sort ascending per sid. Tra cuu = binary search floorEntry(sid, entryMs/300000).
 */
public final class PumpDumpFilter {

    private static final Logger LOG = LoggerFactory.getLogger(PumpDumpFilter.class);

    /** Duong dan bang tra cuu OI (artifact offline, KHONG trong git). */
    public static final String OI_TABLE_PATH = "/home/ubuntu/java/filter_oi_lookup.bin";

    /** p90 co dinh tinh tren DEV (920 leg entry moi, 2022-2025) — xem pre-reg muc 2. */
    public static final float P90_D3 = 0.319439835f;
    public static final float P90_D4 = 0.112770706f;

    private static final int MIN_MS = 60_000;
    private static final int HOUR_MS = 3_600_000;
    private static final int FIVE_MIN_MS = 5 * MIN_MS;

    private static final int MAX_SYMBOL = 1000;

    private static String mode = "off";
    private static boolean loaded = false;
    private static int[][] oiTsIdx = null;   // [sid][i] ts/300000, ascending
    private static float[][] oiOid = null;   // [sid][i] oiDelta24h

    private static long skipped = 0L;

    private PumpDumpFilter() {
    }

    /** Doc mode tu Configs (1 lan). Goi tu Configs static block de ASKED duoc ghi nhan cho audit. */
    public static void configure(String m) {
        String v = (m == null || m.trim().isEmpty()) ? "off" : m.trim().toLowerCase();
        switch (v) {
            case "off":
            case "d3":
            case "d4":
            case "both":
                mode = v;
                break;
            default:
                throw new IllegalArgumentException(
                        "SIM_FILTER_D3D4 khong hop le: " + m + " (chi off|d3|d4|both)");
        }
    }

    public static String mode() {
        return mode;
    }

    public static boolean active() {
        return !"off".equals(mode);
    }

    public static long skippedCount() {
        return skipped;
    }

    private static boolean useD3() {
        return "d3".equals(mode) || "both".equals(mode);
    }

    private static boolean useD4() {
        return "d4".equals(mode) || "both".equals(mode);
    }

    /**
     * Bo qua lenh moi nay khong? Chi ap cho PREDICT_SYMBOL_TRADE (selector) va BIG_DOWN, KHONG DCA.
     *
     * @param dcaSignal true = leg DCA theo tin hieu (bo qua, khong filter).
     */
    public static boolean shouldSkip(short symId, long entryMs, MarketLevelChange levelChange, boolean dcaSignal) {
        if (!active()) return false;
        if (dcaSignal) return false;
        if (levelChange != MarketLevelChange.PREDICT_SYMBOL_TRADE
                && levelChange != MarketLevelChange.BIG_DOWN) {
            return false;
        }

        HistoryManager hm = HistoryManager.getInstance();
        Float now = hm.getPriceAt(symId, entryMs - MIN_MS);
        if (now == null || now <= 0f) return false;   // khong tinh duoc "now" -> giu lenh

        boolean skip = false;

        if (useD4()) {
            Float c15 = hm.getPriceAt(symId, entryMs - 15L * MIN_MS);
            Float c6h = hm.getPriceAt(symId, entryMs - 6L * HOUR_MS);
            if (c15 != null && c6h != null && c15 > 0f && c6h > 0f) {
                double ret15 = now / (double) c15 - 1.0;
                double ret6h = now / (double) c6h - 1.0;
                double stall = ret6h - ret15;
                if (stall > P90_D4) skip = true;
            }
        }

        if (useD3() && !skip) {
            Float c24 = hm.getPriceAt(symId, entryMs - 24L * HOUR_MS);
            Float oid = oiDelta24h(symId, entryMs);
            if (c24 != null && oid != null && c24 > 0f && !Float.isNaN(oid)) {
                double ret24 = now / (double) c24 - 1.0;
                double oiPxDiv = oid - ret24;
                if (oiPxDiv > P90_D3) skip = true;
            }
        }

        if (skip) skipped++;
        return skip;
    }

    /** OI 5m snapshot gan nhat ts &lt;= entryMs; null neu khong co bang / khong co record. */
    private static Float oiDelta24h(short symId, long entryMs) {
        if (!loaded) loadOiTable();
        if (oiTsIdx == null || symId < 0 || symId >= oiTsIdx.length) return null;
        int[] idx = oiTsIdx[symId];
        float[] oid = oiOid[symId];
        if (idx == null || idx.length == 0) return null;
        long q = Math.floorDiv(entryMs, (long) FIVE_MIN_MS);
        if (q > Integer.MAX_VALUE) q = Integer.MAX_VALUE;
        int i = floorEntry(idx, (int) q);
        if (i < 0) return null;
        return oid[i];
    }

    private static int floorEntry(int[] arr, int key) {
        int lo = 0, hi = arr.length - 1, ans = -1;
        while (lo <= hi) {
            int mid = (lo + hi) >>> 1;
            if (arr[mid] <= key) {
                ans = mid;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        return ans;
    }

    private static synchronized void loadOiTable() {
        if (loaded) return;
        File f = new File(OI_TABLE_PATH);
        if (!f.exists()) {
            LOG.warn("[D3D4-FILTER] bang tra cuu OI khong ton tai: {} — D3 se KHONG filter", OI_TABLE_PATH);
            loaded = true;
            return;
        }
        try (DataInputStream dis = new DataInputStream(new BufferedInputStream(new FileInputStream(f), 1 << 20))) {
            int slots = dis.readInt();
            int[][] tsArr = new int[Math.max(slots, MAX_SYMBOL + 1)][];
            float[][] oidArr = new float[tsArr.length][];
            for (int sid = 0; sid < slots; sid++) {
                int count = dis.readInt();
                if (count <= 0) continue;
                int[] t = new int[count];
                float[] o = new float[count];
                for (int i = 0; i < count; i++) {
                    t[i] = dis.readInt();
                    o[i] = dis.readFloat();
                }
                tsArr[sid] = t;
                oidArr[sid] = o;
            }
            oiTsIdx = tsArr;
            oiOid = oidArr;
            LOG.info("[D3D4-FILTER] nap bang tra cuu OI: {} slots", slots);
        } catch (IOException e) {
            LOG.error("[D3D4-FILTER] loi nap bang tra cuu OI", e);
        }
        loaded = true;
    }
}
