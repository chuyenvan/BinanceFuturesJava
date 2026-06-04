package com.binance.chuyennd.ai_ml.validation.predict.market;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * KIỂM CHỨNG PREDICT MÔ HÌNH CŨ TRÊN OUT-OF-SAMPLE THẬT.
 *
 * Mô hình cũ predict tới khoảng 19/12/2025. Mọi timestamp >= CUTOFF (20/12/2025) là dữ liệu
 * mô hình CHƯA TỪNG train, và predict đã được sinh/chạy thật => tập kiểm trung thực nhất (không thể leak).
 *
 * Logic:
 *   1. Nạp toàn bộ predict cũ (basket-level, theo timestamp) từ Aerospike 226.
 *   2. REPLAY ticker tuần tự từ (CUTOFF - warmup) -> nay để nuôi HistoryManager (cho findPotentialLosers
 *      + indicator ấm). Phải replay, không được nhảy thẳng, nếu không basket/realized SAI.
 *   3. Mỗi phút có predict: dựng basket = findPotentialLosers(T) ĐÚNG như label lúc train,
 *      tính realized max-gain 15p (và realized max-drawdown 15p = rủi ro DCA trong cửa sổ vào).
 *   4. Ghép (predReturn15M, realized15M), de-overlap 15p, đo:
 *        - IC (Spearman) live thật.
 *        - LIFT tại các ngưỡng 1/2/3/6%: trong top-decile predict, % thực chạm ngưỡng vs base-rate.
 *        - Phân bố drawdown trước khi chạm (để biết DCA phải gánh sâu bao nhiêu ở các điểm model chọn).
 *
 * Chạy trên 226 (đọc predict tại chỗ + với tới ticker 242). KHÔNG sửa gì, chỉ đọc + tính.
 */
public class ValidateOldPredictVsRealized {

    private static final Logger LOG = LoggerFactory.getLogger(ValidateOldPredictVsRealized.class);

    private static final String CUTOFF_DATE = "20251220";   // mô hình cũ không thấy từ đây trở đi
    private static final int WARMUP_DAYS = 2;               // nuôi history trước cutoff
    private static final int HORIZON_MIN = 15;              // label nhìn 15 phút
    private static final long HORIZON_MS = HORIZON_MIN * 60_000L;
    private static final float[] THRESHOLDS = {0.01f, 0.02f, 0.03f, 0.06f};
    private static final double TOP_QUANTILE = 0.10;        // top 10% theo predict

    public static void main(String[] args) {
        try {
            new ValidateOldPredictVsRealized().run();
        } catch (Exception e) {
            LOG.error("Main error", e);
        }
    }

    public void run() throws Exception {
        long cutoff = Utils.sdfFile.parse(CUTOFF_DATE).getTime();
        long warmupStart = cutoff - WARMUP_DAYS * Utils.TIME_DAY;
        long endTime = System.currentTimeMillis();

        LOG.info("📥 Nạp predict cũ từ Aerospike 226...");
        TreeMap<Long, AiPredictionData> predictionMap =
                DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        LOG.info("✅ Tổng predict nạp được: {} | đo từ {} -> nay",
                predictionMap.size(), Utils.normalizeDateYYYYMMDD(cutoff));

        HistoryManager.getInstance().resetCache();

        List<float[]> rows = new ArrayList<>(); // {timestamp, pred15M, realized15M, realizedDD15M}
        long current = warmupStart;
        int days = 0;

        while (current <= endTime) {
            try {
                TreeMap<Long, Map<String, KlineObjectSimple>> today =
                        DataManagerAerospikeFloatSim.readDataFromAerospike1M(current);
                TreeMap<Long, Map<String, KlineObjectSimple>> tomorrow =
                        DataManagerAerospikeFloatSim.readDataFromAerospike1M(current + Utils.TIME_DAY);

                TreeMap<Long, Map<String, KlineObjectSimple>> lookup = new TreeMap<>();
                if (today != null) lookup.putAll(today);
                if (tomorrow != null) lookup.putAll(tomorrow);

                if (today != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : today.entrySet()) {
                        long ts = e.getKey();
                        Map<String, KlineObjectSimple> snapshot = e.getValue();

                        // NUÔI HISTORY MỖI PHÚT (kể cả warmup) — bắt buộc để basket/indicator ấm.
                        HistoryManager.getInstance().updateHistory(snapshot);

                        if (ts < cutoff) continue;                  // chỉ đo từ cutoff
                        AiPredictionData pred = predictionMap.get(ts);
                        if (pred == null) continue;                 // không có predict cho mốc này

                        List<String> basket = HistoryManager.getInstance().findPotentialLosers(ts);
                        if (basket == null || basket.isEmpty()) continue;

                        float realized = basketMaxGain(lookup, ts, HORIZON_MIN, basket);
                        float realizedDD = basketMaxDrawdown(lookup, ts, HORIZON_MIN, basket);

                        rows.add(new float[]{ts, pred.predReturn15M, realized, realizedDD});
                    }
                }
            } catch (Exception ex) {
                LOG.warn("⚠️ Lỗi ngày {}: {}", Utils.normalizeDateYYYYMMDD(current), ex.getMessage());
            }
            current += Utils.TIME_DAY;
            if (++days % 10 == 0) LOG.info("... đã xử lý {} ngày, thu {} điểm", days, rows.size());
        }

