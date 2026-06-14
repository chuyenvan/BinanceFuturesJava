package com.binance.chuyennd.ai_ml.features.export;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.google.gson.reflect.TypeToken;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.FileWriter;
import java.lang.reflect.Type;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-017 (H1_GATE_SPEC §2.2 B1–B5 + B7) — export FEATURE GATE NHÓM B (giá/xu-hướng + funding-breadth),
 * CODE MỚI. Align {@code t} với {@code gate_return.csv} (lưới 15m, 2021→nay). Mỗi feature validate RIÊNG.
 * B6/B8 (OI/LS-market) = TASK-018 (chờ 013).
 *
 * <p><b>Nguồn (đọc-only 226):</b> {@code kline_15m_btceth} + {@code kline_4h_btceth} (TASK-009; key
 * {@code SYMBOL-YYYYMM}, bin {@code data}=Snappy(gson(TreeMap&lt;startMs,float[o,h,l,c,v]&gt;))), daily BTC
 * gom từ 4h (B3 MA200), {@code funding_data} (B7, qua {@link DataManagerAerospikeFloatSim#getAllFundingMap}).
 *
 * <p><b>13 cột:</b> b1_sma20_15m, b1_sma50_4h · b2_alignment, b2_bearRally · b3_distMA200, b3_regime ·
 * b4_ethRet15m, b4_ethRet4h · b5_coDown, b5_dispersion, b5_rollingCorr · b7_pctFundingHigh, b7_fundingDispersion.
 *
 * <p><b>Look-ahead clean (bẫy #1):</b> tại quyết định {@code t} (biên 15m) chỉ dùng nến ĐÓNG ≤ t —
 * {@code closedBy(series,t,frameMs) = series.headMap(t-frameMs, true)} (nến [t, t+frame) là TƯƠNG LAI, loại).
 * B7 ngưỡng cao = <b>expanding histogram percentile</b>: chỉ nạp điểm funding có {@code ts ≤ t} (stream con trỏ
 * theo t) → KHÔNG dùng percentile full-sample (không rò tương lai). Ghi rõ cách tính.
 *
 * <p><b>Warmup KHÔNG fill 0 (bẫy #2):</b> B3 MA200 (cần 200 ngày) + B5 rollingCorr (cần 96 nến 15m) thiếu
 * dữ liệu → ô để TRỐNG (CSV NaN), KHÔNG ghi 0 (0 nghĩa SAI). Vẫn emit dòng (feature khác hợp lệ) để align.
 *
 * <p><b>Survivorship:</b> B7 aggregate GỒM mọi coin trong {@code funding_data} (getAllFundingMap KHÔNG lọc
 * {@code diedSymbol}); báo #coin/năm trong validate.
 */
public class ExportGateFeaturesGroupB {

    private static final Logger LOG = LoggerFactory.getLogger(ExportGateFeaturesGroupB.class);
    private static final long MS_15M = 15L * 60_000L, MS_4H = 240L * 60_000L, DAY = 24L * 3600_000L;
    private static final String SET_15M = "kline_15m_btceth", SET_4H = "kline_4h_btceth";
    private static final Type SERIES_TYPE = new TypeToken<TreeMap<Long, float[]>>() {}.getType();
    private static final String START_DATE = "20210101";
    private static final String OUT = "outputs/gate_features_groupB_now.csv";
    private static final String GATE_RETURN = "outputs/gate_return.csv";

    private static final int SMA_15M = 20, SMA_4H = 50, MA_DAILY = 200, MOM_SHORT_N = 4, CORR_W = 96;
    private static final String[] COLS = {
            "b1_sma20_15m", "b1_sma50_4h", "b2_alignment", "b2_bearRally", "b3_distMA200", "b3_regime",
            "b4_ethRet15m", "b4_ethRet4h", "b5_coDown", "b5_dispersion", "b5_rollingCorr",
            "b7_pctFundingHigh", "b7_fundingDispersion"
    };

    public static void main(String[] args) {
        try {
            Configs.IS_HPO_MODE = false;
            Configs.IS_KAGGLE_MODE = true; // đọc 226 local

            long start = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
            long end = System.currentTimeMillis();
            LOG.info("🏷️ TASK-017 export feature gate NHÓM B | từ {} → nay | lưới 15m | {} cột", START_DATE, COLS.length);

            // 1) Nạp series 15m/4h BTC+ETH
            TreeMap<Long, float[]> btc15 = readSeries(SET_15M, "BTCUSDT"), eth15 = readSeries(SET_15M, "ETHUSDT");
            TreeMap<Long, float[]> btc4 = readSeries(SET_4H, "BTCUSDT"), eth4 = readSeries(SET_4H, "ETHUSDT");
            LOG.info("📥 series: btc15={} eth15={} btc4={} eth4={}", btc15.size(), eth15.size(), btc4.size(), eth4.size());
            if (btc15.isEmpty() || btc4.isEmpty()) throw new IllegalStateException("kline_15m/4h BTC rỗng — chạy TASK-009/031 trước.");

            // 2) daily close BTC gom từ 4h (close của nến 4h có start lớn nhất trong ngày)
            TreeMap<Long, Float> dailyClose = buildDaily(btc4);
            LOG.info("📥 dailyClose BTC = {} ngày (cho MA200)", dailyClose.size());

            // 3) funding tất cả coin (B7) — getAllFundingMap KHÔNG lọc died
            Map<String, TreeMap<Long, Float>> funding = DataManagerAerospikeFloatSim.getAllFundingMap();
            LOG.info("📥 funding_data = {} coin", funding.size());
            FundingBreadth fb = new FundingBreadth(funding);

            FileWriter w = new FileWriter(OUT);
            w.write("tEpochMs,tDate," + String.join(",", COLS) + "\n");
            Validate v = new Validate();
            long emitted = 0;

            for (Long t : btc15.keySet()) {
                if (t < start) continue;
                fb.advance(t); // nạp funding ts ≤ t vào histogram + cập nhật current per-coin
                Float[] f = compute(t, btc15, eth15, btc4, eth4, dailyClose, fb);
                StringBuilder sb = new StringBuilder(160);
                sb.append(t).append(',').append(FMT.get().format(new Date(t)));
                for (Float val : f) sb.append(',').append(val == null ? "" : fmt(val));
                sb.append('\n');
                w.write(sb.toString());
                emitted++;
                v.collect(t, f, fb.activeCount());
            }
            w.close();
            LOG.info("✅ Ghi {} dòng × {} feature → {}", emitted, COLS.length, OUT);
            v.report(btc15, eth15, btc4, eth4, dailyClose);
        } catch (Exception e) {
            LOG.error("ExportGateFeaturesGroupB lỗi", e);
            System.exit(1);
        }
        System.exit(0); // TASK-017 #6: thoát sạch (Aerospike client thread non-daemon)
    }

    /** 13 feature tại t; null = warmup/thiếu (KHÔNG fill 0). */
    private static Float[] compute(long t, TreeMap<Long, float[]> btc15, TreeMap<Long, float[]> eth15,
                                   TreeMap<Long, float[]> btc4, TreeMap<Long, float[]> eth4,
                                   TreeMap<Long, Float> dailyClose, FundingBreadth fb) {
        Float[] r = new Float[COLS.length];
        // nến đóng ≤ t
        NavigableMap<Long, float[]> b15 = btc15.headMap(t - MS_15M, true);
        NavigableMap<Long, float[]> e15 = eth15.headMap(t - MS_15M, true);
        NavigableMap<Long, float[]> b4 = btc4.headMap(t - MS_4H, true);
        NavigableMap<Long, float[]> e4 = eth4.headMap(t - MS_4H, true);

        Float close15 = lastClose(b15), sma20_15 = smaClose(b15, SMA_15M);
        Float close4 = lastClose(b4), sma50_4 = smaClose(b4, SMA_4H);
        // B1
        if (close15 != null && sma20_15 != null && sma20_15 != 0) r[0] = close15 / sma20_15 - 1f;
        if (close4 != null && sma50_4 != null && sma50_4 != 0) r[1] = close4 / sma50_4 - 1f;
        // B2 alignment + bearRally
        Integer trendLong = (close4 != null && sma50_4 != null) ? (int) Math.signum(close4 - sma50_4) : null;
        Float ret15N = retN(b15, MOM_SHORT_N);
        Integer momShort = ret15N == null ? null : (int) Math.signum(ret15N);
        if (trendLong != null && momShort != null) {
            r[2] = (float) (momShort * trendLong);
            r[3] = (trendLong < 0 && momShort > 0) ? 1f : 0f;
        }
        // B3 regime MA200 daily
        NavigableMap<Long, Float> dC = dailyClose.headMap(t - DAY, true);
        if (dC.size() >= MA_DAILY) {
            double sum = 0; int c = 0;
            for (Float cl : descNvalues(dC, MA_DAILY)) { sum += cl; c++; }
            float ma200 = (float) (sum / c);
            float curDaily = dC.lastEntry().getValue();
            if (ma200 != 0) { r[4] = curDaily / ma200 - 1f; r[5] = Math.signum(r[4]); }
        } // else warmup → null
        // B4 ETH momentum
        r[6] = retN(e15, 1);
        r[7] = retN(e4, 1);
        // B5 đồng-pha
        Float btcRet4 = retN(b4, 1), ethRet4 = retN(e4, 1);
        if (btcRet4 != null && ethRet4 != null) {
            r[8] = (btcRet4 < 0 && ethRet4 < 0) ? 1f : 0f;
            r[9] = Math.abs(btcRet4 - ethRet4);
        }
        r[10] = rollingCorr(b15, e15, CORR_W); // null nếu <CORR_W returns (warmup)
        // B7 funding-breadth
        Float[] b7 = fb.snapshot();
        r[11] = b7[0];
        r[12] = b7[1];
        return r;
    }

    // ---------- helpers series ----------
    private static Float lastClose(NavigableMap<Long, float[]> m) { return m.isEmpty() ? null : m.lastEntry().getValue()[3]; }

    private static Float smaClose(NavigableMap<Long, float[]> m, int n) {
        if (m.size() < n) return null;
        double s = 0; int c = 0;
        for (float[] v : descN(m, n)) { s += v[3]; c++; }
        return (float) (s / c);
    }

    /** return close-to-close qua n nến ĐÃ đóng (cur vs cur−n). null nếu thiếu. */
    private static Float retN(NavigableMap<Long, float[]> m, int n) {
        if (m.size() < n + 1) return null;
        Iterator<float[]> it = descIter(m);
        float[] cur = it.next();
        float[] past = cur;
        for (int i = 0; i < n; i++) past = it.next();
        if (past[3] == 0) return null;
        return cur[3] / past[3] - 1f;
    }

    /** Pearson corr của return 15m BTC vs ETH trên cửa sổ W nến gần nhất (đã đóng). null nếu thiếu. */
    private static Float rollingCorr(NavigableMap<Long, float[]> b, NavigableMap<Long, float[]> e, int w) {
        if (b.size() < w + 1 || e.size() < w + 1) return null;
        float[] rb = retsDesc(b, w), re = retsDesc(e, w);
        if (rb == null || re == null) return null;
        double mb = 0, me = 0;
        for (int i = 0; i < w; i++) { mb += rb[i]; me += re[i]; }
        mb /= w; me /= w;
        double cov = 0, vb = 0, ve = 0;
        for (int i = 0; i < w; i++) {
            double db = rb[i] - mb, de = re[i] - me;
            cov += db * de; vb += db * db; ve += de * de;
        }
        if (vb <= 0 || ve <= 0) return null;
        return (float) (cov / Math.sqrt(vb * ve));
    }

    /** w return gần nhất (desc theo thời gian) — cần w+1 close liền kề. */
    private static float[] retsDesc(NavigableMap<Long, float[]> m, int w) {
        Iterator<float[]> it = descIter(m);
        float[] out = new float[w];
        float[] newer = it.next();
        for (int i = 0; i < w; i++) {
            if (!it.hasNext()) return null;
            float[] older = it.next();
            out[i] = older[3] == 0 ? 0f : (newer[3] / older[3] - 1f);
            newer = older;
        }
        return out;
    }

    private static List<float[]> descN(NavigableMap<Long, float[]> m, int n) {
        List<float[]> out = new ArrayList<>(n);
        Iterator<float[]> it = descIter(m);
        for (int i = 0; i < n && it.hasNext(); i++) out.add(it.next());
        return out;
    }

    private static List<Float> descNvalues(NavigableMap<Long, Float> m, int n) {
        List<Float> out = new ArrayList<>(n);
        Iterator<Float> it = m.descendingMap().values().iterator();
        for (int i = 0; i < n && it.hasNext(); i++) out.add(it.next());
        return out;
    }

    private static Iterator<float[]> descIter(NavigableMap<Long, float[]> m) { return m.descendingMap().values().iterator(); }

    private static TreeMap<Long, Float> buildDaily(TreeMap<Long, float[]> btc4) {
        TreeMap<Long, Float> daily = new TreeMap<>();
        for (Map.Entry<Long, float[]> e : btc4.entrySet()) {
            long d = Math.floorDiv(e.getKey(), DAY) * DAY;
            daily.put(d, e.getValue()[3]); // entrySet ASC → ghi đè đến nến 4h start lớn nhất trong ngày = close cuối ngày
        }
        return daily;
    }

    /** Đọc series month-key SYMBOL-YYYYMM (202101..tháng hiện tại) → TreeMap<startMs, float[ohlcv]>. */
    private static TreeMap<Long, float[]> readSeries(String set, String symbol) throws Exception {
        TreeMap<Long, float[]> all = new TreeMap<>();
        AerospikeClient c = DataManagerAerospikeFloatSim.getClient226();
        int curYm = Integer.parseInt(YM.get().format(new Date(System.currentTimeMillis())));
        for (int y = 2021; y <= curYm / 100; y++) {
            for (int mo = 1; mo <= 12; mo++) {
                int ym = y * 100 + mo;
                if (ym > curYm) break;
                Record r = c.get(null, new Key(Configs.AEROSPIKE_NAMESPACE, set, symbol + "-" + String.format("%04d%02d", y, mo)));
                if (r == null) continue;
                byte[] comp = (byte[]) r.getValue("data");
                if (comp == null) continue;
                TreeMap<Long, float[]> ser = Utils.gson.fromJson(new String(Snappy.uncompress(comp), "UTF-8"), SERIES_TYPE);
                if (ser != null) all.putAll(ser);
            }
        }
        return all;
    }

    private static String fmt(float v) { return String.format(Locale.US, "%.8f", v); }

    private static final ThreadLocal<SimpleDateFormat> FMT =
            ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyyMMdd-HHmm")); // GMT+7
    private static final ThreadLocal<SimpleDateFormat> YM =
            ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyyMM"));

    // ================== B7 funding-breadth: expanding histogram (no-leak) ==================
    /**
     * Stream funding theo thời gian: con trỏ nạp mọi điểm {@code ts ≤ t} vào histogram (expanding) +
     * cập nhật funding HIỆN TẠI mỗi coin. {@code snapshot()} = {pctFundingHigh (% coin > p80 lịch sử),
     * fundingDispersion (std cross-coin)}. p80 từ histogram tích luỹ ≤ t ⇒ KHÔNG rò tương lai.
     */
    private static final class FundingBreadth {
        private final long[] evTs;       // mọi (ts) đã sort tăng dần
        private final String[] evSym;
        private final float[] evVal;
        private int ptr = 0;
        private final Map<String, Float> current = new HashMap<>();
        // histogram [-0.02, 0.02], 400 bin width 0.0001 + under/over
        private static final double LO = -0.02, HI = 0.02; private static final int BINS = 400;
        private final long[] hist = new long[BINS]; private long under = 0, over = 0, total = 0;
        private static final double HIGH_PCTL = 0.80;

        FundingBreadth(Map<String, TreeMap<Long, Float>> funding) {
            int n = 0;
            for (TreeMap<Long, Float> m : funding.values()) n += m.size();
            evTs = new long[n]; evSym = new String[n]; evVal = new float[n];
            // merge tất cả điểm rồi sort theo ts
            Integer[] idx = new Integer[n];
            int i = 0;
            for (Map.Entry<String, TreeMap<Long, Float>> e : funding.entrySet())
                for (Map.Entry<Long, Float> p : e.getValue().entrySet()) {
                    evTs[i] = p.getKey(); evSym[i] = e.getKey(); evVal[i] = p.getValue(); idx[i] = i; i++;
                }
            Arrays.sort(idx, (a, b) -> Long.compare(evTs[a], evTs[b]));
            long[] ts2 = new long[n]; String[] sym2 = new String[n]; float[] val2 = new float[n];
            for (int k = 0; k < n; k++) { ts2[k] = evTs[idx[k]]; sym2[k] = evSym[idx[k]]; val2[k] = evVal[idx[k]]; }
            System.arraycopy(ts2, 0, evTs, 0, n); System.arraycopy(sym2, 0, evSym, 0, n); System.arraycopy(val2, 0, evVal, 0, n);
        }

        void advance(long t) {
            while (ptr < evTs.length && evTs[ptr] <= t) {
                float v = evVal[ptr];
                current.put(evSym[ptr], v);
                addHist(v);
                ptr++;
            }
        }

        private void addHist(float v) {
            total++;
            if (v < LO) { under++; return; }
            if (v >= HI) { over++; return; }
            int b = (int) ((v - LO) / (HI - LO) * BINS);
            if (b < 0) b = 0; if (b >= BINS) b = BINS - 1;
            hist[b]++;
        }

        /** Giá trị tại percentile p (xấp xỉ tâm bin) từ histogram tích luỹ. */
        private float percentile(double p) {
            if (total == 0) return Float.NaN;
            long target = (long) Math.ceil(p * total);
            long cum = under;
            if (cum >= target) return (float) LO;
            for (int b = 0; b < BINS; b++) {
                cum += hist[b];
                if (cum >= target) return (float) (LO + (b + 0.5) / BINS * (HI - LO));
            }
            return (float) HI;
        }

        /** {pctFundingHigh, fundingDispersion} trên coin đang active (đã có funding ≤ t). */
        Float[] snapshot() {
            if (current.isEmpty()) return new Float[]{null, null};
            float thr = percentile(HIGH_PCTL);
            int high = 0, n = current.size();
            double sum = 0;
            for (float v : current.values()) { if (v > thr) high++; sum += v; }
            double mean = sum / n, var = 0;
            for (float v : current.values()) { double d = v - mean; var += d * d; }
            float disp = (float) Math.sqrt(var / n);
            return new Float[]{(float) high / n, disp};
        }

        int activeCount() { return current.size(); }
    }

    // ================== VALIDATE (§2.4) ==================
    private static final class Validate {
        final List<Float>[] dist = lists();
        final long[] nullCnt = new long[COLS.length], zeros = new long[COLS.length];
        final TreeSet<Long> featureT = new TreeSet<>();
        final Map<Integer, Integer> year2activeFunding = new TreeMap<>();
        final List<long[]> watchT = new ArrayList<>();

        @SuppressWarnings("unchecked")
        private static List<Float>[] lists() {
            List<Float>[] a = new List[COLS.length];
            for (int i = 0; i < a.length; i++) a[i] = new ArrayList<>();
            return a;
        }

        void collect(long t, Float[] f, int activeFunding) {
            featureT.add(t);
            for (int i = 0; i < f.length; i++) {
                if (f[i] == null) { nullCnt[i]++; continue; }
                if (Float.isNaN(f[i]) || Float.isInfinite(f[i])) { nullCnt[i]++; continue; }
                if (f[i] == 0f) zeros[i]++;
                dist[i].add(f[i]);
            }
            year2activeFunding.put(year(t), activeFunding); // ghi đè → giá trị cuối năm (đủ phản ánh)
            if (watchT.size() < 5 && (featureT.size() % 19973 == 0 || watchT.isEmpty())) watchT.add(new long[]{t});
        }

        void report(TreeMap<Long, float[]> btc15, TreeMap<Long, float[]> eth15,
                    TreeMap<Long, float[]> btc4, TreeMap<Long, float[]> eth4, TreeMap<Long, Float> dailyClose) {
            long n = featureT.size();
            LOG.info("=== (a) RANGE/PHÂN BỐ mỗi feature (min|p1/p50/p99|max), n-nonNull ===");
            for (int i = 0; i < COLS.length; i++) {
                List<Float> r = new ArrayList<>(dist[i]); Collections.sort(r);
                LOG.info("  {} n={} min={} p1={} p50={} p99={} max={}", String.format("%-22s", COLS[i]), r.size(),
                        r.isEmpty() ? "-" : g(r.get(0)), pc(r, 1), pc(r, 50), pc(r, 99), r.isEmpty() ? "-" : g(r.get(r.size() - 1)));
            }
            LOG.info("=== (b) NULL/NaN (warmup) + 0-count mỗi feature — null KHÔNG fill 0 ===");
            for (int i = 0; i < COLS.length; i++)
                LOG.info("  {} null/NaN={}/{} zeros={}", String.format("%-22s", COLS[i]), nullCnt[i], n, zeros[i]);

            LOG.info("=== (c) RECOMPUTE độc lập ~5 mốc (b4_ethRet15m vs đọc 2 close ETH trực tiếp) ===");
            for (long[] wt : watchT) {
                long t = wt[0];
                NavigableMap<Long, float[]> e15 = eth15.headMap(t - MS_15M, true);
                Float exp = retN(e15, 1);
                Float re = null;
                if (e15.size() >= 2) {
                    Iterator<float[]> it = e15.descendingMap().values().iterator();
                    float[] cur = it.next(); float[] prev = it.next();
                    if (prev[3] != 0) re = cur[3] / prev[3] - 1f;
                }
                LOG.info("  t={} b4_ethRet15m exp={} re={} {}", FMT.get().format(new Date(t)), s(exp), s(re),
                        (exp != null && re != null && Math.abs(exp - re) < 1e-6) ? "KHỚP✅" : "(warmup/—)");
            }

            LOG.info("=== (d) LOOK-AHEAD: closedBy=headMap(t-frameMs,true) (nến [t,t+frame) loại); "
                    + "B7 histogram chỉ nạp ts≤t (expanding, KHÔNG full-sample percentile). MA200/corr warmup→null. ===");

            LOG.info("=== (e) ALIGN với {} ===", GATE_RETURN);
            alignWithGateReturn();

            LOG.info("=== (B7) ngưỡng cao = expanding histogram p80 (ts≤t). #coin active funding cuối mỗi NĂM (survivorship): ===");
            for (Map.Entry<Integer, Integer> e : year2activeFunding.entrySet())
                LOG.info("  {}: active funding coin = {}", e.getKey(), e.getValue());
        }

        private void alignWithGateReturn() {
            try (BufferedReader br = new BufferedReader(new FileReader(GATE_RETURN))) {
                String line = br.readLine();
                long gateRows = 0, missing = 0, minG = Long.MAX_VALUE, maxG = Long.MIN_VALUE;
                while ((line = br.readLine()) != null) {
                    int c = line.indexOf(',');
                    if (c <= 0) continue;
                    long gt = Long.parseLong(line.substring(0, c).trim());
                    gateRows++; minG = Math.min(minG, gt); maxG = Math.max(maxG, gt);
                    if (!featureT.contains(gt)) missing++;
                }
                LOG.info("  gate rows={} range[{}..{}] | feature t={} | gate-t THIẾU trong feature={} {}",
                        gateRows, FMT.get().format(new Date(minG)), FMT.get().format(new Date(maxG)), featureT.size(),
                        missing, missing == 0 ? "ALIGN ✅" : "LỆCH 🔴 (soi warmup/gap)");
            } catch (Exception e) {
                LOG.warn("  ⚠️ không đọc được {} (chạy 012 trước?): {}", GATE_RETURN, e.getMessage());
            }
        }

        private String s(Float v) { return v == null ? "null" : g(v); }
    }

    private static String pc(List<Float> sorted, int p) {
        if (sorted.isEmpty()) return "-";
        int idx = Math.min(sorted.size() - 1, (int) Math.ceil(p / 100.0 * sorted.size()) - 1);
        return g(sorted.get(Math.max(0, idx)));
    }

    private static String g(float v) { return String.format(Locale.US, "%.6f", v); }
    private static int year(long ms) { return Integer.parseInt(new SimpleDateFormat("yyyy").format(new Date(ms))); }
}
