package com.binance.chuyennd.tradecore.selector;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtSession;
import com.aerospike.client.Key;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiFeatLiveSets;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.tradecore.Cfg;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;

/**
 * SELECTOR S1 REAL-TIME — thay THU TU xep hang cua duong live bang score cua model S1
 * (XGBRanker, fold cutoff 20251001, xem {@code research/pipeline/x1/x1_s1_save_model.py}).
 * CHI chay khi {@link LiveProfileC3#on()}.
 *
 * <p>Duong di: chuoi close 1h dung tu {@code kline_1m_opt} tren Aerospike-242 (quy uoc VISION:
 * {@code close(t)} = {@code priceClose} cua nen 1m {@code open_time = t - 1m}, da do khop
 * {@code featv2/feat_v2_x1.parquet} — xem {@code docs/L2_PORT_C3.md} cong 1) -> 9 feature qua
 * {@link S1FeatureLive} (2 feature OI lay tu {@link LiveOiFeatProvider}) -> ONNX -> score.
 * <b>score THAP = TOT</b> (cung quy uoc {@code pred_s1a2x1.parquet}: {@code score = -predict}).
 *
 * <p>Warm-up: doc lui {@link S1FeatureLive#WARMUP_HOURS} + du tru gio luc khoi dong; moi gio moi
 * chi doc them 1 ban ghi phut.
 */
public final class S1RankerLive {

    private static final Logger LOG = LoggerFactory.getLogger(S1RankerLive.class);
    private static volatile S1RankerLive INSTANCE;

    private static final String SET_TICKER = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER;
    private static final long H = S1FeatureLive.HOUR_MS;
    private static final long MIN = 60_000L;
    /** Du tru them 2 ngay tren lookback 336h de rolling min_periods khong bi cut. */
    private static final int HIST_HOURS = S1FeatureLive.WARMUP_HOURS + 48;

    private final Map<String, TreeMap<Long, Double>> hist = new HashMap<>();
    /** {@code symbol -> [oi_delta24h, ls_global]} — CHI 2 set S1 can (LiveOiFeatProvider nap ca 5). */
    private final Map<String, TreeMap<Long, Float>[]> oiCache = new HashMap<>();
    /** Moc gio cua lan nap OI gan nhat: {@code ComputeOiFeat2Live242} cadence 60' nen nap 1 lan/gio. */
    private long oiCacheHour = 0L;
    private OrtEnvironment env;
    private OrtSession session;
    private String inputName;
    private long lastHourLoaded = 0L;
    private boolean broken = false;

    private S1RankerLive() {
        String path = Cfg.get("S1_MODEL_ONNX");
        if (path == null || path.trim().isEmpty()) {
            path = "/home/ubuntu/s1_model/s1a2x1_cut20251001.onnx";
        }
        try {
            env = OrtEnvironment.getEnvironment();
            session = env.createSession(path.trim(), new OrtSession.SessionOptions());
            inputName = session.getInputNames().iterator().next();
            LOG.info("[S1] nap model ONNX {} input={} nFeature={}", path, inputName,
                    S1FeatureLive.FEATURE_ORDER.length);
        } catch (Throwable t) {
            broken = true;
            LOG.error("[S1] KHONG nap duoc model ONNX {}: {} -> selector giu thu tu pNoPump cu",
                    path, t.toString());
        }
    }

    public static S1RankerLive getInstance() {
        if (INSTANCE == null) {
            synchronized (S1RankerLive.class) {
                if (INSTANCE == null) INSTANCE = new S1RankerLive();
            }
        }
        return INSTANCE;
    }

    public boolean isReady() {
        return !broken;
    }

