package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.TreeMap;

/**
 * Tính EXACT 5 OI feature (oiDelta24h, oiZ expanding, lsGlobal, lsToptrader, takerBuy) — logic COPY
 * CHÍNH XÁC {@code SelectorOiProvider.buildCoin} — rồi PUSH đoạn ROLLING gần đây sang Aerospike-242
 * ({@link OiFeatLiveSets}). Live ({@code LiveOiFeatProvider}) chỉ lookup, không tính → không OOM.
 *
 * <p>HAI CHẾ ĐỘ (env {@code OI_USE_ACCUM}):
 * <ul>
 *   <li><b>BATCH</b> (mặc định, OI_USE_ACCUM!=1): mỗi coin đọc FULL history từ Oracle
 *       ({@code getMetricMap226}) ∪ 242-recent, tính expanding từ đầu. Guard-1 (Oracle health) áp dụng.
 *       Nặng (~29') và phụ thuộc Oracle mỗi lượt.</li>
 *   <li><b>INCREMENTAL / C1</b> (OI_USE_ACCUM=1): giữ accumulator expanding {lastTs,sum,sumSq,n} per-coin
 *       trên 242 ({@link OiFeatLiveSets#ACCUM_SET}). Mỗi lượt chỉ đọc 242-tail (đã có ~14d), fold điểm mới
 *       → z BIT-GIỐNG batch (cùng running-sum) mà KHÔNG đọc Oracle. Coin chưa có accum -> self-seed 1 lần.</li>
 * </ul>
 *
 * <p>Bootstrap: chạy {@code main("SEED")} 1 lần (đọc Oracle full, ghi feature + persist accum) TRƯỚC khi bật
 * OI_USE_ACCUM=1. Kiểm chứng: {@code main("PARITY")} in max diff giữa checkpoint+incremental và batch (mong ~0).
 * Oracle vẫn giữ làm KHO LẠNH để (re)seed — C1 chỉ bỏ phụ thuộc LÚC CHẠY, không xoá nhu cầu lưu trữ.
 */
public class ComputeOiFeat2Live242 {

    private static final Logger LOG = LoggerFactory.getLogger(ComputeOiFeat2Live242.class);
    private static final long STALE_MS = 60L * 60_000L;   // 1h — khớp SelectorOiProvider
    private static final long DAY = 24L * 3600_000L;

    /** [C1] Accumulator expanding cho 1 coin (persist trên 242 set oi_feat_accum). */
    public static class OiAccum {
        public long lastTs;
        public double sum;
        public double sumSq;
        public long n;
        public OiAccum(long lastTs, double sum, double sumSq, long n) {
            this.lastTs = lastTs; this.sum = sum; this.sumSq = sumSq; this.n = n;
        }
    }

    /** Kết quả 1 lượt walk: series feature (ts→5float) + accum sau khi fold. */
    private static class WalkResult {
        final TreeMap<Long, float[]> series;
        final OiAccum acc;
        WalkResult(TreeMap<Long, float[]> series, OiAccum acc) { this.series = series; this.acc = acc; }
    }

    public static void main(String[] args) {
        String mode = args.length > 0 ? args[0].toUpperCase() : "";
        if ("READ".equals(mode)) { readVerify(envInt("READ_N", 10)); System.exit(0); }
        if ("SEED".equals(mode)) { seedAll(); System.exit(0); }
        if ("PARITY".equals(mode)) { parityCheck(envInt("PARITY_N", 30)); System.exit(0); }
        int days = envInt("OI_FEAT_DAYS", 14);
        boolean dry = "1".equals(System.getenv("OI_FEAT_DRY"));
        runOnce(days, dry);
        System.exit(0);
    }

