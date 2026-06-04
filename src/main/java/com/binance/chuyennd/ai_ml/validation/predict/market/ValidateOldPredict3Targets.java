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
 * VALIDATE PREDICT MÔ HÌNH CŨ TRÊN OOS THẬT — CẢ 3 TARGET.
 *
 * Predict cũ (set ai_pred_market_full_basket_v2 trên 226) đã có sẵn 3 trường:
 *   predReturn15M, predReturn24H, predRisk4H (drawdown 4h, số ÂM).
 * Mọi timestamp >= CUTOFF (20/12/2025) là dữ liệu mô hình cũ CHƯA train => OOS thật, không leak.
 *
 * Đo cho từng target (realized tính khác nhau):
 *   - 15M : max-gain basket 15p   -> IC + LIFT @1/2/3/6% (cơ hội vào lệnh).
 *   - 24H : max-gain basket 24h    -> IC (cảnh báo n nhỏ).
 *   - DD4H: max-drawdown basket 4h -> IC + IC theo regime + PRECISION/RECALL của PHANH tại -9.2%.
 *
 * PHANH = filter reject khi predRisk4H <= HARD_RISK_LIMIT_4H (-0.092). Đây là lá chắn chính
 * chống cú sập của hệ KHÔNG hard-stop. Recall@down thấp = phanh để lọt cú sập = rủi ro cháy.
 *
 * Regime tại lúc quyết định = BTC return 24h qua (lấy từ HistoryManager, KHÔNG nhìn tương lai).
 * Chạy trên 226 (đọc predict tại chỗ + với tới ticker 242). Chỉ đọc, không sửa.
 */
public class ValidateOldPredict3Targets {

    private static final Logger LOG = LoggerFactory.getLogger(ValidateOldPredict3Targets.class);

    private static final String CUTOFF_DATE = "20251220";
    private static final int WARMUP_DAYS = 2;
    private static final float DANGER_THRESHOLD = -0.092f;       // = Configs.HARD_RISK_LIMIT_4H
    private static final float[] GAIN_THRESHOLDS = {0.01f, 0.02f, 0.03f, 0.06f};
    private static final double TOP_QUANTILE = 0.10;

    // chỉ số cột trong row[]
    private static final int TS = 0, P15 = 1, P24 = 2, PDD = 3, R15 = 4, R24 = 5, RDD = 6, REG = 7;
    // regime code
    private static final float UP = 0, DOWN = 1, SIDE = 2;

    public static void main(String[] args) {
        try {
            new ValidateOldPredict3Targets().run();
        } catch (Exception e) {
            LOG.error("Main error", e);
        }
    }

