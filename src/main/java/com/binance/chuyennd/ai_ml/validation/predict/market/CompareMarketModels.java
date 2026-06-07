package com.binance.chuyennd.ai_ml.validation.predict.market;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.entry.OnnxInferenceManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * SO SÁNH HEAD-TO-HEAD 2 BỘ MODEL MARKET (ONNX 2025 vs 2026) — black-box, không cần code train.
 *
 * NGUYÊN TẮC CÔNG BẰNG:
 *  - FAIR_START = 20260526: model mới train tới 20260525, label 15M chỉ nhìn 15 phút
 *    => từ 20260526 CẢ HAI model đều OOS sạch (label 4H cũng sạch vì purge 1 ngày > 4h).
 *  - CÙNG MỘT MarketFeatures mỗi phút cho cả hai brain (cùng extractor, cùng history) —
 *    extractFeaturesV3Full nằm TRONG OnnxInferenceManager nên feature parity tự đảm bảo.
 *  - Realized COPY NGUYÊN VĂN từ ValidateOldPredictVsRealized (đã chạy ra IC 0.5175):
 *    basket = HistoryManager.findPotentialLosers(ts); basketMaxGain 15p; basketMaxDrawdown 4h.
 *  - Replay nuôi history mỗi phút (mirror RunGeneratePredictions: updateHistory + getTopCoin,
 *    warmup 48h). KHÔNG nhảy thẳng — nhảy là basket/indicator sai.
 *  - De-overlap theo thời gian, ONLINE: 15p cho target 15M, 240p cho dd4h — chỉ tính realized
 *    cho mẫu sống sót (bài học chậm ~1000x).
 *
 * ĐẦU RA:
 *  (0) sanity: chặn output suy biến (OnnxInferenceManager.predictAll NUỐT lỗi trả (0,0) —
 *      feature-mismatch sẽ thành toàn 0 âm thầm nếu không chặn).
 *  (1) IC(pred15M, realized15M) từng model + IC(predNew−predOld, realized) + corr(old,new).
 *  (2) LIFT top-decile tại +1%/+2% từng model — model nào chọn điểm vào tốt hơn ở vùng dùng thật.
 *  (3) Phân bố pred15M từng model (nếu lệch nhau => deploy phải xem lại MIN_MOMENTUM_15M).
 *  (4) dd4h: IC(predRisk4H, realizedDD4H) từng model (phụ — dd4h vốn chỉ là volatility proxy).
 *
 * ⚠️ Cửa sổ sạch ~10 ngày => n(15M)~1000 tạm được, n(4h)~60 RẤT yếu. Chạy lại định kỳ.
 * Chạy 226 (read-only) hoặc Kaggle. KHÔNG ghi gì.
 */
public class CompareMarketModels {

    private static final Logger LOG = LoggerFactory.getLogger(CompareMarketModels.class);

    // ⚙️ CHỈNH đường dẫn theo máy chạy (tên file model hai thư mục GIỐNG HỆT nhau => chỉ cần trỏ dir)
    private static final String MODEL_DIR_OLD = "../kaggle/kaggle_model/model_2025/ai_models_reg_v3";
    private static final String MODEL_DIR_NEW = "../kaggle/kaggle_model/model_2026/ai_models_v3";

    // trainEnd model mới = 20260525; label 15M/4H => 20260526 sạch cho cả hai
    private static final String FAIR_START_DATE = "20260526";
    private static final int WARMUP_HOURS = 48;              // mirror RunGeneratePredictions

    private static final long H15 = 15 * 60_000L;
    private static final long H240 = 240 * 60_000L;
    private static final float[] THRESHOLDS = {0.01f, 0.02f};
    private static final double TOP_QUANTILE = 0.10;
    private static final int SANITY_N = 200;

    public static void main(String[] args) {
        try { new CompareMarketModels().run(); }
        catch (Exception e) { LOG.error("CompareMarketModels error", e); }
    }

