package com.binance.chuyennd.ai_ml.features.export;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.FileWriter;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-015 (H1_GATE_SPEC §2.1 + §2.4) — export FEATURE GATE NHÓM A (đã có sẵn trong
 * {@link MarketFeatures}/{@link ComprehensiveMarketFeatureExtractor}) ra cột, ALIGN {@code t} với
 * {@code gate_return.csv} (sample 15m, 2021→nay). CHỈ export + validate, KHÔNG code feature mới.
 *
 * <p><b>19 feature nhóm A</b> (đúng §2.1, không hơn — BỎ momentum1M/5M, rsi14, distMA20,
 * momentumAcceleration, trendStrengthETH, trendConsistency, volatility1M, GROUP 5 TIME, label cũ):
 * <ul>
 *   <li>momentum BTC: momentum15M, 1H, 4H, 24H</li>
 *   <li>volatility: volatility15M, 1H, 24H, volatilityTermStructure, volumeSpike, volatilityRegime(ordinal)</li>
 *   <li>breadth: advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, btcDominance</li>
 *   <li>funding: <b>basketFundingAvg</b> (= fundingRateRaw đổi TÊN cho đúng nghĩa ADR-0011, KHÔNG đổi giá trị),
 *       fundingRateAvg24H, fundingRateTrend</li>
 *   <li>basket: basketVolSpike</li>
 * </ul>
 * {@code volatilityRegime} encode ordinal: LOW=0, NORMAL=1, HIGH=2 (mapping ghi sidecar {@link #MAP_OUT} + log).
 *
 * <p><b>Look-ahead clean:</b> extractor stateful chỉ chạm history {@code [.., t]} (ring close quá khứ +
 * funding ≤ t). Bảo đảm bằng feed nến CHRONOLOGICAL, chỉ ≤ t trước khi trích tại t. Warmup 48h (≥1440' cho
 * momentum24H/volatility24H). Sample mỗi 15m, emit từ {@code targetStart}.
 *
 * <p><b>Survivorship (đã kiểm code — §An toàn TASK-015):</b> path này KHÔNG lọc {@code Constants.diedSymbol}
 * ở BẤT KỲ tầng nào: {@code readDataFromAerospike1M} đọc mọi ticker trong proto; {@code HistoryManager.updateHistory}
 * feed mọi symbol; {@code CoinRankManager.updateRanking} xếp hạng từ {@code getAllSymbolsShort()};
 * {@code extractBreadthFeatures} dùng {@code getTopCoin} (xếp theo VOLUME). ⇒ coin die THAM GIA breadth/basket
 * tự nhiên miễn data 1m của chúng có trên 226 (TASK-005 backfill). Validate (e') báo #coin breadth/năm để xác nhận.
 *
 * <p>Đọc-only market data 226 ({@code IS_KAGGLE_MODE=true}); ghi {@link #OUT}. Chạy TRÊN 226 (đọc nặng) —
 * KHÔNG đồng thời với 012/builder-010/013 trên 226.
 */
public class ExportGateFeaturesGroupA {

    private static final Logger LOG = LoggerFactory.getLogger(ExportGateFeaturesGroupA.class);
    private static final long MS_15M = 15L * 60_000L;
    private static final String START_DATE = "20210101";
    private static final String OUT = "outputs/gate_features_groupA.csv";
    private static final String MAP_OUT = "outputs/gate_features_groupA_volatilityRegime_mapping.txt";
    private static final String GATE_RETURN = "outputs/gate_return.csv";   // để validate align

    /** Tên cột feature nhóm A (khớp thứ tự ghi row). */
    private static final String[] COLS = {
            "momentum15M", "momentum1H", "momentum4H", "momentum24H",
            "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure", "volumeSpike", "volatilityRegime",
            "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength", "btcDominance",
            "basketFundingAvg", "fundingRateAvg24H", "fundingRateTrend",
            "basketVolSpike"
    };

    /** Ordinal encode volatilityRegime (LOW<NORMAL<HIGH theo độ biến động tăng dần). */
    private static int encodeRegime(String r) {
        if ("LOW".equals(r)) return 0;
        if ("HIGH".equals(r)) return 2;
        return 1; // NORMAL hoặc null/khác
    }

    public static void main(String[] args) {
        try {
            Configs.IS_HPO_MODE = false;
            Configs.IS_KAGGLE_MODE = true;   // đọc 226 local

            long start = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR; // 2021-01-01 07:00 GMT+7
            long warmupStart = start - 2 * 24L * Utils.TIME_HOUR;                          // 48h warmup
            long end = System.currentTimeMillis();
            LOG.info("🏷️ TASK-015 export feature gate NHÓM A | warmup {} → emit từ {} → nay | sample 15m | {} feature",
                    Utils.normalizeDateYYYYMMDD(warmupStart), START_DATE, COLS.length);

            // MarketDataObject cho momentum15M (= rateDown15MAvg) / momentum1M nội bộ extractor
            LOG.info("📥 Nạp MarketDataObject (cho momentum15M)...");
            TreeMap<Long, MarketDataObject> time2Md = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
            ComprehensiveMarketFeatureExtractor extractor = new ComprehensiveMarketFeatureExtractor();

            FileWriter w = new FileWriter(OUT);
            w.write("tEpochMs,tDate," + String.join(",", COLS) + "\n");

            Validate v = new Validate();
            long emitted = 0, days = 0;

            for (long day = warmupStart; day < end; day += 24L * Utils.TIME_HOUR) {
                TreeMap<Long, Map<String, KlineObjectSimple>> oneDay = DataManagerAerospikeFloatSim.readDataFromAerospike1M(day);
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : oneDay.entrySet()) {
                    long epoch = e.getKey();
                    Map<String, KlineObjectSimple> map = e.getValue();
                    // feed CHRONOLOGICAL (warmup + cập nhật history); idempotent với extractAllFeatures (overwrite cùng startTime)
                    extractor.updateMarketHistory(map);
                    if (epoch < start || epoch % MS_15M != 0) continue;   // chỉ emit từ targetStart, lưới 15m

                    MarketFeatures f = extractor.extractAllFeatures(epoch, map, time2Md.get(epoch));
                    float[] vals = pick(f, v);                            // 19 giá trị (đã NaN/Inf→0, đếm ở v)
                    int basketSize = CoinRankManager.getInstance().getTopCoin(epoch).size();

                    StringBuilder sb = new StringBuilder(256);
                    sb.append(epoch).append(',').append(FMT.get().format(new Date(epoch)));
                    for (float val : vals) sb.append(',').append(fmt(val));
                    sb.append('\n');
                    w.write(sb.toString());
                    emitted++;
                    v.collect(epoch, vals, basketSize);
                }
                if (++days % 200 == 0) LOG.info("   ... {} ngày, {}, emitted={}", days, Utils.normalizeDateYYYYMMDD(day), emitted);
            }
            w.close();
            LOG.info("✅ Ghi {} dòng × {} feature → {} | range {} → ~nay", emitted, COLS.length, OUT, START_DATE);

            // lưu mapping volatilityRegime
            try (FileWriter mw = new FileWriter(MAP_OUT)) {
                mw.write("volatilityRegime ordinal encode (TASK-015):\nLOW=0\nNORMAL=1\nHIGH=2\n");
            }
            LOG.info("🗺️ mapping volatilityRegime → {}", MAP_OUT);

            v.report(time2Md);
        } catch (Exception e) {
            LOG.error("ExportGateFeaturesGroupA lỗi", e);
            System.exit(1);
        }
        // Aerospike client để lại thread NON-DAEMON → JVM KHÔNG tự thoát sau khi main() xong việc
        // (CSV đã ghi + validate đã in). Ép thoát để Kaggle/wrapper finalize + LƯU outputs/ ngay,
        // tránh treo tới 12h cutoff (đã dính: run đầu xong validate lúc ~72' nhưng kernel kẹt RUNNING).
        System.exit(0);
    }

    /** Rút 19 feature nhóm A từ MarketFeatures theo đúng thứ tự {@link #COLS}; NaN/Inf→0 (đếm ở Validate). */
    private static float[] pick(MarketFeatures f, Validate v) {
        float[] raw = {
                f.momentum15M, f.momentum1H, f.momentum4H, f.momentum24H,
                f.volatility15M, f.volatility1H, f.volatility24H, f.volatilityTermStructure, f.volumeSpike, encodeRegime(f.volatilityRegime),
                f.advanceDeclineRatio, f.percentAboveMA20, f.volumeRatioUpDown, f.marketBreadthStrength, f.btcDominance,
                f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend,
                f.basketVolSpike
        };
        for (int i = 0; i < raw.length; i++) {
            if (Float.isNaN(raw[i]) || Float.isInfinite(raw[i])) { v.nanInf[i]++; raw[i] = 0f; }
            if (raw[i] == 0f) v.zeros[i]++;
        }
        return raw;
    }

    private static String fmt(float val) { return String.format(Locale.US, "%.8f", val); }

    // ================== VALIDATE (chạy sau export trên 226) — H1_GATE_SPEC §2.4 ==================

    /**
     * Gom thống kê khi emit + recompute độc lập + align với gate_return.csv. Theo §2.4:
     * (a) range/phân bố percentile mỗi feature; (b) NaN/Inf→0 + 0-count (phân biệt 0-thật vs lỗi);
     * (c) recompute ~5 mốc đường khác (BTC momentum đọc trực tiếp); (d) look-ahead (feed chronological ≤ t);
     * (e) align: tập t khớp gate_return.csv. (e') survivorship: #coin breadth theo năm.
     */
    private static final class Validate {
        final long[] nanInf = new long[COLS.length];
        final long[] zeros = new long[COLS.length];
        final List<Float>[] dist = lists();
        // (c) watch 5 mốc: lưu t + momentum1H/4H/24H export (index 1,2,3)
        final List<long[]> watchT = new ArrayList<>();
        final List<float[]> watchMom = new ArrayList<>();
        // (e) tập t feature
        final TreeSet<Long> featureT = new TreeSet<>();
        // (e') basket size theo năm
        final Map<Integer, List<Integer>> year2basket = new TreeMap<>();

        @SuppressWarnings("unchecked")
        private static List<Float>[] lists() {
            List<Float>[] a = new List[COLS.length];
            for (int i = 0; i < a.length; i++) a[i] = new ArrayList<>();
            return a;
        }

        void collect(long t, float[] vals, int basketSize) {
            for (int i = 0; i < vals.length; i++) dist[i].add(vals[i]);
            featureT.add(t);
            year2basket.computeIfAbsent(year(t), x -> new ArrayList<>()).add(basketSize);
            if (watchT.size() < 5 && (featureT.size() % 9973 == 0 || watchT.isEmpty())) {
                watchT.add(new long[]{t});
                watchMom.add(new float[]{vals[1], vals[2], vals[3]});  // momentum1H/4H/24H
            }
        }

        void report(TreeMap<Long, MarketDataObject> time2Md) throws Exception {
            long n = dist[0].size();
            LOG.info("=== (a) RANGE/PHÂN BỐ mỗi feature (min | p1/p50/p99 | max) — n={} ===", n);
            for (int i = 0; i < COLS.length; i++) {
                List<Float> r = new ArrayList<>(dist[i]); Collections.sort(r);
                LOG.info("  {} min={} p1={} p50={} p99={} max={}", String.format("%-24s", COLS[i]),
                        r.isEmpty() ? "-" : g(r.get(0)), pc(r, 1), pc(r, 50), pc(r, 99),
                        r.isEmpty() ? "-" : g(r.get(r.size() - 1)));
            }
            LOG.info("=== (b) NaN/Inf→0 + 0-count mỗi feature (0 nhiều → soi 0-thật vs lỗi) ===");
            for (int i = 0; i < COLS.length; i++)
                LOG.info("  {} nanInf={} zeros={}/{} ({}%)", String.format("%-24s", COLS[i]), nanInf[i], zeros[i], n,
                        n == 0 ? 0 : String.format(Locale.US, "%.1f", 100.0 * zeros[i] / n));

            LOG.info("=== (c) RECOMPUTE độc lập momentum BTC (đọc close trực tiếp t & t−N) ===");
            for (int i = 0; i < watchT.size(); i++) {
                long t = watchT.get(i)[0];
                float[] exp = watchMom.get(i);
                Float r60 = btcReturn(t, 60), r240 = btcReturn(t, 240), r1440 = btcReturn(t, 1440);
                LOG.info("  t={} mom1H exp={} re={} {} | mom4H exp={} re={} {} | mom24H exp={} re={} {}",
                        FMT.get().format(new Date(t)),
                        g(exp[0]), s(r60), ok(exp[0], r60), g(exp[1]), s(r240), ok(exp[1], r240),
                        g(exp[2]), s(r1440), ok(exp[2], r1440));
            }

            LOG.info("=== (d) LOOK-AHEAD: extractor feed CHRONOLOGICAL, chỉ nến ≤ t trước khi trích tại t; "
                    + "ring/getReturn + funding getNearestFundingFee đều ≤ t (đã đọc code). Không chạm > t. ===");

            LOG.info("=== (e) ALIGN với {} ===", GATE_RETURN);
            alignWithGateReturn();

            LOG.info("=== (e') SURVIVORSHIP: #coin breadth (getTopCoin top-50%) theo NĂM (min/median) — kỳ vọng coin die tham gia ===");
            for (Map.Entry<Integer, List<Integer>> e : year2basket.entrySet()) {
                List<Integer> b = e.getValue(); Collections.sort(b);
                LOG.info("  {}: n={} basket min={} median={}", e.getKey(), b.size(), b.get(0), b.get(b.size() / 2));
            }
        }

        /** So tập t của feature với gate_return.csv: mọi t của gate phải có trong feature (feature ⊇ gate). */
        private void alignWithGateReturn() {
            try (BufferedReader br = new BufferedReader(new FileReader(GATE_RETURN))) {
                String line = br.readLine(); // header
                long gateRows = 0, missing = 0; long minGate = Long.MAX_VALUE, maxGate = Long.MIN_VALUE;
                while ((line = br.readLine()) != null) {
                    int comma = line.indexOf(',');
                    if (comma <= 0) continue;
                    long gt = Long.parseLong(line.substring(0, comma).trim());
                    gateRows++;
                    minGate = Math.min(minGate, gt); maxGate = Math.max(maxGate, gt);
                    if (!featureT.contains(gt)) missing++;
                }
                LOG.info("  gate rows={} range[{}..{}] | feature t={} | gate-t THIẾU trong feature={} {}",
                        gateRows, FMT.get().format(new Date(minGate)), FMT.get().format(new Date(maxGate)),
                        featureT.size(), missing, missing == 0 ? "ALIGN ✅" : "LỆCH 🔴 (soi gap/warmup)");
            } catch (Exception e) {
                LOG.warn("  ⚠️ không đọc được {} để align (chạy 012 trước?): {}", GATE_RETURN, e.getMessage());
            }
        }

        /** BTC close-to-close return qua N phút, đọc TRỰC TIẾP 2 nến (đường khác với ring của extractor). */
        private Float btcReturn(long t, int nMin) throws Exception {
            Float cNow = btcClose(t), cPast = btcClose(t - nMin * Utils.TIME_MINUTE);
            if (cNow == null || cPast == null || cPast <= 0) return null;
            return cNow / cPast - 1f;
        }

        private Float btcClose(long epoch) throws Exception {
            TreeMap<Long, Map<String, KlineObjectSimple>> m = DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(epoch, 1);
            if (m.isEmpty()) return null;
            KlineObjectSimple k = m.firstEntry().getValue().get("BTCUSDT");
            return (k != null && Utils.isTickerAvailable(k)) ? k.priceClose : null;
        }

        private String ok(float exp, Float re) { return (re != null && Math.abs(re - exp) < 1e-4) ? "KHỚP✅" : "LỆCH🔴"; }
        private String s(Float v) { return v == null ? "null" : g(v); }
    }

    private static String pc(List<Float> sorted, int p) {
        if (sorted.isEmpty()) return "-";
        int idx = Math.min(sorted.size() - 1, (int) Math.ceil(p / 100.0 * sorted.size()) - 1);
        if (idx < 0) idx = 0;
        return g(sorted.get(idx));
    }

    private static String g(float v) { return String.format(Locale.US, "%.6f", v); }

    private static final ThreadLocal<SimpleDateFormat> FMT =
            ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyyMMdd-HHmm")); // GMT+7

    private static int year(long ms) { return Integer.parseInt(new SimpleDateFormat("yyyy").format(new Date(ms))); }
}
