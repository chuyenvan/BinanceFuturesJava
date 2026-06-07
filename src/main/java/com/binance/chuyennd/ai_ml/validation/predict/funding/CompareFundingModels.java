package com.binance.chuyennd.ai_ml.validation.predict.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * SO SÁNH HEAD-TO-HEAD 2 MODEL FUNDING (ONNX cũ 2025 vs mới 2026) — black-box, không cần code train.
 *
 * BẢN TỐI ƯU (~100x so với bản đầu):
 *  - CHỈ extract feature + predict cho symbol ĐẾN HẠN de-overlap 72h. Sau lượt quét đầu
 *    (~500 symbol), mỗi symbol chỉ đến hạn lại sau 72h => gần như 0 việc/phút.
 *  - Đánh đổi: bỏ corr full-sample mọi-phút (đã đo được: ~0.80 trên 4.6M cặp, ổn định
 *    qua 2 lần chạy). corr/percentile giờ tính trên mẫu de-overlap — đúng hơn về thống kê.
 *  - updateMarketHistory + getTopCoin VẪN chạy mỗi phút (bắt buộc cho tính liên tục feature).
 *
 * NGUYÊN TẮC CÔNG BẰNG (sai là kết quả vô nghĩa):
 *  - Chỉ đo từ FAIR_START = 20260529: model mới train tới 20260525, label nhìn 72h
 *    => mẫu train cuối dùng giá tới ~20260528 => từ 20260529 CẢ HAI model đều OOS sạch.
 *  - Cùng MỘT feature vector (FundingFeatureExtractorV2, mirror GenerateFundingPredictionsTool)
 *    cho cả hai model. Khác duy nhất = file ONNX.
 *  - Realized khớp ĐÚNG label6: entry=priceClose tại t, target=×1.06, hit nếu maxPrice>=target
 *    trong (t, t+72h] (subMap exclusive-from inclusive-to). Đã verify với FundingDataCollectionManager.
 *  - Chỉ đánh giá t <= now - 72h (cần đủ 72h tương lai cho realized; thiếu => thiên về fail giả).
 *
 * ĐẦU RA:
 *  (0) sanity: output-dim từng model, chặn output suy biến (hằng số/0 = feature mismatch
 *      bị predictBatch nuốt lỗi).
 *  (1) IC(pred[0], realized_fail) từng model — kỳ vọng DƯƠNG.
 *  (2) corr(predOld, predNew) trên mẫu de-overlap (tham chiếu full-sample đã đo: ~0.80).
 *  (3) IC(predNew - predOld, realized_fail) — phần KHÁC NHAU có mang tín hiệu thật không.
 *  (4) Phân bố pred[0] từng model (p10/p50/p90) + %<=0.321 — nếu deploy model mới thì universe
 *      pre-filter (break tại maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD × AI_DYNAMIC_MAX)
 *      PHÌNH/CO bao nhiêu. Thông tin sống còn trước khi deploy.
 *  (5) fail-rate nhóm SỬ DỤNG THẬT (pred<=0.32) từng model + chia lát.
 *
 * ⚠️ Cửa sổ sạch còn ngắn => n nhỏ, kết quả SƠ BỘ. Chạy lại định kỳ khi cửa sổ dài thêm.
 * Chạy trên 226 (read-only) hoặc Kaggle. KHÔNG ghi gì vào Aerospike.
 */
public class CompareFundingModels {

    private static final Logger LOG = LoggerFactory.getLogger(CompareFundingModels.class);

    // ⚙️ CHỈNH đường dẫn theo máy chạy. MODEL_OLD phải là bản train tới 20251219.
    private static final String MODEL_OLD = "../kaggle/kaggle_model/model_2025/models_funding/Funding_Classifier_Final.onnx";
    private static final String MODEL_NEW = "../kaggle/kaggle_model/model_2026/models_funding/Funding_Classifier_Final.onnx";

