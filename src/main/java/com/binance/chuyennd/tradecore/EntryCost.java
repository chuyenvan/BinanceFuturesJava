package com.binance.chuyennd.tradecore;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.function.Function;

/**
 * [ENTRY-COST-BUCKET 2026-10-12] docs/result/EXEC_RESULT.md §6(a) — chi phi VAO theo bucket bar_ret nen quyet dinh.
 *
 * <p>Key: {@code SIM_ENTRY_COST_MODE} in {off (mac dinh), bucket}; {@code SIM_ENTRY_COST_NC/C1/C2/C4} (FRACTION).
 * Bucket theo bar_ret = (close-open)/open float32 (CUNG bieu thuc + bien -0.01f voi
 * {@code SimulatorMarketLevelTicker1MStopLoss.isCrashBar}): NC: bar_ret &gt; -1%; C1: -2% &lt; bar_ret &lt;= -1%;
 * C2: -4% &lt; bar_ret &lt;= -2%; C4: bar_ret &lt;= -4%.
 *
 * <p>BUCKET: gia vao MOI chan = close nen quyet dinh x (1 + cost_bucket) — THAY phan SLIPPAGE_RATE phia VAO
 * (calTp chi tru 1 chan slip = phia RA) va THAY CRASH_ENTRY_PENALTY (cam bat dong thoi). OFF: khong nhanh nao chay
 * => byte-identical.
 *
 * <p>Field CO CHU DICH khong nam trong {@link Configs}: DumpConfig reflect moi public static cua Configs vao
 * CONFIG_HASH => them field o do se doi hash ca khi OFF. Khi BUCKET, {@link #dumpRows()} dua key vao hash.
 */
public final class EntryCost {
    private static final Logger LOG = LoggerFactory.getLogger(EntryCost.class);

    public static final int NC = 0, C1 = 1, C2 = 2, C4 = 3;
    public static final String[] NAMES = {"NC", "C1", "C2", "C4"};
    public static final String K_MODE = "SIM_ENTRY_COST_MODE";
    public static final String[] K_COST = {"SIM_ENTRY_COST_NC", "SIM_ENTRY_COST_C1", "SIM_ENTRY_COST_C2",
            "SIM_ENTRY_COST_C4"};

    private static boolean bucket = false;
    private static final float[] COST = new float[4];

    private EntryCost() {
    }

    public static boolean isBucket() {
        return bucket;
    }

    public static float cost(int b) {
        return COST[b];
    }

    /** Bucket theo bar_ret nen quyet dinh. NC = phu dinh DUNG bieu thuc isCrashBar (ca NaN => NC). */
    public static int bucketOf(float priceClose, float priceOpen) {
        float barRet = (priceClose - priceOpen) / priceOpen;
        if (!(barRet <= -0.01f)) return NC;
        if (barRet > -0.02f) return C1;
        if (barRet > -0.04f) return C2;
        return C4;
    }

    /** Gia vao = gia tham chieu (close nen M) x (1 + cost_bucket) — cung dang phep tinh voi crash penalty. */
    public static float applyEntry(float ref, int b) {
        return ref * (1f + COST[b]);
    }

    /** Fail-fast cho duong CHUA ho tro bucket (van tru SLIPPAGE_RATE x2, khong biet bucket). */
    public static void requireOff(String who) {
        float forceConfigsInit = Configs.CRASH_ENTRY_PENALTY; // dam bao Configs da nap (=> configure da chay)
        if (bucket) throw new IllegalStateException("[ENTRY-COST] " + K_MODE + "=bucket KHONG ho tro trong "
                + who + " (tinh slip x2, khong biet bucket) — dung lai (penalty=" + forceConfigsInit + ")");
    }

    /** Tro ve OFF (chi cho unit test — tranh ro trang thai sang test khac). */
    public static void reset() {
        bucket = false;
        Arrays.fill(COST, 0f);
    }

    /** Dong dua vao CONFIG_HASH cua DumpConfig — RONG khi OFF (hash khong doi). */
    public static List<String> dumpRows() {
        List<String> rows = new ArrayList<>();
        if (!bucket) return rows;
        rows.add("ENTRY_COST_MODE=bucket|EntryCost|String");
        for (int i = 0; i < 4; i++) rows.add("ENTRY_COST_" + NAMES[i] + "=" + COST[i] + "|EntryCost|float");
        return rows;
    }

    /**
     * Doc + kiem cau hinh (goi tu Configs static init, NGOAI try/catch nuot loi => sai = fail-fast).
     * Fail-fast khi: MODE la gia tri la; BUCKET thieu/khong parse duoc bat ky cost nao; cost khong finite hoac
     * |cost| &gt;= 0.1 (FRACTION, khong phai %); BUCKET dong thoi CRASH_ENTRY_PENALTY &gt; 0; OFF ma van khai cost
     * (cau hinh mo ho — tuong la bat ma that ra tat).
     */
    public static void configure(Function<String, String> get, float crashEntryPenalty) {
        String m = get.apply(K_MODE);
        String mode = m == null ? "off" : m.trim().toLowerCase(Locale.ROOT);
        if (mode.isEmpty()) mode = "off";
        final boolean b;
        if ("off".equals(mode)) b = false;
        else if ("bucket".equals(mode)) b = true;
        else throw new IllegalStateException("[ENTRY-COST] " + K_MODE + "=" + m + " khong hop le (chi off|bucket)");
        float[] c = new float[4];
        for (int i = 0; i < 4; i++) {
            String v = get.apply(K_COST[i]);
            boolean declared = v != null && !v.trim().isEmpty();
            if (!b) {
                if (declared) throw new IllegalStateException("[ENTRY-COST] khai " + K_COST[i] + "=" + v
                        + " nhung " + K_MODE + "=off => cau hinh mo ho, dung lai");
                continue;
            }
            if (!declared) throw new IllegalStateException("[ENTRY-COST] " + K_MODE + "=bucket nhung thieu " + K_COST[i]);
            float f;
            try {
                f = Float.parseFloat(v.trim());
            } catch (NumberFormatException e) {
                throw new IllegalStateException("[ENTRY-COST] " + K_COST[i] + "=" + v + " khong phai so", e);
            }
            if (!Float.isFinite(f) || Math.abs(f) >= 0.1f) throw new IllegalStateException("[ENTRY-COST] "
                    + K_COST[i] + "=" + v + " ngoai (-0.1,0.1) — gia tri la FRACTION (vd 0.0007), khong phai %");
            c[i] = f;
        }
        if (b && crashEntryPenalty > 0f) throw new IllegalStateException("[ENTRY-COST] " + K_MODE
                + "=bucket xung dot SIM_CRASH_ENTRY_PENALTY=" + crashEntryPenalty + " (>0) — bucket THAY penalty");
        bucket = b;
        System.arraycopy(c, 0, COST, 0, 4);
        if (b) LOG.info("[ENTRY-COST] MODE=bucket NC={} C1={} C2={} C4={} (thay slip phia VAO + crash penalty)",
                COST[NC], COST[C1], COST[C2], COST[C4]);
    }
}
