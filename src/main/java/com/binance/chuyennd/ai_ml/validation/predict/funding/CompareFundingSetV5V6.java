package com.binance.chuyennd.ai_ml.validation.predict.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * SO SÁNH set funding-pred MỚI (v6, gen bằng model live 5 lớp — mới xong ~1/3, rải rác theo tháng vì
 * task queue shuffle) với set CŨ (v5, model 1-output đã thất lạc, đang là nguồn của MỌI backtest).
 *
 * MỤC ĐÍCH: định lượng "input backtest dịch bao nhiêu khi chuyển v5 -> v6" => (a) backtest cũ còn tin
 * được không, (b) chuyển v6 có phải HPO/calibrate lại ngưỡng cắt không. ĐÂY LÀ PRED-vs-PRED (không có
 * realized) => KHÔNG cần de-overlap.
 *
 * Tái dùng decode chung qua DataManagerAerospikeFloatSim.getFundingPredsForTimestamps(setName, ts[])
 * (long-packed: symbolId<<32 | floatBits pred[0]; cả v5/v6 đều len=1). READ-ONLY, chạy trên 226.
 */
public class CompareFundingSetV5V6 {

    private static final Logger LOG = LoggerFactory.getLogger(CompareFundingSetV5V6.class);

    // === Tên 2 set (literal — KHÔNG dùng AEROSPIKE_SET_NAME_FUNDING_PRED vì field này đang trỏ v5,
    //     và có thể bị đổi qua lại giữa các phiên). v6 = set model live 5 lớp gen ra. ===
    private static final String SET_V5 = "funding_pred_1m_v5";
    private static final String SET_V6 = "funding_pred_1m_20260606";

    private static final String START_MONTH = "202101";
    private static final int COVERAGE_SAMPLE = 50;     // phút/tháng để đo coverage
    private static final int M_PER_MONTH = 200;        // phút/tháng cho so sánh sâu
    private static final double COV_THRESHOLD = 80.0;  // chỉ so sâu tháng v6 coverage > 80%
    private static final int TOP_K = 10;               // top-K pred thấp nhất (sát pre-filter)
    private static final long SEED = 42;
    private static final int MAX_GLOBAL_PAIRS = 300_000; // reservoir cho percentile/Spearman TỔNG (RAM phẳng)

    private final Random rnd = new Random(SEED);
    private final float cut = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * Configs.AI_DYNAMIC_MAX;

    // ===== accumulator TỔNG (exact) =====
    private long tN = 0;                                 // số cặp join
    private double tSx = 0, tSy = 0, tSxx = 0, tSyy = 0, tSxy = 0;  // Pearson tổng (exact)
    private long tCutV5 = 0, tCutV6 = 0;                 // số cặp <= cut
    private long tDisV5inV6out = 0, tDisV6inV5out = 0;   // bất đồng tại ngưỡng
    private double tAbsDiffSum = 0;                       // |v6-v5| tổng
    private long tOnlyV5 = 0, tOnlyV6 = 0;               // symbol lệch coverage
    private final List<Double> allJaccard = new ArrayList<>();        // 1 giá trị/phút (nhỏ)
    private final List<float[]> reservoir = new ArrayList<>();        // {v5,v6} cap MAX_GLOBAL_PAIRS
    private long reservoirSeen = 0;

    private static class MonthRow {
        String month;
        double covV5, covV6;
        int pairs;
        double pearson, spearman;
        double cutV5Pct, cutV6Pct;
        double jaccardMean;
        boolean deepCompared;
    }

    public static void main(String[] args) {
        try { new CompareFundingSetV5V6().run(); }
        catch (Exception e) { LOG.error("CompareFundingSetV5V6 error", e); }
        System.exit(0);
    }