    public void run() throws Exception {
        long cutoff = Utils.sdfFile.parse(CUTOFF_DATE).getTime();
        long warmupStart = cutoff - WARMUP_DAYS * Utils.TIME_DAY;
        long endTime = System.currentTimeMillis();

        LOG.info("📥 Nạp predict cũ (3 target) từ Aerospike 226...");
        TreeMap<Long, AiPredictionData> predictionMap =
                DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        LOG.info("✅ Tổng predict: {} | đo từ {} -> nay", predictionMap.size(), Utils.normalizeDateYYYYMMDD(cutoff));

        HistoryManager.getInstance().resetCache();
        List<float[]> rows = new ArrayList<>();
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
                        HistoryManager.getInstance().updateHistory(e.getValue());   // nuôi history mỗi phút

                        if (ts < cutoff) continue;
                        AiPredictionData pred = predictionMap.get(ts);
                        if (pred == null) continue;

                        List<String> basket = HistoryManager.getInstance().findPotentialLosers(ts);
                        if (basket == null || basket.isEmpty()) continue;

                        float r15 = basketMaxGain(lookup, ts, 15, basket);
                        float r24 = basketMaxGain(lookup, ts, 1440, basket);
                        float rdd = basketMaxDrawdown(lookup, ts, 240, basket);

                        // regime tại lúc quyết định: BTC 24h qua (không nhìn tương lai)
                        float btc24 = HistoryManager.getInstance().getReturn("BTCUSDT", 1440);
                        float reg = btc24 > 0.02f ? UP : (btc24 < -0.02f ? DOWN : SIDE);

                        rows.add(new float[]{ts, pred.predReturn15M, 0f, pred.predRisk4H,
                                r15, r24, rdd, reg});  // cột pred24 = 0 (predReturn24H đã bỏ; giữ layout tool)
                    }
                }
            } catch (Exception ex) {
                LOG.warn("⚠️ Lỗi ngày {}: {}", Utils.normalizeDateYYYYMMDD(current), ex.getMessage());
            }
            current += Utils.TIME_DAY;
            if (++days % 20 == 0) LOG.info("... {} ngày, {} điểm", days, rows.size());
        }

        LOG.info("✅ Thu {} điểm thô.", rows.size());
        rows.sort(Comparator.comparingDouble(r -> r[TS]));

        analyzeGain("15M", rows, P15, R15, 15);
        analyzeGain("24H", rows, P24, R24, 1440);
        analyzeDrawdown(rows);
    }

    // ===================== 15M / 24H: max-gain + IC + LIFT =====================
    private void analyzeGain(String name, List<float[]> rows, int predCol, int realCol, int horizonMin) {
        LOG.info("\n############ TARGET {}: max-gain {}p ############", name, horizonMin);
        List<float[]> dov = deoverlap(rows, horizonMin);
        int n = dov.size();
        LOG.info("🧪 de-overlap -> {} điểm độc lập", n);
        if (n < 100) { LOG.warn("⚠️ n quá nhỏ -> kết luận YẾU."); }
        if (n < 10) return;

        double[] pred = col(dov, predCol), real = col(dov, realCol);
        double ic = spearman(pred, real);
        double t = tstat(ic, n);
        LOG.info("📊 IC live ({} vs realized) = %s | t = %s | n = %d".replace("%s", "{}").replace("%d", "{}"),
                fmt(ic), fmt(t), n);

        double[] sr = real.clone(); Arrays.sort(sr);
        LOG.info("📈 Realized {}: p10={} p50={} p90={} | %>1%={} %>2%={} %>3%={} %>6%={}",
                name, fmt(quant(sr, .10)), fmt(quant(sr, .50)), fmt(quant(sr, .90)),
                fmtPct(pctGe(real, .01f)), fmtPct(pctGe(real, .02f)), fmtPct(pctGe(real, .03f)), fmtPct(pctGe(real, .06f)));

        Integer[] idx = sortedIdxDesc(pred);
        int topK = Math.max(30, (int) (n * TOP_QUANTILE));
        LOG.info("🎯 LIFT top {}% (n_top={}):", (int) (TOP_QUANTILE * 100), topK);
        for (float thr : GAIN_THRESHOLDS) {
            double base = pctGe(real, thr);
            int hit = 0; for (int k = 0; k < topK; k++) if (real[idx[k]] >= thr) hit++;
            double topRate = (double) hit / topK;
            LOG.info("   +{}%: base={} top={} LIFT=x{}", (int) (thr * 100),
                    fmtPct(base), fmtPct(topRate), fmt(base > 0 ? topRate / base : Double.NaN));
        }
        if (Math.abs(t) < 2) LOG.info("🔴 IC không ý nghĩa (|t|<2).");
        else LOG.info("🟢 IC dương ý nghĩa.");
    }

    // ===================== DD4H: IC + regime + PHANH precision/recall =====================
    private void analyzeDrawdown(List<float[]> rows) {
        LOG.info("\n############ TARGET DD4H: max-drawdown 4h + PHANH @{} ############", DANGER_THRESHOLD);
        List<float[]> dov = deoverlap(rows, 240);
        int n = dov.size();
        LOG.info("🧪 de-overlap -> {} điểm độc lập", n);
        if (n < 100) { LOG.warn("⚠️ n nhỏ -> kết luận yếu."); }
        if (n < 10) return;

        double[] pred = col(dov, PDD), real = col(dov, RDD);
        double ic = spearman(pred, real);
        LOG.info("📊 IC(predRisk4H vs realized DD) = {} | t = {} (dương = dự báo đúng độ sâu)",
                fmt(ic), fmt(tstat(ic, n)));

        // IC theo regime
        for (float rg : new float[]{UP, DOWN, SIDE}) {
            List<Integer> sel = new ArrayList<>();
            for (int i = 0; i < n; i++) if (dov.get(i)[REG] == rg) sel.add(i);
            if (sel.size() >= 30) {
                double[] p = pick(pred, sel), r = pick(real, sel);
                LOG.info("   IC[{}] = {} (n={})", rgName(rg), fmt(spearman(p, r)), sel.size());
            }
        }

        // PHANH: precision/recall tại -9.2%
        LOG.info("🛑 PHANH tại {} (model báo sụt sâu hơn => REJECT):", DANGER_THRESHOLD);
        brakeStats("TỔNG", pred, real, null, dov);
        for (float rg : new float[]{UP, DOWN, SIDE}) brakeStats(rgName(rg), pred, real, rg, dov);

        LOG.info("📌 Đọc: RECALL@down THẤP = phanh để LỌT cú sập lúc thị trường xuống = rủi ro cháy. "
                + "PRECISION thấp = phanh chặn NHẦM cơ hội. Cần cân bằng, nhưng recall@down là sống còn.");
    }

    private void brakeStats(String tag, double[] pred, double[] real, Float regime, List<float[]> dov) {
        int predDanger = 0, actualDanger = 0, both = 0, total = 0;
        for (int i = 0; i < pred.length; i++) {
            if (regime != null && dov.get(i)[REG] != regime) continue;
            total++;
            boolean pd = pred[i] <= DANGER_THRESHOLD;     // model báo nguy
            boolean ad = real[i] <= DANGER_THRESHOLD;     // thực tế sụt > 9.2%
            if (pd) predDanger++;
            if (ad) actualDanger++;
            if (pd && ad) both++;
        }
        if (total < 30) return;
        double precision = predDanger > 0 ? (double) both / predDanger : Double.NaN;  // chặn có đúng
        double recall = actualDanger > 0 ? (double) both / actualDanger : Double.NaN; // bắt được bao nhiêu cú sập
        LOG.info("   [{}] n={} | thực-tế-nguy={}% | model-reject={}% | PRECISION={} RECALL={}",
                tag, total, fmtPct((double) actualDanger / total), fmtPct((double) predDanger / total),
                fmt(precision), fmt(recall));
    }

    // ===================== REALIZED =====================
    private float basketMaxGain(TreeMap<Long, Map<String, KlineObjectSimple>> data, long ts, int minutes, List<String> basket) {
        long end = ts + minutes * 60_000L;
        Map<String, KlineObjectSimple> cur = data.get(ts);
        if (cur == null) return 0f;
        Map<String, Float> entry = new HashMap<>();
        for (String s : basket) if (cur.containsKey(s)) entry.put(s, cur.get(s).priceClose);
        NavigableMap<Long, Map<String, KlineObjectSimple>> fut = data.subMap(ts, false, end, true);
        Map<String, Float> maxRet = new HashMap<>();
        for (String s : basket) maxRet.put(s, -999f);
        for (Map<String, KlineObjectSimple> m : fut.values())
            for (String s : basket)
                if (m.containsKey(s) && entry.containsKey(s)) {
                    float e = entry.get(s);
                    if (e > 0) { float r = (m.get(s).maxPrice - e) / e; if (r > maxRet.get(s)) maxRet.put(s, r); }
                }
        float sum = 0; int c = 0;
        for (String s : basket) { float r = maxRet.get(s); if (r != -999f) { sum += r; c++; } }
        return c > 0 ? sum / c : 0f;
    }

    private float basketMaxDrawdown(TreeMap<Long, Map<String, KlineObjectSimple>> data, long ts, int minutes, List<String> basket) {
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
            for (String s : entry.keySet())
                if (m.containsKey(s)) {
                    float low = m.get(s).minPrice, e = entry.get(s);
                    if (low > 0 && e > 0) { float d = (low - e) / e; if (d < -1) d = -1f; sum += d; c++; }
                }
            if (c > 0) { float avg = sum / c; if (avg < worst) worst = avg; }
        }
        return worst;
    }

    // ===================== TIỆN ÍCH =====================
    private List<float[]> deoverlap(List<float[]> rows, int horizonMin) {
        long h = horizonMin * 60_000L;
        List<float[]> out = new ArrayList<>();
        double last = Double.NEGATIVE_INFINITY;
        for (float[] r : rows) if (r[TS] - last >= h) { out.add(r); last = r[TS]; }
        return out;
    }

    private double[] col(List<float[]> rows, int c) {
        double[] a = new double[rows.size()];
        for (int i = 0; i < a.length; i++) a[i] = rows.get(i)[c];
        return a;
    }

    private double[] pick(double[] x, List<Integer> idx) {
        double[] a = new double[idx.size()];
        for (int i = 0; i < a.length; i++) a[i] = x[idx.get(i)];
        return a;
    }

    private Integer[] sortedIdxDesc(double[] x) {
        Integer[] idx = new Integer[x.length];
        for (int i = 0; i < x.length; i++) idx[i] = i;
        Arrays.sort(idx, (a, b) -> Double.compare(x[b], x[a]));
        return idx;
    }

    private double tstat(double ic, int n) {
        return (Math.abs(ic) < 1) ? ic * Math.sqrt((n - 2) / (1 - ic * ic)) : Double.NaN;
    }

    private double spearman(double[] a, double[] b) { return pearson(rank(a), rank(b)); }

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
        int n = a.length; double ma = 0, mb = 0;
        for (int i = 0; i < n; i++) { ma += a[i]; mb += b[i]; }
        ma /= n; mb /= n;
        double cov = 0, va = 0, vb = 0;
        for (int i = 0; i < n; i++) { double da = a[i] - ma, db = b[i] - mb; cov += da * db; va += da * da; vb += db * db; }
        return (va > 0 && vb > 0) ? cov / Math.sqrt(va * vb) : 0;
    }

    private double quant(double[] sorted, double q) {
        if (sorted.length == 0) return 0;
        int i = (int) Math.round(q * (sorted.length - 1));
        return sorted[Math.max(0, Math.min(sorted.length - 1, i))];
    }

    private double pctGe(double[] x, float thr) { int c = 0; for (double v : x) if (v >= thr) c++; return (double) c / x.length; }
    private String rgName(float r) { return r == UP ? "up" : r == DOWN ? "down" : "side"; }
    private String fmt(double v) { return String.format(Locale.US, "%.4f", v); }
    private String fmtPct(double v) { return String.format(Locale.US, "%.1f%%", v * 100); }
}