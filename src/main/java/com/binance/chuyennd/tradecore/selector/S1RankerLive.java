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
 * {@code featv2/feat_v2_x1.parquet} — xem {@code docs/experiment/L2_PORT_C3.md} cong 1) -> 9 feature qua
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

    /**
     * Namespace mac dinh cua cum Aerospike-242. Do TRUC TIEP bang
     * {@code client.info_all('namespaces')} ? xem {@code Configs} muc 9.
     */
    public static final String NS_242_DEFAULT = "ticker";

    /**
     * [L5 2026-09-07] Namespace THAT dung cho warm-up close 1h.
     *
     * <p>BUG da sua: {@code config.properties} cua bot live tren 242 KHONG khai bao
     * {@code AEROSPIKE_NAMESPACE_242} (key nay them 2026-08-05 chi cho 2 tool copy chay tren
     * Oracle) => {@code Configs.AEROSPIKE_NAMESPACE_242 == null} => {@code new Key(null, ...)}
     * => {@code DataManagerAerospikeFloatSim.getExistingTickersMap} co {@code catch} RONG nen
     * NUOT NPE => warm-up doc duoc 0/384 moc gio => {@code [S1] chi co 0 coin} moi tick.
     * Tren Oracle key co san nen shadow L2 chay tot ? khac biet nam O CONFIG, khong o du lieu.
     *
     * <p>Nay: thieu key => ve {@link #NS_242_DEFAULT} va LOG ro nguon, KHONG de null di tiep.
     */
    public static final String NS_242 = resolveNs242(Configs.AEROSPIKE_NAMESPACE_242);

    /** Thuan tinh toan (unit-test): null/rong -> {@link #NS_242_DEFAULT}, con lai trim. */
    public static String resolveNs242(String cfg) {
        return (cfg == null || cfg.trim().isEmpty()) ? NS_242_DEFAULT : cfg.trim();
    }

    /** So coin co it nhat {@code minPts} moc close 1h KHONG NaN trong cua so warm-up. */
    public static int countReady(Map<String, double[]> closes, int minPts) {
        int ready = 0;
        if (closes == null) return 0;
        for (double[] c : closes.values()) {
            if (c == null) continue;
            int n = 0;
            for (double v : c) if (!Double.isNaN(v)) n++;
            if (n >= minPts) ready++;
        }
        return ready;
    }

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
            int ready = countReady(closes, S1FeatureLive.WARMUP_HOURS);
            if (closes.size() < 20 || ready < 20) {
                // ERROR (khong phai WARN): warm-up hong la LOI cau hinh/du lieu, phai bat duoc
                // bang `grep -c ERROR`, khong duoc chim trong WARN nhu dot 07/09.
                LOG.error("[S1] warm-up CHUA DU -> BO tick nay (KHONG fallback pNoPump). "
                                + "{} coin co chuoi close 1h, {} coin du >= {} moc. "
                                + "Nguon aerospike {}:{} ns={} set={}",
                        closes.size(), ready, S1FeatureLive.WARMUP_HOURS,
                        Configs.AEROSPIKE_HOST_242, Configs.AEROSPIKE_PORT_242, NS_242, SET_TICKER);
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
            LOG.info("[S1] score {} coin tai {} (hist gio cuoi {}, {} coin du >= {} moc, ns={})",
                    out.size(), now, lastClosedHour, ready, S1FeatureLive.WARMUP_HOURS, NS_242);
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
        boolean firstWarmup = (lastHourLoaded == 0L);
        long from = firstWarmup
                ? lastClosedHour - (long) (HIST_HOURS - 1) * H
                : lastHourLoaded + H;
        if (from > lastClosedHour) return;
        int want = (int) ((lastClosedHour - from) / H) + 1;
        if (firstWarmup) {
            LOG.info("[S1] warm-up BAT DAU: nguon aerospike {}:{} ns={} set={} | doc {} moc gio "
                            + "({} -> {}), can >= {} moc close 1h moi coin",
                    Configs.AEROSPIKE_HOST_242, Configs.AEROSPIKE_PORT_242, NS_242, SET_TICKER,
                    want, from, lastClosedHour, S1FeatureLive.WARMUP_HOURS);
        }
        long tStart = System.currentTimeMillis();
        int cnt = 0;
        for (long t = from; t <= lastClosedHour; t += H) {
            // quy uoc VISION: close cua gio t = nen 1m co open_time = t - 1m
            Map<String, KlineObjectOptimized> m = DataManagerAerospikeFloatSim.getExistingTickersMap(
                    new Key(NS_242, SET_TICKER, minuteKey(t - MIN)));
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
        long ms = System.currentTimeMillis() - tStart;
        if (cnt > 0) {
            LOG.info("[S1] nap {}/{} moc gio close (toi {}), {} coin trong bo nho, {} ms "
                            + "(ns={} set={})",
                    cnt, want, lastClosedHour, hist.size(), ms, NS_242, SET_TICKER);
        } else {
            LOG.error("[S1] warm-up DOC 0/{} moc gio tu {}:{} ns={} set={} trong {} ms. "
                            + "Kiem: key AEROSPIKE_NAMESPACE_242 trong config.properties, "
                            + "hoac du lieu kline_1m_opt tren cum do.",
                    want, Configs.AEROSPIKE_HOST_242, Configs.AEROSPIKE_PORT_242, NS_242,
                    SET_TICKER, ms);
            probeSource(lastClosedHour);
        }
    }

    /**
     * Doc THU MOT ban ghi bang chinh client/ns/set cua warm-up, nhung KHONG di qua
     * {@code getExistingTickersMap} (ham do co {@code catch} rong nen nuot exception) ? de
     * exception THAT hien ra trong log. Chi goi khi warm-up doc duoc 0 moc.
     */
    private void probeSource(long lastClosedHour) {
        String k = minuteKey(lastClosedHour - MIN);
        try {
            com.aerospike.client.Record r = DataManagerAerospikeFloatSim.getClient242()
                    .get(null, new Key(NS_242, SET_TICKER, k));
            LOG.error("[S1] warm-up PROBE ns={} set={} key={} -> {}", NS_242, SET_TICKER, k,
                    r == null ? "RECORD NULL (ns/set dung nhung KHONG co du lieu o moc nay)"
                              : "RECORD OK (doc duoc ? loi nam o cho khac)");
        } catch (Throwable t) {
            LOG.error("[S1] warm-up PROBE ns={} set={} key={} -> EXCEPTION {}", NS_242, SET_TICKER,
                    k, t.toString());
        }
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