    public void run() throws Exception {
        long now = System.currentTimeMillis();
        long startMonthMs = Utils.sdfFile.parse(START_MONTH + "01").getTime();
        LOG.info("🔎 SO v5({}) vs v6({}) | cut={} (PREDICT_SYMBOL_RATE_MAX_THRESHOLD x AI_DYNAMIC_MAX) | seed={}",
                SET_V5, SET_V6, String.format(Locale.US, "%.4f", cut), SEED);

        // duyệt mốc đầu mỗi tháng
        List<long[]> months = new ArrayList<>(); // {monthStart, monthEnd}
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(startMonthMs);
        cal.set(Calendar.DAY_OF_MONTH, 1);
        cal.set(Calendar.HOUR_OF_DAY, 0); cal.set(Calendar.MINUTE, 0);
        cal.set(Calendar.SECOND, 0); cal.set(Calendar.MILLISECOND, 0);
        while (cal.getTimeInMillis() < now) {
            long ms = cal.getTimeInMillis();
            cal.add(Calendar.MONTH, 1);
            months.add(new long[]{ms, Math.min(cal.getTimeInMillis(), now)});
        }

        List<MonthRow> rows = new ArrayList<>();

        // ===== BƯỚC 1: COVERAGE theo tháng (in TRƯỚC) =====
        LOG.info("\n================ COVERAGE THEO THÁNG ({} phút mẫu/tháng) ================", COVERAGE_SAMPLE);
        LOG.info(String.format(Locale.US, "%-8s %10s %10s", "tháng", "%v5", "%v6"));
        for (long[] mr : months) {
            MonthRow row = new MonthRow();
            row.month = monthLabel(mr[0]);
            long[] ts = sampleMinutes(mr[0], mr[1], COVERAGE_SAMPLE);
            TreeMap<Long, long[]> v5 = DataManagerAerospikeFloatSim.getFundingPredsForTimestamps(SET_V5, ts);
            TreeMap<Long, long[]> v6 = DataManagerAerospikeFloatSim.getFundingPredsForTimestamps(SET_V6, ts);
            row.covV5 = 100.0 * v5.size() / ts.length;
            row.covV6 = 100.0 * v6.size() / ts.length;
            LOG.info(String.format(Locale.US, "%-8s %9.1f%% %9.1f%%", row.month, row.covV5, row.covV6));
            rows.add(row);
        }

        // ===== BƯỚC 2+3: SO SÂU trên tháng v6 coverage > 80% =====
        LOG.info("\n================ SO SÂU (chỉ tháng v6 coverage > {}%) ================", (int) COV_THRESHOLD);
        for (MonthRow row : rows) {
            if (row.covV6 <= COV_THRESHOLD) continue;
            deepCompareMonth(row, monthStartOf(row.month), monthEndOf(row.month, now));
        }

        report(rows);
    }