    /** VERIFY: đọc oi_feat_* THỰC trên 242 (đúng cái LiveOiFeatProvider/selector đọc) cho N coin đầu có data. */
    public static void readVerify(int n) {
        Map<String, Short> syms = SimpleSymbolMapper.getInstance().getAllMappings();
        int shown = 0;
        for (String coin : syms.keySet()) {
            TreeMap<Long, Float> z = DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.OI_Z, OiFeatLiveSets.BIN, coin);
            if (z == null || z.isEmpty()) continue;
            TreeMap<Long, Float> d = DataManagerAerospikeFloatSim.getMetricMap242(OiFeatLiveSets.OI_DELTA24H, OiFeatLiveSets.BIN, coin);
            long ts = z.lastKey();
            LOG.info("[READ242 {}] ts={} | delta24h={} z={} | zPts={}",
                    coin, ts, d == null ? null : d.get(ts), z.get(ts), z.size());
            if (++shown >= n) break;
        }
        LOG.info("READ242 xong: hien {} coin co oi_feat_*", shown);
    }

    /**
     * 1 LƯỢT compute + push (callable từ scheduler trong ingestor 242). KHÔNG System.exit.
     * BATCH (mặc định) hoặc INCREMENTAL (OI_USE_ACCUM=1). Xem javadoc class.
     */
    public static void runOnce(int days, boolean dry) {
        long cutoff = System.currentTimeMillis() - days * DAY;
        boolean useAccum = "1".equals(System.getenv("OI_USE_ACCUM"));
        Map<String, Short> syms = SimpleSymbolMapper.getInstance().getAllMappings();
        LOG.info("ComputeOiFeat2Live242 START | coins={} | rolling {} ngay (cutoff ts={}) | dry={} | mode={}",
                syms.size(), days, cutoff, dry, useAccum ? "INCREMENTAL(accum)" : "BATCH(oracle-full)");

        // [OI-GUARD-1] Chỉ probe Oracle khi run SẼ đọc Oracle (BATCH). INCREMENTAL không đọc Oracle -> bỏ probe
        // (giữ decouple). BATCH: Oracle rỗng/lỗi -> ABORT, không ghi đè oi_feat cũ bằng baseline cụt.
        if (!dry && !useAccum) {
            if (!oracleHealthy()) {
                LOG.error("[OI-GUARD-1] Oracle OI full-history KHONG doc duoc (BTC/ETH rong/loi) "
                        + "-> ABORT run, GIU oi_feat cu tren 242 (khong ghi de)");
                return;
            }
        }

        int done = 0, pushed = 0, empty = 0, seeded = 0;
        for (String coin : syms.keySet()) {
            try {
                TreeMap<Long, float[]> toWrite;
                if (useAccum) {
                    double[] a = DataManagerAerospikeFloatSim.readAccum242(
                            OiFeatLiveSets.ACCUM_SET, OiFeatLiveSets.ACCUM_BIN, coin);
                    if (a == null) {
                        // Self-seed: coin mới / chưa seed -> walk full 1 lần (đọc Oracle ∪ 242), persist accum.
                        WalkResult full = walkFull(coin);
                        if (full == null) { empty++; continue; }
                        persistAccum(coin, full.acc);
                        seeded++;
                        toWrite = new TreeMap<>(full.series.tailMap(cutoff, true));
                    } else {
                        OiAccum acc = new OiAccum((long) a[0], a[1], a[2], (long) a[3]);
                        WalkResult inc = walkIncremental(coin, acc);
                        if (inc == null) { empty++; continue; }
                        persistAccum(coin, inc.acc);
                        toWrite = inc.series; // chỉ điểm mới
                    }
                } else {
                    WalkResult full = walkFull(coin);
                    if (full == null) { empty++; continue; }
                    toWrite = new TreeMap<>(full.series.tailMap(cutoff, true));
                }
                if (toWrite.isEmpty()) { empty++; continue; }
                if (dry) {
                    if (done < 8) {
                        Map.Entry<Long, float[]> last = toWrite.lastEntry();
                        LOG.info("  [DRY {}] writePts={} | lastTs={} oi5={}", coin, toWrite.size(), last.getKey(), fmt(last.getValue()));
                    }
                } else {
                    writeFeatures(coin, toWrite);
                    pushed++;
                }
                done++;
                if (done % 100 == 0) LOG.info("  ... {} coin xu ly ({} push, {} empty, {} self-seed)", done, pushed, empty, seeded);
            } catch (Exception e) {
                LOG.warn("coin {} loi: {}", coin, e.toString());
            }
        }
        LOG.info("ComputeOiFeat2Live242 DONE | processed={} pushed={} empty(no-oi)={} self-seed={} mode={}",
                done, pushed, empty, seeded, useAccum ? "INCR" : "BATCH");
    }

    /** SEED 1 lần: walk full mỗi coin (đọc Oracle ∪ 242), ghi feature rolling + persist accum. Chạy TRƯỚC cutover. */
    public static void seedAll() {
        if (!oracleHealthy()) { LOG.error("[SEED] Oracle khong doc duoc -> HUY seed (tranh accum sai)."); return; }
        long cutoff = System.currentTimeMillis() - envInt("OI_FEAT_DAYS", 14) * DAY;
        Map<String, Short> syms = SimpleSymbolMapper.getInstance().getAllMappings();
        LOG.info("[SEED] START coins={}", syms.size());
        int done = 0, seeded = 0, empty = 0;
        for (String coin : syms.keySet()) {
            try {
                WalkResult full = walkFull(coin);
                if (full == null) { empty++; continue; }
                persistAccum(coin, full.acc);
                TreeMap<Long, float[]> w = new TreeMap<>(full.series.tailMap(cutoff, true));
                if (!w.isEmpty()) writeFeatures(coin, w);
                seeded++;
                done++;
                if (done % 100 == 0) LOG.info("[SEED] ... {} coin ({} seeded, {} empty)", done, seeded, empty);
            } catch (Exception e) {
                LOG.warn("[SEED] coin {} loi: {}", coin, e.toString());
            }
        }
        LOG.info("[SEED] DONE seeded={} empty={}", seeded, empty);
    }

    /**
     * PARITY: chứng minh checkpoint+incremental == batch. Với N coin: dùng batch(full Oracle) làm chuẩn; cắt
     * T0 = now-3d, dựng accum tới T0 (từ full), rồi fold (T0,now] từ 242 THẬT; so z/delta vs batch. In max diff
     * (mong ~0, chỉ sai số float). KHÔNG ghi gì. Cũng lộ mismatch dữ liệu 242 vs Oracle nếu có.
     */
    public static void parityCheck(int n) {
        Map<String, Short> syms = SimpleSymbolMapper.getInstance().getAllMappings();
        long t0 = System.currentTimeMillis() - 3L * DAY;
        double gMaxZ = 0, gMaxD = 0;
        int checked = 0;
        for (String coin : syms.keySet()) {
            TreeMap<Long, Float> oiF = mergedMetric(OiMetricSets.OI.set, OiMetricSets.OI.bin, coin);
            if (oiF.size() < 100) continue;
            TreeMap<Long, Float> lsgF = mergedMetric(OiMetricSets.LS_GLOBAL_ACC.set, OiMetricSets.LS_GLOBAL_ACC.bin, coin);
            TreeMap<Long, Float> lstF = mergedMetric(OiMetricSets.LS_TOPTRADER_ACC.set, OiMetricSets.LS_TOPTRADER_ACC.bin, coin);
            TreeMap<Long, Float> tkF = mergedMetric(OiMetricSets.TAKER_VOL.set, OiMetricSets.TAKER_VOL.bin, coin);
            TreeMap<Long, float[]> batch = walkSeries(oiF, lsgF, lstF, tkF, null, Long.MIN_VALUE, Long.MAX_VALUE).series;
            OiAccum accT0 = walkSeries(oiF, lsgF, lstF, tkF, null, Long.MIN_VALUE, t0).acc; // fold <= t0

            TreeMap<Long, Float> oi2 = DataManagerAerospikeFloatSim.getMetricMap242(OiMetricSets.OI.set, OiMetricSets.OI.bin, coin);
            TreeMap<Long, Float> lsg2 = DataManagerAerospikeFloatSim.getMetricMap242(OiMetricSets.LS_GLOBAL_ACC.set, OiMetricSets.LS_GLOBAL_ACC.bin, coin);
            TreeMap<Long, Float> lst2 = DataManagerAerospikeFloatSim.getMetricMap242(OiMetricSets.LS_TOPTRADER_ACC.set, OiMetricSets.LS_TOPTRADER_ACC.bin, coin);
            TreeMap<Long, Float> tk2 = DataManagerAerospikeFloatSim.getMetricMap242(OiMetricSets.TAKER_VOL.set, OiMetricSets.TAKER_VOL.bin, coin);
            TreeMap<Long, float[]> inc = walkSeries(oi2, lsg2, lst2, tk2, accT0, t0, Long.MAX_VALUE).series;

            double maxZ = 0, maxD = 0;
            int cmp = 0;
            for (Map.Entry<Long, float[]> e : inc.entrySet()) {
                float[] b = batch.get(e.getKey());
                if (b == null) continue;
                float[] v = e.getValue();
                if (!Float.isNaN(b[1]) && !Float.isNaN(v[1])) { maxZ = Math.max(maxZ, Math.abs(b[1] - v[1])); cmp++; }
                if (!Float.isNaN(b[0]) && !Float.isNaN(v[0])) maxD = Math.max(maxD, Math.abs(b[0] - v[0]));
            }
            gMaxZ = Math.max(gMaxZ, maxZ);
            gMaxD = Math.max(gMaxD, maxD);
            LOG.info("[PARITY {}] fullPts={} incPts={} cmp={} maxDiffZ={} maxDiffDelta={}", coin, oiF.size(), inc.size(), cmp, maxZ, maxD);
            if (++checked >= n) break;
        }
        LOG.info("[PARITY] DONE checked={} GLOBAL maxDiffZ={} maxDiffDelta={} (mong ~0, chi sai so float/NaN-seam)", checked, gMaxZ, gMaxD);
    }

    /** BATCH: đọc full (Oracle ∪ 242) 4 metric, walk toàn bộ. null nếu không có OI. */
    private static WalkResult walkFull(String coin) {
        TreeMap<Long, Float> oi = mergedMetric(OiMetricSets.OI.set, OiMetricSets.OI.bin, coin);
        if (oi.isEmpty()) return null;
        TreeMap<Long, Float> lsg = mergedMetric(OiMetricSets.LS_GLOBAL_ACC.set, OiMetricSets.LS_GLOBAL_ACC.bin, coin);
        TreeMap<Long, Float> lst = mergedMetric(OiMetricSets.LS_TOPTRADER_ACC.set, OiMetricSets.LS_TOPTRADER_ACC.bin, coin);
        TreeMap<Long, Float> tk = mergedMetric(OiMetricSets.TAKER_VOL.set, OiMetricSets.TAKER_VOL.bin, coin);
        return walkSeries(oi, lsg, lst, tk, null, Long.MIN_VALUE, Long.MAX_VALUE);
    }

    /** INCREMENTAL: chỉ đọc 242 (đã có ~14d), fold điểm ts>acc.lastTs. null nếu 242 chưa có OI. */
    private static WalkResult walkIncremental(String coin, OiAccum acc) {
        TreeMap<Long, Float> oi = DataManagerAerospikeFloatSim.getMetricMap242(OiMetricSets.OI.set, OiMetricSets.OI.bin, coin);
        if (oi == null || oi.isEmpty()) return null;
        TreeMap<Long, Float> lsg = DataManagerAerospikeFloatSim.getMetricMap242(OiMetricSets.LS_GLOBAL_ACC.set, OiMetricSets.LS_GLOBAL_ACC.bin, coin);
        TreeMap<Long, Float> lst = DataManagerAerospikeFloatSim.getMetricMap242(OiMetricSets.LS_TOPTRADER_ACC.set, OiMetricSets.LS_TOPTRADER_ACC.bin, coin);
        TreeMap<Long, Float> tk = DataManagerAerospikeFloatSim.getMetricMap242(OiMetricSets.TAKER_VOL.set, OiMetricSets.TAKER_VOL.bin, coin);
        return walkSeries(oi, lsg, lst, tk, acc, acc.lastTs, Long.MAX_VALUE);
    }

    /**
     * LÕI expanding — COPY CHÍNH XÁC SelectorOiProvider.buildCoin. Fold điểm oi có foldAfterTs &lt; ts &le; uptoTs
     * vào (sum,sumSq,n) khởi từ {@code start} (null = fresh). Trả series feature cho các điểm đã fold + accum cuối.
     */
    private static WalkResult walkSeries(TreeMap<Long, Float> oi, TreeMap<Long, Float> lsg, TreeMap<Long, Float> lst,
                                         TreeMap<Long, Float> tk, OiAccum start, long foldAfterTs, long uptoTs) {
        double sum = start == null ? 0 : start.sum;
        double sumSq = start == null ? 0 : start.sumSq;
        long n = start == null ? 0 : start.n;
        long lastTs = start == null ? Long.MIN_VALUE : start.lastTs;
        TreeMap<Long, float[]> series = new TreeMap<>();
        if (oi == null || oi.isEmpty()) return new WalkResult(series, new OiAccum(lastTs, sum, sumSq, n));
        for (Map.Entry<Long, Float> en : oi.entrySet()) {
            long t = en.getKey();
            if (t <= foldAfterTs) continue;
            if (t > uptoTs) break;
            float oiVal = en.getValue();
            sum += oiVal;
            sumSq += (double) oiVal * oiVal;
            n++;
            lastTs = t;
            float oiDelta = Float.NaN;
            Map.Entry<Long, Float> past = oi.floorEntry(t - DAY);
            if (past != null && (t - DAY - past.getKey()) <= STALE_MS && past.getValue() != 0f)
                oiDelta = oiVal / past.getValue() - 1f;
            float z = Float.NaN;
            if (n >= 2) {
                double mean = sum / n;
                double var = (sumSq - (sum * sum) / n) / (n - 1);
                if (var > 0) z = (float) ((oiVal - mean) / Math.sqrt(var));
            }
            Float lg = floorStale(lsg, t);
            Float lt = floorStale(lst, t);
            Float r = floorStale(tk, t);
            float takerBuy = (r != null && r >= 0f) ? r / (1f + r) : Float.NaN;
            series.put(t, new float[]{oiDelta, z, lg == null ? Float.NaN : lg, lt == null ? Float.NaN : lt, takerBuy});
        }
        return new WalkResult(series, new OiAccum(lastTs, sum, sumSq, n));
    }

    /** Tách series thành 5 map (bỏ NaN — Gson không serialize NaN) và merge-write xuống 242. */
    private static void writeFeatures(String coin, TreeMap<Long, float[]> series) {
        TreeMap<Long, Float> mDelta = new TreeMap<>(), mZ = new TreeMap<>(),
                mLsg = new TreeMap<>(), mLst = new TreeMap<>(), mTk = new TreeMap<>();
        for (Map.Entry<Long, float[]> e : series.entrySet()) {
            long t = e.getKey();
            float[] v = e.getValue();
            if (!Float.isNaN(v[0])) mDelta.put(t, v[0]);
            if (!Float.isNaN(v[1])) mZ.put(t, v[1]);
            if (!Float.isNaN(v[2])) mLsg.put(t, v[2]);
            if (!Float.isNaN(v[3])) mLst.put(t, v[3]);
            if (!Float.isNaN(v[4])) mTk.put(t, v[4]);
        }
        DataManagerAerospikeFloatSim.writeMetricMap242(OiFeatLiveSets.OI_DELTA24H, OiFeatLiveSets.BIN, coin, mDelta);
        DataManagerAerospikeFloatSim.writeMetricMap242(OiFeatLiveSets.OI_Z, OiFeatLiveSets.BIN, coin, mZ);
        DataManagerAerospikeFloatSim.writeMetricMap242(OiFeatLiveSets.LS_GLOBAL, OiFeatLiveSets.BIN, coin, mLsg);
        DataManagerAerospikeFloatSim.writeMetricMap242(OiFeatLiveSets.LS_TOPTRADER, OiFeatLiveSets.BIN, coin, mLst);
        DataManagerAerospikeFloatSim.writeMetricMap242(OiFeatLiveSets.TAKER_BUY, OiFeatLiveSets.BIN, coin, mTk);
    }

    private static void persistAccum(String coin, OiAccum acc) {
        DataManagerAerospikeFloatSim.writeAccum242(OiFeatLiveSets.ACCUM_SET, OiFeatLiveSets.ACCUM_BIN,
                coin, acc.lastTs, acc.sum, acc.sumSq, acc.n);
    }

    /** Guard-1 probe: OI full-history BTC/ETH đọc được từ Oracle? (true = khỏe). */
    private static boolean oracleHealthy() {
        for (String ref : new String[]{"BTCUSDT", "ETHUSDT"}) {
            try {
                TreeMap<Long, Float> f = DataManagerAerospikeFloatSim.getMetricMap226(
                        OiMetricSets.OI.set, OiMetricSets.OI.bin, ref);
                if (f != null && !f.isEmpty()) return true;
            } catch (Exception e) {
                LOG.warn("[OI-GUARD-1] probe {} loi: {}", ref, e.toString());
            }
        }
        return false;
    }

    /** Merge Oracle-full (getClientOracle) ∪ 242-recent forward cho 1 metric raw. */
    private static TreeMap<Long, Float> mergedMetric(String set, String bin, String coin) {
        TreeMap<Long, Float> full = DataManagerAerospikeFloatSim.getMetricMap226(set, bin, coin);
        TreeMap<Long, Float> recent = DataManagerAerospikeFloatSim.getMetricMap242(set, bin, coin);
        TreeMap<Long, Float> out = (full == null) ? new TreeMap<>() : new TreeMap<>(full);
        if (recent != null) out.putAll(recent); // 242 forward mới hơn -> ghi đè overlap
        return out;
    }

    private static Float floorStale(TreeMap<Long, Float> m, long t) {
        if (m == null || m.isEmpty()) return null;
        Map.Entry<Long, Float> e = m.floorEntry(t);
        if (e == null || (t - e.getKey()) > STALE_MS) return null;
        return e.getValue();
    }

    private static String fmt(float[] v) {
        return String.format("[d=%.4f z=%.3f lsg=%.3f lst=%.3f tk=%.3f]", v[0], v[1], v[2], v[3], v[4]);
    }

    private static int envInt(String k, int d) {
        String v = System.getenv(k);
        try {
            return v == null ? d : Integer.parseInt(v.trim());
        } catch (Exception e) {
            return d;
        }
    }
}
