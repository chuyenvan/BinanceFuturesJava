package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * MÔ PHỎNG PHANH ĐỘNG (checkSignalDynamic) TRÊN OOS THẬT — đo phanh có ĐẠP không, đạp ĐÚNG không,
 * và CỨU được bao nhiêu. Sửa lỗi tool trước (chỉ đo ngưỡng cứng -9.2% => tưởng nhầm phanh chết).
 *
 * Logic mô phỏng KHỚP checkSignalDynamic:
 *   symbolPred = funding pred (label6, pred[0]) của symbol đó tại ts (set FUNDING_PRED, 226).
 *   - chặn sớm: pred15M < MIN_MOMENTUM_15M && symbolPred > PREDICT_SYMBOL_RATE_MAX_THRESHOLD -> REJECT(early)
 *   - scale = clamp((symbolPred/MAX_THRES)*AI_DYNAMIC_MULTIPLIER, AI_DYNAMIC_MIN, AI_DYNAMIC_MAX)
 *   - dyn15M=MIN_MOMENTUM_15M*scale; dyn24H=MIN_MOMENTUM_24H*scale; dynRisk=HARD_RISK_LIMIT_4H/scale
 *   - REJECT nếu predRisk4H<=dynRisk (RISK) | pred15M<dyn15M (MOM15) | pred24H<dyn24H (MOM24)
 *   - symbolPred null -> fallback checkSignal (ngưỡng cứng).
 *
 * Đo:
 *   1. % entry bị REJECT (tổng + tách lý do: RISK / MOM15 / MOM24 / EARLY) — phanh có đạp không.
 *   2. Trong các điểm REJECT-vì-RISK: realized drawdown 4h có THẬT sâu không (precision phanh risk).
 *   3. Ablation: so realized drawdown của PASS-set (phanh cho qua) vs REJECT-set (phanh chặn).
 *      Nếu REJECT-set drawdown sâu hơn PASS-set rõ rệt => phanh CỨU thật (khớp 'bỏ thì lởm').
 *   Tách theo regime.
 *
 * Chạy trên 226. Chỉ đọc. CUTOFF = ngày mô hình cũ chưa thấy.
 */
public class ValidateBrakeDynamic {

    private static final Logger LOG = LoggerFactory.getLogger(ValidateBrakeDynamic.class);

    private static final String CUTOFF_DATE = "20251220";
    private static final int WARMUP_DAYS = 2;
    private static final float UP = 0, DOWN = 1, SIDE = 2;

    // lý do reject
    private static final int PASS = 0, R_RISK = 1, R_MOM15 = 2, R_MOM24 = 3, R_EARLY = 4;

    public static void main(String[] args) {
        try { new ValidateBrakeDynamic().run(); } catch (Exception e) { LOG.error("Main error", e); }
    }