    // 20260525 (trainEnd model mới) + 72h purge label => 20260529 cả hai OOS sạch
    private static final String FAIR_START_DATE = "20260529";

    private static final long H72 = 72L * 60 * 60 * 1000;
    private static final float TARGET_MULT = 1.06f;          // +6%, khớp label6
    private static final float USAGE_CUT = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * Configs.AI_DYNAMIC_MAX; // ≈0.321
    private static final int SANITY_N = 200;

    private final Map<Long, TreeMap<Long, Map<String, KlineObjectSimple>>> dataCache = new HashMap<>();

    public static void main(String[] args) {
        try { new CompareFundingModels().run(); }
        catch (Exception e) { LOG.error("CompareFundingModels error", e); }
    }

    private static class Sample {
        final float pOld, pNew; final int fail;
        Sample(float pOld, float pNew, int fail) { this.pOld = pOld; this.pNew = pNew; this.fail = fail; }
    }

    public void run() throws Exception {
        long fairStart = Utils.sdfFile.parse(FAIR_START_DATE).getTime();
        long warmupStart = fairStart - Utils.TIME_DAY;            // 24h warmup cho extractor (mirror gen tool)
        long evalEnd = System.currentTimeMillis() - H72;          // cần đủ 72h tương lai cho realized
        if (evalEnd <= fairStart) {
            LOG.error("⛔ Cửa sổ sạch chưa đủ: evalEnd({}) <= fairStart({}). Chờ thêm dữ liệu.",
                    Utils.normalizeDateYYYYMMDDHHmm(evalEnd), FAIR_START_DATE);
            return;
        }
        LOG.info("⚖️ SO SÁNH FUNDING OLD vs NEW | fair window: {} -> {} | usageCut(pre-filter)={}",
                FAIR_START_DATE, Utils.normalizeDateYYYYMMDDHHmm(evalEnd), String.format(Locale.US, "%.3f", USAGE_CUT));

        LOG.info("📥 Nạp market data + symbol mapper...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<String, Short> symbolMap = DataManagerAerospikeFloatSim.loadSymbolMapper();

        List<Sample> samples = new ArrayList<>();
        Map<Short, Long> lastAccepted = new HashMap<>();          // de-overlap 72h/symbol ONLINE (sentinel 0L!)
        List<float[]> sanity = new ArrayList<>();
        int[] dims = {-1, -1};

        try (FundingOnnxInferenceManager brainOld = new FundingOnnxInferenceManager(MODEL_OLD);
             FundingOnnxInferenceManager brainNew = new FundingOnnxInferenceManager(MODEL_NEW)) {

            FundingDataCollectionManager.FundingFeatureExtractorV2 extractor =
                    new FundingDataCollectionManager.FundingFeatureExtractorV2();

            long day = Utils.getDate(warmupStart);
            long lastDay = Utils.getDate(System.currentTimeMillis());
            int dayCount = 0;

            while (day <= lastDay) {
                try {
                    ensureLoaded(day);
                    TreeMap<Long, Map<String, KlineObjectSimple>> today = dataCache.get(day);
                    if (today != null) {
                        // lookup 4 ngày (hôm nay + 3 ngày sau) đủ cửa sổ 72h cho realized
                        TreeMap<Long, Map<String, KlineObjectSimple>> lookup = new TreeMap<>();
                        for (int i = 0; i <= 3; i++) {
                            long d = day + (long) i * Utils.TIME_DAY;
                            ensureLoaded(d);
                            TreeMap<Long, Map<String, KlineObjectSimple>> dd = dataCache.get(d);
                            if (dd != null) lookup.putAll(dd);
                        }

                        for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : today.entrySet()) {
                            long time = e.getKey();
                            Map<String, KlineObjectSimple> snap = e.getValue();

                            // 1) LUÔN nuôi history mỗi phút (kể cả warmup) — bắt buộc cho tính liên tục feature
                            extractor.updateMarketHistory(snap);
                            List<String> basket = CoinRankManager.getInstance().getTopCoin(time);

                            if (time < fairStart || time > evalEnd) continue;

                            // 2) CHỈ extract + predict cho symbol ĐẾN HẠN 72h (tối ưu ~100x).
                            //    Lượt quét đầu xử lý ~500 symbol; sau đó mỗi symbol chỉ đến hạn lại sau 72h.
                            List<Short> ids = new ArrayList<>();
                            List<String> syms = new ArrayList<>();
                            List<float[]> feats = new ArrayList<>();
                            for (String symbol : snap.keySet()) {
                                Short symId = symbolMap.get(symbol);
                                if (symId == null) continue;
                                if (time - lastAccepted.getOrDefault(symId, 0L) < H72) continue; // chưa đến hạn
                                KlineObjectSimple ticker = snap.get(symbol);
                                if (ticker == null || !Utils.isTickerAvailable(ticker) || ticker.priceClose <= 0) continue;
                                OrderTargetInfoTest dummy = new OrderTargetInfoTest(
                                        OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                                        Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY);
                                dummy.lastEntry = ticker.priceClose;
                                FundingMarketFeatures f = extractor.extractFeatures(
                                        time, dummy, snap, time2MarketData.get(time), basket);
                                if (f != null) {
                                    ids.add(symId);
                                    syms.add(symbol);
                                    feats.add(brainOld.extractFeaturesToArray(f)); // CÙNG vector cho cả hai brain
                                }
                            }
                            if (feats.isEmpty()) continue;

                            // 3) Predict CẢ HAI model trên cùng batch (chunk 20, mirror gen tool)
                            float[][] pOldArr = predictAll(brainOld, feats);
                            float[][] pNewArr = predictAll(brainNew, feats);

                            // 4) Realized + ghi mẫu (symbol này khóa 72h tới)
                            for (int i = 0; i < ids.size(); i++) {
                                float[] po = pOldArr[i], pn = pNewArr[i];
                                if (po == null || pn == null || po.length == 0 || pn.length == 0) continue;
                                if (dims[0] < 0) {
                                    dims[0] = po.length; dims[1] = pn.length;
                                    LOG.info("🔎 OUTPUT DIM: old={} new={} (pred[0]=P-fail nếu 5 lớp; len=1 thì chính giá trị đó)",
                                            dims[0], dims[1]);
                                }
                                float vOld = po[0], vNew = pn[0];
                                if (sanity.size() < SANITY_N) sanity.add(new float[]{vOld, vNew});

                                String sym = syms.get(i);
                                KlineObjectSimple k = snap.get(sym);
                                boolean hit = hitWithin(lookup, sym, k.priceClose * TARGET_MULT, time);
                                samples.add(new Sample(vOld, vNew, hit ? 0 : 1));
                                lastAccepted.put(ids.get(i), time);
                            }
                        }
                    }
                    dataCache.remove(day - Utils.TIME_DAY);   // xả ngày cũ, giữ RAM phẳng
                } catch (Exception ex) {
                    LOG.warn("⚠️ Lỗi ngày {}: {}", Utils.normalizeDateYYYYMMDD(day), ex.getMessage());
                }
                day += Utils.TIME_DAY;
                if (++dayCount % 2 == 0) LOG.info("... {} ngày | samples(de-overlap)={}", dayCount, samples.size());
            }
        }

        if (!sanityOk(sanity)) return;
        analyze(samples);
    }