    public void run() throws Exception {
        long fairStart = Utils.sdfFile.parse(FAIR_START_DATE).getTime();
        long warmupStart = fairStart - WARMUP_HOURS * Utils.TIME_HOUR;
        long evalEnd = System.currentTimeMillis() - H240;    // cần đủ 4h tương lai cho realizedDD
        if (evalEnd <= fairStart) {
            LOG.error("⛔ Cửa sổ sạch chưa đủ: evalEnd <= fairStart ({}).", FAIR_START_DATE);
            return;
        }
        LOG.info("⚖️ SO SÁNH MARKET OLD vs NEW | fair window: {} -> {}",
                FAIR_START_DATE, Utils.normalizeDateYYYYMMDDHHmm(evalEnd));

        LOG.info("📥 Nạp market rate data...");
        TreeMap<Long, MarketDataObject> time2Rate = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();

        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();

        List<float[]> rows15 = new ArrayList<>();   // {pOld15, pNew15, realized15}
        List<float[]> rows4h = new ArrayList<>();   // {riskOld, riskNew, realizedDD4h}
        List<float[]> sanity = new ArrayList<>();   // {pOld15, pNew15}
        double cN = 0, cSx = 0, cSy = 0, cSxx = 0, cSyy = 0, cSxy = 0;  // streaming corr pred15 old vs new
        long last15 = 0L, last4h = 0L;

        try (OnnxInferenceManager brainOld = new OnnxInferenceManager(MODEL_DIR_OLD);
             OnnxInferenceManager brainNew = new OnnxInferenceManager(MODEL_DIR_NEW)) {

            ComprehensiveMarketFeatureExtractor extractor = new ComprehensiveMarketFeatureExtractor();

            long day = Utils.getDate(warmupStart);
            long lastDay = Utils.getDate(System.currentTimeMillis());
            int dayCount = 0;

            while (day <= lastDay) {
                try {
                    TreeMap<Long, Map<String, KlineObjectSimple>> today =
                            DataManagerAerospikeFloatSim.readDataFromAerospike1M(day);
                    TreeMap<Long, Map<String, KlineObjectSimple>> tomorrow =
                            DataManagerAerospikeFloatSim.readDataFromAerospike1M(day + Utils.TIME_DAY);
                    TreeMap<Long, Map<String, KlineObjectSimple>> lookup = new TreeMap<>();
                    if (today != null) lookup.putAll(today);
                    if (tomorrow != null) lookup.putAll(tomorrow);

                    if (today != null) {
                        for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : today.entrySet()) {
                            long ts = e.getKey();
                            Map<String, KlineObjectSimple> snap = e.getValue();

                            // nuôi history mỗi phút (kể cả warmup) — mirror RunGeneratePredictions
                            HistoryManager.getInstance().updateHistory(snap);
                            CoinRankManager.getInstance().getTopCoin(ts);

                            if (ts < fairStart || ts > evalEnd) continue;

                            MarketFeatures f = extractor.extractAllFeatures(ts, snap, time2Rate.get(ts));
                            if (f == null) continue;

                            // CÙNG MarketFeatures -> cả hai brain (mỗi brain tự extract V3Full bên trong)
                            OnnxInferenceManager.PredictionResult rOld = brainOld.predictAll(f);
                            OnnxInferenceManager.PredictionResult rNew = brainNew.predictAll(f);

                            if (sanity.size() < SANITY_N) sanity.add(new float[]{rOld.return15M, rNew.return15M});
                            cN++; cSx += rOld.return15M; cSy += rNew.return15M;
                            cSxx += rOld.return15M * rOld.return15M; cSyy += rNew.return15M * rNew.return15M;
                            cSxy += rOld.return15M * rNew.return15M;

                            // de-overlap 15p (basket-level, theo thời gian) -> realized 15M
                            if (ts - last15 >= H15) {
                                List<String> basket = HistoryManager.getInstance().findPotentialLosers(ts);
                                if (basket != null && !basket.isEmpty()) {
                                    float realized = basketMaxGain(lookup, ts, 15, basket);
                                    rows15.add(new float[]{rOld.return15M, rNew.return15M, realized});
                                    last15 = ts;
                                }
                            }
                            // de-overlap 240p -> realized DD 4h (phụ)
                            if (ts - last4h >= H240) {
                                List<String> basket = HistoryManager.getInstance().findPotentialLosers(ts);
                                if (basket != null && !basket.isEmpty()) {
                                    float realizedDD = basketMaxDrawdown(lookup, ts, 240, basket);
                                    rows4h.add(new float[]{rOld.riskDrawdown4H, rNew.riskDrawdown4H, realizedDD});
                                    last4h = ts;
                                }
                            }
                        }
                    }
                } catch (Exception ex) {
                    LOG.warn("⚠️ Lỗi ngày {}: {}", Utils.normalizeDateYYYYMMDD(day), ex.getMessage());
                }
                day += Utils.TIME_DAY;
                if (++dayCount % 2 == 0) LOG.info("... {} ngày | n15={} n4h={}", dayCount, rows15.size(), rows4h.size());
            }
        }

