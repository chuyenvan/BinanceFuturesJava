package com.binance.chuyennd.ai_ml.features.export;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.FileWriter;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-012 (H1_GATE_SPEC §1) — export GATE label = retMktMedian(t,H) RETURN THÔ (KHÔNG threshold; 3-class ở H2).
 *
 * retMktMedian(t,H) = median over {sym ∈ altUSDT-perp (trừ BTC,ETH), có close(t) & close(t+H)} của
 *                     [close_sym(t+H)/close_sym(t) − 1].  close-to-close từ kline_1m_opt.  sample t mỗi 15m.
 * H ∈ {4h,12h,24h} = {16,48,96} bước 15m. Look-ahead: chỉ chạm close tại t và t+H; t+H>nay → bỏ dòng đó.
 *
 * Streaming: 4/12/24h là bội 15m → mọi mốc nằm trên lưới 15m. Giữ RING close-map 97 bước gần nhất;
 * tại bước i tính ret cho t=i−Hsteps (dùng ring[t] & ring[i]); emit dòng t khi i=t+96 (đủ cả 3 H).
 * Đọc-only 226 (box cần AEROSPIKE_READ_CLUSTER=226 → getReadClient→226).
 */
public class ExportGateReturn {

    private static final Logger LOG = LoggerFactory.getLogger(ExportGateReturn.class);
    private static final long MS_15M = 15L * 60_000L;
    private static final int[] H_STEPS = {16, 48, 96};   // 4h,12h,24h tính theo bước-15m
    private static final String[] H_NAME = {"4h", "12h", "24h"};
    private static final String START_DATE = "20210101";
    private static final String OUT = "outputs/gate_return.csv";

    private static boolean isAlt(String s) {
        return s.endsWith("USDT") && !s.equals("BTCUSDT") && !s.equals("ETHUSDT")
                && !s.contains("_") && !s.contains("USDC") && !s.equals("BTCDOMUSDT");
    }

