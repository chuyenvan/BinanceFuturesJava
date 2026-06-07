package com.binance.chuyennd.ai_ml.validation.predict.funding;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * VALIDATE FUNDING MODEL (CŨ — set len=1) TRÊN OOS THẬT — đóng nốt Bước 1 cho funding.
 *
 * symbolPred dùng trong filter EARLY = pred[0] = P(FAIL) = xác suất 72h tới KHÔNG đạt +6%.
 *   => symbolPred CAO = symbol XẤU (dễ fail). IC(symbolPred, realized_fail) kỳ vọng DƯƠNG.
 *
 * Realized tái dựng KHỚP ĐÚNG label6 (FundingDataCollectionManager.calculateLabelType/checkProfit):
 *   entry = priceClose tại t; target = entry*1.06f;
 *   hit72h = tồn tại 1 phút trong cửa sổ (t, t+72h] có maxPrice >= target  (subMap exclusive-from, inclusive-to);
 *   realized_fail = !hit72h  (ứng label6 == 0).
 *
 * READ-ONLY, chạy 226. Đo model CŨ đang chạy live (set funding_pred_1m_v5, mỗi record len=1 = pred[0]).
 * KHÔNG kết luận cho model 5 lớp mới (chưa gen vào set).
 */
public class ValidateFundingOOS {

    private static final Logger LOG = LoggerFactory.getLogger(ValidateFundingOOS.class);

    private static final String CUTOFF_DATE = "20251220";   // OOS: model cũ chưa thấy (chỉnh nếu biết mốc train khác)
    private static final int WARMUP_DAYS = 3;
    private static final long H72 = 72L * 60 * 60 * 1000;
    private static final float TARGET_MULT = 1.06f;          // +6% (khớp label6)
    private static final float EARLY_THRES = 0.197f;         // PREDICT_SYMBOL_RATE_MAX_THRESHOLD (điểm cắt EARLY thật)
    private static final int UP = 0, DOWN = 1, SIDE = 2;

    private final Map<Long, TreeMap<Long, Map<String, KlineObjectSimple>>> dataCache = new HashMap<>();

    public static void main(String[] args) {
        try { new ValidateFundingOOS().run(); } catch (Exception e) { LOG.error("ValidateFundingOOS error", e); }
    }

    private static class Rec {
        long ts; short id; float pred; int fail; int regime;
        Rec(long ts, short id, float pred, int fail, int regime) {
            this.ts = ts; this.id = id; this.pred = pred; this.fail = fail; this.regime = regime;
        }
    }

    public void run() throws Exception {
        long cutoff = Utils.sdfFile.parse(CUTOFF_DATE).getTime();
        long warmup = cutoff - WARMUP_DAYS * Utils.TIME_DAY;
        long endTime = System.currentTimeMillis();

        SimpleSymbolMapper mapper = SimpleSymbolMapper.getInstance();
        mapper.init();
        HistoryManager.getInstance().resetCache();

        LOG.info("📥 Nạp funding pred (pred[0]=P-fail) từ 226 (set {})...", DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_FUNDING_PRED);
        TreeMap<Long, long[]> fundingPred = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("✅ funding pred records={} | OOS từ {} | realized: entry=priceClose, target=+6%%, hit nếu maxPrice>=target trong (t, t+72h]",
                fundingPred.size(), CUTOFF_DATE);
        if (fundingPred.isEmpty()) { LOG.error("⛔ funding pred RỖNG — dừng."); return; }

        List<Rec> recs = new ArrayList<>();
        // DE-OVERLAP ONLINE: mốc ts mẫu được NHẬN gần nhất của mỗi symbol (replay đi tăng dần ts
        // -> greedy online == greedy batch). Chỉ tính hitWithin cho mẫu sống sót => giảm ~1000x compute/RAM.
        Map<Short, Long> lastAcceptedTs = new HashMap<>();
        long current = warmup;
        int days = 0;

        while (current <= endTime) {
            try {
                // nạp current + 3 ngày (đủ cửa sổ 72h) vào cache + dựng lookup
                ensureLoaded(current);
                TreeMap<Long, Map<String, KlineObjectSimple>> today = dataCache.get(current);
                if (today != null) {
                    TreeMap<Long, Map<String, KlineObjectSimple>> lookup = new TreeMap<>();
                    for (int i = 0; i <= 3; i++) {
                        long d = current + (long) i * Utils.TIME_DAY;
                        ensureLoaded(d);
                        TreeMap<Long, Map<String, KlineObjectSimple>> dd = dataCache.get(d);
                        if (dd != null) lookup.putAll(dd);
                    }

                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : today.entrySet()) {
                        long ts = e.getKey();
                        Map<String, KlineObjectSimple> snap = e.getValue();
                        HistoryManager.getInstance().updateHistory(snap);   // nuôi history cho regime
                        if (ts < cutoff) continue;

                        long[] fp = fundingPred.get(ts);
                        if (fp == null) continue;

                        float btc24 = HistoryManager.getInstance().getReturn("BTCUSDT", 1440);
                        int reg = btc24 > 0.02f ? UP : (btc24 < -0.02f ? DOWN : SIDE);

                        for (long enc : fp) {
                            short id = (short) (enc >> 32);
                            // de-overlap online: bỏ qua nếu chưa cách mẫu NHẬN trước đó của symbol này >= 72h
                            Long prev = lastAcceptedTs.get(id);
                            if (prev != null && ts - prev < H72) continue;

                            float pred = Float.intBitsToFloat((int) (enc & 0xFFFFFFFFL));
                            String sym = mapper.getSymbol(id);
                            if (sym == null) continue;
                            KlineObjectSimple k = snap.get(sym);
                            if (k == null || k.priceClose <= 0) continue;
                            float target = k.priceClose * TARGET_MULT;
                            boolean hit = hitWithin(lookup, sym, target, ts, H72);  // CHỈ tính cho mẫu sống sót
                            recs.add(new Rec(ts, id, pred, hit ? 0 : 1, reg));
                            lastAcceptedTs.put(id, ts);  // chỉ advance khi THỰC SỰ nhận mẫu
                        }
                    }
                }
                dataCache.remove(current - Utils.TIME_DAY);   // xả ngày cũ
            } catch (Exception ex) {
                LOG.warn("⚠️ Lỗi ngày {}: {}", Utils.normalizeDateYYYYMMDD(current), ex.getMessage());
            }
            current += Utils.TIME_DAY;
            if (++days % 20 == 0) LOG.info("... {} ngày, {} mẫu (đã de-overlap online)", days, recs.size());
        }