    /** predict theo chunk 20 — mirror GenerateFundingPredictionsTool. */
    private float[][] predictAll(FundingOnnxInferenceManager brain, List<float[]> feats) {
        float[][] out = new float[feats.size()][];
        int chunk = 20;
        for (int i = 0; i < feats.size(); i += chunk) {
            List<float[]> sub = feats.subList(i, Math.min(feats.size(), i + chunk));
            List<float[]> res = brain.predictBatch(sub);
            for (int j = 0; j < res.size(); j++) out[i + j] = res.get(j);
        }
        return out;
    }

    /** Khớp label6.checkProfit: cửa sổ (t, t+72h], chạm khi maxPrice >= target. */
    private boolean hitWithin(TreeMap<Long, Map<String, KlineObjectSimple>> lookup, String sym, float target, long startTime) {
        NavigableMap<Long, Map<String, KlineObjectSimple>> range = lookup.subMap(startTime, false, startTime + H72, true);
        for (Map<String, KlineObjectSimple> snap : range.values()) {
            KlineObjectSimple k = snap.get(sym);
            if (k != null && k.maxPrice >= target) return true;
        }
        return false;
    }

    private void ensureLoaded(long day) {
        if (!dataCache.containsKey(day)) {
            try { dataCache.put(day, DataManagerAerospikeFloatSim.readDataFromAerospike1M(day)); }
            catch (Exception e) { dataCache.put(day, null); }
        }
    }

