package com.binance.chuyennd.tradecore.selector;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.BatchPolicy;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.text.SimpleDateFormat;
import java.util.*;

/**
 * GEOM FEAT PROVIDER — bar OHLC 1h (gio DONG) theo symbol tu nen 1m {@code kline_1m_opt}, roi 9 feature GEOM
 * qua {@link GeomFeatureLive}. CHI duoc tao khi {@code LIVE_S1_GEOM_ENABLED=true} (xem {@link S1RankerLive}).
 *
 * <p>QUY UOC BAR (khop {@code research/analysis/s1_geom_store.py::month}): gio [h, h+1h) -> {@code ts_h = h + 1h};
 * 60 nen 1m co open_time {@code ts_h-60m .. ts_h-1m}; gia {@code <= 0} -> NaN; {@code high = max(maxPrice)},
 * {@code low = min(minPrice)}, {@code close = priceClose} cua phut HUU HAN CUOI; khong phut nao co close -> khong co
 * bar. Bo STABLE ({@code short_v3_r1_fade.STABLE}). Ten symbol chuan hoa {@code +USDT} nhu {@link S1RankerLive}.
 * <p><b>Thay cho lineage F_TAIL/F_HEAD cua store</b> (offline bo gio ngoai [first_real, last_real] theo
 * {@code data/meta/symbol_lineage_v2.csv}; live khong biet tuong lai): bar gio co {@code sum(totalUsdt) == 0} bi BO
 * ({@link #REQUIRE_VOLUME}). Do tren 7 ngay cuoi DEV: 85 symbol da delist van co ban ghi gia hang so, qv = 0 trong
 * Aerospike -> neu giu, {@code rk_dist_low24} lech toi 0.099; store chi co 7 998/10 009 699 dong qv = 0 trong vung.
 *
 * <p>Lich su: {@link #HIST_HOURS} gio. Warm-up lan dau doc {@code HIST_HOURS x 60} ban ghi phut (batch 60 key/gio);
 * sau do moi gio 60 ban ghi. Gio cuoi {@code lastClosedHour} duoc doc lai moi tick cho toi khi
 * {@code now >= ts_h + COMMIT_LAG_MS} (phut cuoi co the chua chot).
 */
public final class GeomFeatProvider {