        if (!sanityOk(sanity)) return;
        analyze(rows15, rows4h, cN, cSx, cSy, cSxx, cSyy, cSxy);
    }

    /** predictAll nuốt lỗi trả (0,0) — output hằng số = feature-mismatch âm thầm, phải chặn. */
    private boolean sanityOk(List<float[]> sanity) {
        if (sanity.size() < 20) { LOG.error("⛔ Quá ít mẫu sanity ({}).", sanity.size()); return false; }
        double sdOld = sd(sanity, 0), sdNew = sd(sanity, 1);
        LOG.info("🔎 SANITY: sd(pred15M) old={} new={} trên {} mẫu đầu", f4(sdOld), f4(sdNew), sanity.size());
        if (sdOld < 1e-7 || sdNew < 1e-7) {
            LOG.error("⛔ Model output HẰNG SỐ => predictAll đang nuốt lỗi (khả năng input-shape mismatch). DỪNG.");
            return false;
        }
        return true;
    }

    private double sd(List<float[]> s, int idx) {
        double m = 0; for (float[] v : s) m += v[idx]; m /= s.size();
        double var = 0; for (float[] v : s) var += (v[idx] - m) * (v[idx] - m);
        return Math.sqrt(var / s.size());
    }

    // ====================== ĐO ======================
    private void analyze(List<float[]> rows15, List<float[]> rows4h,
                         double cN, double cSx, double cSy, double cSxx, double cSyy, double cSxy) {
        int n = rows15.size();
        LOG.info("\n================ COMPARE MARKET OLD vs NEW — n15(de-overlap)={} ================", n);
        if (n < 500) LOG.warn("⚠️ n15={} nhỏ => kết quả SƠ BỘ. Chạy lại khi cửa sổ sạch dài thêm.", n);
        if (n < 30) { LOG.error("⛔ Quá ít điểm."); return; }

        double[] pOld = new double[n], pNew = new double[n], real = new double[n], diff = new double[n];
        for (int i = 0; i < n; i++) {
            pOld[i] = rows15.get(i)[0]; pNew[i] = rows15.get(i)[1];
            real[i] = rows15.get(i)[2]; diff[i] = pNew[i] - pOld[i];
        }

        // (1) IC + corr + IC(diff)
        double icOld = spearman(pOld, real), icNew = spearman(pNew, real), icDiff = spearman(diff, real);
        double pearsonFull = (cN > 1) ? (cN * cSxy - cSx * cSy) /
                (Math.sqrt(cN * cSxx - cSx * cSx) * Math.sqrt(cN * cSyy - cSy * cSy)) : Double.NaN;
        LOG.info("(1) IC(pred15M, realized15M): OLD={} (t={}) | NEW={} (t={})",
                f4(icOld), f2(tStat(icOld, n)), f4(icNew), f2(tStat(icNew, n)));
        LOG.info("    corr(predOld, predNew): Pearson full({} cặp)={} | Spearman(dov)={}",
                (long) cN, f4(pearsonFull), f4(spearman(pOld, pNew)));
        LOG.info("    IC(predNew - predOld, realized) = {} (t={})  [DƯƠNG = phần khác mang tín hiệu thêm]",
                f4(icDiff), f2(tStat(icDiff, n)));

        // (2) LIFT top-decile từng model
        int topK = Math.max(30, (int) (n * TOP_QUANTILE));
        for (float thr : THRESHOLDS) {
            double base = pctGe(real, thr);
            double liftOld = topLift(pOld, real, topK, thr, base);
            double liftNew = topLift(pNew, real, topK, thr, base);
            LOG.info("(2) LIFT@+{}% (top-decile, n_top={}): base={}% | OLD=x{} | NEW=x{}",
                    (int) (thr * 100), topK, f1(base * 100), f2(liftOld), f2(liftNew));
        }

        // (3) phân bố pred15M từng model — lệch nhau là deploy phải xem lại MIN_MOMENTUM_15M
        logDist("OLD", pOld);
        logDist("NEW", pNew);

        // (4) dd4h (phụ)
        int n4 = rows4h.size();
        if (n4 >= 30) {
            double[] ro = new double[n4], rn = new double[n4], rd = new double[n4];
            for (int i = 0; i < n4; i++) { ro[i] = rows4h.get(i)[0]; rn[i] = rows4h.get(i)[1]; rd[i] = rows4h.get(i)[2]; }
            LOG.info("(4) dd4h (n={} — {}): IC OLD={} | NEW={} | corr(old,new)={}",
                    n4, n4 < 200 ? "RẤT YẾU, tham khảo" : "tạm",
                    f4(spearman(ro, rd)), f4(spearman(rn, rd)), f4(spearman(ro, rn)));
        } else {
            LOG.info("(4) dd4h: n={} quá ít, bỏ qua.", n4);
        }

        LOG.info("\n📌 CÁCH ĐỌC: NEW đáng thay OLD khi IC + LIFT@1% cao hơn RÕ và IC(diff) dương."
                + " corr~0.98+ hoặc số ngang nhau => GIỮ OLD (model cũ đã validate OOS đàng hoàng, đổi = rủi ro vận hành)."
                + " Phân bố pred15M lệch => deploy phải calibrate lại MIN_MOMENTUM_15M/ngưỡng động."
                + " n nhỏ => sơ bộ, chạy lại hàng tuần.");
    }

    private double topLift(double[] pred, double[] real, int topK, float thr, double base) {
        Integer[] idx = new Integer[pred.length];
        for (int i = 0; i < pred.length; i++) idx[i] = i;
        Arrays.sort(idx, (a, b) -> Double.compare(pred[b], pred[a]));
        int hit = 0;
        for (int k = 0; k < topK; k++) if (real[idx[k]] >= thr) hit++;
        double topRate = (double) hit / topK;
        return base > 0 ? topRate / base : Double.NaN;
    }

    private void logDist(String name, double[] p) {
        double[] s = p.clone(); Arrays.sort(s);
        LOG.info("(3) [{}] pred15M: p10={} p50={} p90={}", name, f4(q(s, 0.10)), f4(q(s, 0.50)), f4(q(s, 0.90)));
    }

    // ============ REALIZED — COPY NGUYÊN VĂN ValidateOldPredictVsRealized (đừng sửa) ============
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
    private static double tStat(double ic, int n) {
        return (Math.abs(ic) < 1 && n > 2) ? ic * Math.sqrt((n - 2) / (1 - ic * ic)) : Double.NaN;
    }
    private static double spearman(double[] x, double[] y) { return pearson(rank(x), rank(y)); }
    private static double[] rank(double[] a) {
        int n = a.length; Integer[] idx = new Integer[n];
        for (int i = 0; i < n; i++) idx[i] = i;
        Arrays.sort(idx, Comparator.comparingDouble(i -> a[i]));
        double[] r = new double[n]; int i = 0;
        while (i < n) {
            int j = i;
            while (j + 1 < n && a[idx[j + 1]] == a[idx[i]]) j++;
            double avg = (i + j) / 2.0 + 1;
            for (int k = i; k <= j; k++) r[idx[k]] = avg;
            i = j + 1;
        }
        return r;
    }
    private static double pearson(double[] x, double[] y) {
        int n = x.length; double mx = mean(x), my = mean(y), sxy = 0, sxx = 0, syy = 0;
        for (int i = 0; i < n; i++) { double dx = x[i] - mx, dy = y[i] - my; sxy += dx * dy; sxx += dx * dx; syy += dy * dy; }
        return (sxx > 0 && syy > 0) ? sxy / Math.sqrt(sxx * syy) : Double.NaN;
    }
    private static double mean(double[] a) { double s = 0; for (double v : a) s += v; return a.length > 0 ? s / a.length : 0; }
    private static double q(double[] sorted, double p) {
        if (sorted.length == 0) return Double.NaN;
        int i = (int) Math.round(p * (sorted.length - 1));
        return sorted[Math.max(0, Math.min(sorted.length - 1, i))];
    }
    private static double pctGe(double[] x, float thr) {
        int c = 0; for (double v : x) if (v >= thr) c++;
        return (double) c / x.length;
    }
    private static String f4(double v) { return String.format(Locale.US, "%.4f", v); }
    private static String f2(double v) { return String.format(Locale.US, "%.2f", v); }
    private static String f1(double v) { return String.format(Locale.US, "%.1f", v); }
}