    public void run() throws Exception {
        long cutoff = Utils.sdfFile.parse(CUTOFF_DATE).getTime();
        long warmup = cutoff - WARMUP_DAYS * Utils.TIME_DAY;
        long endTime = System.currentTimeMillis();

        LOG.info("📥 Nạp market pred + funding pred (symbolPred) từ 226...");
        TreeMap<Long, AiPredictionData> marketPred = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> fundingPred = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        SimpleSymbolMapper mapper = SimpleSymbolMapper.getInstance();
        mapper.init();
        LOG.info("✅ market={} funding={} | đo từ {}", marketPred.size(), fundingPred.size(),
                Utils.normalizeDateYYYYMMDD(cutoff));

        HistoryManager.getInstance().resetCache();

        // gom: mỗi điểm 1 entry quyết định (symbol trong basket)
        // lưu: reason, realizedDD4h, regime, isRejectRisk
        List<int[]> meta = new ArrayList<>();    // {reason, regimeCode}
        List<Float> ddList = new ArrayList<>();   // realized drawdown 4h của symbol đó

        long current = warmup; int days = 0;

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
                        HistoryManager.getInstance().updateHistory(e.getValue());
                        if (ts < cutoff) continue;

                        AiPredictionData mp = marketPred.get(ts);
                        if (mp == null) continue;
                        long[] fp = fundingPred.get(ts);
                        Map<Short, Float> symPredMap = decodeFunding(fp);

                        List<String> basket = HistoryManager.getInstance().findPotentialLosers(ts);
                        if (basket == null || basket.isEmpty()) continue;

                        float btc24 = HistoryManager.getInstance().getReturn("BTCUSDT", 1440);
                        int reg = btc24 > 0.02f ? (int) UP : (btc24 < -0.02f ? (int) DOWN : (int) SIDE);

                        for (String sym : basket) {
                            short id = mapper.getId(sym);
                            Float symbolPred = symPredMap.get(id);  // có thể null

                            int reason = simulateFilter(mp, symbolPred);
                            float ddSym = symbolDrawdown(lookup, ts, 240, sym);

                            meta.add(new int[]{reason, reg});
                            ddList.add(ddSym);
                        }
                    }
                }
            } catch (Exception ex) {
                LOG.warn("⚠️ Lỗi ngày {}: {}", Utils.normalizeDateYYYYMMDD(current), ex.getMessage());
            }
            current += Utils.TIME_DAY;
            if (++days % 20 == 0) LOG.info("... {} ngày, {} quyết định", days, meta.size());
        }

        analyze(meta, ddList);
    }

    /** Khớp AIRejectFilter.checkSignalDynamic + checkSignal. Trả lý do (PASS/R_*). */
    private int simulateFilter(AiPredictionData p, Float symbolPred) {
        float pred15 = p.predReturn15M, risk = p.predRisk4H;   // MOM24 đã bỏ khỏi hệ

        if (symbolPred == null) {
            // fallback checkSignal (ngưỡng cứng)
            if (risk <= Configs.HARD_RISK_LIMIT_4H) return R_RISK;
            if (pred15 < Configs.MIN_MOMENTUM_15M) return R_MOM15;
            return PASS;
        }
        // chặn sớm
        if (pred15 < Configs.MIN_MOMENTUM_15M && symbolPred > Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD)
            return R_EARLY;

        float scale = (symbolPred / Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD) * Configs.AI_DYNAMIC_MULTIPLIER;
        scale = Math.max(Configs.AI_DYNAMIC_MIN, Math.min(scale, Configs.AI_DYNAMIC_MAX));

        float dyn15 = Configs.MIN_MOMENTUM_15M * scale;
        float dynRisk = Configs.HARD_RISK_LIMIT_4H / scale;

        if (risk <= dynRisk) return R_RISK;
        if (pred15 < dyn15) return R_MOM15;
        return PASS;
    }

    private void analyze(List<int[]> meta, List<Float> dd) {
        int n = meta.size();
        if (n < 100) { LOG.warn("⚠️ n quá nhỏ ({})", n); return; }

        int[] cnt = new int[5];
        for (int[] m : meta) cnt[m[0]]++;
        LOG.info("\n================ PHANH ĐỘNG — TỔNG {} quyết định ================", n);
        LOG.info("PASS={}% | REJECT tổng={}%", pct(cnt[PASS], n), pct(n - cnt[PASS], n));
        LOG.info("  trong đó: RISK={}% MOM15={}% MOM24={}% EARLY={}%",
                pct(cnt[R_RISK], n), pct(cnt[R_MOM15], n), pct(cnt[R_MOM24], n), pct(cnt[R_EARLY], n));
        LOG.info("👉 Nếu RISK>0%% => phanh CHỐNG SẬP CÓ đạp (bác bỏ kết luận 'phanh chết' của ngưỡng cứng).");

        // realized drawdown: PASS-set vs REJECT-set (cứu được không)
        double ddPass = avgDD(meta, dd, PASS, -1);
        double ddRejRisk = avgDD(meta, dd, R_RISK, -1);
        double ddRejAll = avgDDReject(meta, dd, -1);
        LOG.info("\n📉 Realized drawdown 4h TB:");
        LOG.info("  PASS (phanh cho vào)      = {}", fmt(ddPass));
        LOG.info("  REJECT-vì-RISK            = {}", fmt(ddRejRisk));
        LOG.info("  REJECT (mọi lý do)        = {}", fmt(ddRejAll));
        LOG.info("👉 REJECT-RISK sâu hơn PASS rõ rệt => phanh risk CHẶN ĐÚNG điểm sắp sụt (cứu thật).");

        // tách regime
        for (float rg : new float[]{UP, DOWN, SIDE}) {
            int total = 0, rejRisk = 0;
            for (int[] m : meta) if (m[1] == (int) rg) { total++; if (m[0] == R_RISK) rejRisk++; }
            if (total >= 30) {
                double ddP = avgDDRegime(meta, dd, PASS, (int) rg);
                double ddR = avgDDRegime(meta, dd, R_RISK, (int) rg);
                LOG.info("  [regime {}] n={} | reject-RISK={}% | ddPASS={} ddREJ-RISK={}",
                        rgName(rg), total, pct(rejRisk, total), fmt(ddP), fmt(ddR));
            }
        }
        LOG.info("\n📌 Kết luận đọc: (a) RISK%% > 0 => phanh sống. (b) ddREJ-RISK << ddPASS => chặn đúng. "
                + "(c) ở regime down phanh đạp nhiều + chặn đúng => đây chính là cái 'bỏ thì lởm'.");
    }

    // ===== helpers =====
    private Map<Short, Float> decodeFunding(long[] arr) {
        Map<Short, Float> m = new HashMap<>();
        if (arr == null) return m;
        for (long enc : arr) {
            short id = (short) (enc >> 32);
            float pred = Float.intBitsToFloat((int) (enc & 0xFFFFFFFFL));
            m.put(id, pred);
        }
        return m;
    }

    private float symbolDrawdown(TreeMap<Long, Map<String, KlineObjectSimple>> data, long ts, int minutes, String sym) {
        long end = ts + minutes * 60_000L;
        Map<String, KlineObjectSimple> cur = data.get(ts);
        if (cur == null || !cur.containsKey(sym)) return 0f;
        float entry = cur.get(sym).priceClose;
        if (entry <= 0) return 0f;
        NavigableMap<Long, Map<String, KlineObjectSimple>> range = data.subMap(ts, false, end, true);
        float worst = 0f;
        for (Map<String, KlineObjectSimple> mm : range.values()) {
            if (mm.containsKey(sym)) {
                float low = mm.get(sym).minPrice;
                if (low > 0) { float d = (low - entry) / entry; if (d < worst) worst = d; }
            }
        }
        return worst;
    }

    private double avgDD(List<int[]> meta, List<Float> dd, int reason, int regime) {
        double s = 0; int c = 0;
        for (int i = 0; i < meta.size(); i++)
            if (meta.get(i)[0] == reason && (regime < 0 || meta.get(i)[1] == regime)) { s += dd.get(i); c++; }
        return c > 0 ? s / c : Double.NaN;
    }

    private double avgDDRegime(List<int[]> meta, List<Float> dd, int reason, int regime) { return avgDD(meta, dd, reason, regime); }

    private double avgDDReject(List<int[]> meta, List<Float> dd, int regime) {
        double s = 0; int c = 0;
        for (int i = 0; i < meta.size(); i++)
            if (meta.get(i)[0] != PASS && (regime < 0 || meta.get(i)[1] == regime)) { s += dd.get(i); c++; }
        return c > 0 ? s / c : Double.NaN;
    }

    private String pct(int a, int b) { return String.format(Locale.US, "%.1f", b > 0 ? 100.0 * a / b : 0); }
    private String fmt(double v) { return String.format(Locale.US, "%.4f", v); }
    private String rgName(float r) { return r == UP ? "up" : r == DOWN ? "down" : "side"; }
}