    /** Output suy biến (hằng số/0) = predictBatch NUỐT lỗi feature-mismatch và trả 0 — phải chặn sớm. */
    private boolean sanityOk(List<float[]> sanity) {
        if (sanity.size() < 20) {
            LOG.error("⛔ Quá ít mẫu sanity ({}). Kiểm tra data/model path.", sanity.size());
            return false;
        }
        double sdOld = sd(sanity, 0), sdNew = sd(sanity, 1);
        LOG.info("🔎 SANITY: sd(pred[0]) old={} new={} trên {} mẫu đầu", f4(sdOld), f4(sdNew), sanity.size());
        if (sdOld < 1e-6 || sdNew < 1e-6) {
            LOG.error("⛔ Model output HẰNG SỐ (sd~0) => khả năng feature-mismatch bị predictBatch nuốt lỗi"
                    + " trả 0. DỪNG — kiểm NUM_FEATURES/input-shape của model đó trước khi tin bất kỳ số nào.");
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
    private void analyze(List<Sample> samples) {
        int n = samples.size();
        LOG.info("\n================ COMPARE FUNDING OLD vs NEW — n(de-overlap)={} ================", n);
        if (n < 1000) LOG.warn("⚠️ n={} < 1000 => kết quả SƠ BỘ (cửa sổ sạch còn ngắn). Chạy lại sau 1-2 tuần.", n);
        if (n < 50) { LOG.error("⛔ Quá ít mẫu."); return; }

        double[] pOld = new double[n], pNew = new double[n], fail = new double[n], diff = new double[n];
        for (int i = 0; i < n; i++) {
            Sample s = samples.get(i);
            pOld[i] = s.pOld; pNew[i] = s.pNew; fail[i] = s.fail; diff[i] = s.pNew - s.pOld;
        }

        // (1) IC từng model
        double icOld = spearman(pOld, fail), icNew = spearman(pNew, fail);
        LOG.info("(1) IC(pred[0], realized_FAIL):  OLD = {} (t={})  |  NEW = {} (t={})   [kỳ vọng DƯƠNG]",
                f4(icOld), f2(tStat(icOld, n)), f4(icNew), f2(tStat(icNew, n)));

        // (2) tương quan hai model — trên mẫu de-overlap (tham chiếu full-sample đã đo: ~0.80 / 4.6M cặp)
        LOG.info("(2) corr(predOld, predNew) trên mẫu de-overlap: Pearson = {} | Spearman = {}"
                        + "   (full-sample tham chiếu: ~0.80)",
                f4(pearson(pOld, pNew)), f4(spearman(pOld, pNew)));
        LOG.info("    => ~0.98+: hai model gần như MỘT, đổi không lợi. Thấp hơn nhiều: model mới THẬT SỰ khác.");

        // (3) phần khác nhau có tín hiệu không
        double icDiff = spearman(diff, fail);
        LOG.info("(3) IC(predNew - predOld, realized_FAIL) = {} (t={})", f4(icDiff), f2(tStat(icDiff, n)));
        LOG.info("    => DƯƠNG có ý nghĩa: phần model mới 'nghĩ khác' mang tín hiệu THÊM. ~0: khác biệt là nhiễu.");

        // (4) phân bố pred[0] + %<=USAGE_CUT
        logDistribution("OLD", pOld);
        logDistribution("NEW", pNew);

        // (5) chất lượng nhóm SỬ DỤNG THẬT (pred <= USAGE_CUT) + chia lát
        double base = mean(fail);
        LOG.info("(5) base-rate FAIL toàn mẫu = {}%", f1(base * 100));
        logUsageSlices("OLD", pOld, fail, base);
        logUsageSlices("NEW", pNew, fail, base);

        LOG.info("\n📌 CÁCH ĐỌC TỔNG:");
        LOG.info("   - NEW thắng khi: IC cao hơn RÕ + fail-rate nhóm <=cut THẤP hơn + IC(diff) dương"
                + " => đáng deploy (sau khi gen set mới + CALIBRATE ngưỡng theo phân bố mới ở mục 4).");
        LOG.info("   - corr ~1 hoặc IC ngang nhau => GIỮ model cũ (đổi model = rủi ro vận hành, không lợi rõ thì không đổi).");
        LOG.info("   - %<=cut của NEW lệch xa OLD => deploy mà KHÔNG chỉnh ngưỡng sẽ đổi hẳn số lệnh vào — phải calibrate trước.");
        LOG.info("   - n nhỏ => mọi kết luận SƠ BỘ; chạy lại hàng tuần khi cửa sổ sạch dài thêm.");
    }

    private void logDistribution(String name, double[] p) {
        double[] sorted = p.clone(); Arrays.sort(sorted);
        int under = 0; for (double v : p) if (v <= USAGE_CUT) under++;
        LOG.info("(4) [{}] pred[0]: p10={} p50={} p90={} | %<= {} (pre-filter cut) = {}%",
                name, f4(perc(sorted, 10)), f4(perc(sorted, 50)), f4(perc(sorted, 90)),
                String.format(Locale.US, "%.3f", USAGE_CUT), f1(under * 100.0 / p.length));
    }

    private void logUsageSlices(String name, double[] p, double[] fail, double base) {
        double[][] slices = {{-1, 0.10}, {0.10, 0.20}, {0.20, USAGE_CUT}, {-1, USAGE_CUT}};
        String[] labels = {"<=0.10", "0.10-0.20", "0.20-" + String.format(Locale.US, "%.2f", USAGE_CUT),
                "<=" + String.format(Locale.US, "%.2f", USAGE_CUT) + " (NHÓM HỆ TRADE)"};
        StringBuilder sb = new StringBuilder("    [" + name + "] ");
        for (int s = 0; s < slices.length; s++) {
            int ns = 0; double sf = 0;
            for (int i = 0; i < p.length; i++)
                if (p[i] > slices[s][0] && p[i] <= slices[s][1]) { ns++; sf += fail[i]; }
            if (ns >= 20) sb.append(String.format(Locale.US, "%s: n=%d fail=%.1f%% (x%.2f base) | ",
                    labels[s], ns, sf / ns * 100, (sf / ns) / base));
            else sb.append(labels[s]).append(": n=").append(ns).append(" (ít) | ");
        }
        LOG.info(sb.toString());
    }

    // ===== thống kê =====
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
    private static double perc(double[] sorted, double p) {
        if (sorted.length == 0) return Double.NaN;
        int i = (int) Math.round(p / 100.0 * (sorted.length - 1));
        return sorted[Math.max(0, Math.min(sorted.length - 1, i))];
    }
    private static String f4(double v) { return String.format(Locale.US, "%.4f", v); }
    private static String f2(double v) { return String.format(Locale.US, "%.2f", v); }
    private static String f1(double v) { return String.format(Locale.US, "%.1f", v); }
}