    /** So sâu 1 tháng: sample M phút, top-K Jaccard/phút, join cặp, tính stats tháng + dồn vào tổng. */
    private void deepCompareMonth(MonthRow row, long mStart, long mEnd) {
        long[] ts = sampleMinutes(mStart, mEnd, M_PER_MONTH);
        TreeMap<Long, long[]> v5map = DataManagerAerospikeFloatSim.getFundingPredsForTimestamps(SET_V5, ts);
        TreeMap<Long, long[]> v6map = DataManagerAerospikeFloatSim.getFundingPredsForTimestamps(SET_V6, ts);

        List<Double> px = new ArrayList<>();   // pred v5
        List<Double> py = new ArrayList<>();   // pred v6
        List<Double> jac = new ArrayList<>();
        long cutV5 = 0, cutV6 = 0, disA = 0, disB = 0, onlyV5 = 0, onlyV6 = 0;

        for (Long t : v5map.keySet()) {
            long[] a5 = v5map.get(t);
            long[] a6 = v6map.get(t);
            if (a6 == null) continue;   // phút chỉ có ở v5 -> không so được, bỏ

            // (d) top-K thấp nhất mỗi set (full list của set đó) -> Jaccard
            jac.add(jaccard(topKLowest(a5), topKLowest(a6)));

            // join theo symbolId
            Map<Integer, Float> m5 = toMap(a5);
            Map<Integer, Float> m6 = toMap(a6);
            for (Map.Entry<Integer, Float> e : m5.entrySet()) {
                Float p6 = m6.get(e.getKey());
                if (p6 == null) { onlyV5++; continue; }   // symbol có ở v5, thiếu ở v6
                float p5 = e.getValue();
                px.add((double) p5);
                py.add((double) p6);
                if (p5 <= cut) cutV5++;
                if (p6 <= cut) cutV6++;
                if (p5 <= cut && p6 > cut) disA++;
                if (p5 > cut && p6 <= cut) disB++;
                addReservoir(p5, p6);
            }
            for (Integer id : m6.keySet()) if (!m5.containsKey(id)) onlyV6++;
        }

        int n = px.size();
        row.pairs = n;
        row.deepCompared = true;
        if (n == 0) { LOG.warn("⚠️ {} không có cặp join.", row.month); return; }

        double[] x = toArr(px), y = toArr(py);
        row.pearson = pearson(x, y);
        row.spearman = pearson(ranks(x), ranks(y));
        row.cutV5Pct = 100.0 * cutV5 / n;
        row.cutV6Pct = 100.0 * cutV6 / n;
        row.jaccardMean = mean(jac);

        // |diff| tháng
        double[] absd = new double[n];
        for (int i = 0; i < n; i++) absd[i] = Math.abs(y[i] - x[i]);
        Arrays.sort(absd);

        LOG.info(String.format(Locale.US,
                "%s: cặp=%d corrP=%.3f corrS=%.3f | %%<=cut v5=%.2f%% v6=%.2f%% | dis(v5in/v6out)=%.2f%% (v6in/v5out)=%.2f%% | Jacc top%d=%.3f | |Δ| p50=%.4f p90=%.4f | symLệch v5only=%d v6only=%d",
                row.month, n, row.pearson, row.spearman, row.cutV5Pct, row.cutV6Pct,
                100.0 * disA / n, 100.0 * disB / n, TOP_K, row.jaccardMean,
                pct(absd, 50), pct(absd, 90), onlyV5, onlyV6));

        // dồn tổng (exact)
        tN += n;
        for (int i = 0; i < n; i++) {
            tSx += x[i]; tSy += y[i]; tSxx += x[i] * x[i]; tSyy += y[i] * y[i]; tSxy += x[i] * y[i];
            tAbsDiffSum += Math.abs(y[i] - x[i]);
        }
        tCutV5 += cutV5; tCutV6 += cutV6;
        tDisV5inV6out += disA; tDisV6inV5out += disB;
        tOnlyV5 += onlyV5; tOnlyV6 += onlyV6;
        allJaccard.addAll(jac);
    }