        LOG.info("✅ Thu {} điểm (predict, realized) thô.", rows.size());
        analyze(rows);
    }

    // ===================== ĐO LƯỜNG =====================
    private void analyze(List<float[]> rows) {
        if (rows.size() < 100) {
            LOG.warn("⚠️ Chỉ {} điểm — quá ít để kết luận.", rows.size());
            return;
        }
        // de-overlap 15p theo thời gian (basket-level)
        rows.sort(Comparator.comparingDouble(r -> r[0]));
        List<float[]> dov = new ArrayList<>();
        double last = Double.NEGATIVE_INFINITY;
        for (float[] r : rows) {
            if (r[0] - last >= HORIZON_MS) {
                dov.add(r);
                last = r[0];
            }
        }
        int n = dov.size();
        LOG.info("🧪 de-overlap {} -> {} điểm độc lập (cửa sổ {}p)", rows.size(), n, HORIZON_MIN);

        double[] pred = new double[n], real = new double[n], dd = new double[n];
        for (int i = 0; i < n; i++) {
            pred[i] = dov.get(i)[1];
            real[i] = dov.get(i)[2];
            dd[i] = dov.get(i)[3];
        }

        // --- IC live thật ---
        double ic = spearman(pred, real);
        double t = (Math.abs(ic) < 1) ? ic * Math.sqrt((n - 2) / (1 - ic * ic)) : Double.NaN;
        LOG.info("📊 IC live (predict cũ vs realized 15M) = {} | t = {} | n = {}",
                fmt(ic), fmt(t), n);

        // --- phân bố realized (đối chiếu trí nhớ: tụ ~1.6%, >2% dưới 10%) ---
        double[] sortedReal = real.clone();
        Arrays.sort(sortedReal);
        LOG.info("📈 Realized 15M: p10={} p50={} p90={} | %>1%={}% %>2%={}% %>3%={}% %>6%={}%",
                fmt(quant(sortedReal, 0.10)), fmt(quant(sortedReal, 0.50)), fmt(quant(sortedReal, 0.90)),
                pctGe(real, 0.01f), pctGe(real, 0.02f), pctGe(real, 0.03f), pctGe(real, 0.06f));

        // --- LIFT: top-decile theo predict, % chạm ngưỡng vs base-rate ---
        Integer[] idx = new Integer[n];
        for (int i = 0; i < n; i++) idx[i] = i;
        Arrays.sort(idx, (a, b) -> Double.compare(pred[b], pred[a])); // predict giảm dần
        int topK = Math.max(30, (int) (n * TOP_QUANTILE));
        LOG.info("🎯 LIFT — top {}% predict (n_top={}) vs toàn bộ:", (int) (TOP_QUANTILE * 100), topK);
        for (float thr : THRESHOLDS) {
            double base = pctGeRaw(real, thr);
            int hit = 0;
            for (int k = 0; k < topK; k++) if (real[idx[k]] >= thr) hit++;
            double topRate = (double) hit / topK;
            double lift = base > 0 ? topRate / base : Double.NaN;
            LOG.info("   ngưỡng +{}%: base={}% | top-decile={}% | LIFT=x{}",
                    (int) (thr * 100), fmtPct(base), fmtPct(topRate), fmt(lift));
        }

        // --- RỦI RO DCA: drawdown sâu nhất trong 15p ở các điểm model chọn (top-decile) ---
        double[] ddTop = new double[topK];
        for (int k = 0; k < topK; k++) ddTop[k] = dd[idx[k]];
        Arrays.sort(ddTop);
        LOG.info("📉 Drawdown 15p tại top-decile (model bảo VÀO): p50={} p90={} worst={}",
                fmt(quant(ddTop, 0.50)), fmt(quant(ddTop, 0.90)), fmt(ddTop[0]));

        // --- PHÁN QUYẾT ---
        LOG.info("================ PHÁN QUYẾT ================");
        if (Math.abs(t) < 2) {
            LOG.info("🔴 IC không có ý nghĩa thống kê (|t|<2) => predict cũ KHÔNG có edge live. "
                    + "R2 đẹp lúc xưa là ảo giác do label tụ hẹp.");
        } else if (ic > 0) {
            LOG.info("🟢 IC dương có ý nghĩa => predict cũ CÓ tương quan thật với realized. "
                    + "Đọc LIFT ở ngưỡng bạn cần để biết có dùng được không.");
        } else {
            LOG.info("🔴 IC ÂM có ý nghĩa => predict cũ dự báo NGƯỢC. Tệ hơn đoán mù.");
        }
        LOG.info("Lưu ý: nếu LIFT ở ngưỡng +3%/+6% (vùng bạn cần để trailing thoát) ~ x1.0 "
                + "=> model chỉ giỏi vùng <2%% vô dụng. Và drawdown top-decile sâu = DCA phải gánh nặng.");
    }

    // ===================== REALIZED (khớp RunFullDataCollection) =====================
    private float basketMaxGain(TreeMap<Long, Map<String, KlineObjectSimple>> data, long ts,
                                int minutes, List<String> basket) {
        long end = ts + minutes * 60_000L;
        Map<String, KlineObjectSimple> cur = data.get(ts);
        if (cur == null) return 0f;
        Map<String, Float> entry = new HashMap<>();
        for (String s : basket) if (cur.containsKey(s)) entry.put(s, cur.get(s).priceClose);
        NavigableMap<Long, Map<String, KlineObjectSimple>> fut = data.subMap(ts, false, end, true);
        Map<String, Float> maxRet = new HashMap<>();
        for (String s : basket) maxRet.put(s, -999f);
        for (Map<String, KlineObjectSimple> m : fut.values()) {
            for (String s : basket) {
                if (m.containsKey(s) && entry.containsKey(s)) {
                    float e = entry.get(s);
                    if (e > 0) {
                        float r = (m.get(s).maxPrice - e) / e;
                        if (r > maxRet.get(s)) maxRet.put(s, r);
                    }
                }
            }
        }
        float sum = 0; int c = 0;
        for (String s : basket) { float r = maxRet.get(s); if (r != -999f) { sum += r; c++; } }
        return c > 0 ? sum / c : 0f;
    }

    private float basketMaxDrawdown(TreeMap<Long, Map<String, KlineObjectSimple>> data, long ts,
                                    int minutes, List<String> basket) {
        long end = ts + minutes * 60_000L;
        NavigableMap<Long, Map<String, KlineObjectSimple>> range = data.subMap(ts, false, end, true);
        Map<String, Float> entry = new HashMap<>();
        Map<String, KlineObjectSimple> cur = data.get(ts);
        if (cur == null) return 0f;
        for (String s : basket) if (cur.containsKey(s) && cur.get(s).priceClose > 1e-7) entry.put(s, cur.get(s).priceClose);
        if (entry.isEmpty()) return 0f;
        float worst = 0f;
        for (Map<String, KlineObjectSimple> m : range.values()) {
            float sum = 0; int c = 0;
            for (String s : entry.keySet()) {
                if (m.containsKey(s)) {
                    float low = m.get(s).minPrice, e = entry.get(s);
                    if (low > 0 && e > 0) {
                        float d = (low - e) / e;
                        if (d < -1) d = -1f;
                        sum += d; c++;
                    }
                }
            }
            if (c > 0) { float avg = sum / c; if (avg < worst) worst = avg; }
        }
        return worst;
    }

    // ===================== THỐNG KÊ =====================
    private double spearman(double[] a, double[] b) {
        double[] ra = rank(a), rb = rank(b);
        return pearson(ra, rb);
    }

    private double[] rank(double[] x) {
        int n = x.length;
        Integer[] idx = new Integer[n];
        for (int i = 0; i < n; i++) idx[i] = i;
        Arrays.sort(idx, Comparator.comparingDouble(i -> x[i]));
        double[] r = new double[n];
        int i = 0;
        while (i < n) {
            int j = i;
            while (j + 1 < n && x[idx[j + 1]] == x[idx[i]]) j++;
            double avg = (i + j) / 2.0 + 1;
            for (int k = i; k <= j; k++) r[idx[k]] = avg;
            i = j + 1;
        }
        return r;
    }

    private double pearson(double[] a, double[] b) {
        int n = a.length;
        double ma = 0, mb = 0;
        for (int i = 0; i < n; i++) { ma += a[i]; mb += b[i]; }
        ma /= n; mb /= n;
        double cov = 0, va = 0, vb = 0;
        for (int i = 0; i < n; i++) {
            double da = a[i] - ma, db = b[i] - mb;
            cov += da * db; va += da * da; vb += db * db;
        }
        return (va > 0 && vb > 0) ? cov / Math.sqrt(va * vb) : 0;
    }

    private double quant(double[] sorted, double q) {
        if (sorted.length == 0) return 0;
        int i = (int) Math.round(q * (sorted.length - 1));
        return sorted[Math.max(0, Math.min(sorted.length - 1, i))];
    }

    private String pctGe(double[] x, float thr) { return fmtPct(pctGeRaw(x, thr)); }

    private double pctGeRaw(double[] x, float thr) {
        int c = 0; for (double v : x) if (v >= thr) c++;
        return (double) c / x.length;
    }

    private String fmt(double v) { return String.format(Locale.US, "%.4f", v); }
    private String fmtPct(double v) { return String.format(Locale.US, "%.1f", v * 100); }
}