package com.binance.chuyennd.ai_ml.features.export;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.research.oibackfill.OiMetricSets;
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
import java.nio.file.Files;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-018 (H1_GATE_SPEC §2.2 B6 + B8) — export FEATURE GATE crowdedness vĩ mô MARKET-LEVEL.
 * Align {@code t} lưới 15m với {@code gate_return.csv}. Mỗi feature validate RIÊNG (§2.4).
 *
 * <p><b>6 cột:</b> b6_oiMarketTotal, b6_oiDelta24h, b6_oiPriceDiverge · b8_lsGlobal, b8_lsToptrader, b8_takerBuySell.
 *
 * <p><b>Nguồn (đọc-only 226):</b> 5 set OI chunk-tháng (TASK-013) qua
 * {@link DataManagerAerospikeFloatSim#getMetricMap226}; {@code kline_15m_btceth} (BTC) cho lưới + giá thị trường.
 * Universe coin đọc từ {@code symfile=} (mỗi dòng 1 symbol; GỒM coin chết — survivorship).
 *
 * <p><b>RAM-aware (KHÁC 017):</b> 622 coin × 4 metric × 5m × ~4.5 năm KHÔNG load hết vào RAM. Xử lý TỪNG coin:
 * đọc map coin → resample lên lưới 15m (cộng dồn vào mảng theo mốc) → giải phóng. Bộ nhớ = 1 map + mảng lưới.
 *
 * <p><b>Look-ahead (bẫy chính):</b> tại mốc t chỉ dùng điểm ts ≤ t. Resample = với mỗi mốc lưới lấy giá trị OI/LS
 * coin GẦN NHẤT có ts ≤ t (2-con-trỏ tiến). Giới hạn STALE 60' để coin CHẾT (hết điểm) KHÔNG cộng giá trị cũ mãi
 * — coin chỉ đóng góp aggregate trong giai đoạn nó còn cập nhật (đúng survivorship: gồm khi sống, tự rụng khi chết).
 * BTC close cho diverge dùng nến ĐÓNG ≤ t ({@code headMap(t-15m,true)}). Δ24h dùng {@code floorEntry(t-24h)} trên
 * chuỗi total đã tính (mốc ≤ t-24h).
 *
 * <p><b>Warmup KHÔNG fill 0:</b> mốc không có coin active (đầu lịch sử) / chưa đủ 24h → ô TRỐNG (null), không 0.
 */
public class ExportGateFeaturesGroupBCrowd {

    private static final Logger LOG = LoggerFactory.getLogger(ExportGateFeaturesGroupBCrowd.class);
    private static final long MS_15M = 15L * 60_000L, DAY = 24L * 3600_000L;
    private static final long STALE_MS = 60L * 60_000L; // coin không có điểm trong 60' tính là không active tại t
    private static final String SET_15M = "kline_15m_btceth";
    private static final Type SERIES_TYPE = new TypeToken<TreeMap<Long, float[]>>() {}.getType();
    private static final String START_DATE = "20211201"; // OI lịch sử bắt đầu ~2021-12
    private static final String OUT = "outputs/gate_features_groupB_crowd.csv";
    private static final String GATE_RETURN = "outputs/gate_return.csv";
    private static final String DEFAULT_SYMFILE = "/tmp/oisyms.txt";

    private static final String[] COLS = {
            "b6_oiMarketTotal", "b6_oiDelta24h", "b6_oiPriceDiverge",
            "b8_lsGlobal", "b8_lsToptrader", "b8_takerBuySell"
    };

    public static void main(String[] args) {
        try {
            Configs.IS_HPO_MODE = false;
            Configs.IS_KAGGLE_MODE = true; // đọc 226 local

            String symfile = DEFAULT_SYMFILE;
            for (String a : args) if (a.toLowerCase().startsWith("symfile=")) symfile = a.substring(8).trim();

            List<String> universe = readUniverse(symfile);
            LOG.info("TASK-018 export B6/B8 | universe={} coin (gom died) | luoi 15m tu {} | {} cot",
                    universe.size(), START_DATE, COLS.length);
            if (universe.isEmpty()) throw new IllegalStateException("Universe rong — kiem tra symfile=" + symfile);

            // 1) BTC 15m → lưới mốc + giá thị trường
            TreeMap<Long, float[]> btc15 = readSeries(SET_15M, "BTCUSDT");
            if (btc15.isEmpty()) throw new IllegalStateException("kline_15m_btceth BTC rong — chay TASK-009/031 truoc.");
            long start = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;

            // lưới = mốc 15m BTC ≥ start (cùng lưới gate_return)
            long[] grid = btc15.keySet().stream().filter(t -> t >= start).mapToLong(Long::longValue).sorted().toArray();
            int G = grid.length;
            LOG.info("luoi G={} moc 15m [{} .. {}]", G, FMT.get().format(new Date(grid[0])), FMT.get().format(new Date(grid[G - 1])));

            // 2) cộng dồn từng coin vào lưới (RAM-aware: 1 coin/lần rồi giải phóng)
            double[] oiSum = new double[G]; int[] oiCnt = new int[G];
            double[] lgSum = new double[G]; int[] lgCnt = new int[G];
            double[] ltSum = new double[G]; int[] ltCnt = new int[G];
            double[] tkSum = new double[G]; int[] tkCnt = new int[G];

            int done = 0;
            for (String coin : universe) {
                accumulate(getMetricMap226(OiMetricSets.OI, coin), grid, oiSum, oiCnt);
                accumulate(getMetricMap226(OiMetricSets.LS_GLOBAL_ACC, coin), grid, lgSum, lgCnt);
                accumulate(getMetricMap226(OiMetricSets.LS_TOPTRADER_ACC, coin), grid, ltSum, ltCnt);
                accumulate(getMetricMap226(OiMetricSets.TAKER_VOL, coin), grid, tkSum, tkCnt);
                if (++done % 100 == 0) LOG.info("  da gop {}/{} coin", done, universe.size());
            }
            LOG.info("gop xong {} coin vao luoi", done);

            // 3) chuỗi oiMarketTotal theo mốc (cho Δ24h) — chỉ mốc có coin active
            TreeMap<Long, Double> oiTotalSeries = new TreeMap<>();
            for (int gi = 0; gi < G; gi++) if (oiCnt[gi] > 0) oiTotalSeries.put(grid[gi], oiSum[gi]);

            // 4) ghi + validate
            FileWriter w = new FileWriter(OUT);
            w.write("tEpochMs,tDate," + String.join(",", COLS) + "\n");
            Validate v = new Validate();
            long emitted = 0;
            for (int gi = 0; gi < G; gi++) {
                long t = grid[gi];
                Float[] f = new Float[COLS.length];
                // B6
                Float oiTotal = oiCnt[gi] > 0 ? (float) oiSum[gi] : null;
                f[0] = oiTotal;
                Float oiDelta24h = null;
                if (oiTotal != null) {
                    Map.Entry<Long, Double> past = oiTotalSeries.floorEntry(t - DAY);
                    if (past != null && past.getValue() != 0) oiDelta24h = (float) (oiSum[gi] / past.getValue() - 1.0);
                }
                f[1] = oiDelta24h;
                Float btcRet24h = btcRet(btc15, t);
                f[2] = (oiDelta24h != null && btcRet24h != null) ? oiDelta24h - btcRet24h : null;
                // B8 (mean cross-coin)
                f[3] = lgCnt[gi] > 0 ? (float) (lgSum[gi] / lgCnt[gi]) : null;
                f[4] = ltCnt[gi] > 0 ? (float) (ltSum[gi] / ltCnt[gi]) : null;
                f[5] = tkCnt[gi] > 0 ? (float) (tkSum[gi] / tkCnt[gi]) : null;

                StringBuilder sb = new StringBuilder(120);
                sb.append(t).append(',').append(FMT.get().format(new Date(t)));
                for (Float val : f) sb.append(',').append(val == null ? "" : fmt(val));
                sb.append('\n');
                w.write(sb.toString());
                emitted++;
                v.collect(t, f, oiCnt[gi]);
            }
            w.close();
            LOG.info("Ghi {} dong x {} feature -> {}", emitted, COLS.length, OUT);
            v.report(grid, oiSum, oiCnt, oiTotalSeries);
        } catch (Exception e) {
            LOG.error("ExportGateFeaturesGroupBCrowd loi", e);
            System.exit(1);
        }
        System.exit(0); // Aerospike client thread non-daemon
    }

    /** Cộng dồn 1 coin vào lưới: tại mỗi mốc t lấy giá trị GẦN NHẤT ts ≤ t (2 con trỏ), nếu (t-ts) ≤ STALE. */
    private static void accumulate(TreeMap<Long, Float> map, long[] grid, double[] sum, int[] cnt) {
        if (map == null || map.isEmpty()) return;
        long[] ts = new long[map.size()];
        float[] val = new float[map.size()];
        int n = 0;
        for (Map.Entry<Long, Float> e : map.entrySet()) { ts[n] = e.getKey(); val[n] = e.getValue(); n++; }
        int p = -1; // con trỏ điểm cuối có ts ≤ mốc hiện tại
        for (int gi = 0; gi < grid.length; gi++) {
            long t = grid[gi];
            while (p + 1 < n && ts[p + 1] <= t) p++;
            if (p >= 0 && (t - ts[p]) <= STALE_MS) { sum[gi] += val[p]; cnt[gi]++; }
        }
        // map + mảng tạm rời scope → GC giải phóng trước coin kế tiếp
    }

    private static TreeMap<Long, Float> getMetricMap226(OiMetricSets.Metric m, String coin) {
        return DataManagerAerospikeFloatSim.getMetricMap226(m.set, m.bin, coin);
    }

    /** BTC return 24h tại t bằng nến ĐÓNG ≤ t (headMap loại nến [t,t+15m)). null nếu thiếu. */
    private static Float btcRet(TreeMap<Long, float[]> btc15, long t) {
        Float now = lastClose(btc15.headMap(t - MS_15M, true));
        Float past = lastClose(btc15.headMap(t - DAY - MS_15M, true));
        if (now == null || past == null || past == 0f) return null;
        return now / past - 1f;
    }

    private static Float lastClose(NavigableMap<Long, float[]> m) { return m.isEmpty() ? null : m.lastEntry().getValue()[3]; }

    private static List<String> readUniverse(String path) throws Exception {
        List<String> out = new ArrayList<>();
        for (String line : Files.readAllLines(Paths.get(path))) {
            String s = line.trim().toUpperCase();
            if (s.matches("^[A-Z0-9]+USDT$")) out.add(s);
        }
        return out;
    }

    /** Đọc series month-key SYMBOL-YYYYMM → TreeMap<startMs, float[ohlcv]> (giống TASK-017). */
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
            ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyyMMdd-HHmm"));
    private static final ThreadLocal<SimpleDateFormat> YM =
            ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyyMM"));

    // ================== VALIDATE (§2.4) ==================
    private static final class Validate {
        final List<Float>[] dist = lists();
        final long[] nullCnt = new long[COLS.length], zeros = new long[COLS.length];
        final TreeSet<Long> featureT = new TreeSet<>();
        final Map<Integer, Integer> year2activeOi = new TreeMap<>();
        final List<Long> watchT = new ArrayList<>();

        @SuppressWarnings("unchecked")
        private static List<Float>[] lists() {
            List<Float>[] a = new List[COLS.length];
            for (int i = 0; i < a.length; i++) a[i] = new ArrayList<>();
            return a;
        }

        void collect(long t, Float[] f, int activeOi) {
            featureT.add(t);
            for (int i = 0; i < f.length; i++) {
                if (f[i] == null || Float.isNaN(f[i]) || Float.isInfinite(f[i])) { nullCnt[i]++; continue; }
                if (f[i] == 0f) zeros[i]++;
                dist[i].add(f[i]);
            }
            year2activeOi.put(year(t), activeOi);
            if (watchT.size() < 5 && (featureT.size() % 9973 == 0 || watchT.isEmpty())) watchT.add(t);
        }

        void report(long[] grid, double[] oiSum, int[] oiCnt, TreeMap<Long, Double> oiTotalSeries) {
            long n = featureT.size();
            LOG.info("=== (a) RANGE/PHAN BO moi feature (min|p1/p50/p99|max), n-nonNull ===");
            for (int i = 0; i < COLS.length; i++) {
                List<Float> r = new ArrayList<>(dist[i]); Collections.sort(r);
                LOG.info("  {} n={} min={} p1={} p50={} p99={} max={}", String.format("%-20s", COLS[i]), r.size(),
                        r.isEmpty() ? "-" : g(r.get(0)), pc(r, 1), pc(r, 50), pc(r, 99), r.isEmpty() ? "-" : g(r.get(r.size() - 1)));
            }
            LOG.info("=== (b) NULL/NaN (warmup) + 0-count — null KHONG fill 0 ===");
            for (int i = 0; i < COLS.length; i++)
                LOG.info("  {} null/NaN={}/{} zeros={}", String.format("%-20s", COLS[i]), nullCnt[i], n, zeros[i]);

            LOG.info("=== (c) RECOMPUTE doc lap ~5 moc: oiMarketTotal(arr) vs oiTotalSeries ===");
            Map<Long, Integer> t2gi = new HashMap<>();
            for (int gi = 0; gi < grid.length; gi++) t2gi.put(grid[gi], gi);
            for (long t : watchT) {
                Integer gi = t2gi.get(t);
                if (gi == null) continue;
                Double series = oiTotalSeries.get(t);
                double direct = oiSum[gi];
                LOG.info("  t={} oiTotal(arr)={} series={} cnt={} {}", FMT.get().format(new Date(t)),
                        g((float) direct), series == null ? "null" : g(series.floatValue()), oiCnt[gi],
                        (series != null && Math.abs(series - direct) < 1.0) ? "KHOP" : "(moc rong/—)");
            }

            LOG.info("=== (d) LOOK-AHEAD: resample 2-con-tro ts<=t + STALE {}'; btcRet24h headMap(t-15m); Delta24h floorEntry(t-24h). ===", STALE_MS / 60000);

            LOG.info("=== (e) ALIGN voi {} ===", GATE_RETURN);
            alignWithGateReturn();

            LOG.info("=== #coin OI active cuoi moi NAM (survivorship: gom died, tang dan theo backfill) ===");
            for (Map.Entry<Integer, Integer> e : year2activeOi.entrySet())
                LOG.info("  {}: active OI coin = {}", e.getKey(), e.getValue());
        }

        private void alignWithGateReturn() {
            try (BufferedReader br = new BufferedReader(new FileReader(GATE_RETURN))) {
                br.readLine();
                String line;
                long gateRows = 0, missing = 0, minG = Long.MAX_VALUE, maxG = Long.MIN_VALUE;
                while ((line = br.readLine()) != null) {
                    int c = line.indexOf(',');
                    if (c <= 0) continue;
                    long gt = Long.parseLong(line.substring(0, c).trim());
                    gateRows++; minG = Math.min(minG, gt); maxG = Math.max(maxG, gt);
                    if (!featureT.contains(gt)) missing++;
                }
                LOG.info("  gate rows={} range[{}..{}] | feature t={} | gate-t THIEU trong feature={} {}",
                        gateRows, FMT.get().format(new Date(minG)), FMT.get().format(new Date(maxG)), featureT.size(),
                        missing, missing == 0 ? "ALIGN OK" : "LECH (warmup: OI tu 2021-12, gate co the som hon)");
            } catch (Exception e) {
                LOG.warn("  khong doc duoc {} (chay 012 truoc?): {}", GATE_RETURN, e.getMessage());
            }
        }
    }

    private static String pc(List<Float> sorted, int p) {
        if (sorted.isEmpty()) return "-";
        int idx = Math.min(sorted.size() - 1, (int) Math.ceil(p / 100.0 * sorted.size()) - 1);
        return g(sorted.get(Math.max(0, idx)));
    }

    private static String g(float v) { return String.format(Locale.US, "%.6f", v); }
    private static int year(long ms) { return Integer.parseInt(new SimpleDateFormat("yyyy").format(new Date(ms))); }
}