    /**
     * Score S1 cho tung coin trong {@code universe} tai thoi diem {@code now}.
     * Tra {@code null} khi chua san sang (model loi / chua du lich su) — caller PHAI giu
     * duong cu khi do.
     */
    public synchronized Map<String, Float> scoreAll(Collection<String> universe, long now) {
        if (broken || universe == null || universe.isEmpty()) return null;
        try {
            long lastClosedHour = (now / H) * H;      // moc gio da co day du 60 nen 1m truoc do
            refresh(universe, lastClosedHour);
            int n = HIST_HOURS;
            Map<String, double[]> closes = new LinkedHashMap<>();
            for (String sym : universe) {
                TreeMap<Long, Double> m = hist.get(sym);
                if (m == null || m.isEmpty()) continue;
                double[] arr = new double[n];
                Arrays.fill(arr, Double.NaN);
                for (int i = 0; i < n; i++) {
                    Double v = m.get(lastClosedHour - (long) (n - 1 - i) * H);
                    if (v != null) arr[i] = v;
                }
                closes.put(sym, arr);
            }
            if (closes.size() < 20) {
                LOG.warn("[S1] chi co {} coin du lich su close 1h -> bo qua tick nay", closes.size());
                return null;
            }
            ensureOi(closes.keySet(), lastClosedHour);
            Map<String, Double> lsg = new HashMap<>();
            Map<String, Double> oid = new HashMap<>();
            for (String sym : closes.keySet()) {
                TreeMap<Long, Float>[] a = oiCache.get(sym);
                Long ref = a == null ? null : floorTol(a[0], now);
                if (ref == null && a != null) ref = floorTol(a[1], now);
                oid.put(sym, ref == null ? Double.NaN : valOf(a[0], ref));
                lsg.put(sym, ref == null ? Double.NaN : valOf(a[1], ref));
            }
            Map<String, double[]> feat = S1FeatureLive.computeTick(closes, n - 1, lsg, oid);
            String[] syms = feat.keySet().toArray(new String[0]);
            float[][] x = new float[syms.length][S1FeatureLive.FEATURE_ORDER.length];
            for (int i = 0; i < syms.length; i++) {
                double[] v = feat.get(syms[i]);
                for (int j = 0; j < v.length; j++) x[i][j] = (float) v[j];
            }
            float[] raw = predict(x);
            if (raw == null) return null;
            Map<String, Float> out = new HashMap<>();
            for (int i = 0; i < syms.length; i++) out.put(syms[i], -raw[i]);   // score thap = tot
            LOG.info("[S1] score {} coin tai {} (hist gio cuoi {})", out.size(), now, lastClosedHour);
            return out;
        } catch (Throwable t) {
            LOG.error("[S1] loi khi tinh score: {}", t.toString());
            return null;
        }
    }

    private float[] predict(float[][] x) {
        try (OnnxTensor t = OnnxTensor.createTensor(env, x);
             OrtSession.Result r = session.run(Collections.singletonMap(inputName, t))) {
            Object v = r.get(0).getValue();
            if (v instanceof float[][]) {
                float[][] m = (float[][]) v;
                float[] o = new float[m.length];
                for (int i = 0; i < m.length; i++) o[i] = m[i][0];
                return o;
            }
            return (float[]) v;
        } catch (Throwable e) {
            LOG.error("[S1] ONNX run loi: {}", e.toString());
            return null;
        }
    }

    /** Nap cac moc gio con thieu (warm-up lan dau; sau do moi gio 1 ban ghi). */
    private void refresh(Collection<String> universe, long lastClosedHour) {
        long from = (lastHourLoaded == 0L)
                ? lastClosedHour - (long) (HIST_HOURS - 1) * H
                : lastHourLoaded + H;
        if (from > lastClosedHour) return;
        int cnt = 0;
        for (long t = from; t <= lastClosedHour; t += H) {
            // quy uoc VISION: close cua gio t = nen 1m co open_time = t - 1m
            Map<String, KlineObjectOptimized> m = DataManagerAerospikeFloatSim.getExistingTickersMap(
                    new Key(Configs.AEROSPIKE_NAMESPACE_242, SET_TICKER, minuteKey(t - MIN)));
            if (m.isEmpty()) continue;
            cnt++;
            for (Map.Entry<String, KlineObjectOptimized> e : m.entrySet()) {
                String sym = e.getKey().endsWith("USDT") ? e.getKey() : e.getKey() + "USDT";
                float pc = e.getValue().getPriceClose();
                if (pc <= 0f) continue;
                hist.computeIfAbsent(sym, k -> new TreeMap<>()).put(t, (double) pc);
            }
        }
        lastHourLoaded = lastClosedHour;
        long cutoff = lastClosedHour - (long) HIST_HOURS * H;
        for (TreeMap<Long, Double> m : hist.values()) m.headMap(cutoff, false).clear();
        if (cnt > 0) LOG.info("[S1] nap {} moc gio close (toi {}), {} coin trong bo nho",
                cnt, lastClosedHour, hist.size());
    }