    private static final Logger LOG = LoggerFactory.getLogger(GeomFeatProvider.class);
    public static final long H = 3_600_000L;
    public static final long MIN = 60_000L;
    /** 169 gio can thiet + 1 du tru. */
    public static final int HIST_HOURS = GeomFeatureLive.NEED_HOURS + 1;
    /** Sau moc gio nay (ms) moi coi gio da chot va khong doc lai. */
    public static final long COMMIT_LAG_MS = 120_000L;
    /** Bo bar gio khong co khoi luong (xap xi lineage F_TAIL/F_HEAD cua store offline). */
    public static final boolean REQUIRE_VOLUME = true;
    public static final Set<String> STABLE = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "FDUSDUSDT", "USDPUSDT")));

    /** Nguon nen 1m. Tra {@code openTimeMs -> (symbol -> nen)}, phut khong co ban ghi thi vang mat; LOI I/O -> null. */
    public interface MinuteSource {
        Map<Long, Map<String, KlineObjectOptimized>> read(long[] openTimesMs);
    }

    private final MinuteSource src;
    /** {@code ts_h -> (symbol -> {high, low, close})}; key co mat = gio DA doc (co the rong). */
    private final TreeMap<Long, Map<String, double[]>> bars = new TreeMap<>();
    /** Gio da chot (khong doc lai). */
    private long committedThrough = Long.MIN_VALUE;

    public GeomFeatProvider(MinuteSource src) {
        this.src = src;
    }

    static String norm(String k) {
        return k.endsWith("USDT") ? k : k + "USDT";
    }

    private static double pos(float v) {
        return v > 0f ? (double) v : Double.NaN;
    }

    /** Gop cac phut (THEO THU TU THOI GIAN TANG) thanh bar gio; xem quy uoc o dau lop. */
    public static Map<String, double[]> aggregateHour(List<Map<String, KlineObjectOptimized>> minutesAsc) {
        Map<String, double[]> acc = new HashMap<>();   // {hi, lo, close, quoteVol}
        for (Map<String, KlineObjectOptimized> m : minutesAsc) {
            if (m == null) continue;
            for (Map.Entry<String, KlineObjectOptimized> e : m.entrySet()) {
                String sym = norm(e.getKey());
                if (STABLE.contains(sym)) continue;
                KlineObjectOptimized k = e.getValue();
                double hi = pos(k.getMaxPrice()), lo = pos(k.getMinPrice()), cl = pos(k.getPriceClose());
                double[] a = acc.computeIfAbsent(sym, s -> new double[]{Double.NaN, Double.NaN, Double.NaN, 0d});
                if (!Double.isNaN(hi) && (Double.isNaN(a[0]) || hi > a[0])) a[0] = hi;
                if (!Double.isNaN(lo) && (Double.isNaN(a[1]) || lo < a[1])) a[1] = lo;
                if (!Double.isNaN(cl)) a[2] = cl;
                float v = k.getTotalUsdt();
                if (!Float.isNaN(v)) a[3] += v;   // np.nansum(V) cua store (V khong loc > 0)
            }
        }
        acc.values().removeIf(a -> Double.isNaN(a[2]) || (REQUIRE_VOLUME && !(a[3] > 0d)));
        return acc;
    }

    /**
     * Nap cac gio con thieu toi {@code lastClosedHour} (gio DONG). Tra false khi nguon loi (lan sau thu lai).
     */
    public synchronized boolean refresh(long lastClosedHour, long nowMs) {
        long winStart = lastClosedHour - (long) (HIST_HOURS - 1) * H;
        long from = Math.max(winStart, committedThrough == Long.MIN_VALUE ? winStart : committedThrough + H);
        boolean warm = bars.isEmpty();
        long t0 = System.currentTimeMillis();
        int nRead = 0;
        for (long t = from; t <= lastClosedHour; t += H) {
            long[] mins = new long[60];
            for (int k = 0; k < 60; k++) mins[k] = t - 60 * MIN + k * MIN;
            Map<Long, Map<String, KlineObjectOptimized>> got = src.read(mins);
            if (got == null) {
                LOG.error("[GEOM] doc nen 1m LOI tai gio {} -> dung, tick sau thu lai", t);
                return false;
            }
            List<Map<String, KlineObjectOptimized>> asc = new ArrayList<>(60);
            for (long m : mins) asc.add(got.get(m));
            bars.put(t, aggregateHour(asc));
            nRead += got.size();
            if (nowMs >= t + COMMIT_LAG_MS) committedThrough = t;
        }
        bars.headMap(winStart, false).clear();
        if (warm) {
            LOG.info("[GEOM] warm-up {} gio ({} ban ghi phut) toi {} trong {} ms", bars.size(), nRead, lastClosedHour,
                    System.currentTimeMillis() - t0);
        }
        return true;
    }

    /** Du lich su cho gio {@code lastClosedHour}: CA {@link #HIST_HOURS} gio da doc. */
    public synchronized boolean ready(long lastClosedHour) {
        for (int k = 0; k < HIST_HOURS; k++) {
            if (!bars.containsKey(lastClosedHour - (long) k * H)) return false;
        }
        return true;
    }

    /**
     * 9 feature GEOM cho MOI symbol co bar trong cua so, tai gio {@code lastClosedHour}. Chua du lich su -> null
     * (caller BO tick, khong thay bang NaN toan cot — offline luc do da co gia tri).
     */
    public synchronized Map<String, double[]> features(long lastClosedHour) {
        if (!ready(lastClosedHour)) return null;
        int n = HIST_HOURS;
        Map<String, double[][]> arr = new HashMap<>();
        for (int k = 0; k < n; k++) {
            Map<String, double[]> b = bars.get(lastClosedHour - (long) (n - 1 - k) * H);
            for (Map.Entry<String, double[]> e : b.entrySet()) {
                double[][] a = arr.computeIfAbsent(e.getKey(), s -> {
                    double[][] z = new double[3][n];
                    for (double[] r : z) Arrays.fill(r, Double.NaN);
                    return z;
                });
                a[0][k] = e.getValue()[0];
                a[1][k] = e.getValue()[1];
                a[2][k] = e.getValue()[2];
            }
        }
        return GeomFeatureLive.computeTick(arr, n - 1);
    }

    /** So gio dang giu (test/log). */
    public synchronized int hoursHeld() {
        return bars.size();
    }

    static String minuteKey(long ms) {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd-HHmm");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        return f.format(new Date(ms));
    }

    /**
     * Nguon Aerospike: batch-get {@code ns/set/key-phut(GMT+7)} bin {@code data} (snappy(MinuteDataFinal)) — cung
     * dinh dang {@code DataManagerAerospikeFloatSim.getExistingTickersMap}, nhung batch 60 key/lan va KHONG nuot loi.
     */
    public static MinuteSource aerospike(AerospikeClient client, String ns, String set) {
        return mins -> {
            Key[] keys = new Key[mins.length];
            for (int k = 0; k < mins.length; k++) keys[k] = new Key(ns, set, minuteKey(mins[k]));
            try {
                Record[] rs = client.get(new BatchPolicy(), keys);
                Map<Long, Map<String, KlineObjectOptimized>> out = new HashMap<>();
                for (int k = 0; k < rs.length; k++) {
                    if (rs[k] == null) continue;
                    byte[] data = (byte[]) rs[k].getValue("data");
                    if (data == null) continue;
                    out.put(mins[k], MinuteDataFinal.parseFrom(Snappy.uncompress(data)).getTickersMap());
                }
                return out;
            } catch (Exception e) {
                LOG.error("[GEOM] batch-get {} key ns={} set={} loi: {}", keys.length, ns, set, e.toString());
                return null;
            }
        };
    }
}