    public static void main(String[] args) {
        try {
            long start = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
            long end = System.currentTimeMillis();
            LOG.info("🏷️ TASK-012 export gate label retMktMedian | {} → nay | sample 15m | H={4h,12h,24h}", START_DATE);

            // ring: gridStep -> (symbol->close) cho alt; chỉ giữ 97 bước gần nhất
            Map<Long, Map<String, Float>> ring = new HashMap<>();
            Set<Long> hadData = new HashSet<>();
            // pending row: tStep -> [ret4,ret12,ret24,n4,n12,n24]
            Map<Long, double[]> pending = new HashMap<>();
            // stats validate
            List<Float>[] retAll = new List[]{new ArrayList<Float>(), new ArrayList<>(), new ArrayList<>()};
            Map<Integer, List<Integer>> year2nCoin = new TreeMap<>();   // dùng n_24h
            // watch (recompute + crash audit)
            Map<Long, double[]> watched = new HashMap<>();
            Set<Long> watchSteps = new HashSet<>();
            for (String d : new String[]{"20210915-1200","20220510-1200","20220512-0000","20221108-1200","20221109-1200","20230615-1200","20240315-1200"})
                watchSteps.add(parse(d) / MS_15M);

            FileWriter w = new FileWriter(OUT);
            w.write("tEpochMs,tDate,ret_4h,ret_12h,ret_24h,n_4h,n_12h,n_24h\n");
            long emitted = 0, days = 0;

            for (long day = start; day < end; day += 24L * Utils.TIME_HOUR) {
                TreeMap<Long, Map<String, KlineObjectSimple>> oneDay = DataManagerAerospikeFloatSim.readDataFromAerospike1M(day);
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : oneDay.entrySet()) {
                    long epoch = e.getKey();
                    if (epoch % MS_15M != 0) continue;          // chỉ lưới 15m
                    long i = epoch / MS_15M;
                    Map<String, Float> closeI = new HashMap<>();
                    for (Map.Entry<String, KlineObjectSimple> se : e.getValue().entrySet()) {
                        if (!isAlt(se.getKey())) continue;
                        KlineObjectSimple k = se.getValue();
                        if (Utils.isTickerAvailable(k)) closeI.put(se.getKey(), k.priceClose);
                    }
                    ring.put(i, closeI); hadData.add(i);

                    // tính ret cho t = i − Hsteps
                    for (int h = 0; h < 3; h++) {
                        long t = i - H_STEPS[h];
                        Map<String, Float> closeT = ring.get(t);
                        if (closeT == null || !hadData.contains(t)) continue;
                        List<Float> rets = new ArrayList<>();
                        for (Map.Entry<String, Float> ce : closeT.entrySet()) {
                            Float cI = closeI.get(ce.getKey());
                            if (cI != null && ce.getValue() != null && ce.getValue() > 0)
                                rets.add(cI / ce.getValue() - 1f);
                        }
                        double[] row = pending.computeIfAbsent(t, x -> new double[]{Double.NaN, Double.NaN, Double.NaN, 0, 0, 0});
                        if (!rets.isEmpty()) { row[h] = median(rets); row[3 + h] = rets.size(); }
                    }

                    // emit t_emit = i − 96 (đủ cả 3 H)
                    long te = i - 96;
                    if (hadData.contains(te) && pending.containsKey(te)) {
                        double[] row = pending.remove(te);
                        long tEpoch = te * MS_15M;
                        w.write(String.format(Locale.US, "%d,%s,%s,%s,%s,%d,%d,%d\n",
                                tEpoch, FMT.get().format(new Date(tEpoch)),
                                f(row[0]), f(row[1]), f(row[2]), (int) row[3], (int) row[4], (int) row[5]));
                        emitted++;
                        for (int h = 0; h < 3; h++) if (!Double.isNaN(row[h])) retAll[h].add((float) row[h]);
                        year2nCoin.computeIfAbsent(year(tEpoch), x -> new ArrayList<>()).add((int) row[5]);
                        if (watchSteps.contains(te)) watched.put(te, row);
                    }
                    ring.remove(i - 96);   // evict ngoài cửa sổ
                }
                if (++days % 200 == 0) LOG.info("   ... {} ngày, {}, emitted={}", days, Utils.normalizeDateYYYYMMDD(day), emitted);
            }
            w.close();
            LOG.info("✅ Ghi {} dòng → {} | range {} → ~nay", emitted, OUT, START_DATE);

            validate(retAll, year2nCoin, watched);
        } catch (Exception e) {
            LOG.error("ExportGateReturn lỗi", e);
        }
    }

    private static void validate(List<Float>[] retAll, Map<Integer, List<Integer>> year2nCoin, Map<Long, double[]> watched) throws Exception {
        // (a) phân bố
        LOG.info("=== (a) PHÂN BỐ return mỗi H (p1/p5/p50/p95/p99 | #ret≤−15%) ===");
        for (int h = 0; h < 3; h++) {
            List<Float> r = retAll[h]; Collections.sort(r);
            long tail = r.stream().filter(x -> x <= -0.15f).count();
            LOG.info("  {}: n={} | p1={} p5={} p50={} p95={} p99={} | đuôi(≤−15%)={} ({}%)",
                    H_NAME[h], r.size(), pc(r, 1), pc(r, 5), pc(r, 50), pc(r, 95), pc(r, 99),
                    tail, r.isEmpty() ? 0 : String.format(Locale.US, "%.2f", 100.0 * tail / r.size()));
        }
        // (b)+(c) recompute độc lập + look-ahead (chỉ chạm t & t+H)
        LOG.info("=== (b/c) RECOMPUTE độc lập (đọc lại close t & t+H trực tiếp) ===");
        for (Map.Entry<Long, double[]> e : watched.entrySet()) {
            long t = e.getKey(); double[] row = e.getValue();
            for (int h = 0; h < 3; h++) {
                long tEpoch = t * MS_15M, thEpoch = (t + H_STEPS[h]) * MS_15M;
                Float reMed = recomputeMedian(tEpoch, thEpoch);
                String exp = f(row[h]);
                boolean ok = reMed != null && Math.abs(reMed - row[h]) < 1e-4;
                LOG.info("  t={} {} : export={} recompute={} {}", FMT.get().format(new Date(tEpoch)), H_NAME[h],
                        exp, reMed == null ? "null" : String.format(Locale.US, "%.5f", reMed), ok ? "KHỚP ✅" : "LỆCH 🔴");
            }
        }
        // (d) cross-audit cú sập (ret_24h tại watch)
        LOG.info("=== (d) CROSS-AUDIT cú sập — ret_24h (kỳ vọng âm sâu quanh LUNA 05/2022, FTT 11/2022) ===");
        for (Map.Entry<Long, double[]> e : new TreeMap<>(watched).entrySet())
            LOG.info("  t={} : ret_24h={}", FMT.get().format(new Date(e.getKey() * MS_15M)), f(e.getValue()[2]));
        // (e) nCoin theo năm
        LOG.info("=== (e) nCoin (median alt, n_24h) theo NĂM: min / median / #(<50) ===");
        for (Map.Entry<Integer, List<Integer>> e : year2nCoin.entrySet()) {
            List<Integer> v = e.getValue(); Collections.sort(v);
            long lt50 = v.stream().filter(x -> x < 50).count();
            LOG.info("  {}: min={} median={} #(<50)={}/{}", e.getKey(), v.get(0), v.get(v.size() / 2), lt50, v.size());
        }
    }

    /** Recompute median ĐỘC LẬP: đọc lại 2 phút (t, t+H) trực tiếp, KHÔNG chạm giá khác. */
    private static Float recomputeMedian(long tEpoch, long thEpoch) throws Exception {
        Map<String, KlineObjectSimple> mt = oneMinute(tEpoch), mth = oneMinute(thEpoch);
        if (mt == null || mth == null) return null;
        List<Float> rets = new ArrayList<>();
        for (Map.Entry<String, KlineObjectSimple> e : mt.entrySet()) {
            if (!isAlt(e.getKey()) || !Utils.isTickerAvailable(e.getValue())) continue;
            KlineObjectSimple kth = mth.get(e.getKey());
            if (kth != null && Utils.isTickerAvailable(kth) && e.getValue().priceClose > 0)
                rets.add(kth.priceClose / e.getValue().priceClose - 1f);
        }
        return rets.isEmpty() ? null : median(rets);
    }

    private static Map<String, KlineObjectSimple> oneMinute(long epoch) throws Exception {
        TreeMap<Long, Map<String, KlineObjectSimple>> m = DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(epoch, 1);
        return m.isEmpty() ? null : m.firstEntry().getValue();
    }

    private static float median(List<Float> v) {
        Collections.sort(v);
        int n = v.size();
        return n % 2 == 1 ? v.get(n / 2) : (v.get(n / 2 - 1) + v.get(n / 2)) / 2f;
    }

    private static String pc(List<Float> sorted, int p) {
        if (sorted.isEmpty()) return "-";
        int idx = Math.min(sorted.size() - 1, (int) Math.ceil(p / 100.0 * sorted.size()) - 1);
        if (idx < 0) idx = 0;
        return String.format(Locale.US, "%.4f", sorted.get(idx));
    }

    private static String f(double v) { return Double.isNaN(v) ? "" : String.format(Locale.US, "%.6f", v); }

    private static final ThreadLocal<SimpleDateFormat> FMT =
            ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyyMMdd-HHmm")); // GMT+7

    private static long parse(String key) { try { return FMT.get().parse(key).getTime(); } catch (Exception e) { throw new RuntimeException(e); } }
    private static int year(long ms) { return Integer.parseInt(new SimpleDateFormat("yyyy").format(new Date(ms))); }
}