    private void report(List<MonthRow> rows) {
        LOG.info("\n================ BẢNG THÁNG (chỉ tháng đã so sâu) ================");
        LOG.info(String.format(Locale.US, "%-8s %8s %8s %12s %12s %10s",
                "tháng", "corrP", "corrS", "%<=cut v5", "%<=cut v6", "Jacc"));
        for (MonthRow r : rows) {
            if (!r.deepCompared) continue;
            LOG.info(String.format(Locale.US, "%-8s %8.3f %8.3f %11.2f%% %11.2f%% %10.3f",
                    r.month, r.pearson, r.spearman, r.cutV5Pct, r.cutV6Pct, r.jaccardMean));
        }

        if (tN == 0) { LOG.warn("⚠️ Không có cặp nào (v6 chưa đủ coverage > {}%?).", (int) COV_THRESHOLD); return; }

        double pearsonTot = pearson(tSx, tSy, tSxx, tSyy, tSxy, tN);
        double[] rv5 = new double[reservoir.size()], rv6 = new double[reservoir.size()];
        for (int i = 0; i < reservoir.size(); i++) { rv5[i] = reservoir.get(i)[0]; rv6[i] = reservoir.get(i)[1]; }
        double spearmanTot = (reservoir.size() > 2) ? pearson(ranks(rv5), ranks(rv6)) : Double.NaN;
        double[] s5 = rv5.clone(), s6 = rv6.clone();
        Arrays.sort(s5); Arrays.sort(s6);
        double[] absd = new double[reservoir.size()];
        for (int i = 0; i < reservoir.size(); i++) absd[i] = Math.abs(rv6[i] - rv5[i]);
        Arrays.sort(absd);
        double[] jacArr = toArr(allJaccard); Arrays.sort(jacArr);

        LOG.info("\n================ TỔNG HỢP ({} cặp join | reservoir {} cho percentile) ================",
                tN, reservoir.size());
        LOG.info("corr Pearson(tổng,exact)={} | Spearman(reservoir)~{}",
                f3(pearsonTot), f3(spearmanTot));
        LOG.info("phân bố v5: p10={} p50={} p90={} | %<=cut={}%",
                f4(pct(s5, 10)), f4(pct(s5, 50)), f4(pct(s5, 90)), f2(100.0 * tCutV5 / tN));
        LOG.info("phân bố v6: p10={} p50={} p90={} | %<=cut={}%",
                f4(pct(s6, 10)), f4(pct(s6, 50)), f4(pct(s6, 90)), f2(100.0 * tCutV6 / tN));
        LOG.info("bất đồng tại ngưỡng cut={}: v5<=cut&v6>cut={}% | v5>cut&v6<=cut={}% (tổng cặp 'đổi phe'={}%)",
                f4(cut), f2(100.0 * tDisV5inV6out / tN), f2(100.0 * tDisV6inV5out / tN),
                f2(100.0 * (tDisV5inV6out + tDisV6inV5out) / tN));
        LOG.info("Jaccard top{} (mỗi phút): mean={} p10={} p50={}",
                TOP_K, f3(mean(allJaccard)), f3(pct(jacArr, 10)), f3(pct(jacArr, 50)));
        LOG.info("|v6-v5|: mean={} p50={} p90={}", f4(tAbsDiffSum / tN), f4(pct(absd, 50)), f4(pct(absd, 90)));
        LOG.info("symbol lệch coverage: v5-only={} | v6-only={}", tOnlyV5, tOnlyV6);

        // ===== CÁCH ĐỌC =====
        LOG.info("\n📌 CÁCH ĐỌC:");
        boolean near = pearsonTot > 0.9
                && Math.abs(tCutV5 - tCutV6) / (double) tN < 0.02
                && mean(allJaccard) >= 0.5;
        if (near) {
            LOG.info("   ✅ corr>0.9 + %<=cut sát + Jaccard>=0.5 => v5/v6 GẦN tương đương: backtest cũ vẫn tham");
            LOG.info("      khảo tốt, chuyển v6 ít rủi ro (vẫn nên backtest đối chứng 1 giai đoạn để chốt).");
        } else {
            LOG.info("   ⚠️ corr/Jaccard/%<=cut LỆCH => universe trade ĐỔI THẬT. TRƯỚC khi chuyển backtest/HPO");
            LOG.info("      sang v6: (1) chạy backtest đối chứng CÙNG giai đoạn v5 vs v6, (2) cân nhắc");
            LOG.info("      calibrate lại PREDICT_SYMBOL_RATE_MAX_THRESHOLD theo phân bố v6.");
        }
        LOG.info("   Nền kỳ vọng: model live (v6) phân bố thấp hơn model ma (v5) đôi chút (p50 ~0.50 vs ~0.55),");
        LOG.info("   %<=cut tương đương ~4-5%% => corr KHÔNG ~1 là bình thường; CẢNH GIÁC nhất là Jaccard top-K thấp.");
        LOG.info("   Coverage v6 thiếu (xem bảng đầu) = tháng cần requeue GenerateFundingPredictionsTool.");
    }

    // ================= HELPERS =================

    /** Mẫu phút ngẫu nhiên (làm tròn về phút) trong [start,end), dedup. */
    private long[] sampleMinutes(long start, long end, int count) {
        long spanMin = (end - start) / Utils.TIME_MINUTE;
        if (spanMin <= 0) return new long[0];
        int k = (int) Math.min(count, spanMin);
        LinkedHashSet<Long> picked = new LinkedHashSet<>();
        int guard = 0;
        while (picked.size() < k && guard++ < k * 20) {
            picked.add(start + (long) (rnd.nextDouble() * spanMin) * Utils.TIME_MINUTE);
        }
        long[] out = new long[picked.size()];
        int i = 0;
        for (long t : picked) out[i++] = t;
        return out;
    }

    private static Map<Integer, Float> toMap(long[] arr) {
        Map<Integer, Float> m = new HashMap<>(arr.length * 2);
        for (long e : arr) m.put((int) (e >> 32), Float.intBitsToFloat((int) e));
        return m;
    }

