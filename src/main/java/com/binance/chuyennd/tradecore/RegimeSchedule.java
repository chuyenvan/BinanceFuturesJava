package com.binance.chuyennd.tradecore;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.Map;
import java.util.TreeMap;

/**
 * Lich regime theo UTC-day cho gate regime-adaptive (docs/PREREG_REGIME_GATE.md).
 *
 * <p>Nap file CSV daily (cot: utcDay,dateUTC,ret30,regime,scale) -> TreeMap&lt;utcDay, scale&gt;.
 * Scale KHONG doc tu cot so (chi de audit) ma map tu cot regime -> HANG SO trong {@link EntryGate}
 * ({@code UP -> REGIME_SCALE_UP=1.00f}, con lai -> {@code REGIME_SCALE_NOTUP=1.70f}) => bit-exact
 * bang T100/T170, KHONG le thuoc parse float text.
 *
 * <p>{@link #scaleForTime(long)}: utcDay = ms/86400000; thieu ngay -> floorEntry (causal, regime
 * ngay gan nhat da biet); rong hoan toan -> NOT-UP (1.70). {@code force(UP|NOTUP)} = ep hang so
 * cho cong gate 2-cuc.
 */
public final class RegimeSchedule {
    private static final long DAY_MS = 86400000L;
    private static TreeMap<Long, Float> dayScale = new TreeMap<>();
    private static boolean loaded = false;
    private static Float forceScale = null;

    private RegimeSchedule() {
    }

    /** Ep hang so cho cong 2-cuc: "UP"->1.00, "NOTUP"->1.70. */
    public static void force(String mode) {
        if (mode == null) return;
        String m = mode.trim().toUpperCase();
        if (m.equals("UP")) {
            forceScale = EntryGate.REGIME_SCALE_UP;
        } else if (m.equals("NOTUP") || m.equals("NOT-UP") || m.equals("NOT_UP")) {
            forceScale = EntryGate.REGIME_SCALE_NOTUP;
        } else {
            throw new IllegalArgumentException("SIM_REGIME_FORCE khong hop le: " + mode + " (chi UP|NOTUP)");
        }
    }

    /** Nap file regime daily. Bo dong header / rong / comment. Cot 0 = utcDay, cot 3 = regime. */
    public static void load(String path) {
        if (path == null || path.trim().isEmpty()) {
            throw new IllegalStateException("GATE_REGIME_ADAPTIVE bat nhung SIM_REGIME_FILE rong");
        }
        TreeMap<Long, Float> m = new TreeMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(path.trim()))) {
            String ln;
            while ((ln = br.readLine()) != null) {
                ln = ln.trim();
                if (ln.isEmpty() || ln.startsWith("#") || ln.startsWith("utcDay")) continue;
                String[] p = ln.split(",");
                if (p.length < 4) continue;
                long day = Long.parseLong(p[0].trim());
                String reg = p[3].trim().toUpperCase();
                float sc = reg.equals("UP") ? EntryGate.REGIME_SCALE_UP : EntryGate.REGIME_SCALE_NOTUP;
                m.put(day, sc);
            }
        } catch (Exception e) {
            throw new RuntimeException("Loi nap SIM_REGIME_FILE=" + path, e);
        }
        if (m.isEmpty()) {
            throw new IllegalStateException("SIM_REGIME_FILE khong co dong hop le: " + path);
        }
        dayScale = m;
        loaded = true;
    }

    /** Scale gate cho thoi diem ms (epoch). */
    public static float scaleForTime(long ms) {
        if (forceScale != null) return forceScale;
        long day = Math.floorDiv(ms, DAY_MS);
        Float s = dayScale.get(day);
        if (s != null) return s;
        Map.Entry<Long, Float> fe = dayScale.floorEntry(day);
        if (fe != null) return fe.getValue();
        return EntryGate.REGIME_SCALE_NOTUP;
    }

    public static boolean isReady() {
        return loaded || forceScale != null;
    }
}