        analyze(recs);
    }

    /** KHỚP label6.checkProfit: cửa sổ (t, t+duration], chạm khi maxPrice >= target. */
    private boolean hitWithin(TreeMap<Long, Map<String, KlineObjectSimple>> lookup, String sym, float target,
                              long startTime, long durationMs) {
        long endTime = startTime + durationMs;
        NavigableMap<Long, Map<String, KlineObjectSimple>> range = lookup.subMap(startTime, false, endTime, true);
        for (Map<String, KlineObjectSimple> snap : range.values()) {
            KlineObjectSimple k = snap.get(sym);
            if (k != null && k.maxPrice >= target) return true;
        }
        return false;
    }

    private void ensureLoaded(long day) {
        if (!dataCache.containsKey(day)) {
            try {
                dataCache.put(day, DataManagerAerospikeFloatSim.readDataFromAerospike1M(day));
            } catch (Exception e) {
                dataCache.put(day, null);
            }
        }
    }

    // ====================== ĐO ======================
    private void analyze(List<Rec> recs) {
        // recs đã được de-overlap 72H/symbol ONLINE ngay trong replay (greedy theo ts tăng dần).
        int n = recs.size();
        LOG.info("\n================ FUNDING OOS — de-overlap(72H/symbol, online)={} ================", n);
        if (n < 100) { LOG.warn("⚠️ n quá nhỏ ({}) — dừng.", n); return; }
        if (n < 1000) LOG.warn("⚠️ n={} < 1000 -> KẾT LUẬN YẾU (giống cảnh báo market 24H).", n);

        double[] pred = new double[n], fail = new double[n], hit = new double[n];
        for (int i = 0; i < n; i++) { pred[i] = recs.get(i).pred; fail[i] = recs.get(i).fail; hit[i] = 1 - recs.get(i).fail; }

        // (1) IC live: symbolPred(P-fail) vs realized_fail -> kỳ vọng DƯƠNG
        double ic = spearman(pred, fail);
        double t = (Math.abs(ic) < 1) ? ic * Math.sqrt((n - 2) / (1 - ic * ic)) : Double.NaN;
        double icHit = spearman(pred, hit);
        LOG.info("(1) IC(symbolPred, realized_FAIL) = {} | t = {} | n = {}  [kỳ vọng DƯƠNG: P-fail cao -> fail thật]",
                f4(ic), f2(t), n);
        LOG.info("    IC(symbolPred, realized_HIT)  = {}  [phải ÂM, đối chiếu chéo]", f4(icHit));
        if (Double.isFinite(t) && ic > 0 && Math.abs(t) >= 2)
            LOG.info("    => IC dương có ý nghĩa: model PHÂN BIỆT được symbol xấu live.");
        else
            LOG.info("    => IC ~0 / sai dấu / |t|<2: model funding KHÔNG có edge live rõ ràng.");

        // (3) phân bố symbolPred
        double[] ps = pred.clone(); Arrays.sort(ps);
        double pctOverEarly = 0; for (double v : pred) if (v > EARLY_THRES) pctOverEarly++;
        pctOverEarly = pctOverEarly * 100 / n;
        LOG.info("(3) symbolPred phân bố: p10={} p50={} p90={} | %>{}(EARLY)= {}%",
                f4(perc(ps, 10)), f4(perc(ps, 50)), f4(perc(ps, 90)), EARLY_THRES, f1(pctOverEarly));

        // (2) LIFT theo ngưỡng (fail-rate trong nhóm pred>thr so base)
        double base = mean(fail);
        LOG.info("(2) base-rate FAIL (toàn mẫu de-overlap) = {}%", f1(base * 100));
        for (float thr : new float[]{0.1f, EARLY_THRES, 0.3f, 0.5f}) {
            int ns = 0; double sumFail = 0;
            for (int i = 0; i < n; i++) if (pred[i] > thr) { ns++; sumFail += fail[i]; }
            if (ns >= 20) {
                double fr = sumFail / ns;
                double lift = base > 0 ? fr / base : Double.NaN;
                double z = base > 0 && base < 1 ? (fr - base) / Math.sqrt(base * (1 - base) / ns) : Double.NaN;
                LOG.info("    pred>{}: n={} fail={}% (base {}%) LIFT=x{} z={}{}",
                        thr, ns, f1(fr * 100), f1(base * 100), f2(lift), f2(z),
                        Math.abs(thr - EARLY_THRES) < 1e-6 ? "   <== ngưỡng EARLY thật" : "");
            } else {
                LOG.info("    pred>{}: n={} (quá ít, bỏ qua)", thr, ns);
            }
        }

        // (4) tách regime
        LOG.info("(4) Theo regime (BTC 24h):");
        for (int rg = 0; rg <= 2; rg++) {
            List<Integer> idx = new ArrayList<>();
            for (int i = 0; i < n; i++) if (recs.get(i).regime == rg) idx.add(i);
            if (idx.size() < 30) { LOG.info("    [{}] n={} (quá ít)", regName(rg), idx.size()); continue; }
            double[] pr = new double[idx.size()], fl = new double[idx.size()];
            double bfail = 0; int over = 0; double sumOverFail = 0;
            for (int j = 0; j < idx.size(); j++) {
                int i = idx.get(j); pr[j] = pred[i]; fl[j] = fail[i]; bfail += fail[i];
                if (pred[i] > EARLY_THRES) { over++; sumOverFail += fail[i]; }
            }
            bfail /= idx.size();
            double icR = spearman(pr, fl);
            String liftStr = over >= 20 && bfail > 0 ? "x" + f2((sumOverFail / over) / bfail) : "n/a";
            LOG.info("    [{}] n={} | IC={} | base-fail={}% | LIFT@{}={}",
                    regName(rg), idx.size(), f4(icR), f1(bfail * 100), EARLY_THRES, liftStr);
        }

        LOG.info("\n📌 PHÁN QUYẾT: IC dương (|t|>=2) + LIFT@{} > 1.2 => funding CÓ edge live, EARLY đáng tin.",
                EARLY_THRES);
        LOG.info("   IC ~0/sai dấu HOẶC LIFT ~1 => funding KHÔNG phân biệt được symbol live => EARLY thực chất chỉ dựa 15M.");
        LOG.info("   (model CŨ, set len=1 — KHÔNG kết luận cho model 5 lớp mới.)");
    }

    // ===== helpers thống kê =====
    private static double spearman(double[] x, double[] y) {
        double[] rx = rank(x), ry = rank(y);
        return pearson(rx, ry);
    }

    private static double[] rank(double[] a) {
        int n = a.length;
        Integer[] idx = new Integer[n];
        for (int i = 0; i < n; i++) idx[i] = i;
        Arrays.sort(idx, Comparator.comparingDouble(i -> a[i]));
        double[] r = new double[n];
        int i = 0;
        while (i < n) {
            int j = i;
            while (j + 1 < n && a[idx[j + 1]] == a[idx[i]]) j++;
            double avg = (i + j) / 2.0 + 1;   // rank trung bình cho tie (1-based)
            for (int k = i; k <= j; k++) r[idx[k]] = avg;
            i = j + 1;
        }
        return r;
    }

    private static double pearson(double[] x, double[] y) {
        int n = x.length;
        double mx = mean(x), my = mean(y), sxy = 0, sxx = 0, syy = 0;
        for (int i = 0; i < n; i++) {
            double dx = x[i] - mx, dy = y[i] - my;
            sxy += dx * dy; sxx += dx * dx; syy += dy * dy;
        }
        return (sxx > 0 && syy > 0) ? sxy / Math.sqrt(sxx * syy) : Double.NaN;
    }

    private static double mean(double[] a) { double s = 0; for (double v : a) s += v; return a.length > 0 ? s / a.length : 0; }
    private static double perc(double[] sorted, double p) {
        if (sorted.length == 0) return Double.NaN;
        int i = (int) Math.round(p / 100.0 * (sorted.length - 1));
        return sorted[Math.max(0, Math.min(sorted.length - 1, i))];
    }
    private static String regName(int r) { return r == UP ? "up" : r == DOWN ? "down" : "side"; }
    private static String f4(double v) { return String.format(Locale.US, "%.4f", v); }
    private static String f2(double v) { return String.format(Locale.US, "%.2f", v); }
    private static String f1(double v) { return String.format(Locale.US, "%.1f", v); }
}