    /**
     * Nap {@code oi_feat_delta24h} + {@code oi_feat_lsg} tu 242, MOI GIO MOT LAN (cadence cua
     * {@code ComputeOiFeat2Live242} la 60'). Doc SONG SONG: tu Oracle sang 242 la duong WAN,
     * moi {@code getMetricMap242} la mot round-trip; doc tuan tu 700 coin mat vai phut.
     */
    @SuppressWarnings("unchecked")
    private void ensureOi(java.util.Set<String> syms, long lastClosedHour) {
        if (oiCacheHour == lastClosedHour && !oiCache.isEmpty()) return;
        long t0 = System.currentTimeMillis();
        java.util.concurrent.ExecutorService ex = java.util.concurrent.Executors.newFixedThreadPool(8);
        Map<String, TreeMap<Long, Float>[]> fresh = new java.util.concurrent.ConcurrentHashMap<>();
        try {
            java.util.List<java.util.concurrent.Future<?>> fs = new java.util.ArrayList<>();
            for (String sym : syms) {
                fs.add(ex.submit(() -> {
                    TreeMap<Long, Float> d = DataManagerAerospikeFloatSim.getMetricMap242(
                            OiFeatLiveSets.OI_DELTA24H, OiFeatLiveSets.BIN, sym);
                    TreeMap<Long, Float> g = DataManagerAerospikeFloatSim.getMetricMap242(
                            OiFeatLiveSets.LS_GLOBAL, OiFeatLiveSets.BIN, sym);
                    fresh.put(sym, new TreeMap[]{tail(d, lastClosedHour), tail(g, lastClosedHour)});
                }));
            }
            for (java.util.concurrent.Future<?> f : fs) f.get();
        } catch (Exception e) {
            LOG.error("[S1] nap OI loi: {}", e.toString());
        } finally {
            ex.shutdownNow();
        }
        if (!fresh.isEmpty()) {
            oiCache.clear();
            oiCache.putAll(fresh);
            oiCacheHour = lastClosedHour;
            LOG.info("[S1] nap OI (delta24h + ls_global) cho {} coin trong {} ms", fresh.size(),
                    System.currentTimeMillis() - t0);
        }
    }

    /** Cat map ve 24h gan nhat (>> MERGE_TOL_MS 2h) — giong FIX OOM cua LiveOiFeatProvider. */
    private static TreeMap<Long, Float> tail(TreeMap<Long, Float> m, long ref) {
        if (m == null || m.isEmpty()) return m;
        return new TreeMap<>(m.tailMap(ref - 24L * 3600_000L, true));
    }

    private static Long floorTol(TreeMap<Long, Float> m, long t) {
        if (m == null || m.isEmpty()) return null;
        Long k = m.floorKey(t);
        if (k == null || (t - k) > OiFeatLiveSets.MERGE_TOL_MS) return null;
        return k;
    }

    private static double valOf(TreeMap<Long, Float> m, long ts) {
        if (m == null) return Double.NaN;
        Float v = m.get(ts);
        return v == null ? Double.NaN : v;
    }

    private static String minuteKey(long ms) {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd-HHmm");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        return f.format(new Date(ms));
    }
}