    /** Top-K symbolId có pred THẤP NHẤT (sát pre-filter sort tăng dần). */
    private static Set<Integer> topKLowest(long[] arr) {
        // sort theo pred (float ở 32 bit thấp) — decode rồi sort tăng dần, lấy K id thấp nhất
        Long[] boxed = new Long[arr.length];
        for (int i = 0; i < arr.length; i++) boxed[i] = arr[i];
        Arrays.sort(boxed, Comparator.comparingDouble(e -> Float.intBitsToFloat((int) (long) e)));
        Set<Integer> top = new HashSet<>();
        for (int i = 0; i < Math.min(TOP_K, boxed.length); i++) top.add((int) (boxed[i] >> 32));
        return top;
    }

    private static double jaccard(Set<Integer> a, Set<Integer> b) {
        if (a.isEmpty() && b.isEmpty()) return 1.0;
        Set<Integer> inter = new HashSet<>(a); inter.retainAll(b);
        Set<Integer> uni = new HashSet<>(a); uni.addAll(b);
        return uni.isEmpty() ? 0.0 : (double) inter.size() / uni.size();
    }

    /** Reservoir sampling (Algorithm R) để percentile/Spearman TỔNG mà RAM phẳng. */
    private void addReservoir(float v5, float v6) {
        reservoirSeen++;
        if (reservoir.size() < MAX_GLOBAL_PAIRS) {
            reservoir.add(new float[]{v5, v6});
        } else {
            long j = (long) (rnd.nextDouble() * reservoirSeen);
            if (j < MAX_GLOBAL_PAIRS) reservoir.set((int) j, new float[]{v5, v6});
        }
    }

    private static double pearson(double[] x, double[] y) {
        double sx = 0, sy = 0, sxx = 0, syy = 0, sxy = 0;
        int n = x.length;
        for (int i = 0; i < n; i++) { sx += x[i]; sy += y[i]; sxx += x[i] * x[i]; syy += y[i] * y[i]; sxy += x[i] * y[i]; }
        return pearson(sx, sy, sxx, syy, sxy, n);
    }

    private static double pearson(double sx, double sy, double sxx, double syy, double sxy, long n) {
        double cov = n * sxy - sx * sy;
        double dx = n * sxx - sx * sx, dy = n * syy - sy * sy;
        double den = Math.sqrt(dx * dy);
        return den == 0 ? Double.NaN : cov / den;
    }

    /** Hạng trung bình (xử lý ties) cho Spearman. */
    private static double[] ranks(double[] a) {
        int n = a.length;
        Integer[] idx = new Integer[n];
        for (int i = 0; i < n; i++) idx[i] = i;
        Arrays.sort(idx, Comparator.comparingDouble(i -> a[i]));
        double[] r = new double[n];
        int i = 0;
        while (i < n) {
            int j = i;
            while (j + 1 < n && a[idx[j + 1]] == a[idx[i]]) j++;
            double avg = (i + j) / 2.0 + 1.0;
            for (int k = i; k <= j; k++) r[idx[k]] = avg;
            i = j + 1;
        }
        return r;
    }

    private static double pct(double[] sorted, double p) {
        if (sorted.length == 0) return Double.NaN;
        int i = (int) Math.round(p / 100.0 * (sorted.length - 1));
        return sorted[Math.max(0, Math.min(sorted.length - 1, i))];
    }

    private static double mean(List<Double> v) {
        if (v.isEmpty()) return Double.NaN;
        double s = 0; for (double d : v) s += d; return s / v.size();
    }

    private static double[] toArr(List<Double> v) {
        double[] a = new double[v.size()];
        for (int i = 0; i < v.size(); i++) a[i] = v.get(i);
        return a;
    }

    private String monthLabel(long ms) { return new java.text.SimpleDateFormat("yyyyMM").format(new Date(ms)); }

    private long monthStartOf(String label) {
        try { return new java.text.SimpleDateFormat("yyyyMM").parse(label).getTime(); }
        catch (Exception e) { return 0L; }
    }

    private long monthEndOf(String label, long now) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(monthStartOf(label));
        c.add(Calendar.MONTH, 1);
        return Math.min(c.getTimeInMillis(), now);
    }

    private static String f4(double v) { return String.format(Locale.US, "%.4f", v); }
    private static String f3(double v) { return String.format(Locale.US, "%.3f", v); }
    private static String f2(double v) { return String.format(Locale.US, "%.2f", v); }
}
